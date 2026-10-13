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
  const sampleCharacter = validCharacters[0] ?? null;
  const characterIDCounts = countBy(validMods, (mod) => mod.characterID);
  const selectedSample = selectedCharacters?.value?.[0];
  const assignmentSample = assignments?.value?.[0];

  structure.textContent = JSON.stringify({
    topLevelKeys: Object.keys(data),
    profileKeys: Object.keys(profile),
    charactersContainer: describeShape(charactersValue),
    firstCharacterKeys: sampleCharacter ? Object.keys(sampleCharacter) : [],
    modsArray: modsEntry.key,
    firstModKeys: sampleMod ? Object.keys(sampleMod) : [],
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
