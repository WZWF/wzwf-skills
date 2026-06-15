#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Impact Scanner — 变更影响分析地图生成器

扫描 Java/Spring Boot 项目，以指定的类或方法为中心，
构建调用图、Spring 隐式依赖、配置关联等影响地图。

Usage:
    python impact-scanner.py /path/to/project --target "LockUtils"
    python impact-scanner.py /path/to/project --target "LockUtils.tryLock" --depth 3
    python impact-scanner.py /path/to/project --target "LockUtils" -o impact-map.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

SKIP_DIRS = {
    "node_modules", ".git", "target", "build", ".gradle",
    ".idea", ".vscode", "__pycache__", "dist", ".next", "docs",
}

FRAMEWORK_PREFIXES = (
    "java.", "javax.", "jakarta.", "org.springframework.",
    "org.apache.", "org.slf4j.", "org.junit.", "org.mockito.",
    "org.aspectj.", "org.hibernate.", "org.mybatis.",
    "com.fasterxml.", "com.google.", "lombok.",
    "io.swagger.", "io.lettuce.", "reactor.",
)

RE_PACKAGE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
RE_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)\s*;", re.MULTILINE)

RE_CLASS_DECL = re.compile(
    r"(?:@\w+(?:\([^)]*\))?\s*)*"
    r"(?:public\s+|protected\s+|private\s+)?"
    r"(?:abstract\s+|static\s+|final\s+)*"
    r"(class|interface|enum|@interface)\s+(\w+)",
    re.MULTILINE | re.DOTALL,
)

RE_METHOD_DECL = re.compile(
    r"(?:@(\w+)(?:\(([^)]*)\))?\s*)*"
    r"(?:public|protected|private)\s+"
    r"(?:static\s+|final\s+|synchronized\s+|abstract\s+)*"
    r"([\w<>,\[\]\?\s]+)\s+(\w+)\s*\(([^)]*)\)",
    re.MULTILINE,
)

RE_FIELD_INJECT = re.compile(
    r"(?:@(?:Autowired|Resource|Inject|Value)(?:\([^)]*\))?\s*)+"
    r"(?:private|protected|public)?\s*(?:final\s+)?([\w<>,\[\]\?\s]+)\s+(\w+)\s*;",
    re.MULTILINE,
)

RE_PRIVATE_FINAL_FIELD = re.compile(
    r"private\s+final\s+([\w<>,\[\]\?\s]+)\s+(\w+)\s*;",
    re.MULTILINE,
)

RE_METHOD_CALL = re.compile(
    r"(\w+)\s*\.\s*(\w+)\s*\(",
)

RE_STATIC_OR_SELF_CALL = re.compile(
    r"(?<!\w)(\w+)\s*\(",
)

RE_ANNOTATION_LINE = re.compile(r"@(\w+)(?:\(([^)]*)\))?")

RE_POINTCUT_EXECUTION = re.compile(
    r"""execution\s*\(\s*
        (?:[\w.*<>,\[\]\s?]+\s+)?
        ([\w.*]+)\.(\w+|\*)\s*\(""",
    re.VERBOSE,
)
RE_POINTCUT_ANNOTATION = re.compile(
    r"@annotation\s*\(\s*([\w.]+)\s*\)",
)
RE_POINTCUT_WITHIN = re.compile(
    r"within\s*\(\s*([\w.*]+)\s*\)",
)

RE_VALUE_KEY = re.compile(r"\$\{([^}:]+)")
RE_CONDITIONAL_KEY = re.compile(
    r'@ConditionalOn\w+\s*\(\s*(?:name\s*=\s*)?["\']([^"\']+)',
)

RE_EVENT_LISTENER = re.compile(
    r"@EventListener(?:\(([^)]*)\))?",
)

RE_SCHEDULED = re.compile(
    r"@Scheduled\s*\(([^)]*)\)",
)


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def strip_comments(source: str) -> str:
    result: list[str] = []
    i, n = 0, len(source)
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


def simple_name(type_ref: str) -> str:
    ref = type_ref.strip()
    ref = ref.split("<", 1)[0].strip()
    ref = ref.split("[", 1)[0].strip()
    if "." in ref:
        return ref.rsplit(".", 1)[-1]
    return ref


def find_method_body(source: str, method_start: int) -> Tuple[int, int]:
    """从方法声明位置找到方法体的起止位置（花括号匹配）"""
    brace_start = source.find("{", method_start)
    if brace_start == -1:
        return method_start, method_start

    depth = 0
    i = brace_start
    while i < len(source):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return brace_start, i
        i += 1
    return brace_start, len(source) - 1


