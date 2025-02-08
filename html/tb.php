<?php
session_start();  // Start the session to check if the user is logged in
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
    $round = 1;
} else {
    $round = $_GET['round'];
}

// Get the associated guild and check if the user is allowed
// Prepare the SQL query
$query = "SELECT guild_id, tb_name, start_date, lastUpdated,";
$query .= " current_round, max(round) AS max_round FROM tb_history";
$query .= " JOIN tb_zones ON tb_zones.tb_id=tb_history.id";
$query .= " WHERE tb_zones.tb_id=".$tb_id;
//error_log("query = ".$query);
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
    //error_log("No valid guild data, redirect to g.php?gid=$guild_id");
    //header("Location: g.php?gid=$guild_id");
    //exit();
    include 'gdata.php';
}
$guild = $_SESSION['guild'];

// define $isMyGuild, $isOfficer FROM $guild_id
include 'gvariables.php';

// --------------- GET ZONE INFO FOR THE TB -----------
// Prepare the SQL query
$query = "SELECT zone_name, zone_phase, score_step1, score_step2, score_step3,";
$query .= " score, estimated_platoons, estimated_strikes, estimated_deployments FROM tb_zones";
$query .= " WHERE tb_id=".$tb_id." AND round=".$round;
//error_log("query = ".$query);
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

// --------------- GET PLAYER INFO FOR THE TB -----------
if ($isMyGuildConfirmed) {
    // Prepare the SQL query
    $query = "SELECT name, gp, deployed_gp, score, strikes, waves";
    $query .= " FROM tb_player_score";
    $query .= " JOIN players ON players.playerId=tb_player_score.player_id";
    $query .= " WHERE tb_id=".$tb_id." AND round=".$round;
    $query .= " ORDER BY deployed_gp/gp DESC";
    //error_log("query = ".$query);
    try {
        // Prepare the SQL query to fetch the zone information
        $stmt = $conn_guionbot->prepare($query);
        $stmt->execute();

        // Fetch all the results as an associative array
        $tb_players = $stmt->fetchAll(PDO::FETCH_ASSOC);

    } catch (PDOException $e) {
        error_log("Error fetching zone data: " . $e->getMessage());
        echo "Error fetching zone data: " . $e->getMessage();
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
</head>
<body>
<div class="site-container">
<div class="site-pusher">

    <!-- Navigation Bar -->
    <?php include 'navbar.php' ; ?>

    <div class="site-content">
    <div class="container">

    <h2 style="display:inline">TB for <a href='/g.php?gid=<?php echo $guild['id']; ?>'><?php echo $guild['name']; ?></a></h2> - <?php echo $tb['tb_name'];?>
    <div><?php echo "last update on ".$tb['lastUpdated']; ?></div>

    
<!-- Clickable round numbers for large screens -->
<div class="phases hide-on-small-and-down">
    <?php for($i = 1; $i <= $tb['max_round']; $i++) {
        echo "<a href='tb.php?id=".$tb_id."&round=".$i."' ".($i==$round?"class='active'":"").">".($i==$tb['current_round']?"&#11093":"")."Round ".$i."</a>";
        if ($i < $tb['max_round']) {
            echo "&gt;";
        }
    }?>
</div>
<!-- style for clickable rounds -->
<style type="text/css">
    .phases {
        font-size: 18px;
        margin: 20px 0 20px;
    }

    .phases a {
        padding: 0 2px 2px;
    }

    .phases a.active {
        color: #333;
        font-weight: bold;
        cursor: default;
        border-bottom: 4px solid #9A6CFF;
    }
    .phases i.fas.fa-chevron-right {
        color: rgba(0, 0, 0, .3);
        font-size: 14px;
        margin: 0 3px;
        vertical-align: middle;
    }
</style>

<!-- Dropdown round menu for small screens -->
<div class="hide-on-med-and-up">
    <div class="dropdown">
        <form>
        <select style="width:200px" name="list" id="list" accesskey="target" onchange="phaseClicked()">
            <?php for($i = 1; $i <= $tb['max_round']; $i++) {
                echo "<option value='".$i."' ".($i==$round?"selected='selected'":"").">".($i==$tb['current_round']?"&#11093":"")."Round ".$i."</option>\n";
            }?>
        </select>
        </form>
    </div>
    <script>
        function phaseClicked(){
            let userPicked = document.getElementById("list").value;
            new_url ="tb.php?id=<?php echo $tb_id; ?>&round="+userPicked;
            console.log(new_url);
            window.location.href=new_url;
        }
    </script>

</div>

    <!-- Cards for zones -->
<div id="resume" class="active">
    <div class="row">    
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
                    $star_txt = "&#11088;&#11088;&#11088;";
                    $next_step_score = $score_step3;
                } elseif ($score >= $score_step2) {
                    $step_count = 2;
                    $star_txt = "&#11088;&#11088;&#10025;";
                    $next_step_score = $score_step3;
                } elseif ($score >= $score_step1) {
                    $step_count = 1;
                    $star_txt = "&#11088;&#10025;&#10025;";
                    $next_step_score = $score_step2;
                } else {
                    $step_count = 0;
                    $star_txt = "&#10025;&#10025;&#10025;";
                    $next_step_score = $score_step1;
                }

                // prepare graph inputs
                $x_step1 = $score_step1 / $score_step3 * 100;
                $x_step2 = $score_step2 / $score_step3 * 100;
                $x_score = min(100, $score / $score_step3 * 100);
                $x_platoons = min(100, $x_score + $estimated_platoons / $score_step3 * 100);
                $x_strikes = min(100, $x_platoons + $estimated_strikes / $score_step3 * 100);
                $x_deployments = min(100, $x_strikes + $estimated_deployments / $score_step3 * 100);
                ?>

                <div class="col s12 m12 l4">
                    <div class="valign-wrapper full-line">
                    <h4><?php echo $zone['zone_name']?></h4>
                    </div>
                    <div class="card zone">
                        <div class="card-content">
                            <div class="stars">
                                <?php echo $star_txt; ?>
                            </div>
                            <div class="score-text">
                            0 /<small><?php echo number_format($next_step_score, 0, ".", " ");?></small>
                            </div>
                            <svg width="100%" height="70">
                                <rect width="<?php echo $x_score;?>%" height="30" style="fill:green;">
                                    <title>Current score: <?php number_format($score, 0, ".", " ");?></title>
                                </rect>
                                <rect x="<?php echo $x_score;?>%" width="<?php echo $x_strikes-$x_score;?>%" height="30" style="fill:orange;">
                                    <title>Estimated strikes: <?php number_format($estimated_strikes, 0, ".", " ");?></title>
                                </rect>
                                <rect x="<?php echo $x_strikes;?>%" width="<?php echo $x_deployments-$x_strikes;?>%" height="30" style="fill:yellow;">
                                    <title>Deployments: <?php number_format($estimated_strikes, 0, ".", " ");?></title>
                                </rect>
                                <rect width="100%" height="30" style="fill:none;stroke:black;"></rect>
                                <line x1="<?php echo $x_step1?>%" y1="0" x2="<?php echo $x_step1;?>%" y2="30" style="stroke:gray"></line>
                                <line x1="<?php echo $x_step2?>%" y1="0" x2="<?php echo $x_step2;?>%" y2="30" style="stroke:gray"></line>
                                <line x1="<?php echo $x_score?>%" y1="0" x2="<?php echo $x_score;?>%" y2="50" style="stroke:darkgreen;stroke-width:2"></line>
                                <text x="0%" y="40" font-size="10">0</text>
                                <text x="<?php echo $x_step1;?>%" y="40" text-anchor="middle" font-size="10"><?php echo number_format($score_step1, 0, ".", " ");?></text>
                                <text x="<?php echo $x_step2;?>%" y="40" text-anchor="middle" font-size="10"><?php echo number_format($score_step2, 0, ".", " ");?></text>
                                <text x="100%" y="40" text-anchor="end" font-size="10"><?php echo number_format($score_step3, 0, ".", " ");?></text>
                                <text x="<?php echo $x_score;?>%" y="60" text-anchor="<?php echo ($score<$score_step3/2?"":"end");?>" font-size="12">&nbsp;<?php echo number_format($score, 0, ".", " ");?>&nbsp;</text>
                            </svg>
                        </div>
                    </div>
                </div>
            <?php }
        }?>
    </div>
