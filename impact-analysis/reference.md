# Impact Analysis — 参考手册

## 脚本参数

```
python impact-scanner.py <project> --target <target> [--depth N] [--output file.json]
```

| 参数 | 必选 | 说明 |
|------|------|------|
| `project` | 是 | Java 项目根目录（含 pom.xml） |
| `--target, -t` | 是 | 分析目标，格式: `ClassName` 或 `ClassName.methodName` |
| `--depth, -d` | 否 | 调用链最大追踪深度（默认 3，设 0 为不限制） |
| `--output, -o` | 否 | 输出 JSON 文件路径（默认 stdout） |

## 深度选择指南

| 深度 | 适用场景 | 地图体积 | 耗时 |
|------|----------|----------|------|
| 2 | 快速评估、小型工具类 | ~2KB | <5s |
| 3 | 默认推荐、大多数 Bug 修复 | ~5KB | <15s |
| 5 | 复杂微服务、跨模块调用链 | ~10KB | <30s |
| 0 (不限) | 极端排查、完整影响评估 | 10-50KB | <60s |

## 输出 JSON 结构

```
{
  "target": {                    // 分析目标信息
    "class", "method", "full_name", "file", "annotations"
  },
  "call_graph": {
    "callers": [...],            // 调用者列表（含 depth）
    "callees": [...]             // 被调用者列表
  },
  "spring_deps": {
    "aop": [...],                // AOP 切面匹配
    "event_listeners": [...],    // 事件监听
    "scheduled": [...],          // 定时任务
    "config": [...],             // 配置依赖
    "transaction": [...],        // 事务边界
    "cache": [...],              // 缓存操作
    "async": [...]               // 异步标记
  },
  "cycles": [...],               // 循环调用检测
  "compressed_views": [...],     // 相关类的压缩视图（签名+行号）
  "risk_assessment": {           // 风险评估
    "level", "factors", "dimensions_hit",
    "total_callers", "total_callees", ...
  }
}
```

## 七大分析维度

| # | 维度 | 检测方式 | 典型风险 |
|---|------|----------|----------|
| 1 | **调用链** | 脚本 BFS 遍历方法调用 | 改了底层方法，上游行为变化 |
| 2 | **AOP 切面** | 脚本匹配 @Aspect + pointcut | 切面隐式修改了方法行为 |
| 3 | **事件监听** | 脚本检测 publishEvent + @EventListener | 事件链路中断或行为变化 |
| 4 | **定时任务** | 脚本检测 @Scheduled 方法的调用目标 | 定时任务调用了被改动的方法 |
| 5 | **配置依赖** | 脚本提取 @Value/@ConditionalOn → 匹配 yml | 配置变更影响行为 |
| 6 | **事务边界** | 脚本检测 @Transactional 及传播级别 | 事务范围变化导致数据不一致 |
| 7 | **缓存操作** | 脚本检测 @Cacheable/@CacheEvict | 缓存一致性被破坏 |

## 环检测说明

脚本使用 BFS + visited 集合遍历调用图：
- 遇到已访问节点时检查是否形成环
- 同类方法重载互调（如 `tryLock(wait)` 调用 `tryLock()`）不标记为环
- 真正的循环依赖被标记为高风险

## 脚本限制

| 限制 | 说明 | 影响 |
|------|------|------|
| 基于正则，非完整 AST | 复杂泛型、Lambda 可能漏匹配 | 可能少报 ~5% 的调用 |
| 不解析运行时类型 | 接口多实现时取注入字段类型 | 可能误报接口调用 |
| 不模拟 AOP 代理行为 | pointcut 使用简化匹配 | 复杂 AspectJ 表达式可能漏匹配 |
| 不跨模块解析第三方库 | 只追踪项目内代码 | 框架内部调用链不可见 |
