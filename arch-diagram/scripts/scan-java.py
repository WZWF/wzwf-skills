#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan Java/Spring Boot project source and emit architecture JSON.

Usage:
    python scan-java.py /path/to/project [--output arch-data.json] [--max-depth 3]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Maven POM namespace
POM_NS = {"m": "http://maven.apache.org/POM/4.0.0"}

# Framework / third-party package prefixes to exclude from dependency edges
FRAMEWORK_PREFIXES = (
    "java.",
    "javax.",
    "jakarta.",
    "org.springframework.",
    "org.apache.",
    "org.slf4j.",
    "org.junit.",
    "org.mockito.",
    "org.aspectj.",
    "org.hibernate.",
    "org.mybatis.",
    "com.fasterxml.",
    "com.google.",
    "lombok.",
    "io.swagger.",
    "io.lettuce.",
    "reactor.",
    "kotlin.",
    "scala.",
)

LAYER_ORDER = [
    "Controller",
    "Service",
    "Aspect",
    "Config",
    "Repository",
    "Infrastructure",
    "Entity",
    "Utils",
    "Annotation",
    "Other",
]

# --- regex patterns ---
RE_PACKAGE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
RE_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)\s*;", re.MULTILINE)
RE_CLASS_DECL = re.compile(
    r"(?:@\w+(?:\([^)]*\))?\s*)*"
    r"(?:public\s+|protected\s+|private\s+)?"
    r"(?:abstract\s+|static\s+|final\s+)?"
    r"(?:strictfp\s+)?"
    r"(class|interface|enum|@interface)\s+(\w+)"
    r"(?:<[^>]+>)?"
    r"(?:\s+extends\s+([\w.<>,\?\s]+))?"
    r"(?:\s+implements\s+([\w.<>,\?\s]+))?",
    re.MULTILINE | re.DOTALL,
)
RE_ANNOTATION = re.compile(r"@(\w+)(?:\([^)]*\))?")
RE_PUBLIC_METHOD = re.compile(
    r"^\s*public\s+(?!static\s+)(?!class\b|interface\b|enum\b|@interface\b)"
    r"([\w<>,\[\]\?\s]+)\s+(\w+)\s*\(([^)]*)\)",
    re.MULTILINE,
)
RE_FIELD_INJECT = re.compile(
    r"(?:@(?:Autowired|Resource|Inject)(?:\([^)]*\))?\s*)+"
    r"(?:private|protected|public)?\s*(?:final\s+)?([\w<>,\[\]\?\s]+)\s+(\w+)\s*;",
    re.MULTILINE,
)
RE_CTOR_FINAL = re.compile(
    r"(?:@(?:Autowired|Inject)(?:\([^)]*\))?\s*)?"
    r"(?:public|protected|private)\s+(\w+)\s*\(([^)]*)\)",
    re.MULTILINE,
)
RE_CTOR_PARAM = re.compile(
    r"(?:@\w+(?:\([^)]*\))?\s*)*(?:final\s+)?([\w<>,\[\]\?\s]+)\s+(\w+)"
)


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def strip_comments(source: str) -> str:
    """Remove block and line comments without breaking string literals."""
    result: List[str] = []
    i = 0
    n = len(source)
    in_str: Optional[str] = None
    while i < n:
        ch = source[i]
        if in_str:
            result.append(ch)
            if ch == "\\" and i + 1 < n:
                result.append(source[i + 1])
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ('"', "'"):
            in_str = ch
            result.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n:
            nxt = source[i + 1]
            if nxt == "/":
                i += 2
                while i < n and source[i] != "\n":
                    i += 1
                continue
            if nxt == "*":
                i += 2
                while i + 1 < n and not (source[i] == "*" and source[i + 1] == "/"):
                    i += 1
                i = min(i + 2, n)
                continue
        result.append(ch)
        i += 1
    return "".join(result)


def is_framework_type(fqn: str) -> bool:
    return any(fqn.startswith(p) for p in FRAMEWORK_PREFIXES)


def simple_name(type_ref: str) -> str:
    """Extract simple class name from a type reference."""
    ref = type_ref.strip()
    ref = ref.split("<", 1)[0].strip()
    ref = ref.split("[", 1)[0].strip()
    if "." in ref:
        return ref.rsplit(".", 1)[-1]
    return ref


