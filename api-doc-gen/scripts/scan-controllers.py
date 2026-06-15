#!/usr/bin/env python3
"""Scan Spring Boot Controller and Knife4j/Swagger annotations, output structured JSON."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path


# ---------------------------------------------------------------------------
# Progress / logging (stderr)
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Comment stripping & annotation parsing
# ---------------------------------------------------------------------------

def strip_comments(source: str) -> str:
    """Remove Java block and line comments while preserving string literals."""
    result = []
    i = 0
    length = len(source)
    in_string = False
    string_char = ""

    while i < length:
        ch = source[i]

        if in_string:
            result.append(ch)
            if ch == "\\" and i + 1 < length:
                result.append(source[i + 1])
                i += 2
                continue
            if ch == string_char:
                in_string = False
            i += 1
            continue

        if ch in ('"', "'"):
            in_string = True
            string_char = ch
            result.append(ch)
            i += 1
            continue

        if ch == "/" and i + 1 < length:
            nxt = source[i + 1]
            if nxt == "/":
                while i < length and source[i] != "\n":
                    i += 1
                continue
            if nxt == "*":
                i += 2
                while i + 1 < length and not (source[i] == "*" and source[i + 1] == "/"):
                    i += 1
                i = min(i + 2, length)
                continue

        result.append(ch)
        i += 1

    return "".join(result)


def find_balanced_paren(text: str, open_idx: int) -> int:
    """Return index of closing ')' matching '(' at open_idx, or -1."""
    depth = 0
    in_string = False
    string_char = ""
    i = open_idx
    while i < len(text):
        ch = text[i]
        if in_string:
            if ch == "\\" and i + 1 < len(text):
                i += 2
                continue
            if ch == string_char:
                in_string = False
            i += 1
            continue
        if ch in ('"', "'"):
            in_string = True
            string_char = ch
            i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def extract_annotations(text: str) -> list[tuple[str, str]]:
    """Extract (name, args) tuples from annotation blocks in text."""
    annotations: list[tuple[str, str]] = []
    i = 0
    while i < len(text):
        match = re.search(r"@([\w.$]+)", text[i:])
        if not match:
            break
        start = i + match.start()
        name = match.group(1).split(".")[-1]
        j = i + match.end()
        args = ""
        if j < len(text) and text[j] == "(":
            close = find_balanced_paren(text, j)
            if close == -1:
                break
            args = text[j + 1:close]
            j = close + 1
        annotations.append((name, args.strip()))
        i = j
    return annotations


def parse_annotation_args(args: str) -> dict[str, str]:
    """Parse annotation arguments into a flat dict (best-effort)."""
    if not args:
        return {}
    result: dict[str, str] = {}

    positional: list[str] = []

    def split_args(s: str) -> list[str]:
        parts: list[str] = []
        current: list[str] = []
        depth = 0
        in_str = False
        str_ch = ""
        k = 0
        while k < len(s):
            c = s[k]
            if in_str:
                current.append(c)
                if c == "\\" and k + 1 < len(s):
                    current.append(s[k + 1])
                    k += 2
                    continue
                if c == str_ch:
                    in_str = False
                k += 1
                continue
            if c in ('"', "'"):
                in_str = True
                str_ch = c
                current.append(c)
                k += 1
                continue
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif c == "," and depth == 0:
                parts.append("".join(current).strip())
                current = []
                k += 1
                continue
            current.append(c)
            k += 1
        if current:
            parts.append("".join(current).strip())
        return parts

    for part in split_args(args):
        if "=" in part:
            key, _, val = part.partition("=")
            result[key.strip()] = val.strip()
        else:
            positional.append(part.strip())

    if positional and "value" not in result:
        result["value"] = positional[0]
    if len(positional) > 1 and "name" not in result:
        result["name"] = positional[0]
    return result


def unquote(value: str) -> str:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def get_attr(args: dict[str, str], *keys: str, default: str = "") -> str:
    for key in keys:
        if key in args:
            return unquote(args[key])
    return default


def get_bool_attr(args: dict[str, str], key: str, default: bool | None = None) -> bool | None:
    if key not in args:
        return default
    val = args[key].strip().lower()
    if val in ("true", "false"):
        return val == "true"
    return default


# ---------------------------------------------------------------------------
# Path & type helpers
# ---------------------------------------------------------------------------

def join_paths(base: str, sub: str) -> str:
    parts = []
    for segment in (base, sub):
        segment = (segment or "").strip()
        if not segment:
            continue
        segment = segment.strip("/")
        if segment:
            parts.append(segment)
    if not parts:
        return "/"
    return "/" + "/".join(parts)


def normalize_type(type_name: str) -> str:
    return re.sub(r"\s+", " ", type_name.strip())


def split_parameters(param_str: str) -> list[str]:
    """Split method parameter list by comma, respecting generics and parens."""
    if not param_str.strip():
        return []
    params: list[str] = []
    current: list[str] = []
    depth_angle = depth_paren = depth_bracket = 0
    in_str = False
    str_ch = ""
    for ch in param_str:
        if in_str:
            current.append(ch)
            if ch == str_ch:
                in_str = False
            continue
        if ch in ('"', "'"):
            in_str = True
            str_ch = ch
            current.append(ch)
            continue
        if ch == "<":
            depth_angle += 1
        elif ch == ">":
            depth_angle = max(0, depth_angle - 1)
        elif ch == "(":
            depth_paren += 1
        elif ch == ")":
            depth_paren = max(0, depth_paren - 1)
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]":
            depth_bracket = max(0, depth_bracket - 1)
        elif ch == "," and depth_angle == depth_paren == depth_bracket == 0:
            params.append("".join(current).strip())
            current = []
            continue
        current.append(ch)
    if current:
        params.append("".join(current).strip())
    return [p for p in params if p]


def parse_method_signature(signature: str) -> tuple[str, list[str], str]:
    """
    Parse: 'public Result<UserVO> getUserById(@PathVariable Long id, ...)'
    Returns (method_name, param_strings, return_type).
    """
    signature = signature.strip()
    sig_match = re.search(
        r"(?:public|protected|private)\s+(?:static\s+)?(?:final\s+)?(.+?)\s+(\w+)\s*\((.*)\)\s*(?:throws\s+[\w.\s,]+)?$",
        signature,
        re.DOTALL,
    )
    if not sig_match:
        return "", [], ""
    return_type = normalize_type(sig_match.group(1))
    method_name = sig_match.group(2)
    params = split_parameters(sig_match.group(3))
    return method_name, params, return_type


def extract_http_method(mapping_name: str, args: dict[str, str]) -> str:
    mapping_methods = {
        "GetMapping": "GET",
        "PostMapping": "POST",
        "PutMapping": "PUT",
        "DeleteMapping": "DELETE",
        "PatchMapping": "PATCH",
    }
    if mapping_name in mapping_methods:
        return mapping_methods[mapping_name]
    if mapping_name == "RequestMapping":
        method_val = get_attr(args, "method")
        if method_val:
            method_val = method_val.replace("RequestMethod.", "").replace(" ", "")
            method_val = method_val.strip("{}")
            for m in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
                if m in method_val.upper():
                    return m
        return "ALL"
    return ""


def extract_mapping_path(args: dict[str, str]) -> str:
    for key in ("value", "path"):
        val = get_attr(args, key)
        if val:
            val = val.strip("{}")
            if val.startswith('"'):
                val = unquote(val.split(",")[0].strip())
            return val
    return ""


def parse_parameter(param: str) -> dict | None:
    """Parse a single method parameter declaration."""
    param = param.strip()
    if not param or param.startswith("final "):
        param = re.sub(r"^final\s+", "", param)

    annotations = extract_annotations(param)
    ann_map = {name: parse_annotation_args(args) for name, args in annotations}

    remainder = param
    for _name, _args in annotations:
        remainder = re.sub(r"@\w+(?:\([^()]*(?:\([^()]*\)[^()]*)*\))?", "", remainder, count=1)
    remainder = remainder.strip()

    type_name = ""
    param_name = ""
    parts = remainder.rsplit(" ", 1)
    if len(parts) == 2:
        type_name, param_name = normalize_type(parts[0]), parts[1]
    else:
        type_name = normalize_type(remainder)

    description = ""
    for key in ("ApiParam", "Parameter"):
        if key in ann_map:
            description = get_attr(ann_map[key], "value", "description", default="")

    if "PathVariable" in ann_map:
        args = ann_map["PathVariable"]
        name = get_attr(args, "value", "name", default=param_name)
        required = get_bool_attr(args, "required", True)
        return {
            "in": "path",
            "name": name or param_name,
            "type": type_name,
            "required": required if required is not None else True,
            "description": description,
        }

    if "RequestParam" in ann_map:
        args = ann_map["RequestParam"]
        name = get_attr(args, "value", "name", default=param_name)
        required = get_bool_attr(args, "required", True)
        default_value = get_attr(args, "defaultValue")
        return {
            "in": "query",
            "name": name or param_name,
            "type": type_name,
            "required": required if required is not None else True,
            "defaultValue": default_value,
            "description": description,
        }

    if "RequestHeader" in ann_map:
        args = ann_map["RequestHeader"]
        name = get_attr(args, "value", "name", default=param_name)
        required = get_bool_attr(args, "required", True)
        return {
            "in": "header",
            "name": name or param_name,
            "type": type_name,
            "required": required if required is not None else True,
            "description": description,
        }

    if "RequestBody" in ann_map:
        return {"in": "body", "name": param_name, "type": type_name, "description": description}

    return None


def parse_request_body(param_strings: list[str]) -> dict | None:
    for param in param_strings:
        parsed = parse_parameter(param)
        if parsed and parsed.get("in") == "body":
            return {"type": parsed["type"], "description": parsed.get("description", "")}
    return None


def parse_endpoint_parameters(param_strings: list[str]) -> list[dict]:
    params: list[dict] = []
    for param in param_strings:
        parsed = parse_parameter(param)
        if parsed and parsed.get("in") != "body":
            entry = {k: v for k, v in parsed.items() if k != "in" or True}
            entry["in"] = parsed["in"]
            if "defaultValue" in entry and not entry["defaultValue"]:
                del entry["defaultValue"]
            params.append(entry)
    return params


# ---------------------------------------------------------------------------
# Java file parsing
# ---------------------------------------------------------------------------

def read_java_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_package(source: str) -> str:
    match = re.search(r"^\s*package\s+([\w.]+)\s*;", source, re.MULTILINE)
    return match.group(1) if match else ""


def find_class_block(source: str) -> tuple[str, str, int, int] | None:
    """
    Find the main class/interface declaration and return
    (class_name, preamble_before_body, body_start, body_end).
    """
    pattern = re.compile(
        r"(^[\w\s@().,\n\"'=/-]*?)((?:public\s+)?(?:abstract\s+)?(?:class|interface)\s+(\w+)(?:<[^>]+>)?\s*(?:extends\s+[\w.<>,\s]+)?(?:implements\s+[\w.<>,\s]+)?\s*\{)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(source)
    if not match:
        return None

    preamble = match.group(1)
    class_name = match.group(3)
    body_start = match.end()

    depth = 1
    i = body_start
    in_str = False
    str_ch = ""
    while i < len(source) and depth > 0:
        ch = source[i]
        if in_str:
            if ch == "\\" and i + 1 < len(source):
                i += 2
                continue
            if ch == str_ch:
                in_str = False
            i += 1
            continue
        if ch in ('"', "'"):
            in_str = True
            str_ch = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1

    body_end = i - 1
    return class_name, preamble, body_start, body_end


def is_controller(preamble: str) -> bool:
    annotations = extract_annotations(preamble)
    names = {name for name, _ in annotations}
    return "RestController" in names or "Controller" in names


def extract_class_info(preamble: str, package: str, class_name: str) -> dict:
    annotations = extract_annotations(preamble)
    ann_map = {name: parse_annotation_args(args) for name, args in annotations}

    base_path = ""
    if "RequestMapping" in ann_map:
        base_path = extract_mapping_path(ann_map["RequestMapping"])

    group = ""
    group_desc = ""
    if "Api" in ann_map:
        group = get_attr(ann_map["Api"], "tags", "value", default="")
        group_desc = get_attr(ann_map["Api"], "description", default="")
        if group.startswith("{"):
            group = unquote(group.split(",")[0].strip())
    if "Tag" in ann_map:
        group = get_attr(ann_map["Tag"], "name", default=group) or group
        group_desc = get_attr(ann_map["Tag"], "description", default=group_desc)

    return {
        "className": class_name,
        "fullName": f"{package}.{class_name}" if package else class_name,
        "basePath": base_path,
        "group": group,
        "groupDesc": group_desc,
    }


def find_methods(class_body: str) -> list[tuple[str, str]]:
    """
    Return list of (annotation_block, method_signature) for public/protected methods.
    """
    methods: list[tuple[str, str]] = []
    pattern = re.compile(
        r"(public|protected)\s+(?:static\s+)?(?:final\s+)?(?:[\w<>,\?\[\]\s.@]+)\s+\w+\s*\(",
    )
    for match in pattern.finditer(class_body):
        start = match.start()
        paren_open = class_body.find("(", match.end() - 1)
        if paren_open == -1:
            continue
        paren_close = find_balanced_paren(class_body, paren_open)
        if paren_close == -1:
            continue

        after = class_body[paren_close + 1:].lstrip()
        if not after.startswith("{") and not after.startswith("throws"):
            continue
        if after.startswith("throws"):
            throws_end = after.find("{")
            if throws_end == -1:
                continue
            after = after[throws_end:]

        sig_end = paren_close + 1
        if "throws" in class_body[paren_close + 1:sig_end + 20]:
            throws_match = re.match(r"\s*(throws\s+[\w.\s,]+)?", class_body[paren_close + 1:])
            if throws_match:
                sig_end = paren_close + 1 + throws_match.end()

        signature = class_body[start:sig_end].strip()

        ann_start = start
        while ann_start > 0:
            prev = class_body.rfind("\n", 0, ann_start - 1)
            line = class_body[prev + 1:ann_start].strip()
            if line.startswith("@"):
                ann_start = prev + 1
                continue
            if not line or line.endswith("{") or line.endswith(";"):
                break
            break

        annotation_block = class_body[ann_start:start].strip()
        methods.append((annotation_block, signature))

    return methods


def parse_endpoint(annotation_block: str, signature: str, base_path: str) -> dict | None:
    method_name, param_strings, return_type = parse_method_signature(signature)
    if not method_name or method_name == class_name_sentinel:
        return None

    annotations = extract_annotations(annotation_block)
    if not annotations:
        return None

    http_method = ""
    method_path = ""
    summary = ""
    description = ""

    mapping_names = {
        "GetMapping", "PostMapping", "PutMapping", "DeleteMapping",
        "PatchMapping", "RequestMapping",
    }

    for name, args_str in annotations:
        args = parse_annotation_args(args_str)
        if name in mapping_names:
            http_method = extract_http_method(name, args) or http_method
            path = extract_mapping_path(args)
            if path:
                method_path = path
        elif name == "ApiOperation":
            summary = get_attr(args, "value", default=summary)
            description = get_attr(args, "notes", default=description)
        elif name == "Operation":
            summary = get_attr(args, "summary", default=summary)
            description = get_attr(args, "description", default=description)

    if not http_method:
        return None

    full_path = join_paths(base_path, method_path)

    return {
        "method": http_method,
        "path": full_path,
        "summary": summary,
        "description": description,
        "methodName": method_name,
        "parameters": parse_endpoint_parameters(param_strings),
        "requestBody": parse_request_body(param_strings),
        "returnType": return_type,
    }


class_name_sentinel = ""  # placeholder replaced during parsing


def scan_controller_file(
    file_path: Path,
    project_root: Path,
    package_filter: str | None,
) -> dict | None:
    source = strip_comments(read_java_file(file_path))
    package = extract_package(source)

    if package_filter and not package.startswith(package_filter):
        return None

    class_info = find_class_block(source)
    if not class_info:
        return None

    class_name, preamble, body_start, body_end = class_info
    if not is_controller(preamble):
        return None

    global class_name_sentinel
    class_name_sentinel = class_name

    info = extract_class_info(preamble, package, class_name)
    class_body = source[body_start:body_end]
    methods = find_methods(class_body)

    endpoints: list[dict] = []
    for ann_block, signature in methods:
        if " abstract " in f" {signature} ":
            continue
        endpoint = parse_endpoint(ann_block, signature, info["basePath"])
        if endpoint:
            endpoints.append(endpoint)

    try:
        rel_path = str(file_path.relative_to(project_root)).replace("\\", "/")
    except ValueError:
        rel_path = str(file_path).replace("\\", "/")

    info["filePath"] = rel_path
    info["endpoints"] = endpoints
    return info


# ---------------------------------------------------------------------------
# DTO / Model scanning
# ---------------------------------------------------------------------------

MODEL_NAME_PATTERN = re.compile(
    r"(Dto|DTO|Vo|VO|Request|Response)$",
)

VALIDATION_ANNOTATIONS = {
    "NotNull", "NotBlank", "NotEmpty", "Size", "Min", "Max", "Pattern",
    "DecimalMin", "DecimalMax",
}


def is_model_candidate(source: str, class_name: str) -> bool:
    preamble_match = re.search(
        r"^([\w\s@().,\n\"'=/-]*?)((?:public\s+)?(?:class|interface|enum)\s+" + re.escape(class_name) + r"\b)",
        source,
        re.MULTILINE | re.DOTALL,
    )
    if not preamble_match:
        return False
    preamble = preamble_match.group(1)
    if MODEL_NAME_PATTERN.search(class_name):
        return True
    annotations = extract_annotations(preamble)
    names = {name for name, _ in annotations}
    return "ApiModel" in names or "Schema" in names


def format_constraint(name: str, args: dict[str, str]) -> str:
    if not args:
        return f"@{name}"
    parts = []
    for key, val in args.items():
        parts.append(f"{key}={val}")
    return f"@{name}({', '.join(parts)})"


def parse_field(field_block: str) -> dict | None:
    field_block = field_block.strip()
    if not field_block or field_block.startswith("static ") or field_block.startswith("final static"):
        return None

    annotations = extract_annotations(field_block)
    ann_map = {name: parse_annotation_args(args) for name, args in annotations}

    remainder = field_block
    for _ in annotations:
        remainder = re.sub(r"@\w+(?:\([^()]*(?:\([^()]*\)[^()]*)*\))?", "", remainder, count=1)
    remainder = remainder.strip()

    match = re.match(
        r"(?:private|protected|public)\s+(?:static\s+)?(?:final\s+)?(.+?)\s+(\w+)\s*(?:=\s*[^;]+)?;",
        remainder,
    )
    if not match:
        return None

    type_name = normalize_type(match.group(1))
    field_name = match.group(2)

    description = ""
    example = ""
    required = False

    if "ApiModelProperty" in ann_map:
        args = ann_map["ApiModelProperty"]
        description = get_attr(args, "value", default="")
        example = get_attr(args, "example", default="")
        req = get_bool_attr(args, "required")
        if req is not None:
            required = req
    if "Schema" in ann_map:
        args = ann_map["Schema"]
        description = get_attr(args, "description", "title", default=description) or description
        example = get_attr(args, "example", default=example)
        req = get_bool_attr(args, "required")
        if req is not None:
            required = req

    constraints: list[str] = []
    for name, args in annotations:
        short = name.split(".")[-1]
        if short in VALIDATION_ANNOTATIONS:
            constraints.append(format_constraint(short, parse_annotation_args(args)))
            if short in ("NotNull", "NotBlank", "NotEmpty"):
                required = True

    return {
        "name": field_name,
        "type": type_name,
        "description": description,
        "example": example,
        "required": required,
        "constraints": constraints,
    }


def scan_model_file(
    file_path: Path,
    project_root: Path,
    package_filter: str | None,
) -> list[dict]:
    source = strip_comments(read_java_file(file_path))
    package = extract_package(source)

    if package_filter and not package.startswith(package_filter):
        return []

    models: list[dict] = []
    class_pattern = re.compile(
        r"(^[\w\s@().,\n\"'=/-]*?)((?:public\s+)?(?:class|interface|enum)\s+(\w+)(?:<[^>]+>)?\s*(?:extends\s+[\w.<>,\s]+)?(?:implements\s+[\w.<>,\s]+)?\s*\{)",
        re.MULTILINE | re.DOTALL,
    )

    for match in class_pattern.finditer(source):
        preamble = match.group(1)
        class_name = match.group(3)
        if not is_model_candidate(source[: match.end()], class_name):
            continue

        body_start = match.end()
        depth = 1
        i = body_start
        in_str = False
        str_ch = ""
        while i < len(source) and depth > 0:
            ch = source[i]
            if in_str:
                if ch == str_ch:
                    in_str = False
                i += 1
                continue
            if ch in ('"', "'"):
                in_str = True
                str_ch = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            i += 1
        class_body = source[body_start: i - 1]

        ann_map = {name: parse_annotation_args(args) for name, args in extract_annotations(preamble)}
        description = ""
        if "ApiModel" in ann_map:
            description = get_attr(ann_map["ApiModel"], "description", "value", default="")
        if "Schema" in ann_map:
            description = get_attr(ann_map["Schema"], "description", "title", default=description)

        fields: list[dict] = []
        for field_match in re.finditer(
            r"((?:@\w+(?:\([^()]*(?:\([^()]*\)[^()]*)*\))?\s*)*(?:private|protected|public)\s+(?:static\s+)?(?:final\s+)?[^;]+;)",
            class_body,
        ):
            field = parse_field(field_match.group(1))
            if field:
                fields.append(field)

        try:
            rel_path = str(file_path.relative_to(project_root)).replace("\\", "/")
        except ValueError:
            rel_path = str(file_path).replace("\\", "/")

        models.append({
            "className": class_name,
            "fullName": f"{package}.{class_name}" if package else class_name,
            "description": description,
            "filePath": rel_path,
            "fields": fields,
        })

    return models


# ---------------------------------------------------------------------------
# Project scanning
# ---------------------------------------------------------------------------

def find_java_files(root: Path) -> list[Path]:
    java_root = root / "src" / "main" / "java"
    if java_root.is_dir():
        return sorted(java_root.rglob("*.java"))
    return sorted(root.rglob("*.java"))


def find_controller_files(root: Path) -> list[Path]:
    return [p for p in find_java_files(root) if p.name.endswith("Controller.java")]


def find_model_files(root: Path) -> list[Path]:
    patterns = ("Dto", "DTO", "Vo", "VO", "Request", "Response")
    files: list[Path] = []
    for java_file in find_java_files(root):
        stem = java_file.stem
        if any(stem.endswith(suffix) for suffix in patterns):
            files.append(java_file)
    return sorted(set(files))


def scan_project(
    project_root: Path,
    include_dto: bool = False,
    package_filter: str | None = None,
) -> dict:
    project_name = project_root.name
    controllers: list[dict] = []
    models: list[dict] = []

    controller_files = find_controller_files(project_root)
    log(f"Found {len(controller_files)} Controller candidate file(s)")

    for idx, file_path in enumerate(controller_files, 1):
        log(f"[{idx}/{len(controller_files)}] Scanning {file_path.name}")
        try:
            controller = scan_controller_file(file_path, project_root, package_filter)
            if controller:
                controllers.append(controller)
        except Exception as exc:
            log(f"  Warning: failed to parse {file_path}: {exc}")

    if include_dto:
        model_files = find_model_files(project_root)
        log(f"Found {len(model_files)} model candidate file(s)")

        seen: set[str] = set()
        for idx, file_path in enumerate(model_files, 1):
            log(f"[{idx}/{len(model_files)}] Scanning model {file_path.name}")
            try:
                for model in scan_model_file(file_path, project_root, package_filter):
                    if model["fullName"] not in seen:
                        seen.add(model["fullName"])
                        models.append(model)
            except Exception as exc:
                log(f"  Warning: failed to parse {file_path}: {exc}")

        log("Scanning additional files with @ApiModel/@Schema annotations")
        for java_file in find_java_files(project_root):
            if java_file in model_files:
                continue
            try:
                source = strip_comments(read_java_file(java_file))
                if "@ApiModel" not in source and "@Schema" not in source:
                    continue
                for model in scan_model_file(java_file, project_root, package_filter):
                    if model["fullName"] not in seen:
                        seen.add(model["fullName"])
                        models.append(model)
            except Exception:
                pass

    endpoint_count = sum(len(c.get("endpoints", [])) for c in controllers)

    return {
        "project": project_name,
        "scanDate": date.today().isoformat(),
        "controllers": controllers,
        "models": models,
        "statistics": {
            "controllerCount": len(controllers),
            "endpointCount": endpoint_count,
            "modelCount": len(models),
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan Spring Boot Controllers and Swagger/Knife4j annotations, output JSON.",
    )
    parser.add_argument(
        "project_root",
        type=Path,
        help="Project root directory path",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output JSON file path (default: stdout)",
    )
    parser.add_argument(
        "--include-dto",
        action="store_true",
        help="Also scan DTO/VO/Request/Response model fields",
    )
    parser.add_argument(
        "--package-filter",
        type=str,
        default=None,
        help="Only scan classes under the specified Java package (e.g. com.example.controller)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    if not project_root.is_dir():
        log(f"Error: project root does not exist: {project_root}")
        return 1

    log(f"Scanning project: {project_root}")
    if args.package_filter:
        log(f"Package filter: {args.package_filter}")

    result = scan_project(
        project_root,
        include_dto=args.include_dto,
        package_filter=args.package_filter,
    )

    output_json = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_json + "\n", encoding="utf-8")
        log(f"Output written to {args.output}")
    else:
        sys.stdout.write(output_json + "\n")

    stats = result["statistics"]
    log(
        f"Done: {stats['controllerCount']} controller(s), "
        f"{stats['endpointCount']} endpoint(s), "
        f"{stats['modelCount']} model(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
