# Git 命令参考

在 Shell 中执行，路径含空格时加引号。

## 关键节点识别

| 节点类型 | 识别方式 |
|----------|----------|
| 文件创建 | `git log --diff-filter=A` 最早 commit |
| 重大重构 | 单次 diff 变更行数 > 50 或删除+新增各 > 30 |
| 功能增量 | commit message 含 feat / add / 实现 / 新增 |
| Bug 修复 | commit message 含 fix / bug / 修复 / hotfix |
| 紧急补丁 | 时间间隔短 + message 含 revert / 临时 / workaround |

## 基础采集

```bash
# 完整历史（追踪重命名）
git log --follow --format="%H|%ai|%an|%s" -- <file>

# 简洁历史 + 变更行数
git log --follow --oneline --stat -- <file>

# 文件首次出现
git log --all --oneline --diff-filter=A -- <file>

# 贡献者统计
git shortlog -sn -- <file>
```

## Blame 分析

```bash
# 标准 blame（带行号）
git blame -L <start>,<end> -- <file>

# 机器可读格式（含 author-time、summary）
git blame --line-porcelain -L <start>,<end> -- <file>

# 忽略空白变更
git blame -w -L <start>,<end> -- <file>
```

## 深入查看

对每个关键节点执行 `git show <commit> --stat` 和 `git show <commit> -- <file>`，提取：

- **改了什么**：diff 摘要
- **为什么改**：commit message、关联 issue/PR
- **谁改的**：author、同一作者的其他近期 commit

```bash
# 某次 commit 的完整 diff
git show <commit> -- <file>

# 某历史时刻的文件内容
git show <commit>:<file>

# 两次 commit 之间该文件的差异
git diff <old-commit>..<new-commit> -- <file>

# 搜索 commit message 关键词
git log --all --grep="关键词" --oneline -- <file>

# 某作者在该文件的提交
git log --author="张三" --oneline -- <file>
```

## 按类名定位文件

```bash
# 在仓库根目录
git ls-files "**/*OrderService*.java"
```

## 重大变更快速筛选

```bash
# 带 numstat 便于找大 diff
git log --follow --numstat --format="%H|%ai|%an|%s" -- <file>
```
