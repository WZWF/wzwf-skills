#!/usr/bin/env node
/**
 * 从 subs/*.json 自动生成 Remotion 的 src/data/subs.ts 文件。
 *
 * 用法: node generate-subs-ts.mjs [subs-dir] [output-file]
 *
 * 默认:
 *   subs-dir   = ../subs  (相对于 remotion-video/scripts/)
 *   output     = src/data/subs.ts
 *
 * 也可以在任意目录下通过绝对路径调用:
 *   node generate-subs-ts.mjs  D:\project\subs  D:\project\remotion-video\src\data\subs.ts
 */

import { readdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, basename, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const subsDir = resolve(process.argv[2] || join(__dirname, "..", "..", "subs"));
const outputFile = resolve(process.argv[3] || join(__dirname, "..", "src", "data", "subs.ts"));

if (!existsSync(subsDir)) {
  console.error(`❌ 字幕目录不存在: ${subsDir}`);
  process.exit(1);
}

const files = readdirSync(subsDir)
  .filter((f) => f.endsWith(".json"))
  .sort();

if (files.length === 0) {
  console.error(`❌ 字幕目录为空: ${subsDir}`);
  process.exit(1);
}

console.log(`📝 从 ${subsDir} 生成 subs.ts (${files.length} 个场景)\n`);

// 从文件名提取 sceneId: "scene1-painpoint.json" -> "scene01"
function fileToSceneId(filename) {
  const name = basename(filename, ".json");
  const match = name.match(/scene(\d+)/i);
  if (!match) return name;
  return `scene${match[1].padStart(2, "0")}`;
}

// 同时复制到 src/data/subs/ 目录
const datSubsDir = join(dirname(outputFile), "subs");
if (!existsSync(datSubsDir)) {
  const { mkdirSync } = await import("node:fs");
  mkdirSync(datSubsDir, { recursive: true });
}

const imports = [];
const mapEntries = [];

for (const file of files) {
  const sceneId = fileToSceneId(file);
  const idx = files.indexOf(file) + 1;
  const varName = `scene${idx}`;

  // 复制 JSON 到 src/data/subs/
  const src = join(subsDir, file);
  const dest = join(datSubsDir, `${sceneId}.json`);
  const content = readFileSync(src, "utf-8");
  writeFileSync(dest, content, "utf-8");

  const entries = JSON.parse(content);
  console.log(`  ${sceneId}: ${entries.length} 条字幕 (${file})`);

  imports.push(`import ${varName} from "./subs/${sceneId}.json";`);
  mapEntries.push(`  ${sceneId}: ${varName} as SubtitleEntry[],`);
}

const output = `import type { SubtitleEntry } from "../types";

${imports.join("\n")}

export const SCENE_SUBS: Record<string, SubtitleEntry[]> = {
${mapEntries.join("\n")}
};
`;

writeFileSync(outputFile, output, "utf-8");
console.log(`\n✅ 已生成: ${outputFile}`);
