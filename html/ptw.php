<?php
$ptw_request_started_at = microtime(true);
$ptw_stage_started_at = $ptw_request_started_at;
$ptw_timings = [];
$ptw_cache_stats = ['hits' => 0, 'misses' => 0];
$ptw_mark = function ($stage, $count = null) use (&$ptw_stage_started_at, &$ptw_timings) {
    $now = microtime(true);
    $ptw_timings[$stage] = round(($now - $ptw_stage_started_at) * 1000, 1);
    $ptw_stage_started_at = $now;
    if ($count !== null) $ptw_timings[$stage . '_count'] = $count;
};
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

if (empty($_SESSION['ptw_push_csrf']) || !is_string($_SESSION['ptw_push_csrf'])) {
    $_SESSION['ptw_push_csrf'] = bin2hex(random_bytes(32));
}

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
$ptw_mark('pdata');

if (($_GET['action'] ?? '') === 'push_proposed_teams' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
    header('Content-Type: application/x-ndjson; charset=utf-8');
    header('Cache-Control: no-cache, no-store, must-revalidate');
    header('X-Accel-Buffering: no');
    ini_set('output_buffering', 'off');
    ini_set('zlib.output_compression', '0');
    ob_implicit_flush(true);
    while (ob_get_level() > 0) { ob_end_flush(); }
    set_time_limit(300);
    $respond = function ($status, $payload) {
        http_response_code($status);
        echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
        exit();
    };
    if (empty($_SESSION['user_id']) || !$isMyAllycodeConfirmed) {
        $respond(403, ['err_code' => 403, 'err_txt' => 'This allyCode is not linked and confirmed for your Discord account.']);
    }
    $rawPayload = file_get_contents('php://input');
    if (!is_string($rawPayload) || strlen($rawPayload) > 65536) {
        $respond(400, ['err_code' => 400, 'err_txt' => 'Invalid request payload.']);
    }
    $payload = json_decode($rawPayload, true);
    if (!is_array($payload)) $respond(400, ['err_code' => 400, 'err_txt' => 'Invalid JSON payload.']);
    $csrf = $payload['csrf'] ?? '';
    if (!is_string($csrf) || empty($_SESSION['ptw_push_csrf']) || !hash_equals($_SESSION['ptw_push_csrf'], $csrf)) {
        $respond(403, ['err_code' => 403, 'err_txt' => 'Invalid security token. Reload the page and try again.']);
    }
    $teams = $payload['teams'] ?? null;
    $validZones = ['B1', 'T1', 'B2', 'T2', 'B3', 'T3', 'B4', 'T4', 'F1', 'F2'];
    if (!is_array($teams) || count($teams) < 1 || count($teams) > 50) {
        $respond(400, ['err_code' => 400, 'err_txt' => 'Select between 1 and 50 proposed teams.']);
    }
    $validatedTeams = [];
    foreach ($teams as $team) {
        if (!is_array($team)) $respond(400, ['err_code' => 400, 'err_txt' => 'Invalid proposed team.']);
        $zone = $team['zone'] ?? '';
        $units = $team['units'] ?? null;
        $datacronId = $team['datacronId'] ?? '';
        if ($datacronId === null) {
            $datacronId = '';
        }
        if (!is_string($zone) || !in_array($zone, $validZones, true) || !is_array($units) || count($units) < 1
            || count($units) > (in_array($zone, ['F1', 'F2'], true) ? 8 : 5)) {
            $respond(400, ['err_code' => 400, 'err_txt' => 'Invalid zone or unit count in proposed team.']);
        }
        // SWGOH datacron IDs are 16-byte URL-safe Base64 values (22 chars, no padding).
        if (!is_string($datacronId) || ($datacronId !== '' && !preg_match('/^[A-Za-z0-9_-]{22}$/', $datacronId))) {
            $respond(400, ['err_code' => 400, 'err_txt' => 'Invalid datacron ID in proposed team.']);
        }
        if (in_array($zone, ['F1', 'F2'], true) && $datacronId !== '') {
            $respond(400, ['err_code' => 400, 'err_txt' => 'Datacrons cannot be deployed with fleet teams.']);
        }
        $seenUnits = [];
        foreach ($units as $unitId) {
            if (!is_string($unitId) || !preg_match('/^[A-Za-z0-9_-]{1,64}$/', $unitId) || isset($seenUnits[$unitId])) {
                $respond(400, ['err_code' => 400, 'err_txt' => 'Invalid or duplicate unit in proposed team.']);
            }
            $seenUnits[$unitId] = true;
        }
        $validatedTeams[] = ['zone' => $zone, 'units' => array_values($units), 'datacronId' => $datacronId];
    }
    $tokenFile = '/home/pi/GuionBot/SERVER_SECRETS/web_commands.token';
    if (!is_readable($tokenFile)) {
        error_log('PTW push teams: web commands token file is unreadable.');
        $respond(503, ['err_code' => 503, 'err_txt' => 'Web commands service is not configured.']);
    }
    $token = trim(file_get_contents($tokenFile));
    if ($token === '') $respond(503, ['err_code' => 503, 'err_txt' => 'Web commands service is not configured.']);
    $requestPayload = json_encode([
        'guild_id' => (string)($player['guild_id'] ?? ''),
        'allyCode' => (string)$allycode,
        'teams' => $validatedTeams,
    ], JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
    $ch = curl_init('http://127.0.0.1:9000/DeployTWTeams');
    $streamed = false;
    curl_setopt_array($ch, [
        CURLOPT_POST => true, CURLOPT_RETURNTRANSFER => false,
        CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'Authorization: Bearer ' . $token],
        CURLOPT_POSTFIELDS => $requestPayload, CURLOPT_CONNECTTIMEOUT => 2, CURLOPT_TIMEOUT => 300,
        CURLOPT_WRITEFUNCTION => function ($curl, $chunk) use (&$streamed) {
            $streamed = true;
            echo $chunk;
            flush();
            return strlen($chunk);
        },
    ]);
    $curlResult = curl_exec($ch);
    $curlError = curl_error($ch);
    curl_close($ch);
    if ($curlResult === false) {
        error_log('PTW push teams service connection error: ' . $curlError);
        if (!$streamed) {
            echo json_encode(['type' => 'error', 'err_code' => 502, 'err_txt' => 'Web commands service unavailable.']) . "\n";
            flush();
        }
    }

    // This request is an NDJSON streaming endpoint, not a page render.
    // Do not append the normal PTW HTML to the stream after cURL completes.
    exit();
}
include 'portrait.php';
$ptw_mark('portrait_include');

