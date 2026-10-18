import { EMBEDDED_OPTIMIZER_DATA } from "./optimizer-data.generated.js";
import { prepareHeroInput, summarizePreparedHero } from "./grandivory-normalize.js";
const fileInput = document.querySelector("#progress-file");
const status = document.querySelector("#file-status");
const summary = document.querySelector("#summary");
const summaryFields = document.querySelector("#summary-fields");
const structure = document.querySelector("#structure");
const errorOutput = document.querySelector("#error");

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function firstArray(object, keys) {
  for (const key of keys) {
    if (Array.isArray(object?.[key])) return { key, value: object[key] };
  }
  return null;
}

function countBy(items, getKey) {
  const counts = {};
  for (const item of items) {
    const key = getKey(item);
    const label = key === null || key === undefined || key === "" ? "(empty)" : String(key);
    counts[label] = (counts[label] || 0) + 1;
  }
  return counts;
}

function describeShape(value) {
  if (Array.isArray(value)) {
    const sample = value[0];
    return {
      type: "array",
      length: value.length,
      firstEntryType: sample === undefined ? null : Array.isArray(sample) ? "array" : typeof sample,
      firstEntryKeys: isObject(sample) ? Object.keys(sample) : [],
    };
  }
  if (isObject(value)) {
    const keys = Object.keys(value);
    const firstKey = keys[0];
    const sample = firstKey === undefined ? undefined : value[firstKey];
    return {
      type: "object",
      keyCount: keys.length,
      firstKeys: keys.slice(0, 12),
      firstValueType: sample === undefined ? null : Array.isArray(sample) ? "array" : typeof sample,
      firstValueKeys: isObject(sample) ? Object.keys(sample) : [],
    };
  }
  return { type: value === null ? "null" : typeof value };
}

function addField(label, value) {
  const term = document.createElement("dt");
  term.textContent = label;
  const description = document.createElement("dd");
  description.textContent = String(value);
  summaryFields.append(term, description);
}

