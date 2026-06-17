---
name: content-fact-check
description: >-
  验证文稿、演讲稿、技术文档中引用的事实、数据、来源的正确性，生成结构化参考文献。
  当用户提到事实核查、资料验证、引用检查、参考文献、来源验证、正确性验证、
  数据溯源、论文验证、GitHub 仓库验证时使用。
  适用于演讲准备、技术分享、对外发布等对内容准确性有高要求的场景。
compatibility: Python 3.10+. 需要网络访问（GitHub API、WebSearch）。可选 GITHUB_TOKEN 环境变量避免限速。
---

# 内容事实核查

对文稿中的声明、引用、数据进行系统性验证，确保对外发布内容的可靠性。

## 核心原则

- **每个声明都需要来源**：无法找到可靠来源的声明，标注为"无法验证"而非默认正确
- **优先一手来源**：arxiv 论文 > 官方文档 > 技术博客 > 新闻报道
- **时效性敏感**：技术领域的数据（star 数、版本号、市场份额）会快速过时，标注验证日期
- **区分事实与观点**：明确标注哪些是事实、哪些是推测或个人观点

## 工作流

```
文稿 → [提取声明] → [分类] → [逐项验证] → [标注结果] → references.md
```

### Phase 1: 声明提取

从文稿中提取所有需要验证的声明，分为五类：

| 类别 | 示例 | 验证方式 |
|------|------|---------|
| 学术论文 | "arxiv 上的 AHE 论文" | arxiv 搜索/WebFetch |
| 人物归属 | "Andrew Ng 提出..." | 官方 profile + 原始出处 |
| 数据指标 | "151k+ stars" | GitHub API / 脚本验证 |
| 术语定义 | "Skill 是开放标准" | 官方文档 + 权威来源 |
| 技术事实 | "被 30+ 产品支持" | 聚合多个来源交叉验证 |

### Phase 2: 分类验证

按类别使用对应的验证方法：

**学术论文**：
1. 在 arxiv 搜索论文 ID（如 `2604.25850`）
2. 核对：标题、作者、发表日期、关键结论
3. 注意区分论文实际结论 vs 文稿中的引用是否准确

**人物归属**：
1. 确认人物的正确头衔/职位（随时间变化）
2. 找到原始出处（推文、论文、演讲）
3. 确认引述的准确性——是原话还是转述

**GitHub 仓库**：
1. 使用配套脚本 `verify-github-repos.py` 批量检查
2. 核对：仓库是否存在、star 数级别、描述是否匹配
3. star 数用区间（如 "151k+"）而非精确值，避免过时

**术语定义**：
1. 找到术语的权威定义来源
2. 确认文稿中的定义与权威来源一致
3. 注意：技术术语可能有多个流派定义

**技术事实**：
1. 需要至少两个独立来源交叉验证
2. 优先使用官方来源或权威技术媒体

### Phase 3: 标注结果

对每个声明标注三种状态之一：

```
✅ 已验证 — 找到可靠来源，事实准确
⚠️ 部分准确 — 核心事实正确但细节需调整
❌ 需修正 — 事实有误或无法找到来源
```

### Phase 4: 生成 references.md

输出结构化参考文献，模板：

```markdown
# 参考文献

## 1. [声明主题]

**来源**：[URL 或引用]

> [原文引述]

**讲稿中使用**：Slide X（用途说明）

---
```

## 配套脚本

**verify-github-repos.py**：批量验证 GitHub 仓库的存在性和 star 数。

```bash
python scripts/verify-github-repos.py repos.txt
# 输入格式（每行一个）: owner/repo
# 输出：仓库名、实际 star 数、描述、是否存在
```

详细验证方法和检查清单 → 读 [reference.md](reference.md)

## 跨 IDE 兼容性

本 Skill 遵循 [Agent Skills 开放标准](https://agentskills.io/specification)，可在 Cursor、Claude Code、GitHub Copilot、Gemini CLI 等 32+ AI 工具中使用。

| 使用场景 | 放置路径 |
|---------|---------|
| 个人级（Cursor） | `~/.cursor/skills/content-fact-check/` |
| 个人级（Claude Code） | `~/.claude/skills/content-fact-check/` |
| 项目级（跨 IDE 推荐） | `.agents/skills/content-fact-check/` |
