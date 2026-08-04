<?php
function set_session_rights_for_allycode($allycode) {
    global $conn_guionbot;

    if (isset($_SESSION['user_id'])) {
        // Define if user is member (or allowed) of the guild
        // $_SESSION allycdes are integers, $allycode is a string
        $isMyAllycode = in_array(intval($allycode),array_keys($_SESSION['allyCodes']),true);
        $isMyAllycodeConfirmed = $isMyAllycode && $_SESSION['allyCodes'][$allycode];

    } else {
        $isMyAllycode = false;
        $isMyAllycodeConfirmed = false;
    }

    return array($isMyAllycode, $isMyAllycodeConfirmed);
}

?>
