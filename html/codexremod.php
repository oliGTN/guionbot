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
require_once __DIR__ . '/pvariables.php';

// Selling is available only when this page is explicitly scoped to a confirmed allyCode.
$codex_requested_ally_code = isset($_GET['ac']) && is_string($_GET['ac'])
    ? preg_replace('/[ -]/', '', $_GET['ac'])
    : '';
if (!preg_match('/^\\d{5,12}$/', $codex_requested_ally_code)) {
    $codex_requested_ally_code = '';
}
[$codex_is_my_ally_code, $codex_is_my_ally_code_confirmed] = $codex_requested_ally_code !== ''
    ? set_session_rights_for_allycode($codex_requested_ally_code)
    : [false, false, false, false];
$codex_can_sell_mods = $codex_requested_ally_code !== '' && $codex_is_my_ally_code_confirmed;
$hasJob = isset($_SESSION['codex_remod_job']) && is_array($_SESSION['codex_remod_job']);
$codex_unit_search_metadata = [];
$codex_units_file = __DIR__ . '/../DATA/unitsList_dict.json';
$codex_categories_file = __DIR__ . '/../DATA/categoryList_dict.json';
if (is_readable($codex_units_file) && is_readable($codex_categories_file)) {
    $codex_units = json_decode(file_get_contents($codex_units_file), true) ?: [];
    $codex_categories = json_decode(file_get_contents($codex_categories_file), true) ?: [];
    foreach ($codex_units as $unit_id => $unit) {
        $tags = [];
        $category_ids = $unit['categoryId'] ?? [];
        if (!is_array($category_ids)) {
            $category_ids = [$category_ids];
        }
        foreach ($category_ids as $category_id) {
            $desc = $codex_categories[$category_id]['descKey'] ?? null;
            if (is_string($desc) && trim($desc) !== '') {
                $tags[] = $desc;
            }
        }
        $codex_unit_search_metadata[strtolower((string) $unit_id)] = implode(' ', array_unique($tags));
    }
}

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
    <link rel="stylesheet" href="portrait.css">
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
        .remod-error-log { margin-top:12px; padding-top:10px; border-top:1px solid #e5b8b8; }
        .remod-error-log summary { cursor:pointer; font-weight:700; }
        .remod-error-log pre { max-height:420px; overflow:auto; white-space:pre-wrap; overflow-wrap:anywhere; background:#fff; color:#4b1d1d; border:1px solid #edcccc; border-radius:4px; padding:10px; font-size:12px; }
        .remod-error-log-note { margin:10px 0 0; font-size:13px; }
        .remod-progress { width: 100%; height: 18px; margin: 12px 0; }
        .remod-progress-text { font-weight: 600; }
        .remod-options { display: grid; grid-template-columns: repeat(auto-fit,minmax(190px,1fr)); gap: 14px; margin: 20px 0; }
        .remod-options label { display: block; font-size: 14px; font-weight: 600; margin-bottom: 5px; }
        .remod-options select, .remod-options input { width: 100%; box-sizing: border-box; padding: 9px; border: 1px solid #c7cbd4; border-radius: 4px; background: white; }
        .remod-options label.remod-option-check { display:flex; align-items:center; gap:8px; margin:14px 0; font-weight:600; cursor:pointer; }
        .remod-option-check input[type="checkbox"] { display:inline-block !important; visibility:visible !important; opacity:1 !important; position:static !important; appearance:auto !important; -webkit-appearance:checkbox !important; accent-color:#6c4bd2; flex:0 0 18px; width:18px !important; min-width:18px; height:18px !important; margin:0 !important; padding:0 !important; cursor:pointer; pointer-events:auto !important; }
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
        .remod-results { max-width: 900px; margin: 24px auto 40px; padding: 24px; box-sizing:border-box; background:#fff; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,.10); }
        .remod-plan-toolbar { display:grid; grid-template-columns:minmax(12rem,2fr) minmax(10rem,1fr) minmax(10rem,1fr); gap:8px; align-items:center; margin:14px 0; }
        .remod-plan-count { grid-column:1 / -1; }
        .remod-plan-toolbar input,.remod-plan-toolbar select { width:100%; box-sizing:border-box; padding:9px; border:1px solid #c7cbd4; border-radius:4px; background:white; }
        .remod-plan-list { display:grid; gap:6px; }
        .remod-result-tabs { display:flex; width:100%; gap:0; border-bottom:2px solid #e2e5eb; margin:16px 0; }
        .remod-result-tab { flex:1 1 0; min-width:0; border:0; border-bottom:3px solid transparent; background:#f5f6f8; padding:11px 12px; font-weight:700; cursor:pointer; color:#50586b; margin:0; text-align:center; transition:background .15s,color .15s,border-color .15s; }
        .remod-result-tab + .remod-result-tab { border-left:1px solid #e2e5eb; }
        .remod-result-tab:hover { background:#eeeaf9; color:#5536b7; }
        .remod-result-tab[aria-selected="true"] { color:#5536b7; background:#f2effb; border-bottom-color:#6c4bd2; }
        .remod-profile-picker { display:grid; grid-template-columns:minmax(180px,1fr) minmax(0,2fr); gap:12px; align-items:end; margin:8px 0 18px; padding:12px; border:1px solid #d9dce4; border-radius:7px; background:#fafbfc; }
        .remod-profile-picker[hidden] { display:none !important; }
        .remod-profile-picker label { display:block; margin-bottom:5px; }
        .remod-profile-picker select { width:100%; box-sizing:border-box; padding:9px; border:1px solid #c7cbd4; border-radius:4px; background:white; }
        .remod-profile-summary { display:flex; flex-wrap:wrap; align-items:center; gap:8px 18px; min-height:38px; color:#343a46; }
        .remod-profile-summary span { display:inline-block; }
        @media (max-width:650px) { .remod-profile-picker { grid-template-columns:1fr; } }
        .remod-result-pane[hidden] { display:none !important; }
        .remod-delete-toolbar { display:flex; flex-wrap:wrap; align-items:center; gap:10px; margin:14px 0; }
        .remod-delete-toolbar button { cursor:pointer; padding:7px 11px; }
        .remod-delete-filter { display:inline-flex; align-items:center; gap:6px; font-weight:500; }
        .remod-delete-filter input[type="checkbox"] { display:inline-block !important; visibility:visible !important; opacity:1 !important; position:static !important; appearance:auto !important; -webkit-appearance:checkbox !important; accent-color:#6c4bd2; width:18px !important; min-width:18px; height:18px !important; margin:0 2px 0 0 !important; padding:0 !important; cursor:pointer; pointer-events:auto !important; }
        #remodCancelJob { margin-top:8px; }
        #remodCancelJob[hidden] { display:none !important; }
        .remod-delete-feedback { flex-basis:100%; font-size:13px; color:#4b5563; overflow-wrap:anywhere; }
        .remod-delete-select { display:flex !important; justify-content:flex-end; align-items:center; min-height:24px; margin:-2px 0 3px; position:relative; z-index:5; cursor:pointer; }
        .remod-delete-select input.remod-delete-checkbox { display:inline-block !important; visibility:visible !important; opacity:1 !important; position:static !important; appearance:auto !important; -webkit-appearance:checkbox !important; accent-color:#6c4bd2; flex:0 0 18px; width:18px !important; min-width:18px; height:18px !important; margin:0 2px 0 0 !important; padding:0 !important; cursor:pointer; pointer-events:auto !important; }
        .remod-delete-select input.remod-delete-checkbox:checked { accent-color:#6c4bd2; }
        .remod-delete-card .remod-delete-stats { color:#242936; }
        .remod-delete-card .remod-delete-stats .remod-delete-primary,
        .remod-delete-card .remod-delete-stats .remod-delete-secondary { display:block !important; visibility:visible !important; opacity:1 !important; }
        .remod-delete-art { overflow:visible; }
        .remod-delete-overlay { position:absolute; inset:0; pointer-events:none; }
        .remod-delete-stars { position:absolute; z-index:4; top:0; left:1px; right:1px; text-align:center; font-size:12px; line-height:16px; letter-spacing:-1px; color:#ffe66d; text-shadow:0 1px 2px #000, 0 0 2px #000; white-space:nowrap; }
        .remod-delete-level { position:absolute; z-index:4; right:0; bottom:0; padding:1px 4px; border-radius:4px 0 0 0; background:#111c; color:#fff; font-size:11px; line-height:15px; font-weight:700; text-shadow:0 1px 1px #000; }
        .remod-delete-primary { font-weight:400; border:0 !important; padding-top:0 !important; }
        .remod-delete-secondary { border-top:1px solid #eceef3; padding-top:4px; }
        .remod-delete-stats { text-align:left; }
        .remod-delete-card[hidden] { display:none !important; }
        .remod-delete-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(210px,1fr)); gap:12px; }
        .remod-delete-card { border:1px solid #d9dce4; border-radius:7px; padding:12px; background:#fff; min-width:0; }
        .remod-delete-card { position:relative; overflow:hidden; }
        .remod-delete-sold-overlay { position:absolute; z-index:20; inset:0; display:flex; align-items:center; justify-content:center; width:140%; left:-20%; transform:rotate(-20deg); pointer-events:none; user-select:none; box-sizing:border-box; border-top:4px solid rgba(170,0,0,.82); border-bottom:4px solid rgba(170,0,0,.82); background:rgba(255,255,255,.28); color:rgba(180,0,0,.92); font-size:clamp(28px,5vw,48px); line-height:1.1; font-weight:900; letter-spacing:.12em; text-shadow:0 1px 2px #fff, 1px 2px 2px rgba(0,0,0,.45); }
        .remod-delete-art { width:90px; height:90px; margin:6px auto 10px; position:relative; background-image:url('IMAGES/MODS/mod-shape-atlas.png'); background-size:1080px 450px; background-position:calc(var(--shape-x) * -90px) calc(var(--shape-y) * -90px); background-repeat:no-repeat; }
        .remod-delete-art::after { content:''; position:absolute; width:32px; height:32px; left:29px; top:29px; background-image:url('IMAGES/MODS/mod-icon-atlas.png'); background-size:256px 160px; background-position:calc(var(--icon-x) * -32px) calc(var(--icon-y) * -32px); background-repeat:no-repeat; }
        .remod-delete-card[data-slot="2"] .remod-delete-art::after { left:36px;top:23px; }
        .remod-delete-card[data-slot="3"] .remod-delete-art::after { left:39px;top:20px; }
        .remod-delete-card[data-slot="5"] .remod-delete-art::after { left:29px;top:34px; }
        .remod-delete-portrait { position:absolute; z-index:3; left:-5px; bottom:-5px; width:48px; height:48px; border-radius:50%; overflow:hidden; background:rgba(0,0,0,.75); border:2px solid rgba(255,255,255,.9); box-shadow:0 1px 4px rgba(0,0,0,.65); object-fit:cover; }
        .remod-delete-title { text-align:center; font-weight:700; margin-bottom:5px; }
        .remod-delete-meta { text-align:center; font-size:13px; color:#626979; margin-bottom:8px; }
        .remod-delete-stats { font-size:13px; display:grid; gap:4px; overflow-wrap:anywhere; }
        .remod-delete-stats div { border-top:1px solid #eceef3; padding-top:4px; }
        .remod-plan-card { border:1px solid #d9dce4; border-radius:7px; overflow:hidden; background:#fff; }
        .remod-plan-card[hidden] { display:none; }
        .remod-plan-summary { list-style:none; display:grid; grid-template-columns:28px 44px minmax(0,1fr) auto 16px; gap:10px; align-items:center; padding:10px 12px; cursor:pointer; }
        .remod-plan-summary::-webkit-details-marker { display:none; } .remod-plan-summary:hover { background:#f8f8fb; }
        .remod-rank { color:#7a7f8b; text-align:center; font-size:13px; }
        .remod-portrait { width:42px; height:42px; object-fit:cover; border-radius:50%; }
        .remod-server-portrait { display:inline-flex; align-items:center; justify-content:center; width:42px; height:53px; flex:none; overflow:visible; }
        .remod-server-portrait .portrait-container, .remod-server-portrait .portrait-container.portrait-small { width:42px; margin:0; flex:none; }
        .remod-server-portrait .portrait-name { display:none; }
        .remod-portrait-wrap { position:relative; display:inline-block; width:42px; height:42px; flex:none; }
        .remod-portrait-wrap .remod-portrait { display:block; }
        .remod-progression-badges span { position:absolute; z-index:2; font-size:9px; line-height:13px; font-weight:800; padding:0 3px; border:1px solid #fff; border-radius:5px; white-space:nowrap; box-shadow:0 1px 2px #0005; }
        .remod-progression-stars { top:-4px; left:-5px; background:#f4cf58; color:#493300; }
        .remod-progression-gear { bottom:-4px; left:-5px; background:#475569; color:#fff; }
        .remod-progression-relic { bottom:-4px; right:-5px; background:#6d3fc0; color:#fff; }
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
        .remod-percentile-row td { padding-top:2px; background:#fafbfc; }
        .remod-percentile { min-width:260px; padding:5px 2px 8px; }
        .remod-percentile-track { height:9px; margin:8px 3px 5px; position:relative; border-radius:5px; background:linear-gradient(to right,#e5e7eb,#f3f4f6); }
        .remod-percentile-band { position:absolute; top:0; bottom:0; background:#c7d2fe; border-radius:5px; }
        .remod-percentile-marker { position:absolute; z-index:2; top:-4px; width:3px; height:17px; transform:translateX(-50%); border-radius:2px; }
        .remod-percentile-marker.before { background:#2563eb; }
        .remod-percentile-marker.after { background:#16a34a; }
        .remod-percentile-labels,.remod-percentile-values { display:flex; justify-content:space-between; gap:8px; font-size:11px; color:#626979; flex-wrap:wrap; }
        .remod-percentile-values { justify-content:flex-start; gap:16px; margin-top:4px; color:#343a46; }
        .remod-percentile-dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:4px; }
        .remod-percentile-dot.before { background:#2563eb; } .remod-percentile-dot.after { background:#16a34a; }
        .remod-decision { display:inline-block; padding:2px 7px; border-radius:10px; font-weight:700; font-size:12px; }
        .remod-decision.replace { background:#fff0e8; color:#a43f0b; } .remod-decision.keep { background:#eaf7ee; color:#176b35; }
        .remod-alternatives,.remod-technical { margin-top:12px; } .remod-alternatives > summary,.remod-technical > summary { cursor:pointer; padding:6px 0; font-weight:600; }
        .remod-technical pre { max-height:400px; overflow:auto; background:#f5f6f8; padding:10px; font-size:12px; }
        @media (max-width:650px) { .remod-panel { padding:16px; } .remod-wrap { margin-top:16px; } .remod-plan-toolbar { grid-template-columns:1fr 1fr; } .remod-plan-toolbar .remod-plan-search { grid-column:1 / -1; } .remod-plan-summary { grid-template-columns:20px 36px minmax(0,1fr) auto; gap:6px; padding:8px; } .remod-portrait-wrap { width:34px; height:34px; } .remod-portrait { width:34px; height:34px; } .remod-gain { grid-column:3; grid-row:2; justify-self:start; } .remod-chevron { grid-column:4; grid-row:1 / span 2; } .remod-identity { grid-column:3; } .remod-plan-table { min-width:560px; } }
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
                    <input class="remod-file" type="file" id="remodFile" name="file" accept=".json,application/json">
                    <div id="remodFileName" class="remod-help">JSON file, maximum size 30 MB.</div>
                    <div id="remodProfilePicker" class="remod-profile-picker" hidden>
                        <div>
                            <label for="remodProfileSelect"><strong>AllyCode</strong></label>
                            <select id="remodProfileSelect" aria-label="Select allyCode"></select>
                        </div>
                        <div id="remodProfileSummary" class="remod-profile-summary" aria-live="polite"></div>
                    </div>
                    <div class="remod-result-tabs remod-input-tabs" role="tablist" aria-label="Computation type">
                        <button type="button" class="remod-result-tab" id="remodInputTab" role="tab" aria-selected="true" aria-controls="remodInputPane">Remod</button>
                        <button type="button" class="remod-result-tab" id="statqInputTab" role="tab" aria-selected="false" aria-controls="statqInputPane">StatQ</button>
                    </div>
                    <div id="remodInputPane" role="tabpanel" aria-labelledby="remodInputTab">
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
                            <label for="remodFullLang">Language</label>
                            <select id="remodFullLang" name="lang"><option value="fr" selected>Français</option><option value="en">English</option></select>
                        </div>
                        <div>
                            <label for="remodMinLevel">Minimum hero level</label>
                            <select id="remodMinLevel" name="min_level">
                                <option value="all" selected>All levels</option>
                                <option value="G1">G1</option><option value="G2">G2</option><option value="G3">G3</option><option value="G4">G4</option><option value="G5">G5</option><option value="G6">G6</option><option value="G7">G7</option><option value="G8">G8</option><option value="G9">G9</option><option value="G10">G10</option><option value="G11">G11</option><option value="G12">G12</option><option value="G13">G13</option>
                                <option value="R0">R0</option><option value="R1">R1</option><option value="R2">R2</option><option value="R3">R3</option><option value="R4">R4</option><option value="R5">R5</option><option value="R6">R6</option><option value="R7">R7</option><option value="R8">R8</option><option value="R9">R9</option>
                            </select>
                        </div>
                        <div>
                            <label for="remodProtectLevel">Protect mods below</label>
                            <select id="remodProtectLevel" name="protect_level">
                                <option value="none" selected>No protection</option>
                                <option value="G1">G1</option><option value="G2">G2</option><option value="G3">G3</option><option value="G4">G4</option><option value="G5">G5</option><option value="G6">G6</option><option value="G7">G7</option><option value="G8">G8</option><option value="G9">G9</option><option value="G10">G10</option><option value="G11">G11</option><option value="G12">G12</option><option value="G13">G13</option>
                                <option value="R0">R0</option><option value="R1">R1</option><option value="R2">R2</option><option value="R3">R3</option><option value="R4">R4</option><option value="R5">R5</option><option value="R6">R6</option><option value="R7">R7</option><option value="R8">R8</option><option value="R9">R9</option>
                            </select>
                        </div>
                        <div>
                            <label for="remodPoidsK1">Kyber 1 weighting (0–1)</label>
                            <input id="remodPoidsK1" name="poids_k1" type="number" min="0" max="1" value="0.5" step="0.05">
                        </div>
                        <label class="remod-option-check"><input type="checkbox" id="remodFreeUnselected" name="free_unselected" value="true"> Reuse mods from heroes below the minimum level</label>
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
                    </div>
                    <div id="statqInputPane" role="tabpanel" aria-labelledby="statqInputTab" hidden>
                        <p class="remod-help">Calculate StatQ from your currently equipped mods. Characters below the selected minimum level are excluded from the score and maximum; no remod is performed.</p>
                        <div><label for="statqAllycode">Ally code (optional, 9 digits)</label><input id="statqAllycode" type="text" inputmode="numeric" pattern="[0-9 -]{9,11}" maxlength="11" placeholder="123-456-789"><p class="remod-help">Use an ally code instead of uploading a file. Only equipped mods are counted.</p></div>
                        <div class="remod-options">
                            <div><label for="statqTarget">Kyber 1 target</label><select id="statqTarget"><option value="moyenne" selected>Average</option><option value="mediane">Median</option><option value="p75">75th percentile (harder target)</option></select></div>
                            <div><label for="statqSort">Sort characters</label><select id="statqSort"><option value="alpha" selected>Alphabetical</option><option value="points">Points percentage, best first</option></select></div>
                            <div><label for="statqMinLevel">Minimum hero level</label><select id="statqMinLevel"><option value="all" selected>All levels</option><option value="G1">G1</option><option value="G2">G2</option><option value="G3">G3</option><option value="G4">G4</option><option value="G5">G5</option><option value="G6">G6</option><option value="G7">G7</option><option value="G8">G8</option><option value="G9">G9</option><option value="G10">G10</option><option value="G11">G11</option><option value="G12">G12</option><option value="G13">G13</option><option value="R0">R0</option><option value="R1">R1</option><option value="R2">R2</option><option value="R3">R3</option><option value="R4">R4</option><option value="R5">R5</option><option value="R6">R6</option><option value="R7">R7</option><option value="R8">R8</option><option value="R9">R9</option></select></div>
                            <div><label for="statqLang">Language</label><select id="statqLang"><option value="fr" selected>Français</option><option value="en">English</option></select></div>
                        </div>
                        <button class="remod-button" id="statqSubmit" type="submit">Upload and calculate StatQ</button>
                    </div>
                </form>
                <div id="remodStatus" class="remod-status" role="status" aria-live="polite"></div>
                <div id="remodProgressWrap" hidden>
                    <progress class="remod-progress" id="remodProgress" max="100" value="0"></progress>
                    <div class="remod-progress-text" id="remodProgressText"></div>
                    <button class="remod-button secondary" id="remodCancelJob" type="button" hidden>Cancel calculation</button>
                </div>
                <div id="remodActions" hidden>
                    <button class="remod-button" id="remodShowResults" type="button">Show results</button>
                    <button class="remod-button secondary" id="remodForget" type="button">Clear this result</button>
                </div>
            </section>

            <p class="remod-help">Your file is sent securely to the remod service for processing. It is not stored by this website. Result files contain your roster and mods; keep the downloaded archive private.</p>
            <section id="remodResults" class="remod-results" hidden>
                <h2 id="remodResultsHeading">Remod results</h2>
                <p class="remod-help" id="remodResultsIntro">Click a character row to expand its StatQ, stat changes and mod recommendations.</p>
                <div id="remodResultDownloads" hidden>
                    <button class="remod-button" id="remodDownloadZip" type="button">Download results.zip</button>
                    <button class="remod-button secondary" id="remodDownloadPlan" type="button">Download plan.json</button>
                </div>
                <div id="statqResults" hidden>
                    <p class="remod-help" id="statqSummary"></p>
                    <div id="statqCsvResults" hidden></div>
                </div>
                <div id="remodResultsTabs">
                <div class="remod-result-tabs" role="tablist" aria-label="Remod results">
                    <button type="button" class="remod-result-tab" id="remodPlanTab" role="tab" aria-selected="true" aria-controls="remodPlanPane">Plan</button>
                    <button type="button" class="remod-result-tab" id="remodDeleteTab" role="tab" aria-selected="false" aria-controls="remodDeletePane">Mods to delete</button>
                </div>
                <div class="remod-result-pane" id="remodPlanPane" role="tabpanel" aria-labelledby="remodPlanTab"><div id="remodPlan"></div></div>
                <div class="remod-result-pane" id="remodDeletePane" role="tabpanel" aria-labelledby="remodDeleteTab" hidden>
                    <p class="remod-help" id="remodDeleteNote">Mods listed in mods_a_supprimer.csv, matched by the ID in its second column.</p>
                    <div id="remodDeleteMods"></div>
                </div>
                </div>
            </section>
        </main>
    </div>
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>
</div>
</div>
<script>window.codexRemodUnitMetadata = <?php echo json_encode($codex_unit_search_metadata, JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP | JSON_HEX_QUOT); ?>; window.codexRemodAllyCode = <?php echo json_encode($codex_requested_ally_code, JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP | JSON_HEX_QUOT); ?>; window.codexRemodCanSellMods = <?php echo $codex_can_sell_mods ? 'true' : 'false'; ?>; window.codexRemodSellScopeToken = <?php echo json_encode($codex_can_sell_mods ? hash_hmac('sha256', 'codex-sell:' . $codex_requested_ally_code, $_SESSION['codex_remod_csrf']) : '', JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP | JSON_HEX_QUOT); ?>;</script>
<script src="codexremod_results.js?v=20261021-planpercentiles1"></script>
<script>
(function () {
    'use strict';
    const form = document.getElementById('remodForm');
    const fileInput = document.getElementById('remodFile');
    const fileName = document.getElementById('remodFileName');
    const profilePicker = document.getElementById('remodProfilePicker');
    const profileSelect = document.getElementById('remodProfileSelect');
    const profileSummary = document.getElementById('remodProfileSummary');
    let restoreProfiles = [];
    let selectedRestoreProfile = null;
    function updateSelectedProfile() {
        const selected = restoreProfiles[Number(profileSelect.value)];
        selectedRestoreProfile = selected ? selected.profile : null;
        if (selected) {
            profileSummary.innerHTML = '<span><strong>Player:</strong> ' + esc(selected.playerName) + '</span><span><strong>Characters:</strong> ' + selected.characterCount + '</span>';
            rosterCharacters = extractCharacters(restoreProgressData, selected.profile);
        } else {
            profileSummary.textContent = '';
            rosterCharacters = extractCharacters(restoreProgressData);
        }
        rosterNote.textContent = rosterCharacters.length ? 'Loaded ' + rosterCharacters.length + ' characters from this roster.' : 'No characters found in the selected profile.';
        refreshCharacterSelect();
        if (selectedMode() === 'light' && !rosterCharacters.length) showMessage(rosterNote.textContent, true);
    }
    const remodInputTab = document.getElementById('remodInputTab');
    const statqInputTab = document.getElementById('statqInputTab');
    const remodInputPane = document.getElementById('remodInputPane');
    const statqInputPane = document.getElementById('statqInputPane');
    const statqSubmit = document.getElementById('statqSubmit');
    const statqTarget = document.getElementById('statqTarget');
    const statqSort = document.getElementById('statqSort');
    const statqLang = document.getElementById('statqLang');
    const statqResults = document.getElementById('statqResults');
    const statqSummary = document.getElementById('statqSummary');
    const statqCsvResults = document.getElementById('statqCsvResults');
    const remodResultsTabs = document.getElementById('remodResultsTabs');
    let statqCsvBlob = null;
    let selectedInputTab = 'remod';
    let activeJobMode = <?php echo json_encode($_SESSION['codex_remod_job']['mode'] ?? 'full'); ?>;
    const planTab = document.getElementById('remodPlanTab');
    const deleteTab = document.getElementById('remodDeleteTab');
    const planPane = document.getElementById('remodPlanPane');
    const deletePane = document.getElementById('remodDeletePane');
    const deleteModsContainer = document.getElementById('remodDeleteMods');
    const deleteNote = document.getElementById('remodDeleteNote');
    let restoreProgressData = null;
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
    const cancelJobButton = document.getElementById('remodCancelJob');
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
    function selectInputTab(tab) {
        selectedInputTab = tab;
        const isStatq = tab === 'statq';
        remodInputTab.setAttribute('aria-selected', isStatq ? 'false' : 'true');
        statqInputTab.setAttribute('aria-selected', isStatq ? 'true' : 'false');
        remodInputPane.hidden = isStatq;
        statqInputPane.hidden = !isStatq;
        statqResults.hidden = !isStatq || !statqCsvBlob;
        remodResultsTabs.hidden = isStatq || planJsonText === null;
        resultsSection.hidden = isStatq ? !statqCsvBlob : planJsonText === null;
        submitButton.disabled = busy || isStatq;
        statqSubmit.disabled = busy || !isStatq;
        hideMessage();
    }
    remodInputTab.addEventListener('click', () => selectInputTab('remod'));
    statqInputTab.addEventListener('click', () => selectInputTab('statq'));
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
    const targetSets = [
        ['health','Health',2,3],['offense','Offense',4,1],['defense','Defense',2,3],
        ['speed','Speed',4,1],['critchance','Critical chance',2,3],['critdamage','Critical damage',4,1],
        ['potency','Potency',2,3],['tenacity','Tenacity',2,3]
    ];
    const targetPrimaries = {
        arrow:['Speed','Accuracy %','Critical Avoidance %','Defense %','Health %','Offense %','Protection %'],
        triangle:['Critical Chance %','Critical Damage %','Defense %','Health %','Offense %','Protection %'],
        circle:['Health %','Protection %'],
        cross:['Tenacity %','Potency %','Defense %','Health %','Offense %','Protection %']
    };
    function esc(value) { return String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
    function extractProfiles(data) {
        const source = data && data.profiles;
        const entries = Array.isArray(source) ? source : (source && typeof source === 'object' ? Object.values(source) : []);
        return entries.filter(profile => profile && typeof profile === 'object').map((profile, index) => {
            const allyCode = String(profile.allyCode || profile.allycode || (profile.player && (profile.player.allyCode || profile.player.allycode)) || '').replace(/[ -]/g, '');
            const playerName = String(profile.playerName || profile.name || (profile.player && (profile.player.name || profile.player.playerName)) || profile.displayName || 'Unknown player');
            const characters = profile.characters && typeof profile.characters === 'object' ? profile.characters : {};
            const characterCount = Array.isArray(characters) ? characters.length : Object.keys(characters).length;
            return { profile, allyCode, playerName, characterCount, label: (allyCode || 'No AllyCode') + ' — ' + playerName, index };
        }).filter(item => !window.codexRemodAllyCode || item.allyCode === String(window.codexRemodAllyCode));
    }
    function extractCharacters(data, selectedProfile) {
        const roots = selectedProfile ? [selectedProfile] : [data];
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
            const setsHtml = targetSets.map(([key,label,weight,max])=>'<div><label>'+label+' sets ('+weight+' points each)</label><select data-set="'+key+'" data-weight="'+weight+'" data-max="'+max+'"><option value="0">0</option>'+Array.from({length:max},(_,i)=>i+1).map(n=>'<option value="'+n+'"'+(hero.sets[key]===n?' selected':'')+'>'+n+'</option>').join('')+'</select></div>').join('');
            const primaryHtml = Object.entries(targetPrimaries).map(([slot,opts])=>'<div><label>'+slot.charAt(0).toUpperCase()+slot.slice(1)+' primary</label><select data-primary="'+slot+'"><option value="">No preference</option>'+opts.map(v=>'<option value="'+esc(v)+'"'+(hero.primaires[slot]===v?' selected':'')+'>'+esc(v)+'</option>').join('')+'</select></div>').join('');
            const portraitId = hero.id.replace(/[^A-Za-z0-9_-]/g,'');
            card.innerHTML = '<div class="remod-target-head"><img src="IMAGES/CHARACTERS/'+encodeURIComponent(portraitId)+'.png" alt="" onerror="this.hidden=true"><strong>'+esc(hero.name)+'<br><small>'+esc(hero.id)+'</small></strong><button type="button" class="remod-button secondary" data-remove-hero>Remove</button></div><div class="remod-target-stats">'+statsHtml+'</div><button type="button" class="remod-button secondary" data-add-stat '+(hero.stats.length>=12?'disabled':'')+'>Add stat</button><details><summary>Mod sets (optional)</summary><div class="remod-target-note">Total set weight must not exceed 6.</div><div class="remod-target-extra">'+setsHtml+'</div><div class="remod-target-note" data-set-total></div></details><details><summary>Mod primaries (optional)</summary><div class="remod-target-extra">'+primaryHtml+'</div></details>';
            card.querySelector('[data-remove-hero]').addEventListener('click',()=>{targetHeroes.splice(hi,1);renderTargets();});
            card.querySelector('[data-add-stat]').addEventListener('click',()=>{if(hero.stats.length<12){hero.stats.push({stat:'',value:''});renderTargets();}});
            card.querySelectorAll('[data-remove-stat]').forEach(btn=>btn.addEventListener('click',()=>{if(hero.stats.length>1){hero.stats.splice(Number(btn.dataset.removeStat),1);renderTargets();}}));
            card.querySelectorAll('.remod-target-stat').forEach((row,si)=>{row.querySelector('select').addEventListener('change',e=>hero.stats[si].stat=e.target.value);row.querySelector('input').addEventListener('input',e=>hero.stats[si].value=e.target.value);});
            const setTotal = () => targetSets.reduce((sum,[key,label,weight])=>sum+(Number(hero.sets[key]||0)*weight),0);
            const updateSetTotal = () => {
                const total = setTotal();
                const display = card.querySelector('[data-set-total]');
                display.textContent = 'Set weight: '+total+' / 6';
                display.style.color = total > 6 ? '#b91c1c' : '';
                card.querySelectorAll('[data-set]').forEach(sel => {
                    const key=sel.dataset.set, weight=Number(sel.dataset.weight);
                    const others=targetSets.reduce((sum,[otherKey,label,otherWeight])=>sum+(otherKey===key?0:Number(hero.sets[otherKey]||0)*otherWeight),0);
                    Array.from(sel.options).forEach(option => { option.disabled = Number(option.value)*weight+others>6; });
                });
            };
            card.querySelectorAll('[data-set]').forEach(sel=>sel.addEventListener('change',e=>{
                const k=e.target.dataset.set,v=Number(e.target.value),weight=Number(e.target.dataset.weight);
                const others=targetSets.reduce((sum,[otherKey,label,otherWeight])=>sum+(otherKey===k?0:Number(hero.sets[otherKey]||0)*otherWeight),0);
                if(v*weight+others>6){e.target.value=String(hero.sets[k]||0);return;}
                if(v)hero.sets[k]=v;else delete hero.sets[k];
                updateSetTotal();
            }));
            updateSetTotal();
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
            const setWeight=targetSets.reduce((sum,[key,label,weight,max])=>{
                const count=Number(hero.sets[key]||0);
                if(!Number.isInteger(count)||count<0||count>max)throw new Error('Invalid number of '+label+' sets for '+hero.name+'.');
                return sum+count*weight;
            },0);
            if(setWeight>6)throw new Error('The mod-set weight for '+hero.name+' exceeds 6.');
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
        submitButton.disabled = value || selectedInputTab === 'statq';
        statqSubmit.disabled = value || selectedInputTab !== 'statq';
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
                cancelJobButton.hidden = false;
                const position = Number(state.queue_position);
                activeJobMode = state.mode || activeJobMode;
                showMessage((activeJobMode === 'statq' ? 'Your StatQ calculation is queued' : 'Your remod is queued') + (Number.isFinite(position) && position > 0 ? ' (position ' + position + ')' : '') + '. Waiting for a calculation slot…');
                progressWrap.hidden = false;
                progressBar.removeAttribute('value');
                progressText.textContent = 'Waiting in queue';
                pollTimer = window.setTimeout(pollStatus, 4000);
            } else if (name === 'running' || name === 'cancelling') {
                cancelJobButton.hidden = name === 'cancelling';
                const progress = state.progress || {};
                const pct = Math.max(0, Math.min(100, Number(progress.pct) || 0));
                progressWrap.hidden = false;
                progressBar.value = pct;
                progressText.textContent = (Number(progress.done) || 0) + ' / ' + (Number(progress.total) || 0) + ' heroes (' + Math.round(pct) + '%)';
                showMessage(activeJobMode === 'statq' ? 'StatQ calculation in progress…' : 'Remod calculation in progress…');
                pollTimer = window.setTimeout(pollStatus, 4000);
            } else if (name === 'cancelled') {
                cancelJobButton.hidden = true;
                cancelJobButton.disabled = false;
                setBusy(false);
                progressWrap.hidden = true;
                actions.hidden = false;
                showResultsButton.hidden = true;
                showMessage('Calculation cancelled by request.');
            } else if (name === 'done') {
                cancelJobButton.hidden = true;
                setBusy(false);
                progressWrap.hidden = false;
                progressBar.value = 100;
                progressText.textContent = '100% — calculation complete';
                actions.hidden = false;
                showResultsButton.hidden = false;
                showResultsButton.textContent = activeJobMode === 'statq' ? 'Show StatQ results' : 'Show results';
                showMessage(activeJobMode === 'statq' ? 'StatQ complete. Click Show StatQ results to view the score table.' : 'Remod complete. Click Show results to display the character cards.');
            } else if (name === 'error') {
                cancelJobButton.hidden = true;
                setBusy(false);
                progressWrap.hidden = true;
                actions.hidden = false;
                showResultsButton.hidden = true;
                showMessage('The remod calculation failed: ' + (state.error || 'No further details were provided.'), true);
                const diagnostic = state.log || state.logs || state.error_detail || state.traceback || state.detail;
                if (diagnostic) {
                    const details = document.createElement('details');
                    details.className = 'remod-error-log';
                    const summary = document.createElement('summary');
                    summary.textContent = 'Show calculation log / technical details';
                    const pre = document.createElement('pre');
                    const text = typeof diagnostic === 'string' ? diagnostic : JSON.stringify(diagnostic, null, 2);
                    pre.textContent = text.slice(0, 30000);
                    details.append(summary, pre);
                    statusBox.appendChild(details);
                } else {
                    const note = document.createElement('p');
                    note.className = 'remod-error-log-note';
                    note.textContent = 'The status response did not include a calculation log. The detailed log must be retrieved from the remod service/server logs.';
                    statusBox.appendChild(note);
                }
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
    profileSelect.addEventListener('change', updateSelectedProfile);
    fileInput.addEventListener('change', async function () {
        const file = fileInput.files && fileInput.files[0];
        fileName.textContent = file ? file.name + ' (' + (file.size / (1024 * 1024)).toFixed(2) + ' MB)' : 'JSON file, maximum size 30 MB.';
        if (file && (file.size > 30 * 1024 * 1024 || !file.name.toLowerCase().endsWith('.json'))) {
            showMessage('Choose a .json file no larger than 30 MB.', true);
            submitButton.disabled = true;
        } else {
            hideMessage();
            submitButton.disabled = busy;
            rosterCharacters = [];
            restoreProfiles = [];
            selectedRestoreProfile = null;
            profilePicker.hidden = true;
            profileSelect.replaceChildren();
            profileSummary.textContent = '';
            targetHeroes = [];
            renderTargets();
            if (file) {
                try {
                    const parsed = JSON.parse(await file.text());
                    restoreProgressData = parsed;
                    restoreProfiles = extractProfiles(parsed);
                    profilePicker.hidden = restoreProfiles.length === 0;
                    profileSelect.innerHTML = restoreProfiles.map((item, index) => '<option value="' + index + '">' + esc(item.label) + '</option>').join('');
                    profileSelect.value = restoreProfiles.length ? '0' : '';
                    selectedRestoreProfile = restoreProfiles.length ? restoreProfiles[0].profile : null;
                    // When ?ac= is present, never fall back to characters from an unscoped or mismatched profile.
                    rosterCharacters = restoreProfiles.length
                        ? extractCharacters(parsed, selectedRestoreProfile)
                        : (window.codexRemodAllyCode ? [] : extractCharacters(parsed));
                    if (restoreProfiles.length) updateSelectedProfile();
                    else {
                        profileSummary.textContent = '';
                        rosterNote.textContent = window.codexRemodAllyCode
                            ? 'No profile matching allyCode ' + window.codexRemodAllyCode + ' was found in this file.'
                            : (rosterCharacters.length ? 'Loaded ' + rosterCharacters.length + ' characters from this roster.' : 'No characters found. Make sure this is a restoreMyProgress.json file.');
                        refreshCharacterSelect();
                    }
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
        const statq = selectedInputTab === 'statq';
        const allycode = document.getElementById('statqAllycode').value.replace(/[ -]/g, '');
        if (!file && !(statq && /^\\d{9}$/.test(allycode))) { showMessage(statq ? 'Select a restoreMyProgress file or enter a 9-digit ally code.' : 'Please select a restoreMyProgress.json file.', true); return; }
        if (file && (!file.name.toLowerCase().endsWith('.json') || file.size > 30 * 1024 * 1024)) {
            showMessage('Choose a .json file no larger than 30 MB.', true); return;
        }
        const light = !statq && selectedMode() === 'light';
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
        showMessage(selectedInputTab === 'statq' ? 'Uploading your file and creating the StatQ job…' : 'Uploading your file and creating the remod job…');
        try {
            const data = new FormData(form);
            if (!file) data.delete('file');
            if (statq && !file) data.set('allycode', allycode);
            else data.delete('allycode');
            activeJobMode = selectedInputTab === 'statq' ? 'statq' : selectedMode();
            data.set('mode', activeJobMode);
            if (activeJobMode === 'statq') {
                ['cibles','sans_bot','sans_emprunt','time_limit','max_heroes','suppr_vitesse_max'].forEach(key => data.delete(key));
                data.set('cible', statqTarget.value);
                data.set('tri', statqSort.value);
                data.set('lang', statqLang.value);
                data.set('min_level', document.getElementById('statqMinLevel').value);
            } else if (light) {
                ['cible', 'max_heroes', 'suppr_vitesse_max'].forEach(key => data.delete(key));
                data.delete('sans_bot');
                data.delete('time_limit');
                data.set('cibles', new Blob([targetsJson], {type:'application/json'}), 'cibles.json');
                data.set('lang', document.getElementById('remodLang').value);
                data.set('time_limit', document.getElementById('remodLightTime').value);
                data.set('sans_bot', document.getElementById('remodSansBot').checked ? 'true' : 'false');
                data.set('sans_emprunt', document.getElementById('remodSansEmprunt').checked ? 'true' : 'false');
            } else {
                data.delete('cibles');
                data.set('lang', document.getElementById('remodFullLang').value);
                data.delete('sans_emprunt');
            }
            data.set('action', 'submit');
            const response = await fetch('codexcon.php', { method: 'POST', body: data, credentials: 'same-origin' });
            const body = await response.json();
            if (!response.ok) throw new Error(body.error || 'Unable to start remod.');
            progressWrap.hidden = false;
            cancelJobButton.hidden = false;
            progressBar.removeAttribute('value');
            progressText.textContent = 'Waiting for the first status update…';
            showMessage('Job accepted by the remod server. Checking progress every 4 seconds.');
            pollTimer = window.setTimeout(pollStatus, 1000);
        } catch (error) {
            setBusy(false);
            showMessage(error.message || 'Unable to start remod.', true);
        }
    });
    function selectResultTab(tab) {
        const showPlan = tab === 'plan';
        planTab.setAttribute('aria-selected', showPlan ? 'true' : 'false');
        deleteTab.setAttribute('aria-selected', showPlan ? 'false' : 'true');
        planPane.hidden = !showPlan;
        deletePane.hidden = showPlan;
    }
    planTab.addEventListener('click', () => selectResultTab('plan'));
    deleteTab.addEventListener('click', () => selectResultTab('delete'));
    [planTab, deleteTab].forEach((button, index) => button.addEventListener('keydown', event => {
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
            event.preventDefault();
            const next = index === 0 ? deleteTab : planTab;
            next.focus();
            selectResultTab(index === 0 ? 'delete' : 'plan');
        }
    }));
    showResultsButton.addEventListener('click', async function () {
        if (busy) return;
        setBusy(true);
        showMessage(activeJobMode === 'statq' ? 'Loading StatQ results from the service…' : 'Loading the completed plan from the remod service…');
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
            if (activeJobMode === 'statq') {
                statqCsvBlob = await window.codexRemodExtractArchiveFile(resultsZipBlob, 'statq.csv');
                const statqCsvText = await statqCsvBlob.text();
                const resumeText = await window.codexRemodExtractArchiveText(resultsZipBlob, 'statq_resume.json').catch(() => '');
                statqSummary.textContent = resumeText ? 'StatQ summary: ' + resumeText : 'StatQ CSV is ready. Click Show results to display characters and their stats.';
                statqCsvResults.replaceChildren();
                const statqStats = window.codexRemodRenderStatq(statqCsvResults, statqCsvText, restoreProgressData, csrf);
                statqCsvResults.hidden = false;
                statqSummary.textContent = 'Loaded ' + statqStats.characters + ' characters and ' + statqStats.stats + ' stat rows. Total StatQ: ' + statqStats.points + ' / ' + statqStats.max + '.';
                document.getElementById('remodResultsHeading').textContent = 'StatQ results';
                document.getElementById('remodResultsIntro').textContent = 'Current equipped mods compared with the selected Kyber 1 target. Characters below the selected minimum level are excluded from the score and maximum.';
                statqResults.hidden = false;
                remodResultsTabs.hidden = true;
                downloadButtons.hidden = false;
                downloadZipButton.hidden = false;
                downloadPlanButton.hidden = true;
                selectResultTab('plan');
                resultsSection.hidden = false;
                actions.hidden = true;
                progressWrap.hidden = true;
                showMessage('StatQ results loaded. Open the StatQ tab to view the character list and expand each character for its stats.');
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                return;
            }
            const extracted = await window.codexRemodExtractPlan(resultsZipBlob);
            planJsonText = extracted.text;
            const count = window.codexRemodRenderPlan(resultsContainer, extracted.data, restoreProgressData, csrf);
            document.getElementById('remodResultsHeading').textContent = 'Remod results';
            document.getElementById('remodResultsIntro').textContent = 'Click a character row to expand its StatQ, stat changes and mod recommendations.';
            statqResults.hidden = true;
            remodResultsTabs.hidden = false;
            downloadPlanButton.hidden = false;
            if (restoreProgressData) {
                try {
                    const csvText = await window.codexRemodExtractArchiveText(resultsZipBlob, 'mods_a_supprimer.csv');
                    const deleteCount = window.codexRemodRenderDeleteMods(deleteModsContainer, csvText, restoreProgressData, csrf);
                    deleteNote.textContent = deleteCount + ' mods found in mods_a_supprimer.csv and matched against your restoreMyProgress inventory.';
                } catch (error) {
                    deleteModsContainer.replaceChildren();
                    deleteNote.textContent = error.message || 'Unable to read mods_a_supprimer.csv from the results archive.';
                }
            } else {
                deleteModsContainer.replaceChildren();
                deleteNote.textContent = 'Select your restoreMyProgress.json file again to display mod characteristics and stats.';
            }
            selectResultTab('plan');
            resultsSection.hidden = false;
            downloadButtons.hidden = false;
            actions.hidden = true;
            progressWrap.hidden = true;
            showResultsButton.textContent = 'Show results';
            showMessage('Loaded ' + count + ' character plans. Choose whether to download the full ZIP or only plan.json.');
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
    cancelJobButton.addEventListener('click', async function () {
        if (!busy) return;
        if (!window.confirm('Cancel the calculation on the remote remod server?')) return;
        cancelJobButton.disabled = true;
        stopPolling();
        showMessage('Cancelling the remote calculation…');
        try {
            const cancellation = await request('cancel');
            cancelJobButton.hidden = true;
            cancelJobButton.disabled = false;
            showMessage(cancellation.status === 'cancelled' ? 'Calculation cancelled.' : 'Cancellation requested. Waiting for the server to stop the calculation…');
            pollTimer = window.setTimeout(pollStatus, 1000);
        } catch (error) {
            cancelJobButton.disabled = false;
            showMessage(error.message || 'Unable to cancel the calculation.', true);
            pollTimer = window.setTimeout(pollStatus, 4000);
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

    selectInputTab('remod');
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
