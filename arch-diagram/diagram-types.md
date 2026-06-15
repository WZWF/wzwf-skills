# 各图类型生成要点

## Step 4 确认话术（用户未明确时）

```
已扫描项目：[项目名]
- 模块数：N | Java 类数：M
- 检测到层次：Controller(x) Service(y) Repository(z) ...

请选择：
1. 图类型：分层架构 / 模块依赖 / 核心流程 / 类关系
2. 输出格式：draw.io / HTML / 两者都要
3. （流程图）入口类或业务场景（如「分布式锁加锁流程」）
4. 输出路径（默认：docs/arch-diagram/）
```

## 分层架构图（layered）

```
┌─────────────────────────────────────┐
│  Controller  (XxxController)        │
├─────────────────────────────────────┤
│  Service     (XxxService / Impl)    │
├─────────────────────────────────────┤
│  Repository  (XxxMapper / Dao)      │
├─────────────────────────────────────┤
│  Infrastructure (Redis/Lock/Client) │
└─────────────────────────────────────┘
         ↓ 依赖方向向下
```

- 每层列出代表性类名（不超过 5 个/层，超出显示 `+N more`）
- 跨层箭头：上层指向下层被注入的类

## 模块依赖图（module-deps）

- 节点 = Maven 模块（artifactId）
- 箭头 = `<dependency>` 方向（A 依赖 B → A → B）
- Spring Bean 跨模块注入用虚线箭头标注
- Starter 项目突出 `*-autoconfigure` → `*-core` 关系

## 核心流程图（flow）

- 起点：用户指定或自动选 `@RestController` 第一个 public 方法
- 节点形状：处理步骤=圆角矩形，判断=菱形，结束=双边框
- 标注注解触发点（如 `@DistributedLock`、`@Transactional`）
- AOP 拦截作为并行支路展示

## 类关系图（class-relation）

- 只展示核心抽象（接口 + 实现 + 关键父类），控制在 15 个节点内
- 关系类型：`──▷` 继承、`──▷` 实现（虚线）、`──>` 依赖
- 不展开 Lombok 生成的方法

## 输出目录与交付

默认输出到 `docs/arch-diagram/`（不存在则创建）。

交付时告知用户：
1. 文件路径与图类型说明
2. draw.io 文件如何用 diagrams.net / VS Code draw.io 插件打开
3. HTML 文件直接浏览器打开即可
4. 采样/省略说明（若有）

**示例交付话术**：

```
已生成架构图：
- docs/arch-diagram/nhai-lock-layered-20260615.drawio（分层架构，可编辑）
- docs/arch-diagram/nhai-lock-layered.html（浏览器预览，悬浮可看方法）

说明：Service 层共 12 个类，图中展示 4 个核心类 + "+8 more"。
```

## 注意事项

1. **控制复杂度**：单图节点不超过 25 个；超出时分模块出多张图
2. **不臆造关系**：只画能从代码中确认的依赖，不确定的用虚线 + 注释
3. **敏感信息**：类名/方法名来自源码，提醒用户分享前检查
4. **Monorepo**：用户可能在子模块目录启动，需向上找到父 pom 或询问范围
5. **无 Spring 项目**：降级为包结构图，不强行套分层模型

## 快速示例

**用户**：「帮我画一下这个 lock starter 的分层架构图，要 HTML 的」

**Agent 动作**：
1. 读取 pom.xml → 识别 `nhai-infra-boot-starter-lock` 模块
2. Grep `@RestController|@Service|@Aspect|@Configuration` → 分类
3. Grep 构造函数注入 → 建依赖边
4. 生成 `docs/arch-diagram/nhai-lock-layered.html`
5. 告知用户打开路径

**用户**：「画模块依赖，draw.io 和 HTML 都要」

**Agent 动作**：Step 1-3 聚焦 Maven `<modules>` 和跨模块 `<dependency>` → 双格式输出。
