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

// Check if a guild is given in URL, otherwise redirect to index
if (!isset($_GET['gid'])) {
    error_log("Redirect to index.php");
    header("Location: index.php");
    exit();
}

$guild_id = $_GET['gid'];

// define $isMyGuild, $isOfficer FROM $guild_id
list($isMyGuild, $isMyGuildConfirmed, $isBonusGuild, $isOfficer) = set_session_rights_for_guild($guild_id);

// The guild page needs to be visited first
if (!isset($_SESSION['guild']) || ($_SESSION['guild']['id']!=$guild_id)){
    error_log("No valid guild data, redirect to g.php?gid=$guild_id");
    header("Location: g.php?gid=$guild_id");
    exit();
}
$guild = $_SESSION['guild'];

// --------------- GET TB LIST GUILD -----------
// Prepare the SQL query
$query = "SELECT tb_history.id, tb_name, start_date, lastUpdated, MAX(tb_zones.round) AS max_round,";
$query .= " sum(case";
$query .= " WHEN score>=score_step3 then CASE WHEN SUBSTRING(tb_zones.zone_name, -1, 1)='b' THEN 1 ELSE 3 END";
$query .= " WHEN score>=score_step2 then CASE WHEN SUBSTRING(tb_zones.zone_name, -1, 1)='b' THEN 0 ELSE 2 END";
$query .= " WHEN score>=score_step1 then CASE WHEN SUBSTRING(tb_zones.zone_name, -1, 1)='b' THEN 0 ELSE 1 END";
$query .= " ELSE 0 END) AS stars";
$query .= " FROM tb_history";
$query .= " LEFT JOIN tb_zones ON tb_zones.tb_id = tb_history.id";
$query .= " JOIN (";
$query .= "   SELECT tb_history.id AS id, zone_name, max(round) AS max_round";
$query .= "   FROM tb_zones";
$query .= "   JOIN tb_history ON tb_zones.tb_id=tb_history.id";
$query .= "   WHERE tb_history.guild_id='".$guild_id."'";
$query .= "   GROUP BY tb_history.id, zone_name";
$query .= " ) T ON T.id=tb_history.id AND T.zone_name = tb_zones.zone_name AND T.max_round = tb_zones.round";
$query .= " WHERE guild_id='".$guild_id."'";
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
    <div class="card">
    <table>
        <thead>
            <tr>
                <th >Start date</th>
                <th >Type</th>
                <th >Result</th>
            </tr>
        </thead>
        <tbody>
            <?php
            echo "\n";
            // Loop through each tb and display in a table row
            if (!empty($tbs)) {
                foreach ($tbs as $tb) {
                    echo "\t\t\t<tr><td>" . $tb['start_date'] . "</td>\n";
                    echo "\t\t\t\t<td><a href='/tb.php?id=".$tb['id']."&round=".$tb['max_round']."'>" . $tb['tb_name'] . "</a></td>\n";
                    echo "\t\t\t\t<td>".$tb['stars']."&#11088;</td></tr>\n";
                }
            } else {
                echo "<tr><td colspan='2'>No TB found.</td></tr>";
            }
            ?>
        </tbody>
    </table>
    </div>

    </div> <!-- container -->
    </div> <!-- site-content -->
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>
</div>
</div>
</body>
<?php include 'sitefooter.php' ; ?>
</html>
