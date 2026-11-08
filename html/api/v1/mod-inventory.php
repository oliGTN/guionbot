<?php
declare(strict_types=1);

/**
 * Return only the unequipped mod inventory for the requested allycode.
 * The RPC call is performed by the local web_commands_server.
 */

function modInventoryApiRespond(int $status, array $payload, array $headers = []): void
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
    modInventoryApiRespond(403, ['success' => false, 'error' => 'HTTPS required']);
}
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    modInventoryApiRespond(405, ['success' => false, 'error' => 'Method not allowed'], ['Allow' => 'POST']);
}

$contentLength = isset($_SERVER['CONTENT_LENGTH']) ? (int) $_SERVER['CONTENT_LENGTH'] : 0;
if ($contentLength > 1024) {
    modInventoryApiRespond(413, ['success' => false, 'error' => 'Request body too large']);
}

require_once dirname(__DIR__) . '/includes/api_auth.php';
$authContext = apiAuthenticate('mod-inventory', 'modInventoryApiRespond');

$body = file_get_contents('php://input');
if ($body === false || trim($body) === '') {
    modInventoryApiRespond(400, ['success' => false, 'error' => 'A JSON request body is required']);
}
$payload = json_decode($body, true);
if (
    json_last_error() !== JSON_ERROR_NONE ||
    !is_array($payload) ||
    !isset($payload['allycode']) ||
    !is_string($payload['allycode']) ||
    !preg_match('/^[0-9]{9}$/', $payload['allycode'])
) {
    modInventoryApiRespond(400, ['success' => false, 'error' => 'Invalid allycode; expected a 9-digit string']);
}

$tokenPath = '/home/pi/GuionBot/SERVER_SECRETS/web_commands.token';
if (!is_file($tokenPath) || !is_readable($tokenPath)) {
    error_log('Mod inventory API web commands token is missing or unreadable');
    modInventoryApiRespond(503, ['success' => false, 'error' => 'Mod inventory service is not configured']);
}
$token = trim((string) file_get_contents($tokenPath));
if ($token === '') {
    modInventoryApiRespond(503, ['success' => false, 'error' => 'Mod inventory service is not configured']);
}

$internalPayload = json_encode(['allycode' => $payload['allycode']]);
if ($internalPayload === false) {
    modInventoryApiRespond(500, ['success' => false, 'error' => 'Unable to encode request']);
}

$ch = curl_init('http://127.0.0.1:9000/ModInventory');
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        'Authorization: Bearer ' . $token,
    ],
    CURLOPT_POSTFIELDS => $internalPayload,
    CURLOPT_CONNECTTIMEOUT => 3,
    CURLOPT_TIMEOUT => 180,
]);
$response = curl_exec($ch);
$curlError = curl_error($ch);
$httpCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($response === false) {
    error_log('Mod inventory API web command connection failed: ' . $curlError);
    modInventoryApiRespond(502, ['success' => false, 'error' => 'Mod inventory service unavailable']);
}
$result = json_decode($response, true);
if (!is_array($result)) {
    error_log('Mod inventory API received an invalid web command response; HTTP ' . $httpCode);
    modInventoryApiRespond(502, ['success' => false, 'error' => 'Invalid mod inventory service response']);
}
if ($httpCode === 200 && array_key_exists('unequippedMod', $result)) {
    // The public response deliberately contains exactly one key.
    modInventoryApiRespond(200, ['unequippedMod' => $result['unequippedMod']], [
        'RateLimit-Limit' => (string)$authContext['limit'],
        'RateLimit-Remaining' => (string)$authContext['remaining'],
    ]);
}
if (in_array($httpCode, [400, 401, 502, 503], true)) {
    modInventoryApiRespond($httpCode, $result);
}
error_log('Mod inventory API received an unexpected internal service HTTP status: ' . $httpCode);
modInventoryApiRespond(502, ['success' => false, 'error' => 'Mod inventory service unavailable']);
