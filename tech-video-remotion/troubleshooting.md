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
| **渲染后字幕抖动** | **见下方「预览正常但渲染抖动」** | **三处修复** |

---

## 预览正常但渲染抖动

**典型表现**：Studio 预览一切正常，`pnpm run build` 渲染导出的 MP4 中字幕出现位置跳动、闪烁。

**根因**：Remotion 渲染模式是**逐帧独立截图**，每帧之间没有浏览器上下文。预览是实时播放，浏览器有帧间状态。

### 必须修复的三个点

**1. 禁止 CSS transition**

Remotion 渲染时每帧独立，CSS `transition` 完全无效且会导致不确定行为。

```tsx
// 错误：渲染时每帧独立，transition 无意义
style={{ transition: "width 0.1s linear" }}

// 正确：用 interpolate() 基于帧计算
const width = interpolate(frame, [0, totalFrames], [0, 100], CLAMP);
style={{ width: `${width}%` }}
```

**全局规则**：在 Remotion 组件中搜索并移除所有 `transition` CSS 属性。所有动画必须通过 `useCurrentFrame()` + `interpolate()` 或 `spring()` 实现。

**2. 字幕容器必须固定布局**

文本内容切换时，如果容器尺寸跟随文本变化，会导致位置微跳。

```tsx
// 错误：flex 居中 + 自适应宽度 → 每帧重新布局
<div style={{ display: "flex", justifyContent: "center" }}>
  <span>{text}</span>
</div>

// 正确：固定容器 + text-align + min-height
<div style={{ textAlign: "center", minHeight: 52 }}>
  <span style={{ display: "inline-block" }}>{text}</span>
</div>
```

**3. 字幕匹配加容差**

浮点时间比较在帧边界处可能导致相邻字幕间出现空帧（两条都不匹配）。

```tsx
const TOLERANCE = 0.04; // 略大于 1 帧间隔 (1/30 ≈ 0.033s)

// 错误：精确比较，边界处可能空帧
const current = subs.find(s => t >= s.start && t < s.end);

// 正确：start 加容差，消除间隙
const current = subs.find(s => t >= s.start - TOLERANCE && t < s.end);
```

### 渲染前检查清单

- [ ] 全局搜索 `transition` — 确认无 CSS transition
- [ ] 字幕容器用 `textAlign: "center"` + `minHeight` 而非 flex 居中
- [ ] 字幕匹配用 `start - TOLERANCE` 而非精确 `start`
- [ ] `validate-project.mjs` 无 Error
- [ ] 实际渲染一版 MP4 验证（预览不可靠）

## 技术栈

- **动画框架**: Remotion (React视频) + spring/interpolate
- **音频**: Edge TTS (zh-CN-YunxiNeural)
- **字幕**: Edge TTS SentenceBoundary 事件
- **图形**: 纯 React + CSS + 内联 SVG（零外部设计工具）
- **画面**: 1920×1080, 30fps
- **自动化**: Node.js 脚本 (init / subs / timeline / validate)
