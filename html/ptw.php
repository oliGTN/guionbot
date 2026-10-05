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

$dict_units = [];
$dict_units_file = __DIR__ . '/../DATA/unitsList_dict.json';
if (is_readable($dict_units_file)) {
    $dict_units = json_decode(file_get_contents($dict_units_file), true) ?: [];
}

$datacron_icons = load_datacron_icons($conn_guionbot);

$tw_zones = ['B1', 'T1', 'B2', 'T2', 'B3', 'T3', 'B4', 'T4', 'F1', 'F2'];
$player_datacrons = [];
if ($tw) {
    try {
        $stmt = $conn_guionbot->prepare(
            "SELECT id, setId, focused, level_3, level_6, level_9, level_12, level_15
             FROM datacrons
             WHERE allyCode = :allycode
             ORDER BY setId DESC, id"
        );
        $stmt->execute([':allycode' => $allycode]);
        $player_datacrons = $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (PDOException $e) {
        error_log('Error fetching player datacrons: ' . $e->getMessage());
    }
}

$team_creation_error = null;
$team_created = isset($_GET['created']) && $_GET['created'] === '1';

if ($_SERVER['REQUEST_METHOD'] === 'POST' && $tw && ($isGuildMate || $isAdmin)) {
    require_csrf_token();

    $zone_name = $_POST['zone_name'] ?? '';
    $units = json_decode($_POST['units'] ?? '[]', true);
    $datacron_id = $_POST['datacron_id'] ?? '';
    $is_fleet = in_array($zone_name, ['F1', 'F2'], true);
    $max_units = $is_fleet ? 8 : 5;

    if (!is_array($units)) {
        $units = [];
    }

    $validated_units = [];
    foreach ($units as $unit_id) {
        if (is_string($unit_id) && isset($dict_units[$unit_id])
            && !in_array($unit_id, $validated_units, true)) {
            $validated_units[] = $unit_id;
        }
    }

    $valid_team = in_array($zone_name, $tw_zones, true)
        && count($validated_units) > 0
        && count($validated_units) <= $max_units;

    if ($valid_team && !$is_fleet) {
        foreach ($validated_units as $unit_id) {
            if ((int) ($dict_units[$unit_id]['combatType'] ?? 1) === 2) {
                $valid_team = false;
                break;
            }
        }
    }

    if ($valid_team && $is_fleet) {
        $valid_team = (int) ($dict_units[$validated_units[0]]['combatType'] ?? 1) === 2
            && strpos($validated_units[0], 'CAPITAL') === 0;
        foreach (array_slice($validated_units, 1) as $unit_id) {
            if ((int) ($dict_units[$unit_id]['combatType'] ?? 1) !== 2
                || strpos($unit_id, 'CAPITAL') === 0) {
                $valid_team = false;
                break;
            }
        }
    }

    if ($valid_team && !$is_fleet && $datacron_id !== '') {
        $valid_datacron = false;
        foreach ($player_datacrons as $datacron) {
            if ((string) $datacron['id'] === $datacron_id) {
                $valid_datacron = true;
                break;
            }
        }
        if (!$valid_datacron) {
            $team_creation_error = 'Invalid datacron selection.';
        }
    }

    if (!$valid_team && $team_creation_error === null) {
        $team_creation_error = 'Invalid team composition for the selected zone.';
    }

    if ($team_creation_error === null) {
        try {
            $new_squad_id = bin2hex(random_bytes(16));
            $conn_guionbot->beginTransaction();

            $stmt = $conn_guionbot->prepare(
                "INSERT INTO tw_squads
                    (id, tw_id, side, zone_name, player_name, is_beaten, fights, gp, datacron_id)
                 VALUES
                    (:id, :tw_id, 'home', :zone_name, :player_name, 0, 0, 0, :datacron_id)"
            );
            $stmt->execute([
                ':id' => $new_squad_id,
                ':tw_id' => $tw_id,
                ':zone_name' => $zone_name,
                ':player_name' => $player['name'],
                ':datacron_id' => (!$is_fleet && $datacron_id !== '') ? $datacron_id : null,
            ]);

            $stmt = $conn_guionbot->prepare(
                "INSERT INTO tw_squad_cells
                    (tw_id, squad_id, defId, cellIndex, level, tier, unitRelicTier, zetaCount, omicronCount)
                 VALUES
                    (:tw_id, :squad_id, :def_id, :cell_index, 0, 0, 2, 0, 0)"
            );
            foreach ($validated_units as $cell_index => $unit_id) {
                $stmt->execute([
                    ':tw_id' => $tw_id,
                    ':squad_id' => $new_squad_id,
                    ':def_id' => $unit_id . ':SEVEN_STAR',
                    ':cell_index' => $cell_index,
                ]);
            }

            $conn_guionbot->commit();
            header('Location: ptw.php?ac=' . rawurlencode($allycode) . '&created=1');
            exit();
        } catch (PDOException $e) {
            if ($conn_guionbot->inTransaction()) {
                $conn_guionbot->rollBack();
            }
            error_log('Error creating player TW team: ' . $e->getMessage());
            $team_creation_error = 'Unable to create the team.';
        }
    }
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
            gap: 2rem;
            min-height: 90px;
            white-space: nowrap;
        }

        .tw-team-portraits > div {
            flex: 0 0 auto;
        }

        .tw-team-creator {
            display: grid;
            gap: 1rem;
        }

        .tw-selected-units {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            min-height: 100px;
            padding: 0.75rem;
            border: 1px solid #ccc;
            border-radius: 4px;
        }

        .tw-selected-unit {
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            max-width: 120px;
            text-align: center;
        }

        .tw-selected-unit img {
            width: 100px;
            height: 100px;
            object-fit: contain;
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
            padding: 0.25rem;
            width: 80px;
            height: 80px;
        }

        .tw-unit-result img {
            width: 70px;
            height: 70px;
            object-fit: contain;
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
            width: 90px;
            min-height: 90px;
            border: 2px solid transparent;
            border-radius: 6px;
            background: none;
            padding: 2px;
            text-align: center;
        }

        .tw-datacron-card.selected {
            border-color: #333;
        }

        .tw-datacron-card img {
            width: 70px;
            height: 70px;
            object-fit: contain;
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

                <div class="card tw-team-creator" id="create-team">
                    <h3>Create a new TW team</h3>
<?php if ($team_created): ?>
                    <div><b>Team created successfully.</b></div>
<?php endif; ?>
<?php if ($team_creation_error !== null): ?>
                    <div class="tw-creator-error"><?php echo htmlspecialchars($team_creation_error, ENT_QUOTES, 'UTF-8'); ?></div>
<?php endif; ?>
                    <form method="post" id="tw-team-form">
                        <input type="hidden" name="csrf_token" value="<?php echo htmlspecialchars(csrf_token(), ENT_QUOTES, 'UTF-8'); ?>">
                        <input type="hidden" name="units" id="tw-selected-units-input" value="[]">

                        <label for="tw-zone-select"><b>Zone</b></label>
                        <select id="tw-zone-select" name="zone_name">
<?php foreach ($tw_zones as $zone): ?>
                            <option value="<?php echo htmlspecialchars($zone, ENT_QUOTES, 'UTF-8'); ?>"><?php echo htmlspecialchars($zone, ENT_QUOTES, 'UTF-8'); ?></option>
<?php endforeach; ?>
                        </select>

                        <div id="tw-zone-command-creator" class="tw-zone-command-creator"></div>

                        <div class="tw-unit-picker">
                            <div>
                                <b>Selected units</b>
                                <div id="tw-selected-units" class="tw-selected-units"></div>
                            </div>
                            <div>
                                <label for="tw-unit-search"><b>Find a character or ship</b></label>
                                <input type="search" id="tw-unit-search" class="tw-unit-search" placeholder="Type a unit name..." autocomplete="off">
                                <div id="tw-unit-results" class="tw-unit-results"></div>
                            </div>
                        </div>

                        <div id="tw-datacron-selector">
                            <label for="tw-datacron-select"><b>Datacron</b></label>
                            <select id="tw-datacron-select" name="datacron_id">
                                <option value="">No datacron</option>
<?php foreach ($player_datacrons as $datacron): ?>
                                <option value="<?php echo htmlspecialchars($datacron['id'], ENT_QUOTES, 'UTF-8'); ?>">
                                    Set <?php echo htmlspecialchars($datacron['setId'], ENT_QUOTES, 'UTF-8'); ?><?php echo !empty($datacron['focused']) ? ' (focused)' : ''; ?>
                                </option>
<?php endforeach; ?>
                            </select>
                        </div>

                        <div id="tw-creator-limit"></div>
                        <button type="submit">Create team</button>
                    </form>
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
const twUnits = <?php
$creator_units = [];
foreach ($dict_units as $unit_id => $unit) {
    if (isset($unit['name'])) {
        $creator_units[] = [
            'id' => $unit_id,
            'name' => $unit['name'],
            'isShip' => (int) ($unit['combatType'] ?? 1) === 2,
            'isCapital' => strpos($unit_id, 'CAPITAL') === 0,
        ];
    }
}
echo json_encode($creator_units, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT);
?>;

const twZoneCommands = <?php
$creator_zone_commands = [];
foreach ($tw_zones as $zone) {
    $creator_zone_commands[$zone] = $zones['home'][$zone]['commandMsg'] ?? '';
}
echo json_encode($creator_zone_commands, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT);
?>;

const zoneSelect = document.getElementById('tw-zone-select');
const unitSearch = document.getElementById('tw-unit-search');
const unitResults = document.getElementById('tw-unit-results');
const selectedUnitsContainer = document.getElementById('tw-selected-units');
const selectedUnitsInput = document.getElementById('tw-selected-units-input');
const datacronSelector = document.getElementById('tw-datacron-selector');
const datacronFilter = document.getElementById('tw-datacron-filter');
const datacronIdInput = document.getElementById('tw-datacron-id');
const datacronList = document.getElementById('tw-datacron-list');
const zoneCommandCreator = document.getElementById('tw-zone-command-creator');
const creatorLimit = document.getElementById('tw-creator-limit');

if (zoneSelect) {
    let selectedUnits = [];

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

            const portrait = document.createElement('img');
            portrait.src = 'IMAGES/CHARACTERS/' + encodeURIComponent(unit.id) + '.png';
            portrait.alt = unit.name;
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
        selectedUnitsInput.value = JSON.stringify(selectedUnits);
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
            .filter((unit) => !fleet || (selectedUnits.length === 0 ? unit.isCapital : !unit.isCapital))
            .slice(0, 100)
            .forEach((unit) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'tw-unit-result';

                const portrait = document.createElement('img');
                portrait.src = 'IMAGES/CHARACTERS/' + encodeURIComponent(unit.id) + '.png';
                portrait.alt = unit.name;
                portrait.title = unit.name;
                button.appendChild(portrait);
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
        datacronList.querySelectorAll('.tw-datacron-card').forEach((card) => {
            card.style.display = !selectedSet || card.dataset.setId === selectedSet ? '' : 'none';
        });
    }

    if (datacronList) {
        datacronList.querySelectorAll('.tw-datacron-card').forEach((card) => {
            card.addEventListener('click', () => {
                datacronList.querySelectorAll('.tw-datacron-card').forEach((item) => item.classList.remove('selected'));
                card.classList.add('selected');
                datacronIdInput.value = card.dataset.datacronId;
            });
        });
    }

    if (datacronFilter) {
        datacronFilter.addEventListener('change', updateDatacrons);
    }

    function updateCreator() {
        const fleet = fleetZone();
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

    zoneSelect.addEventListener('change', updateCreator);
    unitSearch.addEventListener('input', renderResults);
    updateCreator();
}
</script>
</body>
<?php include 'sitefooter.php'; ?>
</html>