// Find the most recent TW recorded for the player's current guild.
$tw_id = null;
try {
    $query_started_at = microtime(true);
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
    $twvariables_started_at = microtime(true);
    include 'twvariables.php';
}
$ptw_mark('twvariables');

// Load all recorded TWs for the player's guild. The current/latest TW is
// intentionally omitted from the import selector and historical team list.
$tw_history_options = [];
$previous_tw_ids = [];
try {
    $query_started_at = microtime(true);
    $history_stmt = $conn_guionbot->prepare(
        "SELECT id, start_date FROM tw_history
         WHERE guild_id = :guild_id
         ORDER BY start_date DESC"
    );
    $history_stmt->execute([':guild_id' => $player['guild_id']]);
    $all_tw_history = $history_stmt->fetchAll(PDO::FETCH_ASSOC);
    $tw_history_options = array_slice($all_tw_history, 1);
    $previous_tw_ids = array_map('intval', array_column($tw_history_options, 'id'));
} catch (PDOException $e) {
    error_log('Error fetching TW history options: ' . $e->getMessage());
}

// Get the player's squads for this TW.
$squad_list = [];
if ($tw) {
    try {
        $query_started_at = microtime(true);
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

$dict_units_file = __DIR__ . '/../DATA/unitsList_dict.json';
$dict_load_started_at = microtime(true);
$dict_units = load_cached_json_file($dict_units_file, function ($source) {
    $light = [];
    foreach ($source as $def_id => $unit) {
        $light[$def_id] = [
            'name' => $unit['name'] ?? $def_id,
            'forceAlignment' => $unit['forceAlignment'] ?? 0,
            'combatType' => $unit['combatType'] ?? 1,
            'categoryId' => $unit['categoryId'] ?? [],
        ];
    }
    return $light;
});
$dict_units = is_array($dict_units) ? $dict_units : [];
$ptw_timings['unit_dictionary_cached_load_ms'] = round((microtime(true) - $dict_load_started_at) * 1000, 1);

$dict_capas_file = __DIR__ . '/../DATA/unit_capa_list.json';
$dict_capas_started_at = microtime(true);
$dict_capas = load_cached_json_file($dict_capas_file);
$dict_capas = is_array($dict_capas) ? $dict_capas : [];
$ptw_timings['capa_dictionary_cached_load_ms'] = round((microtime(true) - $dict_capas_started_at) * 1000, 1);

$dict_abilities_file = __DIR__ . '/../DATA/abilityList_dict.json';
$dict_abilities_started_at = microtime(true);
$dict_abilities = load_cached_json_file($dict_abilities_file);
$dict_abilities = is_array($dict_abilities) ? $dict_abilities : [];
$ptw_timings['ability_dictionary_cached_load_ms'] = round((microtime(true) - $dict_abilities_started_at) * 1000, 1);

$icons_started_at = microtime(true);
$datacron_icons = load_datacron_icons($conn_guionbot);
$ptw_timings['datacron_icons_ms'] = round((microtime(true) - $icons_started_at) * 1000, 1);
$categories_started_at = microtime(true);
$dict_categories = load_categories();
$ptw_timings['categories_dictionary_ms'] = round((microtime(true) - $categories_started_at) * 1000, 1);
$localization_started_at = microtime(true);
$FRE_FR = load_loc('FRE_FR');
$ptw_timings['localization_dictionary_ms'] = round((microtime(true) - $localization_started_at) * 1000, 1);
$ptw_mark('other_dictionaries');

// Historical TW imports are loaded on demand. This endpoint deliberately runs
// before roster and current-datacron processing so it does not repeat that work.
if (($_GET['action'] ?? '') === 'load_tw_history' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'GET') {
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    $respondHistory = function ($status, $payload) {
        http_response_code($status);
        echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
        exit();
    };

    if (empty($_SESSION['user_id']) || (!$isGuildMate && !$isAdmin)) {
        $respondHistory(403, ['error' => 'You are not allowed to access this Territory War.']);
    }

    $historyTwId = filter_input(INPUT_GET, 'tw_id', FILTER_VALIDATE_INT);
    if (!$historyTwId || $historyTwId < 1) {
        $respondHistory(400, ['error' => 'Invalid Territory War.']);
    }

    $historyLoadStartedAt = microtime(true);
    try {
        $checkHistoryStmt = $conn_guionbot->prepare(
            "SELECT id FROM tw_history WHERE id = :tw_id AND guild_id = :guild_id LIMIT 1"
        );
        $checkHistoryStmt->execute([
            ':tw_id' => $historyTwId,
            ':guild_id' => $player['guild_id'],
        ]);
        if (!$checkHistoryStmt->fetchColumn()) {
            $respondHistory(404, ['error' => 'Territory War not found.']);
        }

        $importStmt = $conn_guionbot->prepare(
            "SELECT tw_squads.id AS squad_id, tw_squads.tw_id, tw_squads.zone_name,
                    tw_squad_cells.defId, tw_squad_cells.cellIndex,
                    tw_squad_cells.level, tw_squad_cells.tier,
                    tw_squad_cells.unitRelicTier, tw_squad_cells.zetaCount,
                    tw_squad_cells.omicronCount,
                    datacrons.id AS datacron_id, datacrons.setId AS datacron_setId,
                    datacrons.focused AS datacron_focused,
                    datacrons.level_3 AS datacron_level_3, datacrons.level_6 AS datacron_level_6,
                    datacrons.level_9 AS datacron_level_9, datacrons.level_12 AS datacron_level_12,
                    datacrons.level_15 AS datacron_level_15
             FROM tw_squads
             JOIN tw_squad_cells ON tw_squad_cells.squad_id = tw_squads.id
             LEFT JOIN datacrons ON datacrons.id = tw_squads.datacron_id
             WHERE tw_squads.tw_id = :tw_id
               AND tw_squads.player_name = :player_name
             ORDER BY FIELD(tw_squads.zone_name, 'B1','T1','B2','T2','B3','T3','B4','T4','F1','F2'),
                      tw_squads.id, tw_squad_cells.cellIndex"
        );
        $importStmt->execute([
            ':tw_id' => $historyTwId,
            ':player_name' => $player['name'],
        ]);
        $importSquadList = $importStmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (PDOException $e) {
        error_log('Error fetching historical TW squads: ' . $e->getMessage());
        $respondHistory(500, ['error' => 'Unable to load historical teams.']);
    }

    $rarityValues = [
        'ONE_STAR' => 1, 'TWO_STAR' => 2, 'THREE_STAR' => 3,
        'FOUR_STAR' => 4, 'FIVE_STAR' => 5, 'SIX_STAR' => 6, 'SEVEN_STAR' => 7,
    ];
    $importTeamsByZone = [];
    foreach ($importSquadList as $cell) {
        $sid = (string) $cell['squad_id'];
        $zone = (string) $cell['zone_name'];
        if (!isset($importTeamsByZone[$zone][$sid])) {
            $importTeamsByZone[$zone][$sid] = [
                'zone' => $zone,
                'units' => [],
                'unitData' => [],
                'datacronId' => (string) ($cell['datacron_id'] ?? ''),
                'datacronHtml' => '',
                'datacron' => !empty($cell['datacron_id']) ? [
                    'id' => $cell['datacron_id'], 'setId' => $cell['datacron_setId'],
                    'focused' => $cell['datacron_focused'], 'level_3' => $cell['datacron_level_3'],
                    'level_6' => $cell['datacron_level_6'], 'level_9' => $cell['datacron_level_9'],
                    'level_12' => $cell['datacron_level_12'], 'level_15' => $cell['datacron_level_15'],
                ] : null,
            ];
        }

        $parts = explode(':', (string) $cell['defId']);
        $shortId = (string) $parts[0];
        $unitInfo = $dict_units[$shortId] ?? [];
        $isShip = (int) ($unitInfo['combatType'] ?? 1) === 2;
        $unitName = $unitInfo['name'] ?? $shortId;
        $portraitName = isset($unitInfo['name']) ? $unitInfo['name'] . 'XX' : $shortId;

        ob_start();
        display_portrait(
            $shortId,
            $unitInfo['forceAlignment'] ?? 0,
            $rarityValues[$parts[1] ?? 'SEVEN_STAR'] ?? 7,
            $isShip ? 0 : (int) $cell['tier'],
            (int) $cell['unitRelicTier'],
            (int) $cell['zetaCount'],
            (int) $cell['omicronCount'],
            $isShip,
            $portraitName,
            $isShip && (int) $cell['cellIndex'] >= 4
        );
        $portraitHtml = ob_get_clean();

        $teamRef =& $importTeamsByZone[$zone][$sid];
        $teamRef['units'][] = $shortId;
        if (!empty($cell['datacron_id']) && $teamRef['datacronHtml'] === '') {
            ob_start();
            display_datacron($teamRef['datacron'], $datacron_icons, $dict_categories, $dict_abilities, $FRE_FR, true);
            $teamRef['datacronHtml'] = ob_get_clean();
        }
        $teamRef['unitData'][] = [
            'id' => $shortId,
            'portrait' => $portraitHtml,
            'name' => $unitName,
            'isShip' => $isShip,
        ];
        unset($teamRef);
    }

    ob_start();
    $twZones = ['B1', 'T1', 'B2', 'T2', 'B3', 'T3', 'B4', 'T4', 'F1', 'F2'];
    $hasTeams = false;
    foreach ($twZones as $importZone) {
        if (empty($importTeamsByZone[$importZone])) continue;
        $hasTeams = true;
        ?>
        <div class="card tw-zone">
            <div class="tw-zone-header">
                <h4><?php echo htmlspecialchars($importZone, ENT_QUOTES, 'UTF-8'); ?></h4>
                <span class="tw-zone-command"><?php echo htmlspecialchars($zones['home'][$importZone]['commandMsg'] ?? '', ENT_QUOTES, 'UTF-8'); ?></span>
            </div>
            <?php foreach ($importTeamsByZone[$importZone] as $importTeam): ?>
                <?php
                $teamPayload = json_encode([
                    'zone' => $importTeam['zone'],
                    'units' => $importTeam['units'],
                    'datacronId' => $importTeam['datacronId'],
                    'datacronHtml' => $importTeam['datacronHtml'],
                ], JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT);
                ?>
                <div class="tw-team">
                    <div class="tw-import-team-row">
                        <div class="tw-team-portraits">
                            <?php foreach ($importTeam['unitData'] as $unitIndex => $importUnit): ?>
                                <div data-unit-id="<?php echo htmlspecialchars($importUnit['id'], ENT_QUOTES, 'UTF-8'); ?>"
                                     data-base-title="<?php echo htmlspecialchars($importUnit['name'], ENT_QUOTES, 'UTF-8'); ?>"
                                     <?php echo ($importUnit['isShip'] && $unitIndex >= 4) ? 'class="tw-fleet-reinforcement"' : ''; ?>
                                     title="<?php echo htmlspecialchars($importUnit['name'], ENT_QUOTES, 'UTF-8'); ?>"><?php echo $importUnit['portrait']; ?></div>
                            <?php endforeach; ?>
                            <?php if ($importTeam['datacronId'] !== ''): ?>
                                <div class="tw-import-datacron" data-datacron-id="<?php echo htmlspecialchars($importTeam['datacronId'], ENT_QUOTES, 'UTF-8'); ?>"><?php echo $importTeam['datacronHtml']; ?></div>
                            <?php endif; ?>
                        </div>
                        <div class="tw-import-actions">
                            <button type="button" class="tw-add-team tw-import-add" data-team="<?php echo htmlspecialchars($teamPayload, ENT_QUOTES, 'UTF-8'); ?>">Add</button>
                            <button type="button" class="tw-add-team tw-import-add tw-import-add-in-zone" data-team="<?php echo htmlspecialchars($teamPayload, ENT_QUOTES, 'UTF-8'); ?>">Add in <?php echo htmlspecialchars($importTeam['zone'], ENT_QUOTES, 'UTF-8'); ?></button>
                        </div>
                    </div>
                </div>
            <?php endforeach; ?>
        </div>
        <?php
    }
    if (!$hasTeams) {
        echo '<p>No teams found for this player in this Territory War.</p>';
    }
    $historyHtml = ob_get_clean();
    error_log('PTW_HISTORY_LOAD_TIMING ' . json_encode([
        'tw_id' => $historyTwId,
        'squad_cells' => count($importSquadList),
        'teams' => array_sum(array_map('count', $importTeamsByZone)),
        'elapsed_ms' => round((microtime(true) - $historyLoadStartedAt) * 1000, 1),
        'html_bytes' => strlen($historyHtml),
        'peak_memory_mb' => round(memory_get_peak_usage(true) / 1048576, 1),
    ], JSON_UNESCAPED_SLASHES));
    $respondHistory(200, ['html' => $historyHtml, 'teamCount' => array_sum(array_map('count', $importTeamsByZone))]);
}

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
    $query_started_at = microtime(true);
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
                        WHEN rs.omicron_type = 'TW' AND rs.level > 0 THEN 1
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
    $roster_rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $roster_processing_started_at = microtime(true);
    $ptw_timings['roster_sql_ms'] = round(($roster_processing_started_at - $query_started_at) * 1000, 1);
    $ptw_timings['roster_rows'] = count($roster_rows);

    $roster_zeta_ms = 0.0;
    $roster_portrait_ms = 0.0;
    $roster_metadata_ms = 0.0;
    $roster_unit_build_ms = 0.0;
    $roster_zeta_count = 0;
    $roster_portrait_count = 0;
    $roster_metadata_count = 0;
    $roster_skipped_count = 0;

    foreach ($roster_rows as $roster_unit) {
        $def_id = (string) $roster_unit['defId'];

        if (!isset($dict_units[$def_id]) || isset($used_unit_ids[$def_id])) {
            $roster_skipped_count++;
            continue;
        }

        $zeta_count = 0;
        $zeta_started_at = microtime(true);
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
                } else if ($skill_name == 'GL')
                {
                    $zeta_count++;
                }
            }
        }

        $roster_zeta_ms += microtime(true) - $zeta_started_at;
        $roster_zeta_count++;

        // unit selector
        $portrait_started_at = microtime(true);
        ob_start();
        display_portrait(
            $def_id,
            (int) $roster_unit['forceAlignment'],
            max(1, min(7, (int) $roster_unit['rarity'])),
            (int) $roster_unit['gear'],
            (int) $roster_unit['relic_currentTier'],
            $zeta_count,
            (int) $roster_unit['omicron_count'],
            (int) $roster_unit['combatType'] === 2,
            $dict_units[$def_id]['name'] ?? $def_id
        );
        $portrait_html = ob_get_clean();
        $roster_portrait_ms += microtime(true) - $portrait_started_at;
        $roster_portrait_count++;

        $metadata_started_at = microtime(true);
        $search_metadata = [];
        foreach (($dict_units[$def_id]['categoryId'] ?? []) as $category_id) {
            if (
                isset($dict_categories[$category_id]['descKey'])
                && is_string($dict_categories[$category_id]['descKey'])
                && $dict_categories[$category_id]['descKey'] !== ''
            ) {
                $search_metadata[] = $dict_categories[$category_id]['descKey'];
            }
        }
        $search_metadata = array_values(array_unique($search_metadata));
        $roster_metadata_ms += microtime(true) - $metadata_started_at;
        $roster_metadata_count++;

        $unit_build_started_at = microtime(true);
        $roster_units[] = [
            'id' => $def_id,
            'name' => $dict_units[$def_id]['name'] ?? $def_id,
            'searchMetadata' => $search_metadata,
            'isShip' => (int) $roster_unit['combatType'] === 2,
            'isCapital' => strpos($def_id, 'CAPITAL') === 0,
            'portrait' => $portrait_html,
        ];
        $roster_unit_build_ms += microtime(true) - $unit_build_started_at;
    }

    $ptw_timings['roster_zeta_ms'] = round($roster_zeta_ms * 1000, 1);
    $ptw_timings['roster_zeta_count'] = $roster_zeta_count;
    $ptw_timings['roster_portrait_ms'] = round($roster_portrait_ms * 1000, 1);
    $ptw_timings['roster_portrait_count'] = $roster_portrait_count;
    $ptw_timings['roster_metadata_ms'] = round($roster_metadata_ms * 1000, 1);
    $ptw_timings['roster_metadata_count'] = $roster_metadata_count;
    $ptw_timings['roster_unit_build_ms'] = round($roster_unit_build_ms * 1000, 1);
    $ptw_timings['roster_skipped_count'] = $roster_skipped_count;
}

