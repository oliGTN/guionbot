<?php
function set_session_rights_for_allycode($allycode)
{
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

    return [$isMyAllycode, $isMyAllycode && !empty($confirmed)];
}
?>
