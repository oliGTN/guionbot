<?php
declare(strict_types=1);

/**
 * Read-only Rise of the Empire TB history API.
 * Public identifier: tb_history.tb_id. Internal tb_history.id is used only for joins.
 */

function tbHistoryRespond(int $status, array $payload, array $headers = []): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, private');
    header('X-Content-Type-Options: nosniff');
    foreach ($headers as $name => $value) {
        header($name . ': ' . $value);
    }
    echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function tbHistoryIso(?DateTimeImmutable $date): ?string
{
    return $date === null ? null : $date->setTimezone(new DateTimeZone('UTC'))->format('Y-m-d\TH:i:s\Z');
}

function tbHistoryNullableInt($value): ?int
{
    return $value === null ? null : (int)$value;
}

function tbHistoryStatValue(array $stats, string $statId, string $playerId): ?int
{
    if (!array_key_exists($statId, $stats) || $stats[$statId] === null) {
        return null;
    }
    return array_key_exists($playerId, $stats[$statId]) ? $stats[$statId][$playerId] : 0;
}

function tbHistoryLoadMapstats(string $guildId, string $tbId): ?array
{
    if (!preg_match('/^TB_EVENT_TB3_MIXED:O[0-9]+$/', $tbId)) {
        return null;
    }
    $eventsDir = dirname(__DIR__, 3) . DIRECTORY_SEPARATOR . 'EVENTS';
    $baseDir = realpath($eventsDir);
    if ($baseDir === false) {
        return null;
    }
    $path = $baseDir . DIRECTORY_SEPARATOR . $guildId . '_' . $tbId . '_mapstats.json';
    if (!is_file($path) || !is_readable($path)) {
        return null;
    }
    $size = filesize($path);
    if ($size === false || $size > 20000000) {
        return null;
    }
    $raw = file_get_contents($path);
    if ($raw === false) {
        return null;
    }
    $decoded = json_decode($raw, true);
    if (json_last_error() !== JSON_ERROR_NONE || !is_array($decoded)) {
        error_log('TB history API: invalid mapstats JSON for a TB');
        return null;
    }

    $indexed = [];
    foreach ($decoded as $entry) {
        if (!is_array($entry) || !isset($entry['mapStatId']) || !is_string($entry['mapStatId'])) {
            continue;
        }
        if (!isset($entry['playerStat']) || !is_array($entry['playerStat'])) {
            $indexed[$entry['mapStatId']] = null;
            continue;
        }
        $indexed[$entry['mapStatId']] = [];
        foreach ($entry['playerStat'] as $playerStat) {
            if (!is_array($playerStat) || !isset($playerStat['memberId']) || !is_string($playerStat['memberId'])) {
                continue;
            }
            if (isset($playerStat['score']) && is_numeric($playerStat['score'])) {
                $indexed[$entry['mapStatId']][$playerStat['memberId']] = (int)$playerStat['score'];
            }
        }
    }
    return $indexed;
}

