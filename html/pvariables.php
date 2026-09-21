<?php
function set_session_rights_for_allycode($allycode)
{
    global $conn_guionbot;

    $isMyAllycode = false;
    $isMyAllycodeConfirmed = false;
    $isGuildMate = false;
    $isGuildMateConfirmed = false;

    if (!isset($_SESSION['user_id'])) {
        return [$isMyAllycode, $isMyAllycodeConfirmed, $isGuildMate, $isGuildMateConfirmed];
    }

    $user_guildmates = $_SESSION['user_guildmates'] ?? [];

    $allyCodes = $_SESSION['allyCodes'] ?? [];
    $key = (int) $allycode;
    $isMyAllycode = array_key_exists($key, $allyCodes)
        || array_key_exists($allycode, $allyCodes);

    $confirmed = array_key_exists($key, $allyCodes)
        ? $allyCodes[$key]
        : ($allyCodes[$allycode] ?? false);
    $isMyAllycodeConfirmed = $isMyAllycode && !empty($confirmed);

    $isGuildMate = array_key_exists($allycode, $user_guildmates);
    $isGuildMateConfirmed = $isGuildMate && !empty($user_guildmates[$allycode]);

    return [$isMyAllycode, $isMyAllycodeConfirmed, $isGuildMate, $isGuildMateConfirmed];
}
?>
