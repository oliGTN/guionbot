/* Browser-side renderer for Codex Remod plan.json inside results.zip. No build step required. */
(function () {
  'use strict';
  const SLOT_ORDER = ['square', 'arrow', 'diamond', 'triangle', 'circle', 'cross'];
  const SLOT_LABELS = { square: 'Square', arrow: 'Arrow', diamond: 'Diamond', triangle: 'Triangle', circle: 'Circle', cross: 'Cross' };
  const STAT_LABELS = { speed: 'Speed', protection: 'Protection', health: 'Health', potency: 'Potency', tenacity: 'Tenacity', critDmg: 'Critical Damage', critChance: 'Critical Chance', physDmg: 'Physical Damage', specDmg: 'Special Damage', '1': 'Health', '5': 'Speed', '6': 'Physical Damage', '7': 'Special Damage', '16': 'Critical Chance', '17': 'Tenacity', '18': 'Critical Damage', '28': 'Protection', '56': 'Potency' };

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
  function renderCard(row, index) {
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
    return '<details class="remod-plan-card" data-name="' + esc(String(name).toLowerCase()) + '" data-replacements="' + replacements + '" data-gain="' + (Number.isFinite(gain) ? gain : -999) + '" data-search="' + esc(search) + '">' +
      '<summary class="remod-plan-summary"><span class="remod-rank">' + (index + 1) + '</span>' +
      (portrait ? '<img class="remod-portrait" src="' + esc(portrait) + '" alt="" loading="lazy">' : '<span class="remod-portrait remod-initials">' + esc(String(name).split(/\s+/).map(w => w[0] || '').join('').slice(0, 2).toUpperCase()) + '</span>') +
      '<span class="remod-identity"><strong>' + esc(name) + '</strong><small>' + esc(base) + ' · ' + replacements + ' mod(s) to replace</small><small class="remod-stat-summary">' + esc(statSummary || 'Stat comparison unavailable') + '</small></span>' +
      '<span class="remod-gain ' + (gain > 0 ? 'remod-positive' : gain < 0 ? 'remod-negative' : '') + '">' + (Number.isFinite(gain) ? esc(signed(gain, 0) + ' StatQ') : 'StatQ —') + '</span><span class="remod-chevron">⌄</span></summary>' +
      '<div class="remod-plan-expanded"><div class="remod-plan-meta"><span><strong>StatQ:</strong> ' + esc(beforeQ == null ? '—' : beforeQ) + ' → ' + esc(afterQ == null ? '—' : afterQ) + ' / ' + esc(maxQ) + '</span><span><strong>Sets:</strong> ' + esc(setText || 'Not specified') + '</span><span><strong>Time:</strong> ' + esc(row.seconds == null ? '—' : num(row.seconds, 2) + ' s') + '</span></div>' +
      '<h4>Stat changes</h4><div class="remod-table-wrap"><table class="remod-plan-table"><thead><tr><th>Stat</th><th>Before</th><th>Projected after</th><th>Change</th><th>Target</th><th>Target %</th></tr></thead><tbody>' + (statRows || '<tr><td colspan="6">No stat details in this plan entry.</td></tr>') + '</tbody></table></div>' +
      '<h4>Mods</h4><div class="remod-table-wrap"><table class="remod-plan-table remod-mod-table"><tbody>' + modRows + '</tbody></table></div>' +
      (tierRows ? '<details class="remod-alternatives"><summary>Alternative plans (' + alternatives.length + ')</summary><div class="remod-table-wrap"><table class="remod-plan-table"><thead><tr><th>StatQ</th><th>Gain</th><th>Replacements</th><th>Sets</th></tr></thead><tbody>' + tierRows + '</tbody></table></div></details>' : '') +
      '<details class="remod-technical"><summary>Technical details</summary><pre>' + esc(JSON.stringify({ solver: row.solver, advice: row.advice }, null, 2)) + '</pre></details></div></details>';
  }

  function renderPlan(container, planData) {
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
    list.innerHTML = rows.map(renderCard).join('');
    container.replaceChildren(toolbar, list);
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
    search.addEventListener('input', update);
    filter.addEventListener('change', update);
    sort.addEventListener('change', update);
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


  async function extractArchiveText(blob, targetName) {
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
        return new TextDecoder().decode(payload);
      }
      offset += 46 + nameLength + extraLength + commentLength;
    }
    throw new Error('The results archive does not contain ' + targetName + '.');
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
        [mod.id, mod.modId, mod.mod_id, mod.uid, key].forEach(rawId => {
          const id = String(rawId == null ? '' : rawId).trim();
          if (id && !found.has(id)) found.set(id, mod);
        });
      });
    });
    return found;
  }

  function csvModIds(csvText) {
    const rows = parseCsv(csvText);
    const ids = [];
    rows.forEach((row, index) => {
      if (row.length < 2) return;
      const id = String(row[1] || '').trim();
      if (!id) return;
      if (index === 0 && /mod.?id|identifiant|(^id$)/i.test(id)) return;
      if (!ids.includes(id)) ids.push(id);
    });
    return ids;
  }

  function modDisplayEntries(mod) {
    const entries = [];
    const add = (label, value) => {
      if (value === undefined || value === null || value === '') return;
      if (typeof value === 'object') {
        if (Array.isArray(value)) {
          if (value.length && value.every(v => v === null || typeof v !== 'object')) entries.push([label, value.join(', ')]);
          else value.forEach((v, i) => add(label + ' ' + (i + 1), v));
        } else Object.entries(value).forEach(([key, nested]) => add(label ? label + ' · ' + key : key, nested));
      } else entries.push([label, String(value)]);
    };
    Object.entries(mod).forEach(([key, value]) => add(key, value));
    return entries;
  }

  function modField(mod, keys) {
    for (const key of keys) if (mod[key] !== undefined && mod[key] !== null && mod[key] !== '') return mod[key];
    return null;
  }

  function resolveCharacterPortraitId(restoreData, rawId) {
    const candidate = String(rawId == null ? '' : rawId).trim();
    if (!candidate) return '';
    const roots = [restoreData];
    if (restoreData && restoreData.profiles && typeof restoreData.profiles === 'object') {
      roots.push(...(Array.isArray(restoreData.profiles) ? restoreData.profiles : Object.values(restoreData.profiles)));
    }
    for (const root of roots) {
      const chars = root && root.characters;
      if (!chars || typeof chars !== 'object') continue;
      const entries = Array.isArray(chars) ? chars.map(ch => [ch && (ch.baseId || ch.definitionId || ch.defId || ch.id), ch]) : Object.entries(chars);
      for (const [key, ch] of entries) {
        if (!ch || typeof ch !== 'object') continue;
        const baseId = String(ch.baseId || ch.definitionId || ch.defId || key || '');
        if ([key, ch.id, ch.characterID, ch.characterId, ch.baseId, ch.definitionId, ch.defId].some(value => value != null && String(value) === candidate)) return baseId;
      }
    }
    return candidate;
  }

  function renderDeleteMods(container, csvText, restoreData) {
    const ids = csvModIds(csvText);
    const inventory = collectInventoryMods(restoreData);
    const matches = ids.map(id => ({ id, mod: inventory.get(id) })).filter(item => item.mod);
    const slotNames = { 2:'Square', 3:'Arrow', 4:'Diamond', 5:'Triangle', 6:'Circle', 7:'Cross', square:'Square', arrow:'Arrow', diamond:'Diamond', triangle:'Triangle', circle:'Circle', cross:'Cross' };
    const setNames = { 1:'Health', 2:'Offense', 3:'Defense', 4:'Speed', 5:'Critical Chance', 6:'Critical Damage', 7:'Potency', 8:'Tenacity', health:'Health', offense:'Offense', defense:'Defense', speed:'Speed', critchance:'Critical Chance', critdamage:'Critical Damage', potency:'Potency', tenacity:'Tenacity' };
    const stats = mod => {
      const primary = modField(mod, ['primaryStat','primary','primary_stat']);
      const secondary = modField(mod, ['secondaryStat','secondaryStats','secondary','secondary_stats']);
      const other = {};
      Object.entries(mod).forEach(([key,value]) => {
        if (/^(id|modid|mod_id|uid|slot|set|modset|mod_set|pips|dots|level|tier|characterid|character_id|character|owner|assignedto|assigned_to|primarystat|primary|primary_stat|secondarystat|secondarystats|secondary|secondary_stats)$/i.test(key)) return;
        other[key] = value;
      });
      const entries = [];
      if (primary !== null) entries.push(['Primary', primary]);
      if (secondary !== null) entries.push(['Secondary stats', secondary]);
      Object.entries(other).forEach(([key,value]) => entries.push([key,value]));
      return entries.map(([key,value]) => '<div><strong>'+esc(key)+':</strong> '+esc(typeof value === 'object' ? JSON.stringify(value) : String(value))+'</div>').join('');
    };
    container.replaceChildren();
    const toolbar = document.createElement('div');
    toolbar.className = 'remod-delete-toolbar';
    toolbar.innerHTML = '<strong>'+matches.length+' matching mods</strong><span class="remod-muted">'+(ids.length-matches.length)+' CSV IDs not found in the inventory</span><input type="search" aria-label="Search mods to delete" placeholder="Search mod, character, stat…">';
    const grid = document.createElement('div');
    grid.className = 'remod-delete-grid';
    grid.innerHTML = matches.map(({id,mod}) => {
      const slotRaw = modField(mod,['slot','slotId','slot_id']);
      const slot = String(slotRaw == null ? '' : slotRaw).toLowerCase();
      const slotNum = /^\d+$/.test(slot) ? Number(slot) : ({square:2,arrow:3,diamond:4,triangle:5,circle:6,cross:7}[slot] || 0);
      const setRaw = modField(mod,['set','modSet','mod_set','setId','set_id']);
      const setKey = String(setRaw == null ? '' : setRaw).toLowerCase();
      const setNum = /^\d+$/.test(setKey) ? Number(setKey) : 0;
      const pips = Number(modField(mod,['pips','dots','dotCount','dot_count']) || 5);
      const tier = Math.max(1,Math.min(5,Number(modField(mod,['tier','rarity','colorTier','color_tier']) || 1)));
      const shapeIndex = Math.max(0,Math.min(5,slotNum-2)) + (pips >= 6 ? 6 : 0);
      const iconIndex = Math.max(0,Math.min(7,(setNum || ({health:1,offense:2,defense:3,speed:4,critchance:5,critdamage:6,potency:7,tenacity:8}[setKey] || 1))-1));
      const charRaw = modField(mod,['characterID','characterId','character_id','defId','def_id','owner','assignedTo','assigned_to']);
      const characterRaw = charRaw && typeof charRaw === 'object' ? (charRaw.baseId || charRaw.defId || charRaw.id || '') : String(charRaw || '');
      const character = resolveCharacterPortraitId(restoreData, characterRaw);
      const level = modField(mod,['level','lvl']);
      const title = (setNames[setNum] || setNames[setKey] || 'Mod')+' · '+(slotNames[slotNum] || slotNames[slot] || 'Unknown slot');
      const detail = [pips+' dots',level != null ? 'Level '+level : '',modField(mod,['id','modId','mod_id','uid']) || id].filter(Boolean).join(' · ');
      const flat = modDisplayEntries(mod).map(([key,value])=>key+': '+(typeof value==='object'?JSON.stringify(value):String(value))).join(' ').toLowerCase();
      return '<article class="remod-delete-card" data-search="'+esc((title+' '+detail+' '+character+' '+flat).toLowerCase())+'" data-slot="'+slotNum+'"><div class="remod-delete-title">'+esc(title)+'</div><div class="remod-delete-meta">'+esc(detail)+'</div><div class="remod-delete-art" style="--shape-x:'+shapeIndex+';--shape-y:'+(tier-1)+';--icon-x:'+iconIndex+';--icon-y:'+(tier-1)+'">'+(character?'<img class="remod-delete-portrait" src="IMAGES/CHARACTERS/'+encodeURIComponent(character)+'.png" alt="" loading="lazy" onerror="this.hidden=true">':'')+'</div><div class="remod-delete-stats">'+stats(mod)+'</div></article>';
    }).join('');
    const search = toolbar.querySelector('input');
    search.addEventListener('input', () => {
      const query = search.value.trim().toLowerCase();
      grid.querySelectorAll('.remod-delete-card').forEach(card => { card.hidden = !card.dataset.search.includes(query); });
    });
    container.append(toolbar,grid);
    return matches.length;
  }

  window.codexRemodRenderPlan = renderPlan;
  window.codexRemodExtractPlan = extractPlanFromZip;
  window.codexRemodExtractArchiveText = extractArchiveText;
  window.codexRemodRenderDeleteMods = renderDeleteMods;
})();