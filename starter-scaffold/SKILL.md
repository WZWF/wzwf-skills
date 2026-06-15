---
name: starter-scaffold
description: 输入名称自动生成完整的 Spring Boot Starter 项目骨架，包括标准目录结构、pom.xml、AutoConfiguration、spring.factories 和 README。当用户提到新建 Starter、创建 Starter、Starter 脚手架、Spring Boot 自动配置、starter 模板时使用。
author: czc
---

# Spring Boot Starter 脚手架

根据用户输入，在 `nhai-infra-starters` 下生成标准 Starter 模块骨架。参考实现：`nhai-infra-boot-starter-lock`。

## 预置脚本

**`scripts/scaffold.mjs`** — 一键生成完整 Starter 项目骨架（目录 + 全部 Java 文件 + pom.xml + README）。

```bash
node scripts/scaffold.mjs --name=cache --desc="二级缓存" --boot=both --aop --redis --output=./
```

支持参数：`--name`、`--desc`、`--base-package`、`--boot`（2.x/3.x/both）、`--aop`、`--redis`、`--lua`、`--group-id`、`--java-version`、`--output`。可优先用脚本生成骨架，再由 AI 填充业务逻辑。

## 命名规则

| 占位符 | 规则 | 示例（输入 `rate-limit`） |
|--------|------|---------------------------|
| `{name}` | kebab-case 原名 | `rate-limit` |
| `{Name}` | PascalCase | `RateLimit` |
| `{nameCamel}` | camelCase | `rateLimit` |
| `{artifactId}` | `nhai-infra-boot-starter-{name}` | `nhai-infra-boot-starter-rate-limit` |
| `{package}` | `{basePackage}.{name}`（`-` 转 `.`） | `com.nhai.infra.ratelimit` |

## 目标目录结构

```
nhai-infra-boot-starter-{name}/
├── pom.xml
├── README.md
├── src/main/java/{packagePath}/
│   ├── annotations/
│   ├── aspect/               # 仅 needAop=true
│   ├── autoconfigure/
│   │   └── {Name}AutoConfiguration.java
│   ├── config/
│   │   └── {Name}Properties.java
│   ├── exception/
│   └── utils/
├── src/main/resources/
│   ├── META-INF/
│   │   ├── spring.factories
│   │   └── spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
│   └── lua/                  # 仅 needLua=true
└── src/test/java/{packagePath}/
```

`{packagePath}` = 包名 `.` 换 `/`，如 `com/nhai/infra/lock`。

## Step 1：收集参数

若用户未提供，逐项确认（可用默认值）：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | 是 | — | kebab-case，如 `lock`、`cache` |
| `description` | 是 | — | 一句话功能描述 |
| `basePackage` | 否 | `com.nhai.infra` | 基础包名 |
| `bootVersion` | 否 | `both` | `2.x` / `3.x` / `both` |
| `needAop` | 否 | `false` | 是否生成 AOP 切面 |
| `needRedis` | 否 | `false` | 是否依赖 Redis |
| `needLua` | 否 | `false` | 是否创建 `lua/` 目录 |
| `outputDir` | 否 | 当前 `nhai-infra-starters` | 模块输出目录 |

**上下文检测**：若已在 nhai-infra 仓库，读取父 POM 的 `groupId`（常见 `com.jidian.msa`）和 Java 版本，覆盖默认值。生成前向用户确认参数摘要。

## Step 2：生成目录结构

按目标结构创建目录；空目录用 `.gitkeep` 占位（`annotations/`、`exception/`、`utils/`、`src/test/java/`）。`needAop=false` 不创建 `aspect/`，`needLua=false` 不创建 `lua/`。

**注册模块**：在 `nhai-infra-starters/pom.xml` 的 `<modules>` 追加：

```xml
<module>nhai-infra-boot-starter-{name}</module>
```

## 详细指引（按需加载）

- Step 3 各文件的 Java 模板 → 读 [java-templates.md](java-templates.md)
- Step 4 README 模板 → 读 [readme-template.md](readme-template.md)
