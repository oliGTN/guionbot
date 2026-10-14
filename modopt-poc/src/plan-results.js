const SLOT_ORDER = ["square", "arrow", "diamond", "triangle", "circle", "cross"];
const SLOT_LABELS = { square: "Square", arrow: "Arrow", diamond: "Diamond", triangle: "Triangle", circle: "Circle", cross: "Cross" };

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}
function number(value, digits = 1) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";
}
function signed(value, digits = 1) {
  const n = Number(value);
  return Number.isFinite(n) ? (n > 0 ? "+" : "") + number(n, digits) : "—";
}
function bestTier(row) {
  const tiers = row?.advice?.tiers;
  if (!Array.isArray(tiers) || !tiers.length) return null;
  return [...tiers].sort((a, b) => Number(b?.pts ?? 0) - Number(a?.pts ?? 0) || Number(a?.n_replace ?? 99) - Number(b?.n_replace ?? 99))[0];
}
function statsFor(row, tier) {
  const before = row?.advice?.before ?? row?.before?.stats ?? [];
  const result = tier?.result ?? row?.after?.stats ?? [];
  const afterMap = new Map((Array.isArray(result) ? result : []).map(s => [s.stat, s]));
  return (Array.isArray(before) ? before : []).map(s => {
    const after = afterMap.get(s.stat) ?? {};
    return { stat: s.stat, before: s.value ?? s.now, after: after.value ?? after.after ?? after.now, target: s.target ?? row?.before?.stats?.find(x => x.stat === s.stat)?.target, beforePoints: s.points ?? s.pts_now, afterPoints: after.points ?? after.pts_after };
  });
}
function modSlots(row, tier) {
  const slots = tier?.slots ?? row?.advice?.slots ?? [];
  const bySlot = new Map(slots.map(s => [s.slot, s]));
  return SLOT_ORDER.map(slot => {
    const advice = bySlot.get(slot) ?? {};
    const move = (row?.moves ?? []).find(m => m.slot === slot);
    return { slot, advice, move, decision: advice.decision ?? (move ? "REMPLACER" : "GARDER") };
  });
}
function statLabel(stat) {
  const statIdLabels = { "5": "Speed", "28": "Protection", "56": "Potency", "17": "Tenacity", "16": "Critical Chance", "18": "Critical Damage", "1": "Health", "6": "Physical Damage", "7": "Special Damage" };
  return statIdLabels[String(stat)] ?? ({ speed: "Speed", protection: "Protection", health: "Health", potency: "Potency", tenacity: "Tenacity", critDmg: "Critical Damage", critChance: "Critical Chance", physDmg: "Physical Damage", specDmg: "Special Damage" })[stat] ?? stat ?? "Stat";
}
function renderCharacter(row, index) {
  const tier = bestTier(row);
  const stats = statsFor(row, tier);
  const slots = modSlots(row, tier);
  const replaceCount = slots.filter(s => /REMPLAC|REPLACE/i.test(s.decision)).length;
  const ptsBefore = row?.advice?.pts_before ?? row?.before?.points;
  const ptsAfter = tier?.pts ?? row?.advice?.pts_ideal ?? row?.after?.points;
  const gain = Number.isFinite(Number(ptsBefore)) && Number.isFinite(Number(ptsAfter)) ? Number(ptsAfter) - Number(ptsBefore) : Number(row?.advice?.gain);
  const statSummary = stats.map(s => {
    const delta = Number(s.after) - Number(s.before);
    return `${statLabel(s.stat)} ${Number.isFinite(delta) ? signed(delta, s.stat === "speed" ? 1 : 0) : "—"}`;
  }).join(" · ");
  const name = row?.hero || row?.base || row?.heroId || `Character ${index + 1}`;
  const id = row?.base || row?.heroId || row?.hero_id || row?.id || String(index);
  const sets = (tier?.sets_after ?? row?.sets ?? []).map(s => Array.isArray(s) ? `${s[1]} ${s[0]}` : "").filter(Boolean).join(" + ");
  const statRows = stats.map(s => {
    const delta = Number(s.after) - Number(s.before);
    const target = Number(s.target);
    const ratio = Number.isFinite(target) && target !== 0 && Number.isFinite(Number(s.after)) ? Number(s.after) / target * 100 : null;
    return `<tr><th>${escapeHtml(statLabel(s.stat))}</th><td>${escapeHtml(number(s.before, 2))}</td><td>${escapeHtml(number(s.after, 2))}</td><td class="${delta > 0 ? "positive" : delta < 0 ? "negative" : ""}">${escapeHtml(signed(delta, 2))}</td><td>${escapeHtml(number(s.target, 2))}</td><td>${ratio === null ? "—" : escapeHtml(number(ratio, 1) + "%")}</td></tr>`;
  }).join("");
  const modRows = slots.map(({ slot, advice, move, decision }) => {
    const current = advice.current ?? {};
    const need = advice.need;
    const owner = move?.from ?? current.owner ?? "Unknown";
    const set = current.set ? ` · ${escapeHtml(current.set)} set` : "";
    const primary = current.primary !== undefined ? ` · primary ${escapeHtml(current.primary)}` : "";
    const needs = need ? `<div class="mod-need"><strong>Required:</strong> ${escapeHtml(need.set ?? current.set ?? "Any")} set${need.primary !== undefined ? `, primary ${escapeHtml(need.primary)}` : ""}${(need.secs ?? []).map(sec => `; ${escapeHtml(statLabel(String(sec[0])))} ${escapeHtml(number(sec[1], 2))}`).join("")}</div>` : "";
    const defects = (advice.defects ?? []).map(d => `${escapeHtml(d[0] === "sec" ? statLabel(String(d[1])) : d[0])}: ${escapeHtml(number(d[2], 2))} → ${escapeHtml(number(d[3], 2))}`).join(", ");
    const action = /REMPLAC|REPLACE/i.test(decision) ? "Replace" : "Keep";
    return `<tr><th>${escapeHtml(SLOT_LABELS[slot])}</th><td><strong>${escapeHtml(action)}</strong><div class="muted">From ${escapeHtml(owner)}${set}${primary}</div>${needs}${defects ? `<div class="muted">Reason: ${defects}</div>` : ""}</td></tr>`;
  }).join("");
  const tierRows = (row?.advice?.tiers ?? []).map(t => `<tr><td>${escapeHtml(t.pts ?? "—")}</td><td>${escapeHtml(t.gain ?? "—")}</td><td>${escapeHtml(t.n_replace ?? "—")}</td><td>${escapeHtml((t.sets_after ?? []).map(s => Array.isArray(s) ? `${s[1]} ${s[0]}` : "").filter(Boolean).join(" + ") || "—")}</td></tr>`).join("");
  const searchText = `${name} ${id} ${statSummary} ${sets}`.toLowerCase();
  return `<details class="plan-card" data-name="${escapeHtml(String(name).toLowerCase())}" data-id="${escapeHtml(String(id).toLowerCase())}" data-replacements="${replaceCount}" data-gain="${Number.isFinite(gain) ? gain : -999}" data-search="${escapeHtml(searchText)}">
    <summary class="plan-summary">
      <span class="plan-rank">${escapeHtml(row?.rank ?? index + 1)}</span>
      <span class="plan-portrait" aria-hidden="true">${escapeHtml(String(name).split(/\s+/).map(w => w[0]).join("").slice(0, 2).toUpperCase())}</span>
      <span class="plan-identity"><strong>${escapeHtml(name)}</strong><small>${escapeHtml(id)} · ${replaceCount} mod(s) to replace</small><small class="plan-stat-summary">${escapeHtml(statSummary || "No stat comparison available")}</small></span>
      <span class="plan-gain ${gain > 0 ? "positive" : gain < 0 ? "negative" : ""}">${Number.isFinite(gain) ? signed(gain, 0) + " StatQ" : "StatQ —"}</span>
      <span class="plan-chevron" aria-hidden="true">⌄</span>
    </summary>
    <div class="plan-expanded">
      <div class="plan-meta"><span><strong>StatQ:</strong> ${escapeHtml(ptsBefore ?? "—")} → ${escapeHtml(ptsAfter ?? "—")} / ${escapeHtml(row?.advice?.max ?? row?.after?.max ?? row?.before?.max ?? "—")}</span><span><strong>Sets:</strong> ${escapeHtml(sets || "Not specified")}</span><span><strong>Solver:</strong> ${escapeHtml(row?.solver?.mode ?? row?.solver?.status ?? "—")}</span><span><strong>Time:</strong> ${escapeHtml(row?.seconds === undefined ? "—" : number(row.seconds, 2) + " s")}</span></div>
      <h4>Stat changes</h4>
      <div class="plan-table-wrap"><table class="plan-table"><thead><tr><th>Stat</th><th>Before</th><th>After</th><th>Change</th><th>Target</th><th>Target reached</th></tr></thead><tbody>${statRows || '<tr><td colspan="6">No stat details in this plan entry.</td></tr>'}</tbody></table></div>
      <h4>Mods to move</h4>
      <div class="plan-table-wrap"><table class="plan-table mod-table"><tbody>${modRows}</tbody></table></div>
      ${tierRows ? `<details class="plan-alternatives"><summary>Alternative plans (${tierRows.split("</tr>").length - 1})</summary><div class="plan-table-wrap"><table class="plan-table"><thead><tr><th>StatQ</th><th>Gain</th><th>Replacements</th><th>Sets</th></tr></thead><tbody>${tierRows}</tbody></table></div></details>` : ""}
      <details class="plan-raw"><summary>Technical details</summary><pre>${escapeHtml(JSON.stringify({ solver: row?.solver, advice: row?.advice }, null, 2))}</pre></details>
    </div>
  </details>`;
}