def line_number_at(source: str, pos: int) -> int:
    return source[:pos].count("\n") + 1


# ─── Data Classes ──────────────────────────────────────────

@dataclass
class MethodInfo:
    name: str
    class_name: str
    return_type: str
    params: str
    annotations: List[str]
    annotation_args: Dict[str, str]
    line_start: int
    line_end: int
    body: str = ""
    is_target: bool = False

    @property
    def signature(self) -> str:
        return f"{self.class_name}.{self.name}({self.params})"

    @property
    def short_sig(self) -> str:
        param_types = []
        if self.params.strip():
            for p in self.params.split(","):
                parts = p.strip().rsplit(" ", 1)
                param_types.append(simple_name(parts[0]) if parts else "?")
        return f"{self.name}({', '.join(param_types)})"


@dataclass
class ClassInfo:
    name: str
    package: str
    full_name: str
    file_path: str
    kind: str
    annotations: List[str]
    methods: List[MethodInfo] = field(default_factory=list)
    injected_fields: Dict[str, str] = field(default_factory=dict)
    imports: List[str] = field(default_factory=list)
    implements: List[str] = field(default_factory=list)
    extends: Optional[str] = None


@dataclass
class CallEdge:
    from_class: str
    from_method: str
    to_class: str
    to_method: str
    depth: int
    edge_type: str = "call"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SpringDep:
    dep_type: str
    source_class: str
    source_method: str
    detail: str
    file_path: str
    line: int

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Parsing ───────────────────────────────────────────────

def find_java_roots(project_root: Path) -> List[Path]:
    roots: List[Path] = []
    for dirpath, dirnames, _ in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for pattern in ["src/main/java", "src/test/java"]:
            candidate = Path(dirpath) / pattern
            if candidate.is_dir():
                roots.append(candidate.resolve())
    seen: Set[Path] = set()
    unique: List[Path] = []
    for r in roots:
        if r not in seen:
            seen.add(r)
            unique.append(r)
    return unique


def collect_java_files(project_root: Path) -> List[Path]:
    files: List[Path] = []
    for java_root in find_java_roots(project_root):
        for java_file in java_root.rglob("*.java"):
            files.append(java_file)
    return sorted(set(files))


def extract_annotations_before(source: str, pos: int, max_lookback: int = 500) -> Tuple[List[str], Dict[str, str]]:
    """提取位置之前的注解"""
    start = max(0, pos - max_lookback)
    prefix = source[start:pos]
    last_code = max(prefix.rfind(";"), prefix.rfind("}"), prefix.rfind("{"))
    if last_code >= 0:
        prefix = prefix[last_code + 1:]

    annotations = []
    annotation_args = {}
    for m in RE_ANNOTATION_LINE.finditer(prefix):
        ann_name = m.group(1)
        ann_arg = m.group(2) or ""
        annotations.append(ann_name)
        if ann_arg:
            annotation_args[ann_name] = ann_arg.strip()
    return annotations, annotation_args


