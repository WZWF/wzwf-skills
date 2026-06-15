# 问题排查与音画同步

## 字幕数据校验

生成字幕后必须运行校验，确保无时间重叠：

```javascript
// node -e "...（见下方完整脚本）..."
const sceneRegex = /(\w+):\s*\[([\s\S]*?)\]/g;
let match;
while ((match = sceneRegex.exec(content)) !== null) {
  const entries = [];
  const entryRegex = /start:\s*([\d.]+),\s*end:\s*([\d.]+)/g;
  let em;
  while ((em = entryRegex.exec(match[2])) !== null) {
    entries.push({ start: parseFloat(em[1]), end: parseFloat(em[2]) });
  }
  for (let i = 0; i < entries.length - 1; i++) {
    if (entries[i].end > entries[i + 1].start) {
      console.log(`OVERLAP in ${match[1]}: ${entries[i].end} > ${entries[i + 1].start}`);
    }
  }
}
```

## 音画同步要点

| 问题 | 原因 | 解决 |
|------|------|------|
| 画面持续跳动 | GlowBox 的 sin() 脉冲叠加 | GlowBox 不做 scale 动画 |
| 场景切换时粒子跳切 | 不同场景用了不同 seed | 所有场景统一 seed={42} |
| 模块提前弹出 | delaySec 没对齐字幕 | 按字幕 start 时间写 delaySec |
| 字幕比声音晚 | Audio 组件播放延迟 | Subtitle 加 offsetSec={-0.15} |
| 字幕闪烁 | 标点符号单独成条 | 合并纯标点条目到前一条 |

## 技术栈

- **动画框架**: Remotion (React视频) + spring/interpolate
- **音频**: Edge TTS (zh-CN-YunxiNeural)
- **字幕**: Edge TTS SentenceBoundary 事件
- **图形**: 纯 React + CSS + 内联 SVG（零外部设计工具）
- **画面**: 1920×1080, 30fps
- **自动化**: Node.js 脚本 (init / subs / timeline / validate)
