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

if (!isset($_SESSION['user_id']) && isset($_COOKIE['discord_access_token'])) {
    $return_path = $_SERVER['REQUEST_URI'] ?? '/';
    if (!is_string($return_path) || $return_path === '' || $return_path[0] !== '/' || substr($return_path, 0, 2) === '//' || strpos($return_path, '\\') !== false || preg_match('/[\\x00-\\x1F\\x7F]/', $return_path)) {
        $return_path = '/';
    }
    header('Location: init-oauth.php?return=' . rawurlencode($return_path));
    exit();
}

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
                tw_squad_cells.omicronCount,
                datacrons.id AS datacron_id,
                datacrons.setId AS datacron_setId,
                datacrons.focused AS datacron_focused,
                datacrons.level_3 AS datacron_level_3,
                datacrons.level_6 AS datacron_level_6,
                datacrons.level_9 AS datacron_level_9,
                datacrons.level_12 AS datacron_level_12,
                datacrons.level_15 AS datacron_level_15
             FROM tw_squad_cells
             JOIN tw_squads
                 ON tw_squads.id = tw_squad_cells.squad_id
             LEFT JOIN datacrons
                 ON datacrons.id = tw_squads.datacron_id
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
            'datacron' => !empty($cell['datacron_id']) ? [
                'id' => $cell['datacron_id'],
                'setId' => $cell['datacron_setId'],
                'focused' => $cell['datacron_focused'],
                'level_3' => $cell['datacron_level_3'],
                'level_6' => $cell['datacron_level_6'],
                'level_9' => $cell['datacron_level_9'],
                'level_12' => $cell['datacron_level_12'],
                'level_15' => $cell['datacron_level_15'],
            ] : null,
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

$tw_zones = ['B1', 'T1', 'B2', 'T2', 'B3', 'T3', 'B4', 'T4', 'F1', 'F2'];

$zone_team_counts = [];
foreach ($tw_zones as $zone_name) {
    $zone_team_counts[$zone_name] = isset($squads_by_zone[$zone_name])
        ? count($squads_by_zone[$zone_name])
        : 0;
}

$dict_units = [];
$dict_units_file = __DIR__ . '/../DATA/unitsList_dict.json';
if (is_readable($dict_units_file)) {
    $dict_units = json_decode(file_get_contents($dict_units_file), true) ?: [];
}

$dict_capas = [];
$dict_capas_file = __DIR__ . '/../DATA/unit_capa_list.json';
if (is_readable($dict_capas_file)) {
    $dict_capas = json_decode(file_get_contents($dict_capas_file), true) ?: [];
}

$datacron_icons = load_datacron_icons($conn_guionbot);

$used_unit_ids = [];
$used_datacron_ids = [];

foreach ($squad_list as $cell) {
    $def_parts = explode(':', (string) $cell['defId']);
    $used_unit_ids[(string) $def_parts[0]] = true;
    if (!empty($cell['datacron_id'])) {
        $used_datacron_ids[(string) $cell['datacron_id']] = true;
    }
}

$roster_units = [];
try {
    $stmt = $conn_guionbot->prepare(
        "SELECT
            r.defId,
            r.combatType,
            r.forceAlignment,
            r.gear,
            r.level,
            r.rarity,
            r.relic_currentTier,
            GROUP_CONCAT(
                CONCAT(rs.name, ':', rs.level)
                SEPARATOR ','
            ) AS skill_levels,
            COALESCE(
                SUM(
                    CASE
                        WHEN rs.omicron_type <> '' AND rs.level > 0 THEN 1
                        ELSE 0
                    END
                ),
                0
            ) AS omicron_count
         FROM roster r
         LEFT JOIN roster_skills rs ON rs.roster_id = r.id
         WHERE r.allyCode = :allycode
           AND ISNULL(r.eraLevel)
         GROUP BY
            r.id,
            r.defId,
            r.combatType,
            r.forceAlignment,
            r.gear,
            r.level,
            r.rarity,
            r.relic_currentTier
         ORDER BY r.combatType, r.gp DESC"
    );
    $stmt->execute([':allycode' => $allycode]);

    foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $roster_unit) {
        $def_id = (string) $roster_unit['defId'];

        if (!isset($dict_units[$def_id]) || isset($used_unit_ids[$def_id])) {
            continue;
        }

        $zeta_count = 0;
        if (isset($dict_capas[$def_id]) && !empty($roster_unit['skill_levels'])) {
            foreach (explode(',', $roster_unit['skill_levels']) as $skill_data) {
                [$skill_name, $skill_level] = array_pad(explode(':', $skill_data, 2), 2, null);
                if (
                    $skill_name !== null
                    && $skill_level !== null
                    && isset($dict_capas[$def_id][$skill_name]['zetaTier'])
                    && (int) $dict_capas[$def_id][$skill_name]['zetaTier'] < 99
                    && (int) $skill_level >= (int) $dict_capas[$def_id][$skill_name]['zetaTier']
                ) {
                    $zeta_count++;
                }
            }
        }

        ob_start();
        display_portrait(
            $def_id,
            (int) $roster_unit['forceAlignment'],
            max(1, min(7, (int) $roster_unit['rarity'])),
            (int) $roster_unit['gear'],
            (int) $roster_unit['relic_currentTier'],
            $zeta_count,
            (int) $roster_unit['omicron_count'],
            (int) $roster_unit['combatType'] === 2
        );
        $portrait_html = ob_get_clean();

        $roster_units[] = [
            'id' => $def_id,
            'name' => $dict_units[$def_id]['name'] ?? $def_id,
            'isShip' => (int) $roster_unit['combatType'] === 2,
            'isCapital' => strpos($def_id, 'CAPITAL') === 0,
            'portrait' => $portrait_html,
        ];
    }
}

