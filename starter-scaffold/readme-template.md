# Step 4：生成 README.md

```markdown
# {description}

## 特性

- 自动配置，引入依赖即可使用
- 可通过 `nhai.{nameCamel}.enabled` 开关（默认 true）
<!-- needAop: 注解式接入 -->
<!-- needRedis: 基于 Redis -->

## 快速开始

### 1. 添加依赖

\`\`\`xml
<dependency>
    <groupId>{groupId}</groupId>
    <artifactId>nhai-infra-boot-starter-{name}</artifactId>
</dependency>
\`\`\`

### 2. 配置

\`\`\`yaml
nhai:
  {nameCamel}:
    enabled: true
\`\`\`

<!-- needRedis 追加 spring.redis 配置示例 -->

### 3. 使用

<!-- 根据 needAop 给出注解示例或 API 调用示例 -->

## 配置项

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `nhai.{nameCamel}.enabled` | boolean | `true` | 是否启用 |

## 目录结构

（列出主要包说明）
```

---

## 执行清单

```
- [ ] Step 1: 收集并确认参数
- [ ] Step 2: 创建目录 + 注册父 POM module
- [ ] Step 3: 生成 pom.xml、Java 源文件、META-INF 注册文件
- [ ] Step 4: 生成 README.md
- [ ] 验证: mvn -pl nhai-infra-boot-starter-{name} compile
```
