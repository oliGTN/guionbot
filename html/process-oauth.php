<?php
require_once 'security.php';
require 'websitedb.php';
require 'guionbotdb.php';
include 'oauth_secret.php';

session_set_cookie_params(['lifetime'=>3600*24*7,'path'=>'/','secure'=>true,'httponly'=>true,'samesite'=>'Lax']);
session_start();

if (isset($_GET['code'])) {
    $state = $_GET['state'] ?? '';
    if (!is_string($state) || empty($_SESSION['oauth_state']) || !hash_equals($_SESSION['oauth_state'], $state)) {
        http_response_code(400);
        exit('Invalid OAuth state');
    }
    unset($_SESSION['oauth_state']);
}

if (!isset($_GET['code']) && isset($_SESSION['discord_access_token'])) {
    $token_data = $_SESSION['discord_access_token'];
    $access_token = $token_data->access_token ?? null;
    $refresh_token = $token_data->refresh_token ?? null;
} else {
    if (!isset($_GET['code']) || !is_string($_GET['code']) || $_GET['code'] === '') {
        header("Location: index.php"); exit();
    }
    $discord_code = $_GET['code'];
    $payload = ['code'=>$discord_code,'client_id'=>$client_id,'client_secret'=>$client_secret,'grant_type'=>'authorization_code','redirect_uri'=>'https://guionbot.fr/process-oauth.php','scope'=>'identify'];
    $ch = curl_init('https://discord.com/api/oauth2/token');
    curl_setopt_array($ch, [CURLOPT_POST=>true,CURLOPT_POSTFIELDS=>http_build_query($payload),CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>10]);
    $result = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    if ($result === false || $http_code < 200 || $http_code >= 300) {
        error_log('Discord token request failed: '.curl_error($ch).' HTTP '.$http_code);
        curl_close($ch); http_response_code(502); exit('Authentication service unavailable.');
    }
    curl_close($ch);
    $data = json_decode($result, true);
    if (!is_array($data) || empty($data['access_token']) || empty($data['refresh_token']) || empty($data['expires_in'])) {
        error_log('Invalid Discord token response'); http_response_code(502); exit('Authentication service unavailable.');
    }
    $access_token = $data['access_token'];
    $refresh_token = $data['refresh_token'];
    $expiry = time() + (int)$data['expires_in'];
    $cookie_data = json_encode(['access_token'=>$access_token,'refresh_token'=>$refresh_token,'expiry'=>$expiry]);
    setcookie('discord_access_token', $cookie_data, ['expires'=>$expiry,'path'=>'/','secure'=>true,'httponly'=>true,'samesite'=>'Lax']);
}

if (!$access_token) { http_response_code(401); exit('Authentication failed.'); }

$ch = curl_init('https://discord.com/api/users/@me');
curl_setopt_array($ch, [CURLOPT_HTTPHEADER=>['Authorization: Bearer '.$access_token,'Content-Type: application/x-www-form-urlencoded'],CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>10]);
$result = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);
if ($result === false || $http_code !== 200) {
    setcookie('discord_access_token','',['expires'=>time()-3600,'path'=>'/','secure'=>true,'httponly'=>true,'samesite'=>'Lax']);
    unset($_SESSION['discord_access_token']);
    http_response_code(401); exit('Authentication failed.');
}
$user = json_decode($result, true);
if (!is_array($user) || empty($user['id']) || !isset($user['global_name'])) { http_response_code(502); exit('Authentication service unavailable.'); }

session_regenerate_id(true);
$user_id = (string)$user['id'];
$user_name = (string)$user['global_name'];
$_SESSION['user_id'] = $user_id;
$_SESSION['user_name'] = $user_name;

try {
    $stmt = $conn->prepare("INSERT INTO users(user_id,name) VALUES(:user_id,:name) ON DUPLICATE KEY UPDATE name=:name_update");
    $stmt->execute([':user_id'=>$user_id,':name'=>$user_name,':name_update'=>$user_name]);
    $stmt = $conn->prepare("SELECT is_admin, sql_select FROM users WHERE user_id=:user_id");
    $stmt->execute([':user_id'=>$user_id]);
    $details = $stmt->fetch(PDO::FETCH_ASSOC) ?: [];
    $_SESSION['admin'] = !empty($details['is_admin']);
    $_SESSION['sql_select'] = !empty($details['sql_select']);

    $stmt = $conn_guionbot->prepare("SELECT players.allyCode AS allyCode, confirmed FROM players JOIN player_discord ON player_discord.allyCode=players.allyCode WHERE discord_id=:discord_id");
    $stmt->execute([':discord_id'=>$user_id]);
    $user_allyCodes = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $stmt = $conn_guionbot->prepare("SELECT guildId, MAX(confirmed) AS confirmed FROM players JOIN player_discord ON player_discord.allyCode=players.allyCode WHERE discord_id=:discord_id GROUP BY guildId");
    $stmt->execute([':discord_id'=>$user_id]);
    $user_guilds = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $stmt = $conn->prepare("SELECT guild_id FROM user_guilds WHERE user_id=:user_id");
    $stmt->execute([':user_id'=>$user_id]);
    $user_bonus_guilds = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    error_log('OAuth database error: '.$e->getMessage()); http_response_code(500); exit('An internal error occurred.');
}

$_SESSION['allyCodes']=[]; foreach($user_allyCodes as $row) $_SESSION['allyCodes'][$row['allyCode']]=$row['confirmed'];
$_SESSION['user_guilds']=[]; foreach($user_guilds as $row) $_SESSION['user_guilds'][$row['guildId']]=$row['confirmed'];
$_SESSION['user_bonus_guilds']=[]; foreach($user_bonus_guilds as $row) $_SESSION['user_bonus_guilds'][]=$row['guild_id'];

$return = safe_return_path($_SESSION['login_return'] ?? 'dashboard.php');
unset($_SESSION['login_return']);
header('Location: '.$return);
exit();
?>
