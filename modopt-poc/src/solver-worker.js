import loadHighs from "highs";

const SLOT_NAMES = ["square", "arrow", "diamond", "triangle", "circle", "cross"];
const BAND_THRESHOLDS = [0.90, 0.95, 0.98, 1.02];
const BIG = 100000;
const SET_REWARD = 5000;
const KEEP_BONUS = 150;

// Synthetic fixture only. Values are illustrative units, not live SWGOH stats.
function makeFixture() {
  const rows = [];
  const setCycle = [1, 4, 2, 3, 1, 4, 5, 6];
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
    const highs = await loadHighs();
    const mods = makeFixture();
    const lp = buildModel(mods);
    const modelBuilt = performance.now();
    const result = highs.solve(lp, {
      output_flag: false,
      time_limit: 8,
      mip_rel_gap: 0.001,
    });
    const finished = performance.now();

    if (!result || !result.Status) throw new Error("HiGHS returned no solver status");

    const selected = mods
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

    self.postMessage({
      status: result.Status,
      objectiveValue: result.ObjectiveValue,
      selectedMods: selected,
      counts: {
        candidateMods: mods.length,
        slots: SLOT_NAMES.length,
        statBands: 2 * BAND_THRESHOLDS.length,
      },
      timingsMs: {
        initializationAndModelBuild: Number((modelBuilt - started).toFixed(2)),
        solve: Number((finished - modelBuilt).toFixed(2)),
        total: Number((finished - started).toFixed(2)),
      },
      note: "Synthetic model only; timings are browser/device dependent and do not yet measure the full optimizer workload.",
    });
  } catch (error) {
    self.postMessage({
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    });
  }
};