def parse_class(file_path: Path, project_root: Path) -> Optional[ClassInfo]:
    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError:
        return None

    source = strip_comments(raw)
    pkg_match = RE_PACKAGE.search(source)
    package = pkg_match.group(1) if pkg_match else ""

    all_class_matches = list(RE_CLASS_DECL.finditer(source))
    if not all_class_matches:
        return None

    file_stem = file_path.stem
    class_match = all_class_matches[-1]
    for m in all_class_matches:
        if m.group(2) == file_stem:
            class_match = m
            break
    else:
        for m in all_class_matches:
            if m.group(1) == "class":
                class_match = m
                break

    kind = class_match.group(1)
    class_name = class_match.group(2)
    full_name = f"{package}.{class_name}" if package else class_name

    try:
        rel_path = str(file_path.resolve().relative_to(project_root.resolve())).replace("\\", "/")
    except ValueError:
        rel_path = str(file_path).replace("\\", "/")

    class_ann, class_ann_args = extract_annotations_before(source, class_match.start())
    decl_region = source[class_match.start():class_match.end()]
    for ann_m in RE_ANNOTATION_LINE.finditer(decl_region):
        ann_name = ann_m.group(1)
        if ann_name not in class_ann:
            class_ann.append(ann_name)
            if ann_m.group(2):
                class_ann_args[ann_name] = ann_m.group(2).strip()

    imports = [m.group(1) for m in RE_IMPORT.finditer(source)]

    injected: Dict[str, str] = {}
    for fm in RE_FIELD_INJECT.finditer(source):
        field_type = simple_name(fm.group(1))
        field_name = fm.group(2)
        injected[field_name] = field_type
    for fm in RE_PRIVATE_FINAL_FIELD.finditer(source):
        field_type = simple_name(fm.group(1))
        field_name = fm.group(2)
        if field_type[0].isupper() and field_type not in (
            "String", "Long", "Integer", "Boolean", "Double", "Float",
            "List", "Map", "Set", "Logger",
        ):
            injected[field_name] = field_type

    methods: List[MethodInfo] = []
    for mm in RE_METHOD_DECL.finditer(source):
        method_name = mm.group(4)
        if method_name == class_name:
            continue
        ret_type = re.sub(r"\s+", " ", mm.group(3)).strip()
        params = mm.group(5).strip()

        m_anns, m_ann_args = extract_annotations_before(source, mm.start())

        body_start, body_end = find_method_body(source, mm.end())
        body = source[body_start:body_end + 1] if body_start != body_end else ""

        methods.append(MethodInfo(
            name=method_name,
            class_name=class_name,
            return_type=ret_type,
            params=params,
            annotations=m_anns,
            annotation_args=m_ann_args,
            line_start=line_number_at(raw, mm.start()),
            line_end=line_number_at(raw, body_end) if body_end > mm.end() else line_number_at(raw, mm.end()),
            body=body,
        ))

    impl_list: List[str] = []
    ext_name: Optional[str] = None
    impl_m = re.search(r"implements\s+([\w.<>,\s]+?)(?:\s*\{)", source[class_match.start():])
    if impl_m:
        for t in impl_m.group(1).split(","):
            impl_list.append(simple_name(t))
    ext_m = re.search(r"extends\s+([\w.<>,\s]+?)(?:\s+implements|\s*\{)", source[class_match.start():])
    if ext_m:
        ext_name = simple_name(ext_m.group(1))

    return ClassInfo(
        name=class_name,
        package=package,
        full_name=full_name,
        file_path=rel_path,
        kind=kind,
        annotations=class_ann,
        methods=methods,
        injected_fields=injected,
        imports=imports,
        implements=impl_list,
        extends=ext_name,
    )


# ─── Call Graph ────────────────────────────────────────────

def resolve_callee_class(
    var_or_class: str,
    caller: ClassInfo,
    class_index: Dict[str, ClassInfo],
) -> Optional[str]:
    """解析方法调用的目标类名"""
    if var_or_class in class_index:
        return var_or_class
    if var_or_class in caller.injected_fields:
        type_name = caller.injected_fields[var_or_class]
        if type_name in class_index:
            return type_name
    for imp in caller.imports:
        if imp.endswith(f".{var_or_class}"):
            sn = simple_name(imp)
            if sn in class_index:
                return sn
    return None


def extract_calls_from_body(
    method: MethodInfo,
    owner: ClassInfo,
    class_index: Dict[str, ClassInfo],
) -> List[Tuple[str, str]]:
    """从方法体中提取调用的（类名, 方法名）列表"""
    calls: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    body = method.body
    if not body:
        return calls

    for m in RE_METHOD_CALL.finditer(body):
        var_or_class = m.group(1)
        called_method = m.group(2)

        if var_or_class in ("if", "for", "while", "switch", "return", "new", "this", "super", "log", "logger"):
            if var_or_class in ("this", "super"):
                target = owner.name
            else:
                continue
        else:
            target = resolve_callee_class(var_or_class, owner, class_index)

        if target and (target, called_method) not in seen:
            seen.add((target, called_method))
            calls.append((target, called_method))

    for m in RE_STATIC_OR_SELF_CALL.finditer(body):
        func_name = m.group(1)
        if func_name[0].islower() and func_name not in (
            "if", "for", "while", "switch", "return", "new", "try", "catch",
            "throw", "break", "continue", "synchronized",
        ):
            own_methods = {mt.name for mt in owner.methods}
            if func_name in own_methods and (owner.name, func_name) not in seen:
                seen.add((owner.name, func_name))
                calls.append((owner.name, func_name))

    return calls


