#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Field Impact Scanner — 字段级变更影响分析

扫描 Java/Spring Boot 项目中某个字段的影响范围，
支持从 Entity 类或数据库表切入。

Usage:
    python field-impact-scanner.py /path/to/project --target "User.email"
    python field-impact-scanner.py /path/to/project --target "user.email" -o field-impact.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set

SKIP_DIRS = {
    "node_modules", ".git", "target", "build", ".gradle",
    ".idea", ".vscode", "__pycache__", "dist", ".next", "docs",
}


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# ─── Data Classes ──────────────────────────────────────────

@dataclass
class FieldInfo:
    """Entity 字段信息"""
    class_name: str
    field_name: str
    column_name: str
    field_type: str
    annotations: List[str]
    file_path: str
    line: int


@dataclass
class SqlReference:
    """SQL 中的字段引用"""
    file_path: str
    statement_id: str
    sql_type: str  # select/insert/update/delete
    columns: List[str]
    line: int


@dataclass
class MapperMethod:
    """Mapper 方法信息"""
    class_name: str
    method_name: str
    sql_type: str
    columns: List[str]
    file_path: str
    line: int


@dataclass
class ImpactNode:
    """影响节点"""
    layer: str  # entity/mapper/service/controller
    class_name: str
    member_name: str
    file_path: str
    line: int
    annotations: List[str] = field(default_factory=list)  # 类/方法注解
    injected_deps: List[str] = field(default_factory=list)  # 注入的依赖
    suggest_read_lines: str = ""  # 建议读取的行范围


# ─── File Collection ──────────────────────────────────────

def collect_java_files(project_root: Path) -> List[Path]:
    """收集所有 Java 文件"""
    files = []
    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(".java"):
                files.append(Path(dirpath) / f)
    return sorted(files)


def collect_xml_files(project_root: Path) -> List[Path]:
    """收集所有 MyBatis XML 文件"""
    files = []
    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(".xml"):
                files.append(Path(dirpath) / f)
    return sorted(files)


# ─── Entity Field Scanning ────────────────────────────────

RE_COLUMN = re.compile(r'@Column\s*\(\s*(?:name\s*=\s*)?["\']?(\w+)["\']?')
RE_TABLE_FIELD = re.compile(r'@TableField\s*\(\s*(?:value\s*=\s*)?["\']?(\w+)["\']?')
RE_FIELD_DECL = re.compile(r'private\s+([\w<>,\[\]]+)\s+(\w+)\s*;')


def scan_entity_fields(
    java_files: List[Path],
    project_root: Path,
) -> Dict[str, List[FieldInfo]]:
    """扫描所有 Entity 类的字段，返回 {类名: [FieldInfo]}"""
    entities: Dict[str, List[FieldInfo]] = {}

    for fpath in java_files:
        try:
            content = fpath.read_text(encoding="utf-8")
        except OSError:
            continue

        # 简单判断是否是 Entity
        if "@Entity" not in content and "@TableName" not in content:
            if not any(x in fpath.stem for x in ("DO", "Entity", "Model")):
                continue

        class_match = re.search(r'class\s+(\w+)', content)
        if not class_match:
            continue
        class_name = class_match.group(1)

        rel_path = str(fpath.relative_to(project_root)).replace("\\", "/")
        fields = []

        for line_num, line in enumerate(content.splitlines(), 1):
            field_match = RE_FIELD_DECL.search(line)
            if not field_match:
                continue

            field_type = field_match.group(1)
            field_name = field_match.group(2)

            # 提取 column 名 - 向上找紧邻的注解
            column_name = field_name
            lines = content.splitlines()
            start = max(0, line_num - 5)
            context_lines = lines[start:line_num]
            context = "\n".join(context_lines)

            # 只找最后一个 @Column 或 @TableField（紧邻当前字段的）
            col_matches = list(RE_COLUMN.finditer(context))
            if col_matches:
                column_name = col_matches[-1].group(1)
            else:
                tf_matches = list(RE_TABLE_FIELD.finditer(context))
                if tf_matches:
                    column_name = tf_matches[-1].group(1)

            annotations = []
            for ann in ["Column", "TableField", "Id", "TableId"]:
                if f"@{ann}" in context:
                    annotations.append(ann)

            fields.append(FieldInfo(
                class_name=class_name,
                field_name=field_name,
                column_name=column_name,
                field_type=field_type,
                annotations=annotations,
                file_path=rel_path,
                line=line_num,
            ))

        if fields:
            entities[class_name] = fields

    return entities


