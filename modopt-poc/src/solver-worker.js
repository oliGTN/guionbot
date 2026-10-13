import loadHighs from "highs";
import highsWasmUrl from "../node_modules/highs/build/highs.wasm?url";
import { solveHero } from "./hero-milp.js";

const SLOT_NAMES = ["square", "arrow", "diamond", "triangle", "circle", "cross"];
const BAND_THRESHOLDS = [0.90, 0.95, 0.98, 1.02];
const BIG = 100000;
const SET_REWARD = 5000;
const KEEP_BONUS = 150;

// Synthetic fixture only. Values are illustrative units, not live SWGOH stats.
function makeFixture() {
  const rows = [];
  const setCycle = [1, 4, 2, 3, 5, 6, 7, 8];
  const speed = [
    [8, 12, 17], [10, 15, 20], [7, 13, 18],
    [9, 14, 19], [11, 16, 21], [8, 15, 22],
  ];
  const health = [
    [120, 180, 220], [130, 170, 240], [110, 190, 250],
    [140, 200, 230], [125, 185, 260], [135, 195, 245],
  ];

  for (let slot = 0; slot < 6; slot += 1) {
    for (let choice = 0; choice < 3; choice += 1) {
      rows.push({
        id: "mod_" + (slot + 1) + "_" + (choice + 1),
        slot: slot + 1,
        set: setCycle[(slot + choice * 2) % setCycle.length],
        speed: speed[slot][choice],
        health: health[slot][choice],
        quality: [4, 7, 9][choice] + (slot % 2),
        current: choice === 0,
      });
    }
  }
  return rows;
}

function fmt(value) {
  if (!Number.isFinite(value)) throw new Error("Non-finite coefficient in LP model");
  return Number(value.toFixed(8)).toString();
}

function expression(terms) {
  let output = "";
  for (const [name, coefficient] of terms) {
    if (!coefficient) continue;
    const sign = coefficient < 0 ? " - " : output ? " + " : "";
    output += sign + fmt(Math.abs(coefficient)) + " " + name;
  }
  return output || "0";
}

function buildModel(mods) {
  const lines = ["Maximize"];
  const objective = [];

  for (const mod of mods) {
    // A positive quality number is a cost, as in swgoh_modopt.py.
    objective.push(["x_" + mod.id, (mod.current ? KEEP_BONUS : 0) - 6 * mod.quality]);
  }
  for (const setId of [1, 2, 3, 4, 5, 6, 7, 8]) {
    objective.push(["g_" + setId, SET_REWARD]);
  }
  for (const stat of ["speed", "health"]) {
    for (let band = 0; band < BAND_THRESHOLDS.length; band += 1) {
      objective.push(["b_" + stat + "_" + band, BIG]);
    }
  }

  lines.push(" objective: " + expression(objective));
  lines.push("Subject To");

  for (let slot = 1; slot <= 6; slot += 1) {
    lines.push("one_mod_slot_" + slot + ": " +
      expression(mods.filter(m => m.slot === slot).map(m => ["x_" + m.id, 1])) + " = 1");
  }

  // Exact set-group accounting: selected mods = setSize * groups + remainder.
  const setSizes = { 1: 2, 2: 4, 3: 2, 4: 4, 5: 2, 6: 4, 7: 2, 8: 2 };
  for (const [setIdText, setSize] of Object.entries(setSizes)) {
    const setId = Number(setIdText);
    const members = mods.filter(m => m.set === setId).map(m => ["x_" + m.id, 1]);
    if (!members.length) continue;
    lines.push("set_count_" + setId + ": " +
      expression([...members, ["g_" + setId, -setSize], ["r_" + setId, -1]]) + " = 0");
  }

  const statTargets = { speed: 100, health: 1200 };
  for (const stat of Object.keys(statTargets)) {
    const terms = mods.map(m => ["x_" + m.id, m[stat]]);
    // Illustrative set bonus, added linearly per completed group.
    if (stat === "speed") terms.push(["g_4", 5]);
    if (stat === "health") terms.push(["g_1", 60]);

    for (let band = 0; band < BAND_THRESHOLDS.length; band += 1) {
      const threshold = BAND_THRESHOLDS[band];
      lines.push(stat + "_band_" + band + ": " +
        expression([...terms, ["b_" + stat + "_" + band, -threshold * statTargets[stat]]]) + " >= 0");
      if (band > 0) {
        lines.push(stat + "_band_order_" + band + ": b_" + stat + "_" + band +
          " - b_" + stat + "_" + (band - 1) + " <= 0");
      }
    }
  }

  lines.push("Bounds");
  for (const setId of [1, 2, 3, 4, 5, 6, 7, 8]) {
    const setSize = setSizes[setId];
    lines.push("0 <= g_" + setId + " <= " + Math.floor(6 / setSize));
    lines.push("0 <= r_" + setId + " <= " + (setSize - 1));
  }

  lines.push("Generals");
  for (const setId of [1, 2, 3, 4, 5, 6, 7, 8]) {
    lines.push("g_" + setId + " r_" + setId);
  }

  lines.push("Binaries");
  for (const mod of mods) lines.push("x_" + mod.id);
  for (const stat of ["speed", "health"]) {
    for (let band = 0; band < BAND_THRESHOLDS.length; band += 1) {
      lines.push("b_" + stat + "_" + band);
    }
  }
  lines.push("End");

  return lines.join("\n");
}