def build_call_graph(
    target_class: str,
    target_method: Optional[str],
    class_index: Dict[str, ClassInfo],
    max_depth: int,
) -> Tuple[List[CallEdge], List[CallEdge], List[dict]]:
    """
    构建双向调用图。
    返回 (callers, callees, cycles)
    """
    callers: List[CallEdge] = []
    callees: List[CallEdge] = []
    cycles: List[dict] = []

    target_cls = class_index.get(target_class)
    if not target_cls:
        return callers, callees, cycles

    target_methods: Set[str] = set()
    if target_method:
        target_methods.add(target_method)
    else:
        target_methods = {m.name for m in target_cls.methods}

    # --- Callees: 目标方法调用了谁 ---
    callee_visited: Set[Tuple[str, str]] = set()
    callee_queue: deque[Tuple[str, str, int, List[str]]] = deque()

    for m in target_cls.methods:
        if m.name in target_methods:
            callee_queue.append((target_class, m.name, 0, [f"{target_class}.{m.name}"]))

    while callee_queue:
        cls_name, mth_name, depth, path = callee_queue.popleft()
        if depth > max_depth:
            continue
        if (cls_name, mth_name) in callee_visited:
            continue
        callee_visited.add((cls_name, mth_name))

        cls_info = class_index.get(cls_name)
        if not cls_info:
            continue

        for mth in cls_info.methods:
            if mth.name != mth_name:
                continue
            for called_cls, called_mth in extract_calls_from_body(mth, cls_info, class_index):
                if called_cls == cls_name and called_mth == mth_name:
                    continue

                node_key = f"{called_cls}.{called_mth}"
                new_path = path + [node_key]

                if (called_cls, called_mth) in callee_visited:
                    if node_key in path:
                        cycles.append({
                            "path": new_path,
                            "type": "callee_cycle",
                        })
                    continue

                if depth == 0 or cls_name != target_class:
                    callees.append(CallEdge(
                        from_class=cls_name,
                        from_method=mth_name,
                        to_class=called_cls,
                        to_method=called_mth,
                        depth=depth + 1,
                    ))

                if depth + 1 < max_depth:
                    callee_queue.append((called_cls, called_mth, depth + 1, new_path))

    # --- Callers: 谁调用了目标方法 ---
    caller_visited: Set[Tuple[str, str]] = set()
    caller_queue: deque[Tuple[str, str, int, List[str]]] = deque()

    for cls_name, cls_info in class_index.items():
        if cls_name == target_class:
            continue
        for mth in cls_info.methods:
            calls = extract_calls_from_body(mth, cls_info, class_index)
            for called_cls, called_mth in calls:
                if called_cls == target_class and called_mth in target_methods:
                    edge = CallEdge(
                        from_class=cls_name,
                        from_method=mth.name,
                        to_class=target_class,
                        to_method=called_mth,
                        depth=1,
                    )
                    callers.append(edge)
                    caller_queue.append((cls_name, mth.name, 1, [f"{cls_name}.{mth.name}"]))

    while caller_queue:
        cls_name, mth_name, depth, path = caller_queue.popleft()
        if depth >= max_depth:
            continue
        if (cls_name, mth_name) in caller_visited:
            continue
        caller_visited.add((cls_name, mth_name))

        for other_cls_name, other_cls_info in class_index.items():
            if other_cls_name == cls_name and other_cls_name == target_class:
                continue
            for other_mth in other_cls_info.methods:
                calls = extract_calls_from_body(other_mth, other_cls_info, class_index)
                for called_cls, called_mth in calls:
                    if called_cls == cls_name and called_mth == mth_name:
                        node_key = f"{other_cls_name}.{other_mth.name}"
                        new_path = path + [node_key]

                        if node_key in path:
                            cycles.append({
                                "path": new_path,
                                "type": "caller_cycle",
                            })
                            continue

                        callers.append(CallEdge(
                            from_class=other_cls_name,
                            from_method=other_mth.name,
                            to_class=cls_name,
                            to_method=mth_name,
                            depth=depth + 1,
                        ))

                        if depth + 1 < max_depth:
                            caller_queue.append((other_cls_name, other_mth.name, depth + 1, new_path))

    return callers, callees, cycles


# ─── Spring 隐式依赖扫描 ──────────────────────────────────

