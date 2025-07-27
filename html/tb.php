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

// Check if a TB id and a round are given in URL, otherwise redirect to index
if (!isset($_GET['id'])) {
    error_log("No id or no round: redirect to index.php");
    header("Location: index.php");
    exit();
}
$tb_id = $_GET['id'];

if (!isset($_GET['round'])) {
    // Get the max round
    // Prepare the SQL query
    $query = "SELECT current_round";
    $query .= " FROM tb_history";
    $query .= " WHERE tb_history.id=".$tb_id;
    //error_log("query = ".$query);
    try {
        // Prepare the SQL query
        $stmt = $conn_guionbot->prepare($query);
        $stmt->execute();

        // Fetch all the results as an associative array
        $rounds = $stmt->fetchAll(PDO::FETCH_ASSOC);
        if (count($rounds)==0) {
            error_log("Unknown TB id: redirect to index.php");
            header("Location: index.php");
            exit();
        }
        $round = $rounds[0]['current_round'];

    } catch (PDOException $e) {
        error_log("Error fetching guild data: " . $e->getMessage());
        echo "Error fetching guild data: " . $e->getMessage();
        $round = 1;
    }
} else {
    $round = $_GET['round'];
}

// --------------- SORTING PLAYERS BY COLUMN -----------
// Get sort parameters from URL or set default
$valid_columns = ['name', 'score', 'deployment', 'waves', 'strikes'];
$sort_column = isset($_GET['sort']) && in_array($_GET['sort'], $valid_columns) ? $_GET['sort'] : 'score';
$sort_order = isset($_GET['order']) && strtolower($_GET['order']) === 'asc' ? 'ASC' : 'DESC';

// Toggle sort order for next click
$next_order = $sort_order === 'ASC' ? 'desc' : 'asc';


// --------------- GET ROUND INFO FOR THE TB -----------
// Prepare the SQL query
$query = "SELECT sum(score_strikes) AS strikes, sum(score_platoons) AS platoons,";
$query .= " sum(score_deployed) AS deployed,";
$query .= " availableShipDeploy, availableCharDeploy, availableMixDeploy,";
$query .= " remainingShipPlayers, remainingCharPlayers, remainingMixPlayers,";
$query .= " deploymentType, totalPlayers";
$query .= " FROM tb_player_score";
$query .= " JOIN tb_phases ON tb_phases.tb_id = tb_player_score.tb_id";
$query .= " AND tb_phases.round = tb_player_score.round";
$query .= " WHERE tb_player_score.tb_id=".$tb_id." AND tb_player_score.round=".$round;
//error_log("query = ".$query);
try {
    // Prepare the SQL query to fetch the zone information
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $round_score = $stmt->fetchAll(PDO::FETCH_ASSOC)[0];
//print_r($round_score);

} catch (PDOException $e) {
    error_log("Error fetching round data: " . $e->getMessage());
    echo "Error fetching round data: " . $e->getMessage();
}

// --------------- GET PLAYER INFO FOR THE TB -----------
if ($isMyGuildConfirmed|$isBonusGuild|$isAdmin) {
    if ($sort_column == 'deployment') {
        $sort_column_sql = 'deployed_gp/gp';
    } else {
        $sort_column_sql = $sort_column;
    }
    // Prepare the SQL query
    $query = "SELECT name, allyCode, deployed_gp,";
    $query .= " tb_player_score.gp AS gp, tb_player_score.ship_gp AS ship_gp, tb_player_score.char_gp AS char_gp,";
    $query .= " score_strikes+score_deployed as score, strikes, waves";
    $query .= " FROM tb_player_score";
    $query .= " JOIN players ON players.playerId=tb_player_score.player_id";
    $query .= " WHERE tb_id=".$tb_id." AND round=".$round;
    $query .= " ORDER BY $sort_column_sql $sort_order";
    //error_log("query = ".$query);
    try {
        // Prepare the SQL query to fetch the zone information
        $stmt = $conn_guionbot->prepare($query);
        $stmt->execute();

        // Fetch all the results as an associative array
        $tb_players = $stmt->fetchAll(PDO::FETCH_ASSOC);

    } catch (PDOException $e) {
        error_log("Error fetching player data: " . $e->getMessage());
        echo "Error fetching player data: " . $e->getMessage();
    }
} else {
    $tb_players = [];
}
?>
<!DOCTYPE html>
<html>
<head>
    <title>GuiOn bot for SWGOH</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="basic.css">
    <link rel="stylesheet" href="navbar.css">
    <link rel="stylesheet" href="tables.css">
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