def split_type_list(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    parts: List[str] = []
    depth = 0
    current: List[str] = []
    for ch in raw:
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return [simple_name(p) for p in parts if p.strip()]


def package_depth(java_root: Path, file_path: Path) -> int:
    try:
        rel = file_path.parent.relative_to(java_root)
    except ValueError:
        return 0
    if str(rel) == ".":
        return 0
    return len(rel.parts)


SKIP_DIRS = {"node_modules", ".git", "target", "build", ".gradle", ".idea", ".vscode", "__pycache__", "dist", ".next"}


def find_java_roots(project_root: Path, include_test: bool) -> List[Path]:
    roots: List[Path] = []
    patterns = ["src/main/java"]
    if include_test:
        patterns.append("src/test/java")
    for dirpath, dirnames, _ in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for pattern in patterns:
            candidate = Path(dirpath) / pattern
            if candidate.is_dir():
                roots.append(candidate.resolve())
    # dedupe while preserving order
    seen: Set[Path] = set()
    unique: List[Path] = []
    for r in roots:
        if r not in seen:
            seen.add(r)
            unique.append(r)
    return unique


def collect_java_files(
    project_root: Path, include_test: bool, max_depth: int
) -> List[Path]:
    files: List[Path] = []
    java_roots = find_java_roots(project_root, include_test)
    if not java_roots:
        log(f"警告: 未找到 src/main/java 目录于 {project_root}")
        return files

    for java_root in java_roots:
        is_test = "test" in java_root.parts
        if is_test and not include_test:
            continue
        log(f"扫描目录: {java_root}")
        for java_file in java_root.rglob("*.java"):
            depth = package_depth(java_root, java_file)
            if max_depth >= 0 and depth > max_depth:
                continue
            files.append(java_file)
    return sorted(set(files))


def classify_layer(
    class_name: str,
    kind: str,
    annotations: Set[str],
    source_text: str,
) -> str:
    if kind == "@interface" or "@interface" in source_text[:500]:
        return "Annotation"

    ann = {a.lower() for a in annotations}
    name = class_name

    if (
        "restcontroller" in ann
        or "controller" in ann
        or name.endswith("Controller")
    ):
        return "Controller"
    if "service" in ann or "Service" in name or name.endswith("ServiceImpl"):
        return "Service"
    if (
        "repository" in ann
        or name.endswith("Mapper")
        or name.endswith("Dao")
        or name.endswith("Repository")
    ):
        return "Repository"
    if (
        "configuration" in ann
        or "autoconfiguration" in ann
        or name.endswith("AutoConfiguration")
        or name.endswith("Config")
        or name.endswith("Configuration")
        or name.endswith("Properties")
    ):
        return "Config"
    if (
        "aspect" in ann
        or name.endswith("Aspect")
        or name.endswith("Interceptor")
    ):
        return "Aspect"
    for suffix in ("Entity", "DO", "DTO", "VO", "BO", "Param"):
        if suffix in name:
            return "Entity"
    for suffix in ("Util", "Utils", "Helper", "Constants"):
        if suffix in name:
            return "Utils"
    for suffix in ("Client", "Template", "Handler"):
        if name.endswith(suffix):
            return "Infrastructure"
    return "Other"


def extract_public_methods(source: str, limit: int = 10) -> List[str]:
    methods: List[str] = []
    seen: Set[str] = set()
    for match in RE_PUBLIC_METHOD.finditer(source):
        ret_type = re.sub(r"\s+", " ", match.group(1)).strip()
        method_name = match.group(2)
        params_raw = match.group(3).strip()
        if method_name == class_name_from_context(source, match.start()):
            continue  # skip constructors mis-matched as methods
        param_types = []
        if params_raw:
            depth = 0
            buf: List[str] = []
            for ch in params_raw + ",":
                if ch in "<([":
                    depth += 1
                elif ch in ">)]":
                    depth = max(0, depth - 1)
                if ch == "," and depth == 0:
                    token = "".join(buf).strip()
                    if token:
                        param_types.append(simplify_param(token))
                    buf = []
                else:
                    buf.append(ch)
        sig = f"{method_name}({', '.join(param_types)})"
        if sig not in seen:
            seen.add(sig)
            methods.append(sig)
        if len(methods) >= limit:
            break
    return methods


def class_name_from_context(source: str, pos: int) -> Optional[str]:
    prefix = source[:pos]
    matches = list(RE_CLASS_DECL.finditer(prefix))
    if not matches:
        return None
    return matches[-1].group(2)


def simplify_param(param: str) -> str:
    param = param.strip()
    param = re.sub(r"@\w+(?:\([^)]*\))?\s*", "", param)
    param = re.sub(r"\bfinal\s+", "", param)
    parts = param.rsplit(" ", 1)
    if len(parts) == 2:
        return simple_name(parts[0]) + " " + parts[1]
    return simple_name(param)


def parse_java_file(file_path: Path, project_root: Path) -> Optional[dict]:
    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        log(f"无法读取 {file_path}: {exc}")
        return None

    source = strip_comments(raw)
    pkg_match = RE_PACKAGE.search(source)
    package = pkg_match.group(1) if pkg_match else ""

    all_matches = list(RE_CLASS_DECL.finditer(source))
    if not all_matches:
        return None

    file_stem = file_path.stem
    class_match = all_matches[-1]
    for m in all_matches:
        if m.group(2) == file_stem:
            class_match = m
            break
    else:
        for m in all_matches:
            if m.group(1) == "class":
                class_match = m
                break

    kind = class_match.group(1)
    class_name = class_match.group(2)
    extends_raw = class_match.group(3)
    implements_raw = class_match.group(4)

    header_end = class_match.end()
    header_text = source[class_match.start() : header_end]
    annotations = set(RE_ANNOTATION.findall(header_text))
    # also scan lines immediately above declaration
    pre_decl = source[max(0, class_match.start() - 400) : class_match.start()]
    annotations.update(RE_ANNOTATION.findall(pre_decl))

    layer = classify_layer(class_name, kind, annotations, source)
    full_name = f"{package}.{class_name}" if package else class_name

    try:
        rel_path = str(file_path.resolve().relative_to(project_root.resolve())).replace("\\", "/")
    except ValueError:
        rel_path = str(file_path).replace("\\", "/")

    imports = [m.group(1) for m in RE_IMPORT.finditer(source)]
    project_imports = [
        imp for imp in imports if not is_framework_type(imp) and not imp.endswith(".*")
    ]

    extends_list = split_type_list(extends_raw)
    implements_list = split_type_list(implements_raw)

    # field injection
    injected: Set[str] = set()
    for fm in RE_FIELD_INJECT.finditer(source):
        injected.add(simple_name(fm.group(1)))

    # constructor injection (private final Xxx yyy in ctor params)
    for cm in RE_CTOR_FINAL.finditer(source):
        ctor_name = cm.group(1)
        if ctor_name != class_name:
            continue
        params = cm.group(2)
        for pm in RE_CTOR_PARAM.finditer(params):
            injected.add(simple_name(pm.group(1)))

    # also detect `private final Type field` pattern (common Spring style)
    for fm in re.finditer(
        r"private\s+final\s+([\w<>,\[\]\?\s]+)\s+(\w+)\s*;", source
    ):
        injected.add(simple_name(fm.group(1)))

    methods = extract_public_methods(source)

    ann_display = sorted({f"@{a}" for a in annotations})

    return {
        "name": class_name,
        "fullName": full_name,
        "layer": layer,
        "filePath": rel_path,
        "methods": methods,
        "annotations": ann_display,
        "dependencies": sorted(injected),
        "_imports": project_imports,
        "_implements": implements_list,
        "_extends": extends_list[0] if extends_list else None,
        "_kind": kind,
    }


def build_class_index(parsed_classes: List[dict]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Map simple name -> full name; full name -> simple name."""
    simple_to_full: Dict[str, str] = {}
    full_to_simple: Dict[str, str] = {}
    for cls in parsed_classes:
        simple = cls["name"]
        full = cls["fullName"]
        full_to_simple[full] = simple
        if simple not in simple_to_full:
            simple_to_full[simple] = full
    return simple_to_full, full_to_simple


def resolve_to_project_class(name: str, simple_to_full: Dict[str, str]) -> Optional[str]:
    if name in simple_to_full:
        return simple_to_full[name]
    return None


def resolve_import(fqn: str, simple_to_full: Dict[str, str]) -> Optional[str]:
    if fqn in simple_to_full.values():
        return fqn.rsplit(".", 1)[-1]
    simple = fqn.rsplit(".", 1)[-1]
    if simple in simple_to_full:
        return simple
    return None


def build_edges(classes: List[dict], simple_to_full: Dict[str, str]) -> List[dict]:
    edges: List[dict] = []
    seen: Set[Tuple[str, str, str]] = set()

    def add_edge(src: str, dst: str, edge_type: str) -> None:
        if not dst or src == dst:
            return
        key = (src, dst, edge_type)
        if key in seen:
            return
        seen.add(key)
        edges.append({"from": src, "to": dst, "type": edge_type})

    for cls in classes:
        src = cls["name"]
        for dep in cls.get("dependencies", []):
            resolved = resolve_to_project_class(dep, simple_to_full)
            if resolved:
                add_edge(src, resolved.rsplit(".", 1)[-1], "injection")
        for imp in cls.get("_imports", []):
            resolved = resolve_import(imp, simple_to_full)
            if resolved:
                add_edge(src, resolved, "import")
        for impl in cls.get("_implements", []):
            resolved = resolve_to_project_class(impl, simple_to_full)
            if resolved:
                add_edge(src, resolved.rsplit(".", 1)[-1], "implements")
        ext = cls.get("_extends")
        if ext:
            resolved = resolve_to_project_class(ext, simple_to_full)
            if resolved:
                add_edge(src, resolved.rsplit(".", 1)[-1], "extends")

    return edges


def clean_class_output(cls: dict) -> dict:
    deps: Set[str] = set(cls.get("dependencies", []))
    for imp in cls.get("_imports", []):
        simple = imp.rsplit(".", 1)[-1]
        deps.add(simple)
    for impl in cls.get("_implements", []):
        deps.add(impl)
    ext = cls.get("_extends")
    if ext:
        deps.add(ext)
    deps.discard(cls["name"])

    return {
        "name": cls["name"],
        "fullName": cls["fullName"],
        "layer": cls["layer"],
        "filePath": cls["filePath"],
        "methods": cls["methods"],
        "annotations": cls["annotations"],
        "dependencies": sorted(deps),
        "implements": cls.get("_implements", []),
        "extends": cls.get("_extends"),
    }


def parse_pom_modules(project_root: Path) -> Tuple[str, List[dict]]:
    pom_path = project_root / "pom.xml"
    if not pom_path.is_file():
        return project_root.name, []

    artifact_id = project_root.name
    modules: List[dict] = []

    try:
        tree = ET.parse(pom_path)
        root = tree.getroot()
    except ET.ParseError as exc:
        log(f"警告: 无法解析 pom.xml: {exc}")
        return artifact_id, modules

    # handle default namespace
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    def find_text(parent, tag: str) -> Optional[str]:
        el = parent.find(f"{ns}{tag}")
        return el.text.strip() if el is not None and el.text else None

    art_el = root.find(f"{ns}artifactId")
    if art_el is not None and art_el.text:
        artifact_id = art_el.text.strip()

    deps: List[str] = []
    for dep in root.findall(f".//{ns}dependencies/{ns}dependency"):
        dep_art = find_text(dep, "artifactId")
        if dep_art:
            deps.append(dep_art)

    modules.append({"artifactId": artifact_id, "dependencies": deps})

    modules_el = root.find(f"{ns}modules")
    if modules_el is not None:
        for mod in modules_el.findall(f"{ns}module"):
            if mod.text:
                sub_path = project_root / mod.text.strip()
                if sub_path.is_dir():
                    sub_art, sub_modules = parse_pom_modules(sub_path)
                    modules.extend(sub_modules)

    return artifact_id, modules


def scan_project(
    project_root: Path,
    max_depth: int,
    include_test: bool,
) -> dict:
    project_root = project_root.resolve()
    if not project_root.is_dir():
        raise FileNotFoundError(f"项目目录不存在: {project_root}")

    log(f"开始扫描项目: {project_root}")
    artifact_id, modules = parse_pom_modules(project_root)

    java_files = collect_java_files(project_root, include_test, max_depth)
    log(f"找到 {len(java_files)} 个 Java 文件 (max-depth={max_depth})")

    parsed: List[dict] = []
    for idx, java_file in enumerate(java_files, 1):
        log(f"  [{idx}/{len(java_files)}] {java_file.name}")
        info = parse_java_file(java_file, project_root)
        if info:
            parsed.append(info)

    simple_to_full, _ = build_class_index(parsed)
    edges = build_edges(parsed, simple_to_full)
    classes = [clean_class_output(c) for c in parsed]

    layers: Dict[str, List[str]] = {layer: [] for layer in LAYER_ORDER}
    for cls in classes:
        layer = cls["layer"]
        if layer not in layers:
            layers[layer] = []
        layers[layer].append(cls["name"])

    for layer in layers:
        layers[layer] = sorted(set(layers[layer]))

    result = {
        "project": artifact_id,
        "scanDate": date.today().isoformat(),
        "totalClasses": len(classes),
        "layers": layers,
        "classes": sorted(classes, key=lambda c: c["fullName"]),
        "edges": edges,
        "modules": modules if modules else [{"artifactId": artifact_id, "dependencies": []}],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="扫描 Java/Spring Boot 项目并输出架构 JSON"
    )
    parser.add_argument("project", type=Path, help="项目根目录路径")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="输出 JSON 文件路径（默认 stdout）",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="包路径最大深度，相对 src/*/java 根目录（默认 3，设为 -1 表示不限制）",
    )
    parser.add_argument(
        "--include-test",
        action="store_true",
        help="包含测试代码（默认不包含）",
    )
    args = parser.parse_args()

    try:
        result = scan_project(args.project, args.max_depth, args.include_test)
    except FileNotFoundError as exc:
        log(str(exc))
        return 1

    output_json = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_json + "\n", encoding="utf-8")
        log(f"已写入: {args.output}")
    else:
        print(output_json)

    log(f"扫描完成: {result['totalClasses']} 个类, {len(result['edges'])} 条依赖边")
    return 0


if __name__ == "__main__":
    sys.exit(main())
