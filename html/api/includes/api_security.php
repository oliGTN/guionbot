<?php
declare(strict_types=1);

/**
 * Append-only security events for the public GuionBot API.
 * Never pass credentials or raw request bodies to this logger.
 */
function apiSecurityLog(string $eventType, string $severity = 'LOW', array $details = []): void
{
    $directory = '/var/log/guionbot-api-security';
    if (!is_dir($directory) || !is_writable($directory)) {
        error_log('API security logger is unavailable');
        return;
    }

    $uri = (string)($_SERVER['REQUEST_URI'] ?? '');
    $path = parse_url($uri, PHP_URL_PATH);
    $status = http_response_code() ?: 200;\n    if ($status === 200) {\n        if ($eventType === 'MALFORMED_AUTH' || $eventType === 'INVALID_API_KEY') $status = 401;\n        elseif ($eventType === 'ENDPOINT_FORBIDDEN') $status = 403;\n        elseif ($eventType === 'RATE_LIMIT_EXCEEDED') $status = 429;\n    }\n\n    $record = [
        'timestamp' => gmdate('Y-m-d\TH:i:s\Z'),
        'event_type' => $eventType,
        'severity' => $severity,
        'ip' => (string)($_SERVER['REMOTE_ADDR'] ?? 'unknown'),
        'method' => (string)($_SERVER['REQUEST_METHOD'] ?? 'unknown'),
        'path' => is_string($path) ? substr($path, 0, 512) : '',
        'status' => $status,
        'client_id' => $GLOBALS['apiSecurityClientId'] ?? null,
        'details' => $details
    ];

    $file = $directory . '/events-' . gmdate('Y-m-d') . '.jsonl';
    $handle = @fopen($file, 'ab');
    if ($handle === false) {
        error_log('Unable to open API security event log');
        return;
    }
    if (flock($handle, LOCK_EX)) {
        fwrite($handle, json_encode($record, JSON_UNESCAPED_SLASHES | JSON_INVALID_UTF8_SUBSTITUTE) . "\n");
        fflush($handle);
        flock($handle, LOCK_UN);
    }
    fclose($handle);
}