def scan_aop_matches(
    target_class: ClassInfo,
    target_method: Optional[str],
    all_classes: List[ClassInfo],
) -> List[SpringDep]:
    """扫描 AOP 切面是否拦截了目标方法"""
    results: List[SpringDep] = []
    target_ann_set = set()
    for m in target_class.methods:
        if target_method and m.name != target_method:
            continue
        target_ann_set.update(m.annotations)

    for cls in all_classes:
        if "Aspect" not in cls.annotations:
            continue
        for method in cls.methods:
            around_or_before = [a for a in method.annotations if a in ("Around", "Before", "After", "AfterReturning", "AfterThrowing")]
            if not around_or_before:
                continue

            for advice_type in around_or_before:
                pointcut_expr = method.annotation_args.get(advice_type, "")
                matched = False
                match_reason = ""

                for em in RE_POINTCUT_EXECUTION.finditer(pointcut_expr):
                    pkg_pattern = em.group(1)
                    mth_pattern = em.group(2)
                    pkg_parts = target_class.full_name.replace(".", "\\.")
                    if "*" in pkg_pattern:
                        regex_pattern = pkg_pattern.replace(".", "\\.").replace("*", ".*")
                        if re.match(regex_pattern, target_class.full_name):
                            matched = True
                            match_reason = f"execution匹配: {pkg_pattern}"

                for am in RE_POINTCUT_ANNOTATION.finditer(pointcut_expr):
                    ann_fqn = am.group(1)
                    ann_simple = simple_name(ann_fqn)
                    if ann_simple in target_ann_set:
                        matched = True
                        match_reason = f"@annotation匹配: {ann_simple}"

                for wm in RE_POINTCUT_WITHIN.finditer(pointcut_expr):
                    within_pattern = wm.group(1)
                    regex_pattern = within_pattern.replace(".", "\\.").replace("*", ".*")
                    if re.match(regex_pattern, target_class.full_name):
                        matched = True
                        match_reason = f"within匹配: {within_pattern}"

                if not matched and target_class.annotations:
                    for ann in target_class.annotations:
                        if ann.lower() in pointcut_expr.lower():
                            matched = True
                            match_reason = f"注解名出现在pointcut中: @{ann}"

                if not matched:
                    target_names = [target_class.name, target_class.full_name]
                    if target_method:
                        target_names.append(target_method)
                    for tn in target_names:
                        if tn in pointcut_expr:
                            matched = True
                            match_reason = f"名称出现在pointcut中: {tn}"
                            break

                if matched:
                    results.append(SpringDep(
                        dep_type="aop",
                        source_class=cls.name,
                        source_method=method.name,
                        detail=f"@{advice_type} - {match_reason}",
                        file_path=cls.file_path,
                        line=method.line_start,
                    ))

    return results


def scan_event_listeners(
    target_class: ClassInfo,
    all_classes: List[ClassInfo],
) -> List[SpringDep]:
    """扫描事件监听器"""
    results: List[SpringDep] = []
    published_events: Set[str] = set()
    for m in target_class.methods:
        for call_m in RE_METHOD_CALL.finditer(m.body):
            if call_m.group(2) in ("publishEvent", "publish", "multicastEvent"):
                published_events.add(call_m.group(1))

    if not published_events:
        return results

    for cls in all_classes:
        for method in cls.methods:
            if "EventListener" in method.annotations:
                results.append(SpringDep(
                    dep_type="event_listener",
                    source_class=cls.name,
                    source_method=method.name,
                    detail=f"@EventListener (目标类发布了事件)",
                    file_path=cls.file_path,
                    line=method.line_start,
                ))

    return results


def scan_scheduled_tasks(
    target_class: ClassInfo,
    target_method: Optional[str],
    all_classes: List[ClassInfo],
    class_index: Dict[str, ClassInfo],
) -> List[SpringDep]:
    """扫描定时任务是否使用了目标代码"""
    results: List[SpringDep] = []
    target_methods = {target_method} if target_method else {m.name for m in target_class.methods}

    for cls in all_classes:
        for method in cls.methods:
            if "Scheduled" not in method.annotations:
                continue
            calls = extract_calls_from_body(method, cls, class_index)
            for called_cls, called_mth in calls:
                if called_cls == target_class.name and called_mth in target_methods:
                    schedule_config = method.annotation_args.get("Scheduled", "")
                    results.append(SpringDep(
                        dep_type="scheduled",
                        source_class=cls.name,
                        source_method=method.name,
                        detail=f"@Scheduled({schedule_config}) 调用了 {target_class.name}.{called_mth}",
                        file_path=cls.file_path,
                        line=method.line_start,
                    ))

    return results


