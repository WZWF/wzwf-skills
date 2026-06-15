#!/usr/bin/env node
/**
 * 根据实际 MP3 时长自动更新 timeline.ts 的 duration 字段。
 *
 * 用法: node generate-timeline-ts.mjs [audio-dir] [timeline-ts-path]
 *
 * 默认:
 *   audio-dir      = ../audio  (相对于 remotion-video/scripts/)
 *   timeline-ts    = src/data/timeline.ts
 *
 * 原理:
 *   读取每个 audio/*.mp3 的文件大小，用 128kbps CBR 估算时长。
 *   如果安装了 mutagen (Python)，使用精确测量。
 *   duration = ceil(实际时长) + 3 秒缓冲。
 *
 * 如果 timeline.ts 已存在，会原地更新 duration 字段。
 * 如果不存在，从 audio 目录反推生成。
 */

import { readdirSync, readFileSync, writeFileSync, existsSync, statSync } from "node:fs";
import { join, basename, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));

const audioDir = resolve(process.argv[2] || join(__dirname, "..", "..", "audio"));
const timelinePath = resolve(process.argv[3] || join(__dirname, "..", "src", "data", "timeline.ts"));

if (!existsSync(audioDir)) {
  console.error(`❌ 音频目录不存在: ${audioDir}`);
  process.exit(1);
}

const mp3Files = readdirSync(audioDir).filter((f) => f.endsWith(".mp3")).sort();
if (mp3Files.length === 0) {
  console.error(`❌ 音频目录为空: ${audioDir}`);
  process.exit(1);
}

console.log(`🎵 从 ${audioDir} 测量 MP3 时长 (${mp3Files.length} 个文件)\n`);

// 尝试用 Python mutagen 精确测量
function getMutagenDuration(filePath) {
  try {
    const cmd = `python -c "from mutagen.mp3 import MP3; print(MP3(r'${filePath.replace(/'/g, "\\'")}').info.length)"`;
    const out = execSync(cmd, { timeout: 5000, encoding: "utf-8" }).trim();
    return parseFloat(out);
  } catch {
    return null;
  }
}

// CBR 估算 (128kbps)
function estimateDuration(filePath) {
  const size = statSync(filePath).size;
  return size / (128 * 1000 / 8);
}

function fileToSceneId(filename) {
  const name = basename(filename, ".mp3");
  const match = name.match(/scene(\d+)/i);
  if (!match) return name;
  return `scene${match[1].padStart(2, "0")}`;
}

const durations = {};
let usedMutagen = false;

for (const file of mp3Files) {
  const filePath = join(audioDir, file);
  const sceneId = fileToSceneId(file);
  let dur = getMutagenDuration(filePath);
  if (dur !== null) {
    usedMutagen = true;
  } else {
    dur = estimateDuration(filePath);
  }
  const buffered = Math.ceil(dur) + 3;
  durations[sceneId] = { actual: dur, buffered };
  console.log(`  ${sceneId}: ${dur.toFixed(2)}s → duration=${buffered} (${file})`);
}

if (!usedMutagen) {
  console.log("\n⚠️  未检测到 mutagen，使用 CBR 估算。精确测量: pip install mutagen");
}

// 更新 timeline.ts
if (existsSync(timelinePath)) {
  let content = readFileSync(timelinePath, "utf-8");
  let updated = 0;

  for (const [sceneId, { buffered }] of Object.entries(durations)) {
    // 匹配 id: "sceneXX" 后的 duration: N
    const regex = new RegExp(
      `(id:\\s*"${sceneId}"[\\s\\S]*?duration:\\s*)\\d+`,
      "g"
    );
    const newContent = content.replace(regex, `$1${buffered}`);
    if (newContent !== content) {
      updated++;
      content = newContent;
    }
  }

  writeFileSync(timelinePath, content, "utf-8");
  console.log(`\n✅ 已更新 ${timelinePath} (${updated} 个场景)`);
} else {
  // 从头生成
  const scenes = mp3Files.map((file) => {
    const sceneId = fileToSceneId(file);
    const name = basename(file, ".mp3");
    return {
      id: sceneId,
      visual: null,
      audio: `audio/${name}.mp3`,
      duration: durations[sceneId].buffered,
      animation: [],
    };
  });

  const content = `import type { Timeline } from "../types";

export const timeline: Timeline = ${JSON.stringify({ scenes }, null, 2)};
`;
  writeFileSync(timelinePath, content, "utf-8");
  console.log(`\n✅ 已生成 ${timelinePath}`);
}
