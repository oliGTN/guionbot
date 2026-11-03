<?php
declare(strict_types=1);

/**
 * Read-only API: connected-account authentication status for players in the
 * configured guild. The guild ID is never accepted from client input.
 */

function guildAccountsRespond(int $status, array $payload, array $extraHeaders = []): void
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

$isHttps = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== '' &&
    strtolower((string) $_SERVER['HTTPS']) !== 'off';
if (!$isHttps) {
    guildAccountsRespond(403, ['success' => false, 'error' => 'HTTPS required']);
}
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    guildAccountsRespond(405, ['success' => false, 'error' => 'Method not allowed'], ['Allow' => 'POST']);
}

$contentLength = isset($_SERVER['CONTENT_LENGTH']) ? (int) $_SERVER['CONTENT_LENGTH'] : 0;
if ($contentLength > 1024) {
    guildAccountsRespond(413, ['success' => false, 'error' => 'Request body too large']);
}
$body = file_get_contents('php://input');
if ($body === false) {
    guildAccountsRespond(400, ['success' => false, 'error' => 'Invalid request body']);
}
if (trim($body) !== '') {
    $request = json_decode($body);
    if (json_last_error() !== JSON_ERROR_NONE ||
        !($request instanceof stdClass) ||
        count(get_object_vars($request)) !== 0) {
        guildAccountsRespond(400, ['success' => false, 'error' => 'Request body must be empty or an empty JSON object']);
    }
}

require_once dirname(__DIR__) . '/includes/api_auth.php';
$authContext = apiAuthenticate('guild-connected-accounts', 'guildAccountsRespond');
$config = $authContext['config'];

$tokenPath = '/home/pi/GuionBot/SERVER_SECRETS/web_commands.token';
if (!is_file($tokenPath) || !is_readable($tokenPath)) {
    error_log('Guild connected accounts API web commands token is missing or unreadable');
    guildAccountsRespond(503, ['success' => false, 'error' => 'Service unavailable']);
}
$token = trim((string) file_get_contents($tokenPath));
if ($token === '') {
    guildAccountsRespond(503, ['success' => false, 'error' => 'Service unavailable']);
}

$ch = curl_init('http://127.0.0.1:9000/GuildConnectedAccounts');
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $token,
    ],
    CURLOPT_POSTFIELDS => json_encode(['guild_id' => $config['guild_id']]),
    CURLOPT_CONNECTTIMEOUT => 3,
    CURLOPT_TIMEOUT => 90,
]);
$response = curl_exec($ch);
$curlError = curl_error($ch);
$httpCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($response === false) {
    error_log('Guild connected accounts API web command connection failed: ' . $curlError);
    guildAccountsRespond(502, ['success' => false, 'error' => 'Service unavailable']);
}
$result = json_decode($response, true);
if (!is_array($result)) {
    error_log('Guild connected accounts API received an invalid internal response; HTTP ' . $httpCode);
    guildAccountsRespond(502, ['success' => false, 'error' => 'Invalid service response']);
}
if ($httpCode === 200 && !empty($result['success']) && array_key_exists('data', $result)) {
    guildAccountsRespond(200, [
        'success' => true,
        'data' => $result['data'],
    ], [
        'RateLimit-Limit' => (string)$authContext['limit'],
        'RateLimit-Remaining' => (string)$authContext['remaining'],
    ]);
}
if ($httpCode === 502 || $httpCode === 504) {
    guildAccountsRespond($httpCode, ['success' => false, 'error' => 'Unable to retrieve connected-account data']);
}
error_log('Guild connected accounts API internal service returned HTTP ' . $httpCode);
guildAccountsRespond(502, ['success' => false, 'error' => 'Service unavailable']);