</div>

    <!-- table for players -->
    <?php if ($isMyGuildConfirmed) : ?>
    <table>
        <thead>
            <tr>
                <td>Player</td>
                <td>Score</td>
                <td>Deployment</td>
                <td>Waves</td>
                <td>Strikes</td>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($tb_players as $tb_player) {
                $ratio_deployed = $tb_player['deployed_gp']/$tb_player['gp'];
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
                echo "<tr>\n";
                echo "\t<td>".$tb_player['name']."</td>\n";
                echo "\t<td class='hide-on-large-only'>".round($tb_player['score']/1000000, 1)."M</td>\n";
                echo "\t<td class='hide-on-med-and-down'>".number_format($tb_player['score'], 0, ".", " ")."</td>\n";
            ?>
                    <td>
                        <svg width="100%" height="30">
                            <rect width="100%" height="30" style="fill:<?php echo $lightcolor_deploy; ?>;"/>
                            <rect width="<?php echo $tb_player['deployed_gp']/$tb_player['gp']*100?>%" height="30" style="fill:<?php echo $color_deploy; ?>;">
                            <title><?php $tb_player['deployed_gp']/$tb_player['gp']*100?>%</title>
                            </rect>
                        </svg>
                    </td>
                <?php echo "\t<td style='text-align:center'>".$tb_player['waves']."</td>\n"; ?>
                <?php echo "\t<td style='text-align:center'>".$tb_player['strikes']."</td>\n"; ?>
                </tr>
            <?php }?>
        </tbody>
    </table>
    <?php endif; ?>


    </div> <!-- container -->
    </div> <!-- site-content -->
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>
</div>
</div>
</body>
<?php include 'sitefooter.php' ; ?>
</html>

