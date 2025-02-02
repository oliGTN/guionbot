<?php
require 'websitedb.php';  // Include the database connection for guionbotdb
require 'guionbotdb.php';  // Include the database connection for guionbotdb

include 'oauth_secret.php'; // defines $client_id and $client_secret

if(!isset($_GET['code'])){
    error_log("No discord code, redirect to index.php");
    header("Location: index.php");
    exit();
}

$discord_code = $_GET['code'];

$payload = [
    'code'=>$discord_code,
    'client_id'=>$client_id,
    'client_secret'=>$client_secret,
    'grant_type'=>'authorization_code',
    'redirect_uri'=>'https://guionbot.fr/process-oauth.php',!
    'scope'=>'identify'
   ];

//print_r($payload);

$payload_string = http_build_query($payload);
$discord_token_url = "https://discordapp.com/api/oauth2/token";

$ch = curl_init();

curl_setopt($ch, CURLOPT_URL, $discord_token_url);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $payload_string);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

//curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
//curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$result = curl_exec($ch);

if(!$result){
    echo curl_error($ch);
}

$result = json_decode($result, true);
$access_token = $result['access_token'];

$discord_users_url = "https://discordapp.com/api/users/@me";
$header = array("Authorization: Bearer $access_token", "Content-Type: application/x-www-form-urlencoded");

$ch = curl_init();
curl_setopt($ch, CURLOPT_HTTPHEADER, $header);
curl_setopt($ch, CURLOPT_URL, $discord_users_url);
curl_setopt($ch, CURLOPT_POST, false);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$result = curl_exec($ch);

if(!$result){
    echo curl_error($ch);
}

$result = json_decode($result, true);
$user_id = $result['id'];
$user_name = $result['global_name'];

session_start();
$_SESSION['user_id'] = $user_id;
$_SESSION['user_name'] = $user_name;
print_r($_SESSION);

try {
    // Prepare SQL to create the user if not already, and store the name
    $query = "INSERT INTO users(user_id, name)";
    $query .= " VALUES('".$user_id."', '".$user_name."')";
    $query .= " ON DUPLICATE KEY UPDATE name='".$user_name."'";
    error_log($query);
    $stmt = $conn->prepare($query);
    $stmt->execute();

} catch (PDOException $e) {
    echo "Error: " . $e->getMessage();
}    


try {
    // Prepare SQL to check if user is admin
    $query = "SELECT is_admin FROM users WHERE user_id='".$user_id."'";
    error_log($query);
    $stmt = $conn->prepare($query);
    $stmt->execute();
    $user_admin = $stmt->fetch(PDO::FETCH_ASSOC);
    if ($user_admin) {
        //error_log("user_admin=".$user_admin['is_admin']);
        $_SESSION['admin'] = $user_admin['is_admin'];  // Mark the user as an admin if applicable
    }
} catch (PDOException $e) {
    echo "Error: " . $e->getMessage();
}    

try {
    // Prepare SQL to get user allyCodes
    $query = "SELECT players.allyCode AS allyCode, confirmed";
    $query .= " FROM players";
    $query .= " JOIN player_discord ON player_discord.allyCode = players.allyCode";
    $query .= " WHERE discord_id='".$user_id."'";
    error_log($query);
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();
    $user_allyCodes = $stmt->fetchAll(PDO::FETCH_ASSOC);
    //print_r($user_data);

    // Prepare SQL to get user guilds
    $query = "SELECT guildId, max(confirmed) AS confirmed";
    $query .= " FROM players";
    $query .= " JOIN player_discord ON player_discord.allyCode = players.allyCode";
    $query .= " WHERE discord_id='".$user_id."'";
    $query .= " GROUP BY guildId";
    //error_log($query);
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();
    $user_guilds = $stmt->fetchAll(PDO::FETCH_ASSOC);
    //print_r($user_data);

    // Prepare SQL to get user bonus guilds
    $query = "SELECT guild_id";
    $query .= " FROM user_guilds";
    $query .= " WHERE user_id='".$user_id."'";
    //$error_log($query);
    $stmt = $conn->prepare($query);
    $stmt->execute();
    $user_bonus_guilds = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    echo "Error: " . $e->getMessage();
}

// store allyCodes in session data
$_SESSION['allyCodes'] = [];
foreach($user_allyCodes as $user_allyCode) {
    $_SESSION['allyCodes'][$user_allyCode['allyCode']] = $user_allyCode['confirmed'];
}   

// store guilds in session data
$_SESSION['user_guilds'] = [];
foreach($user_guilds as $user_guild) {
    $_SESSION['user_guilds'][$user_guild['guildId']] = $user_guild['confirmed'];
}

// store bonus guilds in session data
$_SESSION['user_bonus_guilds'] = [];
foreach($user_bonus_guilds as $user_bonus_guild) {
    array_push($_SESSION['user_bonus_guilds'], $user_bonus_guild['guild_id']);
}
//print_r($_SESSION);

//Process comes to an end, redirct to dashboard page
header("Location: dashboard.php");  // Redirect to dashboard after login
exit();

?>

