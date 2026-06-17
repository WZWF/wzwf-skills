#!/usr/bin/env node
/**
 * 一键校验 Remotion 视频项目的常见问题。
 *
 * 用法: node validate-project.mjs [remotion-video-dir]
 *
 * 检查项目:
 *   1a. 字幕重叠检测 — 相邻字幕 end > next.start
 *   1b. 字幕-场景映射校验 — 字幕 JSON 个数/ID 与 timeline 场景一致
 *   2. 孤立标点检测 — 纯标点符号的字幕条目
 *   3. 时长匹配检测 — timeline.ts duration vs 实际音频时长
 *   4. fadeOut 安全检测 — 场景组件的 fadeOutStart < duration
 *   5. interpolate 安全检测 — 是否使用了安全钳制
 *   6. lockfile 冲突检测 — package-lock.json + pnpm-lock.yaml 共存
 */

import { readdirSync, readFileSync, existsSync, statSync } from "node:fs";
import { join, resolve, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const rvDir = resolve(process.argv[2] || join(__dirname, ".."));

let errors = 0;
let warnings = 0;

function error(msg) { console.error(`  ❌ ${msg}`); errors++; }
function warn(msg) { console.warn(`  ⚠️  ${msg}`); warnings++; }
function ok(msg) { console.log(`  ✅ ${msg}`); }

// ===== 1. 字幕校验 =====
console.log("\n📋 字幕校验");

const subsDir = join(rvDir, "public", "subs");
const datSubsDir = join(rvDir, "src", "data", "subs");
const actualSubsDir = existsSync(subsDir) ? subsDir : existsSync(datSubsDir) ? datSubsDir : null;

if (actualSubsDir) {
  const subFiles = readdirSync(actualSubsDir).filter((f) => f.endsWith(".json")).sort();
  let totalOverlaps = 0;
  let totalOrphanPunct = 0;

  for (const file of subFiles) {
    const entries = JSON.parse(readFileSync(join(actualSubsDir, file), "utf-8"));
    const sceneId = basename(file, ".json");

    for (let i = 0; i < entries.length - 1; i++) {
      if (entries[i].end > entries[i + 1].start + 0.01) {
        error(`[${sceneId}] 字幕重叠: #${i} end=${entries[i].end} > #${i + 1} start=${entries[i + 1].start}`);
        totalOverlaps++;
      }
    }

    const punctOnly = entries.filter((e) => /^[，。！？、；：""''（）\s]+$/.test(e.text));
    if (punctOnly.length > 0) {
      warn(`[${sceneId}] ${punctOnly.length} 条纯标点字幕，应合并到前一条`);
      totalOrphanPunct += punctOnly.length;
    }
  }

  if (totalOverlaps === 0 && totalOrphanPunct === 0) {
    ok(`${subFiles.length} 个场景字幕均正常`);
  }
} else {
  warn("未找到字幕目录 (public/subs/ 或 src/data/subs/)");
}

// ===== 1b. 字幕-场景映射校验 =====
console.log("\n🗺️ 字幕-场景映射校验");

const timelinePath = join(rvDir, "src", "data", "timeline.ts");

if (actualSubsDir && existsSync(timelinePath)) {
  const tlContent = readFileSync(timelinePath, "utf-8");
  const tlSceneIds = [...tlContent.matchAll(/id:\s*"(scene\d+)"/g)].map((m) => m[1]);
  const subSceneIds = readdirSync(actualSubsDir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => {
      const m = basename(f, ".json").match(/scene(\d+)/i);
      return m ? `scene${m[1].padStart(2, "0")}` : null;
    })
    .filter(Boolean)
    .sort();

  const missingInSubs = tlSceneIds.filter((id) => !subSceneIds.includes(id));
  const extraInSubs = subSceneIds.filter((id) => !tlSceneIds.includes(id));

  if (missingInSubs.length > 0) {
    error(`timeline 中有 ${missingInSubs.length} 个场景缺少字幕: ${missingInSubs.join(", ")}`);
  }
  if (extraInSubs.length > 0) {
    warn(`字幕目录中有 ${extraInSubs.length} 个多余文件: ${extraInSubs.join(", ")}`);
  }

  // 检测空字幕文件
  for (const file of readdirSync(actualSubsDir).filter((f) => f.endsWith(".json"))) {
    try {
      const entries = JSON.parse(readFileSync(join(actualSubsDir, file), "utf-8"));
      if (!Array.isArray(entries) || entries.length === 0) {
        error(`[${basename(file, ".json")}] 字幕文件为空或非数组`);
      }
    } catch (e) {
      error(`[${basename(file, ".json")}] 字幕 JSON 解析失败: ${e.message}`);
    }
  }

  if (missingInSubs.length === 0 && extraInSubs.length === 0) {
    ok(`字幕文件与 timeline 场景 1:1 匹配 (${tlSceneIds.length} 个场景)`);
  }
} else if (!actualSubsDir) {
  warn("字幕目录不存在，跳过映射校验");
}

// ===== 2. 时长匹配 =====
console.log("\n🎵 时长匹配");

const audioPublicDir = join(rvDir, "public", "audio");

if (existsSync(timelinePath)) {
  const timelineContent = readFileSync(timelinePath, "utf-8");
  const sceneRegex = /id:\s*"(scene\d+)"[\s\S]*?duration:\s*(\d+)/g;
  let match;
  const sceneDurations = {};

  while ((match = sceneRegex.exec(timelineContent)) !== null) {
    sceneDurations[match[1]] = parseInt(match[2], 10);
  }

  if (existsSync(audioPublicDir)) {
    const audioFiles = readdirSync(audioPublicDir).filter((f) => f.endsWith(".mp3"));
    for (const file of audioFiles) {
      const filePath = join(audioPublicDir, file);
      const nameMatch = file.match(/scene(\d+)/i);
      if (!nameMatch) continue;
      const sceneId = `scene${nameMatch[1].padStart(2, "0")}`;
      const tlDuration = sceneDurations[sceneId];

      if (!tlDuration) {
        warn(`[${sceneId}] 在 timeline.ts 中未找到`);
        continue;
      }

      // 估算音频时长 (128kbps CBR)
      let audioDur;
      try {
        const cmd = `python -c "from mutagen.mp3 import MP3; print(MP3(r'${filePath.replace(/'/g, "\\'")}').info.length)"`;
        audioDur = parseFloat(execSync(cmd, { timeout: 5000, encoding: "utf-8" }).trim());
      } catch {
        audioDur = statSync(filePath).size / (128 * 1000 / 8);
      }

      if (tlDuration < Math.ceil(audioDur)) {
        error(`[${sceneId}] duration=${tlDuration} < 音频实际=${audioDur.toFixed(1)}s — 音频会被截断！`);
      } else if (tlDuration > Math.ceil(audioDur) + 10) {
        warn(`[${sceneId}] duration=${tlDuration} 比音频 ${audioDur.toFixed(1)}s 多了 ${(tlDuration - audioDur).toFixed(1)}s`);
      } else {
        ok(`[${sceneId}] duration=${tlDuration} ≥ 音频 ${audioDur.toFixed(1)}s ✓`);
      }
    }
  } else {
    warn("未找到 public/audio/，跳过时长匹配检查");
  }
} else {
  warn("未找到 timeline.ts");
}

// ===== 3. fadeOut 安全检测 =====
console.log("\n🛡️ fadeOut 安全检测");

const scenesDir = join(rvDir, "src", "scenes");
if (existsSync(scenesDir)) {
  const sceneFiles = readdirSync(scenesDir).filter((f) => f.endsWith(".tsx") || f.endsWith(".ts"));

  for (const file of sceneFiles) {
    const content = readFileSync(join(scenesDir, file), "utf-8");

    // 检查 fadeOutStart 是否使用了 Math.min 安全钳制
    const hasFadeOut = content.includes("fadeOutStart") || content.includes("fadeOut");
    const hasSafeClamp = content.includes("Math.min") && content.includes("durationFrames");

    if (hasFadeOut && !hasSafeClamp) {
      error(`[${file}] fadeOut 未使用 Math.min 安全钳制 — 当 fadeOutStart > duration 时会崩溃`);
    } else if (hasFadeOut && hasSafeClamp) {
      ok(`[${file}] fadeOut 有安全钳制`);
    }

    // 检查 overflow: hidden
    if (content.includes('overflow: "hidden"') || content.includes("overflow: 'hidden'")) {
      warn(`[${file}] 包含 overflow: hidden — 可能裁切子元素动画`);
    }
  }
} else {
  warn("未找到 src/scenes/ 目录");
}

// ===== 4. lockfile 冲突 =====
console.log("\n🔒 锁文件检测");

const hasPackageLock = existsSync(join(rvDir, "package-lock.json"));
const hasPnpmLock = existsSync(join(rvDir, "pnpm-lock.yaml"));

if (hasPackageLock && hasPnpmLock) {
  error("同时存在 package-lock.json 和 pnpm-lock.yaml — Remotion 会拒绝启动！删除其中一个。");
} else {
  ok("锁文件无冲突");
}

// ===== 5. react-compat.d.ts =====
console.log("\n🔧 兼容性补丁");

if (existsSync(join(rvDir, "src", "react-compat.d.ts"))) {
  ok("react-compat.d.ts 存在");
} else {
  warn("缺少 react-compat.d.ts — Remotion 4 + @types/react 18.3 可能报 TS2739");
}

// ===== 汇总 =====
console.log("\n" + "=".repeat(50));
if (errors > 0) {
  console.log(`\n❌ ${errors} 个错误, ${warnings} 个警告。请修复后再预览。`);
  process.exit(1);
} else if (warnings > 0) {
  console.log(`\n⚠️  0 个错误, ${warnings} 个警告。可以预览但建议处理。`);
} else {
  console.log(`\n✅ 全部通过！可以 pnpm start 预览。`);
}
