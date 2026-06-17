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

### 中文 TTS 关键注意事项

**必须使用 `SentenceBoundary`，禁止使用 `WordBoundary`**：

- `WordBoundary` 对中文会逐字/逐词拆分，生成大量碎片字幕（每条 1-3 个字），完全不可用
- `SentenceBoundary` 按句子粒度切分，中文按标点断句，输出合理

```python
# 正确：
if chunk["type"] == "SentenceBoundary":

# 错误：中文场景禁止
if chunk["type"] == "WordBoundary":
```

### 单场景重生成工作流

只修改了部分场景的旁白时，无需全量重生成。推荐流程：

```bash
# 1. 只重生成指定场景（修改 generate-audio-with-subs.py 中的执行逻辑）
python -c "
import asyncio
# 只生成 scene03 和 scene11
scenes_to_regen = ['scene03', 'scene11']
# ... 调用 edge_tts 生成
"

# 2. 用 mutagen 测量新音频时长
python -c "
from mutagen.mp3 import MP3
import os
for f in ['audio/scene3-xxx.mp3', 'audio/scene11-xxx.mp3']:
    print(f'{f}: {MP3(f).info.length:.1f}s')
"

# 3. 手动更新 timeline.ts 中对应 scene 的 duration
# 4. 拷贝新文件到 public/
# 5. 验证
node $SKILL_DIR/scripts/validate-project.mjs .
```

### 变更传播清单

改旁白时必须同步更新的文件（详见 [troubleshooting.md](troubleshooting.md#跨文件变更一致性)）：

1. `presentation-script.md` → 2. `generate-audio-with-subs.py` → 3. `voiceover-clean.txt`
4. 运行脚本重生成 `subs/*.json` + `audio/*.mp3`
5. 更新 `timeline.ts` duration
6. 核对 `Scene*.tsx` delaySec
