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
include 'portrait.php';

try {
    $stmt = $conn_guionbot->prepare("SELECT id, setId, focused, level_3, level_6, level_9, level_12, level_15 FROM datacrons WHERE allyCode = :allycode ORDER BY id");
    $stmt->execute([':allycode' => $allycode]);
    $datacrons = $stmt->fetchAll(PDO::FETCH_ASSOC);

    $icons = load_datacron_icons($conn_guionbot);
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
    <link rel="stylesheet" href="portrait.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
    <style>
        .datacrons-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:1rem; }
        .datacron-card { text-align:center; padding:1rem; }
        .datacron-art { position:relative; width:160px; height:160px; margin:0 auto; }
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
<div class="card datacron-card">
<?php display_datacron($datacron, $icons); ?>
</div>
<?php endforeach; ?>
</div>
<?php endif; ?>
</div></div></div></div>
<?php include 'sitefooter.php'; ?>
</body></html>
