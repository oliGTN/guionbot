<?php
require_once 'security.php';
ini_set('session.gc_maxlifetime', 3600 * 24 * 7);
session_set_cookie_params(['lifetime'=>3600*24*7,'path'=>'/','secure'=>true,'httponly'=>true,'samesite'=>'Lax']);
session_start();
require 'guionbotdb.php';
include 'pvariables.php';
$isAdmin = !empty($_SESSION['admin']);
if (!isset($_GET['ac'])) { header('Location: index.php'); exit(); }
$allycode = get_required_ally_code();
[$isMyAllycode, $isMyAllycodeConfirmed, $isGuildMate, $isGuildMateConfirmed] = set_session_rights_for_allycode($allycode);
include 'pdata.php';

try {
    $stmt = $conn_guionbot->prepare("SELECT id, setId, focused, level_3, level_6, level_9, level_12, level_15 FROM datacrons WHERE allyCode = :allycode ORDER BY id");
    $stmt->execute([':allycode' => $allycode]);
    $datacrons = $stmt->fetchAll(PDO::FETCH_ASSOC);

    $icon_keys = [];
    foreach ($datacrons as $datacron) {
        for ($level = 15; $level >= 3; $level -= 3) {
            $value = trim((string)($datacron['level_'.$level] ?? ''));
            if ($value === '') continue;
            $parts = explode(':', $value, 2);
            $icon_key = trim($parts[1] ?? '');
            if ($icon_key !== '') {
                $icon_keys[$icon_key] = true;
            }
            break;
        }
    }

    $icons = [];
    //error_log(print_r($icon_keys, true));
    if ($icon_keys) {
        $icon_stmt = $conn_guionbot->prepare(
            "SELECT targetRule, scopeIcon FROM datacron_icons"
        );
        $icon_stmt->execute();
        foreach ($icon_stmt->fetchAll(PDO::FETCH_ASSOC) as $icon) {
            $icons[strtolower(trim($icon['targetRule']))] = trim((string)$icon['scopeIcon']);
        }
    }
} catch (PDOException $e) {
    error_log('Error fetching player datacrons: '.$e->getMessage());
    $datacrons = [];
    $icons = [];
}
?>
<!DOCTYPE html>
<html>
<head>
    <title>GuiOn bot for SWGOH</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="basic.css">
    <link rel="stylesheet" href="tables.css">
    <link rel="stylesheet" href="navbar.css">
    <link rel="stylesheet" href="main.1.008.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
    <style>
        .datacrons-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:1rem; }
        .datacron-card { text-align:center; padding:1rem; }
        .datacron-art { position:relative; width:160px; height:160px; margin:0 auto; }
        .datacron-art .datacron-background,.datacron-art .datacron-icon { position:absolute; inset:0; width:100%; height:100%; object-fit:contain; }
        .datacron-art .datacron-icon { z-index:2; padding:25%; box-sizing:border-box; }
        .datacron-dots { position:absolute; z-index:3; bottom:8px; left:50%; transform:translateX(-50%); display:flex; gap:6px; }
        .datacron-dot { width:10px; height:10px; border-radius:50%; background:white; border:1px solid #555; box-shadow:0 1px 3px rgba(0,0,0,.7); }
        @media only screen and (max-width:600px) {
            .datacrons-grid { grid-template-columns:repeat(2,minmax(0,1fr)); gap:.5rem; }
            .datacron-art { width:130px; height:130px; }
        }
    </style>
</head>
<body>
<div class="site-container"><div class="site-pusher">
<?php include 'navbar.php'; ?>
<div class="site-content"><div class="container">
<?php include 'pheader.php'; ?>
<h3>Player Datacrons</h3>
<?php if (empty($datacrons)): ?>
<div class="card">No datacrons found.</div>
<?php else: ?>
<div class="datacrons-grid">

<?php foreach ($datacrons as $datacron): ?>
<?php
$target_rule = null;
foreach ([15,12,9,6,3] as $level) {
    $value = trim((string)($datacron['level_'.$level] ?? ''));
    if ($value !== '') {
        $parts = explode(':', $value, 2);
        $target_rule = trim($parts[1] ?? '');

        break;
    }
}
$remainder = ((int)$datacron['setId']) % 4;
$suffix = [1=>'a',2=>'b',3=>'c',0=>'d'][$remainder];
$background = 'IMAGES/DATACRONS/tex.datacron_'.$suffix.'.png';
$icon = null;
if ($target_rule !== '') {
    $icon_value = $icons[strtolower($target_rule)] ?? null;
    if ($icon_value !== null && $icon_value !== '') {
        $icon = preg_match('#^https?://#i', $icon_value)
            ? $icon_value
            : (
                strpos($icon_value, 'IMAGES/') === 0
                    ? $icon_value
                    : 'IMAGES/DATACRONS/' . ltrim($icon_value, '/')
            );
    }
}
$dot_count = 0;
foreach ([3,6,9,12,15] as $level) if (trim((string)($datacron['level_'.$level] ?? '')) !== '') $dot_count++;
?>
<div class="card datacron-card"><div class="datacron-art">
<img class="datacron-background" src="<?php echo h($background); ?>" alt="">
<?php if ($icon !== null): ?><img class="datacron-icon" src="<?php echo h($icon); ?>" alt=""><?php endif; ?>
<div class="datacron-dots"><?php for ($i=0;$i<$dot_count;$i++): ?><span class="datacron-dot"></span><?php endfor; ?></div>
</div></div>
<?php endforeach; ?>
</div>
<?php endif; ?>
</div></div></div></div>
<?php include 'sitefooter.php'; ?>
</body></html>
