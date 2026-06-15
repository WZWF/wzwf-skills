# Step 3：生成文件

## 3.1 pom.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>{groupId}</groupId>
        <artifactId>nhai-infra-starters</artifactId>
        <version>${revision}</version>
    </parent>

    <artifactId>nhai-infra-boot-starter-{name}</artifactId>
    <packaging>jar</packaging>

    <properties>
        <maven.compiler.source>{javaVersion}</maven.compiler.source>
        <maven.compiler.target>{javaVersion}</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-autoconfigure</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-configuration-processor</artifactId>
            <optional>true</optional>
        </dependency>
        <!-- needAop: spring-boot-starter-aop -->
        <!-- needRedis: nhai-infra-boot-starter-multipleredis（nhai 项目）或 spring-boot-starter-data-redis -->
        <dependency>
            <groupId>{groupId}</groupId>
            <artifactId>nhai-infra-utils</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
```

依赖规则：
- **AOP**（`needAop=true`）：`spring-boot-starter-aop`
- **Redis**（`needRedis=true`）：优先 `nhai-infra-boot-starter-multipleredis`；非 nhai 项目用 `spring-boot-starter-data-redis`
- **nhai 公共依赖**（可选）：`nhai-infra-core`、`nhai-infra-operation`

## 3.2 {Name}Properties.java

路径：`config/{Name}Properties.java`

```java
package {package}.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "nhai.{nameCamel}")
public class {Name}Properties {

    /** 是否启用 */
    private boolean enabled = true;

    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }
}
```

## 3.3 {Name}AutoConfiguration.java

路径：`autoconfigure/{Name}AutoConfiguration.java`

```java
package {package}.autoconfigure;

import {package}.config.{Name}Properties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
// needRedis: import RedisAutoConfiguration; @AutoConfiguration(after = RedisAutoConfiguration.class)
// needRedis: @ConditionalOnClass(RedisTemplate.class)

@AutoConfiguration
@ConditionalOnProperty(prefix = "nhai.{nameCamel}", name = "enabled",
        havingValue = "true", matchIfMissing = true)
@EnableConfigurationProperties({Name}Properties.class)
public class {Name}AutoConfiguration {

    private static final Logger log = LoggerFactory.getLogger({Name}AutoConfiguration.class);

    public {Name}AutoConfiguration() {
        log.info("Nhai {Name} Starter 自动配置已加载");
    }
}
```

`needAop=true` 时追加 `@Bean` + `@ConditionalOnMissingBean` 注册 `{Name}Aspect`。
`needRedis=true` 时添加 `@AutoConfiguration(after = RedisAutoConfiguration.class)` 和 `@ConditionalOnClass(RedisTemplate.class)`。

## 3.4 AOP 骨架（needAop=true）

**annotations/{Name}.java** — 方法级注解，`@Target(METHOD)` + `@Retention(RUNTIME)`。

**aspect/{Name}Aspect.java** — `@Aspect` + `@Component`，`@Around("@annotation(...))` 占位实现。

## 3.5 异常与工具类

**exception/{Name}Exception.java** — 继承 `RuntimeException`；nhai 项目可继承 `BusinessException`。

**utils/{Name}Utils.java** — 静态工具类占位。

## 3.6 自动配置注册

**bootVersion = 2.x 或 both** — `META-INF/spring.factories`：

```properties
org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
  {package}.autoconfigure.{Name}AutoConfiguration
```

**bootVersion = 3.x 或 both** — `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`：

```
{package}.autoconfigure.{Name}AutoConfiguration
```

## 3.7 Lua 脚本（needLua=true）

在 `src/main/resources/lua/` 创建 `{nameCamel}.lua` 占位脚本，注释说明用途。

## 3.8 测试骨架

`src/test/java/{packagePath}/autoconfigure/{Name}AutoConfigurationTest.java`：

```java
@SpringBootTest(classes = {Name}AutoConfiguration.class)
class {Name}AutoConfigurationTest {
    @Test
    void contextLoads() { }
}
```

---

## 注意事项

1. **包名**：`rate-limit` → 包段 `ratelimit`（去掉连字符），非 `rate.limit`。
2. **AutoConfiguration 位置**：放 `autoconfigure/`，Properties 放 `config/`（与 lock 参考项目不同，按本规范执行）。
3. **条件注解**：AutoConfiguration 必须含 `@ConditionalOnProperty` 开关，Bean 用 `@ConditionalOnMissingBean` 允许覆盖。
4. **不要过度生成**：无 AOP/Redis/Lua 需求时不创建对应文件和依赖。
5. **编译验证**：生成后执行 `mvn compile` 确认通过。

## 示例

**输入**：name=`cache`，description=`本地与 Redis 二级缓存 Starter`，needRedis=true，bootVersion=both

**输出**：
- `nhai-infra-boot-starter-cache/`
- `CacheProperties`（prefix=`nhai.cache`）
- `CacheAutoConfiguration`（after RedisAutoConfiguration）
- spring.factories + AutoConfiguration.imports
- README 含依赖与 YAML 示例
