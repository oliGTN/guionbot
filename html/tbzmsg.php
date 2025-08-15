<?php
// server should keep session data for AT LEAST 1 hour
ini_set('session.gc_maxlifetime', 3600*24*7);
// each client should remember their session id for EXACTLY 1 hour
session_set_cookie_params(3600*24*7);
// Start the session to check if the user is logged in
session_start();

require 'guionbotdb.php';  // Include the database connection for guionbotdb
include 'gvariables.php';

// Check if the user is logged in and if the user is an admin
$isAdmin = isset($_SESSION['admin']) && $_SESSION['admin'];

$entityBody = json_decode(file_get_contents('php://input'), true);
error_log(print_r($entityBody,true));
error_log(print_r($entityBody["guild_id"],true));

// define $isMyGuild, $isOfficer FROM $guild_id
if (isset($entityBody['guild_id'])) {
    $guild_id = $entityBody['guild_id'];
    list($isMyGuild, $isMyGuildConfirmed, $isBonusGuild, $isOfficer) = set_session_rights_for_guild($guild_id);

    if (($isMyGuildConfirmed&$isOfficer)|$isAdmin) {
        // dump entityBody into base64 string
        $my_json_content = json_encode($entityBody);
        //error_log("my_json_content=".$my_json_content);
        $my_json_base64 = base64_encode($my_json_content);
        //error_log("my_json_base64=".$my_json_base64);

        // run the command
        $output = null;
        $retval = null;
        $cmd_exec = 'cd /home/pi/GuionBot/guionbot-dev/;';
        $cmd_exec .= 'python web_commands.py';
        $cmd_exec .= ' TBzoneOrder';
        $cmd_exec .= ' '.$my_json_base64;
        error_log($cmd_exec);
        exec($cmd_exec, $output, $retval);
        foreach($output as $line) {
            error_log($line);
        }
        if ($retval == 0) {
            $output_json = json_decode(end($output), true);
            $err_code = $output_json['err_code'];
            $err_txt = $output_json['err_txt'];
        } else {
            $err_code = 500;
            $err_txt = "execution error, code=".$retval;
        }
    } else {
        $err_code = 400;
        $err_txt = "Not authorized";
    }
} else {
    $err_code = 400;
    $err_txt = "Missing parameters6";
}

$data = array (
    "err_code"  => $err_code,
    "err_txt" => $err_txt
);
header('Content-Type: application/json; charset=utf-8');
echo json_encode($data);
?>

