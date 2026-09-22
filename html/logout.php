<?php
session_start();
session_destroy();

$cookie_options = [
    'expires' => time() - 3600,
    'path' => '/',
    'secure' => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
    'httponly' => true,
    'samesite' => 'Lax',
];
setcookie('discord_access_token', '', $cookie_options);
header("Location: index.php");
exit();
?>