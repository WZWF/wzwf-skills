# CLAUDE.md

## 文本长度约束

**重要**：输出文本时必须分段处理，避免一次性输出过长内容导致截断。

规则：
- 单次输出不超过 500 字
- 长内容分多次输出，每次用 Edit/Write 工具追加
- 代码实现分步骤进行，每步完成后确认再继续
- 计划文件分段写入，不要一次性写完

## 项目概述

这是一套面向 Java/Spring Boot 开发者的 Skills 工具集，包含：
- api-doc-gen: API 文档生成
- arch-diagram: 架构图生成
- code-archaeology: 代码考古
- content-fact-check: 内容事实核查
- database-operations: 数据库操作
- document-reader: 文档读取
- impact-analysis: 变更影响分析
- interview-prep: 面试题生成
- resume-project: 简历项目提炼
- starter-scaffold: Starter 脚手架
- tech-video-remotion: 技术视频制作

## 代码规范

- Python 脚本使用 3.10+ 语法
- Node.js 脚本使用 ESM 模块
- 输出 JSON 使用 ensure_ascii=False 支持中文
- 日志输出到 stderr，结果输出到 stdout
