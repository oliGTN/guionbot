<?php
// --------------- GET GUILD BASIC DATA -----------
// INPUT fr the file is $guild_id
//
// Prepare the SQL query
$query = "SELECT guilds.id AS id, name, players, gp, lastUpdated, NOT isnull(bot_allyCode) AS bot FROM guilds";
$query .= " LEFT JOIN guild_bot_infos ON (guild_bot_infos.guild_id=guilds.id)";
$query .= " WHERE guilds.id='".$guild_id."'";
#error_log("query = ".$query);
try {
    // Prepare the SQL query to fetch the player information
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $guilds = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $guild = array_values($guilds)[0];

} catch (PDOException $e) {
    echo "Error fetching guild data: " . $e->getMessage();
}

// Manage case where the guild ID does not exist in DB
if (!isset($guild['name']) || is_null($guild['name'])) {
    echo "<title>ERR: unknown guild</title>"; 
    echo "<h2>ERR: unknown guild</h2>"; 
    exit();
}

// --------------- GET GUILD HISTORY OF GP/PLAYERS -----------
// Prepare the SQL query
$query = "SELECT date, gp, players FROM guild_gp_history";
$query .= " WHERE guild_id = '".$guild_id."'";
$query .= " AND DATEDIFF(CURDATE(), date)<30";
//error_log("query = ".$query);
try {
    // Prepare the SQL query to fetch the player information
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $guild_history = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    echo "Error fetching guild data: " . $e->getMessage();
}
$graph_date = array();
$graph_gp = array();
$graph_players = array();
foreach($guild_history as $line)
{
    array_push($graph_date, $line['date']);
    array_push($graph_gp, $line['gp']);
    array_push($graph_players, $line['players']);
}
$guild['graph_date'] = $graph_date;
$guild['graph_gp'] = $graph_gp;
$guild['graph_players'] = $graph_players;

$_SESSION['guild'] = $guild;
?>
