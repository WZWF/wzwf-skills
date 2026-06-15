#!/usr/bin/env node
/**
 * Spring Boot Starter 项目骨架生成脚本
 *
 * 用法:
 *   node scaffold.mjs --name=cache --desc="本地与Redis二级缓存" --base-package=com.nhai.infra --boot=both --aop --redis --lua --output=./
 */

import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { join, resolve, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = join(__filename, '..');

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

const FLAGS = new Set(['aop', 'redis', 'lua']);

function parseArgs(argv) {
  const args = {};
  for (const arg of argv.slice(2)) {
    if (!arg.startsWith('--')) continue;
    const body = arg.slice(2);
    const eq = body.indexOf('=');
    if (eq !== -1) {
      args[body.slice(0, eq)] = body.slice(eq + 1);
    } else {
      args[body] = true;
    }
  }
  return args;
}

function usage() {
  console.error(`
用法:
  node scaffold.mjs --name=<kebab-name> --desc="<description>" [options]

必填:
  --name          Starter 名称 (kebab-case)，如 cache、rate-limit
  --desc          一句话功能描述

可选:
  --base-package  基础包名 (默认 com.nhai.infra)
  --boot          Spring Boot 版本: 2.x | 3.x | both (默认 both)
  --aop           生成 AOP 注解与切面
  --redis         添加 Redis 依赖与条件配置
  --lua           生成 lua/ 脚本目录
  --output        输出根目录 (默认 ./)
  --group-id      Maven groupId (默认 com.jidian.msa)
  --java-version  Java 版本 (默认 8)
`);
}

function resolveOptions(raw) {
  const name = raw.name;
  const desc = raw.desc;

  if (!name || !desc) {
    usage();
    process.exit(1);
  }

  if (!/^[a-z][a-z0-9-]*$/.test(name)) {
    console.error('错误: --name 须为 kebab-case，如 cache、rate-limit');
    process.exit(1);
  }

  const boot = (raw.boot || 'both').toLowerCase();
  if (!['2.x', '3.x', 'both'].includes(boot)) {
    console.error('错误: --boot 须为 2.x、3.x 或 both');
    process.exit(1);
  }

  return {
    name,
    desc,
    basePackage: raw['base-package'] || 'com.nhai.infra',
    boot,
    needAop: Boolean(raw.aop),
    needRedis: Boolean(raw.redis),
    needLua: Boolean(raw.lua),
    outputDir: resolve(raw.output || './'),
    groupId: raw['group-id'] || 'com.jidian.msa',
    javaVersion: raw['java-version'] || '8',
  };
}

// ---------------------------------------------------------------------------
// Naming
// ---------------------------------------------------------------------------

function toPascalCase(kebab) {
  return kebab
    .split('-')
    .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
    .join('');
}

function toCamelCase(kebab) {
  const pascal = toPascalCase(kebab);
  return pascal.charAt(0).toLowerCase() + pascal.slice(1);
}

function toPackageSegment(kebab) {
  return kebab.replace(/-/g, '');
}

function buildContext(opts) {
  const Name = toPascalCase(opts.name);
  const nameCamel = toCamelCase(opts.name);
  const packageSegment = toPackageSegment(opts.name);
  const pkg = `${opts.basePackage}.${packageSegment}`;
  const packagePath = pkg.replace(/\./g, '/');
  const artifactId = `nhai-infra-boot-starter-${opts.name}`;
  const moduleDir = artifactId;

  return {
    ...opts,
    Name,
    nameCamel,
    packageSegment,
    pkg,
    packagePath,
    artifactId,
    moduleDir,
  };
}

// ---------------------------------------------------------------------------
// File writers
// ---------------------------------------------------------------------------

const createdFiles = [];

function writeFile(absPath, content) {
  const dir = join(absPath, '..');
  mkdirSync(dir, { recursive: true });
  writeFileSync(absPath, content, { encoding: 'utf8' });
  createdFiles.push(absPath);
}

function writeGitkeep(absPath) {
  writeFile(absPath, '');
}

// ---------------------------------------------------------------------------
// Templates
// ---------------------------------------------------------------------------

function genPom(ctx) {
  const deps = [];

  deps.push(`        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-autoconfigure</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-configuration-processor</artifactId>
            <optional>true</optional>
        </dependency>`);

  if (ctx.needAop) {
    deps.push(`        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-aop</artifactId>
        </dependency>`);
  }

  if (ctx.needRedis) {
    deps.push(`        <dependency>
            <groupId>${ctx.groupId}</groupId>
            <artifactId>nhai-infra-boot-starter-multipleredis</artifactId>
        </dependency>`);
  }

  deps.push(`        <dependency>
            <groupId>${ctx.groupId}</groupId>
            <artifactId>nhai-infra-utils</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>`);

  return `<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>${ctx.groupId}</groupId>
        <artifactId>nhai-infra-starters</artifactId>
        <version>\${revision}</version>
    </parent>

    <artifactId>${ctx.artifactId}</artifactId>
    <packaging>jar</packaging>

    <properties>
        <maven.compiler.source>${ctx.javaVersion}</maven.compiler.source>
        <maven.compiler.target>${ctx.javaVersion}</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <dependencies>
${deps.join('\n')}
    </dependencies>
</project>
`;
}

function genProperties(ctx) {
  return `package ${ctx.pkg}.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * ${ctx.desc}
 */
@ConfigurationProperties(prefix = "nhai.${ctx.nameCamel}")
public class ${ctx.Name}Properties {

    /** 是否启用 */
    private boolean enabled = true;

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }
}
`;
}

function genAutoConfiguration(ctx) {
  const imports = [
    `import ${ctx.pkg}.config.${ctx.Name}Properties;`,
    'import org.slf4j.Logger;',
    'import org.slf4j.LoggerFactory;',
    'import org.springframework.boot.autoconfigure.AutoConfiguration;',
    'import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;',
    'import org.springframework.boot.context.properties.EnableConfigurationProperties;',
  ];

  const annotations = [
    '@AutoConfiguration',
    `@ConditionalOnProperty(prefix = "nhai.${ctx.nameCamel}", name = "enabled", havingValue = "true", matchIfMissing = true)`,
    `@EnableConfigurationProperties(${ctx.Name}Properties.class)`,
  ];

  const beans = [];

  if (ctx.needRedis) {
    imports.push('import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;');
    imports.push('import org.springframework.boot.autoconfigure.data.redis.RedisAutoConfiguration;');
    imports.push('import org.springframework.data.redis.core.RedisTemplate;');
    annotations[0] = '@AutoConfiguration(after = RedisAutoConfiguration.class)';
    annotations.splice(1, 0, '@ConditionalOnClass(RedisTemplate.class)');
  }

  if (ctx.needAop) {
    imports.push(`import ${ctx.pkg}.aspect.${ctx.Name}Aspect;`);
    imports.push('import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;');
    imports.push('import org.springframework.context.annotation.Bean;');
    beans.push(`
    @Bean
    @ConditionalOnMissingBean
    public ${ctx.Name}Aspect ${ctx.nameCamel}Aspect() {
        log.info("注册 ${ctx.Name} 切面");
        return new ${ctx.Name}Aspect();
    }`);
  }

  return `package ${ctx.pkg}.autoconfigure;

${imports.join('\n')}

/**
 * ${ctx.desc} 自动配置
 */
${annotations.join('\n')}
public class ${ctx.Name}AutoConfiguration {

    private static final Logger log = LoggerFactory.getLogger(${ctx.Name}AutoConfiguration.class);

    public ${ctx.Name}AutoConfiguration() {
        log.info("Nhai ${ctx.Name} Starter 自动配置已加载");
    }
${beans.join('\n')}
}
`;
}

function genAnnotation(ctx) {
  return `package ${ctx.pkg}.annotations;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * ${ctx.desc} 注解
 *
 * <p>标注在方法上，由 {@link ${ctx.pkg}.aspect.${ctx.Name}Aspect} 拦截处理。</p>
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface ${ctx.Name} {
}
`;
}

function genAspect(ctx) {
  return `package ${ctx.pkg}.aspect;

import ${ctx.pkg}.annotations.${ctx.Name};
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/**
 * ${ctx.desc} 切面
 */
@Aspect
@Component
public class ${ctx.Name}Aspect {

    private static final Logger log = LoggerFactory.getLogger(${ctx.Name}Aspect.class);

    @Around("@annotation(${ctx.nameCamel}Annotation)")
    public Object around(ProceedingJoinPoint joinPoint, ${ctx.Name} ${ctx.nameCamel}Annotation) throws Throwable {
        log.debug("${ctx.Name} 切面拦截: {}", joinPoint.getSignature().toShortString());
        // TODO: 实现切面逻辑
        return joinPoint.proceed();
    }
}
`;
}

function genException(ctx) {
  return `package ${ctx.pkg}.exception;

/**
 * ${ctx.desc} 异常
 */
public class ${ctx.Name}Exception extends RuntimeException {

    private static final long serialVersionUID = 1L;

    public ${ctx.Name}Exception(String message) {
        super(message);
    }

    public ${ctx.Name}Exception(String message, Throwable cause) {
        super(message, cause);
    }
}
`;
}

function genUtils(ctx) {
  return `package ${ctx.pkg}.utils;

/**
 * ${ctx.desc} 工具类
 */
public final class ${ctx.Name}Utils {

    private ${ctx.Name}Utils() {
    }

    // TODO: 添加工具方法
}
`;
}

function genSpringFactories(ctx) {
  return `org.springframework.boot.autoconfigure.EnableAutoConfiguration=\\
  ${ctx.pkg}.autoconfigure.${ctx.Name}AutoConfiguration
`;
}

function genAutoConfigurationImports(ctx) {
  return `${ctx.pkg}.autoconfigure.${ctx.Name}AutoConfiguration
`;
}

function genLua(ctx) {
  return `-- ${ctx.desc}
-- 脚本名称: ${ctx.nameCamel}.lua
-- TODO: 实现 Lua 脚本逻辑

return 1
`;
}

function genTest(ctx) {
  return `package ${ctx.pkg}.autoconfigure;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(classes = ${ctx.Name}AutoConfiguration.class)
class ${ctx.Name}AutoConfigurationTest {

    @Test
    void contextLoads() {
    }
}
`;
}

function genReadme(ctx) {
  const features = [
    '- 自动配置，引入依赖即可使用',
    `- 可通过 \`nhai.${ctx.nameCamel}.enabled\` 开关（默认 true）`,
  ];
  if (ctx.needAop) features.push('- 注解式接入，基于 AOP 拦截');
  if (ctx.needRedis) features.push('- 基于 Redis 实现');
  if (ctx.needLua) features.push('- 内置 Lua 脚本支持');

  let usageSection = '引入依赖并开启配置后，Starter 将自动生效。';
  if (ctx.needAop) {
    usageSection = `\`\`\`java
@Service
public class DemoService {

    @${ctx.Name}
    public void doSomething() {
        // 业务逻辑
    }
}
\`\`\``;
  }

  let redisConfig = '';
  if (ctx.needRedis) {
    redisConfig = `
\`\`\`yaml
spring:
  redis:
    host: localhost
    port: 6379
\`\`\`
`;
  }

  const dirLines = [
    `- \`autoconfigure/\` — 自动配置类`,
    `- \`config/\` — 配置属性 \`${ctx.Name}Properties\``,
    `- \`exception/\` — 业务异常 \`${ctx.Name}Exception\``,
    `- \`utils/\` — 工具类 \`${ctx.Name}Utils\``,
  ];
  if (ctx.needAop) {
    dirLines.push(`- \`annotations/\` — 注解 \`@${ctx.Name}\``);
    dirLines.push(`- \`aspect/\` — AOP 切面 \`${ctx.Name}Aspect\``);
  }
  if (ctx.needLua) {
    dirLines.push(`- \`resources/lua/\` — Lua 脚本 \`${ctx.nameCamel}.lua\``);
  }

  return `# ${ctx.desc}

## 特性

${features.join('\n')}

## 快速开始

### 1. 添加依赖

\`\`\`xml
<dependency>
    <groupId>${ctx.groupId}</groupId>
    <artifactId>${ctx.artifactId}</artifactId>
</dependency>
\`\`\`

### 2. 配置

\`\`\`yaml
nhai:
  ${ctx.nameCamel}:
    enabled: true
\`\`\`
${redisConfig}
### 3. 使用

${usageSection}

## 配置项

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| \`nhai.${ctx.nameCamel}.enabled\` | boolean | \`true\` | 是否启用 |

## 目录结构

\`\`\`
${ctx.artifactId}/
├── autoconfigure/     自动配置
├── config/            配置属性
├── exception/         异常定义
├── utils/             工具类${ctx.needAop ? '\n├── annotations/       注解定义\n├── aspect/            AOP 切面' : ''}${ctx.needLua ? '\n└── resources/lua/     Lua 脚本' : ''}
\`\`\`

${dirLines.join('\n')}
`;
}

// ---------------------------------------------------------------------------
// Scaffold
// ---------------------------------------------------------------------------

function scaffold(ctx) {
  const root = join(ctx.outputDir, ctx.moduleDir);
  const javaBase = join(root, 'src', 'main', 'java', ...ctx.packagePath.split('/'));
  const testBase = join(root, 'src', 'test', 'java', ...ctx.packagePath.split('/'));
  const resBase = join(root, 'src', 'main', 'resources');

  writeFile(join(root, 'pom.xml'), genPom(ctx));
  writeFile(join(root, 'README.md'), genReadme(ctx));

  writeFile(join(javaBase, 'config', `${ctx.Name}Properties.java`), genProperties(ctx));
  writeFile(join(javaBase, 'autoconfigure', `${ctx.Name}AutoConfiguration.java`), genAutoConfiguration(ctx));
  writeFile(join(javaBase, 'exception', `${ctx.Name}Exception.java`), genException(ctx));
  writeFile(join(javaBase, 'utils', `${ctx.Name}Utils.java`), genUtils(ctx));

  if (ctx.needAop) {
    writeFile(join(javaBase, 'annotations', `${ctx.Name}.java`), genAnnotation(ctx));
    writeFile(join(javaBase, 'aspect', `${ctx.Name}Aspect.java`), genAspect(ctx));
  } else {
    writeGitkeep(join(javaBase, 'annotations', '.gitkeep'));
  }

  if (ctx.boot === '2.x' || ctx.boot === 'both') {
    writeFile(join(resBase, 'META-INF', 'spring.factories'), genSpringFactories(ctx));
  }

  if (ctx.boot === '3.x' || ctx.boot === 'both') {
    writeFile(
      join(
        resBase,
        'META-INF',
        'spring',
        'org.springframework.boot.autoconfigure.AutoConfiguration.imports',
      ),
      genAutoConfigurationImports(ctx),
    );
  }

  if (ctx.needLua) {
    writeFile(join(resBase, 'lua', `${ctx.nameCamel}.lua`), genLua(ctx));
  }

  writeFile(
    join(testBase, 'autoconfigure', `${ctx.Name}AutoConfigurationTest.java`),
    genTest(ctx),
  );
}

// ---------------------------------------------------------------------------
// Report
// ---------------------------------------------------------------------------

function buildTree(files, rootDir) {
  const tree = {};
  for (const file of files) {
    const rel = relative(rootDir, file).split(sep).join('/');
    let node = tree;
    const parts = rel.split('/');
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (i === parts.length - 1) {
        if (!node.__files) node.__files = [];
        node.__files.push(part);
      } else {
        if (!node[part]) node[part] = {};
        node = node[part];
      }
    }
  }

  const lines = [];
  function walk(node, prefix) {
    const dirs = Object.keys(node).filter((k) => k !== '__files').sort();
    const fileList = (node.__files || []).sort();

    dirs.forEach((dir, idx) => {
      const isLast = idx === dirs.length - 1 && fileList.length === 0;
      lines.push(`${prefix}${isLast ? '└── ' : '├── '}${dir}/`);
      walk(node[dir], prefix + (isLast ? '    ' : '│   '));
    });

    fileList.forEach((file, idx) => {
      const isLast = idx === fileList.length - 1;
      lines.push(`${prefix}${isLast ? '└── ' : '├── '}${file}`);
    });
  }

  walk(tree, '');
  return lines.join('\n');
}

