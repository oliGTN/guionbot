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
$query = "SELECT tw_history.id, start_date, away_guild_name,";
$query .= " homeScore, awayScore, lastUpdated FROM tw_history";
$query .= " WHERE guild_id='".$_GET['gid']."'";
$query .= " ORDER BY start_date DESC";
#error_log("query = ".$query);
try {
    // Prepare the SQL query to fetch the player information
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $tws = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    error_log("Error fetching TW history data: " . $e->getMessage());
    echo "Error fetching TW history data: " . $e->getMessage();
}

?>

<!DOCTYPE html>
<html>
<head>
    <title><?php echo $guild['name']; ?></title>
    <link rel="stylesheet" href="basic.css">
    <link rel="stylesheet" href="navbar.css">
    <link rel="stylesheet" href="tables.css">
</head>
<body>

    <!-- Navigation Bar -->
    <?php include 'navbar.php' ; ?>

    <!-- Guild header -->
    <?php include 'gheader.php' ; ?>
    
    <!-- Table of TB history -->
    <table>
        <thead>
            <tr>
                <th >Start date</th>
                <th >Opponent</th>
                <th >Score</th>
            </tr>
        </thead>
        <tbody>
            <?php
            echo "\n";
            // Loop through each tw and display in a table row
            if (!empty($tws)) {
                foreach ($tws as $tw) {
                    $score_color = ($tw['homeScore']>=$tw['awayScore']?'green':'red');
                    $start_time = $tw['start_date'];
                    $start_tab = explode(' ', $start_time);
                    $start_date = $start_tab[0];
                    echo "\t\t\t<tr><td>" . $start_date . "</td>\n";
                    echo "\t\t\t\t<td><a href='/tw.php?id=".$tw['id']."'>" . $tw['away_guild_name'] . "</a></td>\n";
                    echo "\t\t\t\t<td style='color:".$score_color."'><b>".$tw['homeScore']."/".$tw['awayScore']."</b></td></tr>\n";
                }
            } else {
                echo "<tr><td colspan='3'>No Tw found.</td></tr>";
            }
            ?>
        </tbody>
    </table>
    
</body>
</html>
