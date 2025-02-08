<?php
session_start();  // Start the session to check if the user is logged in
require 'guionbotdb.php';  // Include the database connection for guionbotdb

// Check if the user is logged in and if the user is an admin
$isAdmin = isset($_SESSION['admin']) && $_SESSION['admin'];

// Check if a guild is given in URL, otherwise redirect to index
if (!isset($_GET['gid'])) {
    error_log("Redirect to index.php");
    header("Location: index.php");
    exit();
}

$guild_id = $_GET['gid'];

// define $isMyGuild, $isOfficer FROM $guild_id
include 'gvariables.php';

// The guild page needs to be visited first
if (!isset($_SESSION['guild']) || ($_SESSION['guild']['id']!=$guild_id)){
    error_log("No valid guild data, redirect to g.php?gid=$guild_id");
    header("Location: g.php?gid=$guild_id");
    exit();
}
$guild = $_SESSION['guild'];

// --------------- GET TB LIST GUILD -----------
// Prepare the SQL query
$query = "SELECT tb_history.id, tb_name, start_date, lastUpdated, MAX(tb_zones.round) AS max_round FROM tb_history";
$query .= " LEFT JOIN tb_zones ON tb_zones.tb_id = tb_history.id";
$query .= " WHERE guild_id='".$_GET['gid']."'";
$query .= " GROUP BY tb_history.id";
$query .= " ORDER BY start_date DESC";
#error_log("query = ".$query);
try {
    // Prepare the SQL query to fetch the player information
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $tbs = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    error_log("Error fetching TB history data: " . $e->getMessage());
    echo "Error fetching TB history data: " . $e->getMessage();
}

?>

<!DOCTYPE html>
<html>
<head>
    <title>GuiOn bot for SWGOH</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="basic.css">
    <link rel="stylesheet" href="tables.css">
    <link rel="stylesheet" href="navbar.css">
    <link rel="stylesheet" href="main.1.008.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
</head>
<body>
<div class="site-container">
<div class="site-pusher">

    <!-- Navigation Bar -->
    <?php include 'navbar.php' ; ?>

    <div class="site-content">
    <div class="container">

    <!-- Guild header -->
    <?php include 'gheader.php' ; ?>
    
    <!-- Table of TB history -->
    <table>
        <thead>
            <tr>
                <th >Start date</th>
                <th >Type</th>
            </tr>
        </thead>
        <tbody>
            <?php
            echo "\n";
            // Loop through each tb and display in a table row
            if (!empty($tbs)) {
                foreach ($tbs as $tb) {
                    echo "\t\t\t<tr><td>" . $tb['start_date'] . "</td>\n";
                    echo "\t\t\t\t<td><a href='/tb.php?id=".$tb['id']."&round=".$tb['max_round']."'>" . $tb['tb_name'] . "</a></td></tr>\n";
                }
            } else {
                echo "<tr><td colspan='2'>No TB found.</td></tr>";
            }
            ?>
        </tbody>
    </table>

    </div> <!-- container -->
    </div> <!-- site-content -->
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>
</div>
</div>
</body>
<?php include 'sitefooter.php' ; ?>
</html>