function inspectProgressFile(data, file) {
  if (!isObject(data)) throw new Error("The JSON root must be an object.");

  const profiles = data.profiles;
  if (!Array.isArray(profiles) || profiles.length === 0 || !isObject(profiles[0])) {
    throw new Error('Unsupported progress export: expected a non-empty "profiles" array.');
  }

  const profile = profiles[0];
  const modsEntry = firstArray(profile, ["mods"]);
  if (!modsEntry) {
    throw new Error('The first profile has no "mods" array. Select the Grandivory progress export JSON.');
  }

  const mods = modsEntry.value;
  const validMods = mods.filter(isObject);
  const charactersValue = profile.characters;
  const characterMap = isObject(charactersValue) ? charactersValue : null;
  const charactersArray = firstArray(profile, ["characters", "roster", "units", "rosterUnit"]);
  const selectedCharacters = firstArray(profile, ["selectedCharacters", "selected_characters"]);
  const assignments = firstArray(profile, ["modAssignments", "mod_assignments"]);
  const validCharacters = charactersArray ? charactersArray.value.filter(isObject) : [];
  const withCharacterID = validMods.filter((mod) =>
    typeof mod.characterID === "string" && mod.characterID.trim() !== ""
  ).length;
  const withoutCharacterID = validMods.filter((mod) =>
    mod.characterID === undefined || mod.characterID === null || String(mod.characterID).trim() === ""
  ).length;
  const profileName = profile.playerName ?? profile.name ?? profile.profileName ?? "(not present)";

  summaryFields.replaceChildren();
  addField("File", file.name);
  addField("Size", (file.size / 1024).toFixed(1) + " KiB");
  addField("Player profile", profileName);
  addField("Profiles in file", profiles.length);
  addField("Characters container", describeShape(charactersValue).type);
  addField("Character entries", charactersArray ? charactersArray.value.length : isObject(charactersValue) ? Object.keys(charactersValue).length : "not detected");
  addField("Mods in first profile", mods.length);
  addField("Mod entries that are objects", validMods.length);
  addField('Mods with non-empty "characterID"', withCharacterID);
  addField('Mods with missing/empty "characterID"', withoutCharacterID);
  addField("Selected-character entries", selectedCharacters ? selectedCharacters.value.length : "not found as an array");
  addField("Mod-assignment entries", assignments ? assignments.value.length : "not found as an array");

  const sampleMod = validMods[0] ?? null;
  const sampleCharacter = validCharacters[0] ?? (isObject(charactersValue) ? Object.values(charactersValue).find(isObject) ?? null : null);
  const sampleCharacterId = sampleCharacter && isObject(charactersValue)
    ? Object.keys(charactersValue).find((key) => charactersValue[key] === sampleCharacter) ?? null
    : null;
  const characterIDCounts = countBy(validMods, (mod) => mod.characterID);
  const selectedSample = selectedCharacters?.value?.[0];
  const assignmentSample = assignments?.value?.[0];
  const target = isObject(selectedSample?.target) ? selectedSample.target : null;
  const playerValues = isObject(sampleCharacter?.playerValues) ? sampleCharacter.playerValues : null;
  const optimizerSettings = isObject(sampleCharacter?.optimizerSettings) ? sampleCharacter.optimizerSettings : null;
  const targetValueTypes = target ? Object.fromEntries(Object.entries(target).map(([key, value]) => [
    key, value === null ? "null" : Array.isArray(value) ? "array" : typeof value
  ])) : {};
  const targetSettings = optimizerSettings?.targets;
  const selectedEntries = selectedCharacters?.value?.filter(isObject) ?? [];
  const selectedTargets = selectedEntries.map((entry) => isObject(entry.target) ? entry.target : null).filter(Boolean);
  const targetStatsArrays = selectedTargets.map((entry) => Array.isArray(entry.targetStats) ? entry.targetStats : []);
  const targetStatsLengths = countBy(targetStatsArrays, (items) => items.length);
  const targetStatsSample = targetStatsArrays.flat().find(isObject) ?? null;
  const charsWithOptimizerTargets = characterMap
    ? Object.values(characterMap).filter((character) =>
        isObject(character?.optimizerSettings) &&
        Array.isArray(character.optimizerSettings.targets) &&
        character.optimizerSettings.targets.length > 0
      ).length
    : null;
  const selectedIdMatchCount = characterMap
    ? selectedEntries.filter((entry) => typeof entry.id === "string" && Object.prototype.hasOwnProperty.call(characterMap, entry.id)).length
    : null;
  const scalarTargetSummary = {};
  for (const key of ["health", "protection", "speed", "critDmg", "potency", "tenacity", "physDmg", "specDmg", "critChance", "armor", "resistance", "accuracy", "critAvoid"]) {
    const values = selectedTargets.map((entry) => entry[key]).filter((value) => typeof value === "number" && Number.isFinite(value));
    scalarTargetSummary[key] = {
      numericCount: values.length,
      distinctCount: new Set(values).size,
      min: values.length ? Math.min(...values) : null,
      max: values.length ? Math.max(...values) : null,
      zeroCount: values.filter((value) => value === 0).length,
      positiveCount: values.filter((value) => value > 0).length,
    };
  }
  const restrictionSummary = (key) => {
    const values = selectedTargets.map((entry) => entry[key]).filter(isObject);
    return {
      entriesWithObject: values.length,
      sampleKeys: values.length ? Object.keys(values[0]) : [],
      valueTypes: values.length ? Object.fromEntries(Object.entries(values[0]).map(([name, value]) => [
        name, value === null ? "null" : Array.isArray(value) ? "array" : typeof value
      ])) : {},
      entriesWithAnyKeys: values.filter((value) => Object.keys(value).length > 0).length,
    };
  };
  const statObjectShape = (value) => ({
    shape: describeShape(value),
    keys: isObject(value) ? Object.keys(value).slice(0, 40) : [],
    valueTypes: isObject(value) ? Object.fromEntries(Object.entries(value).slice(0, 40).map(([key, item]) => [
      key, item === null ? "null" : Array.isArray(item) ? "array" : typeof item
    ])) : {},
  });

  structure.textContent = JSON.stringify({
    topLevelKeys: Object.keys(data),
    profileKeys: Object.keys(profile),
    charactersContainer: describeShape(charactersValue),
    sampleCharacterIdKey: sampleCharacterId,
    firstCharacterKeys: sampleCharacter ? Object.keys(sampleCharacter) : [],
    characterPlayerValuesShape: describeShape(sampleCharacter?.playerValues),
    characterPlayerStats: {
      baseStats: statObjectShape(playerValues?.baseStats),
      equippedStats: statObjectShape(playerValues?.equippedStats),
    },
    characterOptimizerSettingsShape: describeShape(sampleCharacter?.optimizerSettings),
    optimizerTargets: {
      sampleCharacterTargetsShape: describeShape(targetSettings),
      charactersWithNonEmptyOptimizerTargets: charsWithOptimizerTargets,
      note: "The per-character optimizerSettings.targets field may be separate from selectedCharacters[].target.",
    },
    modsArray: modsEntry.key,
    firstModKeys: sampleMod ? Object.keys(sampleMod) : [],
    firstModValueTypes: sampleMod ? Object.fromEntries(Object.entries(sampleMod).map(([key, value]) => [
      key, value === null ? "null" : Array.isArray(value) ? "array" : typeof value
    ])) : {},
    modDistribution: {
      bySlot: countBy(validMods, (mod) => mod.slot),
      bySet: countBy(validMods, (mod) => mod.set),
      byPips: countBy(validMods, (mod) => mod.pips),
      byLevel: countBy(validMods, (mod) => mod.level),
      characterIDPresentVsEmpty: { nonEmpty: withCharacterID, emptyOrMissing: withoutCharacterID },
      distinctCharacterIDCount: Object.keys(characterIDCounts).filter((key) => key !== "(empty)").length,
    },
    selectedCharactersArray: selectedCharacters?.key ?? null,
    selectedCharacterCount: selectedCharacters?.value.length ?? null,
    selectedCharacterEntryType: selectedSample === undefined ? null : Array.isArray(selectedSample) ? "array" : typeof selectedSample,
    selectedCharacterObjectKeys: isObject(selectedSample) ? Object.keys(selectedSample) : [],
    selectedCharacterTargetShape: describeShape(selectedSample?.target),
    selectedCharacterTargetKeys: target ? Object.keys(target) : [],
    selectedCharacterTargetValueTypes: targetValueTypes,
    selectedCharacterTargetSampleShape: target ? statObjectShape(target) : null,
    selectedTargetSummary: {
      selectedCharacterCount: selectedEntries.length,
      selectedIdsMatchingCharacterMap: selectedIdMatchCount,
      entriesWithTargetObject: selectedTargets.length,
      scalarTargetSummary,
      primaryStatRestrictions: restrictionSummary("primaryStatRestrictions"),
      setRestrictions: restrictionSummary("setRestrictions"),
      targetStatsArrayLengths: targetStatsLengths,
      firstTargetStatsEntryKeys: targetStatsSample ? Object.keys(targetStatsSample) : [],
      firstTargetStatsEntryValueTypes: targetStatsSample ? Object.fromEntries(Object.entries(targetStatsSample).map(([key, value]) => [
        key, value === null ? "null" : Array.isArray(value) ? "array" : typeof value
      ])) : {},
      primaryStatRestrictionsShape: describeShape(target?.primaryStatRestrictions),
      setRestrictionsShape: describeShape(target?.setRestrictions),
    },
    modAssignmentsArray: assignments?.key ?? null,
    modAssignmentCount: assignments?.value.length ?? null,
    modAssignmentEntryType: assignmentSample === undefined ? null : Array.isArray(assignmentSample) ? "array" : typeof assignmentSample,
    modAssignmentObjectKeys: isObject(assignmentSample) ? Object.keys(assignmentSample) : [],
    gameSettingsShape: describeShape(data.gameSettings),
    characterTemplatesShape: describeShape(data.characterTemplates),
    notes: [
      "This is a structural inventory only; it does not yet normalize mods for the solver.",
      'A non-empty "characterID" is reported as a field observation, not yet treated as a confirmed equipped-mod rule.',
      "Object key names and field names are reported, but character/mod values are not copied into this diagnostic.",
      "The file is parsed locally and is not uploaded.",
    ],
  }, null, 2);
  summary.hidden = false;
}