catch (PDOException $e) {
    error_log('Error fetching player roster for TW team creator: ' . $e->getMessage());
}

$player_datacrons = [];
if ($tw) {
    try {
        $stmt = $conn_guionbot->prepare(
            "SELECT id, setId, focused, level_3, level_6, level_9, level_12, level_15
             FROM datacrons
             WHERE allyCode = :allycode
               AND id NOT IN (
                   SELECT datacron_id
                   FROM tw_squads
                   WHERE tw_id = :tw_id
                     AND player_name = :player_name
                     AND datacron_id IS NOT NULL
               )
             ORDER BY 
                setId,
                CASE
                WHEN NOT isnull(level_15) THEN 15
                WHEN NOT isnull(level_12) THEN 12
                WHEN NOT isnull(level_9) THEN 9
                WHEN NOT isnull(level_6) THEN 6
                WHEN NOT isnull(level_3) THEN 3
                ELSE 0 END DESC;
            "
        );
        $stmt->execute([
            ':allycode' => $allycode,
            ':tw_id' => $tw_id,
            ':player_name' => $player['name'],
        ]);
        $player_datacrons = $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (PDOException $e) {
        error_log('Error fetching player datacrons: ' . $e->getMessage());
    }
}

$player_datacron_html = [];
foreach ($player_datacrons as $datacron) {
    ob_start();
    display_datacron($datacron, $datacron_icons, true);
    $player_datacron_html[(string) $datacron['id']] = ob_get_clean();
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

        .tw-team.proposed {
            background: #fff1d6;
            border: 2px solid #f28c28;
            border-radius: 6px;
            padding: 0.5rem;
        }

        .tw-team-proposed-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            margin-bottom: 0.5rem;
            color: #b35a00;
            font-weight: bold;
        }

        .tw-team-delete,
        .tw-add-team {
            border: 0;
            border-radius: 4px;
            cursor: pointer;
            padding: 0.25rem 0.6rem;
        }

        .tw-add-team {
            align-self: flex-start;
            margin-left: 0.5rem;
        }

        .tw-push-proposed {
            margin-top: 1rem;
            display: none;
        }

        .tw-team-portraits {
            display: flex;
            align-items: flex-start;
            gap: 2rem;
            min-height: 90px;
            white-space: nowrap;
        }

        .tw-team-portraits > div {
            flex: 0 0 auto;
        }

        .tw-selected-unit.tw-fleet-reinforcement,
        .tw-team-portraits .tw-fleet-reinforcement {
            transform: scale(0.75);
            transform-origin: top left;
            margin-right: -1.5rem;
        }

        .tw-team-creator {
            display: grid;
            gap: 1rem;
        }

        .tw-selected-units {
            display: flex;
            align-items: flex-start;
            flex-wrap: nowrap;
            gap: 0.25rem;
            min-height: 100px;
            padding: 0.75rem;
            border: 1px solid #ccc;
            border-radius: 4px;
        }

        .tw-portrait-slot {
            width: 120px;
            height: 100px;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            flex: 0 0 120px;
        }

        .tw-portrait-slot > .portrait-container {
            flex: 0 0 80px;
        }

        .tw-selected-unit {
            position: relative;
            width: 120px;
            height: 100px;
            flex: 0 0 120px;
        }

        .tw-selected-unit[draggable="true"] {
            cursor: grab;
        }

        .tw-selected-unit.tw-dragging {
            opacity: 0.45;
            cursor: grabbing;
        }

        .tw-selected-unit[draggable="false"] {
            cursor: default;
        }

        .tw-selected-team {
            display: flex;
            align-items: flex-start;
            flex-wrap: nowrap;
            width: 100%;
        }

        .tw-selected-datacron {
            flex: 0 0 95px;
            width: 95px;
            height: 95px;
            position: relative;
            margin-left: 0.5rem;
        }

        .tw-selected-datacron .datacron-display {
            width: 95px;
            height: 95px;
        }

        .tw-selected-datacron-item {
            position: relative;
            width: 95px;
            height: 95px;
        }

        .tw-selected-datacron-item > button {
            position: absolute;
            top: -0.4rem;
            right: -0.4rem;
            border: 0;
            border-radius: 50%;
            width: 22px;
            height: 22px;
            cursor: pointer;
            z-index: 10;
        }

        .tw-selected-unit button {
            position: absolute;
            top: -0.4rem;
            right: -0.4rem;
            border: 0;
            border-radius: 50%;
            width: 22px;
            height: 22px;
            cursor: pointer;
        }

        .tw-unit-search {
            width: 100%;
            max-width: 420px;
            box-sizing: border-box;
            padding: 0.6rem;
        }

        .tw-unit-results {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            max-height: 300px;
            overflow-y: auto;
            padding: 0.5rem;
            border: 1px solid #ccc;
            border-radius: 4px;
        }

        .tw-unit-result {
            cursor: pointer;
            border: 1px solid #ccc;
            background: #fff;
            border-radius: 4px;
            padding: 0;
            width: 120px;
            height: 150px;
            box-sizing: border-box;
            position: relative;
            overflow: visible;
            text-align: center;
        }

        /* The portrait component owns its badge alignment. Keep the selector neutral. */
        .tw-unit-result .tw-portrait-slot {
            justify-content: center;
        }

        .tw-unit-result .tw-portrait-slot > .portrait-container {
            transform: translateX(-11%);
        }

        .tw-datacron-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            max-height: 260px;
            overflow-y: auto;
            padding: 0.5rem;
            border: 1px solid #ccc;
            border-radius: 4px;
        }

        .tw-datacron-card {
            cursor: pointer;
            width: 95px;
            height: 95px;
            flex: 0 0 95px;
            border: 2px solid transparent;
            border-radius: 6px;
            background: none;
            padding: 0;
            text-align: center;
        }

        .tw-datacron-card .datacron-display {
            width: 95px;
            height: 95px;
        }

        .tw-datacron-card.selected {
            border-color: #333;
        }

        .tw-datacron-card.tw-datacron-new-set {
            margin-left: 1.5rem;
        }

        .tw-datacron-card span {
            display: block;
            font-size: 0.75rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .tw-zone-command-creator {
            padding: 0.75rem;
            border-left: 4px solid #888;
            background: #f5f5f5;
        }

        .tw-creator-error {
            color: #b00020;
            font-weight: bold;
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
                $twheader_no_navbar = true;
                include 'twheader.php';
                ?>

                <h3>My TW teams</h3>

                <div class="tw-zone-teams" id="tw-zone-teams">
<?php if (empty($ordered_squads_by_zone)): ?>
                    <div class="card" id="tw-no-teams">
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
foreach ($squad['cells'] as $unit) {
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
        $unit_isShip,
        $unit_isShip && (int) $unit['cellIndex'] >= 4
    );
}
?>
<?php if (!empty($squad['datacron'])): ?>
                                <?php display_datacron($squad['datacron'], $datacron_icons, true); ?>
<?php endif; ?>
                            </div>
                        </div>
<?php endforeach; ?>
                    </div>
<?php endforeach; ?>
<?php endif; ?>
                </div>

                <button type="button" class="tw-push-proposed" id="tw-push-proposed">Push proposed teams to game</button>

                <div class="card tw-team-creator" id="create-team">
                    <h3>Create a new TW team</h3>
                    <div id="tw-team-form">

                        <label for="tw-zone-select"><b>Zone</b></label>
                        <select id="tw-zone-select">
<?php foreach ($tw_zones as $zone): ?>
                            <option value="<?php echo htmlspecialchars($zone, ENT_QUOTES, 'UTF-8'); ?>"><?php echo htmlspecialchars($zone, ENT_QUOTES, 'UTF-8'); ?> (<?php echo $zone_team_counts[$zone]; ?>)</option>
<?php endforeach; ?>
                        </select>

                        <div id="tw-zone-command-creator" class="tw-zone-command-creator"></div>

                        <div class="tw-unit-picker">
                            <div>
                                <b>Selected units</b>
                                <div id="tw-selected-team" class="tw-selected-team">
                                    <div id="tw-selected-units" class="tw-selected-units"></div>
                                    <div id="tw-selected-datacron" class="tw-selected-datacron"></div>
                                    <button type="button" id="tw-create-team" class="tw-add-team">Add</button>
                                </div>
                            </div>
                            <div>
                                <label for="tw-unit-search"><b>Find a character or ship</b></label>
                                <input type="search" id="tw-unit-search" class="tw-unit-search" placeholder="Type a unit name..." autocomplete="off">
                                <div id="tw-unit-results" class="tw-unit-results"></div>
                            </div>
                        </div>

                        <div id="tw-datacron-selector">
                            <label for="tw-datacron-set"><b>Datacron set</b></label>
                            <select id="tw-datacron-set">
                                <option value="">All sets</option>
<?php
$player_datacron_sets = [];
foreach ($player_datacrons as $datacron) {
    $player_datacron_sets[(string) $datacron['setId']] = true;
}
ksort($player_datacron_sets, SORT_NUMERIC);
foreach (array_keys($player_datacron_sets) as $set_id):
?>
                                <option value="<?php echo htmlspecialchars($set_id, ENT_QUOTES, 'UTF-8'); ?>">Set <?php echo htmlspecialchars($set_id, ENT_QUOTES, 'UTF-8'); ?></option>
<?php endforeach; ?>
                            </select>

                            <div id="tw-datacron-list" class="tw-datacron-list">
<?php foreach ($player_datacrons as $datacron): ?>
                                <button type="button"
                                        class="tw-datacron-card"
                                        data-set-id="<?php echo htmlspecialchars((string) $datacron['setId'], ENT_QUOTES, 'UTF-8'); ?>"
                                        data-datacron-id="<?php echo htmlspecialchars((string) $datacron['id'], ENT_QUOTES, 'UTF-8'); ?>"
                                        title="Set <?php echo htmlspecialchars((string) $datacron['setId'], ENT_QUOTES, 'UTF-8'); ?>">
                                    <?php echo $player_datacron_html[(string) $datacron['id']] ?? ''; ?>
                                </button>
<?php endforeach; ?>
                            </div>
                            <input type="hidden" id="tw-datacron-id" value="">
                        </div>

                        <div id="tw-creator-limit"></div>
                    </div>
                </div>

            </div>
<?php endif; ?>
<?php else: ?>
        You are not allowed to see TW data for this guild
<?php endif; //($isGuildMate||$isAdmin) ?>
        </div>

        <div class="site-cache" id="site-cache"></div>
    </div>
</div>
<script>
const twUnits = <?php echo json_encode($roster_units, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT); ?>;

const twDatacrons = <?php echo json_encode($player_datacron_html, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT); ?>;
const twZoneCommands = <?php
$creator_zone_commands = [];
foreach ($tw_zones as $zone) {
    $creator_zone_commands[$zone] = $zones['home'][$zone]['commandMsg'] ?? '';
}
echo json_encode($creator_zone_commands, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT);
?>;

const zoneTeamsContainer = document.getElementById('tw-zone-teams');
const pushProposedButton = document.getElementById('tw-push-proposed');
const createTeamButton = document.getElementById('tw-create-team');
const noTeamsMessage = document.getElementById('tw-no-teams');

const zoneSelect = document.getElementById('tw-zone-select');
const unitSearch = document.getElementById('tw-unit-search');
const unitResults = document.getElementById('tw-unit-results');
const selectedDatacronContainer = document.getElementById('tw-selected-datacron');
const selectedUnitsContainer = document.getElementById('tw-selected-units');
const datacronSelector = document.getElementById('tw-datacron-selector');
const datacronFilter = document.getElementById('tw-datacron-set');
const datacronIdInput = document.getElementById('tw-datacron-id');
const datacronList = document.getElementById('tw-datacron-list');
const zoneCommandCreator = document.getElementById('tw-zone-command-creator');
const creatorLimit = document.getElementById('tw-creator-limit');

if (zoneSelect) {
    let selectedUnits = [];
    let proposedTeams = [];

    function fleetZone() {
        return zoneSelect.value === 'F1' || zoneSelect.value === 'F2';
    }

    function renderSelected() {
        selectedUnitsContainer.innerHTML = '';
        selectedUnits.forEach((unitId, index) => {
            const unit = twUnits.find((entry) => entry.id === unitId);
            if (!unit) return;

            const wrapper = document.createElement('div');
            wrapper.className = 'tw-selected-unit';
            wrapper.dataset.index = String(index);

            const fleet = fleetZone();
            const isCapital = fleet && index === 0;

            if (fleet && index >= 4) {
                wrapper.classList.add('tw-fleet-reinforcement');
            }

            // The capital ship must remain first and cannot be dragged.
            wrapper.draggable = !isCapital;
            if (!isCapital) {
                wrapper.addEventListener('dragstart', (event) => {
                    event.dataTransfer.effectAllowed = 'move';
                    event.dataTransfer.setData('text/plain', String(index));
                    wrapper.classList.add('tw-dragging');
                });
                wrapper.addEventListener('dragend', () => {
                    wrapper.classList.remove('tw-dragging');
                });
            }

            wrapper.addEventListener('dragover', (event) => {
                event.preventDefault();

                const sourceIndex = Number(event.dataTransfer.getData('text/plain'));
                const targetIndex = Number(wrapper.dataset.index);

                if (!Number.isInteger(sourceIndex) || sourceIndex === targetIndex) return;
                if (fleet && (sourceIndex === 0 || targetIndex === 0)) return;

                event.dataTransfer.dropEffect = 'move';
            });

            wrapper.addEventListener('drop', (event) => {
                event.preventDefault();

                const sourceIndex = Number(event.dataTransfer.getData('text/plain'));
                const targetIndex = Number(wrapper.dataset.index);

                if (!Number.isInteger(sourceIndex) || !Number.isInteger(targetIndex)) return;
                if (sourceIndex === targetIndex) return;
                if (fleet && (sourceIndex === 0 || targetIndex === 0)) return;

                const [movedUnit] = selectedUnits.splice(sourceIndex, 1);
                selectedUnits.splice(targetIndex, 0, movedUnit);

                renderSelected();
                renderResults();
            });

            const portrait = document.createElement('div');
            portrait.className = 'tw-portrait-slot';
            portrait.innerHTML = unit.portrait;
            portrait.title = unit.name;
            wrapper.appendChild(portrait);

            const remove = document.createElement('button');
            remove.type = 'button';
            remove.textContent = '×';
            remove.title = 'Remove ' + unit.name;
            remove.addEventListener('click', () => {
                selectedUnits.splice(index, 1);
                renderSelected();
                renderResults();
            });
            wrapper.appendChild(remove);
            selectedUnitsContainer.appendChild(wrapper);
        });
        if (selectedDatacronContainer) {
            selectedDatacronContainer.innerHTML = '';
            const datacronId = datacronIdInput ? datacronIdInput.value : '';
            if (datacronId && twDatacrons[datacronId]) {
                const datacron = document.createElement('div');
                datacron.className = 'tw-selected-datacron-item';
                datacron.innerHTML = twDatacrons[datacronId];

                const removeDatacron = document.createElement('button');
                removeDatacron.type = 'button';
                removeDatacron.textContent = '×';
                removeDatacron.title = 'Remove datacron';
                removeDatacron.addEventListener('click', () => {
                    datacronIdInput.value = '';
                    datacronList.querySelectorAll('.tw-datacron-card').forEach((item) => item.classList.remove('selected'));
                    renderSelected();
                });
                datacron.appendChild(removeDatacron);
                selectedDatacronContainer.appendChild(datacron);
            }
        }

    }

    function renderResults() {
        const fleet = fleetZone();
        const max = fleet ? 8 : 5;
        const search = unitSearch.value.trim().toLowerCase();
        unitResults.innerHTML = '';

        twUnits
            .filter((unit) => fleet ? unit.isShip : !unit.isShip)
            .filter((unit) => unit.name.toLowerCase().includes(search))
            .filter((unit) => !selectedUnits.includes(unit.id))
            .filter((unit) => !proposedTeams.some((team) => team.units.includes(unit.id)))
            .filter((unit) => !fleet || (selectedUnits.length === 0 ? unit.isCapital : !unit.isCapital))
            .slice(0, 100)
            .forEach((unit) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'tw-unit-result';

                const portraitWrapper = document.createElement('div');
                portraitWrapper.className = 'tw-portrait-slot';
                portraitWrapper.innerHTML = unit.portrait;
                portraitWrapper.title = unit.name;
                button.appendChild(portraitWrapper);

                button.title = unit.name;

                button.addEventListener('click', () => {
                    if (selectedUnits.length >= max) return;
                    if (fleet && selectedUnits.length === 0 && !unit.isCapital) return;
                    if (fleet && selectedUnits.length > 0 && unit.isCapital) return;
                    selectedUnits.push(unit.id);
                    renderSelected();
                    renderResults();
                    unitSearch.focus();
                });
                unitResults.appendChild(button);
            });
    }

    function updateDatacrons() {
        const selectedSet = datacronFilter ? datacronFilter.value : '';
        if (!datacronList) return;

        let previousSet = null;
        datacronList.querySelectorAll('.tw-datacron-card').forEach((card) => {
            const visible = (!selectedSet || card.dataset.setId === selectedSet)
                && !proposedTeams.some((team) => team.datacronId === card.dataset.datacronId);
            card.style.display = visible ? 'block' : 'none';

            if (visible && !selectedSet && previousSet !== null && previousSet !== card.dataset.setId) {
                card.classList.add('tw-datacron-new-set');
            } else {
                card.classList.remove('tw-datacron-new-set');
            }

            if (visible) {
                previousSet = card.dataset.setId;
            }
        });
    }

    if (datacronList) {
        datacronList.querySelectorAll('.tw-datacron-card').forEach((card) => {
            card.addEventListener('click', () => {
                datacronList.querySelectorAll('.tw-datacron-card').forEach((item) => item.classList.remove('selected'));
                card.classList.add('selected');
                datacronIdInput.value = card.dataset.datacronId;
                renderSelected();
            });
        });
    }

    if (datacronFilter) {
        datacronFilter.addEventListener('change', updateDatacrons);
    }

    function updateZoneCounts() {
        const baseCounts = <?php echo json_encode($zone_team_counts); ?>;

        zoneSelect.querySelectorAll('option').forEach((option) => {
            const zone = option.value;
            const proposedCount = proposedTeams.filter((team) => team.zone === zone).length;
            option.textContent = zone + ' (' + ((baseCounts[zone] || 0) + proposedCount) + ')';
        });
    }

    function getZoneCard(zone) {
        let card = zoneTeamsContainer.querySelector('[data-tw-zone="' + zone + '"]');
        if (card) return card;

        card = document.createElement('div');
        card.className = 'card tw-zone';
        card.dataset.twZone = zone;

        const header = document.createElement('div');
        header.className = 'tw-zone-header';

        const title = document.createElement('h4');
        title.textContent = zone;
        header.appendChild(title);

        const command = document.createElement('span');
        command.className = 'tw-zone-command';
        command.textContent = twZoneCommands[zone] || '';
        if (command.textContent) header.appendChild(command);

        card.appendChild(header);
        zoneTeamsContainer.appendChild(card);
        return card;
    }

    function renderProposedTeams() {
        proposedTeams.forEach((team) => {
            if (team.element && team.element.isConnected) return;

            const zoneCard = getZoneCard(team.zone);
            const teamElement = document.createElement('div');
            teamElement.className = 'tw-team proposed';
            teamElement.dataset.proposedId = team.id;

            const header = document.createElement('div');
            header.className = 'tw-team-proposed-header';

            const label = document.createElement('span');
            label.textContent = 'Proposed team';
            header.appendChild(label);

            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'tw-team-delete';
            remove.textContent = 'Delete';
            remove.title = 'Delete proposed team';
            remove.addEventListener('click', () => deleteProposedTeam(team.id));
            header.appendChild(remove);

            teamElement.appendChild(header);

            const portraits = document.createElement('div');
            portraits.className = 'tw-team-portraits';

            team.units.forEach((unitId, index) => {
                const unit = twUnits.find((entry) => entry.id === unitId);
                if (!unit) return;

                const portrait = document.createElement('div');
                portrait.innerHTML = unit.portrait;
                portrait.title = unit.name;

                // Fleet reinforcements are cells 4-7 in My TW teams and
                // use the same smaller portrait treatment there.
                if ((team.zone === 'F1' || team.zone === 'F2') && index >= 4) {
                    portrait.classList.add('tw-fleet-reinforcement');
                }

                portraits.appendChild(portrait);
            });

            if (team.datacronId && twDatacrons[team.datacronId]) {
                const datacron = document.createElement('div');
                datacron.innerHTML = twDatacrons[team.datacronId];
                portraits.appendChild(datacron);
            }

            teamElement.appendChild(portraits);
            zoneCard.appendChild(teamElement);
            team.element = teamElement;
        });

        if (noTeamsMessage) {
            noTeamsMessage.style.display = zoneTeamsContainer.querySelector('.tw-team')
                ? 'none'
                : 'block';
        }

        pushProposedButton.style.display = proposedTeams.length > 0 ? 'block' : 'none';
        updateZoneCounts();
    }

    function deleteProposedTeam(teamId) {
        const index = proposedTeams.findIndex((team) => team.id === teamId);
        if (index < 0) return;

        const team = proposedTeams[index];
        const zone = team.zone;
        if (team.element) team.element.remove();
        proposedTeams.splice(index, 1);

        const zoneCard = zoneTeamsContainer.querySelector('[data-tw-zone="' + zone + '"]');
        if (zoneCard && !zoneCard.querySelector('.tw-team')) {
            zoneCard.remove();
        }

        renderProposedTeams();
        renderResults();
        updateDatacrons();
    }

    function createProposedTeam() {
        const fleet = fleetZone();
        const max = fleet ? 8 : 5;

        if (selectedUnits.length === 0 || selectedUnits.length > max) return;

        const team = {
            id: (window.crypto && crypto.randomUUID)
                ? crypto.randomUUID()
                : String(Date.now()) + '-' + Math.random(),
            zone: zoneSelect.value,
            units: [...selectedUnits],
            datacronId: fleet ? '' : (datacronIdInput.value || ''),
            element: null
        };

        proposedTeams.push(team);

        selectedUnits = [];
        datacronIdInput.value = '';

        if (datacronList) {
            datacronList.querySelectorAll('.tw-datacron-card')
                .forEach((item) => item.classList.remove('selected'));
        }

        renderSelected();
        renderResults();
        updateDatacrons();
        renderProposedTeams();
    }

    function pushProposedTeams() {
        if (proposedTeams.length === 0) return;

        alert('Pushing proposed teams to the game is not implemented yet.');
    }

    function updateCreator(previousFleet) {
        const fleet = fleetZone();
        const fleetStatusChanged = previousFleet !== undefined && previousFleet !== fleet;

        // Only reset the current selection when switching between fleet and
        // non-fleet zones. Switching between zones of the same type keeps it.
        if (fleetStatusChanged) {
            selectedUnits = [];
            datacronIdInput.value = '';

            if (datacronList) {
                datacronList.querySelectorAll('.tw-datacron-card')
                    .forEach((item) => item.classList.remove('selected'));
            }
        }

        datacronSelector.style.display = fleet ? 'none' : 'block';
        zoneCommandCreator.textContent = twZoneCommands[zoneSelect.value] || '';
        creatorLimit.textContent = fleet
            ? 'Fleet: select 1 capital ship, up to 3 line-up ships, then up to 4 reinforcements.'
            : 'Non-fleet: select up to 5 characters.';
        selectedUnits = selectedUnits.filter((unitId) => {
            const unit = twUnits.find((entry) => entry.id === unitId);
            return unit && (fleet ? unit.isShip : !unit.isShip);
        });
        if (selectedUnits.length > (fleet ? 8 : 5)) {
            selectedUnits.length = fleet ? 8 : 5;
        }
        renderSelected();
        renderResults();
        updateDatacrons();
    }

    let previousFleetStatus = fleetZone();

    createTeamButton.addEventListener('click', createProposedTeam);
    pushProposedButton.addEventListener('click', pushProposedTeams);

    zoneSelect.addEventListener('change', () => {
        const currentFleetStatus = fleetZone();
        updateCreator(previousFleetStatus);
        previousFleetStatus = currentFleetStatus;
    });
    unitSearch.addEventListener('input', renderResults);
    updateCreator();
    updateZoneCounts();
    renderProposedTeams();
}
</script>
</body>
<?php include 'sitefooter.php'; ?>
</html>