def scan_config_deps(
    target_class: ClassInfo,
    all_classes: List[ClassInfo],
    project_root: Path,
) -> List[SpringDep]:
    """扫描配置依赖：@Value, @ConditionalOn*"""
    results: List[SpringDep] = []
    config_keys: Set[str] = set()

    for m in target_class.methods:
        for ann_name, ann_arg in m.annotation_args.items():
            for km in RE_VALUE_KEY.finditer(ann_arg):
                config_keys.add(km.group(1))

    for cls_ann_name in target_class.annotations:
        if cls_ann_name.startswith("ConditionalOn"):
            for cls in all_classes:
                for ann in cls.annotations:
                    if ann == cls_ann_name:
                        pass

    source_text = ""
    for fp in target_class.file_path, :
        abs_path = project_root / fp
        if abs_path.is_file():
            try:
                source_text = abs_path.read_text(encoding="utf-8")
            except OSError:
                pass

    for km in RE_VALUE_KEY.finditer(source_text):
        config_keys.add(km.group(1))

    for km in RE_CONDITIONAL_KEY.finditer(source_text):
        config_keys.add(km.group(1))

    if config_keys:
        yml_files = list(project_root.rglob("*.yml")) + list(project_root.rglob("*.yaml")) + list(project_root.rglob("*.properties"))
        yml_files = [f for f in yml_files if "target" not in str(f) and "node_modules" not in str(f)]

        for key in config_keys:
            for yml_file in yml_files:
                try:
                    content = yml_file.read_text(encoding="utf-8")
                except OSError:
                    continue
                key_variants = [key, key.replace(".", ":"), key.split(".")[-1]]
                for kv in key_variants:
                    if kv in content:
                        try:
                            rel = str(yml_file.relative_to(project_root)).replace("\\", "/")
                        except ValueError:
                            rel = str(yml_file)
                        results.append(SpringDep(
                            dep_type="config",
                            source_class="[config]",
                            source_method="",
                            detail=f"配置键 '{key}' 出现在 {rel}",
                            file_path=rel,
                            line=0,
                        ))
                        break

    return results


def scan_transaction_boundaries(
    target_class: ClassInfo,
    target_method: Optional[str],
    class_index: Dict[str, ClassInfo],
) -> List[SpringDep]:
    """检查事务边界"""
    results: List[SpringDep] = []
    target_methods = target_class.methods
    if target_method:
        target_methods = [m for m in target_methods if m.name == target_method]

    for m in target_methods:
        if "Transactional" in m.annotations:
            propagation = ""
            args = m.annotation_args.get("Transactional", "")
            prop_m = re.search(r"propagation\s*=\s*([\w.]+)", args)
            if prop_m:
                propagation = prop_m.group(1)
            results.append(SpringDep(
                dep_type="transaction",
                source_class=target_class.name,
                source_method=m.name,
                detail=f"@Transactional{f'(propagation={propagation})' if propagation else ''}",
                file_path=target_class.file_path,
                line=m.line_start,
            ))

    if "Transactional" in target_class.annotations:
        results.append(SpringDep(
            dep_type="transaction",
            source_class=target_class.name,
            source_method="[class-level]",
            detail="类级别 @Transactional",
            file_path=target_class.file_path,
            line=0,
        ))

    return results


def scan_cache_ops(
    target_class: ClassInfo,
    target_method: Optional[str],
) -> List[SpringDep]:
    """检查缓存操作"""
    results: List[SpringDep] = []
    cache_annotations = {"Cacheable", "CacheEvict", "CachePut", "Caching"}

    for m in target_class.methods:
        if target_method and m.name != target_method:
            continue
        for ann in m.annotations:
            if ann in cache_annotations:
                results.append(SpringDep(
                    dep_type="cache",
                    source_class=target_class.name,
                    source_method=m.name,
                    detail=f"@{ann}({m.annotation_args.get(ann, '')})",
                    file_path=target_class.file_path,
                    line=m.line_start,
                ))

    return results


def scan_async_marks(
    target_class: ClassInfo,
    target_method: Optional[str],
) -> List[SpringDep]:
    """检查异步标记"""
    results: List[SpringDep] = []
    for m in target_class.methods:
        if target_method and m.name != target_method:
            continue
        if "Async" in m.annotations:
            results.append(SpringDep(
                dep_type="async",
                source_class=target_class.name,
                source_method=m.name,
                detail="@Async",
                file_path=target_class.file_path,
                line=m.line_start,
            ))

    return results


# ─── Compressed View ───────────────────────────────────────

