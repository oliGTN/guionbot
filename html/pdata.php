<?php
// --------------- GET GUILD BASIC DATA -----------
// INPUT for the file is $allycode
//
// Prepare the SQL query
$query = "SELECT players.playerId AS id, name, guildId AS guild_id, guildName AS guild_name, guildMemberLevel,";
$query .= " level, char_gp, ship_gp, grand_arena_rank, poUTCOffsetMinutes,";
$query .= " modq, statq FROM players";
$query .= " WHERE allyCode=".$allycode;
#error_log("query = ".$query);
try {
    // Prepare the SQL query to fetch the player information
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $players = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $player = array_values($players)[0];

} catch (PDOException $e) {
    echo "Error fetching player data: " . $e->getMessage();
}

// Manage case where the allycode does not exist in DB
if (!isset($player['name']) || is_null($player['name'])) {
    echo "<title>ERR: unknown player</title>"; 
    echo "<h2>ERR: unknown player</h2>"; 
    exit();
}

?>
