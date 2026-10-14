<?php
ini_set('session.gc_maxlifetime', 3600 * 24 * 7);
session_set_cookie_params([
    'lifetime' => 3600 * 24 * 7,
    'path' => '/',
    'secure' => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
    'httponly' => true,
    'samesite' => 'Lax',
]);
session_start();

if (empty($_SESSION['user_id'])) {
    $return = '/codexremod.php';
    header('Location: init-oauth.php?return=' . rawurlencode($return));
    exit();
}
if (empty($_SESSION['codex_remod_csrf'])) {
    $_SESSION['codex_remod_csrf'] = bin2hex(random_bytes(32));
}
$csrf = $_SESSION['codex_remod_csrf'];
$hasJob = isset($_SESSION['codex_remod_job']) && is_array($_SESSION['codex_remod_job']);
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Codex remod - GuiOn bot</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="basic.css">
    <link rel="stylesheet" href="navbar.css">
    <link rel="stylesheet" href="main.1.008.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
    <style>
        .remod-wrap { max-width: 900px; margin: 28px auto; padding: 0 14px 36px; }
        .remod-panel { background: #fff; border-radius: 8px; padding: 24px; margin: 18px 0; box-shadow: 0 2px 8px rgba(0,0,0,.10); }
        .remod-panel h2 { margin-top: 0; }
        .remod-file { display: block; width: 100%; box-sizing: border-box; margin: 10px 0 18px; padding: 14px; border: 2px dashed #aab0bf; border-radius: 6px; background: #fafbfc; }
        .remod-button { border: 0; border-radius: 5px; padding: 11px 17px; background: #6c4bd2; color: white; cursor: pointer; font-size: 15px; margin: 5px 8px 5px 0; }
        .remod-button:hover { background: #5536b7; }
        .remod-button:disabled { opacity: .55; cursor: wait; }
        .remod-button.secondary { background: #50586b; }
        .remod-help { color: #626979; font-size: 14px; line-height: 1.5; }
        .remod-status { display: none; margin-top: 20px; padding: 15px; border-radius: 6px; background: #f2f0fa; }
        .remod-status.error { display: block; color: #8b1d1d; background: #fff0f0; }
        .remod-status.visible { display: block; }
        .remod-progress { width: 100%; height: 18px; margin: 12px 0; }
        .remod-progress-text { font-weight: 600; }
        .remod-options { display: grid; grid-template-columns: repeat(auto-fit,minmax(190px,1fr)); gap: 14px; margin: 20px 0; }
        .remod-options label { display: block; font-size: 14px; font-weight: 600; margin-bottom: 5px; }
        .remod-options select, .remod-options input { width: 100%; box-sizing: border-box; padding: 9px; border: 1px solid #c7cbd4; border-radius: 4px; background: white; }
        .remod-option-check { display: flex; align-items: center; gap: 8px; margin: 14px 0; }
        .remod-option-check input { width: auto; }
        .remod-mode { display:flex; flex-wrap:wrap; gap:16px; margin:16px 0; }
        .remod-mode label { display:flex; align-items:center; gap:7px; font-weight:600; }
        .remod-mode label { padding:10px 14px; border:2px solid #cbd0d8; border-radius:7px; background:#f5f6f8; color:#343a46; cursor:pointer; transition:background .15s,border-color .15s,color .15s; }
        .remod-mode label.selected { border-color:#d97706; background:#fff0d6; color:#873b08; box-shadow:0 0 0 1px #d97706; }
        .remod-mode label input { accent-color:#b45309; }
        .remod-mode input { width:auto; }
        .remod-target-picker { display:grid; grid-template-columns:minmax(0,1fr) minmax(12rem,2fr) auto; gap:8px; align-items:end; margin:12px 0 18px; }
        .remod-target-picker label { display:block; font-weight:600; font-size:14px; margin-bottom:5px; }
        .remod-target-picker input,.remod-target-picker select { width:100%; box-sizing:border-box; padding:9px; border:1px solid #c7cbd4; border-radius:4px; background:white; }
        .remod-target-list { display:grid; gap:12px; margin:14px 0; }
        .remod-target-card { border:1px solid #d9dce4; border-radius:7px; padding:14px; background:#fff; }
        .remod-target-head { display:flex; align-items:center; gap:10px; margin-bottom:12px; }
        .remod-target-head img { width:42px; height:42px; border-radius:50%; object-fit:cover; }
        .remod-target-head strong { flex:1; overflow-wrap:anywhere; }
        .remod-target-stats { display:grid; gap:7px; }
        .remod-target-stat { display:grid; grid-template-columns:minmax(0,1.2fr) minmax(7rem,1fr) auto; gap:8px; align-items:center; }
        .remod-target-card select,.remod-target-card input { min-width:0; width:100%; box-sizing:border-box; padding:8px; border:1px solid #c7cbd4; border-radius:4px; background:white; }
        .remod-target-card details { margin-top:12px; border-top:1px solid #eceef3; padding-top:10px; }
        .remod-target-card summary { cursor:pointer; font-weight:600; }
        .remod-target-extra { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:10px; margin-top:10px; }
        .remod-target-extra label { display:block; font-size:13px; font-weight:600; margin-bottom:5px; }
        .remod-target-note { color:#626979; font-size:13px; margin:8px 0; }
        @media (max-width:650px) { .remod-target-picker { grid-template-columns:1fr; } }
        .remod-options-toggle { margin:0 0 10px; }
        .remod-options[hidden], .remod-option-group[hidden] { display:none !important; }
        .remod-option-group { grid-column:1 / -1; display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; }
        .remod-option-group > .remod-option-check { grid-column:1 / -1; }
        #remodFileName { margin: 8px 0; overflow-wrap: anywhere; }
        .remod-results { max-width: 1200px; margin: 24px auto 40px; padding: 0 14px; }
        .remod-plan-toolbar { display:grid; grid-template-columns:minmax(12rem,2fr) minmax(10rem,1fr) minmax(10rem,1fr); gap:8px; align-items:center; margin:14px 0; }
        .remod-plan-count { grid-column:1 / -1; }
        .remod-plan-toolbar input,.remod-plan-toolbar select { width:100%; box-sizing:border-box; padding:9px; border:1px solid #c7cbd4; border-radius:4px; background:white; }
        .remod-plan-list { display:grid; gap:6px; }
        .remod-plan-card { border:1px solid #d9dce4; border-radius:7px; overflow:hidden; background:#fff; }
        .remod-plan-card[hidden] { display:none; }
        .remod-plan-summary { list-style:none; display:grid; grid-template-columns:28px 44px minmax(0,1fr) auto 16px; gap:10px; align-items:center; padding:10px 12px; cursor:pointer; }
        .remod-plan-summary::-webkit-details-marker { display:none; } .remod-plan-summary:hover { background:#f8f8fb; }
        .remod-rank { color:#7a7f8b; text-align:center; font-size:13px; }
        .remod-portrait { width:42px; height:42px; object-fit:cover; border-radius:50%; }
        .remod-initials { display:grid; place-items:center; background:#e8eaf0; color:#384052; font-weight:700; }
        .remod-identity { display:grid; gap:3px; min-width:0; } .remod-identity strong { overflow-wrap:anywhere; }
        .remod-identity small,.remod-muted { color:#697080; font-size:12px; } .remod-stat-summary { white-space:normal; }
        .remod-gain { font-size:13px; font-weight:700; white-space:nowrap; } .remod-chevron { color:#697080; }
        .remod-plan-card[open] > .remod-plan-summary .remod-chevron { transform:rotate(180deg); }
        .remod-plan-expanded { border-top:1px solid #e2e5eb; padding:10px 14px 16px; } .remod-plan-expanded h4 { margin:16px 0 7px; }
        .remod-plan-meta { display:flex; flex-wrap:wrap; gap:8px 20px; font-size:13px; } .remod-table-wrap { width:100%; overflow-x:auto; }
        .remod-plan-table { width:100%; border-collapse:collapse; font-size:13px; } .remod-plan-table th,.remod-plan-table td { text-align:left; vertical-align:top; padding:8px; border-bottom:1px solid #e5e7eb; }
        .remod-plan-table thead th { color:#626979; white-space:nowrap; } .remod-plan-table tbody th { white-space:nowrap; }
        .remod-positive { color:#16803c; } .remod-negative { color:#b42318; }
        .remod-decision { display:inline-block; padding:2px 7px; border-radius:10px; font-weight:700; font-size:12px; }
        .remod-decision.replace { background:#fff0e8; color:#a43f0b; } .remod-decision.keep { background:#eaf7ee; color:#176b35; }
        .remod-alternatives,.remod-technical { margin-top:12px; } .remod-alternatives > summary,.remod-technical > summary { cursor:pointer; padding:6px 0; font-weight:600; }
        .remod-technical pre { max-height:400px; overflow:auto; background:#f5f6f8; padding:10px; font-size:12px; }
        @media (max-width:650px) { .remod-panel { padding:16px; } .remod-wrap { margin-top:16px; } .remod-plan-toolbar { grid-template-columns:1fr 1fr; } .remod-plan-toolbar .remod-plan-search { grid-column:1 / -1; } .remod-plan-summary { grid-template-columns:20px 36px minmax(0,1fr) auto; gap:6px; padding:8px; } .remod-portrait { width:34px; height:34px; } .remod-gain { grid-column:3; grid-row:2; justify-self:start; } .remod-chevron { grid-column:4; grid-row:1 / span 2; } .remod-identity { grid-column:3; } .remod-plan-table { min-width:560px; } }
    </style>
</head>
<body>
<div class="site-container">
<div class="site-pusher">
    <?php include 'navbar.php'; ?>
    <div class="site-content">
        <main class="container remod-wrap">
            <h2>Codex remod</h2>
            <p>Upload your SWGOH <code>restoreMyProgress.json</code> file to calculate a remod plan. The calculation runs on the Codex Remod server, so you can leave this page open while it works.</p>
            <section class="remod-panel">
                <form id="remodForm">
                    <input type="hidden" name="csrf" value="<?php echo htmlspecialchars($csrf, ENT_QUOTES, 'UTF-8'); ?>">
                    <label for="remodFile"><strong>Select a restoreMyProgress.json file</strong></label>
                    <input class="remod-file" type="file" id="remodFile" name="file" accept=".json,application/json" required>
                    <div id="remodFileName" class="remod-help">JSON file, maximum size 30 MB.</div>
                    <fieldset class="remod-mode"><legend><strong>Remod type</strong></legend>
                        <label><input type="radio" name="mode" value="full" checked> Full remod</label>
                        <label><input type="radio" name="mode" value="light"> Light remod (target stats)</label>
                    </fieldset>
                    <div id="remodTargetsWrap" hidden>
                        <strong>Light-remod targets</strong>
                        <p class="remod-help">Choose characters from your restoreMyProgress file. For each character, add at least one target stat and its final in-game value. Sets and primaries are optional.</p>
                        <div class="remod-target-picker">
                            <div><label for="remodHeroSearch">Search characters</label><input type="search" id="remodHeroSearch" placeholder="Name or character ID" autocomplete="off"></div>
                            <div><label for="remodHeroSelect">Characters in your roster</label><select id="remodHeroSelect"><option value="">Select a roster file first</option></select></div>
                            <button class="remod-button secondary" type="button" id="remodAddHero" disabled>Add character</button>
                        </div>
                        <div id="remodRosterNote" class="remod-target-note">Select a restoreMyProgress.json file to load your characters.</div>
                        <div id="remodTargetList" class="remod-target-list"></div>
                        <div id="remodTargetCount" class="remod-help">0 / 40 characters added.</div>
                    </div>
                    <button class="remod-button secondary remod-options-toggle" id="remodOptionsToggle" type="button" aria-expanded="false">Show options</button>
                    <div class="remod-options" id="remodOptions" hidden>
                      <div class="remod-option-group" id="remodFullOptions">
                        <div>
                            <label for="remodTarget">Target level</label>
                            <select id="remodTarget" name="cible">
                                <option value="moyenne" selected>Average (Kyber 1)</option>
                                <option value="mediane">Median (Kyber 1)</option>
                                <option value="p75">75th percentile (Kyber 1)</option>
                            </select>
                        </div>
                        <div>
                            <label for="remodTime">Time limit per hero (seconds)</label>
                            <select id="remodTime" name="time_limit"><option value="2">2</option><option value="4">4</option><option value="6">6</option><option value="8" selected>8</option><option value="10">10</option><option value="12">12</option><option value="15">15</option></select>
                        </div>
                        <div>
                            <label for="remodMaxHeroes">Maximum heroes (0 = all)</label>
                            <input id="remodMaxHeroes" name="max_heroes" type="number" min="0" max="500" value="0" step="1">
                        </div>
                        <div>
                            <label for="remodSpeed">Remove-speed threshold</label>
                            <input id="remodSpeed" name="suppr_vitesse_max" type="number" min="0" max="30" value="10" step="1">
                        </div>
                        <div>
                            <label for="remodDepartStats">depart_stats (optional, 0–9999)</label>
                            <input id="remodDepartStats" name="depart_stats" type="number" min="0" max="9999" step="1" placeholder="Leave empty to omit">
                        </div>
                        <label class="remod-option-check"><input type="checkbox" id="remodFullSansBot" name="sans_bot" value="true"> Manual remod only (do not generate <code>progress_out.json</code>)</label>
                      </div>
                      <div class="remod-option-group" id="remodLightOptions" hidden>
                        <div><label for="remodLang">Language</label><select id="remodLang" name="lang" disabled><option value="fr" selected>Français</option><option value="en">English</option></select></div>
                        <div><label for="remodLightTime">Time limit per hero (seconds)</label><select id="remodLightTime" name="time_limit_light" disabled><option value="2">2</option><option value="4">4</option><option value="6">6</option><option value="8" selected>8</option><option value="10">10</option><option value="12">12</option><option value="15">15</option></select></div>
                        <label class="remod-option-check"><input type="checkbox" id="remodSansBot" name="sans_bot_light" value="true" disabled> Manual remod only (do not generate <code>progress_out.json</code>)</label>
                        <label class="remod-option-check"><input type="checkbox" id="remodSansEmprunt" name="sans_emprunt" value="true" disabled> Do not borrow mods from heroes outside the target list</label>
                      </div>
                    </div>
                    <button class="remod-button" id="remodSubmit" type="submit">Upload and start remod</button>
                </form>
                <div id="remodStatus" class="remod-status" role="status" aria-live="polite"></div>
                <div id="remodProgressWrap" hidden>
                    <progress class="remod-progress" id="remodProgress" max="100" value="0"></progress>
                    <div class="remod-progress-text" id="remodProgressText"></div>
                </div>
                <div id="remodActions" hidden>
                    <button class="remod-button" id="remodShowResults" type="button">Show results</button>
                    <button class="remod-button secondary" id="remodForget" type="button">Clear this result</button>
                </div>
            </section>

            <p class="remod-help">Your file is sent securely to the remod service for processing. It is not stored by this website. Result files contain your roster and mods; keep the downloaded archive private.</p>
            <section id="remodResults" class="remod-results" hidden>
                <h2>Remod results</h2>
                <p class="remod-help">Click a character row to expand its StatQ, stat changes and mod recommendations.</p>
                <div id="remodResultDownloads" hidden>
                    <button class="remod-button" id="remodDownloadZip" type="button">Download results.zip</button>
                    <button class="remod-button secondary" id="remodDownloadPlan" type="button">Download plan.json</button>
                </div>
                <div id="remodPlan"></div>
            </section>
        </main>
    </div>
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>
</div>
</div>
<script src="codexremod_results.js"></script>
<script>
(function () {
    'use strict';
    const form = document.getElementById('remodForm');
    const fileInput = document.getElementById('remodFile');
    const fileName = document.getElementById('remodFileName');
    const heroSearch = document.getElementById('remodHeroSearch');
    const heroSelect = document.getElementById('remodHeroSelect');
    const addHeroButton = document.getElementById('remodAddHero');
    const rosterNote = document.getElementById('remodRosterNote');
    const targetList = document.getElementById('remodTargetList');
    const targetCount = document.getElementById('remodTargetCount');
    let rosterCharacters = [];
    let targetHeroes = [];
    const modeInputs = Array.from(form.querySelectorAll('input[name="mode"]'));
    const optionsToggle = document.getElementById('remodOptionsToggle');
    const optionsPanel = document.getElementById('remodOptions');
    const fullOptions = document.getElementById('remodFullOptions');
    const lightOptions = document.getElementById('remodLightOptions');
    const submitButton = document.getElementById('remodSubmit');
    const statusBox = document.getElementById('remodStatus');
    const progressWrap = document.getElementById('remodProgressWrap');
    const progressBar = document.getElementById('remodProgress');
    const progressText = document.getElementById('remodProgressText');
    const actions = document.getElementById('remodActions');
    const showResultsButton = document.getElementById('remodShowResults');
    const downloadButtons = document.getElementById('remodResultDownloads');
    const downloadZipButton = document.getElementById('remodDownloadZip');
    const downloadPlanButton = document.getElementById('remodDownloadPlan');
    const forgetButton = document.getElementById('remodForget');
    const resultsSection = document.getElementById('remodResults');
    const resultsContainer = document.getElementById('remodPlan');
    let resultsZipBlob = null;
    let planJsonText = null;
    const csrf = form.elements.csrf.value;
    let pollTimer = null;
    let busy = false;
    let optionsExpanded = false;

    function selectedMode() { return modeInputs.find(input => input.checked).value; }
    function setGroupEnabled(group, enabled) { group.querySelectorAll('input, select, textarea').forEach(control => { control.disabled = !enabled; }); }
    function updateMode() {
        const light = selectedMode() === 'light';
        modeInputs.forEach(input => input.closest('label').classList.toggle('selected', input.checked));
        document.getElementById('remodTargetsWrap').hidden = !light;
        heroSearch.disabled = !light || !rosterCharacters.length;
        heroSelect.disabled = !light || !rosterCharacters.length;
        addHeroButton.disabled = !light || !heroSelect.value || targetHeroes.length >= 40;
        fullOptions.hidden = light;
        lightOptions.hidden = !light;
        setGroupEnabled(fullOptions, !light);
        setGroupEnabled(lightOptions, light);
        optionsPanel.hidden = !optionsExpanded;
        optionsToggle.textContent = optionsExpanded ? 'Hide options' : 'Show options';
        optionsToggle.setAttribute('aria-expanded', optionsExpanded ? 'true' : 'false');
    }

    const targetStats = [
        ['speed','Speed / Vitesse'], ['health','Health / Santé'], ['protection','Protection'],
        ['armor','Armor % / Armure %'], ['resistance','Resistance % / Résistance %'],
        ['crit_damage','Critical damage % / Dégâts critiques %'], ['potency','Potency % / Pouvoir %'],
        ['tenacity','Tenacity % / Ténacité %'], ['physical_damage','Physical damage / Dégâts physiques'],
        ['special_damage','Special damage / Dégâts spéciaux'], ['offense','Offense / Attaque'],
        ['crit_chance','Critical chance from mods / Chance critique apportée par les mods']
    ];
    const targetSets = [['health','Health'],['offense','Offense'],['defense','Defense'],['speed','Speed'],['critchance','Critical chance'],['critdamage','Critical damage'],['potency','Potency'],['tenacity','Tenacity']];
    const targetPrimaries = {
        arrow:['Speed','Accuracy %','Critical Avoidance %','Defense %','Health %','Offense %','Protection %'],
        triangle:['Critical Chance %','Critical Damage %','Defense %','Health %','Offense %','Protection %'],
        circle:['Health %','Protection %'],
        cross:['Tenacity %','Potency %','Defense %','Health %','Offense %','Protection %']
    };
    function esc(value) { return String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
    function extractCharacters(data) {
        const roots = [data];
        if (data && data.profiles && typeof data.profiles === 'object') roots.push(...(Array.isArray(data.profiles) ? data.profiles : Object.values(data.profiles)));
        const found = new Map();
        for (const root of roots) {
            const chars = root && root.characters;
            if (!chars || typeof chars !== 'object') continue;
            const entries = Array.isArray(chars) ? chars.map(ch => [ch && (ch.baseId || ch.definitionId || ch.defId || ch.id), ch]) : Object.entries(chars);
            for (const [key, ch] of entries) {
                if (!key || !ch || typeof ch !== 'object') continue;
                const id = String(key);
                if (found.has(id.toUpperCase())) continue;
                const name = ch.displayName || ch.localizedName || ch.characterName || ch.name || id;
                found.set(id.toUpperCase(), {id, name:String(name), search:(id+' '+name).toLowerCase()});
            }
        }
        return [...found.values()].sort((a,b) => a.name.localeCompare(b.name, undefined, {sensitivity:'base'}));
    }
    function refreshCharacterSelect() {
        const query = heroSearch.value.trim().toLowerCase();
        const added = new Set(targetHeroes.map(h => h.id.toUpperCase()));
        const available = rosterCharacters.filter(h => !added.has(h.id.toUpperCase()) && (!query || h.search.includes(query)));
        const previous = heroSelect.value;
        heroSelect.innerHTML = '<option value="">Choose a character…</option>' + available.map(h => '<option value="'+esc(h.id)+'">'+esc(h.name)+(h.name.toUpperCase()===h.id.toUpperCase()?'':' ('+esc(h.id)+')')+'</option>').join('');
        if (available.some(h => h.id === previous)) heroSelect.value = previous;
        addHeroButton.disabled = selectedMode() !== 'light' || !heroSelect.value || targetHeroes.length >= 40;
    }
    function renderTargets() {
        targetList.innerHTML = '';
        targetHeroes.forEach((hero, hi) => {
            const card = document.createElement('section');
            card.className = 'remod-target-card';
            const statsHtml = hero.stats.map((item, si) => '<div class="remod-target-stat" data-stat-index="'+si+'"><select aria-label="Target stat"><option value="">Choose stat…</option>'+targetStats.map(([key,label])=>'<option value="'+key+'"'+(item.stat===key?' selected':'')+'>'+label+'</option>').join('')+'</select><input type="number" min="0.000001" step="any" aria-label="Final stat value" placeholder="Final value" value="'+esc(item.value)+'"><button type="button" class="remod-button secondary" data-remove-stat="'+si+'" aria-label="Remove stat">×</button></div>').join('');
            const setsHtml = targetSets.map(([key,label])=>'<div><label>'+label+' sets</label><select data-set="'+key+'"><option value="0">No preference</option>'+[1,2,3].map(n=>'<option value="'+n+'"'+(hero.sets[key]===n?' selected':'')+'>'+n+'</option>').join('')+'</select></div>').join('');
            const primaryHtml = Object.entries(targetPrimaries).map(([slot,opts])=>'<div><label>'+slot.charAt(0).toUpperCase()+slot.slice(1)+' primary</label><select data-primary="'+slot+'"><option value="">No preference</option>'+opts.map(v=>'<option value="'+esc(v)+'"'+(hero.primaires[slot]===v?' selected':'')+'>'+esc(v)+'</option>').join('')+'</select></div>').join('');
            const portraitId = hero.id.replace(/[^A-Za-z0-9_-]/g,'');
            card.innerHTML = '<div class="remod-target-head"><img src="IMAGES/CHARACTERS/'+encodeURIComponent(portraitId)+'.png" alt="" onerror="this.hidden=true"><strong>'+esc(hero.name)+'<br><small>'+esc(hero.id)+'</small></strong><button type="button" class="remod-button secondary" data-remove-hero>Remove</button></div><div class="remod-target-stats">'+statsHtml+'</div><button type="button" class="remod-button secondary" data-add-stat '+(hero.stats.length>=12?'disabled':'')+'>Add stat</button><details><summary>Mod sets (optional)</summary><div class="remod-target-extra">'+setsHtml+'</div></details><details><summary>Mod primaries (optional)</summary><div class="remod-target-extra">'+primaryHtml+'</div></details>';
            card.querySelector('[data-remove-hero]').addEventListener('click',()=>{targetHeroes.splice(hi,1);renderTargets();});
            card.querySelector('[data-add-stat]').addEventListener('click',()=>{if(hero.stats.length<12){hero.stats.push({stat:'',value:''});renderTargets();}});
            card.querySelectorAll('[data-remove-stat]').forEach(btn=>btn.addEventListener('click',()=>{if(hero.stats.length>1){hero.stats.splice(Number(btn.dataset.removeStat),1);renderTargets();}}));
            card.querySelectorAll('.remod-target-stat').forEach((row,si)=>{row.querySelector('select').addEventListener('change',e=>hero.stats[si].stat=e.target.value);row.querySelector('input').addEventListener('input',e=>hero.stats[si].value=e.target.value);});
            card.querySelectorAll('[data-set]').forEach(sel=>sel.addEventListener('change',e=>{const k=e.target.dataset.set,v=Number(e.target.value);if(v)hero.sets[k]=v;else delete hero.sets[k];}));
            card.querySelectorAll('[data-primary]').forEach(sel=>sel.addEventListener('change',e=>{const k=e.target.dataset.primary,v=e.target.value;if(v)hero.primaires[k]=v;else delete hero.primaires[k];}));
            targetList.appendChild(card);
        });
        targetCount.textContent=targetHeroes.length+' / 40 characters added.';
        refreshCharacterSelect();
    }
    function makeTargetsJson() {
        if(targetHeroes.length<1||targetHeroes.length>40)throw new Error('Add between 1 and 40 characters for light remod.');
        const heroes=targetHeroes.map(hero=>{
            const stats={};
            hero.stats.forEach(item=>{const value=Number(item.value);if(!item.stat||!Number.isFinite(value)||value<=0)throw new Error('Each character needs at least one selected stat with a positive final value.');if(Object.prototype.hasOwnProperty.call(stats,item.stat))throw new Error('Choose each stat only once per character.');stats[item.stat]=value;});
            const output={id:hero.id,stats};
            if(Object.keys(hero.sets).length)output.sets=hero.sets;
            if(Object.keys(hero.primaires).length)output.primaires=hero.primaires;
            return output;
        });
        return JSON.stringify({heroes},null,2);
    }
    function showMessage(message, isError) {
        statusBox.textContent = message;
        statusBox.className = 'remod-status visible' + (isError ? ' error' : '');
    }
    function hideMessage() {
        statusBox.textContent = '';
        statusBox.className = 'remod-status';
    }
    function setBusy(value) {
        busy = value;
        submitButton.disabled = value;
        showResultsButton.disabled = value;
        downloadZipButton.disabled = value;
        downloadPlanButton.disabled = value;
        forgetButton.disabled = value;
    }
    async function request(action, extra) {
        const data = new FormData();
        data.append('action', action);
        data.append('csrf', csrf);
        Object.keys(extra || {}).forEach(function (key) { data.append(key, extra[key]); });
        const response = await fetch('codexcon.php', { method: 'POST', body: data, credentials: 'same-origin' });
        const type = response.headers.get('content-type') || '';
        if (!type.includes('application/json')) {
            if (!response.ok) throw new Error('Request failed (HTTP ' + response.status + ').');
            throw new Error('Unexpected response from the server.');
        }
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || 'Request failed (HTTP ' + response.status + ').');
        return body;
    }
    function stopPolling() {
        if (pollTimer !== null) window.clearTimeout(pollTimer);
        pollTimer = null;
    }
    async function pollStatus() {
        try {
            const state = await request('status');
            const name = state.status || 'unknown';
            if (name === 'queued') {
                const position = Number(state.queue_position);
                showMessage('Your remod is queued' + (Number.isFinite(position) && position > 0 ? ' (position ' + position + ')' : '') + '. Waiting for a calculation slot…');
                progressWrap.hidden = false;
                progressBar.removeAttribute('value');
                progressText.textContent = 'Waiting in queue';
                pollTimer = window.setTimeout(pollStatus, 4000);
            } else if (name === 'running') {
                const progress = state.progress || {};
                const pct = Math.max(0, Math.min(100, Number(progress.pct) || 0));
                progressWrap.hidden = false;
                progressBar.value = pct;
                progressText.textContent = (Number(progress.done) || 0) + ' / ' + (Number(progress.total) || 0) + ' heroes (' + Math.round(pct) + '%)';
                showMessage('Remod calculation in progress…');
                pollTimer = window.setTimeout(pollStatus, 4000);
            } else if (name === 'done') {
                setBusy(false);
                progressWrap.hidden = false;
                progressBar.value = 100;
                progressText.textContent = '100% — calculation complete';
                actions.hidden = false;
                showResultsButton.hidden = false;
                showMessage('Remod complete. Click Show results to display the character cards.');
            } else if (name === 'error') {
                setBusy(false);
                progressWrap.hidden = true;
                actions.hidden = false;
                showResultsButton.hidden = true;
                showMessage('The remod calculation failed: ' + (state.error || 'No further details were provided.'), true);
            } else {
                throw new Error('Unknown remod status: ' + name);
            }
        } catch (error) {
            setBusy(false);
            showMessage(error.message || 'Unable to retrieve the job status.', true);
        }
    }
    optionsToggle.addEventListener('click', function () { optionsExpanded = !optionsExpanded; updateMode(); });
    modeInputs.forEach(input => input.addEventListener('change', function () { updateMode(); hideMessage(); }));
    heroSearch.addEventListener('input', refreshCharacterSelect);
    heroSelect.addEventListener('change', refreshCharacterSelect);
    addHeroButton.addEventListener('click', function () {
        const character=rosterCharacters.find(h=>h.id===heroSelect.value);
        if(!character||targetHeroes.length>=40)return;
        targetHeroes.push({id:character.id,name:character.name,stats:[{stat:'',value:''}],sets:{},primaires:{}});
        heroSearch.value='';
        renderTargets();
    });
    fileInput.addEventListener('change', function () {
        const file = fileInput.files && fileInput.files[0];
        fileName.textContent = file ? file.name + ' (' + (file.size / (1024 * 1024)).toFixed(2) + ' MB)' : 'JSON file, maximum size 30 MB.';
        if (file && (file.size > 30 * 1024 * 1024 || !file.name.toLowerCase().endsWith('.json'))) {
            showMessage('Choose a .json file no larger than 30 MB.', true);
            submitButton.disabled = true;
        } else {
            hideMessage();
            submitButton.disabled = busy;
            rosterCharacters = [];
            targetHeroes = [];
            renderTargets();
            if (file) {
                try {
                    const parsed = JSON.parse(await file.text());
                    rosterCharacters = extractCharacters(parsed);
                    rosterNote.textContent = rosterCharacters.length ? 'Loaded '+rosterCharacters.length+' characters from this roster.' : 'No characters found. Make sure this is a restoreMyProgress.json file.';
                    refreshCharacterSelect();
                    if (!rosterCharacters.length && selectedMode()==='light') showMessage(rosterNote.textContent,true);
                    else if (!busy) showMessage('File selected. Configure the options below, then click Upload and start remod.');
                } catch (error) {
                    rosterNote.textContent='Could not parse this JSON file.';
                    if(selectedMode()==='light')showMessage('Could not parse restoreMyProgress.json to list characters.',true);
                }
            } else rosterNote.textContent='Select a restoreMyProgress.json file to load your characters.';
        }
    });
    form.addEventListener('submit', async function (event) {
        event.preventDefault();
        if (busy) return;
        const file = fileInput.files && fileInput.files[0];
        if (!file) { showMessage('Please select a restoreMyProgress.json file.', true); return; }
        if (!file.name.toLowerCase().endsWith('.json') || file.size > 30 * 1024 * 1024) {
            showMessage('Choose a .json file no larger than 30 MB.', true); return;
        }
        const light = selectedMode() === 'light';
        let targetsJson = null;
        if (light) {
            if (!rosterCharacters.length) { showMessage('Select a valid restoreMyProgress.json file to load the character list.', true); return; }
            try { targetsJson = makeTargetsJson(); }
            catch (error) { showMessage(error.message || 'Check your target characters and stats.', true); return; }
            if (new Blob([targetsJson]).size > 256 * 1024) { showMessage('Generated targets exceed the 256 KB limit.', true); return; }
        }
        stopPolling();
        actions.hidden = true;
        resultsSection.hidden = true;
        downloadButtons.hidden = true;
        resultsZipBlob = null;
        planJsonText = null;
        progressWrap.hidden = true;
        hideMessage();
        setBusy(true);
        showMessage('Uploading your file and creating the remod job…');
        try {
            const data = new FormData(form);
            data.set('mode', selectedMode());
            if (light) {
                ['cible', 'max_heroes', 'suppr_vitesse_max', 'depart_stats'].forEach(key => data.delete(key));
                data.delete('sans_bot');
                data.delete('time_limit');
                data.set('cibles', new Blob([targetsJson], {type:'application/json'}), 'cibles.json');
                data.set('lang', document.getElementById('remodLang').value);
                data.set('time_limit', document.getElementById('remodLightTime').value);
                data.set('sans_bot', document.getElementById('remodSansBot').checked ? 'true' : 'false');
                data.set('sans_emprunt', document.getElementById('remodSansEmprunt').checked ? 'true' : 'false');
            } else {
                data.delete('cibles');
                data.delete('lang');
                data.delete('sans_emprunt');
                const departStats = document.getElementById('remodDepartStats').value.trim();
                if (departStats === '') data.delete('depart_stats');
                else if (!/^\d+$/.test(departStats) || Number(departStats) > 9999) throw new Error('depart_stats must be an integer between 0 and 9999.');
            }
            data.set('action', 'submit');
            const response = await fetch('codexcon.php', { method: 'POST', body: data, credentials: 'same-origin' });
            const body = await response.json();
            if (!response.ok) throw new Error(body.error || 'Unable to start remod.');
            progressWrap.hidden = false;
            progressBar.removeAttribute('value');
            progressText.textContent = 'Waiting for the first status update…';
            showMessage('Job accepted by the remod server. Checking progress every 4 seconds.');
            pollTimer = window.setTimeout(pollStatus, 1000);
        } catch (error) {
            setBusy(false);
            showMessage(error.message || 'Unable to start remod.', true);
        }
    });
    showResultsButton.addEventListener('click', async function () {
        if (busy) return;
        setBusy(true);
        showMessage('Loading the completed plan from the remod service…');
        try {
            const data = new FormData();
            data.append('action', 'download');
            data.append('csrf', csrf);
            const response = await fetch('codexcon.php', { method: 'POST', body: data, credentials: 'same-origin' });
            if (!response.ok) {
                const body = await response.json().catch(function () { return {}; });
                throw new Error(body.error || 'Unable to retrieve results.');
            }
            resultsZipBlob = await response.blob();
            const extracted = await window.codexRemodExtractPlan(resultsZipBlob);
            planJsonText = extracted.text;
            const count = window.codexRemodRenderPlan(resultsContainer, extracted.data);
            resultsSection.hidden = false;
            downloadButtons.hidden = false;
            actions.hidden = true;
            progressWrap.hidden = true;
            showMessage('Loaded ' + count + ' character plans. Choose whether to download the full ZIP or only plan.json.');
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            fileInput.value = '';
            fileName.textContent = 'JSON file, maximum size 30 MB.';
        } catch (error) {
            showMessage(error.message || 'Unable to show remod results.', true);
        } finally {
            setBusy(false);
        }
    });
    function downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(function () { URL.revokeObjectURL(url); }, 30000);
    }
    downloadZipButton.addEventListener('click', function () {
        if (resultsZipBlob) downloadBlob(resultsZipBlob, 'codex-remod-results.zip');
    });
    downloadPlanButton.addEventListener('click', function () {
        if (planJsonText !== null) downloadBlob(new Blob([planJsonText], { type: 'application/json;charset=utf-8' }), 'plan.json');
    });
    forgetButton.addEventListener('click', async function () {
        if (busy) return;
        if (!window.confirm('Clear this remod job and delete its remote results if they are ready?')) return;
        setBusy(true);
        stopPolling();
        try {
            await request('forget');
            actions.hidden = true;
            showResultsButton.hidden = false;
            progressWrap.hidden = true;
            showMessage('Remod job cleared.');
            setBusy(false);
            submitButton.disabled = false;
        } catch (error) {
            setBusy(false);
            showMessage(error.message || 'Unable to clear the job.', true);
        }
    });

    updateMode();
    <?php if ($hasJob): ?>
    setBusy(true);
    showMessage('Restoring your remod job status…');
    pollTimer = window.setTimeout(pollStatus, 300);
    <?php endif; ?>
})();
</script>
</body>
</html>