def build_compressed_view(
    callers: List[CallEdge],
    callees: List[CallEdge],
    class_index: Dict[str, ClassInfo],
) -> List[dict]:
    """为调用图中涉及的每个类生成压缩视图（签名+注解+行号）"""
    involved_classes: Set[str] = set()
    for e in callers:
        involved_classes.add(e.from_class)
    for e in callees:
        involved_classes.add(e.to_class)

    views = []
    for cls_name in sorted(involved_classes):
        cls = class_index.get(cls_name)
        if not cls:
            continue

        involved_methods: Set[str] = set()
        for e in callers:
            if e.from_class == cls_name:
                involved_methods.add(e.from_method)
        for e in callees:
            if e.to_class == cls_name:
                involved_methods.add(e.to_method)

        method_summaries = []
        for m in cls.methods:
            if m.name in involved_methods:
                method_summaries.append({
                    "signature": m.short_sig,
                    "annotations": [f"@{a}" for a in m.annotations] if m.annotations else [],
                    "lines": f"{m.line_start}-{m.line_end}",
                })

        views.append({
            "class": cls_name,
            "file": cls.file_path,
            "annotations": [f"@{a}" for a in cls.annotations] if cls.annotations else [],
            "relevant_methods": method_summaries,
            "suggest_read_lines": f"{min(m.line_start for m in cls.methods if m.name in involved_methods)}-{max(m.line_end for m in cls.methods if m.name in involved_methods)}" if method_summaries else "",
        })

    return views


# ─── Risk Assessment ───────────────────────────────────────

def assess_risk(
    callers: List[CallEdge],
    callees: List[CallEdge],
    spring_deps: List[SpringDep],
    cycles: List[dict],
) -> dict:
    risk_factors = []
    risk_level = "LOW"

    if len(callers) > 5:
        risk_factors.append(f"调用者较多({len(callers)}个)，改动影响面广")
        risk_level = "MEDIUM"
    if len(callers) > 10:
        risk_level = "HIGH"

    aop_deps = [d for d in spring_deps if d.dep_type == "aop"]
    if aop_deps:
        risk_factors.append(f"被{len(aop_deps)}个AOP切面拦截，行为可能被隐式修改")
        risk_level = max(risk_level, "MEDIUM", key=lambda x: ["LOW", "MEDIUM", "HIGH"].index(x))

    tx_deps = [d for d in spring_deps if d.dep_type == "transaction"]
    if tx_deps:
        risk_factors.append(f"涉及事务边界({len(tx_deps)}处)，需关注事务传播和回滚")
        risk_level = max(risk_level, "MEDIUM", key=lambda x: ["LOW", "MEDIUM", "HIGH"].index(x))

    if cycles:
        risk_factors.append(f"检测到{len(cycles)}个循环调用，可能导致栈溢出或死锁")
        risk_level = "HIGH"

    scheduled_deps = [d for d in spring_deps if d.dep_type == "scheduled"]
    if scheduled_deps:
        risk_factors.append(f"被{len(scheduled_deps)}个定时任务使用")

    event_deps = [d for d in spring_deps if d.dep_type == "event_listener"]
    if event_deps:
        risk_factors.append(f"涉及事件发布/监听({len(event_deps)}个监听器)")

    cache_deps = [d for d in spring_deps if d.dep_type == "cache"]
    if cache_deps:
        risk_factors.append(f"涉及缓存操作({len(cache_deps)}处)，需关注缓存一致性")

    dimensions_hit = sorted(set(d.dep_type for d in spring_deps))

    return {
        "level": risk_level,
        "factors": risk_factors,
        "dimensions_hit": dimensions_hit,
        "total_callers": len(callers),
        "total_callees": len(callees),
        "total_spring_deps": len(spring_deps),
        "cycles_detected": len(cycles),
    }


# ─── Main ──────────────────────────────────────────────────

