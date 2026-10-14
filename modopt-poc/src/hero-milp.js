/**
 * JavaScript port of the per-hero MILP core from swgoh_modopt.py.
 *
 * This module intentionally accepts normalized data from Python (base stats,
 * parsed mods, set bonus definitions and keystats). It does not yet replace
 * the Python data-loading / exact in-game stat evaluation pipeline.
 */
const BAND_THRESHOLDS = [0.90, 0.95, 0.98, 1.02];
const BIG = 100000;
const DEFAULT_SET_REWARD = 5000;
const VIRTUAL_PENALTY = 800;
const SLOTS = [1, 2, 3, 4, 5, 6];

const number = (v, fallback = 0) => Number.isFinite(Number(v)) ? Number(v) : fallback;
const get = (obj, key) => number(obj?.[key], 0);

class MilpBuilder {
  constructor() {
    this.vars = new Map();
    this.rows = [];
    this.objective = new Map();
  }

  variable(name, { lb = 0, ub = 1, integer = true, objective = 0 } = {}) {
    if (this.vars.has(name)) throw new Error("Duplicate MILP variable: " + name);
    this.vars.set(name, { lb, ub, integer });
    if (objective) this.objective.set(name, objective);
    return name;
  }

  addObjective(name, coefficient) {
    this.objective.set(name, (this.objective.get(name) || 0) + coefficient);
  }

  row(name, terms, lb = -Infinity, ub = Infinity) {
    this.rows.push({ name, terms: new Map(Object.entries(terms).filter(([, v]) => v)), lb, ub });
  }

  static fmt(v) {
    if (!Number.isFinite(v)) throw new Error("Non-finite coefficient in MILP");
    return Number(v.toPrecision(12)).toString();
  }

  expression(terms) {
    const parts = [];
    for (const [name, coefficient] of terms) {
      if (!coefficient) continue;
      const sign = coefficient < 0 ? "-" : "+";
      parts.push({ sign, text: MilpBuilder.fmt(Math.abs(coefficient)) + " " + name });
    }
    if (!parts.length) return "0";
    return parts.map((p, i) => (i === 0 ? (p.sign === "-" ? "- " : "") : " " + p.sign + " ") + p.text).join("");
  }

  toLp() {
    const lines = ["Maximize", " obj: " + this.expression(this.objective)];
    lines.push("Subject To");
    for (const row of this.rows) {
      const lhs = this.expression(row.terms);
      if (row.lb === row.ub) lines.push(" " + row.name + ": " + lhs + " = " + MilpBuilder.fmt(row.lb));
      else {
        if (Number.isFinite(row.lb)) lines.push(" " + row.name + "_lo: " + lhs + " >= " + MilpBuilder.fmt(row.lb));
        if (Number.isFinite(row.ub)) lines.push(" " + row.name + "_hi: " + lhs + " <= " + MilpBuilder.fmt(row.ub));
      }
    }
    lines.push("Bounds");
    for (const [name, v] of this.vars) {
      if (v.integer && v.lb === 0 && v.ub === 1) continue;
      lines.push(" " + MilpBuilder.fmt(v.lb) + " <= " + name + " <= " + MilpBuilder.fmt(v.ub));
    }
    const binaries = [...this.vars].filter(([, v]) => v.integer && v.lb === 0 && v.ub === 1).map(([n]) => n);
    const generals = [...this.vars].filter(([, v]) => v.integer && !(v.lb === 0 && v.ub === 1)).map(([n]) => n);
    if (generals.length) lines.push("Generals", ...generals.map(n => " " + n));
    if (binaries.length) lines.push("Binaries", ...binaries.map(n => " " + n));
    lines.push("End");
    return lines.join("\n");
  }
}

function makeStatForm(modKey, base) {
  const stats = base.stats || {};
  const level = number(base.level);
  const K = level * 7.5 * 1e8;
  const form = { key: modKey, stats, kind: "linear" };
  if (modKey === "health") {
    form.kind = "health";
    form.B = get(stats, 1);
  } else if (modKey === "armor") {
    form.A0 = number(base.armor_flat);
    form.slope = 100 * K / Math.pow(form.A0 + K, 2);
  } else if (modKey === "resistance") {
    form.R0 = number(base.resist_flat);
    form.slope = 100 * K / Math.pow(form.R0 + K, 2);
  }
  return form;
}

