/**
 * Normalize Grandivory progress + Python optimizer data into hero-milp.js input.
 * This deliberately rejects unknown mod stat labels instead of silently scoring them as zero.
 */
const SLOT_ID = { square: 1, arrow: 2, diamond: 3, triangle: 4, circle: 5, cross: 6 };
const SET_ID = { health: 1, offense: 2, defence: 3, defense: 3, speed: 4, critchance: 5, crit_chance: 5, critdamage: 6, crit_damage: 6, potency: 7, tenacity: 8 };
const STAT_ID = {
  health: 1, speed: 5, physical_damage: 6, physicaldamage: 6, physdmg: 6,
  special_damage: 7, specialdamage: 7, specdmg: 7, protection: 28, offense: 41,
  physical_offense: 41, special_offense: 41, defense: 42, defence: 42,
  crit_damage: 16, critdamage: 16, potency: 17, tenacity: 18,
  offense_pct: 48, physical_damage_pct: 48, special_damage_pct: 48,
  defense_pct: 49, defence_pct: 49, accuracy_pct: 52, crit_chance_pct: 53,
  critical_chance_pct: 53, crit_avoid_pct: 54, critical_avoidance_pct: 54,
  health_pct: 55, protection_pct: 56, speed_pct: 57,
};
const LABEL_TO_STAT = {
  health: 1, protection: 28, speed: 5, offense: 41, "physical damage": 41,
  "special damage": 41, defense: 42, defence: 42, "offense %": 48, "physical damage %": 48,
  "special damage %": 48, "defense %": 49, "defence %": 49, "accuracy %": 52,
  "critical chance %": 53, "crit chance %": 53, "critical avoidance %": 54,
  "crit avoidance %": 54, "health %": 55, "protection %": 56, "speed %": 57,
  "critical damage %": 16, "crit damage %": 16, "potency %": 17, "tenacity %": 18,
};
const PCT_IDS = new Set([16, 17, 18, 48, 49, 52, 53, 54, 55, 56, 57]);
const SLOT_NAME = Object.fromEntries(Object.entries(SLOT_ID).map(([k, v]) => [v, k]));

