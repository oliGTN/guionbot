<?php
include 'oauth_secret.php'; // defines $client_id

$discord_url = "https://discord.com/oauth2/authorize?client_id=".$client_id."&response_type=code&redirect_uri=https%3A%2F%2Fguionbot.fr%2Fprocess-oauth.php&scope=identify";

header("Location: $discord_url");
exit();

?>  
