---
name: impact-analysis
description: 变更影响分析。当用户提到修Bug、接手功能、改动影响、影响范围、影响分析、上下游、调用链时使用。在涉及代码变更前应主动使用此技能评估影响范围。
author: czc
version: 1.0.0
tags: [java, spring-boot, impact, analysis, call-graph, change]
---

# Impact Analysis — 变更影响分析

分析 Java/Spring Boot 代码变更的影响范围，通过脚本构建确定性依赖地图，再由 AI 按图索骥逐维度分析。

## 核心理念

**不让 AI 一次性读所有关联代码**，而是：
1. 脚本先建"地图"（零 token 成本，确定性结果）
2. AI 读地图定位风险点（低 token）
3. AI 只对高风险文件做深度分析（精准 token）

## 工具依赖

- **Python 3.10+**：运行 `impact-scanner.py`
- **Git**：可选，用于历史关联分析

## 快速入口

用户说"分析一下改 XX 的影响"时，直接执行：

```bash
python "<SKILL_DIR>/scripts/impact-scanner.py" "<PROJECT_ROOT>" --target "ClassName" -o impact-map.json
python "<SKILL_DIR>/scripts/impact-scanner.py" "<PROJECT_ROOT>" --target "ClassName.methodName" --depth 3 -o impact-map.json
```

其中 `<SKILL_DIR>` 为此 SKILL.md 所在目录，`<PROJECT_ROOT>` 为 Java 项目根目录。

### 字段级影响分析

当用户提到"加字段"、"删字段"、"改字段"、"字段脱敏"等场景时，使用：

```bash
python "<SKILL_DIR>/scripts/field-impact-scanner.py" "<PROJECT_ROOT>" --target "User.email" -o field-impact.json
python "<SKILL_DIR>/scripts/field-impact-scanner.py" "<PROJECT_ROOT>" --target "user.email" -o field-impact.json
```

- `User.email` — 从 Entity 类切入（大写开头）
- `user.email` — 从数据库表切入（小写开头）

## 四阶段工作流

| 阶段 | 执行者 | 成本 | 做什么 |
|------|--------|------|--------|
| Phase 1: 侦察 | Python 脚本 | $0 | 构建调用图 + Spring 隐式依赖地图 |
| Phase 2: 定位 | AI（快速） | ~2K token | 读地图 → 标记风险维度 |
| Phase 3: 深潜 | AI（高级） | 按需 | 只读高风险文件的相关行 |
| Phase 4: 汇总 | AI（快速） | ~1K token | 输出结构化风险报告 |

## 详细指引

根据当前阶段，按需阅读以下文件：

- **完整工作流步骤** → 阅读 [workflow.md](workflow.md)
- **输出报告模板** → 阅读 [templates.md](templates.md)
- **脚本参数和维度参考** → 阅读 [reference.md](reference.md)

## 输出格式要求

最终输出为 Markdown 格式的影响分析报告，包含：
1. 影响概览（风险等级、关键数字）
2. 调用链追踪结果
3. Spring 隐式依赖清单
4. 逐维度风险评估（已确认/有风险/不适用）
5. 建议的变更策略

**禁止使用"可能"、"应该没问题"等模糊表述，每个结论必须有代码证据支撑。**