fileInput.addEventListener("change", async () => {
  summary.hidden = true;
  errorOutput.hidden = true;
  errorOutput.textContent = "";
  summaryFields.replaceChildren();
  structure.textContent = "";

  const file = fileInput.files?.[0];
  if (!file) {
    status.textContent = "Choose a progress file to inspect it.";
    return;
  }

  status.textContent = "Reading and inspecting file locally…";
  try {
    const raw = await file.text();
    let data;
    try {
      data = JSON.parse(raw);
    } catch {
      throw new Error("The selected file is not valid JSON.");
    }
    inspectProgressFile(data, file);
    loadedData.set("progress-file", { fileName: file.name, data });
    refreshHeroOptions();
    refreshOptimizerDataSummary();
    refreshParityAvailability();
    status.textContent = "File parsed successfully. No optimization has been run.";
  } catch (error) {
    status.textContent = "Could not inspect this file.";
    errorOutput.textContent = error instanceof Error ? error.message : String(error);
    errorOutput.hidden = false;
  }
});


// Inspect the three optimizer data sources independently. The schema is not
// assumed: we report the top-level shape and shallow field names before wiring
// these files into the solver.
const dataFileInputs = [
  { id: "gamedata-file", label: "GameData.json" },
  { id: "keystats-file", label: "keystats.json" },
  { id: "stats-file", label: "stats_v2_top100.json" },
];
const dataStatus = document.querySelector("#data-status");
const dataSummary = document.querySelector("#data-summary");
const dataSummaryFields = document.querySelector("#data-summary-fields");
const dataStructure = document.querySelector("#data-structure");
const loadedData = new Map();
const hasEmbeddedOptimizerData = Boolean(
  EMBEDDED_OPTIMIZER_DATA?.gameData?.statModSet &&
  EMBEDDED_OPTIMIZER_DATA?.keystats?.heroes &&
  EMBEDDED_OPTIMIZER_DATA?.stats?.units
);
if (hasEmbeddedOptimizerData) {
  loadedData.set("gamedata-file", { fileName: "embedded GameData statModSet", data: EMBEDDED_OPTIMIZER_DATA.gameData });
  loadedData.set("keystats-file", { fileName: "embedded keystats", data: EMBEDDED_OPTIMIZER_DATA.keystats });
  loadedData.set("stats-file", { fileName: "embedded stats-v2 medians", data: EMBEDDED_OPTIMIZER_DATA.stats });
}

function shallowDescription(value, depth = 0) {
  if (Array.isArray(value)) {
    return {
      type: "array",
      length: value.length,
      sample: value.length ? shallowDescription(value[0], depth + 1) : null,
    };
  }
  if (isObject(value)) {
    const entries = Object.entries(value);
    const result = {
      type: "object",
      keyCount: entries.length,
      firstKeys: entries.slice(0, 40).map(([key]) => key),
    };
    if (depth < 1) {
      const first = entries.slice(0, 12);
      result.firstValueTypes = Object.fromEntries(first.map(([key, item]) => [
        key,
        item === null ? "null" : Array.isArray(item) ? "array" : typeof item,
      ]));
      const sampleEntry = first.find(([, item]) => isObject(item) || Array.isArray(item));
      if (sampleEntry) {
        result.sampleEntryKey = sampleEntry[0];
        result.sampleEntry = shallowDescription(sampleEntry[1], depth + 1);
      }
    }
    return result;
  }
  return { type: value === null ? "null" : typeof value };
}

