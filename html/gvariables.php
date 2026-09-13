<?php
function set_session_rights_for_guild($guild_id) {
    global $conn_guionbot;

    $isMyGuild = false;
    $isMyGuildConfirmed = false;
    $isBonusGuild = false;
    $isOfficer = false;

    if (!isset($_SESSION['user_id'])) {
        return [$isMyGuild, $isMyGuildConfirmed, $isBonusGuild, $isOfficer];
    }

    $user_guilds = $_SESSION['user_guilds'] ?? [];
    $bonus_guilds = $_SESSION['user_bonus_guilds'] ?? [];
    $isMyGuild = array_key_exists($guild_id, $user_guilds);
    $isMyGuildConfirmed = $isMyGuild && !empty($user_guilds[$guild_id]);
    $isBonusGuild = in_array($guild_id, $bonus_guilds, true);

    try {
        $stmt = $conn_guionbot->prepare(
            "SELECT MAX(guildMemberLevel) > 2 AS isOfficer
             FROM players
             JOIN player_discord ON player_discord.allyCode = players.allyCode
             WHERE guildId = :guild_id AND discord_id = :discord_id
             GROUP BY guildId"
        );
        $stmt->execute([
            ':guild_id' => $guild_id,
            ':discord_id' => $_SESSION['user_id']
        ]);
        $player = $stmt->fetch(PDO::FETCH_ASSOC);
        $isOfficer = $player ? (bool)$player['isOfficer'] : false;
    } catch (PDOException $e) {
        error_log('Error fetching guild rights: '.$e->getMessage());
        $isOfficer = false;
    }

    return [$isMyGuild, $isMyGuildConfirmed, $isBonusGuild, $isOfficer];
}
?>