catch (PDOException $e) {
    error_log('Error fetching player roster for TW team creator: ' . $e->getMessage());
}
$ptw_mark('roster_processing', count($roster_units));

$player_datacrons = [];
if ($tw) {
    try {
        $query_started_at = microtime(true);
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

        // Keep the complete inventory separately: the selector above excludes
        // datacrons already deployed in this TW, but historical imports must
        // distinguish those from datacrons the player no longer owns.
        $inventory_stmt = $conn_guionbot->prepare(
            "SELECT id FROM datacrons WHERE allyCode = :allycode"
        );
        $inventory_stmt->execute([':allycode' => $allycode]);
        $player_datacron_ids = array_map('strval', $inventory_stmt->fetchAll(PDO::FETCH_COLUMN));
    } catch (PDOException $e) {
        error_log('Error fetching player datacrons: ' . $e->getMessage());
        $player_datacron_ids = [];
    }
} else {
    $player_datacron_ids = [];
}

$ptw_mark('datacron_queries', count($player_datacrons));
$player_datacron_html = [];
foreach ($player_datacrons as $datacron) {
    ob_start();
    display_datacron($datacron, $datacron_icons, $dict_categories, $dict_abilities, $FRE_FR, true);
    $player_datacron_html[(string) $datacron['id']] = ob_get_clean();
}

