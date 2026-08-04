<?php
// server should keep session data for AT LEAST 1 hour
ini_set('session.gc_maxlifetime', 3600*24*7);
// each client should remember their session id for EXACTLY 1 hour
session_set_cookie_params(3600*24*7);
// Start the session to check if the user is logged in
session_start();

require 'guionbotdb.php';  // Include the database connection for guionbotdb
include 'pvariables.php';

// Check if the user is logged in and if the user is an admin
$isAdmin = isset($_SESSION['admin']) && $_SESSION['admin'];

// Check if a player is given in URL, otherwise redirect to index
if (!isset($_GET['ac'])) {
    error_log("No ac, redirect to index.php");
    header("Location: index.php");
    exit();
}

$allycode = substr($_GET['ac'], 0, 9);

// define $isMyAllycode FROM $allycode
list($isMyAllycode, $isMyAllycodeConfirmed) = set_session_rights_for_allycode($allycode);

// get basic player data (gp, roster...)
include 'pdata.php';

//-------------- PREPARE THE QUERY for players
// Prepare the SQL query to get guild evolutions
$query = "SELECT timestamp, guild_id, name, description FROM guild_evolutions";
$query .= " JOIN guilds ON guilds.id = guild_evolutions.guild_id";
$query .= " WHERE playerId=(SELECT playerId FROM players WHERE allyCode=".$allycode.")";
$query .= " ORDER BY timestamp DESC";

try {
    // Prepare the SQL query to fetch the player information
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $guild_evo = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    echo "Error fetching player data: " . $e->getMessage();
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

    <h2><?php echo $player['name']; ?>
        <a href="https://swgoh.gg/p/<?php echo $allycode; ?>"><img src="IMAGES/LOGOS/swgohgg_logo.png" width="50" alt="swgoh.gg"/></a>
    </h2>

    <div class="card">
        <p style="color:green;display:inline"><?php echo ($isMyAllycode ? 'This is your account':''); ?>
        </p>
    <p style="color:red;display:inline"><br/><?php echo ($isAdmin ? 'You are logged as an administrator' : ''); ?></p>
    </div>


    <h3>Player current guild</h3>
    <a href="g.php?gid=<?php echo $player['guild_id']; ?>"><?php echo $player['guild_name'];?></a>


    <h3>Player past guilds</h3>

    <!-- Table to display guild names and lastUpdated -->
    <div class="card">
    <table>
        <thead>
            <tr>
                <th >Date</a></th>
                <th >Guild</a></th>
                <th >Description</a></th>
            </tr>
        </thead>
        <tbody>
            <?php
            echo "\n";
            // Loop through each guild_evo and display in a table row
            if (!empty($guild_evo)) {
                foreach ($guild_evo as $evo) {
                    $isMyGuild = ($evo['guild_id'] == $player['guild_id']);
                    $line_color = ($isMyGuild?'lightgray':'');
                    
                    if ($evo['description'] == 'removed') {
                        $evo_display = 'leaves the guild';
                    } elseif ($evo['description'] == 'added') {
                        $evo_display = 'joins the guild';
                    } elseif (substr($evo['description'], 0, strlen('guildMemberLevel changed')) == 'guildMemberLevel changed') {
                    
                        if ($evo['description'][-1] =='4') {
                            $evo_display = 'role changed to leader';
                        } elseif ($evo['description'][-1] =='3') {
                            $evo_display = 'role changed to officer';
                        } else {
                            $evo_display = 'role changed to member';
                        }
                    } else {
                        $evo_display = $evo['description'];
                    }

                    echo "\t\t\t<tr style='background-color:".$line_color."'>\n";
                    echo "\t\t\t\t<td>" . $evo['timestamp'] . "</td>\n";
                    echo "\t\t\t<td><a href='g.php?gid=".$evo['guild_id']."/'>" . htmlspecialchars($evo['name']) . "</a></td>\n";
                    echo "\t\t\t\t<td>" . $evo_display . "</td></tr>\n";
                }
            } else {
                echo "<tr><td colspan='2'>No guild history found.</td></tr>\n";
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
