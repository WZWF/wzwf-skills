---
name: code-archaeology
description: 追溯文件的 Git 演化历史生成代码传记时间线，并分析看似匪夷所思的代码写法背后的可能原因。当用户提到代码考古、代码历史、git blame、为什么这么写、看不懂这段代码、代码传记、代码演化、接手代码、遗留代码时使用。
author: czc
---

# 代码考古（Code Archaeology）

通过 Git 历史追溯代码演化脉络，还原设计决策；对「匪夷所思」的写法进行证据链推理，帮助 Java 后端开发者理解遗留代码。

## 何时使用

| 场景 | 能力 |
|------|------|
| 接手陌生模块、想了解文件/类的来龙去脉 | 能力一：代码传记 |
| 某段代码写法奇怪、注释缺失、不知为何存在 | 能力二：匪夷所思代码解释器 |
| 回顾自己半年前的代码，忘了设计初衷 | 两者结合 |
| 排查「这行代码是谁加的、为什么加」 | 能力二（从 git blame 切入） |

## 依赖与前置

| 工具 | 用途 | 必须 |
|------|------|------|
| Shell | 执行 git log / blame / show / diff | ✅ |
| Read | 读取目标文件源码 | ✅ |
| Grep | 按类名定位文件、搜索 issue/PR 引用 | ✅ |
| Glob | 按类名查找 `.java` 文件 | ✅ |
| SemanticSearch | 查找调用方、相关模块上下文 | 可选 |

**前置条件**：目标路径在 Git 仓库内且有提交历史；若无，改从源码静态分析 + 询问原作者。

## 总工作流程

```
Task Progress:
- [ ] Step 1: 确认目标文件/代码段
- [ ] Step 2: 运行 git log / blame 收集历史
- [ ] Step 3: 识别关键变更节点
- [ ] Step 4: 分析每个节点的 commit message + diff
- [ ] Step 5: 构建叙事时间线或推理解释
- [ ] Step 6: 输出 Markdown
```

### Step 1: 确认目标

- **文件路径** / **类名**（Glob `**/*ClassName*.java`，多个则询问）/ **代码段**（记录行号）
- 确认仓库根：`git rev-parse --show-toplevel`

### Step 2: 收集历史

按 [git-commands.md](git-commands.md) 并行基础采集，再深入 `git show`。

### Step 3: 识别关键节点

创建（`--diff-filter=A`）| 重大重构（diff > 50 行）| 功能（feat/add）| 修复（fix/bug）| 紧急补丁（revert/临时/workaround）

### Step 4–6: 分析与输出

对每个节点 `git show` 提取 diff、message、author；按用户意图选模板，**区分事实与推理**（message/diff 为事实，原因需证据链）。模板见下方指引。

## 详细指引（按需加载）

- 执行「代码传记」（追溯文件演化历史）→ 读 [biography.md](biography.md)
- 执行「匪夷所思代码解释」（理解奇怪写法）→ 读 [wtf-code.md](wtf-code.md)
- Git 命令参考 → 读 [git-commands.md](git-commands.md)