function statMod(form, flat = {}, pct = {}) {
  const st = form.stats;
  switch (form.key) {
    case "protection": return get(st, 28) * get(pct, 56) / 100 + get(flat, 28);
    case "speed": return get(st, 5) * get(pct, 57) / 100 + get(flat, 5);
    case "physical_damage": return get(st, 6) * get(pct, 48) / 100 + get(flat, 41);
    case "special_damage": return get(st, 7) * get(pct, 48) / 100 + get(flat, 41);
    case "crit_damage": return get(pct, 16);
    case "potency": return get(pct, 17);
    case "tenacity": return get(pct, 18);
    case "crit_chance_pct": return get(pct, 53);
    case "armor": return form.slope * (get(flat, 42) * 1e8 + form.A0 * get(pct, 49) / 100);
    case "resistance": return form.slope * (form.R0 * get(pct, 49) / 100);
    default: return 0;
  }
}

function setBonusValue(form, bonus) {
  return statMod(form, {}, { [bonus.stat]: number(bonus.lvl15) / 1e6 });
}

function statExpression(mk, ctx, F0, P0) {
  const { forms, candidates, xs, groups, setBonuses } = ctx;
  const form = forms.get(mk);
  const terms = {};
  let constant = 0;
  if (form.kind === "health") {
    candidates.forEach((mod, i) => {
      const F = get(mod.flat, 1);
      const Pf = get(mod.pct, 55);
      terms[xs[i]] = F + form.B * Pf / 100 + (F0 * Pf + P0 * F) / 100;
    });
    if (groups.has(1)) terms[groups.get(1)] = (form.B * 10 + F0 * 10) / 100;
    constant = -F0 * P0 / 100;
  } else {
    candidates.forEach((mod, i) => {
      const v = statMod(form, mod.flat, mod.pct);
      if (v) terms[xs[i]] = v;
    });
    for (const [sid, variable] of groups) {
      const bonus = setBonuses[sid];
      if (!bonus) continue;
      const v = setBonusValue(form, bonus);
      if (v) terms[variable] = (terms[variable] || 0) + v;
    }
  }
  return { terms, constant };
}

function chooseCandidates(input, lock, forms, targets, keyKeys, alsoKeys) {
  const relevance = mod => {
    let score = 0;
    for (const [mk, form] of forms) {
      const target = Math.max(targets[mk], 1e-9);
      const v = mk === "health"
        ? get(mod.flat, 1) + form.B * get(mod.pct, 55) / 100
        : statMod(form, mod.flat, mod.pct);
      score += (keyKeys.some(([key]) => key === mk) ? 3 : 1) * v / target;
    }
    return score;
  };
  const cand = [];
  for (const slot of SLOTS) {
    const pool = input.modsAvailable.filter(m => Number(m.slot) === slot &&
      (!lock.has(slot) || Number(m.primary) === lock.get(slot)));
    const bySet = new Map();
    for (const mod of pool) {
      if (!bySet.has(Number(mod.set))) bySet.set(Number(mod.set), []);
      bySet.get(Number(mod.set)).push(mod);
    }
    for (const list of bySet.values()) {
      list.sort((a, b) => (relevance(b) + 0.05 * number(b.quality)) -
        (relevance(a) + 0.05 * number(a.quality)));
      cand.push(...list.slice(0, 30));
    }
    const already = new Set(cand.map(m => m.id));
    cand.push(...pool.filter(m => input.currentIds.includes(m.id) && !already.has(m.id)));
  }
  return cand;
}

/**
 * Solve one hero's MILP. Input is a JSON-safe normalized structure:
 * { base, modsAvailable, currentIds, keyStats, also, setBonuses, combos,
 *   primaryLock, strict, timeLimit, keepBonus, setReward }
 *
 * Each stat row needs { stat, mod_key, target }; mods need { id, slot, set,
 * primary, flat, pct, quality, owner?, virtual? }. setBonuses is keyed by
 * numeric set ID and each value is { count, stat, lvl15 }.
 */
