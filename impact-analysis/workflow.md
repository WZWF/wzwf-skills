# Impact Analysis — 完整工作流

## Phase 1: 侦察（Scout）

### Step 1.1: 确认分析目标

从用户输入中提取：

**类/方法级分析**：
- **目标类名**：如 `LockUtils`
- **目标方法名**（可选）：如 `tryLock`
- **变更描述**（可选）：用户打算改什么

**字段级分析**（加字段/删字段/改字段）：
- **Entity 类名**：如 `User`
- **字段名**：如 `email`
- 或 **表名.字段名**：如 `user.email`

### Step 1.2: 定位项目根目录

找到包含 `pom.xml` 或 `build.gradle` 的最近祖先目录作为项目根。
如果是多模块项目，使用顶层根目录以覆盖跨模块调用。

### Step 1.3: 运行扫描脚本

**类/方法级分析**：
```bash
python "<SKILL_DIR>/scripts/impact-scanner.py" "<PROJECT_ROOT>" \
  --target "ClassName.methodName" \
  --depth 3 \
  -o impact-map.json
```

**字段级分析**：
```bash
python "<SKILL_DIR>/scripts/field-impact-scanner.py" "<PROJECT_ROOT>" \
  --target "User.email" \
  -o field-impact.json
```

等待脚本完成，检查 stderr 输出的摘要信息。

### Step 1.4: 读取地图 JSON

**类/方法级分析** — 读取 `impact-map.json`：
- `risk_assessment.level` → 整体风险等级
- `risk_assessment.factors` → 风险因素列表
- `call_graph.callers` → 谁调用了目标
- `call_graph.callees` → 目标调用了谁
- `spring_deps` → Spring 隐式依赖
- `cycles` → 循环调用

**字段级分析** — 读取 `field-impact.json`：
- `target` → 目标字段信息
- `entities` → 涉及的 Entity 类和字段定义
- `sql_refs` → MyBatis XML 中的 SQL 引用
- `mapper_methods` → Mapper 方法
- `call_chain` → Mapper → Service → Controller 调用链

---

## Phase 2: 定位（Locate）

基于地图 JSON，逐维度判定风险级别。

### 判定规则

| 维度 | 低风险 | 中风险 | 高风险 |
|------|--------|--------|--------|
| 调用者数量 | ≤3 | 4-10 | >10 |
| AOP 切面 | 0 | 1 | >1 |
| 事务边界 | 无 @Transactional | 有，REQUIRED | 有，REQUIRES_NEW 或嵌套 |
| 循环调用 | 0 | — | >0 |
| 缓存操作 | 0 | @Cacheable | @CacheEvict（影响一致性） |
| 异步标记 | 无 | @Async | @Async + 事务 |

### 标记需要深入的文件

从 `compressed_views` 中筛选需要 Phase 3 深入分析的类：
- 标记为**高风险**的调用者
- 涉及 AOP/事务/缓存的类
- `suggest_read_lines` 指示的行范围

---

## Phase 3: 深潜（Dive）

对每个高风险文件，只读取 `suggest_read_lines` 指示的行范围，分析：

### 3.1 调用者分析
- 调用者传入了什么参数？
- 是否依赖目标方法的返回值做分支判断？
- 调用者的异常处理是否覆盖了目标方法可能的异常？

### 3.2 事务分析（如有）
- 事务传播级别是什么？
- 改动是否可能导致事务回滚范围变化？
- 是否有跨方法的事务依赖？

### 3.3 AOP 分析（如有）
- 切面是否修改了方法的入参或返回值？
- 切面的执行顺序（@Order）是否影响行为？

### 3.4 每分析完一个维度，将发现追加到报告文件

---

## Phase 4: 汇总（Report）

读取所有阶段的发现，生成最终报告。

→ 报告格式参考 [templates.md](templates.md)

**下一步**：阅读 [templates.md](templates.md) 了解输出格式。