function addDataSummaryField(label, value) {
  const term = document.createElement("dt");
  term.textContent = label;
  const description = document.createElement("dd");
  description.textContent = String(value);
  dataSummaryFields.append(term, description);
}

function focusedValueShape(value) {
  if (Array.isArray(value)) {
    return {
      type: "array",
      length: value.length,
      sample: value.length ? focusedValueShape(value[0]) : null,
    };
  }
  if (isObject(value)) {
    const entries = Object.entries(value);
    const firstNested = entries.find(([, item]) => isObject(item) || Array.isArray(item));
    return {
      type: "object",
      keyCount: entries.length,
      keys: entries.slice(0, 60).map(([key]) => key),
      valueTypes: Object.fromEntries(entries.slice(0, 30).map(([key, item]) => [
        key,
        item === null ? "null" : Array.isArray(item) ? "array" : typeof item,
      ])),
      sampleNestedKey: firstNested?.[0] ?? null,
      sampleNested: firstNested ? focusedValueShape(firstNested[1]) : null,
    };
  }
  return { type: value === null ? "null" : typeof value };
}

function compactExample(value, maxDepth = 3, maxEntries = 12) {
  if (maxDepth < 0) return "[depth limit]";
  if (Array.isArray(value)) {
    return {
      type: "array",
      length: value.length,
      examples: value.slice(0, 3).map(item => compactExample(item, maxDepth - 1, maxEntries)),
    };
  }
  if (isObject(value)) {
    const entries = Object.entries(value);
    const result = {};
    for (const [key, item] of entries.slice(0, maxEntries)) {
      result[key] = isObject(item) || Array.isArray(item)
        ? compactExample(item, maxDepth - 1, maxEntries)
        : item;
    }
    if (entries.length > maxEntries) result.__remainingKeys = entries.length - maxEntries;
    return result;
  }
  return value;
}

function inspectRelevantBranches(definitionId, data) {
  if (!isObject(data)) return {};
  if (definitionId === "gamedata-file") {
    const units = data.units;
    const statMod = data.statMod;
    const statModSet = data.statModSet;
    const firstUnit = Array.isArray(units) ? units[0] : null;
    const firstSet = Array.isArray(statModSet) ? statModSet[0] : null;
    return {
      units: focusedValueShape(units),
      statMod: focusedValueShape(statMod),
      statModSet: focusedValueShape(statModSet),
      relicTierDefinition: focusedValueShape(data.relicTierDefinition),
      examples: {
        unit: firstUnit ? compactExample(firstUnit, 3, 15) : null,
        statMod: Array.isArray(statMod) ? compactExample(statMod[0], 3, 15) : null,
        statModSet: firstSet ? compactExample(firstSet, 4, 10) : null,
        relicTier: Array.isArray(data.relicTierDefinition) ? compactExample(data.relicTierDefinition[0], 4, 10) : null,
      },
    };
  }
  if (definitionId === "keystats-file") {
    const heroes = data.heroes;
    const firstId = isObject(heroes) ? Object.keys(heroes)[0] : null;
    const firstHero = firstId ? heroes[firstId] : null;
    return {
      meta: focusedValueShape(data._meta),
      heroes: focusedValueShape(heroes),
      firstHero: focusedValueShape(firstHero),
      examples: firstHero ? {
        heroId: firstId,
        key_stats: compactExample(firstHero.key_stats, 4, 10),
        also: compactExample(firstHero.also, 4, 10),
        sets: compactExample(firstHero.sets, 4, 10),
        primaries: compactExample(firstHero.primaries, 4, 10),
      } : null,
    };
  }
  if (definitionId === "stats-file") {
    const units = data.units;
    const firstId = isObject(units) ? Object.keys(units)[0] : null;
    const firstUnit = firstId ? units[firstId] : null;
    return {
      meta: focusedValueShape(data._meta),
      units: focusedValueShape(units),
      firstUnit: focusedValueShape(firstUnit),
      examples: firstUnit ? {
        unitId: firstId,
        stats: compactExample(firstUnit.stats, 4, 10),
        mod_stats: compactExample(firstUnit.mod_stats, 4, 10),
        set_bonus_stats: compactExample(firstUnit.set_bonus_stats, 4, 10),
        mod_raw: compactExample(firstUnit.mod_raw, 4, 10),
        sets: compactExample(firstUnit.sets, 4, 10),
        primaries: compactExample(firstUnit.primaries, 4, 10),
        secondaries: compactExample(firstUnit.secondaries, 4, 10),
      } : null,
    };
  }
  return {};
}

async function inspectOptimizerDataFile(definition, file) {
  const raw = await file.text();
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error(definition.label + " is not valid JSON.");
  }
  loadedData.set(definition.id, { fileName: file.name, data: parsed });
  return {
    label: definition.label,
    fileName: file.name,
    sizeBytes: file.size,
    root: shallowDescription(parsed),
    relevantBranches: inspectRelevantBranches(definition.id, parsed),
  };
}