export function renderPlanResults(container, planData) {
  const rows = Array.isArray(planData) ? planData : Array.isArray(planData?.plan) ? planData.plan : Array.isArray(planData?.results) ? planData.results : null;
  if (!rows) throw new Error('The selected JSON does not contain a top-level "plan" array.');
  container.replaceChildren();
  const toolbar = document.createElement("div");
  toolbar.className = "plan-toolbar";
  toolbar.innerHTML = `<div class="plan-summary-count"><strong>${rows.length}</strong> characters in plan</div>
    <input type="search" class="plan-search" placeholder="Search character or stat…" aria-label="Search plan characters">
    <select class="plan-filter" aria-label="Filter characters"><option value="all">All characters</option><option value="replace">Mods to replace</option><option value="gain">StatQ gain</option><option value="complete">No replacements</option></select>
    <select class="plan-sort" aria-label="Sort characters"><option value="order">Plan order</option><option value="gain">Highest StatQ gain</option><option value="replace">Most replacements</option><option value="name">Character name</option></select>
    <button type="button" class="plan-expand-all">Expand all</button><button type="button" class="plan-collapse-all">Collapse all</button>`;
  const list = document.createElement("div");
  list.className = "plan-list";
  list.innerHTML = rows.map(renderCharacter).join("");
  container.append(toolbar, list);
  const search = toolbar.querySelector(".plan-search");
  const filter = toolbar.querySelector(".plan-filter");
  const sort = toolbar.querySelector(".plan-sort");
  const cards = [...list.querySelectorAll(".plan-card")];
  function update() {
    const q = search.value.trim().toLowerCase();
    const mode = filter.value;
    for (const card of cards) {
      const replacements = Number(card.dataset.replacements);
      const gain = Number(card.dataset.gain);
      const visible = (!q || card.dataset.search.includes(q)) &&
        (mode === "all" || mode === "replace" && replacements > 0 || mode === "gain" && gain > 0 || mode === "complete" && replacements === 0);
      card.hidden = !visible;
    }
    const sorted = [...cards].sort((a, b) => {
      if (sort.value === "gain") return Number(b.dataset.gain) - Number(a.dataset.gain);
      if (sort.value === "replace") return Number(b.dataset.replacements) - Number(a.dataset.replacements);
      if (sort.value === "name") return a.dataset.name.localeCompare(b.dataset.name);
      return Number(a.querySelector(".plan-rank").textContent) - Number(b.querySelector(".plan-rank").textContent);
    });
    sorted.forEach(card => list.append(card));
  }
  search.addEventListener("input", update);
  filter.addEventListener("change", update);
  sort.addEventListener("change", update);
  toolbar.querySelector(".plan-expand-all").addEventListener("click", () => cards.filter(c => !c.hidden).forEach(c => { c.open = true; }));
  toolbar.querySelector(".plan-collapse-all").addEventListener("click", () => cards.forEach(c => { c.open = false; }));
  update();
  return rows.length;
}
