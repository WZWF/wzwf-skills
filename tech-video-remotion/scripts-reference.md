# 脚本详细说明

本 Skill 的 4 个自动化脚本位于 `scripts/` 目录下。

## init-remotion-project.mjs

一键创建完整项目骨架。自动生成：
- Remotion 项目 (package.json, tsconfig, 入口文件)
- 4 个动画基础组件 (CinematicBg, FadeSlide, GlowBox, DrawLine)
- Subtitle 组件 + 设计令牌 + 类型定义
- react-compat.d.ts 兼容补丁
- Video.tsx 模板（含 FallbackScene，AI 填充后替换）
- generate-audio-with-subs.py（如果传入 voiceover-clean.txt 自动解析场景文案）
- setup-assets.mjs 资产拷贝脚本

```bash
# 基础用法
node init-remotion-project.mjs my-video

# 传入旁白文稿自动提取场景（文稿格式: ## Scene 01: 标题\n正文）
node init-remotion-project.mjs my-video voiceover-clean.txt
```

## generate-subs-ts.mjs

从 `subs/*.json` 自动生成 Remotion 可用的 `subs.ts`：
- 自动推断 sceneId（scene1-xxx.json → scene01）
- 同时复制 JSON 到 `src/data/subs/` 目录
- 输出统计（每个场景多少条字幕）

```bash
node generate-subs-ts.mjs ../subs src/data/subs.ts
```

## generate-timeline-ts.mjs

根据实际 MP3 文件大小/时长自动更新 `timeline.ts` 的 `duration` 字段：
- 优先使用 Python `mutagen` 精确测量，回退到 CBR 估算
- duration = ceil(实际时长) + 3 秒缓冲
- 如果 timeline.ts 已存在则原地更新，否则从零生成

```bash
node generate-timeline-ts.mjs ../audio src/data/timeline.ts
```

## validate-project.mjs

一键校验 7 类常见问题：

| 检查项 | 错误/警告 | 说明 |
|--------|----------|------|
| **字幕-场景映射** | **Error** | **字幕 JSON 个数/ID 与 timeline 不匹配** |
| 空字幕文件 | Error | JSON 为空或解析失败 |
| 字幕重叠 | Error | 相邻字幕 end > next.start |
| 孤立标点 | Warning | 纯标点字幕应合并 |
| 时长截断 | Error | duration < 实际音频时长 |
| 时长过长 | Warning | duration 比音频多 10s+ |
| fadeOut 不安全 | Error | 未使用 Math.min 钳制 |
| 锁文件冲突 | Error | package-lock + pnpm-lock 共存 |

```bash
node validate-project.mjs .  # 在 remotion-video 目录下运行
```
