---
name: tech-video-remotion
description: >-
  基于 Remotion 的全自动技术视频制作。从项目代码生成分镜→旁白→音频+字幕→React动画组件→视频。
  当用户提到技术视频、Remotion、视频制作、动画组件、分镜脚本、旁白、字幕生成、Edge TTS、
  视频渲染、场景动画时使用。适用于将开源项目/框架转化为技术介绍视频的完整流程。
  包含一套脚本工具链，可自动初始化项目、生成字幕/时间轴 TypeScript 文件、校验项目完整性。
author: czc
---

# 技术视频制作 (Remotion)

将开源项目代码和文档转化为专业技术介绍视频的全自动流程。

## 脚本工具链

本 Skill 附带 4 个自动化脚本，位于同目录 `scripts/` 下：

| 脚本 | 用途 | 可自动化的环节 |
|------|------|---------------|
| `init-remotion-project.mjs` | 一键创建 Remotion 项目骨架 | 目录结构 + 模板文件 + 动画组件 |
| `generate-subs-ts.mjs` | 从 subs/*.json 生成 subs.ts | 字幕数据的 TypeScript 封装 |
| `generate-timeline-ts.mjs` | 从实际 MP3 时长更新 timeline.ts | duration 字段精确对齐 |
| `validate-project.mjs` | 一键校验项目完整性 | 字幕重叠/时长匹配/fadeOut安全/锁文件 |

**快速开始（完整命令序列）**：

```bash
# 1. 初始化项目骨架（可选传入 voiceover-clean.txt 自动解析场景）
node scripts/init-remotion-project.mjs my-video voiceover-clean.txt

# 2. AI 生成旁白 → 手工调整 → 生成音频+字幕
cd my-video
python generate-audio-with-subs.py

# 3. 自动更新 timeline 时长
cd remotion-video
node scripts/generate-timeline-ts.mjs ../audio src/data/timeline.ts

# 4. 自动生成 subs.ts
node scripts/generate-subs-ts.mjs ../subs src/data/subs.ts

# 5. 拷贝资产到 public/
node scripts/setup-assets.mjs

# 6. AI 生成场景组件 → src/scenes/

# 7. 校验
node scripts/validate-project.mjs .

# 8. 预览
pnpm install && pnpm start
```

**人工 vs 自动化分界**：

| 步骤 | 方式 | 说明 |
|------|------|------|
| 分镜脚本 | AI 生成 | 需要理解项目代码 |
| 旁白文稿 | AI 生成 + 人工微调 | 口语化调整 |
| 音频+字幕 | **脚本自动** | `generate-audio-with-subs.py` |
| 项目骨架 | **脚本自动** | `init-remotion-project.mjs` |
| timeline.ts | **脚本自动** | `generate-timeline-ts.mjs` |
| subs.ts | **脚本自动** | `generate-subs-ts.mjs` |
| 场景组件 | AI 生成 | 每个场景的动画编排 |
| 资产拷贝 | **脚本自动** | `setup-assets.mjs` |
| 项目校验 | **脚本自动** | `validate-project.mjs` |

## 完整流程

```
项目代码 → [AI] 分镜脚本 → [AI] 旁白文稿 → [脚本] Edge TTS音频+字幕
                                                          ↓
                  [脚本] 项目骨架 → [脚本] timeline.ts + subs.ts
                                                          ↓
                              [AI] 场景组件 → [脚本] 校验 → 视频
```

## 详细指引（按需加载）

- Step 1-2 内容创作与音频生成 → 读 [content-workflow.md](content-workflow.md)
- Step 3-6 Remotion 项目结构、场景设计与运行 → 读 [scene-design.md](scene-design.md)
  - 注意：Step 3 开始前需先运行 `init-remotion-project.mjs` 创建骨架（见上方「快速开始」第 1 步）
- 4 个脚本详细说明 → 读 [scripts-reference.md](scripts-reference.md)
- 问题排查与音画同步 → 读 [troubleshooting.md](troubleshooting.md)
