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
            min-height: 280px;
        }

        .mod-card-title {
            text-align: center;
            font-size: 18px;
            font-weight: 500;
            margin-bottom: 0.5rem;
            text-transform: capitalize;
        }

        /*
         * SWGOH mod shape atlas:
         * 1080 x 450 pixels, 12 columns x 5 rows, 90 x 90 pixel cells.
         * Columns 0-5 are normal shapes and columns 6-11 are gold shapes.
         */
        .mod-art {
            position: relative;
            width: 180px;
            height: 180px;
            margin: 0 auto 0.75rem;
            background-image: url('IMAGES/MODS/mod-shape-atlas.png');
            background-size: 2160px 900px;
            background-position:
                calc(var(--shape-x) * -180px)
                calc(var(--shape-y) * -180px);
            background-repeat: no-repeat;
        }

        /*
         * SWGOH mod icon atlas:
         * 256 x 160 pixels, 8 columns x 5 rows, 32 x 32 pixel cells.
         */
        .mod-art::after {
            content: '';
            position: absolute;
            width: 64px;
            height: 64px;
            left: 58px;
            top: 58px;
            background-image: url('IMAGES/MODS/mod-icon-atlas.png');
            background-size: 512px 320px;
            background-position:
                calc(var(--icon-x) * -64px)
                calc(var(--icon-y) * -64px);
            background-repeat: no-repeat;
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

            .mod-art {
                width: 140px;
                height: 140px;
                background-size: 1680px 700px;
                background-position:
                    calc(var(--shape-x) * -140px)
                    calc(var(--shape-y) * -140px);
            }

            .mod-art::after {
                width: 50px;
                height: 50px;
                left: 45px;
                top: 45px;
                background-size: 400px 250px;
                background-position:
                    calc(var(--icon-x) * -50px)
                    calc(var(--icon-y) * -50px);
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
    $pips = (int) $mod['pips'];
    $tier = (int) $mod['tier'];

    $slot_name = $slot_names[$slot] ?? 'unknown';
    $set_name = $set_names[$mod_set] ?? 'unknown';

    // Slots 2-7 map to the six shape columns.
    $slot_index = max(0, min(5, $slot - 2));

    // The gold shape is the 6-dot variant (columns 6-11).
    $shape_index = $slot_index + ($pips >= 6 ? 6 : 0);

    // Both atlases use the same five color/tier rows.
    $tier_index = max(0, min(4, $tier - 1));

    // Mod sets 1-8 map directly to the eight icon columns.
    $icon_index = max(0, min(7, $mod_set - 1));
?>
                    <div class="card mod-card">
                        <div class="mod-card-title">
                            <?php echo h($set_name); ?>
                        </div>

                        <div
                            class="mod-art"
                            style="--shape-x: <?php echo $shape_index; ?>; --shape-y: <?php echo $tier_index; ?>; --icon-x: <?php echo $icon_index; ?>; --icon-y: <?php echo $tier_index; ?>;"
                            role="img"
                            aria-label="<?php echo h($set_name . ' ' . $slot_name); ?> mod"
                        ></div>

                        <div class="mod-details">
                            <span><?php echo h($slot_name); ?></span>
                            <span><?php echo h($pips); ?>★</span>
                            <span>Lvl <?php echo h($mod['level']); ?></span>
                            <span>Tier <?php echo h($tier); ?></span>
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
