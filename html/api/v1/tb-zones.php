<?php
declare(strict_types=1);

/**
 * Read-only API: current unfinished TB zones for one configured guild.
 *
 * The API key and fixed guild ID are loaded from /home/pi/GuionBot/SERVER_SECRETS/web_api.php,
 * outside the web document root. Database settings and the PDO connection are
 * reused from html/guionbotdb.php. See docs/tb-zones-api.md.
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

require_once dirname(__DIR__) . '/includes/api_auth.php';
$authContext = apiAuthenticate('tb-zones', 'apiRespond');
$config = $authContext['config'];

try {
    // Reuse the existing website DB configuration and PDO connection.
    // This file defines $host, $dbname, $username, $password and $conn_guionbot.
    require_once dirname(__DIR__, 2) . '/guionbotdb.php';

    if (!isset($conn_guionbot) || !($conn_guionbot instanceof PDO)) {
        throw new RuntimeException('Website database connection is unavailable');
    }

    // The guild ID is server configuration, never client input.
    $sql = 'SELECT z.zone_name, z.score_step1, z.score_step2, z.score_step3, z.score,
                   CASE
                       WHEN z.score >= z.score_step3 THEN 3
                       WHEN z.score >= z.score_step2 THEN 2
                       WHEN z.score >= z.score_step1 THEN 1
                       ELSE 0
                   END AS stars,
                   z.round = h.current_round AS open
            FROM tb_zones AS z
            INNER JOIN tb_history AS h ON h.id = z.tb_id
            WHERE h.guild_id = :guild_id
              AND h.stars_final IS NULL
            LIMIT 5001';
    $statement = $conn_guionbot->prepare($sql);
    $statement->execute([':guild_id' => $config['guild_id']]);
    $rows = $statement->fetchAll();
} catch (PDOException $exception) {
    // Do not send SQL details, credentials, or internal database errors to the client.
    error_log('TB zones API database query failed; SQLSTATE=' . (string) $exception->getCode());
    apiRespond(500, ['success' => false, 'error' => 'Unable to retrieve zone data']);
} catch (Throwable $exception) {
    error_log('TB zones API database setup failed; exception=' . get_class($exception));
    apiRespond(500, ['success' => false, 'error' => 'Unable to retrieve zone data']);
}

if (count($rows) > 5000) {
    apiRespond(503, ['success' => false, 'error' => 'Result exceeds the API row limit']);
}

apiRespond(200, [
    'success' => true,
    'count' => count($rows),
    'data' => $rows,
], [
    'RateLimit-Limit' => (string)$authContext['limit'],
    'RateLimit-Remaining' => (string)$authContext['remaining'],
]);
