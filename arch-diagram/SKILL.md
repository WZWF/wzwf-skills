---
name: arch-diagram
description: 扫描 Java/Spring Boot 项目代码自动生成架构图。支持 draw.io XML 和独立 HTML 双格式输出。当用户提到架构图、模块依赖、系统设计图、分层架构、UML、draw.io、技术架构可视化、新人入职文档时使用。
author: czc
---

# 架构图生成器（arch-diagram）

扫描 Java/Spring Boot 项目代码，自动生成可编辑的架构图。适用于开会讲解、新人入职、理清模块依赖。

## 何时使用

- 用户要求画/生成架构图、模块依赖图、类图、流程图
- 用户提到 draw.io、系统设计图、分层架构、技术架构可视化
- 新人入职需要项目结构说明文档
- 用户想快速理解当前项目的模块关系或请求处理链

## 依赖与工具

| 工具 | 用途 | 必须 |
|------|------|------|
| Glob | 扫描 pom.xml、Java 源码目录 | ✅ |
| Grep | 搜索 import、注解、类名模式 | ✅ |
| Read | 读取 pom.xml、关键 Java 类 | ✅ |
| Write | 输出 .drawio / .html 文件 | ✅ |
| user-drawio MCP | 优先调用 draw.io 工具渲染/编辑 | 可选（不可用时降级为手写 XML） |

## 预置脚本

**`scripts/scan-java.py`** — 输出 `layers`/`classes`/`edges`/`modules` JSON：

```bash
python scripts/scan-java.py /path/to/project --max-depth -1 --output arch-data.json
```

## 支持的图类型

| 类型 | 标识 | 内容 | 典型场景 |
|------|------|------|----------|
| 分层架构图 | `layered` | Controller → Service → Repository → Infrastructure | 讲解项目分层、新人 onboarding |
| 模块依赖图 | `module-deps` | Maven 模块间依赖、Spring Bean 注入关系 | 理清多模块边界、Starter 依赖 |
| 核心流程图 | `flow` | 关键业务流程（加锁、请求链、AOP 拦截） | 技术分享、排查链路 |
| 类关系图 | `class-relation` | 接口/实现类/继承/组合关系（简化 UML） | 理解核心抽象与扩展点 |

## 工作流程

```
任务进度：
- [ ] Step 1: 扫描项目结构（pom.xml / 模块）
- [ ] Step 2: 扫描 Java 源码识别层次
- [ ] Step 3: 分析依赖关系
- [ ] Step 4: 确认图类型与输出格式
- [ ] Step 5: 生成图文件（按格式读子指南）
```

### Step 1: 扫描项目结构

1. 定位根 `pom.xml`（工作区向上或用户指定路径）
2. 解析 `<modules>`、`<dependency>` 构建模块列表与依赖矩阵
3. 识别项目类型：单体 / 多模块 / Spring Boot Starter
4. `Glob: **/pom.xml` 与 `**/src/main/java/**/*.java`

### Step 2: 扫描 Java 源码识别层次

按包名后缀和注解分类（优先级：注解 > 包名 > 类名后缀）：

| 层次 | 识别规则 |
|------|----------|
| Controller | `@RestController` `@Controller` 或 `*Controller` |
| Service | `@Service` 或 `*Service` / `*ServiceImpl` |
| Repository | `@Repository` `*Mapper` `*Dao` `*Repository` |
| Config | `@Configuration` `@Enable*` `*AutoConfiguration` |
| Aspect | `@Aspect` `*Aspect` `*Interceptor` |
| Infrastructure | `*Client` `*Template` `*Handler` Redis/Lock/MQ 相关 |
| Domain/Entity | `*Entity` `*DO` `*DTO` `*VO` `*BO` |
| Utils | `*Util` `*Helper` `*Constants` |

类数 > 30 时每层取代表性类，输出注明「已采样，共 N 类」。

### Step 3: 分析依赖关系

- **Maven**（module-deps）：子模块 pom 的 `<dependency>` 匹配兄弟 `<artifactId>`
- **Spring 注入**（layered / module-deps / class-relation）：Grep `@Autowired|@Resource|@Inject|private final \w+`（构造注入 `private final XxxService`，字段注入 `@Autowired private XxxMapper`）；保留项目内依赖，过滤 `java.*` / `org.springframework.*`
- **类关系**（class-relation）：`implements` / `extends`；接口与 `*Impl` 配对
- **流程链**（flow）：从指定入口或 `@RestController` 追踪 Controller → Service → Repository/Client → AOP；标注失败/异常/重试

Step 4 确认图类型、格式、流程入口、输出路径（默认 `docs/arch-diagram/`）；Step 5 按下方子指南生成。

## 详细指引（按需加载）

- 生成 draw.io 格式 → 读 [drawio-guide.md](drawio-guide.md)
- 生成 HTML 格式 → 读 [html-guide.md](html-guide.md)
- 各图类型详细规则 → 读 [diagram-types.md](diagram-types.md)
