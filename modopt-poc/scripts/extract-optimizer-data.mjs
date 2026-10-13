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
  // Find the literal key in the stream, then parse only its array value.
  // The GameData segments may each be independent sections, so do not carry
  // JSON nesting/string state from one segment to the next.
  const marker = Buffer.from(JSON.stringify(targetKey), "utf8");
  let tail = Buffer.alloc(0);
  let found = false;
  let awaitingArray = false;
  let captureArray = false;
  let captured = [];
  let depth = 0;
  let inString = false;
  let escaped = false;

  for (const filePath of filePaths) {
    process.stdout.write("Streaming GameData segment: " + filePath + "\n");
    tail = Buffer.alloc(0);
    for await (const chunk of fs.createReadStream(filePath)) {
      let i = 0;
      while (i < chunk.length) {
        if (!found) {
          const combined = tail.length ? Buffer.concat([tail, chunk.subarray(i)]) : chunk.subarray(i);
          const markerIndex = combined.indexOf(marker);
          if (markerIndex < 0) {
            const keep = Math.min(marker.length - 1, combined.length);
            tail = Buffer.from(combined.subarray(combined.length - keep));
            break;
          }
          found = true;
          awaitingArray = true;
          i += markerIndex - tail.length + marker.length;
          if (i < 0) i = 0;
          tail = Buffer.alloc(0);
          continue;
        }

        const b = chunk[i++];
        if (awaitingArray) {
          if (b === 0x20 || b === 0x09 || b === 0x0a || b === 0x0d) continue;
          if (b === 0x3a) continue;
          if (b !== 0x5b) {
            throw new Error("Found " + targetKey + " but its value is not an array in " + filePath);
          }
          awaitingArray = false;
          captureArray = true;
          depth = 1;
          captured.push(b);
          continue;
        }

        if (!captureArray) continue;
        captured.push(b);
        if (inString) {
          if (escaped) escaped = false;
          else if (b === 0x5c) escaped = true;
          else if (b === 0x22) inString = false;
        } else if (b === 0x22) inString = true;
        else if (b === 0x5b) depth++;
        else if (b === 0x5d) {
          depth--;
          if (depth === 0) {
            const parsed = JSON.parse(Buffer.from(captured).toString("utf8"));
            if (!Array.isArray(parsed)) throw new Error(targetKey + " is not an array.");
            return parsed;
          }
        }
      }
    }
  }
  throw new Error("Could not find array " + targetKey + " in " + filePaths.join(", "));
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
    mod_stats: {
      speed: {
        median: unit.mod_stats?.speed?.median ?? null,
        mean: unit.mod_stats?.speed?.mean ?? null,
      },
    },
    secondaries: {
      speed: { rolls_mean: unit.secondaries?.speed?.rolls_mean ?? null },
    },
    relic: { mean: unit.relic?.mean ?? null },
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
