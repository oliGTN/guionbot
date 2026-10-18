/* Browser-side renderer for Codex Remod plan.json inside results.zip. No build step required. */
(function () {
  'use strict';
  const SLOT_ORDER = ['square', 'arrow', 'diamond', 'triangle', 'circle', 'cross'];
  const SLOT_LABELS = { square: 'Square', arrow: 'Arrow', diamond: 'Diamond', triangle: 'Triangle', circle: 'Circle', cross: 'Cross' };
  const STAT_LABELS = { speed: 'Speed', protection: 'Protection', health: 'Health', potency: 'Potency', tenacity: 'Tenacity', critDmg: 'Critical Damage', critChance: 'Critical Chance', physDmg: 'Physical Damage', specDmg: 'Special Damage', '1': 'Health', '5': 'Speed', '6': 'Physical Damage', '7': 'Special Damage', '16': 'Critical Chance', '17': 'Tenacity', '18': 'Critical Damage', '28': 'Protection', '56': 'Potency' };

  let unitSearchMetadataPromise = null;
  function loadUnitSearchMetadata() {
    if (!unitSearchMetadataPromise) {
      // codexremod.php loads the metadata from its filesystem paths and injects it here.
      // This avoids browser URL/path assumptions for files outside the public document root.
      const supplied = window.codexRemodUnitMetadata;
      unitSearchMetadataPromise = Promise.resolve(
        supplied && typeof supplied === 'object' ? supplied : {}
      );
    }
    return unitSearchMetadataPromise;
  }
  function addMetadataToCardSearch(container, selector) {
    loadUnitSearchMetadata().then(metadata => {
      container.querySelectorAll(selector).forEach(card => {
        const id = String(card.dataset.unitId || '').toLowerCase();
        const tags = metadata[id] || '';
        if (tags) card.dataset.search = (card.dataset.search + ' ' + tags).toLocaleLowerCase();
      });
      const search = container.querySelector('input[type="search"]');
      if (search) search.dispatchEvent(new Event('input', { bubbles: true }));
    }).catch(error => {
      console.warn('Codex Remod: unit metadata search is unavailable.', error);
    });
  }

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  function num(value, digits) {
    const n = Number(value);
    return value !== null && value !== '' && Number.isFinite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: digits == null ? 1 : digits }) : '—';
  }
  function signed(value, digits) {
    const n = Number(value);
    return Number.isFinite(n) ? (n > 0 ? '+' : '') + num(n, digits) : '—';
  }
  function statLabel(stat) { return STAT_LABELS[String(stat)] || String(stat || 'Stat'); }
  function bestTier(row) {
    const tiers = row && row.advice && row.advice.tiers;
    if (!Array.isArray(tiers) || !tiers.length) return null;
    return tiers.slice().sort((a, b) => Number(b.pts || 0) - Number(a.pts || 0) || Number(a.n_replace == null ? 999 : a.n_replace) - Number(b.n_replace == null ? 999 : b.n_replace))[0];
  }
  function statList(value) {
    if (Array.isArray(value)) return value;
    if (value && typeof value === 'object') return Object.entries(value).map(([stat, data]) => data && typeof data === 'object' ? Object.assign({ stat }, data) : ({ stat, value: data }));
    return [];
  }
  function getStats(row, tier) {
    const before = statList((row.advice && row.advice.before) || (row.before && row.before.stats));
    const after = statList((row.after && row.after.stats) || (tier && tier.result));
    const afterByStat = new Map(after.map(s => [String(s.stat), s]));
    return before.map(s => {
      const a = afterByStat.get(String(s.stat)) || {};
      const beforeValue = s.value != null ? s.value : (s.now != null ? s.now : s.after);
      const afterValue = a.value != null ? a.value : (a.after != null ? a.after : (a.now != null ? a.now : beforeValue));
      const target = s.target != null ? s.target : (row.before && Array.isArray(row.before.stats) ? ((row.before.stats.find(x => String(x.stat) === String(s.stat)) || {}).target) : null);
      return { stat: s.stat, before: beforeValue, after: afterValue, target };
    });
  }
  function slotAdvice(row, tier) {
    const entries = (tier && Array.isArray(tier.slots) ? tier.slots : null) || (row.advice && Array.isArray(row.advice.slots) ? row.advice.slots : []);
    return new Map(entries.map(s => [String(s.slot).toLowerCase(), s]));
  }
  function movesFor(row) { return Array.isArray(row.moves) ? row.moves : []; }
  function replacementDecision(slot, advice, move) {
    const decision = String(advice.decision || '');
    if (/remplac|replace/i.test(decision)) return true;
    if (/garder|keep/i.test(decision)) return false;
    return Boolean(move);
  }

  function findCharacterProgress(restoreData, unitId) {
    const candidate = String(unitId || '').trim().toUpperCase();
    if (!candidate || !restoreData || typeof restoreData !== 'object') return null;
    const roots = [restoreData];
    if (restoreData.profiles && typeof restoreData.profiles === 'object') {
      roots.push(...(Array.isArray(restoreData.profiles) ? restoreData.profiles : Object.values(restoreData.profiles)));
    }
    for (const root of roots) {
      const chars = root && root.characters;
      if (!chars || typeof chars !== 'object') continue;
      const entries = Array.isArray(chars) ? chars.map(ch => [ch && (ch.baseID || ch.baseId || ch.definitionId || ch.defId || ch.id), ch]) : Object.entries(chars);
      for (const [key, character] of entries) {
        if (!character || typeof character !== 'object') continue;
        const baseId = String(character.baseID || character.baseId || character.definitionId || character.defId || key || '').toUpperCase();
        if (baseId !== candidate && String(key || '').toUpperCase() !== candidate) continue;
        const values = character.playerValues && typeof character.playerValues === 'object' ? character.playerValues : character;
        return {
          stars: Number(values.stars) || 0,
          gearLevel: Number(values.gearLevel) || 0,
          relicTier: Number(values.relicTier) || 0
        };
      }
    }
    return { stars: 0, gearLevel: 0, relicTier: 0 };
  }

  function portraitMarkup(unitId, restoreData, altName) {
    if (!unitId) return '';
    return '<span class="remod-server-portrait" data-portrait-unit-id="' + esc(unitId) + '" aria-label="' + esc(altName || unitId) + '"><span class="remod-portrait-loading"></span></span>';
  }

  async function hydratePortraits(container, restoreData, csrfToken) {
    if (!container) return;
    const placeholders = Array.from(container.querySelectorAll('[data-portrait-unit-id]'));
    const uniqueIds = Array.from(new Set(placeholders.map(el => el.dataset.portraitUnitId).filter(Boolean)));
    if (!uniqueIds.length) return;
    const characters = uniqueIds.map(id => Object.assign({ id }, findCharacterProgress(restoreData, id)));
    try {
      const body = new FormData();
      body.append('action', 'portraits');
      body.append('csrf', csrfToken || '');
      body.append('characters', JSON.stringify(characters));
      const response = await fetch('codexcon.php', { method: 'POST', body, credentials: 'same-origin' });
      const responseText = await response.text();
      let result;
      try {
        result = JSON.parse(responseText);
      } catch (_) {
        throw new Error('Portrait endpoint returned non-JSON (HTTP ' + response.status + '): ' + responseText.slice(0, 300));
      }
      if (!response.ok) throw new Error(result.error || 'Unable to load character portraits (HTTP ' + response.status + ').');
      placeholders.forEach(el => {
        const markup = result.portraits && result.portraits[el.dataset.portraitUnitId];
        if (markup) el.innerHTML = markup;
        else el.textContent = el.dataset.portraitUnitId;
      });
    } catch (error) {
      console.warn('Codex Remod: could not load shared portrait renderer.', error);
      placeholders.forEach(el => {
        const id = el.dataset.portraitUnitId;
        el.innerHTML = '<img class="remod-portrait" src="IMAGES/CHARACTERS/' + esc(encodeURIComponent(id)) + '.png" alt="' + esc(id) + '" loading="lazy" onerror="this.style.visibility=\'hidden\'">';
        el.title = 'Shared portrait renderer unavailable; showing basic portrait. ' + error.message;
      });
    }
  }

  function renderCard(row, index, restoreData) {
    row = row && typeof row === 'object' ? row : {};
    const tier = bestTier(row);
    const stats = getStats(row, tier);
    const adviceBySlot = slotAdvice(row, tier);
    const moves = movesFor(row);
    const replacements = SLOT_ORDER.filter(slot => replacementDecision(slot, adviceBySlot.get(slot) || {}, moves.find(m => String(m.slot).toLowerCase() === slot))).length;
    const beforeQ = row.advice && (row.advice.pts_now != null ? row.advice.pts_now : row.before && row.before.points);
    const afterQ = tier && tier.pts != null ? tier.pts : (row.advice && row.advice.pts_ideal != null ? row.advice.pts_ideal : row.after && row.after.points);
    const gainRaw = Number(afterQ) - Number(beforeQ);
    const gain = beforeQ != null && afterQ != null && Number.isFinite(gainRaw) ? gainRaw : Number(row.advice && row.advice.gain);
    const name = row.hero || row.name || row.base || ('Character ' + (index + 1));
    const base = row.base || row.id || '';
    const statSummary = stats.slice(0, 3).map(s => statLabel(s.stat) + ' ' + signed(Number(s.after) - Number(s.before), String(s.stat) === 'speed' ? 1 : 0)).join(' · ');
    const sets = (tier && tier.sets_after) || (row.advice && row.advice.sets_after) || row.sets || [];
    const setText = Array.isArray(sets) ? sets.map(s => Array.isArray(s) ? String(s[1]) + ' ' + String(s[0]) : (typeof s === 'string' ? s : '')).filter(Boolean).join(' + ') : String(sets || '');
    const portrait = base ? 'IMAGES/CHARACTERS/' + encodeURIComponent(base) + '.png' : (row.thumb || row.portrait || row.image || '');
    const statRows = stats.map(s => {
      const delta = Number(s.after) - Number(s.before);
      const reached = s.target != null && Number(s.target) !== 0 && Number.isFinite(Number(s.after)) ? (Number(s.after) / Number(s.target) * 100) : null;
      return '<tr><th>' + esc(statLabel(s.stat)) + '</th><td>' + esc(num(s.before, 2)) + '</td><td>' + esc(num(s.after, 2)) + '</td><td class="' + (delta > 0 ? 'remod-positive' : delta < 0 ? 'remod-negative' : '') + '">' + esc(signed(delta, 2)) + '</td><td>' + esc(num(s.target, 2)) + '</td><td>' + (reached == null ? '—' : esc(num(reached, 1) + '%')) + '</td></tr>';
    }).join('');
    const modRows = SLOT_ORDER.map(slot => {
      const a = adviceBySlot.get(slot) || {};
      const move = moves.find(m => String(m.slot).toLowerCase() === slot);
      const replace = replacementDecision(slot, a, move);
      const current = a.current || a.mod || {};
      const from = (move && (move.from || move.from_owner || move.owner)) || current.owner || current.character || 'Current owner';
      const set = current.set ? ' · ' + esc(current.set) + ' set' : '';
      const primary = current.primary != null ? ' · primary ' + esc(current.primary) : '';
      const need = a.need || {};
      const required = Object.keys(need).length ? '<div class="remod-muted"><strong>Needed:</strong> ' + esc(need.set || 'set unrestricted') + (need.primary != null ? ', primary ' + esc(need.primary) : '') + (Array.isArray(need.secs) ? need.secs.map(x => '; ' + esc(statLabel(x[0])) + ' ' + esc(num(x[1], 2))).join('') : '') + '</div>' : '';
      const defects = Array.isArray(a.defects) ? a.defects.map(d => esc(Array.isArray(d) ? statLabel(d[1]) + ': ' + num(d[2], 2) + ' → ' + num(d[3], 2) : d)).join(', ') : '';
      return '<tr><th>' + esc(SLOT_LABELS[slot]) + '</th><td><span class="remod-decision ' + (replace ? 'replace' : 'keep') + '">' + (replace ? 'Replace' : 'Keep') + '</span><div class="remod-muted">From ' + esc(from) + set + primary + '</div>' + required + (defects ? '<div class="remod-muted">Reason: ' + defects + '</div>' : '') + '</td></tr>';
    }).join('');
    const alternatives = row.advice && Array.isArray(row.advice.tiers) ? row.advice.tiers : [];
    const tierRows = alternatives.map(t => '<tr><td>' + esc(t.pts == null ? '—' : t.pts) + '</td><td>' + esc(t.gain == null ? '—' : t.gain) + '</td><td>' + esc(t.n_replace == null ? '—' : t.n_replace) + '</td><td>' + esc(Array.isArray(t.sets_after) ? t.sets_after.map(s => Array.isArray(s) ? s[1] + ' ' + s[0] : '').filter(Boolean).join(' + ') : '—') + '</td></tr>').join('');
    const maxQ = (row.advice && row.advice.max) || (row.after && row.after.max) || (row.before && row.before.max) || '—';
    const search = (name + ' ' + base + ' ' + statSummary + ' ' + setText).toLowerCase();
    return '<details class="remod-plan-card" data-unit-id="' + esc(base) + '" data-name="' + esc(String(name).toLowerCase()) + '" data-replacements="' + replacements + '" data-gain="' + (Number.isFinite(gain) ? gain : -999) + '" data-search="' + esc(search) + '">' +
      '<summary class="remod-plan-summary"><span class="remod-rank">' + (index + 1) + '</span>' +
      (portrait ? portraitMarkup(base, restoreData, name) : '<span class="remod-portrait remod-initials">' + esc(String(name).split(/\s+/).map(w => w[0] || '').join('').slice(0, 2).toUpperCase()) + '</span>') +
      '<span class="remod-identity"><strong>' + esc(name) + '</strong><small>' + esc(base) + ' · ' + replacements + ' mod(s) to replace</small><small class="remod-stat-summary">' + esc(statSummary || 'Stat comparison unavailable') + '</small></span>' +
      '<span class="remod-gain ' + (gain > 0 ? 'remod-positive' : gain < 0 ? 'remod-negative' : '') + '">' + (Number.isFinite(gain) ? esc(signed(gain, 0) + ' StatQ') : 'StatQ —') + '</span><span class="remod-chevron">⌄</span></summary>' +
      '<div class="remod-plan-expanded"><div class="remod-plan-meta"><span><strong>StatQ:</strong> ' + esc(beforeQ == null ? '—' : beforeQ) + ' → ' + esc(afterQ == null ? '—' : afterQ) + ' / ' + esc(maxQ) + '</span><span><strong>Sets:</strong> ' + esc(setText || 'Not specified') + '</span><span><strong>Time:</strong> ' + esc(row.seconds == null ? '—' : num(row.seconds, 2) + ' s') + '</span></div>' +
      '<h4>Stat changes</h4><div class="remod-table-wrap"><table class="remod-plan-table"><thead><tr><th>Stat</th><th>Before</th><th>Projected after</th><th>Change</th><th>Target</th><th>Target %</th></tr></thead><tbody>' + (statRows || '<tr><td colspan="6">No stat details in this plan entry.</td></tr>') + '</tbody></table></div>' +
      '<h4>Mods</h4><div class="remod-table-wrap"><table class="remod-plan-table remod-mod-table"><tbody>' + modRows + '</tbody></table></div>' +
      (tierRows ? '<details class="remod-alternatives"><summary>Alternative plans (' + alternatives.length + ')</summary><div class="remod-table-wrap"><table class="remod-plan-table"><thead><tr><th>StatQ</th><th>Gain</th><th>Replacements</th><th>Sets</th></tr></thead><tbody>' + tierRows + '</tbody></table></div></details>' : '') +
      '<details class="remod-technical"><summary>Technical details</summary><pre>' + esc(JSON.stringify({ solver: row.solver, advice: row.advice }, null, 2)) + '</pre></details></div></details>';
  }

  function renderPlan(container, planData, restoreData, csrfToken) {
    const rows = Array.isArray(planData) ? planData : planData && Array.isArray(planData.plan) ? planData.plan : null;
    if (!rows) throw new Error('The archive does not contain a plan.json with a top-level "plan" array.');
    const toolbar = document.createElement('div');
    toolbar.className = 'remod-plan-toolbar';
    toolbar.innerHTML = '<div class="remod-plan-count"><strong>' + rows.length + '</strong> characters in the plan</div>' +
      '<input type="search" class="remod-plan-search" placeholder="Search character or stat…" aria-label="Search plan">' +
      '<select class="remod-plan-filter" aria-label="Filter plan"><option value="all">All characters</option><option value="replace">Mods to replace</option><option value="gain">StatQ gain</option><option value="complete">No replacements</option></select>' +
      '<select class="remod-plan-sort" aria-label="Sort plan"><option value="order">Plan order</option><option value="gain">Highest StatQ gain</option><option value="replace">Most replacements</option><option value="name">Character name</option></select>' +
      '<button type="button" class="remod-button secondary remod-expand-all">Expand all</button><button type="button" class="remod-button secondary remod-collapse-all">Collapse all</button>';
    const list = document.createElement('div');
    list.className = 'remod-plan-list';
    list.innerHTML = rows.map((row, index) => renderCard(row, index, restoreData)).join('');
    container.replaceChildren(toolbar, list);
    hydratePortraits(container, restoreData, csrfToken);
    const search = toolbar.querySelector('.remod-plan-search');
    const filter = toolbar.querySelector('.remod-plan-filter');
    const sort = toolbar.querySelector('.remod-plan-sort');
    const cards = Array.from(list.querySelectorAll('.remod-plan-card'));
    function update() {
      const q = search.value.trim().toLowerCase();
      const mode = filter.value;
      cards.forEach(card => {
        const n = Number(card.dataset.replacements);
        const g = Number(card.dataset.gain);
        card.hidden = !(card.dataset.search.includes(q) && (mode === 'all' || mode === 'replace' && n > 0 || mode === 'gain' && g > 0 || mode === 'complete' && n === 0));
      });
      cards.slice().sort((a, b) => sort.value === 'gain' ? Number(b.dataset.gain) - Number(a.dataset.gain) : sort.value === 'replace' ? Number(b.dataset.replacements) - Number(a.dataset.replacements) : sort.value === 'name' ? a.dataset.name.localeCompare(b.dataset.name) : Number(a.dataset.order) - Number(b.dataset.order)).forEach(card => list.appendChild(card));
    }
    cards.forEach((card, i) => { card.dataset.order = String(i); });
    search.placeholder = 'Search character, stat or metadata…';
    search.addEventListener('input', update);
    filter.addEventListener('change', update);
    sort.addEventListener('change', update);
    addMetadataToCardSearch(container, '.remod-plan-card');
    toolbar.querySelector('.remod-expand-all').addEventListener('click', () => cards.filter(c => !c.hidden).forEach(c => { c.open = true; }));
    toolbar.querySelector('.remod-collapse-all').addEventListener('click', () => cards.forEach(c => { c.open = false; }));
    update();
    return rows.length;
  }

  async function extractPlanFromZip(blob) {
    const bytes = new Uint8Array(await blob.arrayBuffer());
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const u16 = offset => view.getUint16(offset, true);
    const u32 = offset => view.getUint32(offset, true);
    let eocd = -1;
    for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 65557); i--) {
      if (u32(i) === 0x06054b50) { eocd = i; break; }
    }
    if (eocd < 0) throw new Error('The downloaded file is not a valid ZIP archive.');
    const count = u16(eocd + 10);
    let offset = u32(eocd + 16);
    for (let i = 0; i < count; i++) {
      if (u32(offset) !== 0x02014b50) throw new Error('Invalid ZIP directory entry.');
      const method = u16(offset + 10), size = u32(offset + 20);
      const nameLength = u16(offset + 28), extraLength = u16(offset + 30), commentLength = u16(offset + 32);
      const localOffset = u32(offset + 42);
      const name = new TextDecoder().decode(bytes.subarray(offset + 46, offset + 46 + nameLength));
      if (name.toLowerCase() === 'plan.json' || name.toLowerCase().endsWith('/plan.json')) {
        if (u32(localOffset) !== 0x04034b50) throw new Error('Invalid plan.json entry.');
        const localNameLength = u16(localOffset + 26), localExtraLength = u16(localOffset + 28);
        const start = localOffset + 30 + localNameLength + localExtraLength;
        const compressed = bytes.slice(start, start + size);
        let payload;
        if (method === 0) payload = compressed;
        else if (method === 8 && typeof DecompressionStream !== 'undefined') {
          payload = new Uint8Array(await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('deflate-raw'))).arrayBuffer());
        } else throw new Error('Unsupported ZIP compression or browser. Please use a recent Chrome/Edge/Firefox browser.');
        const text = new TextDecoder().decode(payload);
        const data = JSON.parse(text);
        return { data, text };
      }
      offset += 46 + nameLength + extraLength + commentLength;
    }
    throw new Error('The ZIP archive does not contain plan.json.');
  }


  async function extractArchiveFile(blob, targetName) {
    const bytes = new Uint8Array(await blob.arrayBuffer());
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const u16 = offset => view.getUint16(offset, true);
    const u32 = offset => view.getUint32(offset, true);
    let eocd = -1;
    for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 65557); i--) {
      if (u32(i) === 0x06054b50) { eocd = i; break; }
    }
    if (eocd < 0) throw new Error('The downloaded file is not a valid ZIP archive.');
    const wanted = String(targetName).toLowerCase();
    const count = u16(eocd + 10);
    let offset = u32(eocd + 16);
    for (let i = 0; i < count; i++) {
      if (u32(offset) !== 0x02014b50) throw new Error('Invalid ZIP directory entry.');
      const method = u16(offset + 10), compressedSize = u32(offset + 20);
      const nameLength = u16(offset + 28), extraLength = u16(offset + 30), commentLength = u16(offset + 32);
      const localOffset = u32(offset + 42);
      const name = new TextDecoder().decode(bytes.subarray(offset + 46, offset + 46 + nameLength));
      if (name.toLowerCase() === wanted || name.toLowerCase().endsWith('/' + wanted)) {
        if (u32(localOffset) !== 0x04034b50) throw new Error('Invalid ' + targetName + ' ZIP entry.');
        const localNameLength = u16(localOffset + 26), localExtraLength = u16(localOffset + 28);
        const start = localOffset + 30 + localNameLength + localExtraLength;
        const compressed = bytes.slice(start, start + compressedSize);
        let payload;
        if (method === 0) payload = compressed;
        else if (method === 8 && typeof DecompressionStream !== 'undefined') {
          payload = new Uint8Array(await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('deflate-raw'))).arrayBuffer());
        } else throw new Error('Unsupported ZIP compression or browser. Please use a recent Chrome/Edge/Firefox browser.');
        return new Blob([payload]);
      }
      offset += 46 + nameLength + extraLength + commentLength;
    }
    throw new Error('The results archive does not contain ' + targetName + '.');
  }

  async function extractArchiveText(blob, targetName) {
    return new TextDecoder().decode(await (await extractArchiveFile(blob, targetName)).arrayBuffer());
  }

  function parseCsv(text) {
    const rows = [];
    let row = [], cell = '', quoted = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (ch === '"') {
        if (quoted && text[i + 1] === '"') { cell += '"'; i++; }
        else quoted = !quoted;
      } else if (!quoted && (ch === ',' || ch === ';' || ch === '\t')) {
        row.push(cell.trim()); cell = '';
      } else if (!quoted && (ch === '\n' || ch === '\r')) {
        if (ch === '\r' && text[i + 1] === '\n') i++;
        row.push(cell.trim()); cell = '';
        if (row.some(v => v !== '')) rows.push(row);
        row = [];
      } else cell += ch;
    }
    row.push(cell.trim());
    if (row.some(v => v !== '')) rows.push(row);
    return rows;
  }

  function resolveCharacterPortraitId(restoreData, characterRaw) {
    if (characterRaw === null || characterRaw === undefined || characterRaw === '') return '';
    if (typeof characterRaw === 'object') {
      characterRaw = characterRaw.baseID || characterRaw.baseId || characterRaw.definitionId ||
        characterRaw.defId || characterRaw.characterID || characterRaw.characterId ||
        characterRaw.id || '';
    }
    const candidate = String(characterRaw || '').trim().toUpperCase();
    if (!candidate) return '';

    // RestoreMyProgress stores character records by baseID. If the supplied value
    // is already a unit ID, preserve it; otherwise try to resolve common wrappers.
    const progress = findCharacterProgress(restoreData, candidate);
    if (progress) return candidate;
    const match = candidate.match(/(?:^|[:_])([A-Z][A-Z0-9]+)$/);
    if (match) {
      const possibleId = match[1];
      if (findCharacterProgress(restoreData, possibleId)) return possibleId;
      return possibleId;
    }
    return candidate;
  }

  function collectInventoryMods(restoreData) {
    const roots = [restoreData];
    if (restoreData && restoreData.profiles && typeof restoreData.profiles === 'object') {
      roots.push(...(Array.isArray(restoreData.profiles) ? restoreData.profiles : Object.values(restoreData.profiles)));
    }
    const found = new Map();
    roots.forEach(root => {
      const mods = root && root.mods;
      if (!mods || typeof mods !== 'object') return;
      const entries = Array.isArray(mods) ? mods.map((mod, i) => [String(i), mod]) : Object.entries(mods);
      entries.forEach(([key, mod]) => {
        if (!mod || typeof mod !== 'object') return;
        [mod.id, mod.modId, mod.mod_id, mod.mod_uid, mod.modUid, mod.uid, key].forEach(rawId => {
          const id = String(rawId == null ? '' : rawId).trim();
          if (id && !found.has(id)) found.set(id, mod);
        });
      });
    });
    return found;
  }

  function csvModRows(csvText) {
    const rows = parseCsv(String(csvText || '').replace(/^\uFEFF/, ''));
    if (!rows.length) return [];
    const headers = rows.shift().map(value => String(value || '').trim().toLowerCase().replace(/[\s-]+/g, '_'));
    const idIndex = headers.findIndex(value => /^(id_mod|mod_id|mod_uid|id|identifiant)$/.test(value));
    const ownerIndex = headers.findIndex(value => value === 'porte_par' || value === 'portepar');
    return rows.map(row => ({
      id: String(row[idIndex >= 0 ? idIndex : 1] || '').trim(),
      portePar: String(row[ownerIndex >= 0 ? ownerIndex : -1] || '').trim()
    })).filter(row => row.id);
  }

  function modField(mod, keys) {
    for (const key of keys) if (mod[key] !== undefined && mod[key] !== null && mod[key] !== '') return mod[key];
    return null;
  }

  function statPayload(stat) {
    let payload = stat;
    // SWGOH mod stats are usually {stat:{unitStatId,statValueDecimal},statRolls}.
    // Accept extra wrappers used by some progress-file exporters as well.
    for (let depth = 0; depth < 4 && payload && typeof payload === 'object'; depth++) {
      const nested = payload.stat || payload.statInfo || payload.stat_info;
      if (!nested || typeof nested !== 'object') break;
      payload = nested;
    }
    return payload;
  }

  function statContainer(mod) {
    const visited = new Set();
    const queue = [{ value: mod, depth: 0 }];
    while (queue.length) {
      const item = queue.shift();
      const current = item.value;
      if (!current || typeof current !== 'object' || visited.has(current) || item.depth > 4) continue;
      visited.add(current);
      if (current.primaryStat || current.secondaryStat || current.secondaryStats ||
          current.primary_stat || current.secondary_stats) return current;
      ['mod', 'modData', 'data', 'details', 'stats', 'modStats'].forEach(key => {
        const nested = current[key];
        if (nested && typeof nested === 'object') queue.push({ value: nested, depth: item.depth + 1 });
      });
    }
    return mod || {};
  }

  function statName(stat) {
    if (stat === undefined || stat === null || stat === '') return 'Stat';
    const outer = stat && typeof stat === 'object' ? stat : {};
    const payload = statPayload(stat);
    const id = Number((payload && payload.unitStatId) ?? (outer.stat && outer.stat.unitStatId));
    const idLabels = {
      1:'Health', 5:'Speed', 16:'Critical Damage %', 17:'Potency %',
      18:'Tenacity %', 28:'Protection', 41:'Offense', 42:'Defense',
      48:'Offense %', 49:'Defense %', 52:'Accuracy %',
      53:'Critical Chance %', 54:'Critical Avoidance %',
      55:'Health %', 56:'Protection %'
    };
    if (Number.isFinite(id) && idLabels[id]) return idLabels[id];
    let raw = typeof stat === 'object'
      ? (outer.name || outer.statName || outer.stat_name || outer.unitStatName || outer.unitStat || payload.name || payload.statName || payload.stat_name || payload.unitStatName || payload.unitStat || payload.stat || payload.type || 'Stat')
      : stat;
    if (typeof raw === 'object') raw = raw.name || raw.unitStatName || raw.type || '';
    raw = String(raw || 'Stat');
    const normalized = raw.toLowerCase().replace(/^unitstat_?/, '').replace(/[^a-z0-9]/g, '');
    const labels = {
      health:'Health', maxhealth:'Health', protection:'Protection', speed:'Speed',
      potency:'Potency', tenacity:'Tenacity', criticalchance:'Critical Chance',
      critchance:'Critical Chance', criticaldamage:'Critical Damage', critdamage:'Critical Damage',
      physicaldamage:'Physical Damage', physicaloffense:'Physical Damage',
      specialdamage:'Special Damage', specialoffense:'Special Damage', armor:'Armor',
      resistance:'Resistance', accuracy:'Accuracy', dodge:'Dodge', deflection:'Deflection',
      healthsteal:'Health Steal', physicalcriticalchance:'Physical Critical Chance',
      specialcriticalchance:'Special Critical Chance', mastery:'Mastery'
    };
    return labels[normalized] || raw.replace(/^UNITSTAT_?/i, '').replace(/_/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase());
  }

  function statValue(stat) {
    if (stat === null || stat === undefined) return '';
    if (typeof stat !== 'object') return String(stat);
    const outer = stat;
    const payload = statPayload(stat);
    let value = modField(outer, ['value','statValue','stat_value','decimalValue','decimal_value','valueDecimal','unscaledDecimalValue','unscaled_decimal_value','statValueDecimal','amount']);
    if (value === null) value = modField(payload, ['unscaledDecimalValue','unscaled_decimal_value','statValueDecimal','value','statValue','stat_value','decimalValue','decimal_value','valueDecimal','amount']);
    if (value === null) return '';
    const id = Number(payload && payload.unitStatId);
    const hasUnscaled = payload && payload.unscaledDecimalValue !== undefined && payload.unscaledDecimalValue !== null;
    const hasStatDecimal = payload && payload.statValueDecimal !== undefined && payload.statValueDecimal !== null;
    if (hasUnscaled) {
      const percentageIds = new Set([16,17,18,48,49,52,53,54,55,56]);
      const scaled = Number(value) * (percentageIds.has(id) ? 1e-6 : 1e-8);
      return Number.isFinite(scaled) ? String(Number(scaled.toFixed(3))) : String(value);
    }
    if (hasStatDecimal && outer.value === undefined) {
      const percentageIds = new Set([16,17,18,48,49,52,53,54,55,56]);
      const scaled = Number(value) / (percentageIds.has(id) ? 100 : 10000);
      return Number.isFinite(scaled) ? String(Number(scaled.toFixed(3))) : String(value);
    }
    return String(value);
  }

  function statRerolls(stat) {
    if (!stat || typeof stat !== 'object') return 0;
    const keys = ['statRolls','stat_rolls','rolls','reroll','rerolls','rollCount','roll_count','statRollCount'];
    let value = modField(stat, keys);
    if (value === null) value = modField(statPayload(stat), keys);
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  }

  function statText(stat) {
    if (stat === null || stat === undefined) return '';
    const name = statName(stat);
    const value = statValue(stat);
    return [value, name].filter(Boolean).join(' ');
  }

  function renderDeleteMods(container, csvText, restoreData, csrfToken) {
    const rows = csvModRows(csvText);
    const inventory = collectInventoryMods(restoreData);
    const matches = rows.map(row => ({ ...row, mod: inventory.get(row.id) })).filter(item => item.mod);
    const slotNames = { 2:'Square', 3:'Arrow', 4:'Diamond', 5:'Triangle', 6:'Circle', 7:'Cross', square:'Square', arrow:'Arrow', diamond:'Diamond', triangle:'Triangle', circle:'Circle', cross:'Cross' };
    const setNames = { 1:'Health', 2:'Offense', 3:'Defense', 4:'Speed', 5:'Critical Chance', 6:'Critical Damage', 7:'Potency', 8:'Tenacity', health:'Health', offense:'Offense', defense:'Defense', speed:'Speed', critchance:'Critical Chance', critdamage:'Critical Damage', potency:'Potency', tenacity:'Tenacity' };
    // Authorization is decided by PHP for the allyCode supplied in ?ac=.
    // Never infer sell permissions from the uploaded file or client-side session data.
    const allyCode = String(window.codexRemodAllyCode || '');
    const canSellMods = window.codexRemodCanSellMods === true;
    const renderStats = mod => {
      const source = statContainer(mod);
      let primary = modField(source, ['primaryStat','primary','primary_stat']);
      if (primary === null) {
        const name = modField(source, ['primaryBonusType','primaryStatName','primary_stat_name','primaryStatType']);
        const value = modField(source, ['primaryBonusValue','primaryStatValue','primary_stat_value','primaryValue']);
        if (name !== null || value !== null) primary = { stat: name || 'Primary', value: value };
      }
      let secondary = modField(source, ['secondaryStat','secondaryStats','secondary','secondary_stats']);
      if (!Array.isArray(secondary)) {
        if (secondary && typeof secondary === 'object') {
          secondary = Object.values(secondary);
        } else {
          secondary = [];
          for (let i = 1; i <= 4; i++) {
            const name = modField(source, ['secondaryType_' + i, 'secondaryStat' + i, 'secondary_stat_' + i, 'secondary' + i]);
            const value = modField(source, ['secondaryValue_' + i, 'secondaryStat' + i + 'Value', 'secondary_stat_' + i + '_value']);
            const rerolls = modField(source, ['secondaryRoll_' + i, 'secondaryStat' + i + 'Rolls', 'secondary_stat_' + i + '_rolls']);
            if (name !== null || value !== null) secondary.push({ stat: name || 'Stat', value, statRolls: rerolls });
          }
        }
      }
      const primaryText = primary !== null ? statText(primary) : '';
      const secondaryHtml = secondary.slice(0, 4).map(stat => {
        if (stat === null || stat === undefined) return '';
        const rerolls = statRerolls(stat);
        const text = statText(stat);
        return text ? '<div class="remod-delete-secondary">(' + esc(rerolls) + ') ' + esc(text) + '</div>' : '';
      }).join('');
      return (primaryText ? '<div class="remod-delete-primary">' + esc(primaryText) + '</div>' : '') + secondaryHtml;
    };
    container.replaceChildren();
    const toolbar = document.createElement('div');
    toolbar.className = 'remod-delete-toolbar';
    toolbar.innerHTML =
      '<strong>' + matches.length + ' matching mods</strong>' +
      '<label class="remod-delete-filter"><input type="checkbox" id="remodUnequippedOnly"> <span>Unequipped mods</span></label>' +
      '<button type="button" id="remodDeleteSelectAll" hidden>Select all</button>' +
      '<button type="button" id="remodDeleteUnselectAll" hidden>Unselect all</button>' +
      '<button type="button" id="remodSellMods" hidden disabled>sell 0 mods</button>' +
      '<span class="remod-delete-feedback" role="status" aria-live="polite"></span>';
    const grid = document.createElement('div');
    grid.className = 'remod-delete-grid';
    grid.innerHTML = matches.map(({id,mod,portePar}) => {
      const slotRaw = modField(mod,['slot','slotId','slot_id']);
      const slot = String(slotRaw == null ? '' : slotRaw).toLowerCase();
      const slotNum = /^\d+$/.test(slot) ? Number(slot) : ({square:2,arrow:3,diamond:4,triangle:5,circle:6,cross:7}[slot] || 0);
      const setRaw = modField(mod,['set','modSet','mod_set','setId','set_id']);
      const setKey = String(setRaw == null ? '' : setRaw).toLowerCase();
      const setNum = /^\d+$/.test(setKey) ? Number(setKey) : 0;
      const pips = Math.max(1, Math.min(6, Number(modField(mod,['pips','dots','dotCount','dot_count']) || 5)));
      const tier = Math.max(1,Math.min(5,Number(modField(mod,['tier','rarity','colorTier','color_tier']) || 1)));
      const shapeIndex = Math.max(0,Math.min(5,slotNum-2)) + (pips >= 6 ? 6 : 0);
      const iconIndex = Math.max(0,Math.min(7,(setNum || ({health:1,offense:2,defense:3,speed:4,critchance:5,critdamage:6,potency:7,tenacity:8}[setKey] || 1))-1));
      const charRaw = modField(mod,['characterID','characterId','character_id','defId','def_id','owner','assignedTo','assigned_to','characterID']);
      const characterRaw = charRaw && typeof charRaw === 'object' ? (charRaw.baseId || charRaw.defId || charRaw.id || '') : String(charRaw || '');
      const character = resolveCharacterPortraitId(restoreData, characterRaw);
      const level = modField(mod,['level','lvl']);
      const title = (setNames[setNum] || setNames[setKey] || 'Mod')+' · '+(slotNames[slotNum] || slotNames[slot] || 'Unknown slot');
      const assigned = portePar.trim() !== '';
      return '<article class="remod-delete-card" data-porte-par="' + esc(portePar) + '" data-mod-id="' + esc(id) + '" data-assigned="' + (assigned ? '1' : '0') + '">' +
        (canSellMods ? '<label class="remod-delete-select"><input type="checkbox" class="remod-delete-checkbox" value="' + esc(id) + '" aria-label="Select mod ' + esc(id) + '"></label>' : '') +
        '<div class="remod-delete-title">' + esc(title) + '</div>' +
        '<div class="remod-delete-art" style="--shape-x:' + shapeIndex + ';--shape-y:' + (tier-1) + ';--icon-x:' + iconIndex + ';--icon-y:' + (tier-1) + '">' +
          '<div class="remod-delete-overlay"><span class="remod-delete-stars">' + '★'.repeat(pips) + '</span><span class="remod-delete-level">Lvl ' + esc(level == null ? 0 : level) + '</span></div>' +
          (character ? '<img class="remod-delete-portrait" src="IMAGES/CHARACTERS/' + encodeURIComponent(character) + '.png" alt="" loading="lazy" onerror="this.hidden=true">' : '') +
        '</div>' +
        '<div class="remod-delete-stats">' + renderStats(mod) + '</div>' +
      '</article>';
    }).join('');
    const unequipped = toolbar.querySelector('#remodUnequippedOnly');
    const selectAll = toolbar.querySelector('#remodDeleteSelectAll');
    const unselectAll = toolbar.querySelector('#remodDeleteUnselectAll');
    const sellButton = toolbar.querySelector('#remodSellMods');
    const feedback = toolbar.querySelector('.remod-delete-feedback');
    const applyUnequippedFilter = () => {
      grid.querySelectorAll('.remod-delete-card').forEach(card => {
        card.hidden = unequipped.checked && card.dataset.portePar.trim() !== '';
      });
    };
    unequipped.addEventListener('change', applyUnequippedFilter);
    selectAll.addEventListener('click', () => {
      grid.querySelectorAll('.remod-delete-card:not([hidden]) .remod-delete-checkbox').forEach(box => { box.checked = true; });
      updateSellButton();
      clearButtonFocus(selectAll);
    });
    unselectAll.addEventListener('click', () => {
      grid.querySelectorAll('.remod-delete-card:not([hidden]) .remod-delete-checkbox').forEach(box => { box.checked = false; });
      updateSellButton();
      clearButtonFocus(unselectAll);
    });
    if (canSellMods) {
      sellButton.hidden = false;
      selectAll.hidden = false;
      unselectAll.hidden = false;
    }
    const clearButtonFocus = button => {
      button.blur();
      button.classList.remove('focus');
    };
    const updateSellButton = () => {
      const selectedCount = grid.querySelectorAll('.remod-delete-checkbox:checked').length;
      sellButton.textContent = 'sell ' + selectedCount + ' mods';
      sellButton.disabled = selectedCount === 0;
    };
    grid.addEventListener('change', event => {
      if (event.target && event.target.matches('.remod-delete-checkbox')) updateSellButton();
    });
    updateSellButton();
    sellButton.addEventListener('click', async () => {
      const selected = Array.from(grid.querySelectorAll('.remod-delete-card:not([hidden]) .remod-delete-checkbox:checked')).map(box => box.value);
      if (!selected.length) { feedback.textContent = 'Select at least one mod first.'; return; }
      if (!canSellMods || !allyCode) { feedback.textContent = 'Selling mods is not enabled for this page.'; return; }
      sellButton.disabled = true;
      feedback.textContent = 'Sending selected mods…';
      try {
        const body = new FormData();
        body.append('action', 'sell_mods');
        body.append('csrf', csrfToken || '');
        body.append('allyCode', allyCode);
        body.append('scope_token', String(window.codexRemodSellScopeToken || ''));
        body.append('mod_ids', JSON.stringify(selected));
        const response = await fetch('codexcon.php', { method: 'POST', body, credentials: 'same-origin' });
        const result = await response.json();
        if (!response.ok || result.ok !== true) throw new Error(result.error || 'Sell mods request failed.');
        selected.forEach(modId => {
          const card = grid.querySelector('.remod-delete-card[data-mod-id="' + CSS.escape(modId) + '"]');
          if (!card) return;
          card.dataset.sold = '1';
          card.classList.add('remod-delete-card-sold');
          const checkboxLabel = card.querySelector('.remod-delete-select');
          if (checkboxLabel) checkboxLabel.remove();
          const soldOverlay = document.createElement('div');
          soldOverlay.className = 'remod-delete-sold-overlay';
          soldOverlay.setAttribute('aria-label', 'SOLD');
          soldOverlay.textContent = 'SOLD';
          card.appendChild(soldOverlay);
        });
        updateSellButton();
        feedback.textContent = result.err_txt || 'Selected mods sold successfully.';
      } catch (error) {
        feedback.textContent = error.message || 'Unable to send sell mods request.';
      } finally {
        sellButton.disabled = false;
      }
    });
    applyUnequippedFilter();
    container.append(toolbar,grid);
    return matches.length;
  }

  function parseSemicolonCsv(text) {
    text = String(text || '').replace(/^\uFEFF/, '');
    const rows = [];
    let row = [], field = '', quoted = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (quoted) {
        if (ch === '"' && text[i + 1] === '"') { field += '"'; i++; }
        else if (ch === '"') quoted = false;
        else field += ch;
      } else if (ch === '"' && field === '') quoted = true;
      else if (ch === ';') { row.push(field); field = ''; }
      else if (ch === '\n' || ch === '\r') {
        if (ch === '\r' && text[i + 1] === '\n') i++;
        row.push(field); field = '';
        if (row.some(value => value !== '')) rows.push(row);
        row = [];
      } else field += ch;
    }
    if (field !== '' || row.length) { row.push(field); if (row.some(value => value !== '')) rows.push(row); }
    if (!rows.length) return [];
    const headers = rows.shift().map(value => value.trim());
    return rows.map(values => Object.fromEntries(headers.map((header, index) => [header, String(values[index] == null ? '' : values[index]).trim()])));
  }

  function renderStatq(container, csvText, restoreData, csrfToken) {
    const rows = parseSemicolonCsv(csvText);
    if (!rows.length) throw new Error('statq.csv contains no StatQ rows.');
    const grouped = new Map();
    rows.forEach(row => {
      const id = row.id || row.personnage || 'unknown';
      const key = id + '|' + (row.personnage || '');
      if (!grouped.has(key)) grouped.set(key, { id, name: row.personnage || id, rows: [] });
      grouped.get(key).rows.push(row);
    });
    const statLabelFr = {
      vitesse: 'Vitesse', speed: 'Speed', santé: 'Santé', health: 'Health',
      protection: 'Protection', pouvoir: 'Pouvoir', potency: 'Potency',
      ténacité: 'Ténacité', tenacity: 'Tenacity', 'dégâts critiques': 'Dégâts critiques',
      crit_damage: 'Critical damage', degphys: 'Dégâts physiques', physical_damage: 'Physical damage',
      degspec: 'Dégâts spéciaux', special_damage: 'Special damage', armure: 'Armure',
      armor: 'Armor', résistance: 'Résistance', resistance: 'Resistance',
      'chance critique': 'Chance critique', crit_chance: 'Critical chance'
    };
    const cards = Array.from(grouped.values());
    const totalPoints = rows.reduce((sum, row) => sum + (Number(row.points) || 0), 0);
    const totalMax = rows.reduce((sum, row) => sum + (Number(row.points_max) || 0), 0);
    const fmt = (value, digits = 1) => {
      const n = Number(value);
      return value !== '' && Number.isFinite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: digits }) : '—';
    };
    const pct = totalMax ? (100 * totalPoints / totalMax) : 0;
    const cardHtml = cards.map((hero, index) => {
      const points = hero.rows.reduce((sum, row) => sum + (Number(row.points) || 0), 0);
      const max = hero.rows.reduce((sum, row) => sum + (Number(row.points_max) || 0), 0);
      const pctHero = max ? 100 * points / max : 0;
      const summary = hero.rows.map(row => (statLabelFr[String(row.stat || '').toLowerCase()] || row.stat || 'Stat') + ' ' + (row.points || '0') + '/' + (row.points_max || '4')).join(' · ');
      const portrait = hero.id ? 'IMAGES/CHARACTERS/' + encodeURIComponent(hero.id) + '.png' : '';
      const statRows = hero.rows.map(row => {
        const pointsNow = Number(row.points);
        const maxNow = Number(row.points_max);
        const pctNow = Number(row.avancement_pct);
        const scoreClass = pointsNow >= 3 ? 'remod-positive' : pointsNow === 0 ? 'remod-negative' : '';
        const statName = statLabelFr[String(row.stat || '').toLowerCase()] || row.stat || 'Stat';
        return '<tr><th>' + esc(statName) + '</th><td>' + esc(fmt(row.valeur_totale, 2)) + '</td><td>' + esc(fmt(row.apport_mods, 2)) + '</td><td>' + esc(fmt(row.objectif, 2)) + '</td><td>' + esc(fmt(row.cible_mods_k1, 2)) + '</td><td>' + esc(row.avancement_pct === '' ? '—' : fmt(row.avancement_pct, 1) + '%') + '</td><td class="' + scoreClass + '"><strong>' + esc(Number.isFinite(pointsNow) ? pointsNow : '—') + '/' + esc(Number.isFinite(maxNow) ? maxNow : '—') + '</strong></td></tr>';
      }).join('');
      return '<details class="remod-plan-card statq-character-card" data-unit-id="' + esc(hero.id) + '" data-search="' + esc((hero.name + ' ' + hero.id + ' ' + summary).toLowerCase()) + '">' +
        '<summary class="remod-plan-summary"><span class="remod-rank">' + (index + 1) + '</span>' +
        (portrait ? portraitMarkup(hero.id, restoreData, hero.name) : '') +
        '<span class="remod-identity"><strong>' + esc(hero.name) + '</strong><small>' + esc(hero.id) + ' · ' + hero.rows.length + ' stat(s)</small><small class="remod-stat-summary">' + esc(summary) + '</small></span>' +
        '<span class="remod-gain ' + (pctHero >= 75 ? 'remod-positive' : pctHero < 25 ? 'remod-negative' : '') + '">' + esc(points + '/' + max + ' StatQ · ' + fmt(pctHero, 1) + '%') + '</span><span class="remod-chevron">⌄</span></summary>' +
        '<div class="remod-plan-expanded"><div class="remod-table-wrap"><table class="remod-plan-table"><thead><tr><th>Stat</th><th>Current total</th><th>Mods contribution</th><th>Target</th><th>K1 mods target</th><th>Progress</th><th>StatQ</th></tr></thead><tbody>' + statRows + '</tbody></table></div></div></details>';
    }).join('');
    container.innerHTML = '<div class="remod-plan-toolbar"><div class="remod-plan-search"><label for="statqCharacterSearch">Search characters</label><input id="statqCharacterSearch" type="search" placeholder="Character name or ID"></div><div class="remod-plan-count">' + cards.length + ' characters</div></div>' +
      '<p class="remod-help"><strong>Total StatQ:</strong> ' + esc(totalPoints + ' / ' + totalMax + ' (' + fmt(pct, 1) + '%)') + ' · ' + rows.length + ' stat rows</p>' +
      '<div class="remod-plan-list">' + cardHtml + '</div>';
    hydratePortraits(container, restoreData, csrfToken);
    const search = container.querySelector('#statqCharacterSearch');
    search.placeholder = 'Character name, ID or metadata';
    search.addEventListener('input', () => {
      const query = search.value.trim().toLowerCase();
      container.querySelectorAll('.statq-character-card').forEach(card => { card.hidden = !card.dataset.search.includes(query); });
    });
    addMetadataToCardSearch(container, '.statq-character-card');
    return { characters: cards.length, stats: rows.length, points: totalPoints, max: totalMax };
  }

  window.codexRemodRenderPlan = renderPlan;
  window.codexRemodRenderStatq = renderStatq;
  window.codexRemodExtractPlan = extractPlanFromZip;
  window.codexRemodExtractArchiveText = extractArchiveText;
  window.codexRemodExtractArchiveFile = extractArchiveFile;
  window.codexRemodRenderDeleteMods = renderDeleteMods;
})();