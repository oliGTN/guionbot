const fileInput = document.querySelector("#progress-file");
const status = document.querySelector("#file-status");
const summary = document.querySelector("#summary");
const summaryFields = document.querySelector("#summary-fields");
const structure = document.querySelector("#structure");
const errorOutput = document.querySelector("#error");

const OWNER_FIELDS = [
  "characterId", "character_id", "unitId", "unit_id",
  "character", "owner", "assignedTo", "assigned_to",
];

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function firstArray(object, keys) {
  for (const key of keys) {
    if (Array.isArray(object?.[key])) return { key, value: object[key] };
  }
  return null;
}

function hasOwnerReference(mod) {
  return OWNER_FIELDS.some((key) => {
    const value = mod?.[key];
    if (typeof value === "string") return value.trim().length > 0;
    if (typeof value === "number") return value !== 0;
    return isObject(value) && Object.keys(value).length > 0;
  });
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
  const ownerCount = validMods.filter(hasOwnerReference).length;
  const selectedCharacters = firstArray(profile, ["selectedCharacters", "selected_characters"]);
  const assignments = firstArray(profile, ["modAssignments", "mod_assignments"]);
  const roster = firstArray(profile, ["roster", "characters", "units", "rosterUnit"]);
  const profileName = profile.name ?? profile.profileName ?? profile.playerName ?? profile.allyCode ?? "(not present)";

  summaryFields.replaceChildren();
  addField("File", file.name);
  addField("Size", (file.size / 1024).toFixed(1) + " KiB");
  addField("Profile", profileName);
  addField("Profiles in file", profiles.length);
  addField("Mods in first profile", mods.length);
  addField("Mod entries that are objects", validMods.length);
  addField("Mods with a recognizable owner/character reference", ownerCount);
  addField("Selected-character entries", selectedCharacters ? selectedCharacters.value.length : "not found as an array");
  addField("Mod-assignment entries", assignments ? assignments.value.length : "not found as an array");
  addField("Possible roster array", roster ? roster.key + " (" + roster.value.length + " entries)" : "not found");

  const sampleMod = validMods[0] ?? null;
  structure.textContent = JSON.stringify({
    topLevelKeys: Object.keys(data),
    profileKeys: Object.keys(profile),
    modsArray: modsEntry.key,
    firstModKeys: sampleMod ? Object.keys(sampleMod) : [],
    selectedCharactersArray: selectedCharacters?.key ?? null,
    modAssignmentsArray: assignments?.key ?? null,
    possibleRosterArray: roster?.key ?? null,
    notes: [
      "These counts describe JSON structure; they do not yet prove every mod can be normalized for the solver.",
      "Owner-reference detection is heuristic, not a definitive equipped/unequipped count.",
      "The file is read locally and is not uploaded.",
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
    try { data = JSON.parse(raw); }
    catch { throw new Error("The selected file is not valid JSON."); }
    inspectProgressFile(data, file);
    status.textContent = "File parsed successfully. No optimization has been run.";
  } catch (error) {
    status.textContent = "Could not inspect this file.";
    errorOutput.textContent = error instanceof Error ? error.message : String(error);
    errorOutput.hidden = false;
  }
});
