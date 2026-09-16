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

try {
    $stmt = $conn_guionbot->prepare(
        "SELECT slot, mod_set, pips, mods.level, tier, roster.defId
         FROM mods
         JOIN roster ON roster.id = mods.roster_id
         WHERE allyCode = :allycode
         ORDER BY slot, mod_set"
    );
    $stmt->execute([':allycode' => $allycode]);
    $mods = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    error_log('Error fetching player mods: ' . $e->getMessage());
    $mods = [];
}

$slot_names = [
    2 => 'square',
    3 => 'arrow',
    4 => 'diamond',
    5 => 'triangle',
    6 => 'circle',
    7 => 'cross',
];

$set_names = [
    1 => 'health',
    2 => 'offense',
    3 => 'defense',
    4 => 'speed',
    5 => 'critchance',
    6 => 'critdamage',
    7 => 'potency',
    8 => 'tenacity',
];
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
        .mods-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
            gap: 1rem;
        }

        .mod-card {
            position: relative;
            padding: 0.9rem;
            margin: 0;
            min-height: 260px;
        }

        .mod-card-title {
            text-align: center;
            font-size: 18px;
            font-weight: 500;
            margin-bottom: 0.5rem;
            text-transform: capitalize;
        }

        .mod-image {
            display: block;
            width: 150px;
            height: 150px;
            margin: 0 auto 0.75rem;
            object-fit: contain;
        }

        .mod-details {
            text-align: center;
            line-height: 1.5;
        }

        .mod-details span {
            margin: 0 0.25rem;
        }

        @media only screen and (max-width: 600px) {
            .mods-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .mod-image {
                width: 120px;
                height: 120px;
            }
        }
    </style>
</head>
<body>
<div class="site-container">
    <div class="site-pusher">
        <?php include 'navbar.php'; ?>

        <div class="site-content">
            <div class="container">
                <?php include 'pheader.php'; ?>

                <h3>Player Mods</h3>

                <div class="mods-grid">
<?php foreach ($mods as $mod): ?>
<?php
    $slot = (int) $mod['slot'];
    $mod_set = (int) $mod['mod_set'];
    $slot_name = $slot_names[$slot] ?? 'unknown';
    $set_name = $set_names[$mod_set] ?? 'unknown';

    // The mod atlas contains the SWGOH mod artwork. Keep the atlas as a CSS
    // background so the image remains crisp and transparent like in-game.
    $atlas = 'IMAGES/MODS/mods.png';
?>
                    <div class="card mod-card">
                        <div class="mod-card-title">
                            <?php echo h($set_name); ?>
                        </div>

                        <div
                            class="mod-image mod-<?php echo h($slot_name); ?>"
                            data-slot="<?php echo h($slot); ?>"
                            data-set="<?php echo h($mod_set); ?>"
                            style="background-image:url('<?php echo h($atlas); ?>');"
                            aria-label="<?php echo h($set_name . ' ' . $slot_name); ?> mod"
                        ></div>

                        <div class="mod-details">
                            <span><?php echo h($slot_name); ?></span>
                            <span><?php echo h($mod['pips']); ?>★</span>
                            <span>Lvl <?php echo h($mod['level']); ?></span>
                            <span>Tier <?php echo h($mod['tier']); ?></span>
                            <div><?php echo h($mod['defId']); ?></div>
                        </div>
                    </div>
<?php endforeach; ?>
                </div>

                <?php if (empty($mods)): ?>
                    <div class="card">
                        No mods found.
                    </div>
                <?php endif; ?>
            </div>
        </div>

        <div class="site-cache" id="site-cache"></div>
    </div>
</div>
</body>
<?php include 'sitefooter.php'; ?>
</html>
