---
name: api-doc-gen
description: 扫描 Spring Boot Controller 和 Knife4j/Swagger 注解自动生成 Markdown API 文档。当用户提到接口文档、API文档、Swagger、Knife4j、接口列表、API清单、文档生成、文档同步时使用。
author: czc
---

# 接口文档生成器（api-doc-gen）

扫描 Java Spring Boot 项目的 Controller 层及 Knife4j/Swagger 注解，从源码生成与代码同步的 Markdown 接口文档，解决「文档与代码脱节、维护成本高」的痛点。

## 何时使用

- 用户要求生成/更新接口文档、API 清单、Swagger 导出
- 用户提到 Knife4j、Swagger、接口同步、文档过期
- 项目有 `@RestController` 但缺少或过时的人工文档
- 用户指定输出路径（默认 `docs/api/` 或用户指定）

## 工具依赖

| 工具 | 用途 |
|------|------|
| Glob | 扫描 `**/*Controller.java`、`**/*Dto*.java`、`**/*Vo*.java`、`**/*Request*.java`、`**/*Response*.java` |
| Grep | 搜索注解、类级/方法级映射、统一响应包装类 |
| Read | 读取 Controller、DTO/VO、全局异常处理、错误码枚举 |
| SemanticSearch | 定位 `Result`/`R`/`ApiResponse` 等统一响应结构 |

## 预置脚本

**`scripts/scan-controllers.py`** — 扫描 Controller 和 DTO/VO 注解，输出结构化 JSON。

```bash
python scripts/scan-controllers.py /path/to/project --include-dto --output api-data.json
```

脚本输出 JSON 包含 `controllers`（接口映射）、`models`（DTO 字段）、`statistics`（统计），可直接用于生成 Markdown 文档。优先运行此脚本获取结构化数据，再基于 JSON 补充 AI 分析。

## 执行流程

```
任务进度：
- [ ] Step 1: 扫描 Controller 类
- [ ] Step 2: 提取接口映射信息
- [ ] Step 3: 递归解析 DTO/VO 字段
- [ ] Step 4: 构造示例 JSON
- [ ] Step 5: 输出 Markdown 文件
```

| 步骤 | 摘要 |
|------|------|
| Step 1 | Glob `**/*Controller.java`，记录包名、类名、类级 `@RequestMapping` 与分组注解 |
| Step 2 | 解析 HTTP 方法、完整路径、描述、参数列表、返回类型及 Produces/Consumes |
| Step 3 | 读取 DTO/VO 字段与注解，映射文档类型，递归嵌套类型（深度上限 3 层） |
| Step 4 | 生成请求/响应示例 JSON，提取业务错误码并与接口关联 |
| Step 5 | 按模板写入 `docs/api/`，汇报 Controller 数、接口数及未解析类型 |

## 详细指引（按需加载）

- Step 1-5 完整工作流（扫描、解析、示例JSON、输出规则）→ 读 [workflow.md](workflow.md)
- 输出 Markdown 模板与锚点规则 → 读 [templates.md](templates.md)
- 注解覆盖范围与类型映射查阅 → 读 [reference.md](reference.md)
