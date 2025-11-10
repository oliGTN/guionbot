<!-- source video: https://www.youtube.com/watch?v=w5ZLlnid8g0  -->
<?php
require 'websitedb.php';  // Include the database connection for guionbotdb
require 'guionbotdb.php';  // Include the database connection for guionbotdb

include 'oauth_secret.php'; // defines $client_id and $client_secret

// check if there is an access token in the session 
// (set from the cookie in init-oauth)
session_start();
if(!isset($_GET['code']) && isset($_SESSION['discord_access_token'])) {
    $access_token = $_SESSION['discord_access_token']->access_token;
    $refresh_token = $_SESSION['discord_access_token']->refresh_token;

} else {
    // no cookie, need to use the code from init-ouath
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

    $result = curl_exec($ch);

    if(!$result){
        echo curl_error($ch);
    }

    // get tokens and store in cookies
    $result = json_decode($result, true);
    $access_token = $result['access_token'];
    $refresh_token = $result['refresh_token'];
    $expires_in = $result['expires_in'];
    $expiry = time()+$expires_in;
    $cookie_data = (object) array( "access_token"=> $access_token, "refresh_token"=> $refresh_token, "expiry"=> $expiry);
    setcookie('discord_access_token', json_encode( $cookie_data), $expiry, "/");
}

// use token to get discord data
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

    // delete the cookie
    setcookie('discord_access_token', "", time()-3600, "/");
    unset($_SESSION['discord_access_token']);
    unset($_COOKIE['discord_access_token']);
}

$result = json_decode($result, true);
$user_id = $result['id'];
$user_name = $result['global_name'];

$_SESSION['user_id'] = $user_id;
$_SESSION['user_name'] = $user_name;
//print_r($_SESSION);

try {
    // Prepare SQL to create the user if not already, and store the name
    $query = "INSERT INTO users(user_id, name)";
    $query .= " VALUES('".$user_id."', '".$user_name."')";
    $query .= " ON DUPLICATE KEY UPDATE name='".$user_name."'";
    //error_log($query);
    $stmt = $conn->prepare($query);
    $stmt->execute();

} catch (PDOException $e) {
    echo "Error: " . $e->getMessage();
}    

try {
    // Prepare SQL to check if user is admin
    $query = "SELECT is_admin, sql_select FROM users WHERE user_id='".$user_id."'";
    //error_log($query);
    $stmt = $conn->prepare($query);
    $stmt->execute();
    $user_details = $stmt->fetch(PDO::FETCH_ASSOC);
    error_log(print_r($user_details, true));
    if ($user_details) {
        $_SESSION['admin'] = $user_details['is_admin'];  // Mark the user as an admin if applicable
        $_SESSION['sql_select'] = $user_details['sql_select'];  // Mark the user with sql SELECT rights
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
    //error_log($query);
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

