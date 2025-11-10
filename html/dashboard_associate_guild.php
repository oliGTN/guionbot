<?php
error_log("eeeeeeeeeeeeeeeeeeeeeee");
// server should keep session data for AT LEAST 1 hour
ini_set('session.gc_maxlifetime', 3600*24*7);
// each client should remember their session id for EXACTLY 1 hour
session_set_cookie_params(3600*24*7);
// Start the session to check if the user is logged in
session_start();

require 'websitedb.php';  // Include the database connection for websitedb

// Check if the user is logged in
if (!isset($_SESSION['user_id'])) {
    error_log("no user_id, redirect to index.php");
    header("Location: index.php");
    exit();
}

// Check if the user is an admin
$isAdmin = isset($_SESSION['admin']) && $_SESSION['admin'];

$err_code = 0;
$err_txt = "";

if ($isAdmin) {
    //this line is a workaround as the POST request is not from a form
    $_POST = json_decode(file_get_contents('php://input'), true);

    // Handle guild association
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['associate_guild'])) {
        $user_id = $_POST['user_id'];
        $guild_id = $_POST['guild_id'];

        $check_stmt = $conn->prepare("SELECT * FROM user_guilds WHERE user_id = :user_id AND guild_id = :guild_id");
        $check_stmt->execute(['user_id' => $user_id, 'guild_id' => $guild_id]);
        if (!$check_stmt->fetch()) {
            $insert_stmt = $conn->prepare("INSERT INTO user_guilds (user_id, guild_id) VALUES (:user_id, :guild_id)");
            $insert_stmt->execute(['user_id' => $user_id, 'guild_id' => $guild_id]);
        }

        //add the bonus guild to $_SESSION is current user is target user
        if ($_SESSION['user_id'] == $user_id) {
            array_push($_SESSION['user_bonus_guilds'], $guild_id);
        }
    }

    // Handle guild de-association
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['deassociate_guild'])) {
        $user_id = $_POST['user_id'];
        $guild_id = $_POST['guild_id'];

        $query = "DELETE FROM user_guilds WHERE user_id = :user_id AND guild_id = :guild_id";
        error_log($query.' '.$user_id.' '.$guild_id);
        $stmt = $conn->prepare($query);
        $stmt->execute(['user_id' => $user_id, 'guild_id' => $guild_id]);

        //remove the bonus guild from $_SESSION if current user is target user
        if ($_SESSION['user_id'] == $user_id) {
            $_SESSION['user_bonus_guilds'] = array_diff($_SESSION['user_bonus_guilds'], array($guild_id));
        }
    }
} else {
    $err_code = 1;
    $err_txt = "You need to be logges as admin to access this page";
}

// return values
$data = array (
    "err_code"  => $err_code,
    "err_txt" => $err_txt,
);
header('Content-Type: application/json; charset=utf-8');
echo json_encode($data);
?>
