# 能力二：匪夷所思代码解释器

对看不懂的代码段进行证据链推理，还原写法背后的可能原因。

## 输入

- 一段看不懂的代码（带行号），或整个文件 + 「哪里奇怪」的说明

## 分析步骤

1. **Blame 定位**：对可疑行执行 `git blame -L <start>,<end> --line-porcelain`
2. **Commit 上下文**：`git show <commit>` 看完整 diff，不仅看单行
3. **同期关联**：`git log --since=<date-7d> --until=<date+7d> --oneline -- <file>` 及同目录文件
4. **防御性模式识别**（Java 常见）：
   - 空 catch / 吞异常 → 可能是上线救火
   - 重复 null 检查 → 历史 NPE 修复
   - 魔法数字 / 硬编码 → 临时方案未清理
   - `synchronized` / 双重检查 → 并发 bug 补丁
   - 废弃 API 仍使用 → 兼容性约束
   - 过度抽象或完全不抽象 → 不同作者风格叠加
5. **Issue/PR 引用**：在 commit message、注释、代码中搜索 `#123`、`JIRA-xxx`、`fixes`、`reverts`
6. **调用链上下文**：SemanticSearch / Grep 查谁调用、何时调用

> Git 命令详见 [git-commands.md](git-commands.md)。

## 输出模板

````markdown
# 代码解读：<位置描述>

## 可疑代码
```java
<原样引用>
```

## 证据链

| # | 证据 | 来源 |
|---|------|------|
| 1 | <事实> | `git blame` L42 → commit abc123 |
| 2 | <事实> | commit message: "fix NPE when..." |
| 3 | <事实> | 同期 commit def456 修改了同模块 |

## 可能原因（按置信度排序）

### 🟢 高置信度 — <原因标题>
<推理过程，引用证据 #>

### 🟡 中等置信度 — <原因标题>
<推理过程>

### 🔴 低置信度 — <原因标题>
<推理过程，标注缺乏直接证据>

## 改进建议（可选）
- <若确认是 workaround，建议如何正规化>
- <若缺注释，建议补什么>

> ⚠️ 以上为基于 Git 历史的推理，非作者原话。如需确认，建议联系 <主要作者>。
````

---

## Java 后端考古提示

- **Spring 注解突变**（如 `@Transactional` 加/删）→ 查同期是否有数据一致性 bug
- **DTO/Entity 字段增减** → 对照 DB migration 或 MyBatis XML 变更
- **ThreadLocal / 上下文传递** → 常见于异步改造或请求链路追踪
- **if-else 嵌套过深** → 可能是多次 hotfix 叠床架屋，blame 按行看每次加了哪层
- **@Deprecated 但仍调用** → 查谁还在用，可能是迁移进行中

---

## 注意事项

1. **必须执行命令**：不要凭猜测编造 commit 信息，所有 hash、日期、作者从 git 输出获取
2. **区分事实与推理**：commit message 和 diff 是事实；「为什么这样写」是推理，用置信度标注
3. **重命名追踪**：Java 重构常 rename，务必加 `--follow`
4. **merge commit**：信息量少时看 `--first-parent` 或进入 feature 分支查
5. **大文件**：超过 500 行历史时，优先分析 Top 10 关键 commit，避免全量 diff
6. **无 message 的 commit**：从 diff 内容推断，标注「message 缺失，从 diff 推断」

## 示例触发语

- 「帮我考古一下 `OrderService.java`」
- 「这段代码为什么这么写？」（选中代码）
- 「这个类是谁写的、改过什么」
- 「git blame 一下第 120-135 行，看能不能还原原因」
- 「我半年前写的 XXX，忘了为什么这样设计」
