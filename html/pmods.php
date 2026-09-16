<?php
require_once 'security.php';

ini_set('session.gc_maxlifetime', 3600 * 24 * 7);
session_set_cookie_params([
    'lifetime' => 3600 * 24 * 7,
    'path' => '/',
    'secure' => true,
    'httponly' => true,
    'samesite' => 'Lax',
]);
session_start();

require 'guionbotdb.php';
include 'pvariables.php';

$isAdmin = !empty($_SESSION['admin']);

if (!isset($_GET['ac'])) {
    header('Location: index.php');
    exit();
}

$allycode = get_required_ally_code();
[$isMyAllycode, $isMyAllycodeConfirmed] = set_session_rights_for_allycode($allycode);

include 'pdata.php';
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
</head>
<body>
<div class="site-container">
    <div class="site-pusher">
        <?php include 'navbar.php'; ?>

        <div class="site-content">
            <div class="container">
                <h2>
                    <?php echo h($player['name']); ?>
                    <a href="https://swgoh.gg/p/<?php echo rawurlencode($allycode); ?>">
                        <img src="IMAGES/LOGOS/swgohgg_logo.png" width="50" alt="swgoh.gg" />
                    </a>
                </h2>

                <div class="card">
                    <p style="color:green;display:inline">
                        <?php echo $isMyAllycode ? 'This is your account' : ''; ?>
                    </p>
                    <p style="color:red;display:inline">
                        <br/>
                        <?php echo $isAdmin ? 'You are logged as an administrator' : ''; ?>
                    </p>
                </div>

                <h3>Player current guild</h3>
                <a href="g.php?gid=<?php echo rawurlencode((string) $player['guild_id']); ?>">
                    <?php echo h($player['guild_name']); ?>
                </a>

                <h3>Player allyCode</h3>
                <p><?php echo h($allycode); ?></p>

                <?php include 'pnavbar.php'; ?>

                <h3>Player Mods</h3>
            </div>
        </div>

        <div class="site-cache" id="site-cache"></div>
    </div>
</div>
</body>
<?php include 'sitefooter.php'; ?>
</html>