self.onmessage = async ({ data }) => {
  if (data?.type !== "run") return;

  const started = performance.now();
  try {
    const highs = await loadHighs({ locateFile: () => highsWasmUrl });
    const solverReady = performance.now();
    const operationStarted = performance.now();
    let result;
    let selected;
    let counts;
    let note;

    if (data.mode === "batch" && Array.isArray(data.inputs)) {
      const results = [];
      const total = data.inputs.length;
      const sequentialAllocation = data.sequentialAllocation === true;
      const usedModIds = new Set();
      for (let index = 0; index < total; index += 1) {
        const item = data.inputs[index];
        self.postMessage({ type: "progress", completed: index, total, heroId: item.heroId });
        // Yield between heroes so the browser can render progress updates.
        await new Promise(resolve => setTimeout(resolve, 0));
        try {
          // Python removes each hero's assigned mods from the pool before solving the next.
          // Keep the original input untouched so candidate counts and current IDs remain inspectable.
          const solveInput = sequentialAllocation
            ? { ...item.input, modsAvailable: item.input.modsAvailable.filter(mod => !usedModIds.has(mod.id)) }
            : item.input;
          const solved = solveHero(highs, solveInput);
          let referenceForcedDiagnostic;
          const referenceIds = [...new Set(item.input.referenceMods || [])];
          if (referenceIds.length === 6) {
            try {
              const forced = solveHero(highs, { ...solveInput, forceReferenceMods: true });
              referenceForcedDiagnostic = {
                status: forced.info?.status ?? null,
                objectiveValue: forced.info?.objectiveValue ?? null,
                objectiveBreakdown: forced.info?.objectiveBreakdown ?? null,
                activeStatBands: forced.info?.activeStatBands ?? [],
                normalObjectiveBreakdown: solved.info?.objectiveBreakdown ?? null,
                normalActiveStatBands: solved.info?.activeStatBands ?? [],
                objectiveDeltaVsNormal: Number.isFinite(Number(forced.info?.objectiveValue)) && Number.isFinite(Number(solved.info?.objectiveValue))
                  ? Number((Number(forced.info.objectiveValue) - Number(solved.info.objectiveValue)).toFixed(6))
                  : null,
                selectedModIds: (forced.chosen || []).map(mod => mod.id).sort(),
                expectedModIds: referenceIds.slice().sort(),
                exactAssignmentSelected: Boolean(forced.chosen && forced.chosen.length === 6 && referenceIds.every(id => forced.chosen.some(mod => mod.id === id))),
                note: "Objective value for the Python assignment forced into the browser MILP; compare with the normal browser objective within this browser model."
              };
            } catch (error) {
              referenceForcedDiagnostic = { status: "diagnostic-error", objectiveValue: null, expectedModIds: referenceIds.slice().sort(), error: error instanceof Error ? error.message : String(error) };
            }
          } else {
            referenceForcedDiagnostic = { status: "not-run", expectedModCount: referenceIds.length, note: "A six-mod Python reference assignment is required." };
          }
          const chosen = (solved.chosen || []).slice().sort((a, b) => a.slot - b.slot).map(mod => ({
            slot: SLOT_NAMES[mod.slot - 1], id: mod.id, set: mod.set, primary: mod.primary,
            speed: Number(mod.flat?.[5] || 0) + Number(mod.pct?.[57] || 0),
            current: (item.input.currentIds || []).includes(mod.id),
          }));
          if (sequentialAllocation) {
            for (const mod of chosen) usedModIds.add(mod.id);
          }
          results.push({ heroId: item.heroId, status: solved.info?.status, objectiveValue: solved.info?.objectiveValue ?? null,
            objectiveBreakdown: solved.info?.objectiveBreakdown ?? null,
            activeStatBands: solved.info?.activeStatBands ?? [],
            selectedMods: chosen, counts: { candidateMods: solved.info?.n_candidates ?? null, slots: 6 },
            referenceForcedDiagnostic,
            referenceDiagnostics: {
              expectedModIds: solved.info?.referenceMods ?? item.input.referenceMods ?? [],
              expectedModsInCandidatePool: solved.info?.referenceCandidates ?? [],
              expectedModsInCandidatePoolCount: solved.info?.referenceCandidateCount ?? 0,
              expectedModsSelected: chosen.filter(mod => (solved.info?.referenceMods ?? item.input.referenceMods ?? []).includes(mod.id)).map(mod => mod.id),
            },
            allocationMode: sequentialAllocation ? "sequential" : "independent",
            modsReservedByEarlierHeroes: sequentialAllocation ? usedModIds.size - chosen.length : 0 });
        } catch (error) {
          results.push({ heroId: item.heroId, error: error instanceof Error ? error.message : String(error) });
        }
        self.postMessage({ type: "progress", completed: index + 1, total, heroId: item.heroId });
      }
      self.postMessage({ mode: "batch", results, allocationMode: sequentialAllocation ? "sequential" : "independent", timingsMs: { initialization: Number((solverReady - started).toFixed(2)), total: Number((performance.now() - started).toFixed(2)) }, note: sequentialAllocation ? "Sequential roster allocation in input priority order. Mods chosen for earlier heroes are excluded from later candidate pools. Mods equipped on unselected heroes remain locked by input normalization." : "Independent single-hero diagnostic; this does not model mods reserved by earlier heroes. Compare with a full sequential batch for roster parity." });
      return;
    }

    if (data.mode === "hero" && data.input) {
      result = solveHero(highs, data.input);
      selected = (result.chosen || []).slice().sort((a, b) => a.slot - b.slot).map(mod => ({
        slot: SLOT_NAMES[mod.slot - 1],
        id: mod.id,
        set: mod.set,
        primary: mod.primary,
        speed: Number(mod.flat?.[5] || 0) + Number(mod.pct?.[57] || 0),
        current: (data.input.currentIds || []).includes(mod.id),
      }));
      counts = { candidateMods: result.info?.n_candidates ?? null, slots: SLOT_NAMES.length };
      note = "Normalized single-hero input; exact in-game evaluation and multi-hero inventory allocation are not included.";
    } else {
      const mods = makeFixture();
      const lp = buildModel(mods);
      result = highs.solve(lp, {
        output_flag: false,
        time_limit: 8,
        mip_rel_gap: 0.001,
      });
      if (!result || !result.Status) throw new Error("HiGHS returned no solver status");
      selected = mods
        .filter(mod => (result.Columns?.["x_" + mod.id]?.Primal ?? 0) > 0.5)
        .sort((a, b) => a.slot - b.slot)
        .map(mod => ({
          slot: SLOT_NAMES[mod.slot - 1],
          id: mod.id,
          set: mod.set,
          speed: mod.speed,
          health: mod.health,
          current: mod.current,
        }));
      counts = { candidateMods: mods.length, slots: SLOT_NAMES.length, statBands: 2 * BAND_THRESHOLDS.length };
      note = "Synthetic model only; timings are browser/device dependent and do not yet measure the full optimizer workload.";
    }
    const operationFinished = performance.now();

    self.postMessage({
      status: data.mode === "hero" ? result.info?.status : result.Status,
      objectiveValue: data.mode === "hero" ? result.info?.objectiveValue : result.ObjectiveValue,
      selectedMods: selected,
      counts,
      timingsMs: {
        initialization: Number((solverReady - started).toFixed(2)),
        modelAndSolve: Number((operationFinished - operationStarted).toFixed(2)),
        total: Number((operationFinished - started).toFixed(2)),
      },
      note,
    });
  } catch (error) {
    self.postMessage({
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    });
  }
};