def run_scan(
    project_root: Path,
    target: str,
    max_depth: int,
    output: Optional[Path],
) -> int:
    project_root = project_root.resolve()
    if not project_root.is_dir():
        log(f"项目目录不存在: {project_root}")
        return 1

    parts = target.split(".", 1)
    target_class_name = parts[0]
    target_method_name = parts[1] if len(parts) > 1 else None

    log(f"目标: {target_class_name}" + (f".{target_method_name}" if target_method_name else " (全类)"))
    log(f"深度限制: {max_depth}")
    log(f"扫描项目: {project_root}")

    java_files = collect_java_files(project_root)
    log(f"找到 {len(java_files)} 个 Java 文件")

    all_classes: List[ClassInfo] = []
    class_index: Dict[str, ClassInfo] = {}

    for idx, jf in enumerate(java_files, 1):
        if idx % 50 == 0:
            log(f"  解析进度: {idx}/{len(java_files)}")
        cls = parse_class(jf, project_root)
        if cls:
            all_classes.append(cls)
            class_index[cls.name] = cls

    log(f"解析完成: {len(all_classes)} 个类")

    target_cls = class_index.get(target_class_name)
    if not target_cls:
        log(f"未找到目标类: {target_class_name}")
        candidates = [c.name for c in all_classes if target_class_name.lower() in c.name.lower()]
        if candidates:
            log(f"可能的匹配: {', '.join(candidates[:5])}")
        return 1

    if target_method_name:
        method_names = {m.name for m in target_cls.methods}
        if target_method_name not in method_names:
            log(f"未找到目标方法: {target_class_name}.{target_method_name}")
            log(f"可用方法: {', '.join(sorted(method_names))}")
            return 1

    log("构建调用图...")
    callers, callees, cycles = build_call_graph(
        target_class_name, target_method_name, class_index, max_depth,
    )

    log("扫描 Spring 隐式依赖...")
    spring_deps: List[SpringDep] = []
    spring_deps.extend(scan_aop_matches(target_cls, target_method_name, all_classes))
    spring_deps.extend(scan_event_listeners(target_cls, all_classes))
    spring_deps.extend(scan_scheduled_tasks(target_cls, target_method_name, all_classes, class_index))
    spring_deps.extend(scan_config_deps(target_cls, all_classes, project_root))
    spring_deps.extend(scan_transaction_boundaries(target_cls, target_method_name, class_index))
    spring_deps.extend(scan_cache_ops(target_cls, target_method_name))
    spring_deps.extend(scan_async_marks(target_cls, target_method_name))

    log("生成压缩视图...")
    compressed = build_compressed_view(callers, callees, class_index)

    log("评估风险...")
    risk = assess_risk(callers, callees, spring_deps, cycles)

    target_info = {
        "class": target_class_name,
        "method": target_method_name,
        "full_name": target_cls.full_name,
        "file": target_cls.file_path,
        "annotations": [f"@{a}" for a in target_cls.annotations],
    }
    if target_method_name:
        for m in target_cls.methods:
            if m.name == target_method_name:
                target_info["method_signature"] = m.short_sig
                target_info["method_annotations"] = [f"@{a}" for a in m.annotations]
                target_info["method_lines"] = f"{m.line_start}-{m.line_end}"
                break

    result = {
        "target": target_info,
        "call_graph": {
            "callers": [e.to_dict() for e in callers],
            "callees": [e.to_dict() for e in callees],
        },
        "spring_deps": {
            "aop": [d.to_dict() for d in spring_deps if d.dep_type == "aop"],
            "event_listeners": [d.to_dict() for d in spring_deps if d.dep_type == "event_listener"],
            "scheduled": [d.to_dict() for d in spring_deps if d.dep_type == "scheduled"],
            "config": [d.to_dict() for d in spring_deps if d.dep_type == "config"],
            "transaction": [d.to_dict() for d in spring_deps if d.dep_type == "transaction"],
            "cache": [d.to_dict() for d in spring_deps if d.dep_type == "cache"],
            "async": [d.to_dict() for d in spring_deps if d.dep_type == "async"],
        },
        "cycles": cycles,
        "compressed_views": compressed,
        "risk_assessment": risk,
        "scan_config": {
            "depth_limit": max_depth,
            "total_classes_scanned": len(all_classes),
        },
    }

    output_json = json.dumps(result, ensure_ascii=False, indent=2)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(output_json + "\n", encoding="utf-8")
        log(f"已写入: {output}")
    else:
        print(output_json)

    log(f"\n===== 影响分析摘要 =====")
    log(f"  目标: {target}")
    log(f"  风险等级: {risk['level']}")
    log(f"  调用者: {risk['total_callers']} 个")
    log(f"  被调用: {risk['total_callees']} 个")
    log(f"  Spring隐式依赖: {risk['total_spring_deps']} 个")
    log(f"  循环调用: {risk['cycles_detected']} 个")
    if risk["factors"]:
        log(f"  风险因素:")
        for f in risk["factors"]:
            log(f"    - {f}")
    log(f"========================")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="变更影响分析地图生成器 — 扫描 Java/Spring Boot 项目并输出影响地图 JSON",
    )
    parser.add_argument("project", type=Path, help="项目根目录路径")
    parser.add_argument(
        "--target", "-t", required=True,
        help="分析目标，格式: ClassName 或 ClassName.methodName",
    )
    parser.add_argument(
        "--depth", "-d", type=int, default=3,
        help="调用链最大追踪深度（默认 3，设 0 为不限制）",
    )
    parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="输出 JSON 文件路径（默认 stdout）",
    )
    args = parser.parse_args()

    effective_depth = args.depth if args.depth > 0 else 999
    return run_scan(args.project, args.target, effective_depth, args.output)


if __name__ == "__main__":
    sys.exit(main())
