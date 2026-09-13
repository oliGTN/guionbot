<?php
// Input: $guild_id (validated by caller).
try {
    $stmt = $conn_guionbot->prepare(
        "SELECT guilds.id AS id, name, players, gp, lastUpdated,
                NOT ISNULL(guild_bots.allyCode) AS bot
         FROM guilds
         LEFT JOIN guild_bot_infos ON guild_bot_infos.guild_id = guilds.id
         LEFT JOIN guild_bots ON guild_bots.guild_id = guilds.id
         WHERE guilds.id = :guild_id"
    );
    $stmt->execute([':guild_id' => $guild_id]);
    $guilds = $stmt->fetchAll(PDO::FETCH_ASSOC);
    if (empty($guilds)) {
        echo "<title>ERR: unknown guild</title><h2>ERR: unknown guild</h2>";
        exit();
    }
    $guild = $guilds[0];
} catch (PDOException $e) {
    error_log('Error fetching guild data: '.$e->getMessage());
    http_response_code(500);
    exit('An internal error occurred.');
}

try {
    $stmt = $conn_guionbot->prepare(
        "SELECT date, gp, players FROM guild_gp_history
         WHERE guild_id = :guild_id
         AND DATEDIFF(CURDATE(), date) < 30"
    );
    $stmt->execute([':guild_id' => $guild_id]);
    $guild_history = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    error_log('Error fetching guild history: '.$e->getMessage());
    $guild_history = [];
}

$guild['graph_date'] = [];
$guild['graph_gp'] = [];
$guild['graph_players'] = [];
foreach ($guild_history as $line) {
    $guild['graph_date'][] = $line['date'];
    $guild['graph_gp'][] = $line['gp'];
    $guild['graph_players'][] = $line['players'];
}
$_SESSION['guild'] = $guild;
?>
