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

require_once dirname(__DIR__) . '/includes/api_auth.php';
$authContext = apiAuthenticate('tb-platoon-deploy', 'tbPlatoonApiRespond', 'deploy');
$config = $authContext['config'];

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
// Preserve deployment outcomes and backend gateway errors from the internal service.
if (in_array($httpCode, [200, 202, 207, 502, 504], true)) {
    // Preserve the EA One-Time Code action response (HTTP 202) unchanged.
    tbPlatoonApiRespond($httpCode, $result);
}
error_log('TB platoon deploy API received an unexpected internal service HTTP status: ' . $httpCode);
tbPlatoonApiRespond(502, ['success' => false, 'err_code' => 502, 'err_txt' => 'Deployment service unavailable']);