async function refreshOptimizerDataSummary() {
  const chosen = dataFileInputs
    .map((definition) => ({ definition, file: document.getElementById(definition.id).files?.[0] }))
    .filter((entry) => entry.file);
  dataSummaryFields.replaceChildren();
  dataStructure.textContent = "";
  if (!chosen.length) {
    dataSummaryFields.replaceChildren();
    if (hasEmbeddedOptimizerData) {
      addDataSummaryField("GameData", EMBEDDED_OPTIMIZER_DATA.sourceFiles?.gameData || "embedded");
      addDataSummaryField("Keystats", EMBEDDED_OPTIMIZER_DATA.sourceFiles?.keystats || "embedded");
      addDataSummaryField("Stats-v2", EMBEDDED_OPTIMIZER_DATA.sourceFiles?.stats || "embedded");
      addDataSummaryField("Generated", EMBEDDED_OPTIMIZER_DATA.generatedAt || "unknown");
      dataStructure.textContent = JSON.stringify({
        setDefinitions: EMBEDDED_OPTIMIZER_DATA.gameData.statModSet.length,
        keystatsHeroes: Object.keys(EMBEDDED_OPTIMIZER_DATA.keystats.heroes).length,
        statsV2Units: Object.keys(EMBEDDED_OPTIMIZER_DATA.stats.units).length,
        note: "Reference data was extracted once into src/optimizer-data.generated.js and is loaded automatically."
      }, null, 2);
      dataSummary.hidden = false;
      dataStatus.textContent = "Embedded optimizer reference data loaded automatically.";
    } else {
      dataSummary.hidden = true;
      dataStatus.textContent = "Embedded reference data is not generated yet. Run npm run extract-data once, or choose the files below.";
    }
    return;
  }

  dataStatus.textContent = "Reading selected data files locally…";
  try {
    const reports = await Promise.all(chosen.map(({ definition, file }) =>
      inspectOptimizerDataFile(definition, file)
    ));
    for (const report of reports) {
      addDataSummaryField(report.label, report.fileName);
      addDataSummaryField(report.label + " size", (report.sizeBytes / 1024 / 1024).toFixed(2) + " MiB");
    }
    dataStructure.textContent = JSON.stringify({
      filesSelected: reports.length,
      filesExpected: dataFileInputs.length,
      files: reports.map(({ label, root, relevantBranches }) => ({
        label,
        root,
        relevantBranches,
      })),
      note: "This is schema discovery only. The files have not yet been mapped to the optimizer's internal stat IDs or loaded into the MILP.",
    }, null, 2);
    dataSummary.hidden = false;
    dataStatus.textContent = reports.length + " optional reference file(s) loaded; other reference data remains embedded when available.";
    refreshOptimizerControls();
  } catch (error) {
    dataStatus.textContent = "Could not inspect optimizer data files.";
    errorOutput.textContent = error instanceof Error ? error.message : String(error);
    errorOutput.hidden = false;
  }
}

for (const definition of dataFileInputs) {
  document.getElementById(definition.id).addEventListener("change", () => {
    errorOutput.hidden = true;
    refreshOptimizerDataSummary();
  });
}


// Wire the real normalized single-hero input into the existing Web Worker.
const heroSelect = document.querySelector("#hero-select");
const prepareHeroButton = document.querySelector("#prepare-hero");
const solveHeroButton = document.querySelector("#solve-hero");
const optimizerStatus = document.querySelector("#optimizer-status");
const optimizerOutput = document.querySelector("#optimizer-output");
let preparedHeroInput = null;
let activeWorker = null;

function refreshHeroOptions() {
  if (!heroSelect) return;
  const progress = loadedData.get("progress-file")?.data;
  const ks = loadedData.get("keystats-file")?.data;
  const profile = progress?.profiles?.[0];
  const heroes = ks?.heroes;
  const previous = heroSelect.value;
  heroSelect.replaceChildren();
  if (!profile || !heroes || !profile.characters) {
    heroSelect.add(new Option("Load all files first", ""));
    heroSelect.disabled = true;
    prepareHeroButton.disabled = true;
    solveHeroButton.disabled = true;
    return;
  }
  const eligible = (profile.selectedCharacters || [])
    .filter(c => c?.id && profile.characters[c.id] && heroes[c.id]?.key_stats?.length)
    .sort((a, b) => a.id.localeCompare(b.id));
  heroSelect.add(new Option("Select a hero (" + eligible.length + " available)", ""));
  for (const hero of eligible) heroSelect.add(new Option(hero.id, hero.id));
  if (eligible.some(h => h.id === previous)) heroSelect.value = previous;
  heroSelect.disabled = eligible.length === 0;
  prepareHeroButton.disabled = !heroSelect.value;
  solveHeroButton.disabled = !preparedHeroInput || preparedHeroInput.heroId !== heroSelect.value;
}

heroSelect?.addEventListener("change", () => {
  preparedHeroInput = null;
  prepareHeroButton.disabled = !heroSelect.value;
  solveHeroButton.disabled = true;
  optimizerOutput.textContent = "";
  optimizerStatus.textContent = heroSelect.value ? "Hero selected; prepare its normalized input." : "Choose a hero.";
});