function tbHistoryBuildPlayers(PDO $db, string $guildId, string $tbId, int $internalTbId): array
{
    $stats = tbHistoryLoadMapstats($guildId, $tbId);

    // tb_player_score stores the per-player GP snapshot for every phase. Its tb_id
    // is the internal FK and is never exposed in the API response.
    $phaseStatement = $db->prepare(
        'SELECT player_id, round, gp, char_gp, ship_gp
         FROM tb_player_score
         WHERE tb_id = :id
         ORDER BY round, player_id'
    );
    $phaseStatement->execute([':id' => $internalTbId]);
    $phaseRows = [];
    $playerIds = [];
    foreach ($phaseStatement->fetchAll(PDO::FETCH_ASSOC) as $row) {
        $playerId = (string)$row['player_id'];
        $round = (int)$row['round'];
        if ($playerId === '' || $round < 1 || $round > 6) {
            continue;
        }
        $phaseRows[$playerId][$round] = [
            'gp' => tbHistoryNullableInt($row['gp']),
            'gp_chars' => tbHistoryNullableInt($row['char_gp']),
            'gp_ships' => tbHistoryNullableInt($row['ship_gp'])
        ];
        $playerIds[$playerId] = true;
    }

    if ($stats !== null) {
        for ($round = 1; $round <= 6; $round++) {
            foreach ([
                'summary_round_' . $round,
                'power_round_' . $round,
                'strike_attempt_round_' . $round,
                'strike_encounter_round_' . $round,
                'covert_attempt_round_' . $round,
                'unit_donated_round_' . $round,
                'disobey_round_' . $round
            ] as $statId) {
                foreach (array_keys($stats[$statId] ?? []) as $playerId) {
                    $playerIds[$playerId] = true;
                }
            }
        }
    }

    if (!$playerIds) {
        return [[], $stats !== null];
    }

    // Mapstats covert completions are mission-specific; the phase is encoded
    // in the mission identifier.
    $covertDone = [];
    if ($stats !== null) {
        foreach ($stats as $statId => $playerScores) {
            if (preg_match('/^covert_complete_mission_tb3_mixed_phase0([1-6])_/', $statId, $match) &&
                is_array($playerScores)) {
                $round = (int)$match[1];
                foreach ($playerScores as $playerId => $score) {
                    if (!isset($covertDone[$round][$playerId])) {
                        $covertDone[$round][$playerId] = 0;
                    }
                    $covertDone[$round][$playerId] += $score;
                }
            }
        }
    }

    $ids = array_keys($playerIds);
    $placeholders = [];
    $params = [];
    foreach ($ids as $index => $playerId) {
        $key = ':player' . $index;
        $placeholders[] = $key;
        $params[$key] = $playerId;
    }
    $sql = 'SELECT playerId, CAST(allyCode AS CHAR) AS ally_code, name, lastUpdated
            FROM players
            WHERE playerId IN (' . implode(',', $placeholders) . ')
            ORDER BY lastUpdated DESC';
    $statement = $db->prepare($sql);
    $statement->execute($params);
    $playerInfo = [];
    foreach ($statement->fetchAll(PDO::FETCH_ASSOC) as $row) {
        // If an ID has multiple historical rows, use its most recently updated profile.
        if (!isset($playerInfo[$row['playerId']])) {
            $playerInfo[$row['playerId']] = [
                'ally_code' => isset($row['ally_code']) ? (string)$row['ally_code'] : null,
                'name' => $row['name']
            ];
        }
    }

    $players = [];
    foreach ($ids as $playerId) {
        $info = $playerInfo[$playerId] ?? ['ally_code' => null, 'name' => null];
        $roundRows = [];
        for ($round = 1; $round <= 6; $round++) {
            $roundStatIds = [
                'summary_round_' . $round,
                'power_round_' . $round,
                'strike_attempt_round_' . $round,
                'strike_encounter_round_' . $round,
                'covert_attempt_round_' . $round,
                'unit_donated_round_' . $round,
                'disobey_round_' . $round
            ];
            $present = isset($phaseRows[$playerId][$round]);
            if (!$present && $stats !== null) {
                foreach ($roundStatIds as $statId) {
                    if (isset($stats[$statId]) && is_array($stats[$statId]) &&
                        array_key_exists($playerId, $stats[$statId])) {
                        $present = true;
                        break;
                    }
                }
            }

            $summary = $stats === null ? null : tbHistoryStatValue($stats, 'summary_round_' . $round, $playerId);
            $deploy = $stats === null ? null : tbHistoryStatValue($stats, 'power_round_' . $round, $playerId);
            $combat = ($summary !== null && $deploy !== null) ? $summary - $deploy : null;
            $gp = $phaseRows[$playerId][$round] ?? ['gp' => null, 'gp_chars' => null, 'gp_ships' => null];

            $roundRows[] = [
                'round' => $round,
                'present' => $present,
                'gp' => $gp['gp'],
                'gp_chars' => $gp['gp_chars'],
                'gp_ships' => $gp['gp_ships'],
                'deploy_points' => $deploy,
                'combat_points' => $combat,
                'summary' => $summary,
                'strike_attempts' => $stats === null ? null : tbHistoryStatValue($stats, 'strike_attempt_round_' . $round, $playerId),
                'waves_won' => $stats === null ? null : tbHistoryStatValue($stats, 'strike_encounter_round_' . $round, $playerId),
                'covert_attempts' => $stats === null ? null : tbHistoryStatValue($stats, 'covert_attempt_round_' . $round, $playerId),
                'covert_done' => $stats === null ? null : ($covertDone[$round][$playerId] ?? null),
                'units_donated' => $stats === null ? null : tbHistoryStatValue($stats, 'unit_donated_round_' . $round, $playerId),
                'disobey' => $stats === null ? null : tbHistoryStatValue($stats, 'disobey_round_' . $round, $playerId)
            ];
        }
        $players[] = [
            'player_id' => $playerId,
            'ally_code' => $info['ally_code'],
            'name' => $info['name'],
            'rounds' => $roundRows
        ];
    }

    usort($players, static function ($a, $b) {
        return strcmp((string)$a['name'], (string)$b['name']);
    });
    return [$players, $stats !== null];
}