<?php include 'tbheader.php'; ?>

<?php include 'tbnavbar.php'; ?>

<div class="col s12 m12 l8">
    <h4 class="no-wrap no-overflow">Round overall score</h4>
    <div class="card">
    <div class="card-content">
    <div class="row">
        <div class="col s4">
            <div class="stat-panel">
                <div class="stat-detail">
                    <label>Strikes</label>
                    <div class="value xsmall pb-5">
                        <value><?php echo number_format($round_score['strikes'], 0, ".", " "); ?></value>
                    </div>
                </div>
            </div>
        </div>
        <div class="col s4">
            <div class="stat-panel">
                <div class="stat-detail">
                    <label>Platoons</label>
                    <div class="value xsmall pb-5">
                        <value><?php echo number_format($round_score['platoons'], 0, ".", " "); ?></value>
                    </div>
                </div>
            </div>
        </div>
        <div class="col s4">
            <div class="stat-panel">
                <div class="stat-detail">
                    <label>Deployments</label>
                    <div class="value xsmall pb-5">
                        <value><?php echo number_format($round_score['deployed'], 0, ".", " "); ?></value>
                    </div>
                </div>
            </div>
        </div>
    </div>
    </div>
    </div>
</div>


<div class="col s12 m12 l8">
    <h4 class="no-wrap no-overflow">Remain to do</h4>
    <div class="card">
    <div class="card-content">
    <div class="row">
        <div class="col s4">
            <div class="stat-panel">
                <div class="stat-detail">
                    <label>Not fully deployed Players</label>
                    <div class="value xsmall pb-5">
                        <value>
                            <?php if ($round_score['deploymentType']==0) {
                                echo $round_score['remainingMixPlayers']."/".$round_score['totalPlayers'];
                            } else if ($round_score['deploymentType']==1) {
                                echo $round_score['remainingCharPlayers']."/".$round_score['totalPlayers'];
                            } else {
                                echo "Ships: ".$round_score['remainingShipPlayers']."/".$round_score['totalPlayers']."<br/>";
                                echo "Chars: ".$round_score['remainingCharPlayers']."/".$round_score['totalPlayers'];
                            }?>
                        </value>
                    </div>
                </div>
            </div>
        </div>
        <div class="col s4">
            <div class="stat-panel">
                <div class="stat-detail">
                    <label>Remaining deployments</label>
                    <div class="value xsmall pb-5">
                        <value>
                            <?php if ($round_score['deploymentType']==0) {
                                echo number_format($round_score['availableMixDeploy'], 0, ".", " ");
                            } else if ($round_score['deploymentType']==1) {
                                echo number_format($round_score['availableCharDeploy'], 0, ".", " ");
                            } else {
                                echo "Ships: ".number_format($round_score['availableShipDeploy'], 0, ".", " ")."<br/>";
                                echo "Chars: ".number_format($round_score['availableCharDeploy'], 0, ".", " ");
                            }?>
                        </value>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <!--
    <div class="row">
        <div class="col s4">
            <div>
                <button type="button" id="btn_redeploy" onclick="fct_redeploy">re-deploy</button>
            </div>
        </div>
        <div class="col s4">
            <div>
                <input type="checkbox" id="with_fights" name="with_fights" checked />
                <label for="with_fights">With fights</label>
            </div>
        </div>
    </div>
    -->
    </div> <!-- card content -->
    </div> <!-- card -->
</div>

<div class="card">
    <!-- table for players -->
    <?php if ($isMyGuildConfirmed|$isBonusGuild|$isAdmin) : ?>
    <table>
        <thead>
            <tr>
<?php
                $col_active = [];
                $col_arrow = [];
                foreach($valid_columns as $col) {
                    $col_active[$col] = false;
                    $col_arrow[$col] = '';
                }
                $col_active[$sort_column] = 'active-sort';
                if ($sort_order == 'ASC') {
                    $col_arrow[$sort_column] = '↓';
                } else {
                    $col_arrow[$sort_column] = '↑';
                }
