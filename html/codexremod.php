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
                    <div class="remod-options">
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
                            <select id="remodTime" name="time_limit">
                                <option value="2">2</option><option value="4">4</option><option value="6">6</option>
                                <option value="8" selected>8</option><option value="10">10</option><option value="12">12</option><option value="15">15</option>
                            </select>
                        </div>
                        <div>
                            <label for="remodMaxHeroes">Maximum heroes (0 = all)</label>
                            <input id="remodMaxHeroes" name="max_heroes" type="number" min="0" max="500" value="0" step="1">
                        </div>
                        <div>
                            <label for="remodSpeed">Remove-speed threshold</label>
                            <input id="remodSpeed" name="suppr_vitesse_max" type="number" min="0" max="30" value="10" step="1">
                        </div>
                    </div>
                    <label class="remod-option-check"><input type="checkbox" name="sans_bot" value="true"> Manual remod only (do not generate <code>progress_out.json</code>)</label>
                    <button class="remod-button" id="remodSubmit" type="submit">Upload and start remod</button>
                </form>
                <div id="remodStatus" class="remod-status" role="status" aria-live="polite"></div>
                <div id="remodProgressWrap" hidden>
                    <progress class="remod-progress" id="remodProgress" max="100" value="0"></progress>
                    <div class="remod-progress-text" id="remodProgressText"></div>
                </div>
                <div id="remodActions" hidden>
                    <button class="remod-button" id="remodDownload" type="button">Download results (.zip)</button>
                    <button class="remod-button secondary" id="remodForget" type="button">Clear this result</button>
                </div>
            </section>

            <p class="remod-help">Your file is sent securely to the remod service for processing. It is not stored by this website. Result files contain your roster and mods; keep the downloaded archive private.</p>
            <section id="remodResults" class="remod-results" hidden>
                <h2>Remod results</h2>
                <p class="remod-help">Click a character row to expand its StatQ, stat changes and mod recommendations.</p>
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
    const submitButton = document.getElementById('remodSubmit');
    const statusBox = document.getElementById('remodStatus');
    const progressWrap = document.getElementById('remodProgressWrap');
    const progressBar = document.getElementById('remodProgress');
    const progressText = document.getElementById('remodProgressText');
    const actions = document.getElementById('remodActions');
    const downloadButton = document.getElementById('remodDownload');
    const forgetButton = document.getElementById('remodForget');
    const resultsSection = document.getElementById('remodResults');
    const resultsContainer = document.getElementById('remodPlan');
    const csrf = form.elements.csrf.value;
    let pollTimer = null;
    let busy = false;

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
        downloadButton.disabled = value;
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
                downloadButton.hidden = false;
                showMessage('Remod complete. Download the ZIP archive to get your results.');
            } else if (name === 'error') {
                setBusy(false);
                progressWrap.hidden = true;
                actions.hidden = false;
                downloadButton.hidden = true;
                showMessage('The remod calculation failed: ' + (state.error || 'No further details were provided.'), true);
            } else {
                throw new Error('Unknown remod status: ' + name);
            }
        } catch (error) {
            setBusy(false);
            showMessage(error.message || 'Unable to retrieve the job status.', true);
        }
    }
    fileInput.addEventListener('change', function () {
        const file = fileInput.files && fileInput.files[0];
        fileName.textContent = file ? file.name + ' (' + (file.size / (1024 * 1024)).toFixed(2) + ' MB)' : 'JSON file, maximum size 30 MB.';
        if (file && (file.size > 30 * 1024 * 1024 || !file.name.toLowerCase().endsWith('.json'))) {
            showMessage('Choose a .json file no larger than 30 MB.', true);
            submitButton.disabled = true;
        } else {
            hideMessage();
            submitButton.disabled = busy;
            // Selecting a valid file immediately starts the server-side upload.
            if (file && !busy) form.requestSubmit();
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
        stopPolling();
        actions.hidden = true;
        progressWrap.hidden = true;
        hideMessage();
        setBusy(true);
        showMessage('Uploading your file and creating the remod job…');
        try {
            const data = new FormData(form);
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
    downloadButton.addEventListener('click', async function () {
        if (busy) return;
        setBusy(true);
        showMessage('Preparing the results archive…');
        try {
            const data = new FormData();
            data.append('action', 'download');
            data.append('csrf', csrf);
            const response = await fetch('codexcon.php', { method: 'POST', body: data, credentials: 'same-origin' });
            if (!response.ok) {
                const body = await response.json().catch(function () { return {}; });
                throw new Error(body.error || 'Unable to download results.');
            }
            const blob = await response.blob();
            try {
                const planData = await window.codexRemodExtractPlan(blob);
                const count = window.codexRemodRenderPlan(resultsContainer, planData);
                resultsSection.hidden = false;
                showMessage('Remod complete. ' + count + ' character plans loaded below; your ZIP download will start now.');
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } catch (renderError) {
                resultsSection.hidden = true;
                showMessage('The ZIP will be downloaded, but its plan could not be displayed: ' + (renderError.message || String(renderError)), true);
            }
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'codex-remod-results.zip';
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.setTimeout(function () { URL.revokeObjectURL(url); }, 30000);
            actions.hidden = true;
            progressWrap.hidden = true;
            if (resultsSection.hidden) showMessage('Archive downloaded. The remote result has been cleaned up.');
            fileInput.value = '';
            fileName.textContent = 'JSON file, maximum size 30 MB.';
            setBusy(false);
            submitButton.disabled = false;
        } catch (error) {
            showMessage(error.message || 'Unable to download results.', true);
            setBusy(false);
        }
    });
    forgetButton.addEventListener('click', async function () {
        if (busy) return;
        if (!window.confirm('Clear this remod job and delete its remote results if they are ready?')) return;
        setBusy(true);
        stopPolling();
        try {
            await request('forget');
            actions.hidden = true;
            downloadButton.hidden = false;
            progressWrap.hidden = true;
            showMessage('Remod job cleared.');
            setBusy(false);
            submitButton.disabled = false;
        } catch (error) {
            setBusy(false);
            showMessage(error.message || 'Unable to clear the job.', true);
        }
    });

    <?php if ($hasJob): ?>
    setBusy(true);
    showMessage('Restoring your remod job status…');
    pollTimer = window.setTimeout(pollStatus, 300);
    <?php endif; ?>
})();
</script>
</body>
</html>