export function buildHeroMilp(input, overrides = {}) {
  const opts = { ...input, ...overrides };
  const keyStats = opts.keyStats || [];
  const also = opts.also || [];
  if (!Array.isArray(opts.modsAvailable) || !opts.base || !opts.setBonuses) {
    throw new Error("Hero input requires base, modsAvailable, and setBonuses");
  }
  if (!keyStats.length) throw new Error("Hero input has no keyStats");
  for (const row of [...keyStats, ...also]) {
    if (!row.mod_key || !Number.isFinite(Number(row.target))) {
      throw new Error("Each stat row must include mod_key and numeric target");
    }
  }
  const forms = new Map();
  const targets = {};
  for (const row of [...keyStats, ...also]) {
    if (!forms.has(row.mod_key)) {
      forms.set(row.mod_key, makeStatForm(row.mod_key, opts.base));
      targets[row.mod_key] = number(row.target);
    }
  }
  const keyKeys = keyStats.map(r => [r.mod_key, r]);
  const alsoKeys = also.filter(r => !keyKeys.some(([k]) => k === r.mod_key)).map(r => [r.mod_key, r]);
  const currentIds = new Set(opts.currentIds || []);
  const lockedPrimary = new Map(Object.entries(opts.lockedPrimary || {}).map(([s, p]) => [Number(s), Number(p)]));
  const candidates = chooseCandidates({ ...opts, currentIds: [...currentIds] }, lockedPrimary, forms, targets, keyKeys, alsoKeys);
  if (new Set(candidates.map(m => Number(m.slot))).size !== 6) {
    throw new Error("slot sans mod disponible");
  }

  const P = new MilpBuilder();
  const xs = candidates.map((m, i) => P.variable("x_" + i, {
    lb: 0, ub: 1, integer: true,
    objective: (currentIds.has(m.id) ? number(opts.keepBonus, 150) : 0) -
      6 * number(m.quality) - (m.virtual ? VIRTUAL_PENALTY : 0),
  }));
  for (const slot of SLOTS) {
    const terms = {};
    candidates.forEach((m, i) => { if (Number(m.slot) === slot) terms[xs[i]] = 1; });
    P.row("one_mod_slot_" + slot, terms, 1, 1);
  }
  // Diagnostic mode: require the exact Python reference mods.
  if (opts.forceReferenceMods) {
    const expectedIds = [...new Set(opts.referenceMods || [])];
    const missing = expectedIds.filter(id => !candidates.some(mod => mod.id === id));
    if (missing.length) {
      throw new Error("Reference-forced diagnostic cannot run: expected mod(s) missing from candidate pool: " + missing.join(", "));
    }
    for (const id of expectedIds) {
      const index = candidates.findIndex(mod => mod.id === id);
      P.row("force_reference_mod_" + index, { [xs[index]]: 1 }, 1, 1);
    }
  }

  const groups = new Map();
  for (const [sidText, bonus] of Object.entries(opts.setBonuses)) {
    const sid = Number(sidText);
    const members = {};
    candidates.forEach((m, i) => { if (Number(m.set) === sid) members[xs[i]] = 1; });
    if (!Object.keys(members).length) continue;
    const need = Number(bonus.count);
    const g = P.variable("g_" + sid, { lb: 0, ub: Math.floor(6 / need), integer: true });
    const r = P.variable("r_" + sid, { lb: 0, ub: need - 1, integer: true });
    members[g] = -need;
    members[r] = -1;
    P.row("set_count_" + sid, members, 0, 0);
    groups.set(sid, g);
  }

  const combos = (opts.combos || []).slice(0, 4);
  if (combos.length) {
    const cv = combos.map((_, i) => P.variable("c_" + i, { lb: 0, ub: 1, integer: true }));
    P.row("one_target_combo", Object.fromEntries(cv.map(v => [v, 1])), opts.strict ? 1 : 0, 1);
    combos.forEach((combo, k) => {
      for (const [sidText, groupCount] of Object.entries(combo.groups || {})) {
        const sid = Number(sidText);
        if (!groups.has(sid)) {
          if (opts.strict) P.row("missing_set_" + k + "_" + sid, { [cv[k]]: 1 }, 0, 0);
          continue;
        }
        const y = P.variable("y_" + k + "_" + sid, {
          lb: 0, ub: Number(groupCount), integer: false,
          objective: number(opts.setReward, DEFAULT_SET_REWARD),
        });
        P.row("combo_y_g_" + k + "_" + sid, { [y]: 1, [groups.get(sid)]: -1 }, -Infinity, 0);
        P.row("combo_y_c_" + k + "_" + sid, { [y]: 1, [cv[k]]: -Number(groupCount) }, -Infinity, 0);
        if (opts.strict) {
          P.row("strict_set_" + k + "_" + sid, { [groups.get(sid)]: 1, [cv[k]]: -Number(groupCount) }, 0, Infinity);
        }
      }
    });
  }

  const statExpressions = {};
  for (const [mk] of keyKeys) {
    const { terms, constant } = statExpression(mk, { forms, candidates, xs, groups, setBonuses: opts.setBonuses }, number(opts.F0), number(opts.P0));
    const target = targets[mk];
    statExpressions[mk] = { terms, constant, target, kind: "key" };
    let previous = null;
    BAND_THRESHOLDS.forEach((threshold, band) => {
      const b = P.variable("b_" + mk + "_" + band, { lb: 0, ub: 1, integer: true, objective: BIG });
      const row = { ...terms, [b]: (terms[b] || 0) - threshold * target };
      P.row("stat_band_" + mk + "_" + band, row, -constant, Infinity);
      if (previous) P.row("stat_band_order_" + mk + "_" + band, { [b]: 1, [previous]: -1 }, -Infinity, 0);
      previous = b;
    });
  }
  for (const [mk] of alsoKeys) {
    const { terms, constant } = statExpression(mk, { forms, candidates, xs, groups, setBonuses: opts.setBonuses }, number(opts.F0), number(opts.P0));
    const target = Math.max(targets[mk], 1e-9);
    statExpressions[mk] = { terms, constant, target: targets[mk], kind: "also" };
    const z = P.variable("z_" + mk, { lb: 0, ub: 1000, integer: false, objective: 1 });
    const row = Object.fromEntries(Object.entries(terms).map(([name, v]) => [name, -v * 1000 / target]));
    row[z] = 1;
    P.row("also_progress_" + mk, row, -Infinity, constant * 1000 / target);
  }
  return { lp: P.toLp(), candidates, variableNames: xs, objective: P.objective, statExpressions };
}