$ptw_mark('datacron_rendering', count($player_datacron_html));

$rarity_values = [
    'ONE_STAR' => 1,
    'TWO_STAR' => 2,
    'THREE_STAR' => 3,
    'FOUR_STAR' => 4,
    'FIVE_STAR' => 5,
    'SIX_STAR' => 6,
    'SEVEN_STAR' => 7,
];

$import_teams_by_tw = []; // Loaded asynchronously when the import tab is opened.
$ptw_mark('historical_teams_deferred', 0);
$ptw_timings['total_php_before_html_ms'] = round((microtime(true) - $ptw_request_started_at) * 1000, 1);
$ptw_timings['peak_memory_mb'] = round(memory_get_peak_usage(true) / 1048576, 1);
$ptw_timings['response_content_length_before_html'] = 0;
$ptw_timings['dictionary_cache_hits'] = $ptw_cache_stats['hits'];
$ptw_timings['dictionary_cache_misses'] = $ptw_cache_stats['misses'];
error_log('PTW_LOAD_TIMING ' . json_encode($ptw_timings, JSON_UNESCAPED_SLASHES));
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
        .tw-tabs { display: flex; gap: 0.5rem; margin: 1.25rem 0 0; flex-wrap: wrap; }
        .tw-tab { padding: 0.65rem 1rem; border: 1px solid #bbb; border-bottom: 0; border-radius: 5px 5px 0 0; cursor: pointer; background: #eee; color: inherit; }
        .tw-tab.active { background: #fff; font-weight: bold; border-color: #888; }
        .tw-tab-panel { border-top: 1px solid #888; padding-top: 1rem; }
        .tw-import-add { margin: 0; }
        .tw-import-actions { display: flex; flex-direction: column; align-items: stretch; gap: 0.35rem; flex: 0 0 auto; }
        .tw-import-team-row {
            display: flex;
            align-items: flex-start;
            gap: 0.5rem;
            width: max-content;
            min-width: 100%;
            box-sizing: border-box;
        }
        .tw-import-team-row .tw-team-portraits {
            flex: 0 0 auto;
            width: max-content;
            min-width: max-content;
        }
        .tw-import-actions {
            position: relative;
            z-index: 2;
        }
        .tw-shared-zone-controls { display: flex; flex-direction: column; align-items: flex-start; gap: 0.35rem; margin: 1rem 0 0.5rem; }
        .tw-inline-select { display: inline-flex; align-items: center; gap: 0.5rem; }
        .tw-inline-select label { margin: 0; white-space: nowrap; }
        .tw-inline-select select { width: auto; max-width: 100%; }
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
            width: max-content;
            min-width: 100%;
            box-sizing: border-box;
        }

        .tw-team-proposed-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 0.5rem;
            color: #b35a00;
            font-weight: bold;
        }
        .tw-proposed-team-row { display: flex; align-items: flex-start; gap: 0.75rem; width: max-content; min-width: 100%; }
        .tw-proposed-team-row .tw-team-portraits { flex: 0 0 auto; min-width: max-content; }
        .tw-team-actions { display: flex; flex-direction: column; align-items: stretch; gap: 0.35rem; flex: 0 0 auto; }
        .tw-team-edit { border: 0; border-radius: 4px; cursor: pointer; padding: 0.25rem 0.6rem; }
        .tw-import-unit-unavailable { position: relative; opacity: 0.7; }
        .tw-import-unit-unavailable::after {
            content: "";
            position: absolute;
            left: -12%;
            top: 50%;
            width: 124%;
            border-top: 4px solid #d00000;
            transform: rotate(-35deg);
            transform-origin: center;
            pointer-events: none;
            z-index: 10;
        }
        .tw-import-datacron {
            position: relative;
            display: inline-block;
        }
        .tw-import-datacron-unavailable::after {
            content: "";
            position: absolute;
            left: -12%;
            top: 50%;
            width: 124%;
            border-top: 4px solid #d00000;
            transform: rotate(-35deg);
            transform-origin: center;
            pointer-events: none;
            z-index: 10;
        }
        .tw-import-add:disabled { cursor: not-allowed; opacity: 0.45; }

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
            min-height: 120px;
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
            width: max-content;
            min-width: 120px;
            box-sizing: border-box;
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
            width: max-content;
            min-width: 100%;
            max-width: 100%;
            box-sizing: border-box;
        }

        /* On narrow screens, let the edit area grow to the full team width
           and scroll horizontally instead of squeezing the unit slots. */
        @media (max-width: 768px) {
            .tw-selected-team {
                width: max-content;
                min-width: 100%;
                max-width: none;
            }

            .tw-selected-units {
                flex: 0 0 auto;
            }
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
<style>
.tw-push-modal{display:none;position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.72);align-items:center;justify-content:center;padding:20px}
.tw-push-modal.visible{display:flex}
.tw-push-modal-content{width:min(440px,100%);background:var(--bs-body-bg,#fff);color:var(--bs-body-color,#222);border-radius:12px;padding:26px;box-shadow:0 12px 40px rgba(0,0,0,.35);text-align:center}
.tw-push-progress-track{height:18px;background:#dedede;border-radius:10px;overflow:hidden;margin:18px 0 10px}
.tw-push-progress-bar{height:100%;width:0;background:#28a745;transition:width .35s ease}
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
    $unit_name = $dict_units[$unit_short_id]['name'] ?? $unit_short_id;

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
        $unit_name,
        $unit_isShip && (int) $unit['cellIndex'] >= 4
    );
}
?>
<?php if (!empty($squad['datacron'])): ?>
                                <?php display_datacron($squad['datacron'], $datacron_icons, $dict_categories, $dict_abilities, $FRE_FR, true); ?>
<?php endif; ?>
                            </div>
                        </div>
<?php endforeach; ?>
                    </div>
<?php endforeach; ?>
<?php endif; ?>
                </div>

<?php if ((int) ($tw['currentRound'] ?? -1) === 0): ?>
                <button type="button" class="tw-push-proposed" id="tw-push-proposed" style="display:none" disabled>Push proposed teams to game</button>

                <div class="tw-shared-zone-controls">
                    <div class="tw-inline-select">
                        <label for="tw-zone-select"><b>Zone</b></label>
                        <select id="tw-zone-select">
<?php foreach ($tw_zones as $zone): ?>
                            <option value="<?php echo htmlspecialchars($zone, ENT_QUOTES, 'UTF-8'); ?>"><?php echo htmlspecialchars($zone, ENT_QUOTES, 'UTF-8'); ?> (<?php echo $zone_team_counts[$zone]; ?>)</option>
<?php endforeach; ?>
                        </select>
                    </div>
                    <div id="tw-zone-command-creator" class="tw-zone-command-creator"></div>
                </div>

                <div class="tw-tabs" role="tablist" aria-label="TW team tools">
                    <button type="button" class="tw-tab active" role="tab" aria-selected="true" aria-controls="tw-create-tab" id="tw-create-tab-button">Create a new TW team</button>
                    <button type="button" class="tw-tab" role="tab" aria-selected="false" aria-controls="tw-import-tab" id="tw-import-tab-button">Import previous TW team</button>
                </div>
                <section id="tw-create-tab" class="tw-tab-panel" role="tabpanel" aria-labelledby="tw-create-tab-button">
                <div class="card tw-team-creator" id="create-team">
                    <div id="tw-team-form">

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
                </section>

                <section id="tw-import-tab" class="tw-tab-panel" role="tabpanel" aria-labelledby="tw-import-tab-button" hidden>
                    <div class="card tw-team-creator">
                        <div class="tw-inline-select">
                            <label for="tw-history-select"><b>Previous Territory War</b></label>
                            <select id="tw-history-select">
<?php foreach ($tw_history_options as $history): ?>
                                <option value="<?php echo (int) $history['id']; ?>"><?php echo htmlspecialchars(substr((string) $history['start_date'], 0, 10), ENT_QUOTES, 'UTF-8'); ?></option>
<?php endforeach; ?>
                            </select>
                        </div>
                        <div id="tw-import-teams">
                            <p>Select a previous Territory War to load its teams.</p>
                        </div>
                    </div>
                </section>

            </div>
<?php endif; ?>
<?php endif; // Team creation/import is available only before the TW starts. ?>
<?php else: ?>
        You are not allowed to see TW data for this guild
<?php endif; //($isGuildMate||$isAdmin) ?>
        </div>

        <div class="site-cache" id="site-cache"></div>
    </div>
</div>
<script>
document.querySelectorAll('.tw-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tw-tab').forEach((item) => {
            const active = item === tab;
            item.classList.toggle('active', active);
            item.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        document.querySelectorAll('.tw-tab-panel').forEach((panel) => {
            panel.hidden = panel.id !== tab.getAttribute('aria-controls');
        });
        if (tab.getAttribute('aria-controls') === 'tw-import-tab' && historySelect) {
            loadHistoryTeams(historySelect.value);
        }
    });
});
const historySelect = document.getElementById('tw-history-select');
const historyTeamsContainer = document.getElementById('tw-import-teams');
const loadedHistoryTwIds = new Set();
const loadingHistoryTwIds = new Set();