?>
                <th class="<?php echo $col_active['name'];?>"><a href="tb.php?id=<?php echo $tb_id;?>&round=<?php echo $round;?>&sort=name&order=<?php echo $next_order; ?>">Player<?php echo $col_arrow['name'];?></a></th>
                <th class="<?php echo $col_active['score']; ?>"><a href="tb.php?id=<?php echo $tb_id;?>&round=<?php echo $round;?>&sort=score&order=<?php echo $next_order; ?>">Score<?php echo $col_arrow['score'];?></a></th>
                <th class="<?php echo $col_active['deployment']; ?>"><a href="tb.php?id=<?php echo $tb_id;?>&round=<?php echo $round;?>&sort=deployment&order=<?php echo $next_order; ?>">Deployment<?php echo $col_arrow['deployment'];?></a></th>
                <th class="<?php echo $col_active['waves']; ?>"><a href="tb.php?id=<?php echo $tb_id;?>&round=<?php echo $round;?>&sort=waves&order=<?php echo $next_order; ?>">Waves<?php echo $col_arrow['waves'];?></a></th>
                <th class="<?php echo $col_active['strikes']; ?>"><a href="tb.php?id=<?php echo $tb_id;?>&round=<?php echo $round;?>&sort=strikes&order=<?php echo $next_order; ?>">Strikes<?php echo $col_arrow['strikes'];?></a></th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($tb_players as $tb_player) {
                if ($round_score['deploymentType']==1) { 
                    $ratio_deployed = $tb_player['deployed_gp']/$tb_player['char_gp'];
                } else {
                    $ratio_deployed = $tb_player['deployed_gp']/$tb_player['gp'];
                }
                if ($ratio_deployed<0.1) {
                    $color_deploy='red';
                    $lightcolor_deploy='lightpink';
                } else if ($ratio_deployed<0.9) {
                    $color_deploy='darkorange';
                    $lightcolor_deploy='#ffcf77';
                } else {
                    $color_deploy='green';
                    $lightcolor_deploy='lightgreen';
                }
                $isMyallyCode = in_array(intval($tb_player['allyCode']), array_keys($_SESSION['allyCodes']), true);
                $line_color = ($isMyallyCode?'lightgray':'');
                echo "<tr style='background-color:".$line_color."'>\n";
                echo "\t<td>".$tb_player['name']."</td>\n";
                echo "\t<td class='hide-on-large-only'>".round($tb_player['score']/1000000, 1)."M</td>\n";
                echo "\t<td class='hide-on-med-and-down'>".number_format($tb_player['score'], 0, ".", " ")."</td>\n";
            ?>
                    <td>
                        <svg width="100%" height="30">
                            <rect width="100%" height="30" style="fill:<?php echo $lightcolor_deploy; ?>;"/>
                            <?php if ($round_score['deploymentType']==1) { ?>
                            <rect width="<?php echo $tb_player['deployed_gp']/$tb_player['char_gp']*100?>%" height="30" style="fill:<?php echo $color_deploy; ?>;">
                            <title><?php echo round($tb_player['deployed_gp']/$tb_player['char_gp']*100,0)?>%</title>
                            <?php } else { ?>
                            <rect width="<?php echo $tb_player['deployed_gp']/$tb_player['gp']*100?>%" height="30" style="fill:<?php echo $color_deploy; ?>;">
                            <title><?php echo round($tb_player['deployed_gp']/$tb_player['gp']*100,0)?>%</title>
                            </rect>
                            <?php } ?>
                        </svg>
                    </td>
                <?php echo "\t<td style='text-align:center'>".$tb_player['waves']."</td>\n"; ?>
                <?php echo "\t<td style='text-align:center'>".$tb_player['strikes']."</td>\n"; ?>
                </tr>
            <?php }?>
        </tbody>
    </table>
    <?php endif; ?>
</div>

    </div> <!-- container -->
    </div> <!-- site-content -->
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>
</div>
</div>
</body>
<?php include 'sitefooter.php' ; ?>
</html>