# ─── MyBatis XML Scanning ─────────────────────────────────

RE_SQL_COLUMNS = re.compile(
    r'(?:SELECT|INSERT\s+INTO|UPDATE|WHERE|SET)\s+(.*?)(?:FROM|VALUES|WHERE|SET|$)',
    re.IGNORECASE | re.DOTALL,
)
RE_COLUMN_NAME = re.compile(r'\b(\w+)\b(?:\s*[=,]|$)')


def scan_mybatis_xml(
    xml_files: List[Path],
    project_root: Path,
) -> List[SqlReference]:
    """扫描 MyBatis XML 中的字段引用"""
    refs = []

    for fpath in xml_files:
        try:
            content = fpath.read_text(encoding="utf-8")
        except OSError:
            continue

        if "<mapper" not in content:
            continue

        rel_path = str(fpath.relative_to(project_root)).replace("\\", "/")

        # 扫描 select/insert/update/delete
        for match in re.finditer(
            r'<(select|insert|update|delete)\s+id="(\w+)"[^>]*>(.*?)</\1>',
            content, re.DOTALL | re.IGNORECASE,
        ):
            sql_type = match.group(1).lower()
            stmt_id = match.group(2)
            sql_body = match.group(3)
            line = content[:match.start()].count("\n") + 1

            # 提取字段名
            columns = set()
            for col_match in RE_COLUMN_NAME.finditer(sql_body):
                col = col_match.group(1)
                # 过滤 SQL 关键字
                if col.upper() not in (
                    "SELECT", "FROM", "WHERE", "AND", "OR", "INSERT",
                    "INTO", "VALUES", "UPDATE", "SET", "DELETE", "NULL",
                    "TRUE", "FALSE", "AS", "ON", "JOIN", "LEFT", "RIGHT",
                ):
                    columns.add(col.lower())

            if columns:
                refs.append(SqlReference(
                    file_path=rel_path,
                    statement_id=stmt_id,
                    sql_type=sql_type,
                    columns=sorted(columns),
                    line=line,
                ))

    return refs


# ─── Mapper Annotation Scanning ───────────────────────────