function solveOnce(highs, input, lock, F0, P0, strict) {
  const model = buildHeroMilp(input, {
    lockedPrimary: Object.fromEntries(lock),
    F0, P0, strict,
  });
  const result = highs.solve(model.lp, {
    output_flag: false,
    time_limit: number(input.timeLimit, 8),
    mip_rel_gap: 0.001,
  });
  if (!result?.Columns) return { chosen: null, info: { status: result?.Status || "No solution" } };
  const chosen = model.candidates.filter((_, i) =>
    number(result.Columns[model.variableNames[i]]?.Primal) > 0.5);
  if (chosen.length !== 6 || new Set(chosen.map(m => Number(m.slot))).size !== 6) {
    return { chosen: null, info: { status: result.Status, message: "Solver result did not select exactly one mod per slot" } };
  }
  // Break down the objective so parity differences can be attributed to the
  // dominant stat-band rewards versus mod quality/current-mod and set rewards.
  const objectiveBreakdown = { modTerms: 0, statBands: {}, setComboRewards: 0, other: 0 };
  const activeStatBands = {};
  for (const [name, coefficient] of model.objective) {
    const primal = number(result.Columns[name]?.Primal);
    const contribution = coefficient * primal;
    if (name.startsWith("x_")) objectiveBreakdown.modTerms += contribution;
    else if (name.startsWith("b_")) {
      objectiveBreakdown.statBands[name] = contribution;
      if (primal > 0.5) activeStatBands[name] = true;
    } else if (name.startsWith("y_")) objectiveBreakdown.setComboRewards += contribution;
    else objectiveBreakdown.other += contribution;
  }
  objectiveBreakdown.modTerms = Number(objectiveBreakdown.modTerms.toFixed(6));
  objectiveBreakdown.setComboRewards = Number(objectiveBreakdown.setComboRewards.toFixed(6));
  objectiveBreakdown.other = Number(objectiveBreakdown.other.toFixed(6));
  for (const key of Object.keys(objectiveBreakdown.statBands)) {
    if (Math.abs(objectiveBreakdown.statBands[key]) < 1e-8) delete objectiveBreakdown.statBands[key];
  }
  const statDiagnostics = {};
  for (const [mk, expr] of Object.entries(model.statExpressions)) {
    let value = expr.constant;
    for (const [name, coefficient] of Object.entries(expr.terms)) {
      value += coefficient * number(result.Columns[name]?.Primal);
    }
    const ratio = expr.target ? value / expr.target : null;
    statDiagnostics[mk] = {
      value: Number(value.toFixed(4)),
      target: expr.target,
      ratio: ratio === null ? null : Number(ratio.toFixed(6)),
      bandsSatisfied: ratio === null ? 0 : BAND_THRESHOLDS.filter(threshold => ratio >= threshold).length,
      kind: expr.kind,
    };
  }
  const referenceIds = new Set(input.referenceMods || []);
  const referenceCandidates = model.candidates.filter(mod => referenceIds.has(mod.id)).map(mod => mod.id);
  const modObjectiveDetails = chosen.map(mod => {
    const isCurrent = currentIds.has(mod.id);
    const keepBonus = isCurrent ? number(opts.keepBonus, 150) : 0;
    const qualityPenalty = 6 * number(mod.quality);
    const virtualPenalty = mod.virtual ? VIRTUAL_PENALTY : 0;
    return {
      id: mod.id,
      slot: Number(mod.slot),
      isCurrent,
      quality: Number(number(mod.quality).toFixed(6)),
      keepBonus: Number(keepBonus.toFixed(6)),
      qualityPenalty: Number(qualityPenalty.toFixed(6)),
      virtualPenalty: Number(virtualPenalty.toFixed(6)),
      contribution: Number((keepBonus - qualityPenalty - virtualPenalty).toFixed(6)),
    };
  });
  return { chosen, info: {
    status: result.Status,
    n_candidates: model.candidates.length,
    objectiveValue: result.ObjectiveValue,
    objectiveBreakdown,
    modObjectiveDetails,
    activeStatBands: Object.keys(activeStatBands),
    statDiagnostics,
    referenceCandidateCount: referenceCandidates.length,
    referenceCandidates,
    referenceMods: [...referenceIds],
  } };
}