function printReport(ctx) {
  const root = join(ctx.outputDir, ctx.moduleDir);
  console.log('\n✅ Spring Boot Starter 骨架生成完成\n');
  console.log('参数摘要:');
  console.log(`  模块名称:   ${ctx.moduleDir}`);
  console.log(`  描述:       ${ctx.desc}`);
  console.log(`  包名:       ${ctx.pkg}`);
  console.log(`  Boot 版本:  ${ctx.boot}`);
  console.log(`  AOP:        ${ctx.needAop}`);
  console.log(`  Redis:      ${ctx.needRedis}`);
  console.log(`  Lua:        ${ctx.needLua}`);
  console.log(`  输出目录:   ${root}`);
  console.log(`\n生成文件数: ${createdFiles.length}\n`);
  console.log('目录结构:');
  console.log(`${ctx.moduleDir}/`);
  console.log(buildTree(createdFiles, ctx.outputDir));
  console.log('\n下一步: 在 nhai-infra-starters/pom.xml 的 <modules> 中注册该模块，然后执行 mvn compile 验证。');
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  const raw = parseArgs(process.argv);
  const opts = resolveOptions(raw);
  const ctx = buildContext(opts);

  if (existsSync(join(ctx.outputDir, ctx.moduleDir))) {
    console.error(`错误: 目标目录已存在: ${join(ctx.outputDir, ctx.moduleDir)}`);
    process.exit(1);
  }

  scaffold(ctx);
  printReport(ctx);
}

main();