RE_MAPPER_ANNOTATION = re.compile(
    r'@(Select|Insert|Update|Delete)\s*\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
RE_MAPPER_METHOD = re.compile(
    r'(?:public\s+|default\s+)?(?:\w+(?:<[^>]+>)?)\s+(\w+)\s*\(',
)


def scan_mapper_annotations(
    java_files: List[Path],
    project_root: Path,
) -> List[MapperMethod]:
    """扫描 Mapper 接口中的注解 SQL"""
    methods = []

    for fpath in java_files:
        try:
            content = fpath.read_text(encoding="utf-8")
        except OSError:
            continue

        if "Mapper" not in fpath.stem and "@Mapper" not in content:
            continue

        class_match = re.search(r'interface\s+(\w+)', content)
        if not class_match:
            continue
        class_name = class_match.group(1)
        rel_path = str(fpath.relative_to(project_root)).replace("\\", "/")

        # 扫描 @Select/@Insert 等注解
        for match in RE_MAPPER_ANNOTATION.finditer(content):
            sql_type = match.group(1).lower()
            sql = match.group(2)
            line = content[:match.start()].count("\n") + 1

            # 向后找方法名
            after = content[match.end():]
            method_match = RE_MAPPER_METHOD.search(after)
            method_name = method_match.group(1) if method_match else "unknown"

            # 提取字段
            columns = set()
            for col_match in RE_COLUMN_NAME.finditer(sql):
                col = col_match.group(1)
                if col.upper() not in (
                    "SELECT", "FROM", "WHERE", "AND", "OR", "INSERT",
                    "INTO", "VALUES", "UPDATE", "SET", "DELETE",
                ):
                    columns.add(col.lower())

            methods.append(MapperMethod(
                class_name=class_name,
                method_name=method_name,
                sql_type=sql_type,
                columns=sorted(columns),
                file_path=rel_path,
                line=line,
            ))

        # 扫描方法名推断 (findByXxx, deleteByXxx)
        for m in re.finditer(r'(\w+)(?:By(\w+))?\s*\(', content):
            prefix = m.group(1)
            if prefix.startswith(("find", "delete", "update", "count", "exists")):
                field_part = m.group(2)
                if field_part:
                    col = re.sub(r'([A-Z])', r'_\1', field_part).lower().lstrip("_")
                    line = content[:m.start()].count("\n") + 1
                    methods.append(MapperMethod(
                        class_name=class_name,
                        method_name=m.group(1) + (f"By{field_part}" if field_part else ""),
                        sql_type="select" if prefix.startswith("find") else prefix,
                        columns=[col],
                        file_path=rel_path,
                        line=line,
                    ))

    return methods


# ─── Call Chain Tracing ───────────────────────────────────

def classify_layer(class_name: str) -> str:
    """根据类名判断所属层"""
    if "Controller" in class_name or "Resource" in class_name:
        return "controller"
    elif "Service" in class_name:
        return "service"
    elif "Mapper" in class_name or "Repository" in class_name or "Dao" in class_name:
        return "mapper"
    return "other"


def extract_class_context(content: str) -> dict:
    """提取类的上下文信息（注解、注入依赖等）"""
    annotations = []
    injected_deps = []

    for ann in ["Service", "Controller", "RestController", "Component", "Transactional"]:
        if f"@{ann}" in content:
            annotations.append(ann)

    inject_pattern = re.compile(
        r'@(?:Autowired|Resource|Inject)\s+(?:private\s+)?(\w+)\s+(\w+)\s*;'
    )
    for m in inject_pattern.finditer(content):
        injected_deps.append(m.group(1))

    return {"annotations": annotations, "injected_deps": injected_deps}


def trace_call_chain(
    java_files: List[Path],
    project_root: Path,
    matched_mappers: List[MapperMethod],
) -> List[ImpactNode]:
    """追踪 Mapper → Service → Controller 调用链"""
    nodes = []
    mapper_classes = {m.class_name for m in matched_mappers}

    # 构建注入关系图
    inject_map: Dict[str, List[str]] = {}  # 被注入者 → [注入它的类]

    for fpath in java_files:
        try:
            content = fpath.read_text(encoding="utf-8")
        except OSError:
            continue

        class_match = re.search(r'class\s+(\w+)', content)
        if not class_match:
            continue
        class_name = class_match.group(1)
        rel_path = str(fpath.relative_to(project_root)).replace("\\", "/")

        # 检查注入了哪些 Mapper/Service
        for mapper_cls in mapper_classes:
            if mapper_cls in content:
                if mapper_cls not in inject_map:
                    inject_map[mapper_cls] = []
                inject_map[mapper_cls].append(class_name)

                # 添加 Mapper 节点
                for m in matched_mappers:
                    if m.class_name == mapper_cls:
                        nodes.append(ImpactNode(
                            layer="mapper",
                            class_name=mapper_cls,
                            member_name=m.method_name,
                            file_path=m.file_path,
                            line=m.line,
                        ))

        # 检查注入了哪些 Service
        for other_cls in inject_map.get("", []):
            if other_cls in content and classify_layer(other_cls) == "service":
                if other_cls not in inject_map:
                    inject_map[other_cls] = []
                inject_map[other_cls].append(class_name)

    # 追踪 Service 和 Controller
    for fpath in java_files:
        try:
            content = fpath.read_text(encoding="utf-8")
        except OSError:
            continue

        class_match = re.search(r'class\s+(\w+)', content)
        if not class_match:
            continue
        class_name = class_match.group(1)
        rel_path = str(fpath.relative_to(project_root)).replace("\\", "/")
        layer = classify_layer(class_name)

        if layer == "service":
            # 检查是否调用了 Mapper
            for mapper_cls in mapper_classes:
                if mapper_cls in content:
                    ctx = extract_class_context(content)
                    nodes.append(ImpactNode(
                        layer="service",
                        class_name=class_name,
                        member_name="[uses " + mapper_cls + "]",
                        file_path=rel_path,
                        line=0,
                        annotations=ctx["annotations"],
                        injected_deps=ctx["injected_deps"],
                    ))
                    break

    # 第二遍扫描：检测 Controller（此时 Service 节点已存在）
    service_classes = {n.class_name for n in nodes if n.layer == "service"}

    for fpath in java_files:
        try:
            content = fpath.read_text(encoding="utf-8")
        except OSError:
            continue

        class_match = re.search(r'class\s+(\w+)', content)
        if not class_match:
            continue
        class_name = class_match.group(1)
        rel_path = str(fpath.relative_to(project_root)).replace("\\", "/")
        layer = classify_layer(class_name)

        if layer == "controller":
            for svc_cls in service_classes:
                if svc_cls in content:
                    ctx = extract_class_context(content)
                    nodes.append(ImpactNode(
                        layer="controller",
                        class_name=class_name,
                        member_name="[uses " + svc_cls + "]",
                        file_path=rel_path,
                        line=0,
                        annotations=ctx["annotations"],
                        injected_deps=ctx["injected_deps"],
                    ))
                    break

    return nodes


# ─── Main ─────────────────────────────────────────────────

def run_scan(project_root: Path, target: str, output: Optional[Path]) -> int:
    project_root = project_root.resolve()

    # 解析目标: User.email 或 user.email
    parts = target.split(".", 1)
    if len(parts) != 2:
        log("目标格式: ClassName.fieldName 或 tableName.fieldName")
        return 1

    target_first, target_field = parts
    is_table = target_first[0].islower()

    log(f"目标: {target_first}.{target_field}")
    log(f"模式: {'表名' if is_table else 'Entity类'}")

    # 收集文件
    java_files = collect_java_files(project_root)
    xml_files = collect_xml_files(project_root)
    log(f"找到 {len(java_files)} 个 Java 文件, {len(xml_files)} 个 XML 文件")

    # 扫描
    entities = scan_entity_fields(java_files, project_root)
    sql_refs = scan_mybatis_xml(xml_files, project_root)
    mapper_methods = scan_mapper_annotations(java_files, project_root)

    # 匹配目标字段
    matched_entities = []
    matched_sqls = []
    matched_mappers = []

    target_col = target_field.lower()

    for cls_name, fields in entities.items():
        if is_table:
            for f in fields:
                if f.column_name.lower() == target_col:
                    matched_entities.append(f)
        else:
            if cls_name == target_first:
                for f in fields:
                    if f.field_name == target_field:
                        matched_entities.append(f)

    for ref in sql_refs:
        if target_col in ref.columns:
            matched_sqls.append(ref)

    for m in mapper_methods:
        if target_col in m.columns:
            matched_mappers.append(m)

    # 追踪调用链
    call_chain = trace_call_chain(java_files, project_root, matched_mappers)
    log(f"调用链: {len(call_chain)} 个节点")

    # 构建输出
    result = {
        "target": {"first": target_first, "field": target_field, "is_table": is_table},
        "entities": [asdict(e) for e in matched_entities],
        "sql_refs": [asdict(s) for s in matched_sqls],
        "mapper_methods": [asdict(m) for m in matched_mappers],
        "call_chain": [asdict(n) for n in call_chain],
    }

    json_str = json.dumps(result, ensure_ascii=False, indent=2)

    if output:
        output.write_text(json_str + "\n", encoding="utf-8")
        log(f"已写入: {output}")
    else:
        print(json_str)

    # 统计各层节点
    layers = {}
    for n in call_chain:
        layers[n.layer] = layers.get(n.layer, 0) + 1

    log(f"\n===== 字段影响摘要 =====")
    log(f"  Entity: {len(matched_entities)} 个")
    log(f"  SQL引用: {len(matched_sqls)} 个")
    log(f"  Mapper方法: {len(matched_mappers)} 个")
    log(f"  调用链: {layers.get('service', 0)} 个 Service, {layers.get('controller', 0)} 个 Controller")
    log(f"========================")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="字段级变更影响分析")
    parser.add_argument("project", type=Path, help="项目根目录")
    parser.add_argument("--target", "-t", required=True, help="目标: ClassName.fieldName")
    parser.add_argument("--output", "-o", type=Path, help="输出JSON路径")
    args = parser.parse_args()
    return run_scan(args.project, args.target, args.output)


if __name__ == "__main__":
    sys.exit(main())