prepareHeroButton?.addEventListener("click", () => {
  try {
    const progress = loadedData.get("progress-file")?.data;
    const gameData = loadedData.get("gamedata-file")?.data;
    const keystats = loadedData.get("keystats-file")?.data;
    if (!progress || !gameData || !keystats) throw new Error("Select the progress file, GameData.json, and keystats.json first.");
    preparedHeroInput = prepareHeroInput(progress, gameData, keystats, heroSelect.value, { strict: pythonStrictForHero(heroSelect.value), comboName: pythonComboForHero(heroSelect.value), referenceMods: pythonModIdsForHero(heroSelect.value), referencePrimaryLocks: pythonPrimaryLocksForHero(heroSelect.value) });
    const preparedSummary = summarizePreparedHero(preparedHeroInput);
    const populationUnit = loadedData.get("stats-file")?.data?.units?.[heroSelect.value];
    preparedSummary.populationReference = populationUnit ? {
      players: populationUnit.players ?? null,
      modSpeedMedian: populationUnit.mod_stats?.speed?.median ?? null,
      finalSpeedMedian: populationUnit.stats?.speed?.median ?? null,
      note: "Reference population medians only; not used as optimizer targets or constraints.",
    } : null;
    optimizerOutput.textContent = JSON.stringify(preparedSummary, null, 2);
    optimizerStatus.textContent = "Hero normalized. Review counts and stat targets, then run the MILP preview.";
    solveHeroButton.disabled = false;
  } catch (error) {
    preparedHeroInput = null;
    solveHeroButton.disabled = true;
    optimizerStatus.textContent = "Could not prepare this hero.";
    optimizerOutput.textContent = error instanceof Error ? error.message : String(error);
  }
});

solveHeroButton?.addEventListener("click", () => {
  if (!preparedHeroInput) return;
  solveHeroButton.disabled = true;
  optimizerStatus.textContent = "Solving in a Web Worker…";
  optimizerOutput.textContent = "";
  if (activeWorker) activeWorker.terminate();
  activeWorker = new Worker(new URL("./solver-worker.js", import.meta.url), { type: "module" });
  activeWorker.onmessage = ({ data }) => {
    optimizerOutput.textContent = JSON.stringify(data, null, 2);
    optimizerStatus.textContent = data.error
      ? "Solver failed; see details below."
      : "MILP finished. Selected mods are a preliminary model result, not yet exact-stat validated.";
    solveHeroButton.disabled = false;
    activeWorker.terminate();
    activeWorker = null;
  };
  activeWorker.onerror = event => {
    optimizerStatus.textContent = "Worker error.";
    optimizerOutput.textContent = event.message || "Unknown Web Worker error.";
    solveHeroButton.disabled = false;
    activeWorker.terminate();
    activeWorker = null;
  };
  // Structured-clone only the normalized solver input; raw files remain in this tab.
  activeWorker.postMessage({ type: "run", mode: "hero", input: preparedHeroInput });
});

function refreshOptimizerControls() {
  refreshHeroOptions();
  if (loadedData.has("progress-file") && loadedData.has("gamedata-file") && loadedData.has("keystats-file") && loadedData.has("stats-file")) optimizerStatus.textContent = "All input files are ready locally. Choose a hero.";
  if (typeof refreshParityAvailability === "function") refreshParityAvailability();
}
refreshHeroOptions();
refreshOptimizerDataSummary();

// Repeatable Python-vs-browser parity harness. All input and reference files stay
// in this browser tab; the downloadable report contains only solver outputs.
const batchButton = document.querySelector("#run-parity-batch");
const batchLimitInput = document.querySelector("#batch-limit");
const batchHeroIdInput = document.querySelector("#batch-hero-id");
const referenceFileInput = document.querySelector("#reference-file");
const referenceHeroIdInput = document.querySelector("#reference-hero-id");
const parityStatus = document.querySelector("#parity-status");
const parityOutput = document.querySelector("#parity-output");
const downloadParityButton = document.querySelector("#download-parity");
let pythonReference = null;
let lastParityReport = null;

referenceFileInput?.addEventListener("change", async () => {
  pythonReference = null;
  const file = referenceFileInput.files?.[0];
  if (!file) {
    parityStatus.textContent = "No Python reference loaded; batch will produce browser results only.";
    return;
  }
  try {
    pythonReference = JSON.parse(await file.text());
    parityStatus.textContent = "Python reference loaded locally: " + file.name;
  } catch {
    parityStatus.textContent = "Reference file is not valid JSON.";
  }
});

function referenceResultsByHero(reference) {
  const heroKey = row => String(row?.heroId ?? row?.hero_id ?? row?.unitId ?? row?.id ?? row?.base ?? "");
  if (Array.isArray(reference)) return new Map(reference.map(row => [heroKey(row), row]).filter(([id]) => id));
  if (Array.isArray(reference?.results)) return referenceResultsByHero(reference.results);
  // Python optimizer exports its assignments inside a top-level "plan" array.
  if (Array.isArray(reference?.plan)) return new Map(reference.plan.map(row => [heroKey(row), row]).filter(([id]) => id));
  if (reference && typeof reference === "object" && heroKey(reference)) {
    return new Map([[heroKey(reference), reference]]);
  }
  if (reference && typeof reference === "object") {
    return new Map(Object.entries(reference).filter(([, row]) => row && typeof row === "object"));
  }
  return new Map();
}

function pythonReferenceRowForHero(heroId) {
  const references = referenceResultsByHero(pythonReference);
  const target = String(heroId || "").toUpperCase();
  return [...references.entries()].find(([id]) => String(id).toUpperCase() === target)?.[1] ?? null;
}

