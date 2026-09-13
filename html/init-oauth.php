<?php
require_once 'security.php';
session_set_cookie_params(['lifetime'=>3600*24*7,'path'=>'/','secure'=>true,'httponly'=>true,'samesite'=>'Lax']);
session_start();

if (isset($_GET['return'])) {
    $_SESSION['login_return'] = safe_return_path($_GET['return']);
}

if (isset($_COOKIE['discord_access_token'])) {
    $cookie_data = json_decode($_COOKIE['discord_access_token']);
    if (is_object($cookie_data) && isset($cookie_data->access_token, $cookie_data->refresh_token, $cookie_data->expiry)) {
        $_SESSION['discord_access_token'] = $cookie_data;
        header("Location: process-oauth.php");
        exit();
    }
}

$_SESSION['oauth_state'] = bin2hex(random_bytes(32));
include 'oauth_secret.php';
$discord_url = 'https://discord.com/oauth2/authorize?client_id='.rawurlencode($client_id).'&response_type=code&redirect_uri='.rawurlencode('https://guionbot.fr/process-oauth.php').'&scope=identify&state='.rawurlencode($_SESSION['oauth_state']);
header("Location: $discord_url");
exit();
?>
