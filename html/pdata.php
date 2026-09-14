<?php
// Input: $allycode (validated by caller).
try {
    $stmt = $conn_guionbot->prepare(
        "SELECT players.playerId AS id, name, guildId AS guild_id,
                guildName AS guild_name, guildMemberLevel, level, char_gp,
                ship_gp, grand_arena_rank, poUTCOffsetMinutes, modq, statq
         FROM players
         WHERE allyCode = :allycode"
    );
    $stmt->execute([':allycode' => $allycode]);
    $players = $stmt->fetchAll(PDO::FETCH_ASSOC);

    if (empty($players)) {
        echo "<title>ERR: unknown player</title><h2>ERR: unknown player</h2>";
        exit();
    }

    $player = $players[0];
} catch (PDOException $e) {
    error_log('Error fetching player data: ' . $e->getMessage());
    http_response_code(500);
    exit('An internal error occurred.');
}
?>
