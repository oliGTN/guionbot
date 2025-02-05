<?php
// input for this file is $guild_id
//echo (isset($_SESSION['user_id']));
//echo (isset($_SESSION['user_guilds']));
if (isset($_SESSION['user_id'])) {
    // Define if user is member (or allowed) of the guild
    $isMyGuild = in_array($guild_id,array_keys($_SESSION['user_guilds']),true);
    $isMyGuildConfirmed = $isMyGuild && $_SESSION['user_guilds'][$guild_id];
    $isBonusGuild = in_array($guild_id,$_SESSION['user_bonus_guilds'],true);
    //echo "isMyGuild=".$isMyGuild;
    //echo "isMyGuildConfirmed=".$isMyGuildConfirmed;
    //echo "isBonusGuild=".$isBonusGuild;

    // --------------- GET USER RIGHTS FOR THIS GUILD -----------
    // Prepare the SQL query
    $query = "SELECT max(guildMemberLevel)>2 AS isOfficer FROM players";
    $query .= " JOIN player_discord ON (player_discord.allyCode=players.allyCode)";
    $query .= " WHERE guildId='".$guild_id."'";
    $query .= " AND discord_id='".$_SESSION['user_id']."'";
    $query .= " GROUP BY guildId";
    //error_log("query = ".$query);
    try {
        // Prepare the SQL query to fetch the player information
        $stmt = $conn_guionbot->prepare($query);
        $stmt->execute();

        // Fetch all the results as an associative array
        $players = $stmt->fetchAll(PDO::FETCH_ASSOC);

    } catch (PDOException $e) {
        echo "Error fetching guild data: " . $e->getMessage();
    }
    if (count($players)>0) {
        $player = array_values($players)[0];
        $isOfficer = $player['isOfficer'];
    } else {
        $isOfficer = false;
    }
    //echo "isOfficer=".$isOfficer;
} else {
    $isMyGuild = false;
    $isMyGuildConfirmed = false;
    $isBonusGuild = false;
    $isOfficer = false;
}
?>
