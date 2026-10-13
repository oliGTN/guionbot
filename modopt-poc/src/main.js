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

async function inspectOptimizerDataFile(definition, file) {
  const raw = await file.text();
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error(definition.label + " is not valid JSON.");
  }
  loadedData.set(definition.id, { fileName: file.name, data: parsed });
  const description = shallowDescription(parsed);
  return {
    label: definition.label,
    fileName: file.name,
    sizeBytes: file.size,
    root: description,
  };
}

async function refreshOptimizerDataSummary() {
  const chosen = dataFileInputs
    .map((definition) => ({ definition, file: document.getElementById(definition.id).files?.[0] }))
    .filter((entry) => entry.file);
  dataSummaryFields.replaceChildren();
  dataStructure.textContent = "";
  if (!chosen.length) {
    dataSummary.hidden = true;
    dataStatus.textContent = "Select the three optimizer data files to inspect them.";
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
      files: reports.map(({ label, root }) => ({ label, root })),
      note: "This is schema discovery only. The files have not yet been mapped to the optimizer's internal stat IDs or loaded into the MILP.",
    }, null, 2);
    dataSummary.hidden = false;
    dataStatus.textContent = reports.length === dataFileInputs.length
      ? "All three optimizer data files parsed locally."
      : reports.length + " of " + dataFileInputs.length + " optimizer data files parsed locally.";
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