/** Runs the original three-pass health linearization and primary-lock fallback. */
export function solveHero(highs, input) {
  const currentIds = new Set(input.currentIds || []);
  const current = (input.modsAvailable || []).filter(m => currentIds.has(m.id));
  let F0 = current.reduce((sum, m) => sum + get(m.flat, 1), 0);
  let P0 = current.reduce((sum, m) => sum + get(m.pct, 55), 0);
  const forms = [...(input.keyStats || []), ...(input.also || [])].map(r => r.mod_key);
  const iterations = forms.includes("health") ? 3 : 1;
  const lock = new Map(Object.entries(input.lockedPrimary || {}).map(([s, p]) => [Number(s), Number(p)]));
  const seen = new Set();
  let last;
  for (let i = 0; i < iterations; i += 1) {
    last = solveOnce(highs, input, lock, F0, P0, Boolean(input.strict));
    if (!last.chosen && lock.size) {
      lock.clear();
      last = solveOnce(highs, input, lock, F0, P0, Boolean(input.strict));
    }
    if (!last.chosen) return { chosen: null, info: last.info };
    const signature = last.chosen.map(m => m.id).sort().join("|");
    if (seen.has(signature)) break;
    seen.add(signature);
    F0 = last.chosen.reduce((sum, m) => sum + get(m.flat, 1), 0);
    P0 = last.chosen.reduce((sum, m) => sum + get(m.pct, 55), 0) +
      10 * Math.floor(last.chosen.filter(m => Number(m.set) === 1).length / 2);
  }
  return last;
}
