<?php
function set_session_rights_for_allycode($allycode)
{
    global $conn_guionbot;

    if (!isset($_SESSION['user_id'])) {
        return [false, false];
    }

    $allyCodes = $_SESSION['allyCodes'] ?? [];
    $key = (int) $allycode;
    $isMyAllycode = array_key_exists($key, $allyCodes)
        || array_key_exists($allycode, $allyCodes);

    $confirmed = array_key_exists($key, $allyCodes)
        ? $allyCodes[$key]
        : ($allyCodes[$allycode] ?? false);

    $isGuildMate = false;
    try {
        $stmt = $conn_guionbot->prepare(
            "SELECT COUNT(*) FROM players
             WHERE guildId IN (
	            SELECT guildId
	            FROM players
	            JOIN player_discord ON player_discord.allyCode = players.allyCode
	            WHERE discord_id = :discord_id
             ) AND allyCode = :allycode"
        );
        $stmt->execute([
            ':allycode' => $allycode,
            ':discord_id' => $_SESSION['user_id'],
        ]);

        $ac_count = $stmt->fetch(PDO::FETCH_ASSOC);
        $isGuildMate = $ac_count ? (bool) $ac_count : false;
    } catch (PDOException $e) {
        error_log('Error fetching guild rights: ' . $e->getMessage());
        $isGuildMate = false;
    }

    return [$isMyAllycode, $isMyAllycode && !empty($confirmed), $isGuildMate];
}
?>
