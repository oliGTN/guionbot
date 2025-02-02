<?php
session_start();  // Start the session to check if the user is logged in
require 'guionbotdb.php';  // Include the database connection for guionbotdb

// Check if the user is logged in and if the user is an admin
$isAdmin = isset($_SESSION['admin']) && $_SESSION['admin'];

// Check if a TB id and a round are given in URL, otherwise redirect to index
if (!isset($_GET['id']) || !isset($_GET['round'])) {
    error_log("No id or no round: redirect to index.php");
    header("Location: index.php");
    exit();
}

$tb_id = $_GET['id'];
$round = $_GET['round'];

// Get the associated guild and check if the user is allowed
// Prepare the SQL query
$query = "SELECT guild_id, tb_name, start_date, lastUpdated, max(round) AS max_round FROM tb_history";
$query .= " JOIN tb_zones ON tb_zones.tb_id=tb_history.id";
$query .= " WHERE tb_zones.tb_id=".$tb_id;
#error_log("query = ".$query);
try {
    // Prepare the SQL query
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $tb_list = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $tb = array_values($tb_list)[0];

} catch (PDOException $e) {
    error_log("Error fetching guild data: " . $e->getMessage());
    echo "Error fetching guild data: " . $e->getMessage();
}
$guild_id = $tb['guild_id'];

// The guild page needs to be visited first
if (!isset($_SESSION['guild']) || ($_SESSION['guild']['id']!=$guild_id)){
    error_log("No valid guild data, redirect to g.php?gid=$guild_id");
    header("Location: g.php?gid=$guild_id");
    exit();
}
$guild = $_SESSION['guild'];

// define $isMyGuild, $isOfficer FROM $guild_id
include 'gvariables.php';

// --------------- GET ZONE INFO FOR THE TB -----------
// Prepare the SQL query
$query = "SELECT zone_name, zone_phase, score_step1, score_step2, score_step3,";
$query .= " score, estimated_platoons, estimated_strikes, estimated_deployments FROM tb_zones";
$query .= " WHERE tb_id=".$tb_id." AND round=".$round;
#error_log("query = ".$query);
try {
    // Prepare the SQL query to fetch the zone information
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $zones = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    error_log("Error fetching zone data: " . $e->getMessage());
    echo "Error fetching zone data: " . $e->getMessage();
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

    <h2>TB for <a href='/g.php?gid=<?php echo $guild['id']; ?>'><?php echo $guild['name']; ?></a></h2>
    <h3><?php echo $tb['tb_name']." - round ".$round." (last update on ".$tb['lastUpdated'].")"; ?></h3>
    <h3>Rounds: <?php for($i = 1; $i <= $tb['max_round']; $i++) {
		echo "<a".($i!=$round ? " href='/tb.php?id=".$tb_id."&round=".$i."'" : "").">$i</a> /";
	}; ?></h3>
    
    <!-- Table of zones -->
    <table>
    <?php
    // Loop through each tb and display in a table row
    if (!empty($zones)) {
        foreach ($zones as $zone) {
            $score = $zone['score'];
            $estimated_platoons = $zone['estimated_platoons'];
            $estimated_strikes = $zone['estimated_strikes'];
            $estimated_deployments = $zone['estimated_deployments'];
            $score_step1 = $zone['score_step1'];
            $score_step2 = $zone['score_step2'];
            $score_step3 = $zone['score_step3'];
            if ($score >= $score_step3) {
                $step_count = 3;
            } elseif ($score >= $score_step2) {
                $step_count = 2;
            } elseif ($score >= $score_step1) {
                $step_count = 1;
            } else {
                $step_count = 0;
            }
            ?>
        <thead>
            <tr>
                <th ><?php echo $zone['zone_name']." : ".number_format($score, 0, '.', ' ')." / ".number_format($score_step3, 0, '.', ' ') ?></th>
            </tr>
        </thead>
        <tbody>
            <?php
            //prepare graph inputs
            $graph_width=700;
            $graph_height=50;
            $x_step1 = $score_step1 / $score_step3 * $graph_width;
            $x_step2 = $score_step2 / $score_step3 * $graph_width;
            $x_score = min($graph_width, $score / $score_step3 * $graph_width);
            $x_platoons = min($graph_width, $x_score + $estimated_platoons / $score_step3 * $graph_width);
            $x_strikes = min($graph_width, $x_platoons + $estimated_strikes / $score_step3 * $graph_width);
            $x_deployments = min($graph_width, $x_strikes + $estimated_deployments / $score_step3 * $graph_width);
            //print($x_score.", ".$x_score.", ".$x_platoons.", ".$x_strikes."  /// ");
            ?>
                    
            <tr><td><svg class="chart" width="100%" height="100%">
                <g transform="translate(0,0)">
                    <rect x="0" width="<?php echo $x_score ?>" height="50" style="fill:green"></rect>
                    <rect x="<?php echo $x_score ?>" width="<?php echo $x_platoons-$x_score ?>" height="50" style="fill:lightgreen"></rect>
                    <rect x="<?php echo $x_platoons ?>" width="<?php echo $x_strikes-$x_platoons ?>" height="50" style="fill:orange"></rect>
                    <rect x="<?php echo $x_strikes ?>" width="<?php echo $x_deployments-$x_strikes ?>" height="50" style="fill:yellow"></rect>
                    
                    <rect width="<?php echo $graph_width ?>" height="50" style="fill:white;stroke-width:1;stroke:black;fill-opacity:0"></rect>
                    <rect width="<?php echo $x_step2-$x_step1 ?>" height="50" x="<?php echo $x_step1 ?>" style="fill:white;stroke-width:1;stroke:black;fill-opacity:0"></rect>
                    
                    <text x="0" y="70" font-size="10">0</text>
                    <text x="<?php echo $x_step1 ?>" y="70" text-anchor="middle" font-size="10"><?php echo number_format($score_step1, 0, '.', ' ') ?></text>
                    <text x="<?php echo $x_step2 ?>" y="70" text-anchor="middle" font-size="10"><?php echo number_format($score_step2, 0, '.', ' ') ?></text>
                    <text x="<?php echo $graph_width ?>" y="70" text-anchor="end" font-size="10"><?php echo number_format($score_step3, 0, '.', ' ') ?></text>
                </g>
            </svg></td></tr>
        </tbody>
    <?php }
    } else {
        echo "<tr><td colspan='2'>No zone found.</td></tr>";
    } ?>
    </table>
    
</body>
</html>
