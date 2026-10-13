#!/usr/bin/env node
/**
 * Extract the small subset of the Python optimizer reference files used by the
 * browser POC. Run from modopt-poc:
 *
 * node scripts/extract-optimizer-data.mjs
 *
 * Optional positional args: GameData.json keystats.json stats_v2_top100.json output.js
 * Defaults match the user's local GuionBot layout. The output is committed
 * separately because these large source files are intentionally not copied
 * into the web app.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const cwd = process.cwd();
const defaults = [
  path.resolve(cwd, "../../warstats/GameData.json"),
  path.resolve(cwd, "../../DATA/keystats.json"),
  path.resolve(cwd, "../../DATA/stats_v2_top100.json"),
  path.resolve(cwd, "src/optimizer-data.generated.js"),
];
const [gameDataPath, keystatsPath, statsPath, outputPath] = [
  ...defaults.slice(0, 3).map((fallback, i) => process.argv[2 + i] ? path.resolve(process.argv[2 + i]) : fallback),
  process.argv[5] ? path.resolve(process.argv[5]) : defaults[3],
];

function readJson(filePath, label) {
  if (!fs.existsSync(filePath)) {
    throw new Error(label + " not found: " + filePath + "\nPass its path as a command-line argument if it is stored elsewhere.");
  }
  process.stdout.write("Reading " + label + ": " + filePath + "\n");
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

// GameData exceeds Node's maximum string length on this system. Stream it and
// retain only the top-level statModSet array needed by the browser optimizer.
// This works with a single file or with byte-split segments that concatenate
// back into the original JSON document.
async function extractTopLevelArray(filePaths, targetKey) {
  let objectDepth = 0;
  let arrayDepth = 0;
  let inString = false;
  let escaped = false;
  let stringBytes = [];
  let captureTopString = false;
  let candidateState = 0; // 1 = awaiting colon, 2 = awaiting array value
  let captureArray = false;
  let captured = [];
  let targetDepth = 0;
  let arrayInString = false;
  let arrayEscaped = false;

  for (const filePath of filePaths) {
    process.stdout.write("Streaming GameData segment: " + filePath + "\n");
    for await (const chunk of fs.createReadStream(filePath)) {
      for (let i = 0; i < chunk.length; i++) {
        const b = chunk[i];
        if (captureArray) {
          captured.push(b);
          if (arrayInString) {
            if (arrayEscaped) arrayEscaped = false;
            else if (b === 0x5c) arrayEscaped = true;
            else if (b === 0x22) arrayInString = false;
          } else if (b === 0x22) arrayInString = true;
          else if (b === 0x5b) targetDepth++;
          else if (b === 0x5d) {
            targetDepth--;
            if (targetDepth === 0) {
              const parsed = JSON.parse(Buffer.from(captured).toString("utf8"));
              if (!Array.isArray(parsed)) throw new Error(targetKey + " is not an array.");
              return parsed;
            }
          }
          continue;
        }

        if (candidateState === 1) {
          if (b === 0x20 || b === 0x09 || b === 0x0a || b === 0x0d) continue;
          if (b === 0x3a) { candidateState = 2; continue; }
          candidateState = 0;
          // Process this byte normally below.
        } else if (candidateState === 2) {
          if (b === 0x20 || b === 0x09 || b === 0x0a || b === 0x0d) continue;
          if (b === 0x5b) {
            captureArray = true;
            targetDepth = 1;
            captured = [b];
            arrayInString = false;
            arrayEscaped = false;
            continue;
          }
          candidateState = 0;
          // Not an array value; continue normal scanning.
        }

        if (inString) {
          if (captureTopString) stringBytes.push(b);
          if (escaped) escaped = false;
          else if (b === 0x5c) escaped = true;
          else if (b === 0x22) {
            inString = false;
            if (captureTopString) {
              const key = Buffer.from(stringBytes).toString("utf8");
              if (key === targetKey) candidateState = 1;
              captureTopString = false;
              stringBytes = [];
            }
          }
          continue;
        }

        if (b === 0x22) {
          inString = true;
          // Segments may be split by top-level sections rather than raw byte offsets.\n          // Accept the target key at any object depth; it is unique in GameData.\n          captureTopString = true;
          stringBytes = [];
        } else if (b === 0x7b) objectDepth++;
        else if (b === 0x7d) objectDepth--;
        else if (b === 0x5b) arrayDepth++;
        else if (b === 0x5d) arrayDepth--;
      }
    }
  }
  throw new Error("Could not find top-level array " + targetKey + " in " + filePaths.join(", "));
}

async function loadGameDataSetDefinitions(filePath) {
  const dir = path.dirname(filePath);
  const segments = [1, 2, 3, 4].map(n => path.join(dir, "GameData_segment" + n + ".json"));
  const inputs = segments.every(file => fs.existsSync(file)) ? segments : [filePath];
  if (!inputs.every(file => fs.existsSync(file))) {
    throw new Error("GameData.json or all four GameData_segment1.json … GameData_segment4.json files must exist.");
  }
  return { statModSet: await extractTopLevelArray(inputs, "statModSet"), sourceFiles: inputs.map(file => path.basename(file)) };
}

const gameDataRaw = await loadGameDataSetDefinitions(gameDataPath);
const keystatsRaw = readJson(keystatsPath, "keystats.json");
const statsRaw = readJson(statsPath, "stats_v2_top100.json");

if (!Array.isArray(gameDataRaw.statModSet) || gameDataRaw.statModSet.length < 8) {
  throw new Error("GameData.json must contain the 8-entry statModSet array.");
}
if (!keystatsRaw.heroes || typeof keystatsRaw.heroes !== "object") {
  throw new Error("keystats.json is missing its heroes object.");
}
if (!statsRaw.units || typeof statsRaw.units !== "object") {
  throw new Error("stats_v2_top100.json is missing its units object.");
}

// The current browser normalizer only consumes statModSet. Keep its full
// records because completeBonus/maxLevelBonus contain the exact raw stat data.
const gameData = { statModSet: gameDataRaw.statModSet };
const heroes = {};
for (const [id, hero] of Object.entries(keystatsRaw.heroes)) {
  if (!hero || typeof hero !== "object") continue;
  heroes[id] = {
    key_stats: Array.isArray(hero.key_stats) ? hero.key_stats : [],
    also: Array.isArray(hero.also) ? hero.also : [],
    sets: hero.sets && typeof hero.sets === "object"
      ? { combos: Array.isArray(hero.sets.combos) ? hero.sets.combos : [], top_combo: hero.sets.top_combo ?? null }
      : {},
  };
}
const keystats = { _meta: keystatsRaw._meta ?? null, heroes };
const units = {};
for (const [id, unit] of Object.entries(statsRaw.units)) {
  if (!unit || typeof unit !== "object") continue;
  units[id] = {
    players: unit.players ?? null,
    stats: { speed: { median: unit.stats?.speed?.median ?? null } },
    mod_stats: { speed: { median: unit.mod_stats?.speed?.median ?? null } },
  };
}
const stats = { _meta: statsRaw._meta ?? null, units };
const payload = {
  generatedAt: new Date().toISOString(),
  sourceFiles: {
    gameData: gameDataRaw.sourceFiles.join(", "),
    keystats: path.basename(keystatsPath),
    stats: path.basename(statsPath),
  },
  gameData,
  keystats,
  stats,
};
const output = "// Generated by scripts/extract-optimizer-data.mjs. Do not edit manually.\n"
  + "export const EMBEDDED_OPTIMIZER_DATA = "
  + JSON.stringify(payload)
  + ";\n";
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, output);
process.stdout.write(
  "Wrote " + outputPath + "\n"
  + "  set definitions: " + gameData.statModSet.length + "\n"
  + "  keystats heroes: " + Object.keys(heroes).length + "\n"
  + "  stats-v2 units: " + Object.keys(units).length + "\n"
  + "  generated module size: " + Buffer.byteLength(output) + " bytes\n"
);
