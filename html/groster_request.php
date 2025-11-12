<?php
// server should keep session data for AT LEAST 1 hour
ini_set('session.gc_maxlifetime', 3600*24*7);
// each client should remember their session id for EXACTLY 1 hour
session_set_cookie_params(3600*24*7);
// Start the session to check if the user is logged in
session_start();

require 'guionbotdb.php';  // Include the database connection for guionbotdb

// Check if the user is logged in
if (!isset($_SESSION['user_id'])) {
    $data = array (
        "err_code" => 1,
        "err_txt"  => "You need to be logged to use this page"
    );
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data);
    exit();
}

//this line is a workaround as the POST request is not from a form
$_POST = json_decode(file_get_contents('php://input'), true);

// Handle guild association
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['units_list'])) {
    $guild_id = $_POST['guild_id'];
    $units_list = $_POST['units_list'];
    $unitId_list = array();
    foreach($units_list as $unit) {
        array_push($unitId_list, $unit['unit_id']);
    }
    $unitId_list_txt = json_encode($unitId_list);
    $unitId_list_txt = '('.substr($unitId_list_txt, 1, strlen($unitId_list_txt)-2).')';
    $unitId_list_txt = str_replace('"', "'", $unitId_list_txt);

    $query = "SELECT name, defId, gear, greatest(0, relic_currentTier-2) AS relic";
    $query .= " FROM roster JOIN players";
    $query .= " ON players.allyCode=roster.allyCode";
    $query .= " WHERE guildId = '".$guild_id."'";
    $query .= " AND defId IN ".$unitId_list_txt;
    $query .= " ORDER BY name";
    //error_log($query);
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $roster = $stmt->fetchAll(PDO::FETCH_ASSOC);
}

// return values
$data = array (
    "err_code"  => 0,
    "err_txt" => "",
    "roster" => $roster
);
header('Content-Type: application/json; charset=utf-8');
echo json_encode($data);
?>
