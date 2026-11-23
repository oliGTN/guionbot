<?php
declare(strict_types=1);

/**
 * Shared proxy for read-only RPC-backed API endpoints.
 * Public response bodies are gzip-compressed when the client supports it.
 */

function rpcApiRespond(int $status, array $payload, array $headers = []): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, private');
    header('Vary: Accept-Encoding');
    header('X-Content-Type-Options: nosniff');
    foreach ($headers as $name => $value) {
        header($name . ': ' . $value);
    }

    $json = json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    if ($json === false) {
        http_response_code(500);
        $json = '{"success":false,"error":"Unable to encode response"}';
    }

    $acceptEncoding = (string)($_SERVER['HTTP_ACCEPT_ENCODING'] ?? '');
    if (strpos($acceptEncoding, 'gzip') !== false && function_exists('gzencode')) {
        $compressed = gzencode($json, 6);
        if ($compressed !== false) {
            header('Content-Encoding: gzip');
            header('Content-Length: ' . strlen($compressed));
            echo $compressed;
            exit;
        }
    }
    echo $json;
    exit;
}

function rpcApiRun(string $endpoint, string $authName): void
{
    $isHttps = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== '' &&
        strtolower((string)$_SERVER['HTTPS']) !== 'off';
    if (!$isHttps) {
        rpcApiRespond(403, ['success' => false, 'error' => 'HTTPS required']);
    }
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
        rpcApiRespond(405, ['success' => false, 'error' => 'Method not allowed'], ['Allow' => 'POST']);
    }
    if ((int)($_SERVER['CONTENT_LENGTH'] ?? 0) > 1024) {
        rpcApiRespond(413, ['success' => false, 'error' => 'Request body too large']);
    }

    $raw = file_get_contents('php://input');
    if ($raw === false) {
        rpcApiRespond(400, ['success' => false, 'error' => 'Invalid request body']);
    }
    if (trim($raw) !== '') {
        $request = json_decode($raw);
        if (json_last_error() !== JSON_ERROR_NONE || !($request instanceof stdClass) ||
            count(get_object_vars($request)) !== 0) {
            rpcApiRespond(400, ['success' => false, 'error' => 'Request body must be empty or an empty JSON object']);
        }
    }

    require_once dirname(__DIR__) . '/includes/api_auth.php';
    $auth = apiAuthenticate($authName, 'rpcApiRespond');
    $config = $auth['config'];
    $guildId = $config['guild_id'] ?? null;
    $allyCode = $config['allyCode'] ?? null;

    // Missing per-key values are deliberately forwarded as JSON null.
    // Validate only values that are explicitly configured.
    if (($guildId !== null && (!is_string($guildId) || !preg_match('/^[0-9]{1,24}$/', $guildId))) ||
        ($allyCode !== null && (!is_string($allyCode) || !preg_match('/^[0-9]{9}$/', $allyCode)))) {
        rpcApiRespond(503, ['success' => false, 'error' => 'API key has an invalid guild_id or allyCode']);
    }

    $tokenPath = '/home/pi/GuionBot/SERVER_SECRETS/web_commands.token';
    if (!is_file($tokenPath) || !is_readable($tokenPath)) {
        error_log('RPC API proxy: internal command token is unavailable');
        rpcApiRespond(503, ['success' => false, 'error' => 'Service unavailable']);
    }
    $token = trim((string)file_get_contents($tokenPath));
    if ($token === '') {
        error_log('RPC API proxy: internal command token is empty');
        rpcApiRespond(503, ['success' => false, 'error' => 'Service unavailable']);
    }

    $ch = curl_init('http://127.0.0.1:9000/' . $endpoint);
    if ($ch === false) {
        rpcApiRespond(503, ['success' => false, 'error' => 'Service unavailable']);
    }
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $token
        ],
        CURLOPT_POSTFIELDS => json_encode(['guild_id' => $guildId, 'allyCode' => $allyCode]),
        CURLOPT_CONNECTTIMEOUT => 3,
        CURLOPT_TIMEOUT => 180
    ]);
    $body = curl_exec($ch);
    $curlError = curl_error($ch);
    $status = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($body === false) {
        error_log('RPC API proxy request failed: ' . $curlError);
        rpcApiRespond(502, ['success' => false, 'error' => 'Unable to retrieve game data']);
    }
    $decoded = json_decode($body, true);
    if (!is_array($decoded)) {
        error_log('RPC API proxy received invalid JSON; HTTP ' . $status);
        rpcApiRespond(502, ['success' => false, 'error' => 'Invalid response from game data service']);
    }
    if ($status !== 200) {
        $message = $decoded['err_txt'] ?? 'Unable to retrieve game data';
        rpcApiRespond($status >= 400 && $status < 600 ? $status : 502,
            ['success' => false, 'error' => $message]);
    }

    rpcApiRespond(200, $decoded, [
        'RateLimit-Limit' => (string)$auth['limit'],
        'RateLimit-Remaining' => (string)$auth['remaining']
    ]);
}