function obj(v) { return v !== null && typeof v === "object" && !Array.isArray(v); }
function cleanKey(v) { return String(v ?? "").trim().toLowerCase().replace(/[%-]/g, m => m === "%" ? "_pct" : "_").replace(/[\s/]+/g, "_").replace(/__+/g, "_").replace(/^_|_$/g, ""); }
function statId(label) {
  const raw = String(label ?? "").trim();
  const normalized = cleanKey(raw);
  const spaced = raw.toLowerCase().replace(/\s+/g, " ").trim();
  return STAT_ID[normalized] ?? LABEL_TO_STAT[spaced] ?? null;
}
function numeric(v, label) {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  const s = String(v ?? "").replace(/,/g, "").replace(/%/g, "").trim();
  const n = Number(s);
  if (s && Number.isFinite(n)) return n;
  throw new Error("Invalid numeric value for " + label + ": " + String(v));
}
function firstNumber(object, keys) {
  for (const k of keys) if (object?.[k] !== undefined && object?.[k] !== null && object[k] !== "") {
    const n = Number(object[k]);
    if (Number.isFinite(n)) return n;
  }
  return null;
}
function getRawStatId(stat) {
  const id = Number(stat?.unitStatId);
  return Number.isFinite(id) ? id : null;
}
function getRawStatValue(stat) {
  if (!stat) return null;
  const v = stat.unscaledDecimalValue ?? stat.statValueDecimal;
  if (v === undefined || v === null) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export function normalizeSetBonuses(gameData) {
  if (!Array.isArray(gameData?.statModSet)) throw new Error('GameData.json is missing the "statModSet" array.');
  const bonuses = {};
  for (const entry of gameData.statModSet) {
    const id = Number(entry.id);
    const count = Number(entry.setCount);
    const stat = entry.completeBonus?.stat?.stat;
    const statIdValue = getRawStatId(stat);
    const lvl15 = getRawStatValue(entry.maxLevelBonus?.stat?.stat ?? stat);
    if (!Number.isInteger(id) || !Number.isInteger(count) || !statIdValue || lvl15 === null) continue;
    bonuses[id] = { count, stat: statIdValue, lvl15 };
  }
  if (Object.keys(bonuses).length < 8) {
    throw new Error("Only " + Object.keys(bonuses).length + " set bonuses were parsed; expected all 8.");
  }
  return bonuses;
}

function normalizeMod(raw, index) {
  if (!obj(raw)) throw new Error("Mod at index " + index + " is not an object.");
  const slotKey = String(raw.slot ?? "").toLowerCase();
  const slot = SLOT_ID[slotKey] ?? Number(raw.slot);
  const setKey = cleanKey(raw.set);
  const set = SET_ID[setKey] ?? Number(raw.set);
  const primary = statId(raw.primaryBonusType);
  if (!Number.isInteger(slot) || slot < 1 || slot > 6) throw new Error("Unsupported slot on mod " + (raw.mod_uid ?? index) + ": " + raw.slot);
  if (!Number.isInteger(set) || set < 1 || set > 8) throw new Error("Unsupported set on mod " + (raw.mod_uid ?? index) + ": " + raw.set);
  if (!primary) throw new Error("Unsupported primary stat on mod " + (raw.mod_uid ?? index) + ": " + raw.primaryBonusType);
  const flat = {}, pct = {};
  const primaryValue = numeric(raw.primaryBonusValue, "primaryBonusValue");
  (PCT_IDS.has(primary) ? pct : flat)[primary] = primaryValue;
  let quality = 0;
  for (let i = 1; i <= 4; i += 1) {
    const type = raw["secondaryType_" + i];
    const value = raw["secondaryValue_" + i];
    if (type === undefined || type === null || String(type).trim() === "" || value === undefined || value === null || String(value).trim() === "") continue;
    const sid = statId(type);
    if (!sid) throw new Error("Unsupported secondary stat on mod " + (raw.mod_uid ?? index) + ": " + type);
    (PCT_IDS.has(sid) ? pct : flat)[sid] = (PCT_IDS.has(sid) ? (pct[sid] || 0) : (flat[sid] || 0)) + numeric(value, "secondaryValue_" + i);
    const roll = firstNumber(raw, ["secondaryRoll_" + i]);
    if (roll !== null) quality += roll * (sid === 5 ? 2 : 1);
  }
  const id = String(raw.mod_uid ?? raw.id ?? "grandivory-mod-" + index);
  return {
    id, set, slot, pips: Number(raw.pips ?? 0), level: Number(raw.level ?? 0),
    owner: String(raw.characterID ?? "").trim(), primary, flat, pct, quality,
    rawGrandivory: raw,
  };
}

function baseFromGrandivory(character) {
  const pv = character?.playerValues;
  const stats = pv?.baseStats;
  if (!obj(stats)) throw new Error("Character is missing playerValues.baseStats.");
  const result = {};
  const mappings = {
    1: ["health"], 5: ["speed"], 6: ["physDmg", "physicalDamage", "physical_damage"],
    7: ["specDmg", "specialDamage", "special_damage"], 28: ["protection"],
    41: ["offense", "physicalOffense", "physical_offense"], 42: ["defense", "defence"],
  };
  for (const [sid, keys] of Object.entries(mappings)) {
    const value = firstNumber(stats, keys);
    if (value !== null) result[sid] = value;
  }
  // The Python model's armor/resistance linearization needs the underlying rating,
  // not the displayed percentage. Don't fabricate that rating from display stats.
  const level = firstNumber(pv, ["level"]) ?? 85;
  return { level, stats: result, armor_flat: firstNumber(stats, ["armorFlat", "armor_flat"]), resist_flat: firstNumber(stats, ["resistanceFlat", "resistance_flat"]) };
}

function normalizedKeystats(ksHero) {
  const convert = row => ({ ...row, mod_key: row.mod_key || ({
    health: "health", protection: "protection", speed: "speed", offense: "physical_damage",
    physical_damage: "physical_damage", special_damage: "special_damage", armor: "armor",
    resistance: "resistance", crit_damage: "crit_damage", potency: "potency",
    tenacity: "tenacity", crit_chance: "crit_chance_pct",
  }[row.stat] || row.stat) });
  return {
    keyStats: (ksHero.key_stats || []).map(convert),
    also: (ksHero.also || []).map(convert),
  };
}

function comboFromTarget(target, setBonuses) {
  const groups = {};
  for (const [name, countValue] of Object.entries(target?.setRestrictions || {})) {
    const sid = SET_ID[cleanKey(name)];
    const count = Number(countValue);
    if (sid && count > 0 && Number.isFinite(count)) groups[sid] = Math.floor(count);
  }
  if (!Object.keys(groups).length) return null;
  return [{ name: "Grandivory set restrictions", pct: 100, groups }];
}

function primaryLocks(target) {
  const locks = {};
  for (const [slotName, label] of Object.entries(target?.primaryStatRestrictions || {})) {
    const slot = SLOT_ID[String(slotName).toLowerCase()];
    const sid = statId(label);
    if (slot && sid) locks[slot] = sid;
  }
  return locks;
}

export function prepareHeroInput(progress, gameData, keystats, heroId, options = {}) {
  const profile = progress?.profiles?.[0];
  if (!profile || !obj(profile.characters) || !Array.isArray(profile.mods)) {
    throw new Error("Expected Grandivory progress JSON with profiles[0].characters and profiles[0].mods.");
  }
  const selected = (profile.selectedCharacters || []).find(c => c?.id === heroId);
  const character = profile.characters[heroId];
  if (!character) throw new Error("Character " + heroId + " is not present in the Grandivory profile.");
  if (!selected?.target) throw new Error("Character " + heroId + " has no selectedCharacters target settings.");
  const ksHero = keystats?.heroes?.[heroId];
  if (!ksHero?.key_stats?.length) throw new Error("No key-stat data for " + heroId + " in keystats.json.");
  const { keyStats, also } = normalizedKeystats(ksHero);
  const base = baseFromGrandivory(character);
  const needsArmor = [...keyStats, ...also].some(r => ["armor", "resistance"].includes(r.mod_key));
  if (needsArmor && (!Number.isFinite(base.armor_flat) || !Number.isFinite(base.resist_flat))) {
    throw new Error(heroId + " uses armor/resistance as an optimization stat, but this Grandivory export does not provide the underlying defense/resistance rating required for the Python-equivalent formula. This hero must be skipped until GameData stat progression is ported.");
  }
  for (const row of [...keyStats, ...also]) {
    if (!Number.isFinite(Number(row.target)) || Number(row.target) <= 0) throw new Error("Invalid keystats target for " + heroId + ": " + row.stat);
    if (["physical_damage", "special_damage"].includes(row.mod_key) && !base.stats[ row.mod_key === "physical_damage" ? 6 : 7 ]) {
      throw new Error("Missing base damage stat required for " + heroId + ": " + row.mod_key);
    }
  }
  const allMods = profile.mods.map(normalizeMod);
  const modsAvailable = allMods.filter(m => m.level >= 15 && m.pips >= 5 && (!options.lockUnselected || !m.owner || (profile.selectedCharacters || []).some(c => c.id === m.owner)));
  const currentIds = allMods.filter(m => m.owner === heroId).map(m => m.id);
  const setBonuses = normalizeSetBonuses(gameData);
  const combos = comboFromTarget(selected.target, setBonuses) || (ksHero.sets?.combos || [])
    .filter(c => Number(c.pct || 0) >= 25 && c.sets)
    .slice(0, 4)
    .map(c => ({
      name: c.combo, pct: c.pct,
      groups: Object.fromEntries(Object.entries(c.sets).map(([name, count]) => [SET_ID[cleanKey(name)], Math.floor(Number(count) / setBonuses[SET_ID[cleanKey(name)]].count)]).filter(([sid, n]) => sid && n > 0)),
    }));
  return {
    heroId, base, modsAvailable, currentIds, keyStats, also, setBonuses, combos,
    lockedPrimary: primaryLocks(selected.target),
    strict: Boolean(selected.target.useOnlyFullSets),
    timeLimit: Number(options.timeLimit || 8),
    keepBonus: 150,
    setReward: 5000,
    sourceCounts: {
      profileMods: profile.mods.length,
      normalizedMods: allMods.length,
      eligibleMods: modsAvailable.length,
      ownedByHero: currentIds.length,
    },
  };
}

export function summarizePreparedHero(input) {
  return {
    heroId: input.heroId,
    baseStatIds: Object.keys(input.base.stats),
    keyStats: input.keyStats.map(({ stat, mod_key, target }) => ({ stat, mod_key, target })),
    also: input.also.map(({ stat, mod_key, target }) => ({ stat, mod_key, target })),
    candidateMods: input.modsAvailable.length,
    currentMods: input.currentIds.length,
    setBonuses: Object.keys(input.setBonuses).length,
    combos: input.combos.length,
    lockedPrimary: input.lockedPrimary,
  };
}
