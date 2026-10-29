<?php
declare(strict_types=1);

/**
 * Deploy TB platoon assignments supplied by a trusted remote planner.
 * The API key authenticates the caller; a separate local token authenticates
 * the PHP-to-web_commands_server hop.
 */

function tbPlatoonApiRespond(int $status, array $payload, array $headers = []): void
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

$isHttps = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== '' &&
    strtolower((string) $_SERVER['HTTPS']) !== 'off';
if (!$isHttps) {
    tbPlatoonApiRespond(403, ['success' => false, 'err_code' => 403, 'err_txt' => 'HTTPS required']);
}
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    tbPlatoonApiRespond(405, ['success' => false, 'err_code' => 405, 'err_txt' => 'Method not allowed'], ['Allow' => 'POST']);
}

$contentLength = isset($_SERVER['CONTENT_LENGTH']) ? (int) $_SERVER['CONTENT_LENGTH'] : 0;
if ($contentLength > 1048576) {
    tbPlatoonApiRespond(413, ['success' => false, 'err_code' => 413, 'err_txt' => 'Request body too large']);
}

$configPath = '/home/pi/GuionBot/SERVER_SECRETS/web_api.php';
if (!is_file($configPath) || !is_readable($configPath)) {
    error_log('TB platoon deploy API configuration is missing or unreadable');
    tbPlatoonApiRespond(503, ['success' => false, 'err_code' => 503, 'err_txt' => 'Service unavailable']);
}
$config = require $configPath;
if (!is_array($config) || !isset($config['api_key']) ||
    !is_string($config['api_key']) || $config['api_key'] === '') {
    error_log('TB platoon deploy API configuration has an invalid format');
    tbPlatoonApiRespond(503, ['success' => false, 'err_code' => 503, 'err_txt' => 'Service unavailable']);
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
    tbPlatoonApiRespond(401, ['success' => false, 'err_code' => 401, 'err_txt' => 'Unauthorized'], ['WWW-Authenticate' => 'Bearer']);
}

$body = file_get_contents('php://input');
if ($body === false || trim($body) === '') {
    tbPlatoonApiRespond(400, ['success' => false, 'err_code' => 400, 'err_txt' => 'A JSON request body is required']);
}
$payload = json_decode($body, true);
if (json_last_error() !== JSON_ERROR_NONE || !is_array($payload) ||
    !isset($payload['ally_code'], $payload['planets']) ||
    !is_string($payload['ally_code']) || !preg_match('/^[0-9]{9}$/', $payload['ally_code']) ||
    !is_array($payload['planets']) || count($payload['planets']) === 0) {
    tbPlatoonApiRespond(400, ['success' => false, 'err_code' => 400, 'err_txt' => 'Invalid JSON payload: ally_code and a non-empty planets object are required']);
}

// Limit deployment requests independently of the read-only endpoints.
$rateFile = rtrim(sys_get_temp_dir(), DIRECTORY_SEPARATOR) .
    DIRECTORY_SEPARATOR . 'guionbot_tb_platoon_deploy_rate_' . hash('sha256', $config['api_key']) . '.json';
$rateHandle = @fopen($rateFile, 'c+');
if ($rateHandle === false || !flock($rateHandle, LOCK_EX)) {
    if (is_resource($rateHandle)) fclose($rateHandle);
    error_log('TB platoon deploy API rate-limit storage is unavailable');
    tbPlatoonApiRespond(503, ['success' => false, 'err_code' => 503, 'err_txt' => 'Service unavailable']);
}
$now = time();
$rateState = json_decode((string) stream_get_contents($rateHandle), true);
$timestamps = [];
if (is_array($rateState) && isset($rateState['timestamps']) && is_array($rateState['timestamps'])) {
    foreach ($rateState['timestamps'] as $timestamp) {
        if (is_int($timestamp) && $timestamp > $now - 86400 && $timestamp <= $now) {
            $timestamps[] = $timestamp;
        }
    }
}
$recent = array_values(array_filter($timestamps, static function ($timestamp) use ($now) {
    return $timestamp > $now - 60;
}));
$rateError = null;
$retryAfter = 1;
if (count($timestamps) >= 100) {
    sort($timestamps, SORT_NUMERIC);
    $rateError = 'Daily deployment request limit exceeded';
    $retryAfter = max(1, $timestamps[count($timestamps) - 100] + 86400 - $now + 1);
} elseif (count($recent) >= 2) {
    sort($recent, SORT_NUMERIC);
    $rateError = 'Deployment rate limit exceeded';
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
    tbPlatoonApiRespond(429, ['success' => false, 'err_code' => 429, 'err_txt' => $rateError], ['Retry-After' => (string) $retryAfter]);
}

$tokenPath = '/home/pi/GuionBot/SERVER_SECRETS/web_commands.token';
if (!is_file($tokenPath) || !is_readable($tokenPath)) {
    error_log('TB platoon deploy API web commands token is missing or unreadable');
    tbPlatoonApiRespond(503, ['success' => false, 'err_code' => 503, 'err_txt' => 'Deployment service is not configured']);
}
$token = trim((string) file_get_contents($tokenPath));
if ($token === '') {
    tbPlatoonApiRespond(503, ['success' => false, 'err_code' => 503, 'err_txt' => 'Deployment service is not configured']);
}

$ch = curl_init('http://127.0.0.1:9000/DeployTBPlatoons');
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $token,
    ],
    CURLOPT_POSTFIELDS => $body,
    CURLOPT_CONNECTTIMEOUT => 3,
    CURLOPT_TIMEOUT => 900,
]);
$response = curl_exec($ch);
$curlError = curl_error($ch);
$httpCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($response === false) {
    error_log('TB platoon deploy API web command connection failed: ' . $curlError);
    tbPlatoonApiRespond(502, ['success' => false, 'err_code' => 502, 'err_txt' => 'Deployment service unavailable']);
}
$result = json_decode($response, true);
if (!is_array($result)) {
    error_log('TB platoon deploy API received an invalid web command response; HTTP ' . $httpCode);
    tbPlatoonApiRespond(502, ['success' => false, 'err_code' => 502, 'err_txt' => 'Invalid deployment service response']);
}
tbPlatoonApiRespond($httpCode >= 200 && $httpCode < 300 ? $httpCode : 502, $result);
