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
include 'portrait.php';

// Find the most recent TW recorded for the player's current guild.
$tw = null;
try {
    $stmt = $conn_guionbot->prepare(
        "SELECT
            tw_history.id,
            tw_history.tw_id,
            tw_history.guild_id,
            guilds.name AS guild_name,
            tw_history.away_guild_id,
            tw_history.away_guild_name,
            tw_history.homeScore,
            tw_history.awayScore,
            tw_history.lastUpdated
         FROM tw_history
         JOIN guilds ON guilds.id = tw_history.guild_id
         WHERE tw_history.guild_id = :guild_id
         ORDER BY tw_history.start_date DESC
         LIMIT 1"
    );
    $stmt->execute([':guild_id' => $player['guild_id']]);
    $tw = $stmt->fetch(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    error_log('Error fetching player TW: ' . $e->getMessage());
}

// Get the zone information for the selected TW.
$zones = [];
if ($tw) {
    try {
        $stmt = $conn_guionbot->prepare(
            "SELECT
                side,
                zone_name,
                size,
                filled,
                victories,
                fails,
                zoneState,
                commandMsg
             FROM tw_zones
             WHERE tw_id = :tw_id"
        );
        $stmt->execute([':tw_id' => $tw['id']]);
        $zone_list = $stmt->fetchAll(PDO::FETCH_ASSOC);

        foreach ($zone_list as $zone) {
            $zones[$zone['side']][$zone['zone_name']] = $zone;
        }
    } catch (PDOException $e) {
        error_log('Error fetching player TW zones: ' . $e->getMessage());
    }
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
             ORDER BY tw_squads.zone_name, tw_squad_cells.squad_id, tw_squad_cells.cellIndex"
        );
        $stmt->execute([
            ':tw_id' => $tw['id'],
            ':player_name' => $player['name'],
        ]);
        $squad_list = $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (PDOException $e) {
        error_log('Error fetching player TW squads: ' . $e->getMessage());
    }
}

// Group cells into teams.
$squads = [];
foreach ($squad_list as $cell) {
    $squad_id = (string) $cell['squad_id'];

    if (!isset($squads[$squad_id])) {
        $squads[$squad_id] = [
            'zone_name' => $cell['zone_name'],
            'player_name' => $cell['player_name'],
            'cells' => [],
        ];
    }

    $squads[$squad_id]['cells'][] = $cell;
}

// SWGOH rarity is encoded in the defId after the colon.
$rarity_values = [
    'ONE_STAR' => 1,
    'TWO_STAR' => 2,
    'THREE_STAR' => 3,
    'FOUR_STAR' => 4,
    'FIVE_STAR' => 5,
    'SIX_STAR' => 6,
    'SEVEN_STAR' => 7,
];

$dict_units = [];
$dict_units_file = '../DATA/unitsList_dict.json';
if (is_readable($dict_units_file)) {
    $dict_units = json_decode(file_get_contents($dict_units_file), true) ?: [];
}

function player_tw_zone_color($zone, $side) {
    if (!$zone) {
        return $side === 'home' ? 'dodgerblue' : 'red';
    }

    if ($zone['zoneState'] === 'ZONECOMPLETE') {
        return $side === 'home' ? 'darkblue' : 'darkred';
    }

    if ((int) $zone['filled'] < (int) $zone['size'] || $zone['zoneState'] === 'ZONELOCKED') {
        return $side === 'home' ? 'lightblue' : 'pink';
    }

    return $side === 'home' ? 'dodgerblue' : 'red';
}

