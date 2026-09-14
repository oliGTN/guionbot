<?php
require_once 'security.php';

session_set_cookie_params([
    'lifetime' => 3600 * 24 * 7,
    'path' => '/',
    'secure' => true,
    'httponly' => true,
    'samesite' => 'Lax',
]);
session_start();

require 'websitedb.php';

header('Content-Type: application/json; charset=utf-8');

if (!isset($_SESSION['user_id'])) {
    http_response_code(401);
    echo json_encode([
        'err_code' => 1,
        'err_txt' => 'You need to be logged in order to use this page',
    ]);
    exit();
}

if (empty($_SESSION['admin'])) {
    http_response_code(403);
    echo json_encode([
        'err_code' => 1,
        'err_txt' => 'You need to be logged as an Admin in order to use this page',
    ]);
    exit();
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode([
        'err_code' => 1,
        'err_txt' => 'POST required',
    ]);
    exit();
}

// Existing dashboard JavaScript does not submit a CSRF form token.
// Enforce same-origin for this state-changing JSON endpoint until
// the client is migrated to a token header.
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
$referer = $_SERVER['HTTP_REFERER'] ?? '';
$allowed_origin = 'https://guionbot.fr';

if ($origin !== '') {
    if (strcasecmp(rtrim($origin, '/'), $allowed_origin) !== 0) {
        http_response_code(403);
        echo json_encode([
            'err_code' => 1,
            'err_txt' => 'Invalid request origin',
        ]);
        exit();
    }
} elseif ($referer !== '' && strpos($referer, $allowed_origin . '/') !== 0) {
    http_response_code(403);
    echo json_encode([
        'err_code' => 1,
        'err_txt' => 'Invalid request origin',
    ]);
    exit();
}

$body = file_get_contents('php://input');
$_POST = json_decode($body, true);

if (!is_array($_POST)) {
    http_response_code(400);
    echo json_encode([
        'err_code' => 1,
        'err_txt' => 'Invalid JSON',
    ]);
    exit();
}

$user_id = $_POST['user_id'] ?? null;
$guild_id = $_POST['guild_id'] ?? null;

if (
    !is_string($user_id)
    || !preg_match('/^\d+$/', $user_id)
    || !is_string($guild_id)
    || !preg_match('/^[A-Za-z0-9_-]{1,22}$/', $guild_id)
) {
    http_response_code(400);
    echo json_encode([
        'err_code' => 1,
        'err_txt' => 'Invalid user or guild ID',
    ]);
    exit();
}

try {
    if (isset($_POST['associate_guild'])) {
        $stmt = $conn->prepare(
            'SELECT 1 FROM user_guilds WHERE user_id=:user_id AND guild_id=:guild_id'
        );
        $stmt->execute([
            'user_id' => $user_id,
            'guild_id' => $guild_id,
        ]);

        if (!$stmt->fetchColumn()) {
            $stmt = $conn->prepare(
                'INSERT INTO user_guilds (user_id,guild_id) VALUES (:user_id,:guild_id)'
            );
            $stmt->execute([
                'user_id' => $user_id,
                'guild_id' => $guild_id,
            ]);
        }

        if ((string) $_SESSION['user_id'] === $user_id) {
            if (!isset($_SESSION['user_bonus_guilds'])) {
                $_SESSION['user_bonus_guilds'] = [];
            }

            if (!in_array($guild_id, $_SESSION['user_bonus_guilds'], true)) {
                $_SESSION['user_bonus_guilds'][] = $guild_id;
            }
        }
    } elseif (isset($_POST['deassociate_guild'])) {
        $stmt = $conn->prepare(
            'DELETE FROM user_guilds WHERE user_id=:user_id AND guild_id=:guild_id'
        );
        $stmt->execute([
            'user_id' => $user_id,
            'guild_id' => $guild_id,
        ]);

        if ((string) $_SESSION['user_id'] === $user_id) {
            $_SESSION['user_bonus_guilds'] = array_values(
                array_diff($_SESSION['user_bonus_guilds'] ?? [], [$guild_id])
            );
        }
    } else {
        http_response_code(400);
        echo json_encode([
            'err_code' => 1,
            'err_txt' => 'Unknown operation',
        ]);
        exit();
    }
} catch (PDOException $e) {
    error_log('Dashboard request DB error: ' . $e->getMessage());
    http_response_code(500);
    echo json_encode([
        'err_code' => 1,
        'err_txt' => 'Database error',
    ]);
    exit();
}

echo json_encode([
    'err_code' => 0,
    'err_txt' => '',
]);
?>
