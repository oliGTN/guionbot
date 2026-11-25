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
    $requestParams = [];
    if (trim($raw) !== '') {
        $request = json_decode($raw);
        if (json_last_error() !== JSON_ERROR_NONE || !($request instanceof stdClass)) {
            rpcApiRespond(400, ['success' => false, 'error' => 'Request body must be a JSON object']);
        }
        $requestParams = get_object_vars($request);
    }

    // Only tb-events accepts a public request parameter. Guild/account
    // identity always comes from the API key configuration below.
    if ($endpoint === 'tb-events') {
        $unknownParams = array_diff(array_keys($requestParams), ['earliest_timestamp']);
        if (count($unknownParams) > 0) {
            rpcApiRespond(400, ['success' => false, 'error' => 'Unsupported request parameter']);
        }
        if (array_key_exists('earliest_timestamp', $requestParams) &&
            (!is_int($requestParams['earliest_timestamp']) || $requestParams['earliest_timestamp'] < 0)) {
            rpcApiRespond(400, ['success' => false, 'error' => 'Invalid earliest_timestamp']);
        }
    } elseif (count($requestParams) > 0) {
        rpcApiRespond(400, ['success' => false, 'error' => 'Request body must be empty or an empty JSON object']);
    }

    require_once dirname(__DIR__) . '/includes/api_auth.php';
    $auth = apiAuthenticate($authName, 'rpcApiRespond');
    $config = $auth['config'];
    $guildId = $config['guild_id'] ?? null;
    $allyCode = $config['allyCode'] ?? null;

    // Missing per-key values are deliberately forwarded as JSON null.
    // Validate only values that are explicitly configured.
    if (($guildId !== null && (!is_string($guildId) || !preg_match('/^[A-Za-z0-9_-]{1,22}$/', $guildId))) ||
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
        CURLOPT_POSTFIELDS => json_encode(array_merge(
            ['guild_id' => $guildId, 'allyCode' => $allyCode],
            $requestParams
        )),
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