async function loadHistoryTeams(twId) {
    if (!historyTeamsContainer || !twId || loadedHistoryTwIds.has(twId) || loadingHistoryTwIds.has(twId)) return;
    loadingHistoryTwIds.add(twId);
    historyTeamsContainer.innerHTML = '<p>Loading teams…</p>';
    try {
        const url = new URL(window.location.href);
        url.searchParams.set('action', 'load_tw_history');
        url.searchParams.set('tw_id', twId);
        const response = await fetch(url.toString(), {
            method: 'GET',
            credentials: 'same-origin',
            headers: { 'Accept': 'application/json' }
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Unable to load historical teams.');
        historyTeamsContainer.innerHTML = result.html || '<p>No teams found for this player in this Territory War.</p>';
        loadedHistoryTwIds.add(twId);
        document.dispatchEvent(new CustomEvent('tw-history-loaded'));
    } catch (error) {
        historyTeamsContainer.textContent = error.message || 'Unable to load historical teams.';
    } finally {
        loadingHistoryTwIds.delete(twId);
    }
}

if (historySelect) {
    historySelect.addEventListener('change', () => loadHistoryTeams(historySelect.value));
}
const twUnits = <?php echo json_encode($roster_units, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT); ?>;
const twDatacrons = <?php echo json_encode($player_datacron_html, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT); ?>;
const twPlayerDatacronIds = new Set(<?php echo json_encode($player_datacron_ids, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT); ?>);
const twZoneCommands = <?php
$creator_zone_commands = [];
foreach ($tw_zones as $zone) {
    $creator_zone_commands[$zone] = $zones['home'][$zone]['commandMsg'] ?? '';
}
echo json_encode($creator_zone_commands, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT);
?>;

const zoneTeamsContainer = document.getElementById('tw-zone-teams');
const pushProposedButton = document.getElementById('tw-push-proposed');
const pushCsrfToken = <?php echo json_encode($_SESSION['ptw_push_csrf'], JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_AMP | JSON_HEX_QUOT); ?>;
const canPushProposedTeams = <?php echo $isMyAllycodeConfirmed ? 'true' : 'false'; ?>;
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
    let selectedDatacronHtml = '';
    let proposedTeams = [];

    document.addEventListener('tw-history-loaded', refreshImportTeamAvailability);

    function refreshImportTeamAvailability() {
        // Units in the edit zone are released from their proposed team
        // and must be shown as available in historical imports.
        const unavailableIds = new Set();
        proposedTeams.forEach((team) => {
            (team.units || []).forEach((unitId) => unavailableIds.add(unitId));
        });

        document.querySelectorAll('#tw-import-teams').forEach((historyPanel) => {
            historyPanel.querySelectorAll('.tw-import-team-row').forEach((teamRow) => {
                const addButton = teamRow.querySelector('.tw-import-add');
                if (!addButton) return;

                let imported;
                try {
                    imported = JSON.parse(addButton.dataset.team || '{}');
                } catch (e) {
                    addButton.disabled = true;
                    return;
                }

                // A historical datacron that is no longer in the player's
                // inventory must not be imported with the team.
                if (imported.datacronId && !twPlayerDatacronIds.has(String(imported.datacronId))) {
                    imported.datacronId = '';
                    imported.datacronHtml = '';
                    addButton.dataset.team = JSON.stringify(imported);
                    const staleDatacron = teamRow.querySelector('.tw-import-datacron');
                    if (staleDatacron) staleDatacron.remove();
                }

                const missingIds = (imported.units || []).filter((unitId) =>
                    !twUnits.some((unit) => unit.id === unitId)
                );
                const conflictingIds = (imported.units || []).filter((unitId) =>
                    unavailableIds.has(unitId)
                );
                const datacronUnavailable = !!imported.datacronId && proposedTeams.some((team) =>
                    String(team.datacronId || '') === String(imported.datacronId)
                );
                const importedDatacron = teamRow.querySelector('.tw-import-datacron');
                if (importedDatacron) {
                    importedDatacron.classList.toggle('tw-import-datacron-unavailable', datacronUnavailable);
                    importedDatacron.title = datacronUnavailable
                        ? 'Datacron is already assigned to a proposed team'
                        : '';
                }
                const blockedIds = new Set([...missingIds, ...conflictingIds]);
                const availableIds = (imported.units || []).filter((unitId) =>
                    twUnits.some((unit) => unit.id === unitId) && !unavailableIds.has(unitId)
                );

                teamRow.querySelectorAll('[data-unit-id]').forEach((unitElement) => {
                    const unitId = unitElement.dataset.unitId;
                    const blocked = blockedIds.has(unitId);
                    unitElement.classList.toggle('tw-import-unit-unavailable', blocked);
                    if (blocked) {
                        unitElement.title = (unitElement.dataset.baseTitle || unitElement.title || unitId)
                            + ' — unavailable in the create-team unit selector';
                    } else if (unitElement.dataset.baseTitle) {
                        unitElement.title = unitElement.dataset.baseTitle;
                    }
                });

                // A partially available historical team can still be brought
                // into the creator for editing, using only its available units.
                const partiallyAvailable = blockedIds.size > 0 && availableIds.length > 0;
                addButton.disabled = (blockedIds.size > 0 && !partiallyAvailable) || datacronUnavailable;
                addButton.title = datacronUnavailable
                    ? 'Cannot add this team because its datacron is already assigned to a proposed team.'
                    : (partiallyAvailable
                        ? 'Import available characters into the team editor; unavailable characters will be skipped.'
                        : (blockedIds.size > 0
                            ? 'Cannot add this team because none of its characters are available.'
                            : ''));
            });
        });
    }

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
            const datacronHtml = datacronId ? (twDatacrons[datacronId] || selectedDatacronHtml) : '';
            if (datacronHtml) {
                const datacron = document.createElement('div');
                datacron.className = 'tw-selected-datacron-item';
                datacron.innerHTML = datacronHtml;

                const removeDatacron = document.createElement('button');
                removeDatacron.type = 'button';
                removeDatacron.textContent = '×';
                removeDatacron.title = 'Remove datacron';
                removeDatacron.addEventListener('click', () => {
                    datacronIdInput.value = '';
                    selectedDatacronHtml = '';
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
            .filter((unit) => {
                if (!search) return true;

                const searchableMetadata = Array.isArray(unit.searchMetadata)
                    ? unit.searchMetadata.join(' ')
                    : '';

                return (unit.name + ' ' + searchableMetadata)
                    .toLocaleLowerCase()
                    .includes(search);
            })
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
                && card.dataset.datacronId !== String(datacronIdInput.value || '')
                && !proposedTeams.some((team) => String(team.datacronId || '') === String(card.dataset.datacronId));
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
                // Do not allow selecting a datacron already assigned either
                // to another proposed team or to the team currently in edit.
                if (String(datacronIdInput.value || '') === String(card.dataset.datacronId)
                    || proposedTeams.some((team) => String(team.datacronId || '') === String(card.dataset.datacronId))) {
                    return;
                }
                datacronList.querySelectorAll('.tw-datacron-card').forEach((item) => item.classList.remove('selected'));
                card.classList.add('selected');
                datacronIdInput.value = card.dataset.datacronId;
                selectedDatacronHtml = '';
                renderSelected();
                updateDatacrons();
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
            teamElement.appendChild(header);

            const teamRow = document.createElement('div');
            teamRow.className = 'tw-proposed-team-row';
            const portraits = document.createElement('div');
            portraits.className = 'tw-team-portraits';

            team.units.forEach((unitId, index) => {
                const unit = (team.unitData || []).find((entry) => entry.id === unitId) || twUnits.find((entry) => entry.id === unitId);
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

            if (team.datacronId && (team.datacronHtml || twDatacrons[team.datacronId])) {
                const datacron = document.createElement('div');
                datacron.innerHTML = team.datacronHtml || twDatacrons[team.datacronId];
                portraits.appendChild(datacron);
            }

            teamRow.appendChild(portraits);

            const actions = document.createElement('div');
            actions.className = 'tw-team-actions';
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'tw-team-delete';
            remove.textContent = 'Delete';
            remove.title = 'Delete proposed team';
            remove.addEventListener('click', () => deleteProposedTeam(team.id));
            actions.appendChild(remove);

            const edit = document.createElement('button');
            edit.type = 'button';
            edit.className = 'tw-team-edit';
            edit.textContent = 'Edit';
            edit.title = 'Edit proposed team';
            edit.addEventListener('click', () => editProposedTeam(team.id));
            actions.appendChild(edit);

            teamRow.appendChild(actions);
            teamElement.appendChild(teamRow);
            zoneCard.appendChild(teamElement);
            team.element = teamElement;
        });

        if (noTeamsMessage) {
            noTeamsMessage.style.display = zoneTeamsContainer.querySelector('.tw-team')
                ? 'none'
                : 'block';
        }

        pushProposedButton.style.display = canPushProposedTeams && proposedTeams.length > 0 ? 'block' : 'none';
        pushProposedButton.disabled = !canPushProposedTeams || proposedTeams.length === 0;
        updateZoneCounts();
        refreshImportTeamAvailability();
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

    function editProposedTeam(teamId) {
        const index = proposedTeams.findIndex((team) => team.id === teamId);
        if (index < 0) return;

        const team = proposedTeams[index];
        const oldZone = team.zone;
        if (team.element) team.element.remove();
        proposedTeams.splice(index, 1);

        const oldZoneCard = zoneTeamsContainer.querySelector('[data-tw-zone="' + oldZone + '"]');
        if (oldZoneCard && !oldZoneCard.querySelector('.tw-team')) oldZoneCard.remove();

        zoneSelect.value = team.zone;
        selectedUnits = [...team.units];
        datacronIdInput.value = team.datacronId || '';
        selectedDatacronHtml = team.datacronHtml || '';
        if (datacronList) {
            datacronList.querySelectorAll('.tw-datacron-card').forEach((card) => {
                card.classList.toggle('selected', card.dataset.datacronId === datacronIdInput.value);
            });
        }

        updateCreator();
        renderSelected();
        renderResults();
        updateDatacrons();
        renderProposedTeams();
        refreshImportTeamAvailability();
        document.getElementById('tw-create-tab-button').click();
        unitSearch.focus();
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
            unitData: selectedUnits.map((unitId) => twUnits.find((entry) => entry.id === unitId)).filter(Boolean),
            datacronId: fleet ? '' : (datacronIdInput.value || ''),
            datacronHtml: fleet ? '' : (selectedDatacronHtml || twDatacrons[datacronIdInput.value] || ''),
            element: null
        };

        proposedTeams.push(team);

        selectedUnits = [];
        datacronIdInput.value = '';
        selectedDatacronHtml = '';

        if (datacronList) {
            datacronList.querySelectorAll('.tw-datacron-card')
                .forEach((item) => item.classList.remove('selected'));
        }

        renderSelected();
        renderResults();
        updateDatacrons();
        renderProposedTeams();
    }

    async function pushProposedTeams() {
        if (!canPushProposedTeams || proposedTeams.length === 0 || pushProposedButton.disabled) return;
        const teamsToPush = proposedTeams.map((team) => ({ zone: team.zone, units: [...team.units], datacronId: team.datacronId || '' }));
        if (!window.confirm('Push ' + teamsToPush.length + ' proposed team(s) to the game? This will deploy their units and cannot be undone from this page.')) return;

        const modal = document.getElementById('tw-push-progress-modal');
        const message = document.getElementById('tw-push-progress-message');
        const count = document.getElementById('tw-push-progress-count');
        const bar = document.getElementById('tw-push-progress-bar');
        const total = teamsToPush.length;
        let completed = 0;
        let finalResult = null;
        const updateProgress = (value, text) => {
            completed = Math.max(completed, Math.min(total, Number(value) || 0));
            count.textContent = completed + ' / ' + total + ' teams';
            bar.style.width = (completed / total * 100) + '%';
            if (text) message.textContent = text;
        };

        pushProposedButton.disabled = true;
        const originalText = pushProposedButton.textContent;
        pushProposedButton.textContent = 'Pushing teams...';
        modal.classList.add('visible');
        modal.setAttribute('aria-hidden', 'false');
        updateProgress(0, 'Connecting to the game...');
        try {
            const requestUrl = new URL(window.location.href);
            requestUrl.searchParams.set('action', 'push_proposed_teams');
            const response = await fetch(requestUrl.toString(), {
                method: 'POST', credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ csrf: pushCsrfToken, teams: teamsToPush })
            });
            if (!response.ok) {
                const body = await response.json().catch(() => ({}));
                throw new Error(body.err_txt || 'Unable to start team deployment.');
            }
            if (!response.body || !response.body.getReader) throw new Error('Progress streaming is not supported by this browser.');
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            while (true) {
                const part = await reader.read();
                if (part.done) break;
                buffer += decoder.decode(part.value, {stream:true});
                const lines = buffer.split('\n');
                buffer = lines.pop();
                for (const line of lines) {
                    if (!line.trim()) continue;
                    const event = JSON.parse(line);
                    if (event.type === 'progress') updateProgress(event.completed, 'Deploying team ' + event.completed + ' of ' + total + (event.unit ? ' (' + event.unit + ')' : '') + '...');
                    if (event.type === 'stage') updateProgress(event.completed, event.message || 'Refreshing TW status...');
                    if (event.type === 'complete' || event.type === 'error') finalResult = event;
                }
            }
            if (buffer.trim()) {
                const event = JSON.parse(buffer);
                if (event.type === 'complete' || event.type === 'error') finalResult = event;
            }
            if (!finalResult || Number(finalResult.err_code) !== 0) {
                const done = finalResult ? Number(finalResult.completed || completed) : completed;
                const errorMessage = (finalResult && finalResult.err_txt) || 'Deployment ended without confirmation.';
                if (done > 0 && finalResult && finalResult.refreshed) {
                    alert(errorMessage + ' ' + done + ' team(s) were deployed. The page will now refresh with the latest game data.');
                    window.location.reload();
                    return;
                }
                throw new Error(errorMessage + (done ? ' ' + done + ' team(s) were deployed before the error.' : ''));
            }
            updateProgress(total, 'Teams confirmed. Refreshing the page...');
            window.location.reload();
        } catch (error) {
            modal.classList.remove('visible');
            modal.setAttribute('aria-hidden', 'true');
            alert('Could not push proposed teams: ' + (error && error.message ? error.message : 'Unknown error.'));
            pushProposedButton.disabled = false;
            pushProposedButton.textContent = originalText;
        }
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
        refreshImportTeamAvailability();
    }

    let previousFleetStatus = fleetZone();

    if (historyTeamsContainer) {
        historyTeamsContainer.addEventListener('click', (event) => {
            const button = event.target.closest('.tw-import-add');
            if (!button || !historyTeamsContainer.contains(button)) return;
            // Remove the persistent keyboard/mouse focus highlight after
            // choosing the historical zone-specific import action.
            if (button.classList.contains('tw-import-add-in-zone')) {
                button.blur();
            }
            let imported;
            try { imported = JSON.parse(button.dataset.team || '{}'); } catch (e) { return; }
            if (!Array.isArray(imported.units) || imported.units.length === 0) return;
            const targetZone = button.classList.contains('tw-import-add-in-zone')
                ? imported.zone
                : zoneSelect.value;

            // The current edit-zone selection is intentionally not treated
            // as deployed: editing a proposed team releases its units.
            const unavailableIds = new Set();
            proposedTeams.forEach((team) => (team.units || []).forEach((unitId) => unavailableIds.add(unitId)));
            const missingIds = imported.units.filter((unitId) =>
                !twUnits.some((unit) => unit.id === unitId)
            );
            const conflictingIds = imported.units.filter((unitId) => unavailableIds.has(unitId));
            const availableIds = imported.units.filter((unitId) =>
                twUnits.some((unit) => unit.id === unitId) && !unavailableIds.has(unitId)
            );

            if (missingIds.length > 0 || conflictingIds.length > 0) {
                // Open a partial import in the creator so the user can add
                // replacement characters before creating the proposed team.
                if (availableIds.length === 0) return;
                zoneSelect.value = targetZone || zoneSelect.value;
                selectedUnits = availableIds;
                const datacronStillAvailable = imported.datacronId
                    && twDatacrons[imported.datacronId]
                    && !proposedTeams.some((team) => String(team.datacronId || '') === String(imported.datacronId));
                datacronIdInput.value = datacronStillAvailable ? imported.datacronId : '';
                selectedDatacronHtml = datacronStillAvailable ? (imported.datacronHtml || twDatacrons[imported.datacronId]) : '';
                if (datacronList) {
                    datacronList.querySelectorAll('.tw-datacron-card').forEach((card) => {
                        card.classList.toggle('selected', card.dataset.datacronId === datacronIdInput.value);
                    });
                }
                updateCreator();
                renderSelected();
                renderResults();
                updateDatacrons();
                refreshImportTeamAvailability();
                document.getElementById('tw-create-tab-button').click();
                unitSearch.focus();
                return;
            }

            proposedTeams.push({
                id: (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now()) + '-' + Math.random(),
                zone: targetZone || zoneSelect.value,
                units: imported.units,
                unitData: imported.unitData || [],
                datacronId: imported.datacronId || '',
                datacronHtml: imported.datacronHtml || '',
                element: null
            });
            renderProposedTeams();
            renderResults();
            updateDatacrons();
            refreshImportTeamAvailability();
        });
    }

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
    refreshImportTeamAvailability();
}
</script>
<div id="tw-push-progress-modal" class="tw-push-modal" role="dialog" aria-modal="true" aria-hidden="true">
<div class="tw-push-modal-content"><h3>Deploying TW teams</h3><p id="tw-push-progress-message">Preparing deployment...</p>
<div class="tw-push-progress-track"><div id="tw-push-progress-bar" class="tw-push-progress-bar"></div></div>
<p id="tw-push-progress-count">0 / 0 teams</p></div></div>
</body>
<?php include 'sitefooter.php'; ?>
</html>

