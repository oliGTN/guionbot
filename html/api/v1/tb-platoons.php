<?php
declare(strict_types=1);

/**
 * Read-only API: current unfinished TB platoons for one configured guild.
 *
 * The API key and fixed guild ID are loaded from /etc/guionbot/tb_platoons_api.php,
 * outside the web document root. Database settings and the PDO connection are
 * reused from html/guionbotdb.php. See docs/tb-platoons-api.md.
 */

function apiRespond(int $status, array $payload, array $extraHeaders = []): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, private');
    header('X-Content-Type-Options: nosniff');
    foreach ($extraHeaders as $name => $value) {
        header($name . ': ' . $value);
    }
    echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

// This endpoint is intended to be used only through HTTPS.
$isHttps = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== '' &&
    strtolower((string) $_SERVER['HTTPS']) !== 'off';
if (!$isHttps) {
    apiRespond(403, ['success' => false, 'error' => 'HTTPS required']);
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    apiRespond(405, ['success' => false, 'error' => 'Method not allowed'], ['Allow' => 'POST']);
}

$contentLength = isset($_SERVER['CONTENT_LENGTH']) ? (int) $_SERVER['CONTENT_LENGTH'] : 0;
if ($contentLength > 1024) {
    apiRespond(413, ['success' => false, 'error' => 'Request body too large']);
}

// No request parameters are needed. Accept an empty body or an empty JSON object only.
// In particular, the client cannot select a different guild_id.
$body = file_get_contents('php://input');
if ($body === false) {
    apiRespond(400, ['success' => false, 'error' => 'Invalid request body']);
}
if (trim($body) !== '') {
    $request = json_decode($body);
    if (json_last_error() !== JSON_ERROR_NONE ||
        !($request instanceof stdClass) ||
        count(get_object_vars($request)) !== 0) {
        apiRespond(400, ['success' => false, 'error' => 'Request body must be empty or an empty JSON object']);
    }
}

$configPath = '/etc/guionbot/tb_platoons_api.php';
if (!is_file($configPath) || !is_readable($configPath)) {
    error_log('TB platoons API configuration is missing or unreadable');
    apiRespond(503, ['success' => false, 'error' => 'Service unavailable']);
}

$config = require $configPath;
if (!is_array($config)) {
    error_log('TB platoons API configuration has an invalid format');
    apiRespond(503, ['success' => false, 'error' => 'Service unavailable']);
}

$requiredConfig = ['api_key', 'guild_id'];
foreach ($requiredConfig as $key) {
    if (!isset($config[$key]) || !is_string($config[$key]) || $config[$key] === '') {
        error_log('TB platoons API configuration is missing a required value');
        apiRespond(503, ['success' => false, 'error' => 'Service unavailable']);
    }
}

$headers = function_exists('getallheaders') ? getallheaders() : [];
$authorization = '';
foreach ($headers as $name => $value) {
    if (strcasecmp((string) $name, 'Authorization') === 0) {
        $authorization = is_string($value) ? trim($value) : '';
        break;
    }
}
if ($authorization === '' && isset($_SERVER['HTTP_AUTHORIZATION'])) {
    $authorization = trim((string) $_SERVER['HTTP_AUTHORIZATION']);
}
if ($authorization === '' && isset($_SERVER['REDIRECT_HTTP_AUTHORIZATION'])) {
    $authorization = trim((string) $_SERVER['REDIRECT_HTTP_AUTHORIZATION']);
}

if (!preg_match('/^Bearer\s+([^\s]+)$/i', $authorization, $matches) ||
    !hash_equals($config['api_key'], $matches[1])) {
    apiRespond(401, ['success' => false, 'error' => 'Unauthorized'], ['WWW-Authenticate' => 'Bearer']);
}

