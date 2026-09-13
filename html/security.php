<?php
/**
 * Central security helpers for the public PHP site.
 */

function h($value): string {
    return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function get_required_guild_id(): string {
    $value = $_GET['gid'] ?? null;
    if (!is_string($value) || !preg_match('/^[A-Za-z0-9_-]{1,22}$/', $value)) {
        http_response_code(400);
        exit('Invalid guild ID');
    }
    return $value;
}

function get_required_ally_code(): string {
    $value = $_GET['ac'] ?? null;
    if (!is_string($value) || !preg_match('/^\d{9}$/', $value)) {
        http_response_code(400);
        exit('Invalid ally code');
    }
    return $value;
}

function get_positive_int(string $name, int $default = 1): int {
    $value = $_GET[$name] ?? null;
    if ($value === null || $value === '') {
        return $default;
    }
    if (!is_string($value) || !preg_match('/^[1-9]\d*$/', $value)) {
        http_response_code(400);
        exit('Invalid parameter');
    }
    $int = filter_var($value, FILTER_VALIDATE_INT, ['options' => ['min_range' => 1]]);
    if ($int === false) {
        http_response_code(400);
        exit('Invalid parameter');
    }
    return $int;
}

function safe_return_path($value): string {
    if (!is_string($value) || $value === '') {
        return 'dashboard.php';
    }
    // Only allow same-site absolute paths. Reject protocol-relative URLs,
    // backslashes and control characters.
    if ($value[0] !== '/' || str_starts_with($value, '//') || str_contains($value, '\\') || preg_match('/[\x00-\x1F\x7F]/', $value)) {
        return 'dashboard.php';
    }
    return $value;
}

function csrf_token(): string {
    if (empty($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

function require_csrf_token(): void {
    $token = $_POST['csrf_token'] ?? '';
    if (!is_string($token) || empty($_SESSION['csrf_token']) || !hash_equals($_SESSION['csrf_token'], $token)) {
        http_response_code(403);
        exit('Invalid CSRF token');
    }
}
?>
