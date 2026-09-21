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
[$isMyAllycode, $isMyAllycodeConfirmed, $isGuildMate] = set_session_rights_for_allycode($allycode);

include 'pdata.php';
include 'portrait.php';

// Find the most recent TW recorded for the player's current guild.
$tw_id = null;
try {
    $stmt = $conn_guionbot->prepare(
        "SELECT id
         FROM tw_history
         WHERE guild_id = :guild_id
         ORDER BY start_date DESC
         LIMIT 1"
    );
    $stmt->execute([':guild_id' => $player['guild_id']]);
    $tw_id = $stmt->fetchColumn();
} catch (PDOException $e) {
    error_log('Error fetching player TW: ' . $e->getMessage());
}

// twvariables.php provides the complete TW information, including scores
// and potential scores, and twheader.php renders the common TW map.
$tw = null;
if ($tw_id !== false && $tw_id !== null) {
    $tw_id = (int) $tw_id;
    include 'twvariables.php';
}

// Get the player's squads for this TW.
$squad_list = [];
if ($tw) {
    try {
        $stmt = $conn_guionbot->prepare(
            "SELECT
                tw_squad_cells.squad_id,
                tw_squads.player_name,
                tw_squads.zone_name,
                tw_squad_cells.defId,
                tw_squad_cells.cellIndex,
                tw_squad_cells.level,
                tw_squad_cells.tier,
                tw_squad_cells.unitRelicTier,
                tw_squad_cells.zetaCount,
                tw_squad_cells.omicronCount
             FROM tw_squad_cells
             JOIN tw_squads
                 ON tw_squads.id = tw_squad_cells.squad_id
             WHERE tw_squads.tw_id = :tw_id
               AND tw_squads.player_name = :player_name
             ORDER BY
                FIELD(
                    tw_squads.zone_name,
                    'B1', 'T1', 'B2', 'T2',
                    'B3', 'T3', 'B4', 'T4',
                    'F1', 'F2'
                ),
                tw_squad_cells.squad_id,
                tw_squad_cells.cellIndex"
        );
        $stmt->execute([
            ':tw_id' => $tw_id,
            ':player_name' => $player['name'],
        ]);
        $squad_list = $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (PDOException $e) {
        error_log('Error fetching player TW squads: ' . $e->getMessage());
    }
}

// Group cells into teams, then teams by zone.
$squads_by_zone = [];
foreach ($squad_list as $cell) {
    $squad_id = (string) $cell['squad_id'];

    if (!isset($squads_by_zone[$cell['zone_name']])) {
        $squads_by_zone[$cell['zone_name']] = [];
    }

    if (!isset($squads_by_zone[$cell['zone_name']][$squad_id])) {
        $squads_by_zone[$cell['zone_name']][$squad_id] = [
            'zone_name' => $cell['zone_name'],
            'player_name' => $cell['player_name'],
            'cells' => [],
        ];
    }

    $squads_by_zone[$cell['zone_name']][$squad_id]['cells'][] = $cell;
}

// Keep the same logical order as the TW map.
$zone_order = [
    'B1', 'T1', 'B2', 'T2',
    'B3', 'T3', 'B4', 'T4',
    'F1', 'F2',
];

$ordered_squads_by_zone = [];
foreach ($zone_order as $zone_name) {
    if (isset($squads_by_zone[$zone_name])) {
        $ordered_squads_by_zone[$zone_name] = $squads_by_zone[$zone_name];
    }
}

$dict_units = [];
$dict_units_file = '../DATA/unitsList_dict.json';
if (is_readable($dict_units_file)) {
    $dict_units = json_decode(file_get_contents($dict_units_file), true) ?: [];
}

$rarity_values = [
    'ONE_STAR' => 1,
    'TWO_STAR' => 2,
    'THREE_STAR' => 3,
    'FOUR_STAR' => 4,
    'FIVE_STAR' => 5,
    'SIX_STAR' => 6,
    'SEVEN_STAR' => 7,
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
    <link rel="stylesheet" href="portrait.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
    <style>
        .tw-zone-teams {
            display: grid;
            gap: 1.25rem;
        }

        .tw-zone {
            overflow-x: auto;
        }

        .tw-zone-header {
            display: flex;
            align-items: baseline;
            gap: 1rem;
            margin-bottom: 0.75rem;
        }

        .tw-zone-header h4 {
            margin: 0;
        }

        .tw-zone-command {
            font-size: 0.95rem;
            font-weight: normal;
        }

        .tw-team {
            margin-bottom: 1rem;
        }

        .tw-team:last-child {
            margin-bottom: 0;
        }

        .tw-team-portraits {
            display: flex;
            align-items: flex-start;
            gap: 0.25rem;
            min-height: 90px;
            white-space: nowrap;
        }

        .tw-team-portraits > div {
            flex: 0 0 auto;
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

<?php if ($isGuildMate||$isAdmin): ?>
<?php if (!$tw): ?>
                <div class="card">
                    No Territory War found for this player's current guild.
                </div>
<?php else: ?>
                <?php
                // Render the exact same TW map and scores as tw.php/twz.php.
                $twheader_map_only = true;
                include 'twheader.php';
                ?>

                <h3>My TW teams</h3>

                <div class="tw-zone-teams">
<?php if (empty($ordered_squads_by_zone)): ?>
                    <div class="card">
                        No teams found for this Territory War.
                    </div>
<?php else: ?>
<?php foreach ($ordered_squads_by_zone as $zone_name => $zone_squads): ?>
                    <div class="card tw-zone">
                        <?php
                        $command_msg = $zones['home'][$zone_name]['commandMsg'] ?? '';
                        ?>
                        <div class="tw-zone-header">
                            <h4><?php echo htmlspecialchars($zone_name, ENT_QUOTES, 'UTF-8'); ?></h4>
                            <?php if ($command_msg !== ''): ?>
                                <span class="tw-zone-command">
                                    <?php echo htmlspecialchars($command_msg, ENT_QUOTES, 'UTF-8'); ?>
                                </span>
                            <?php endif; ?>
                        </div>

<?php foreach ($zone_squads as $squad): ?>
                        <div class="tw-team">
                            <div class="tw-team-portraits">
<?php
foreach (array_slice($squad['cells'], 0, 5) as $unit) {
    $def_parts = explode(':', (string) $unit['defId']);
    $unit_short_id = $def_parts[0];
    $unit_rarity = $rarity_values[$def_parts[1] ?? ''] ?? 7;
    $unit_alignment = $dict_units[$unit_short_id]['forceAlignment'] ?? 0;
    $unit_isShip = (int) ($dict_units[$unit_short_id]['combatType'] ?? 1) === 2;

    $unit_gear = !empty($dict_units[$unit_short_id])
        && $unit_isShip
        ? 0
        : (int) $unit['tier'];

    display_portrait(
        $unit_short_id,
        $unit_alignment,
        $unit_rarity,
        $unit_gear,
        $unit['unitRelicTier'],
        $unit['zetaCount'],
        $unit['omicronCount'],
        $unit_isShip
    );
}
?>
                            </div>
                        </div>
<?php endforeach; ?>
                    </div>
<?php endforeach; ?>
<?php endif; ?>
                </div>
<?php endif; ?>

            </div>
<?php else: ?>
        You are not allowed to see TW data for this guild
<?php endif; //($isGuildMate||$isAdmin) ?>
        </div>

        <div class="site-cache" id="site-cache"></div>
    </div>
</div>
</body>
<?php include 'sitefooter.php'; ?>
</html>
