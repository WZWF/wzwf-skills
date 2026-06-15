# 内容创作与音频生成（Step 1-2）

## Step 1: 内容创作

1. **分镜脚本** — 分析项目源码+文档，输出 `video-storyboard.md`
   - 结构：痛点→核心思想→架构→核心设计→使用方式→总结
   - 每个Scene包含：旁白文字、视觉描述、动画编排

2. **旁白文稿** — 精炼为口语化 `voiceover-clean.txt`

3. **时间轴** — 定义 `timeline.json`
   ```json
   {
     "scenes": [{
       "id": "scene01",
       "audio": "audio/scene1-xxx.mp3",
       "duration": 47,
       "animation": [
         { "type": "enter", "target": "xxx", "startSec": 3, "durationSec": 0.5 }
       ]
     }]
   }
   ```
   - `duration` 必须 ≥ 实际音频时长 + 3秒缓冲
   - 用 `mutagen` 库精确测量 MP3 时长

## Step 2: 音频+字幕生成

使用 Edge TTS 的 `SentenceBoundary` 事件获取精确时间戳：

```python
async for chunk in comm.stream():
    if chunk["type"] == "SentenceBoundary":
        start = chunk["offset"] / 10_000_000  # 100ns ticks → seconds
        dur = chunk["duration"] / 10_000_000
        subs.append({"text": chunk["text"], "start": start, "end": start + dur})
```

长句按逗号拆分（每条≤20字），按字符比例分配时间。

输出：`audio/*.mp3` + `subs/*.json`
