# Remotion 项目结构与场景设计（Step 3-6）

## Step 3: Remotion 项目结构

```
remotion-video/
├── src/
│   ├── anim/           ← 共享动画基础组件
│   │   ├── CinematicBg.tsx   动态网格+粒子背景
│   │   ├── FadeSlide.tsx     弹簧淡入+位移
│   │   ├── GlowBox.tsx       脉冲高亮方块
│   │   └── DrawLine.tsx      SVG自绘线条
│   ├── scenes/         ← 每个Scene一个React组件
│   ├── data/
│   │   ├── timeline.ts       时间轴数据
│   │   └── subs.ts           字幕数据
│   ├── Video.tsx       ← 主编排 (timeline驱动Sequence)
│   ├── Subtitle.tsx    ← 字幕叠加组件
│   └── styles/tokens.ts ← 设计令牌
├── public/             ← 静态资源 (mp3/json/svg)
└── scripts/
    └── setup-assets.mjs ← 资产拷贝脚本
```

## Step 4: 场景组件设计原则

**消除PPT感的关键**：

| 原则 | 做法 | 禁忌 |
|------|------|------|
| 持续运动 | CinematicBg 背景粒子+网格 | 静态纯色背景 |
| 逐元素入场 | FadeSlide + spring 弹簧 | 整图一次性淡入 |
| 自绘效果 | DrawLine stroke-dashoffset | 箭头直接出现 |
| 深度感 | 多层 z-index + 微视差 | 所有元素同层 |
| 音画同步 | delaySec 对齐旁白节奏 | 固定间隔入场 |

**场景组件模板**：

```tsx
const TIMING = { fadeOutStart: 38 }; // 必须 < scene.duration

export const XxxScene: React.FC<{ scene: SceneData }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const durationFrames = scene.duration * fps;

  // 全局淡入淡出 — fadeOut 用安全钳制
  const fadeIn = interpolate(frame, [0, fps * 0.5], [0, 1], CLAMP);
  const fadeOutFrame = Math.min(
    Math.round(TIMING.fadeOutStart * fps),
    Math.max(0, durationFrames - 1),
  );
  const fadeOut = interpolate(frame, [fadeOutFrame, durationFrames], [1, 0], CLAMP);

  return (
    <AbsoluteFill style={{ opacity: Math.min(fadeIn, fadeOut) }}>
      <CinematicBg seed={42} />  {/* 所有场景必须用同一个 seed */}
      {/* delaySec 必须对齐字幕时间戳，讲到才弹出 */}
      <FadeSlide delaySec={5.6}>
        <GlowBox delaySec={5.6} color={COLORS.success}>
          {/* 模块内容 */}
        </GlowBox>
      </FadeSlide>
      {scene.audio && <Audio src={staticFile(scene.audio)} />}
    </AbsoluteFill>
  );
};
```

**字幕组件必须加负偏移**：

```tsx
// Subtitle.tsx — offsetSec={-0.15} 补偿 Audio 播放延迟
<Subtitle sceneId={scene.id} startFrame={0} offsetSec={-0.15} />
```

**必须遵守的规则**：

1. **fadeOut 必须用安全钳制**：hardcoded 的 `fadeOutStart` 可能超出实际 `duration`
   ```tsx
   const fadeOutFrame = Math.min(
     Math.round(TIMING.fadeOutStart * fps),
     Math.max(0, durationFrames - 1),
   );
   const fadeOut = interpolate(frame, [fadeOutFrame, durationFrames], [1, 0], CLAMP);
   ```
2. **interpolate 输入范围必须严格递增**：四参数 `[a, b, c, d]` 必须 `a < b < c < d`
3. **音频生成后必须更新 timeline**：`duration = ceil(实际时长) + 3`，然后同步更新场景组件的 TIMING 常量
4. **GlowBox 禁止 pulse 缩放动画**：多个 GlowBox 各自用 `sin()` 做缩放脉冲，叠加后画面会持续跳动。GlowBox 只做静态发光，不做 scale 变化
5. **不要对整个内容区域加 breathScale**（全局抖动，多层叠加会抖）
6. **不要在容器上设 `overflow: hidden`**（裁切子元素）
7. **CinematicBg seed 必须所有场景统一**：不同场景用不同 seed 会导致场景切换时粒子位置突变，产生视觉跳切。所有场景用同一个固定值如 `seed={42}`
8. **动画 delaySec 必须对齐字幕时间戳**：每个 FadeSlide/GlowBox 的 delaySec 必须参考 `subs.ts` 中对应字幕的 start 时间。讲到哪个模块才弹出哪个模块，不要提前出现。流程：先看字幕时间戳 → 再写 delaySec
9. **字幕需要负偏移补偿音频延迟**：Remotion 的 `<Audio>` 组件有播放延迟，字幕组件应加 `offsetSec={-0.15}`（负值=字幕提前出现）
10. **字幕数据必须无重叠、无孤立标点**：生成后用脚本检查相邻字幕的 `end > next.start` 重叠；纯标点符号的条目（如单独的"？"）必须合并到前一条

**环境陷阱**：

- Remotion 4.0 + @types/react 18.3 需要 `react-compat.d.ts` 补丁
- 使用 pnpm 时，安装后**必须删除 `package-lock.json`**（如果存在），Remotion 不允许多锁文件共存
  ```bash
  rm -f package-lock.json node_modules/.package-lock.json
  ```
- Node.js 18 不支持 `import.meta.dirname`，用 `fileURLToPath(import.meta.url)` + `dirname()` 替代
- 公司代理环境可能导致 `ERR_EMPTY_RESPONSE`，Studio 预览通常正常，CLI 渲染可能需要 `--browser-executable` 指向 Edge

## Step 5: Video.tsx 编排

```tsx
const SCENE_COMPONENTS: Record<string, React.FC<{ scene: SceneData }>> = {
  scene01: CodeScene,
  scene02: ComparisonScene,
  // ...
};

// Sequence 内统一叠加字幕+进度条
<Sequence from={from} durationInFrames={dur}>
  <SceneComponent scene={scene} />
  <SceneOverlay sceneId={scene.id} durationFrames={dur} />
</Sequence>
```

## Step 6: 运行

```bash
cd remotion-video
pnpm install
node scripts/setup-assets.mjs   # 拷贝音频+字幕+SVG
pnpm start                      # Studio预览
pnpm run build                  # 渲染MP4
```

## 修改场景的快速路径

1. 改旁白 → `generate-audio-with-subs.py` SCENES 数组
2. 重生成 → `python generate-audio-with-subs.py`
3. 测时长 → `mutagen.mp3.MP3(path).info.length`
4. 更新 timeline → `duration` = 实际时长 + 3s，调整尾部 transition
5. **校验字幕** → 检查重叠和孤立标点（见 [troubleshooting.md](troubleshooting.md)）
6. **对齐动画** → 根据字幕时间戳更新场景组件的 delaySec
7. 拷贝资产 → `node scripts/setup-assets.mjs`
8. 预览 → `pnpm start`