// HTTPS and POST only.
$isHttps = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== '' &&
    strtolower((string)$_SERVER['HTTPS']) !== 'off';
if (!$isHttps) {
    tbHistoryRespond(403, ['success' => false, 'error' => 'HTTPS required']);
}
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    tbHistoryRespond(405, ['success' => false, 'error' => 'Method not allowed'], ['Allow' => 'POST']);
}
if ((int)($_SERVER['CONTENT_LENGTH'] ?? 0) > 4096) {
    tbHistoryRespond(413, ['success' => false, 'error' => 'Request body too large']);
}

$raw = file_get_contents('php://input');
$request = [];
if ($raw === false) {
    tbHistoryRespond(400, ['success' => false, 'error' => 'Invalid request body']);
}
if (trim($raw) !== '') {
    $decoded = json_decode($raw, true);
    if (json_last_error() !== JSON_ERROR_NONE || !is_array($decoded) ||
        (count($decoded) > 0 && array_keys($decoded) === range(0, count($decoded) - 1))) {
        tbHistoryRespond(400, ['success' => false, 'error' => 'Request body must be a JSON object']);
    }
    $request = $decoded;
}

$allowed = ['tb_id', 'tb_ids', 'blocks'];
if (array_diff(array_keys($request), $allowed)) {
    tbHistoryRespond(400, ['success' => false, 'error' => 'Unknown request field']);
}
if (isset($request['tb_id']) &&
    (!is_string($request['tb_id']) || trim($request['tb_id']) === '' || strlen($request['tb_id']) > 45)) {
    tbHistoryRespond(400, ['success' => false, 'error' => 'tb_id must be a non-empty string']);
}
if (isset($request['tb_ids'])) {
    if (!is_array($request['tb_ids']) || count($request['tb_ids']) < 1 || count($request['tb_ids']) > 100) {
        tbHistoryRespond(400, ['success' => false, 'error' => 'tb_ids must contain 1 to 100 IDs']);
    }
    foreach ($request['tb_ids'] as $id) {
        if (!is_string($id) || trim($id) === '' || strlen($id) > 45) {
            tbHistoryRespond(400, ['success' => false, 'error' => 'Every tb_ids value must be a non-empty string']);
        }
    }
}
if (isset($request['tb_id'], $request['tb_ids'])) {
    tbHistoryRespond(400, ['success' => false, 'error' => 'Use tb_id or tb_ids, not both']);
}

$validBlocks = ['zones', 'players', 'player_zones', 'strikes', 'covert'];
$blocks = $request['blocks'] ?? ['zones', 'players'];
if (!is_array($blocks) || count($blocks) > count($validBlocks)) {
    tbHistoryRespond(400, ['success' => false, 'error' => 'blocks must be an array']);
}
foreach ($blocks as $block) {
    if (!is_string($block) || !in_array($block, $validBlocks, true)) {
        tbHistoryRespond(400, ['success' => false, 'error' => 'Unknown block']);
    }
}
$blocks = array_values(array_unique($blocks));

