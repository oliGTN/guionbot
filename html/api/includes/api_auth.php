<?php
declare(strict_types=1);

/**
 * Shared API client authentication, endpoint authorization and per-client rate limits.
 *
 * Config format in SERVER_SECRETS/web_api.php:
 * 'api_clients' => [
 *   'existing' => ['key_hash' => '<sha256 hex>', 'enabled' => true,
 *     'endpoints' => ['*'], 'rate_limits' => ['read' => ['per_minute' => 5, 'per_day' => 1000],
 *       'deploy' => ['per_minute' => 20, 'per_day' => 100]]],
 *   'new_client' => ['key_hash' => '<sha256 hex>', 'enabled' => true,
 *     'endpoints' => ['tb-history']]
 * ]
 */
function apiAuthenticate(string $endpoint, callable $respond, string $bucket = 'read'): array
{
    $configPath = '/home/pi/GuionBot/SERVER_SECRETS/web_api.php';
    if (!is_file($configPath) || !is_readable($configPath)) {
        error_log('API configuration is missing or unreadable');
        $respond(503, ['success' => false, 'error' => 'Service unavailable']);
    }
    $config = require $configPath;
    if (!is_array($config) || empty($config['guild_id']) || !is_string($config['guild_id'])) {
        error_log('API configuration has an invalid format');
        $respond(503, ['success' => false, 'error' => 'Service unavailable']);
    }

    $headers = function_exists('getallheaders') ? getallheaders() : [];
    $authorization = '';
    foreach ($headers as $name => $value) {
        if (strcasecmp((string)$name, 'Authorization') === 0) {
            $authorization = is_string($value) ? trim($value) : '';
            break;
        }
    }
    if ($authorization === '') {
        $authorization = trim((string)($_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? ''));
    }
    if (!preg_match('/^Bearer\s+([^\s]+)$/i', $authorization, $matches)) {
        $respond(401, ['success' => false, 'error' => 'Unauthorized'], ['WWW-Authenticate' => 'Bearer']);
    }
    $presentedKey = $matches[1];
    $presentedHash = hash('sha256', $presentedKey);
    $clientId = null;
    $client = null;

    if (isset($config['api_clients']) && is_array($config['api_clients'])) {
        foreach ($config['api_clients'] as $id => $candidate) {
            if (!is_string($id) || !is_array($candidate) ||
                !isset($candidate['key_hash']) || !is_string($candidate['key_hash']) ||
                !preg_match('/^[a-f0-9]{64}$/i', $candidate['key_hash'])) {
                continue;
            }
            if (hash_equals(strtolower($candidate['key_hash']), $presentedHash)) {
                $clientId = $id;
                $client = $candidate;
                break;
            }
        }
    } elseif (isset($config['api_key']) && is_string($config['api_key']) &&
        $config['api_key'] !== '' && hash_equals($config['api_key'], $presentedKey)) {
        // Temporary compatibility while the server-side secret file is migrated.
        $clientId = 'legacy';
        $client = ['enabled' => true, 'endpoints' => ['*']];
    }

    if ($clientId === null || !is_array($client) || empty($client['enabled'])) {
        $respond(401, ['success' => false, 'error' => 'Unauthorized'], ['WWW-Authenticate' => 'Bearer']);
    }

    $allowed = $client['endpoints'] ?? [];
    if (!is_array($allowed) || (!in_array('*', $allowed, true) && !in_array($endpoint, $allowed, true))) {
        $respond(403, ['success' => false, 'error' => 'Endpoint not permitted']);
    }

    $defaults = $bucket === 'deploy'
        ? ['per_minute' => 20, 'per_day' => 100]
        : ['per_minute' => 5, 'per_day' => 1000];
    $limits = $client['rate_limits'][$bucket] ?? $defaults;
    if (!is_array($limits)) $limits = $defaults;
    $perMinute = max(1, (int)($limits['per_minute'] ?? $defaults['per_minute']));
    $perDay = max(1, (int)($limits['per_day'] ?? $defaults['per_day']));

    // Separate read/deploy buckets, shared by all endpoints in each bucket.
    $rateFile = rtrim(sys_get_temp_dir(), DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR .
        'guionbot_api_rate_' . hash('sha256', $clientId . ':' . $bucket) . '.json';
    $rateHandle = @fopen($rateFile, 'c+');
    if ($rateHandle === false || !flock($rateHandle, LOCK_EX)) {
        if (is_resource($rateHandle)) fclose($rateHandle);
        error_log('API rate-limit storage is unavailable');
        $respond(503, ['success' => false, 'error' => 'Service unavailable']);
    }

    $now = time();
    $state = json_decode((string)stream_get_contents($rateHandle), true);
    $timestamps = [];
    foreach (($state['timestamps'] ?? []) as $timestamp) {
        if (is_int($timestamp) && $timestamp > $now - 86400 && $timestamp <= $now) {
            $timestamps[] = $timestamp;
        }
    }
    $recent = array_values(array_filter($timestamps, static function ($timestamp) use ($now) {
        return $timestamp > $now - 60;
    }));
    $rateError = count($timestamps) >= $perDay ? 'Daily request limit exceeded' :
        (count($recent) >= $perMinute ? 'Rate limit exceeded' : null);
    $retryAfter = 1;
    if ($rateError !== null) {
        $daily = $rateError === 'Daily request limit exceeded';
        $list = $daily ? $timestamps : $recent;
        sort($list, SORT_NUMERIC);
        $retryAfter = max(1, $list[0] + ($daily ? 86400 : 60) - $now + 1);
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
        $respond(429, ['success' => false, 'error' => $rateError], [
            'Retry-After' => (string)$retryAfter,
            'RateLimit-Limit' => (string)$perMinute,
            'RateLimit-Remaining' => '0'
        ]);
    }

    return [
        'config' => $config,
        'client_id' => $clientId,
        'remaining' => max(0, $perMinute - count($recent) - 1),
        'limit' => $perMinute
    ];
}
