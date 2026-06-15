#!/usr/bin/env node
/**
 * 一键初始化 Remotion 视频项目骨架。
 *
 * 用法:
 *   node init-remotion-project.mjs <project-name> [voiceover-clean.txt]
 *
 * 输出:
 *   <project-name>/
 *   ├── remotion-video/
 *   │   ├── package.json
 *   │   ├── tsconfig.json
 *   │   ├── src/
 *   │   │   ├── index.ts
 *   │   │   ├── Root.tsx
 *   │   │   ├── Video.tsx           (需 AI 填充场景组件映射)
 *   │   │   ├── Subtitle.tsx
 *   │   │   ├── types.ts
 *   │   │   ├── react-compat.d.ts
 *   │   │   ├── styles/tokens.ts
 *   │   │   ├── anim/               (4 个动画基础组件)
 *   │   │   ├── data/               (timeline.ts, subs.ts — 占位)
 *   │   │   └── scenes/             (空，AI 后续生成)
 *   │   └── scripts/setup-assets.mjs
 *   └── generate-audio-with-subs.py
 *
 * 如果提供了 voiceover-clean.txt，会自动解析场景名+文案到 Python 脚本中。
 */

import { mkdirSync, writeFileSync, existsSync, readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const args = process.argv.slice(2);
if (args.length < 1) {
  console.error("用法: node init-remotion-project.mjs <project-name> [voiceover-clean.txt]");
  process.exit(1);
}

const PROJECT_NAME = args[0];
const VOICEOVER_FILE = args[1];
const ROOT = join(process.cwd(), PROJECT_NAME);
const RV = join(ROOT, "remotion-video");

function ensureDir(dir) {
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

function write(path, content) {
  writeFileSync(path, content, "utf-8");
  console.log(`  [create] ${path.replace(process.cwd() + "\\", "").replace(process.cwd() + "/", "")}`);
}

// ===== 解析旁白文稿 =====
function parseVoiceover(filePath) {
  if (!filePath || !existsSync(filePath)) return [];
  const text = readFileSync(filePath, "utf-8");
  const scenes = [];
  const lines = text.split("\n");
  let currentScene = null;
  let currentText = [];

  for (const line of lines) {
    const trimmed = line.trim();
    // 匹配 "## Scene 01: xxx" 或 "## 场景1：xxx" 或类似模式
    const sceneMatch = trimmed.match(/^##\s*(?:Scene\s*)?(\d+)\s*[:：]\s*(.+)/i)
      || trimmed.match(/^##\s*场景\s*(\d+)\s*[:：]\s*(.+)/i);
    if (sceneMatch) {
      if (currentScene) {
        scenes.push({ ...currentScene, text: currentText.join("") });
      }
      const num = parseInt(sceneMatch[1], 10);
      const title = sceneMatch[2].trim();
      currentScene = {
        id: `scene${String(num).padStart(2, "0")}`,
        name: `scene${num}-${title.replace(/[^a-zA-Z0-9\u4e00-\u9fff]/g, "").substring(0, 15)}`,
        title,
      };
      currentText = [];
    } else if (currentScene && trimmed) {
      currentText.push(trimmed);
    }
  }
  if (currentScene) {
    scenes.push({ ...currentScene, text: currentText.join("") });
  }
  return scenes;
}

const scenes = parseVoiceover(VOICEOVER_FILE);
const sceneCount = scenes.length || 8;

console.log(`\n🎬 初始化 Remotion 视频项目: ${PROJECT_NAME}`);
console.log(`   场景数: ${sceneCount}\n`);

// ===== 目录结构 =====
[
  RV,
  join(RV, "src"),
  join(RV, "src", "anim"),
  join(RV, "src", "data"),
  join(RV, "src", "data", "subs"),
  join(RV, "src", "scenes"),
  join(RV, "src", "styles"),
  join(RV, "scripts"),
  join(RV, "public", "audio"),
  join(RV, "public", "subs"),
  join(ROOT, "audio"),
  join(ROOT, "subs"),
].forEach(ensureDir);

// ===== package.json =====
write(join(RV, "package.json"), JSON.stringify({
  name: `${PROJECT_NAME}-video`,
  version: "1.0.0",
  private: true,
  scripts: {
    start: "remotion studio src/index.ts",
    build: "remotion render src/index.ts MainVideo out/video.mp4 --log=verbose",
    setup: "node scripts/setup-assets.mjs",
  },
  dependencies: {
    "@remotion/cli": "^4.0.0",
    react: "^18.3.1",
    "react-dom": "^18.3.1",
    remotion: "^4.0.0",
  },
  devDependencies: {
    "@types/react": "^18.3.3",
    typescript: "^5.5.0",
  },
}, null, 2) + "\n");

// ===== tsconfig.json =====
write(join(RV, "tsconfig.json"), JSON.stringify({
  compilerOptions: {
    target: "ES2022",
    module: "ES2022",
    moduleResolution: "bundler",
    jsx: "react-jsx",
    strict: true,
    esModuleInterop: true,
    resolveJsonModule: true,
    skipLibCheck: true,
    outDir: "dist",
  },
  include: ["src"],
}, null, 2) + "\n");

// ===== types.ts =====
write(join(RV, "src", "types.ts"), `export interface Animation {
  type: "fadeIn" | "enter" | "highlight" | "transition";
  target: string;
  startSec: number;
  durationSec: number;
}

export interface SceneData {
  id: string;
  visual: string | string[] | null;
  audio: string;
  duration: number;
  note?: string;
  animation: Animation[];
}

export interface Timeline {
  scenes: SceneData[];
}

export interface SubtitleEntry {
  text: string;
  start: number;
  end: number;
}

export const SCENE_TITLES: Record<string, string> = {
${scenes.map((s) => `  ${s.id}: "${s.title}",`).join("\n") || "  // AI 填充场景标题"}
};
`);

// ===== styles/tokens.ts =====
write(join(RV, "src", "styles", "tokens.ts"), `export const colors = {
  bgDark: "#0F0F23",
  bgCard: "#1A1A2E",
  accent: "#F57C00",
  accentGlow: "rgba(245, 124, 0, 0.6)",
  highlightGold: "rgba(255, 213, 79, 0.8)",
  white: "#FFFFFF",
  textPrimary: "#E0E0E0",
  textSecondary: "#78909C",
  titleGradientFrom: "#F57C00",
  titleGradientTo: "#FFB74D",
  codeBg: "rgba(40, 44, 52, 0.95)",
  codeText: "#ABB2BF",
  codeComment: "#5C6370",
  codeKeyword: "#C678DD",
  codeString: "#98C379",
  codeError: "#E06C75",
};

export const fonts = {
  mono: "JetBrains Mono, Fira Code, Consolas, monospace",
  sans: "Inter, Noto Sans SC, system-ui, sans-serif",
};

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;

export const CLAMP = {
  extrapolateLeft: "clamp" as const,
  extrapolateRight: "clamp" as const,
};
`);

// ===== react-compat.d.ts =====
write(join(RV, "src", "react-compat.d.ts"), `import "react";
declare module "react" {
  interface DOMAttributes<T> {
    placeholder?: string | undefined;
    onPointerEnterCapture?: React.PointerEventHandler<T> | undefined;
    onPointerLeaveCapture?: React.PointerEventHandler<T> | undefined;
  }
}
`);

// ===== anim/ 四件套 =====
write(join(RV, "src", "anim", "CinematicBg.tsx"), `import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { colors } from "../styles/tokens";

const GRID = 60;
const PARTICLES = 12;

export const CinematicBg: React.FC<{ seed?: number }> = ({ seed = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  const particles = Array.from({ length: PARTICLES }, (_, i) => {
    const x = ((seed * 137 + i * 223) % 1920);
    const y = ((seed * 97 + i * 311) % 1080);
    const speed = 0.3 + (i % 5) * 0.15;
    const yy = (y + t * speed * 30) % 1080;
    const opacity = 0.15 + 0.1 * Math.sin(t * 0.8 + i);
    return { x, y: yy, opacity, r: 2 + (i % 3) };
  });

  const gridOpacity = 0.04 + 0.015 * Math.sin(t * 0.3);

  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", background: colors.bgDark }}>
      <svg width="1920" height="1080" style={{ position: "absolute", inset: 0 }}>
        {Array.from({ length: Math.ceil(1920 / GRID) + 1 }, (_, i) => (
          <line key={\`v\${i}\`} x1={i * GRID} y1={0} x2={i * GRID} y2={1080}
            stroke="rgba(255,255,255,0.06)" strokeWidth={1} opacity={gridOpacity} />
        ))}
        {Array.from({ length: Math.ceil(1080 / GRID) + 1 }, (_, i) => (
          <line key={\`h\${i}\`} x1={0} y1={i * GRID} x2={1920} y2={i * GRID}
            stroke="rgba(255,255,255,0.06)" strokeWidth={1} opacity={gridOpacity} />
        ))}
        {particles.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={p.r} fill={colors.accent} opacity={p.opacity} />
        ))}
      </svg>
    </div>
  );
};
`);

write(join(RV, "src", "anim", "FadeSlide.tsx"), `import React from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { CLAMP } from "../styles/tokens";

interface FadeSlideProps {
  delaySec: number;
  direction?: "up" | "down" | "left" | "right";
  distance?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}

export const FadeSlide: React.FC<FadeSlideProps> = ({
  delaySec, direction = "up", distance = 30, children, style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const delayFrames = Math.round(delaySec * fps);
  const progress = spring({ fps, frame: frame - delayFrames, config: { damping: 50, stiffness: 120 } });
  const opacity = interpolate(progress, [0, 1], [0, 1], CLAMP);

  const axis = direction === "left" || direction === "right" ? "X" : "Y";
  const sign = direction === "down" || direction === "right" ? -1 : 1;
  const offset = interpolate(progress, [0, 1], [sign * distance, 0], CLAMP);

  return (
    <div style={{ opacity, transform: \`translate\${axis}(\${offset}px)\`, willChange: "transform, opacity", ...style }}>
      {children}
    </div>
  );
};
`);

write(join(RV, "src", "anim", "GlowBox.tsx"), `import React from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import { CLAMP, colors } from "../styles/tokens";

interface GlowBoxProps {
  x: number; y: number; w: number; h: number;
  label: string;
  delaySec: number;
  color?: string;
  textColor?: string;
  fontSize?: number;
  glowSec?: number;
  icon?: string;
  sublabel?: string;
  style?: React.CSSProperties;
}

export const GlowBox: React.FC<GlowBoxProps> = ({
  x, y, w, h, label, delaySec,
  color = colors.bgCard, textColor = colors.textPrimary,
  fontSize = 18, glowSec, icon, sublabel, style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const delayFrames = Math.round(delaySec * fps);
  const progress = spring({ fps, frame: frame - delayFrames, config: { damping: 50, stiffness: 120 } });
  const opacity = interpolate(progress, [0, 1], [0, 1], CLAMP);
  const scale = interpolate(progress, [0, 1], [0.3, 1], CLAMP);

  let glowOpacity = 0;
  if (glowSec !== undefined) {
    const glowFrame = Math.round(glowSec * fps);
    const safeStart = Math.max(0, glowFrame);
    const safeEnd = Math.max(safeStart + 1, glowFrame + Math.round(fps * 2));
    glowOpacity = interpolate(frame, [safeStart, safeStart + fps * 0.3, safeEnd - fps * 0.3, safeEnd], [0, 0.7, 0.7, 0], CLAMP);
  }

  return (
    <div style={{
      position: "absolute", left: x, top: y, width: w, height: h,
      background: color, borderRadius: 12,
      border: \`1px solid rgba(255,255,255,0.08)\`,
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      opacity, transform: \`scale(\${scale})\`,
      boxShadow: glowOpacity > 0 ? \`0 0 \${20 * glowOpacity}px \${colors.accentGlow}\` : "none",
      ...style,
    }}>
      {icon && <span style={{ fontSize: fontSize * 1.4, marginBottom: 4 }}>{icon}</span>}
      <span style={{ color: textColor, fontSize, fontWeight: 600, fontFamily: "JetBrains Mono, Consolas, monospace" }}>{label}</span>
      {sublabel && <span style={{ color: colors.textSecondary, fontSize: fontSize * 0.75, marginTop: 2 }}>{sublabel}</span>}
    </div>
  );
};
`);

write(join(RV, "src", "anim", "DrawLine.tsx"), `import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { CLAMP, colors } from "../styles/tokens";

interface DrawLineProps {
  x1: number; y1: number; x2: number; y2: number;
  delaySec: number;
  color?: string;
  strokeWidth?: number;
  dashed?: boolean;
  arrow?: boolean;
}

export const DrawLine: React.FC<DrawLineProps> = ({
  x1, y1, x2, y2, delaySec,
  color = "rgba(245, 124, 0, 0.7)", strokeWidth = 2, dashed = false, arrow = true,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const len = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
  const startFrame = Math.round(delaySec * fps);
  const drawDur = fps * 0.8;
  const safeEnd = Math.max(startFrame + 1, startFrame + drawDur);
  const progress = interpolate(frame, [startFrame, safeEnd], [0, 1], CLAMP);
  const dashOffset = len * (1 - progress);

  const angle = Math.atan2(y2 - y1, x2 - x1);
  const aLen = 10;

  return (
    <svg style={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "visible" }} width="1920" height="1080">
      <line x1={x1} y1={y1} x2={x2} y2={y2}
        stroke={color} strokeWidth={strokeWidth}
        strokeDasharray={dashed ? "8 4" : \`\${len}\`}
        strokeDashoffset={dashed ? 0 : dashOffset}
        strokeLinecap="round" />
      {arrow && progress > 0.9 && (
        <polygon
          points={\`\${x2},\${y2} \${x2 - aLen * Math.cos(angle - 0.4)},\${y2 - aLen * Math.sin(angle - 0.4)} \${x2 - aLen * Math.cos(angle + 0.4)},\${y2 - aLen * Math.sin(angle + 0.4)}\`}
          fill={color} opacity={interpolate(progress, [0.9, 1], [0, 1], CLAMP)} />
      )}
    </svg>
  );
};
`);

write(join(RV, "src", "anim", "index.ts"), `export { CinematicBg } from "./CinematicBg";
export { FadeSlide } from "./FadeSlide";
export { GlowBox } from "./GlowBox";
export { DrawLine } from "./DrawLine";
`);

// ===== Subtitle.tsx =====
write(join(RV, "src", "Subtitle.tsx"), `import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import type { SubtitleEntry } from "./types";
import { fonts, colors } from "./styles/tokens";

interface Props {
  subs: SubtitleEntry[];
  offsetSec?: number;
}

export const Subtitle: React.FC<Props> = ({ subs, offsetSec = -0.15 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps + offsetSec;
  const current = subs.find((s) => t >= s.start && t < s.end);
  if (!current) return null;
  return (
    <div style={{
      position: "absolute", bottom: 80, left: 0, right: 0,
      display: "flex", justifyContent: "center", pointerEvents: "none",
    }}>
      <span style={{
        background: "rgba(0,0,0,0.7)", color: colors.white,
        padding: "10px 30px", borderRadius: 8,
        fontSize: 28, fontFamily: fonts.sans, letterSpacing: 1,
      }}>{current.text}</span>
    </div>
  );
};
`);

// ===== data/timeline.ts (占位) =====
const timelineScenes = scenes.map((s, i) => ({
  id: s.id,
  visual: null,
  audio: `audio/${s.name}.mp3`,
  duration: 30,
  animation: [],
}));
if (timelineScenes.length === 0) {
  for (let i = 1; i <= sceneCount; i++) {
    timelineScenes.push({
      id: `scene${String(i).padStart(2, "0")}`,
      visual: null,
      audio: `audio/scene${i}-placeholder.mp3`,
      duration: 30,
      animation: [],
    });
  }
}
write(join(RV, "src", "data", "timeline.ts"), `import type { Timeline } from "../types";

// ⚠️ duration 为占位值，音频生成后运行 generate-timeline-ts.mjs 更新
export const timeline: Timeline = ${JSON.stringify({ scenes: timelineScenes }, null, 2)};
`);

// ===== data/subs.ts (占位) =====
const subsImports = timelineScenes.map((s, i) =>
  `import scene${i + 1} from "./subs/${s.id}.json";`
).join("\n");
const subsMap = timelineScenes.map((s, i) =>
  `  ${s.id}: scene${i + 1} as SubtitleEntry[],`
).join("\n");
write(join(RV, "src", "data", "subs.ts"), `import type { SubtitleEntry } from "../types";

${subsImports}

export const SCENE_SUBS: Record<string, SubtitleEntry[]> = {
${subsMap}
};
`);

// ===== index.ts =====
write(join(RV, "src", "index.ts"), `import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";
registerRoot(RemotionRoot);
`);

// ===== Root.tsx =====
write(join(RV, "src", "Root.tsx"), `import React from "react";
import { Composition } from "remotion";
import { Video } from "./Video";
import { timeline } from "./data/timeline";
import { FPS, WIDTH, HEIGHT } from "./styles/tokens";

const totalSeconds = timeline.scenes.reduce((sum, s) => sum + s.duration, 0);
const totalFrames = totalSeconds * FPS;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MainVideo"
        component={Video}
        durationInFrames={totalFrames}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
    </>
  );
};
`);

// ===== Video.tsx (模板) =====
write(join(RV, "src", "Video.tsx"), `import React from "react";
import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { timeline } from "./data/timeline";
import { SCENE_SUBS } from "./data/subs";
import { Subtitle } from "./Subtitle";
import { FPS, colors } from "./styles/tokens";
import type { SceneData } from "./types";
import { SCENE_TITLES } from "./types";
// TODO: AI 生成场景组件后取消注释
// import { Scene01 } from "./scenes/Scene01";
// const SCENE_COMPONENTS: Record<string, React.FC<{ scene: SceneData }>> = {
//   scene01: Scene01,
// };

const SceneOverlay: React.FC<{ sceneId: string; durationFrames: number }> = ({ sceneId, durationFrames }) => {
  const frame = useCurrentFrame();
  const progress = Math.min(frame / durationFrames, 1);
  return (
    <>
      <Subtitle subs={SCENE_SUBS[sceneId] ?? []} />
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0, height: 4,
        background: "rgba(255,255,255,0.1)",
      }}>
        <div style={{
          height: "100%", width: \`\${progress * 100}%\`,
          background: \`linear-gradient(90deg, \${colors.accent}, \${colors.highlightGold})\`,
          transition: "width 0.1s linear",
        }} />
      </div>
    </>
  );
};

const FallbackScene: React.FC<{ scene: SceneData }> = ({ scene }) => (
  <AbsoluteFill style={{ background: colors.bgDark, display: "flex", alignItems: "center", justifyContent: "center" }}>
    <span style={{ color: colors.textPrimary, fontSize: 48 }}>
      {SCENE_TITLES[scene.id] ?? scene.id}
    </span>
  </AbsoluteFill>
);

export const Video: React.FC = () => {
  let frameOffset = 0;
  return (
    <AbsoluteFill>
      {timeline.scenes.map((scene) => {
        const durationFrames = scene.duration * FPS;
        const from = frameOffset;
        frameOffset += durationFrames;
        const label = SCENE_TITLES[scene.id] ?? scene.id;
        // const SceneComponent = SCENE_COMPONENTS[scene.id] ?? FallbackScene;
        const SceneComponent = FallbackScene;
        return (
          <Sequence key={scene.id} from={from} durationInFrames={durationFrames} name={\`\${scene.id} — \${label}\`}>
            <SceneComponent scene={scene} />
            <SceneOverlay sceneId={scene.id} durationFrames={durationFrames} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
`);

// ===== scripts/setup-assets.mjs =====
write(join(RV, "scripts", "setup-assets.mjs"), `import { cpSync, mkdirSync, existsSync, readdirSync } from "node:fs";
import { resolve, join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const PARENT = resolve(ROOT, "..");
const PUBLIC = resolve(ROOT, "public");

function ensureDir(dir) {
  if (!existsSync(dir)) { mkdirSync(dir, { recursive: true }); console.log(\`[mkdir] \${dir}\`); }
}

function copyDir(src, dest, ext) {
  if (!existsSync(src)) { console.warn(\`[skip] 源目录不存在: \${src}\`); return; }
  ensureDir(dest);
  const files = readdirSync(src).filter((f) => ext ? f.endsWith(ext) : true);
  for (const file of files) {
    cpSync(join(src, file), join(dest, file));
    console.log(\`[copy] \${file} -> \${dest}\`);
  }
}

console.log("=== Remotion 资产初始化 ===\\n");
copyDir(join(PARENT, "audio"), join(PUBLIC, "audio"), ".mp3");
copyDir(join(PARENT, "subs"), join(PUBLIC, "subs"), ".json");
console.log("\\n✅ 资产拷贝完成。");
`);

// ===== generate-audio-with-subs.py =====
if (scenes.length > 0) {
  const pyScenes = scenes.map((s) =>
    `    (\n        "${s.name}",\n        "${s.text.replace(/"/g, '\\"')}"\n    ),`
  ).join("\n");

  write(join(ROOT, "generate-audio-with-subs.py"), `"""
生成音频 + 字幕 JSON (Edge TTS + SentenceBoundary)。

用法: python generate-audio-with-subs.py
输出: audio/*.mp3  +  subs/*.json
"""

import asyncio
import json
import os
import edge_tts

VOICE = "zh-CN-YunxiNeural"
RATE = "-5%"
AUDIO_DIR = "audio"
SUBS_DIR = "subs"

SCENES = [
${pyScenes}
]


async def generate_scene(name: str, text: str):
    audio_path = f"{AUDIO_DIR}/{name}.mp3"
    subs_path = f"{SUBS_DIR}/{name}.json"
    print(f"[生成中] {name} ...")
    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    raw_subs = []
    with open(audio_path, "wb") as audio_file:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                start_sec = chunk["offset"] / 10_000_000
                end_sec = start_sec + chunk["duration"] / 10_000_000
                raw_subs.append({"text": chunk["text"], "start": round(start_sec, 2), "end": round(end_sec, 2)})
    subs = split_long_sentences(raw_subs, max_chars=20)
    with open(subs_path, "w", encoding="utf-8") as f:
        json.dump(subs, f, ensure_ascii=False, indent=2)
    print(f"[完成]   {audio_path} + {subs_path} ({len(subs)} 条字幕)")


def split_long_sentences(subs, max_chars=20):
    result = []
    delimiters = "，、；"
    for s in subs:
        text = s["text"]
        if len(text) <= max_chars:
            result.append(s)
            continue
        parts = []
        buf = ""
        for ch in text:
            buf += ch
            if ch in delimiters and len(buf) >= 4:
                parts.append(buf)
                buf = ""
        if buf:
            if parts and len(buf) < 4:
                parts[-1] += buf
            else:
                parts.append(buf)
        total_len = sum(len(p) for p in parts)
        total_dur = s["end"] - s["start"]
        t = s["start"]
        for p in parts:
            dur = total_dur * len(p) / total_len
            result.append({"text": p, "start": round(t, 2), "end": round(t + dur, 2)})
            t += dur
    return result


async def main():
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(SUBS_DIR, exist_ok=True)
    for name, text in SCENES:
        await generate_scene(name, text)
    print(f"\\n全部 {len(SCENES)} 段音频 + 字幕已生成。")


if __name__ == "__main__":
    asyncio.run(main())
`);
} else {
  write(join(ROOT, "generate-audio-with-subs.py"), `"""
生成音频 + 字幕 JSON (Edge TTS + SentenceBoundary)。
⚠️ 请先填写 SCENES 列表！

用法: python generate-audio-with-subs.py
输出: audio/*.mp3  +  subs/*.json
"""

import asyncio
import json
import os
import edge_tts

VOICE = "zh-CN-YunxiNeural"
RATE = "-5%"
AUDIO_DIR = "audio"
SUBS_DIR = "subs"

# 填入场景: (文件名, 旁白文本)
SCENES = [
    # ("scene1-intro", "这里是旁白文本..."),
]

# ... (generate_scene, split_long_sentences, main 同上)
`);
}

console.log("\n✅ 项目骨架已创建！\n");
console.log("后续步骤:");
console.log("  1. 编辑 voiceover-clean.txt (如果还没有)");
console.log("  2. python generate-audio-with-subs.py");
console.log("  3. node scripts/generate-timeline-ts.mjs  (更新时长)");
console.log("  4. node scripts/validate-project.mjs      (校验)");
console.log("  5. AI 生成场景组件 → src/scenes/");
console.log("  6. cd remotion-video && pnpm install && pnpm start");
