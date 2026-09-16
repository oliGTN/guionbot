<?php
// server should keep session data for AT LEAST 1 hour
ini_set('session.gc_maxlifetime', 3600 * 24 * 7);
// each client should remember their session id for EXACTLY 1 hour
session_set_cookie_params(3600 * 24 * 7);
// Start the session to check if the user is logged in
session_start();

require 'guionbotdb.php';  // Include the database connection for guionbotdb
include 'gvariables.php';

// Check if the user is logged in and if the user is an admin
$isAdmin = isset($_SESSION['admin']) && $_SESSION['admin'];

$entityBody = json_decode(file_get_contents('php://input'), true);
#error_log(print_r($entityBody, true));

if (isset($entityBody['guild_id'])) {
    $guild_id = $entityBody['guild_id'];
    list($isMyGuild, $isMyGuildConfirmed, $isBonusGuild, $isOfficer) = set_session_rights_for_guild($guild_id);

    if (($isMyGuildConfirmed & $isOfficer) | $isAdmin) {
        $token_file = '/home/pi/GuionBot/web_commands.token';

        if (!is_readable($token_file)) {
            $err_code = 500;
            $err_txt = 'Web commands service configuration error';
        } else {
            $web_commands_token = trim(file_get_contents($token_file));

            $ch = curl_init('http://127.0.0.1:9000/TBzoneOrder');

            curl_setopt_array($ch, [
                CURLOPT_POST => true,
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_HTTPHEADER => [
                    'Content-Type: application/json',
                    'Authorization: Bearer ' . $web_commands_token
                ],
                CURLOPT_POSTFIELDS => json_encode($entityBody),
                CURLOPT_CONNECTTIMEOUT => 2,
                CURLOPT_TIMEOUT => 30
            ]);

            $response = curl_exec($ch);
            $curl_error = curl_error($ch);
            $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);

            if ($response === false) {
                error_log('Web commands service connection error: ' . $curl_error);
                $err_code = 500;
                $err_txt = 'Web commands service unavailable';
            } else {
                $output_json = json_decode($response, true);

                if (!is_array($output_json)) {
                    error_log(
                        'Invalid response from web commands service, HTTP code=' .
                        $http_code
                    );
                    $err_code = 500;
                    $err_txt = 'Invalid response from web commands service';
                } else {
                    $err_code = $output_json['err_code'] ?? 500;
                    $err_txt = $output_json['err_txt'] ?? 'Invalid response from web commands service';
                }
            }
        }
    } else {
        $err_code = 400;
        $err_txt = 'Not authorized';
    }
} else {
    $err_code = 400;
    $err_txt = 'Missing parameters6';
}

$data = [
    'err_code' => $err_code,
    'err_txt' => $err_txt
];

header('Content-Type: application/json; charset=utf-8');
echo json_encode($data);
?>
