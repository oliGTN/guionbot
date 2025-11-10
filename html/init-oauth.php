<?php
session_start();

// check if the access toke is in a cookie
if(isset($_COOKIE['discord_access_token'])) {
    $cookie_data = json_decode( $_COOKIE['discord_access_token']);
    if(isset($cookie_data->access_token)) {
        $_SESSION['discord_access_token'] = $cookie_data;
        header("Location: process-oauth.php");
        exit();
    }
}

// no cookie, get a new token
include 'oauth_secret.php'; // defines $client_id

$discord_url = "https://discord.com/oauth2/authorize?client_id=".$client_id."&response_type=code&redirect_uri=https%3A%2F%2Fguionbot.fr%2Fprocess-oauth.php&scope=identify";

header("Location: $discord_url");
exit();

?>  