function player_tw_zone_cell($zone_name, $side, $zones, $rowspan) {
    $zone = $zones[$side][$zone_name] ?? null;
    $zone_color = player_tw_zone_color($zone, $side);
    $crossed = $zone && $zone['zoneState'] === 'ZONECOMPLETE'
        ? 'background-image: linear-gradient(to bottom right, transparent calc(50% - 1px), black, transparent calc(50% + 1px));'
        : '';
    $border = $zone && $zone['zoneState'] === 'ZONEOPEN'
        ? '5px solid yellow'
        : '3px solid white';

    echo '<td width="25" rowspan="' . (int) $rowspan . '" '
        . 'style="background-color:' . h($zone_color) . ';' . $crossed . 'border:' . $border . ';">';
    echo '<b>' . h($zone_name) . '</b><br/>';

    if (!$zone) {
        echo '0/0';
    } else {
        echo h((int) $zone['filled'] - (int) $zone['victories'])
            . '/' . h((int) $zone['size']);
    }

    echo '</td>';
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
        .player-tw-map {
            display: flex;
            flex-wrap: wrap;
        }

        .player-tw-map .tw-side {
            width: 50%;
            box-sizing: border-box;
            padding: 0 0.75rem;
        }

        .player-tw-map table {
            table-layout: fixed;
            width: 200px;
            height: 200px;
            color: white;
            margin: 0 auto;
        }

        .player-tw-map .tw-home-map {
            background-color: dodgerblue;
        }

        .player-tw-map .tw-away-map {
            background-color: red;
        }

        .tw-teams {
            display: grid;
            gap: 1rem;
        }

        .tw-team {
            overflow-x: auto;
        }

        .tw-team-header {
            margin-bottom: 0.5rem;
        }

        .tw-team-header strong {
            margin-right: 1rem;
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

        @media only screen and (max-width: 700px) {
            .player-tw-map .tw-side {
                width: 100%;
                margin-bottom: 1rem;
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

<?php if (!$tw): ?>
                <div class="card">
                    No Territory War found for this player's current guild.
                </div>
<?php else: ?>
                <h3>My Territory War</h3>
                <div class="card">
                    <p>
                        <strong>TW:</strong>
                        <?php echo h($tw['guild_name']); ?>
                        vs
                        <?php echo h($tw['away_guild_name']); ?>
                    </p>
                    <p>
                        <small>Last update: <?php echo h($tw['lastUpdated']); ?></small>
                    </p>

                    <div class="player-tw-map">
                        <div class="tw-side">
                            <h4>
                                <?php echo h($tw['homeScore']); ?>
                            </h4>
                            <table class="tw-home-map">
                                <tr>
                                    <?php player_tw_zone_cell('F2', 'home', $zones, 2); ?>
                                    <?php player_tw_zone_cell('F1', 'home', $zones, 2); ?>
                                    <?php player_tw_zone_cell('T2', 'home', $zones, 3); ?>
                                    <?php player_tw_zone_cell('T1', 'home', $zones, 3); ?>
                                </tr>
                                <tr height="33"></tr>
                                <tr>
                                    <?php player_tw_zone_cell('T4', 'home', $zones, 2); ?>
                                    <?php player_tw_zone_cell('T3', 'home', $zones, 2); ?>
                                </tr>
                                <tr>
                                    <?php player_tw_zone_cell('B2', 'home', $zones, 3); ?>
                                    <?php player_tw_zone_cell('B1', 'home', $zones, 3); ?>
                                </tr>
                                <tr>
                                    <?php player_tw_zone_cell('B4', 'home', $zones, 3); ?>
                                    <?php player_tw_zone_cell('B3', 'home', $zones, 3); ?>
                                </tr>
                                <tr height="33"></tr>
                            </table>
                        </div>

                        <div class="tw-side">
                            <h4>
                                <?php echo h($tw['awayScore']); ?>
                            </h4>
                            <table class="tw-away-map">
                                <tr>
                                    <?php player_tw_zone_cell('T1', 'away', $zones, 3); ?>
                                    <?php player_tw_zone_cell('T2', 'away', $zones, 3); ?>
                                    <?php player_tw_zone_cell('F1', 'away', $zones, 2); ?>
                                    <?php player_tw_zone_cell('F2', 'away', $zones, 2); ?>
                                </tr>
                                <tr height="33"></tr>
                                <tr>
                                    <?php player_tw_zone_cell('T3', 'away', $zones, 2); ?>
                                    <?php player_tw_zone_cell('T4', 'away', $zones, 2); ?>
                                </tr>
                                <tr>
                                    <?php player_tw_zone_cell('B1', 'away', $zones, 3); ?>
                                    <?php player_tw_zone_cell('B2', 'away', $zones, 3); ?>
                                </tr>
                                <tr>
                                    <?php player_tw_zone_cell('B3', 'away', $zones, 2); ?>
                                    <?php player_tw_zone_cell('B4', 'away', $zones, 2); ?>
                                </tr>
                                <tr height="33"></tr>
                            </table>
                        </div>
                    </div>
                </div>

                <h3>My TW teams</h3>
                <div class="tw-teams">
<?php if (empty($squads)): ?>
                    <div class="card">
                        No teams found for this Territory War.
                    </div>
<?php else: ?>
<?php foreach ($squads as $squad): ?>
                    <div class="card tw-team">
                        <div class="tw-team-header">
                            <strong><?php echo h($squad['zone_name']); ?></strong>
                        </div>

                        <div class="tw-team-portraits">
<?php
foreach (array_slice($squad['cells'], 0, 5) as $unit) {
    $def_parts = explode(':', (string) $unit['defId']);
    $unit_short_id = $def_parts[0];
    $unit_rarity = $rarity_values[$def_parts[1] ?? ''] ?? 7;
    $unit_alignment = $dict_units[$unit_short_id]['forceAlignment'] ?? 0;

    // Ships do not use gear frames/badges.
    $unit_gear = !empty($dict_units[$unit_short_id])
        && (int) ($dict_units[$unit_short_id]['combatType'] ?? 1) === 2
        ? 0
        : (int) $unit['tier'];

    display_portrait(
        $unit_short_id,
        $unit_alignment,
        $unit_rarity,
        $unit_gear,
        $unit['unitRelicTier'],
        $unit['zetaCount'],
        $unit['omicronCount']
    );
}
?>
                        </div>
                    </div>
<?php endforeach; ?>
<?php endif; ?>
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