$configPath = '/home/pi/GuionBot/SERVER_SECRETS/web_api.php';
if (!is_file($configPath) || !is_readable($configPath)) {
    tbHistoryRespond(503, ['success' => false, 'error' => 'Service unavailable']);
}
$config = require $configPath;
if (!is_array($config) || empty($config['api_key']) || empty($config['guild_id']) ||
    !is_string($config['api_key']) || !is_string($config['guild_id'])) {
    tbHistoryRespond(503, ['success' => false, 'error' => 'Service unavailable']);
}

$headersIn = function_exists('getallheaders') ? getallheaders() : [];
$authorization = '';
foreach ($headersIn as $name => $value) {
    if (strcasecmp((string)$name, 'Authorization') === 0) {
        $authorization = is_string($value) ? trim($value) : '';
        break;
    }
}
if ($authorization === '') {
    $authorization = trim((string)($_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? ''));
}
if (!preg_match('/^Bearer\s+([^\s]+)$/i', $authorization, $matches) ||
    !hash_equals($config['api_key'], $matches[1])) {
    tbHistoryRespond(401, ['success' => false, 'error' => 'Unauthorized'], ['WWW-Authenticate' => 'Bearer']);
}

// 5 requests/minute and 1,000/day per API key.
$rateFile = rtrim(sys_get_temp_dir(), DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR .
    'guionbot_tb_history_rate_' . hash('sha256', $config['api_key']) . '.json';
$rateHandle = @fopen($rateFile, 'c+');
if ($rateHandle === false || !flock($rateHandle, LOCK_EX)) {
    if (is_resource($rateHandle)) {
        fclose($rateHandle);
    }
    tbHistoryRespond(503, ['success' => false, 'error' => 'Service unavailable']);
}
$now = time();
$rateState = json_decode((string)stream_get_contents($rateHandle), true);
$timestamps = [];
foreach (($rateState['timestamps'] ?? []) as $timestamp) {
    if (is_int($timestamp) && $timestamp > $now - 86400 && $timestamp <= $now) {
        $timestamps[] = $timestamp;
    }
}
$recent = array_values(array_filter($timestamps, static function ($timestamp) use ($now) {
    return $timestamp > $now - 60;
}));
$rateError = count($timestamps) >= 1000 ? 'Daily request limit exceeded' :
    (count($recent) >= 5 ? 'Rate limit exceeded' : null);
$retryAfter = 1;
if ($rateError !== null) {
    $list = $rateError === 'Daily request limit exceeded' ? $timestamps : $recent;
    sort($list, SORT_NUMERIC);
    $retryAfter = max(1, $list[0] + ($rateError === 'Daily request limit exceeded' ? 86400 : 60) - $now + 1);
} else {
    $timestamps[] = $now;
}
rewind($rateHandle);
if ($rateError === null) {
    ftruncate($rateHandle, 0);
    fwrite($rateHandle, json_encode(['timestamps' => $timestamps]));
    fflush($rateHandle);
}
flock($rateHandle, LOCK_UN);
fclose($rateHandle);
if ($rateError !== null) {
    tbHistoryRespond(429, ['success' => false, 'error' => $rateError], [
        'Retry-After' => (string)$retryAfter,
        'RateLimit-Limit' => '5',
        'RateLimit-Remaining' => '0'
    ]);
}

try {
    require_once dirname(__DIR__, 2) . '/guionbotdb.php';
    if (!isset($conn_guionbot) || !($conn_guionbot instanceof PDO)) {
        throw new RuntimeException('PDO unavailable');
    }

    // The client-supplied public tb_id is matched only against tb_history.tb_id.
    // The internal h.id is selected solely for child-table joins and is never serialized.
    $where = 'h.guild_id = :guild_id
              AND EXISTS (
                  SELECT 1 FROM tb_zones AS rz
                  WHERE rz.tb_id = h.id AND rz.zone_id LIKE "tb3_mixed_%"
              )';
    $params = [':guild_id' => $config['guild_id']];
    if (isset($request['tb_id'])) {
        $where .= ' AND h.tb_id = :tb_id';
        $params[':tb_id'] = $request['tb_id'];
    } elseif (isset($request['tb_ids'])) {
        $marks = [];
        foreach ($request['tb_ids'] as $index => $id) {
            $key = ':tb' . $index;
            $marks[] = $key;
            $params[$key] = $id;
        }
        $where .= ' AND h.tb_id IN (' . implode(',', $marks) . ')';
    }

    $statement = $conn_guionbot->prepare(
        'SELECT h.id, h.tb_id, h.tb_name, h.start_date, h.current_round, h.stars_final
         FROM tb_history AS h
         WHERE ' . $where . '
         ORDER BY h.start_date DESC
         LIMIT 501'
    );
    $statement->execute($params);
    $history = $statement->fetchAll(PDO::FETCH_ASSOC);
    if (count($history) > 500) {
        tbHistoryRespond(503, ['success' => false, 'error' => 'Result exceeds the API TB limit']);
    }

    $tbs = [];
    foreach ($history as $historyRow) {
        $start = $historyRow['start_date'] !== null
            ? new DateTimeImmutable($historyRow['start_date'], new DateTimeZone('UTC'))
            : null;
        $finished = $historyRow['stars_final'] !== null;
        $currentRound = $finished ? 6 : max(1, min(6, (int)$historyRow['current_round']));
        $rounds = [];
        for ($round = 1; $round <= ($finished ? 6 : $currentRound); $round++) {
            $roundStart = $start ? $start->modify('+' . (($round - 1) * 24) . ' hours') : null;
            $roundEnd = $roundStart ? $roundStart->modify('+24 hours') : null;
            $rounds[] = [
                'round' => $round,
                'start' => tbHistoryIso($roundStart),
                'end' => (!$finished && $round === $currentRound) ? null : tbHistoryIso($roundEnd)
            ];
        }

        $tb = [
            'tb_id' => (string)$historyRow['tb_id'],
            'status' => $finished ? 'finished' : 'current',
            'started' => tbHistoryIso($start),
            'ended' => ($finished && $start) ? tbHistoryIso($start->modify('+144 hours')) : null,
            'rounds' => $rounds,
            'members' => null,
            // Conservative until event/mapstats coverage is calculated by the V2 block.
            'events_complete' => false
        ];

        $phaseStatement = $conn_guionbot->prepare(
            'SELECT totalPlayers FROM tb_phases WHERE tb_id = :id AND round = 1 LIMIT 1'
        );
        $phaseStatement->execute([':id' => $historyRow['id']]);
        $members = $phaseStatement->fetchColumn();
        if ($members !== false && $members !== null) {
            $tb['members'] = (int)$members;
        }

        if (in_array('zones', $blocks, true)) {
            $zoneStatement = $conn_guionbot->prepare(
                'SELECT zone_id, zone_name, round, score_step1, score_step2, score_step3,
                        score, is_bonus, cmdMsg, cmdCmd,
                        recon1_filled, recon2_filled, recon3_filled,
                        recon4_filled, recon5_filled, recon6_filled
                 FROM tb_zones
                 WHERE tb_id = :id AND zone_id LIKE "tb3_mixed_%"
                 ORDER BY zone_id, round'
            );
            $zoneStatement->execute([':id' => $historyRow['id']]);
            $zoneMap = [];
            foreach ($zoneStatement->fetchAll(PDO::FETCH_ASSOC) as $zoneRow) {
                $zoneId = (string)$zoneRow['zone_id'];
                if (!isset($zoneMap[$zoneId])) {
                    $alignment = null;
                    if (preg_match('/_conflict01(?:_bonus)?$/', $zoneId)) {
                        $alignment = 'LS';
                    } elseif (preg_match('/_conflict02(?:_bonus)?$/', $zoneId)) {
                        $alignment = 'DS';
                    } elseif (preg_match('/_conflict03(?:_bonus)?$/', $zoneId)) {
                        $alignment = 'MS';
                    }
                    $zoneMap[$zoneId] = [
                        'zone_id' => $zoneId,
                        'name' => $zoneRow['zone_name'],
                        'alignment' => $alignment,
                        'is_bonus' => (bool)$zoneRow['is_bonus'],
                        'thresholds' => [
                            tbHistoryNullableInt($zoneRow['score_step1']),
                            tbHistoryNullableInt($zoneRow['score_step2']),
                            tbHistoryNullableInt($zoneRow['score_step3'])
                        ],
                        'rounds' => []
                    ];
                }

                $score = tbHistoryNullableInt($zoneRow['score']);
                $threshold1 = tbHistoryNullableInt($zoneRow['score_step1']);
                $threshold2 = tbHistoryNullableInt($zoneRow['score_step2']);
                $threshold3 = tbHistoryNullableInt($zoneRow['score_step3']);
                $stars = null;
                if ($score !== null && $threshold1 !== null && $threshold2 !== null && $threshold3 !== null) {
                    $stars = $score >= $threshold3 ? 3 : ($score >= $threshold2 ? 2 : ($score >= $threshold1 ? 1 : 0));
                }

                $rawStrategy = trim((string)$zoneRow['cmdMsg']);
                $strategy = null;
                if (strcasecmp($rawStrategy, 'Full') === 0) {
                    $strategy = 'Full';
                } elseif (in_array($rawStrategy, ['Pré remplir', 'pré remplir', 'Pré-remplir', 'pré-remplir'], true)) {
                    $strategy = 'Pré remplir';
                } elseif (in_array($rawStrategy, ["Pas d'étoile", "pas d'étoile"], true)) {
                    $strategy = "Pas d'étoile";
                }

                $zoneMap[$zoneId]['rounds'][] = [
                    'round' => (int)$zoneRow['round'],
                    'score_end' => $score,
                    'score_raw' => null,
                    'stars_end' => $stars,
                    'strategy' => $strategy,
                    'strategy_code' => tbHistoryNullableInt($zoneRow['cmdCmd']),
                    'recon_filled' => [
                        tbHistoryNullableInt($zoneRow['recon1_filled']),
                        tbHistoryNullableInt($zoneRow['recon2_filled']),
                        tbHistoryNullableInt($zoneRow['recon3_filled']),
                        tbHistoryNullableInt($zoneRow['recon4_filled']),
                        tbHistoryNullableInt($zoneRow['recon5_filled']),
                        tbHistoryNullableInt($zoneRow['recon6_filled'])
                    ],
                    'platoon_points' => null
                ];
            }
            $tb['zones'] = array_values($zoneMap);
        }

        if (in_array('players', $blocks, true)) {
            list($players, $mapstatsAvailable) = tbHistoryBuildPlayers(
                $conn_guionbot,
                $config['guild_id'],
                (string)$historyRow['tb_id'],
                (int)$historyRow['id']
            );
            $tb['players'] = $players;
            if (!$mapstatsAvailable) {
                $tb['events_complete'] = false;
            }
        }

        foreach (['player_zones', 'strikes', 'covert'] as $optionalBlock) {
            if (in_array($optionalBlock, $blocks, true)) {
                $tb[$optionalBlock] = [];
            }
        }

        $tbs[] = $tb;
    }
} catch (PDOException $exception) {
    error_log('TB history API query failed; SQLSTATE=' . (string)$exception->getCode());
    tbHistoryRespond(500, ['success' => false, 'error' => 'Unable to retrieve TB history']);
} catch (Throwable $exception) {
    error_log('TB history API setup failed; exception=' . get_class($exception));
    tbHistoryRespond(500, ['success' => false, 'error' => 'Unable to retrieve TB history']);
}

tbHistoryRespond(200, [
    'success' => true,
    'generated' => gmdate('Y-m-d\TH:i:s\Z'),
    'tbs' => $tbs
], [
    'RateLimit-Limit' => '5',
    'RateLimit-Remaining' => (string)max(0, 4 - count($recent))
]);
