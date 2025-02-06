<?php
session_start();  // Start the session to check if the user is logged in
require 'guionbotdb.php';  // Include the database connection for guionbotdb

// Check if the user is logged in and if the user is an admin
$isAdmin = isset($_SESSION['admin']) && $_SESSION['admin'];

// Check if a guild is given in URL, otherwise redirect to index
if (!isset($_GET['gid'])) {
    error_log("No gid, redirect to index.php");
    header("Location: index.php");
    exit();
}

$guild_id = $_GET['gid'];

// define $isMyGuild, $isOfficer FROM $guild_id
include 'gvariables.php';
//echo "isMyGuild=".$isMyGuild;

// The guild page (this file) is where the basic guild ifo is gathered
if (isset($_SESSION['guild'])){
    unset($_SESSION['guild']);
}

// get basic guild data (gp, players...) as well as gp/player history
include 'gdata.php';

// --------------- SORTING BY COLUMN -----------
// Get sort parameters from URL or set default
$valid_columns = ['name', 'gp', 'lastUpdated'];
$sort_column = isset($_GET['sort']) && in_array($_GET['sort'], $valid_columns) ? $_GET['sort'] : 'name';
$sort_order = isset($_GET['order']) && strtolower($_GET['order']) === 'desc' ? 'DESC' : 'ASC';

// Toggle sort order for next click
$next_order = $sort_order === 'ASC' ? 'desc' : 'asc';

//-------------- PREPARE THE QUERY for players
// Prepare the SQL query to get players with pagination
$query = "SELECT name, playerId, allyCode, char_gp+ship_gp AS gp, lastUpdated FROM players WHERE guildId='".$_GET['gid']."'";
$query .= " ORDER BY $sort_column $sort_order";

try {
    // Prepare the SQL query to fetch the player information
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $players = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    echo "Error fetching player data: " . $e->getMessage();
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


    <h3>Player List</h3>

    <!-- Table to display player names and lastUpdated, with clickable sortable headers -->
    <table>
        <thead>
            <tr>
                <?php $current_sort = isset($_GET['sort']) ? $_GET['sort'] : 'name'; ?>
                <th>#</th>
                <th class="<?php echo ($current_sort === 'name') ? 'active-sort' : ''; ?>"><a href="g.php?gid=<?php echo $_GET['gid'];?>&sort=name&order=<?php echo $next_order; ?>">Name</a></th>
                <th >allyCode</a></th>
                <th class="<?php echo ($current_sort === 'gp') ? 'active-sort' : ''; ?>"><a href="g.php?gid=<?php echo $_GET['gid'];?>&sort=gp&order=<?php echo $next_order; ?>">GP</a></th>
                <th class="<?php echo ($current_sort === 'lastUpdated') ? 'active-sort' : ''; ?>"><a href="g.php?gid=<?php echo $_GET['gid'];?>&sort=lastUpdated&order=<?php echo $next_order; ?>">Last Updated</a></th>
            </tr>
        </thead>
        <tbody>
            <?php
            echo "\n";
            // Loop through each player and display in a table row
            if (!empty($players)) {
                $i_player = 1;
                foreach ($players as $player) {
                    $allyCode_display = substr($player['allyCode'], 0, 3) . "-";
                    $allyCode_display .= substr($player['allyCode'], 3, 3) . "-";
                    $allyCode_display .= substr($player['allyCode'], 6, 3);
                    $isMyallyCode = in_array(intval($player['allyCode']), array_keys($_SESSION['allyCodes']), true);
                    $line_color = ($isMyallyCode?'lightgray':'');
                    echo "\t\t\t<tr style='background-color:".$line_color."'>\n";
                    echo "\t\t\t<td>".$i_player."</td>\n";
                    echo "\t\t\t<td><a href='https://swgoh.gg/p/".$player['allyCode']."/'>" . htmlspecialchars($player['name']) . "</a></td>\n";
                    echo "\t\t\t\t<td>" . $allyCode_display . "</td>\n";
                    echo "\t\t\t\t<td  style='text-align:right'>" . number_format($player['gp'], 0, '.', ' ') . "</td>\n";
                    echo "\t\t\t\t<td>" . $player['lastUpdated'] . "</td></tr>\n";
                    $i_player += 1;
                }
            } else {
                echo "<tr><td colspan='2'>No players found.</td></tr>\n";
            }
            ?>
        </tbody>
    </table>
    
</body>
</html>