function pythonStrictForHero(heroId) {
  // The Python reference marks heroes solved with an imposed keystats set combo
  // as solver.mode === "sets imposés". Reproduce that mode for parity runs.
  return pythonReferenceRowForHero(heroId)?.solver?.mode === "sets imposés";
}

function pythonComboForHero(heroId) {
  // The Python reference records the exact combo used by its imposed-set solve.
  return pythonReferenceRowForHero(heroId)?.solver?.combo ?? null;
}

function pythonModIdsForHero(heroId) {
  const row = pythonReferenceRowForHero(heroId);
  const mods = row?.mods;
  if (!mods || typeof mods !== "object" || Array.isArray(mods)) return [];
  return Object.values(mods).filter(id => typeof id === "string" && id.length > 0);
}

function pythonPrimaryLocksForHero(heroId) {
  const locks = pythonReferenceRowForHero(heroId)?.solver?.primary_lock;
  return locks && typeof locks === "object" && !Array.isArray(locks) ? locks : null;
}

function slotMap(row) {
  const mods = row?.selectedMods ?? row?.selected_mods ?? row?.chosen ?? row?.mods;
  if (Array.isArray(mods)) return new Map(mods.map(mod => [String(mod.slot ?? ""), String(mod.id ?? mod.mod_uid ?? mod.modId ?? "")]));
  if (mods && typeof mods === "object") {
    return new Map(Object.entries(mods).map(([slot, mod]) => [String(mod?.slot ?? slot), String(typeof mod === "string" ? mod : mod?.id ?? mod?.mod_uid ?? mod?.modId ?? "")]));
  }
  return new Map();
}

function compareWithReference(results, reference) {
  const refs = referenceResultsByHero(reference);
  // A single Python result can omit heroId when the batch contains one hero.
  if (refs.size === 0 && reference && typeof reference === "object" &&
      (reference.selectedMods || reference.selected_mods || reference.chosen || reference.mods)) {
    const explicitHeroId = String(referenceHeroIdInput?.value || "").trim();
    if (explicitHeroId) refs.set(explicitHeroId, reference);
    else if (results.length === 1) refs.set(String(results[0].heroId), reference);
  }
  return results.map(result => {
    const ref = refs.get(String(result.heroId));
    if (!ref) return { ...result, comparison: "no-reference-for-hero" };
    if (result.error || !result.selectedMods?.length) return { ...result, comparison: "browser-solve-failed" };
    const expected = slotMap(ref);
    const actual = slotMap(result);
    if (!expected.size) return { ...result, comparison: "reference-format-unrecognized" };
    const mismatches = [];
    for (const slot of ["square", "arrow", "diamond", "triangle", "circle", "cross"]) {
      if (expected.get(slot) !== actual.get(slot)) mismatches.push({ slot, expected: expected.get(slot) ?? null, actual: actual.get(slot) ?? null });
    }
    const expectedObjective = Number(ref.objectiveValue ?? ref.objective_value ?? ref.objective);
    const objectiveComparable = Number.isFinite(expectedObjective) && Number.isFinite(Number(result.objectiveValue));
    const objectiveMatches = !objectiveComparable || Math.abs(expectedObjective - Number(result.objectiveValue)) < 1e-5;
    return {
      ...result,
      comparison: mismatches.length === 0 && objectiveMatches ? "match" : "mismatch",
      referenceObjectiveValue: objectiveComparable ? expectedObjective : null,
      objectiveMatches: objectiveComparable ? objectiveMatches : null,
      mismatches,
    };
  });
}