// Rate limit this API key: 5 requests per rolling minute and 1,000 per rolling day.
// File locking makes the counter safe when Apache handles concurrent requests.
$rateFile = rtrim(sys_get_temp_dir(), DIRECTORY_SEPARATOR) .
    DIRECTORY_SEPARATOR . 'guionbot_tb_platoons_rate_' . hash('sha256', $config['api_key']) . '.json';
$rateHandle = @fopen($rateFile, 'c+');
if ($rateHandle === false || !flock($rateHandle, LOCK_EX)) {
    if (is_resource($rateHandle)) {
        fclose($rateHandle);
    }
    error_log('TB platoons API rate-limit storage is unavailable');
    apiRespond(503, ['success' => false, 'error' => 'Service unavailable']);
}

$now = time();
$rateState = [];
$rawRateState = stream_get_contents($rateHandle);
if (is_string($rawRateState) && $rawRateState !== '') {
    $decodedRateState = json_decode($rawRateState, true);
    if (is_array($decodedRateState)) {
        $rateState = $decodedRateState;
    }
}
$timestamps = [];
foreach (($rateState['timestamps'] ?? []) as $timestamp) {
    if (is_int($timestamp) && $timestamp > $now - 86400 && $timestamp <= $now) {
        $timestamps[] = $timestamp;
    }
}
$minuteCount = 0;
foreach ($timestamps as $timestamp) {
    if ($timestamp > $now - 60) {
        $minuteCount++;
    }
}

$rateError = null;
$retryAfter = 1;
if (count($timestamps) >= 1000) {
    $rateError = 'Daily request limit exceeded';
    sort($timestamps, SORT_NUMERIC);
    $retryAfter = max(1, $timestamps[count($timestamps) - 1000] + 86400 - $now + 1);
} elseif ($minuteCount >= 5) {
    $rateError = 'Rate limit exceeded';
    $recent = array_values(array_filter($timestamps, static function ($timestamp) use ($now) {
        return $timestamp > $now - 60;
    }));
    sort($recent, SORT_NUMERIC);
    $retryAfter = max(1, $recent[0] + 60 - $now + 1);
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
    apiRespond(429, ['success' => false, 'error' => $rateError], [
        'Retry-After' => (string) $retryAfter,
        'RateLimit-Limit' => '5',
        'RateLimit-Remaining' => '0'
    ]);
}

try {
    // Reuse the existing website DB configuration and PDO connection.
    // This file defines $host, $dbname, $username, $password and $conn_guionbot.
    require_once dirname(__DIR__, 2) . '/guionbotdb.php';

    if (!isset($conn_guionbot) || !($conn_guionbot instanceof PDO)) {
        throw new RuntimeException('Website database connection is unavailable');
    }

    // The guild ID is server configuration, never client input.
    $sql = 'SELECT p.platoon_name, p.unit_name, p.player_name
            FROM tb_platoons AS p
            INNER JOIN tb_history AS h ON h.id = p.tb_id
            WHERE h.guild_id = :guild_id
              AND h.stars_final IS NULL
            LIMIT 5001';
    $statement = $conn_guionbot->prepare($sql);
    $statement->execute([':guild_id' => $config['guild_id']]);
    $rows = $statement->fetchAll();
} catch (PDOException $exception) {
    // Do not send SQL details, credentials, or internal database errors to the client.
    error_log('TB platoons API database query failed; SQLSTATE=' . (string) $exception->getCode());
    apiRespond(500, ['success' => false, 'error' => 'Unable to retrieve platoon data']);
} catch (Throwable $exception) {
    error_log('TB platoons API database setup failed; exception=' . get_class($exception));
    apiRespond(500, ['success' => false, 'error' => 'Unable to retrieve platoon data']);
}

if (count($rows) > 5000) {
    apiRespond(503, ['success' => false, 'error' => 'Result exceeds the API row limit']);
}

apiRespond(200, [
    'success' => true,
    'count' => count($rows),
    'data' => $rows,
], [
    'RateLimit-Limit' => '5',
    'RateLimit-Remaining' => (string) max(0, 4 - $minuteCount),
]);
