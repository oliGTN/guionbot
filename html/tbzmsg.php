<?php
// server should keep session data for AT LEAST 1 hour
ini_set('session.gc_maxlifetime', 3600*24*7);
// each client should remember their session id for EXACTLY 1 hour
session_set_cookie_params(3600*24*7);
// Start the session to check if the user is logged in
session_start();

require 'guionbotdb.php';  // Include the database connection for guionbotdb

// Check if the user is logged in and if the user is an admin
$isAdmin = isset($_SESSION['admin']) && $_SESSION['admin'];

$entityBody = json_decode(file_get_contents('php://input'), true);
error_log(print_r($entityBody,true));
error_log(print_r($entityBody["guild_id"],true));

// define $isMyGuild, $isOfficer FROM $guild_id
if (isset($entityBody['guild_id'])) {
    $guild_id = $entityBody['guild_id'];
    include 'gvariables.php';

    if (($isMyGuildConfirmed&$isOfficer)|$isAdmin) {
        if (!isset($entityBody['tb_id'])) {
            $err_code = 400;
            $err_txt = "Missing parameters1";
        } else if (!isset($entityBody['list_orders'])) {
            $err_code = 400;
            $err_txt = "Missing parameters2";
        } else {
            $tb_id = $entityBody['tb_id'];
            foreach($entityBody['list_orders'] as $order) {
                if (!isset($order['zone_id'])) {
                    $err_code = 400;
                    $err_txt = "Missing parameters3";
                } else if (!isset($order['zone_msg'])) {
                    $err_code = 400;
                    $err_txt = "Missing parameters4";
                } else if (!isset($order['zone_cmd'])) {
                    $err_code = 400;
                    $err_txt = "Missing parameters5";
                } else {
                    $zone_id = $order["zone_id"];
                    $zone_msg = $order["zone_msg"];
                    $zone_cmd = $order["zone_cmd"];

                    $output = null;
                    $retval = null;
                    $cmd_exec = 'cd /home/pi/GuionBot/guionbot-dev/;';
                    $cmd_exec .= 'python web_commands.py';
                    $cmd_exec .= ' TBzoneOrder';
                    $cmd_exec .= ' '.$guild_id;
                    $cmd_exec .= ' '.$tb_id;
                    $cmd_exec .= ' '.$zone_id;
                    $cmd_exec .= ' "'.$zone_msg.'"';
                    $cmd_exec .= ' '.$zone_cmd;
                    //$cmd_exec='cd /home/pi/GuionBot/guionbot-dev/; pip install -r requirements.txt';
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
                }
            }
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