batchButton?.addEventListener("click", () => {
  const progress = loadedData.get("progress-file")?.data;
  const gameData = loadedData.get("gamedata-file")?.data;
  const keystats = loadedData.get("keystats-file")?.data;
  if (!progress || !gameData || !keystats) return;
  const profile = progress.profiles?.[0];
  // Python determines its own priority order; Grandivory selectedCharacters is not that order.
  // When a Python plan is loaded, use its plan order for roster-level parity. Otherwise retain
  // the Grandivory order and explicitly report that this is only an approximate priority order.
  const available = (profile?.selectedCharacters || [])
    .filter(c => c?.id && profile.characters?.[c.id] && keystats.heroes?.[c.id]?.key_stats?.length);
  const pythonPlan = Array.isArray(pythonReference?.plan) ? pythonReference.plan
    : Array.isArray(pythonReference?.results) ? pythonReference.results : Array.isArray(pythonReference) ? pythonReference : [];
  const pythonOrder = new Map(pythonPlan.map((row, index) => [String(row?.base ?? row?.heroId ?? row?.hero_id ?? row?.id ?? "").toUpperCase(), index]).filter(([id]) => id));
  const hasPythonOrder = available.some(c => pythonOrder.has(c.id.toUpperCase()));
  if (hasPythonOrder) available.sort((a, b) => {
    const ai = pythonOrder.has(a.id.toUpperCase()) ? pythonOrder.get(a.id.toUpperCase()) : Number.MAX_SAFE_INTEGER;
    const bi = pythonOrder.has(b.id.toUpperCase()) ? pythonOrder.get(b.id.toUpperCase()) : Number.MAX_SAFE_INTEGER;
    return ai - bi;
  });
  const requestedHeroId = String(batchHeroIdInput?.value || "").trim();
  const heroPool = requestedHeroId ? available.filter(c => c.id.toUpperCase() === requestedHeroId.toUpperCase()) : available;
  if (requestedHeroId && heroPool.length === 0) {
    parityStatus.textContent = "Hero " + requestedHeroId + " is not eligible in the loaded progress/reference data. Check the ID and make sure the hero is selected in the Grandivory export.";
    parityOutput.textContent = "";
    return;
  }
  const requestedLimit = Math.max(0, Number.parseInt(batchLimitInput?.value || "0", 10) || 0);
  const selected = requestedLimit > 0 ? heroPool.slice(0, requestedLimit) : heroPool;
  const inputs = [];
  const preparationErrors = [];
  for (const character of selected) {
    try {
      inputs.push({ heroId: character.id, input: prepareHeroInput(progress, gameData, keystats, character.id, { strict: pythonStrictForHero(character.id), comboName: pythonComboForHero(character.id), referenceMods: pythonModIdsForHero(character.id), referencePrimaryLocks: pythonPrimaryLocksForHero(character.id) }) });
    } catch (error) {
      preparationErrors.push({ heroId: character.id, error: error instanceof Error ? error.message : String(error) });
    }
  }
  if (activeWorker) activeWorker.terminate();
  batchButton.disabled = true;
  solveHeroButton.disabled = true;
  downloadParityButton.disabled = true;
  parityOutput.textContent = "";
  parityStatus.textContent = "Preparing " + inputs.length + " heroes; running " + (requestedHeroId ? "independent single-hero diagnostic" : "sequential roster-allocation batch") + (hasPythonOrder ? " in Python reference order…" : " in Grandivory order (Python priority order unavailable)…");
  activeWorker = new Worker(new URL("./solver-worker.js", import.meta.url), { type: "module" });
  activeWorker.onmessage = ({ data }) => {
    if (data.type === "progress") {
      parityStatus.textContent = "Solving " + data.completed + "/" + data.total + ": " + data.heroId + "…";
      return;
    }
    if (data.error) {
      parityStatus.textContent = "Batch solver failed.";
      parityOutput.textContent = JSON.stringify(data, null, 2);
    } else {
      let results = [...preparationErrors, ...(data.results || [])];
      if (pythonReference) results = compareWithReference(results, pythonReference);
      const matched = results.filter(row => row.comparison === "match").length;
      const mismatched = results.filter(row => row.comparison === "mismatch").length;
      const comparable = results.filter(row => ["match", "mismatch"].includes(row.comparison)).length;
      const noReference = results.filter(row => row.comparison === "no-reference-for-hero").length;
      const unrecognized = results.filter(row => row.comparison === "reference-format-unrecognized").length;
      const report = {
        reportType: "guionbot-modopt-python-parity",
        generatedAt: new Date().toISOString(),
        heroesRequested: selected.length,
        heroesPrepared: inputs.length,
        heroesFailedPreparation: preparationErrors.length,
        allocationMode: data.allocationMode || (requestedHeroId ? "independent" : "sequential"),
        priorityOrder: hasPythonOrder ? "python-reference-plan" : "grandivory-selectedCharacters",
        allocationNote: data.note || null,
        pythonReferenceLoaded: Boolean(pythonReference),
        summary: { results: results.length, compared: comparable, matched, mismatched, noReference, referenceFormatUnrecognized: unrecognized, errors: results.filter(row => row.error || row.comparison === "browser-solve-failed").length },
        timingsMs: data.timingsMs,
        results,
      };
      lastParityReport = report;
      parityOutput.textContent = JSON.stringify(report, null, 2);
      parityStatus.textContent = (requestedHeroId ? "Independent single-hero diagnostic complete. " : "Sequential roster-allocation batch complete. ") + (pythonReference
        ? matched + " matches, " + mismatched + " mismatches; " + noReference + " heroes had no reference" + (unrecognized ? ", " + unrecognized + " reference formats were unrecognized" : "") + ". Compared " + comparable + " of " + results.length + " results."
        : results.length + " heroes solved. Load Python reference JSON and rerun to compare assignments.");
      downloadParityButton.disabled = false;
    }
    batchButton.disabled = false;
    solveHeroButton.disabled = !preparedHeroInput || preparedHeroInput.heroId !== heroSelect.value;
    activeWorker.terminate();
    activeWorker = null;
  };
  activeWorker.onerror = event => {
    parityStatus.textContent = "Batch worker error.";
    parityOutput.textContent = event.message || "Unknown Web Worker error.";
    batchButton.disabled = false;
    activeWorker.terminate();
    activeWorker = null;
  };
  // A named single-hero run remains an independent diagnostic. Full/limited batches
  // reproduce Python\'s sequential allocation, reserving each chosen mod for that hero.
  activeWorker.postMessage({ type: "run", mode: "batch", inputs, sequentialAllocation: !requestedHeroId });
});

downloadParityButton?.addEventListener("click", () => {
  if (!lastParityReport) return;
  const blob = new Blob([JSON.stringify(lastParityReport, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "modopt-parity-results.json";
  anchor.click();
  URL.revokeObjectURL(url);
});

// Keep batch availability synchronized with the existing file-loading flow.
function refreshParityAvailability() {
  const ready = ["progress-file", "gamedata-file", "keystats-file"].every(id => loadedData.has(id));
  if (batchButton) batchButton.disabled = !ready;
}
refreshParityAvailability();
