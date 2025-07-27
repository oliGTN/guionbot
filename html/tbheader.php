<?php
// displays TB zones from $tb_id and $round
if (!isset($tb_id) | !isset($round)) {
    header("Location: index.php");
    exit();
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
$query = "SELECT zone_name, zone_id, zone_phase, score_step1, score_step2, score_step3,";
$query .= " score, estimated_platoons, estimated_strikes, estimated_deployments,";
$query .= " recon1_filled, recon2_filled, recon3_filled,";
$query .= " recon4_filled, recon5_filled, recon6_filled, recon_cmdMsg";
$query .= " FROM tb_zones";
$query .= " WHERE tb_id=".$tb_id." AND round=".$round;
$query .= " ORDER BY CASE WHEN INSTR(zone_name, 'DS')>0 THEN 0 WHEN INSTR(zone_name, 'MS')>0 THEN 1 ELSE 2 END + CASE WHEN is_bonus THEN 0.5 ELSE 0 END";
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

// --------------- GET CURRENT SCORE FOR THE TB -----------
// Prepare the SQL query
$query = "SELECT sum(case";
$query .= " WHEN score>=score_step3 then CASE WHEN SUBSTRING(tb_zones.zone_name, -1, 1)='b' THEN 1 ELSE 3 END";
$query .= " WHEN score>=score_step2 then CASE WHEN SUBSTRING(tb_zones.zone_name, -1, 1)='b' THEN 0 ELSE 2 END";
$query .= " WHEN score>=score_step1 then CASE WHEN SUBSTRING(tb_zones.zone_name, -1, 1)='b' THEN 0 ELSE 1 END";
$query .= " ELSE 0 END) AS stars";
$query .= " FROM tb_zones";

$query .= " JOIN (";
$query .= "   SELECT tb_zones.tb_id AS tb_id, zone_name, max(round) AS max_round";
$query .= "   FROM tb_zones";
$query .= "   JOIN tb_history ON tb_zones.tb_id=tb_history.id";
$query .= "   WHERE tb_zones.tb_id=".$tb_id;
$query .= "   GROUP BY tb_id, zone_name";
$query .= " ) T ON T.tb_id=tb_zones.tb_id AND T.zone_name = tb_zones.zone_name AND T.max_round = tb_zones.round";
$query .= " WHERE tb_zones.tb_id=".$tb_id." AND round<=".$round;
//error_log("query = ".$query);
try {
    // Prepare the SQL query to fetch the zone information
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $round_stars = $stmt->fetchAll(PDO::FETCH_ASSOC)[0]['stars'];

} catch (PDOException $e) {
    error_log("Error fetching TB data: " . $e->getMessage());
    echo "Error fetching TB data: " . $e->getMessage();
}

?>


    <h2 style="display:inline"><a href='/tbs.php?gid=<?php echo $guild['id']; ?>'>TB</a> for <a href='/g.php?gid=<?php echo $guild['id']; ?>'><?php echo $guild['name']; ?></a></h2> - <?php echo $tb['tb_name'];?>
    <div><?php echo "last update on ".$tb['lastUpdated']; ?></div>

    <div class="card">
        <p style="color:green;display:inline"><?php echo ($isMyGuild ? 'You are '.($isOfficer ? 'an officer ' : '').'in this guild' : ''); ?><small><?php echo ($isMyGuild && !$isMyGuildConfirmed ? ' (to confirm your identity and access restricted guild data, please run <i>go.register &lt;allyCode&gt; confirm</i>)':''); ?></small>
        </p>

        <p style="color:green;display:inline"><?php echo ($isBonusGuild ? 'You are a guest in this guild' : ''); ?></p>
        <p style="color:red;display:inline"><br/><?php echo ($isAdmin ? 'You are logged as an administrator' : ''); ?></p>
    </div>

<!-- Clickable round numbers for large screens -->
<div class="phases hide-on-small-and-down">
    <?php for($i = 1; $i <= $tb['max_round']; $i++) {
        echo "<a href='tb.php?id=".$tb_id."&round=".$i."' ".($i==$round?"class='active'":'').">".($i==$tb['current_round']?"&#11093;":'')."Round ".$i."</a>";
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
                echo "<option value='".$i."' ".($i==$round?"selected='selected'":'').">".($i==$tb['current_round']?"&#11093;":'')."Round ".$i."</option>\n";
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
<br/><br/>
</div>

<div class="card">
Score for this round: <?php echo $round_stars; ?>&#11088;
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

                //manage symbols for bonus zones
                $empty_star = "&#x2605;";
                $full_star = "&#11088;";
                $empty_circle = "&#x25CF;";
                $full_circle = "&#x1F535;";
                if (substr($zone['zone_name'], -1)=='b') {
                    $empty_star_12 = $empty_circle;
                    $star_12 = $full_circle;
                } else {
                    $empty_star_12 = $empty_star;
                    $star_12 = $full_star;
                }

                // prepare display variables
                if ($score >= $score_step3) {
                    $step_count = 3;
                    $star_txt = "$star_12$star_12$full_star";
                    $next_step_score = $score_step3;
                } elseif ($score >= $score_step2) {
                    $step_count = 2;
                    $star_txt = "$star_12$star_12$empty_star";
                    $next_step_score = $score_step3;
                } elseif ($score >= $score_step1) {
                    $step_count = 1;
                    $star_txt = "$star_12$empty_star_12$empty_star";
                    $next_step_score = $score_step2;
                } else {
                    $step_count = 0;
                    $star_txt = "$empty_star_12$empty_star_12$empty_star";
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
                                <?php echo number_format($score, 0, ".", " ");?> /<small><?php echo number_format($next_step_score, 0, ".", " ");?></small>
                            </div>
                            <svg width="100%" height="70">
                                <rect width="<?php echo $x_score;?>%" height="30" style="fill:green;">
                                    <title>Current score: <?php echo number_format($score, 0, ".", " ");?></title>
                                </rect>
                                <rect id="fights-<?php echo $zone['zone_name'];?>" x="<?php echo $x_score;?>%" width="<?php echo $x_strikes-$x_score;?>%" height="30" style="fill:orange;">
                                    <title>Estimated strikes: <?php echo number_format($estimated_strikes, 0, ".", " ");?></title>
                                </rect>
                                <rect id="deploy-<?php echo $zone['zone_name'];?>" x="<?php echo $x_strikes;?>%" width="<?php echo $x_deployments-$x_strikes;?>%" height="30" style="fill:yellow;">
                                    <title>Deployments: <?php echo number_format($estimated_strikes, 0, ".", " ");?></title>
                                </rect>
                                <rect width="100%" height="30" style="fill:none;stroke:black;"></rect>
                                <line x1="<?php echo $x_step1?>%" y1="0" x2="<?php echo $x_step1;?>%" y2="30" style="stroke:gray"></line>
                                <line x1="<?php echo $x_step2?>%" y1="0" x2="<?php echo $x_step2;?>%" y2="30" style="stroke:gray"></line>
                                <line x1="<?php echo $x_score?>%" y1="0" x2="<?php echo $x_score;?>%" y2="50" style="stroke:darkgreen;stroke-width:2"></line>
                                <text x="0%" y="40" font-size="10">0</text>
                                <text x="<?php echo $x_step1;?>%" y="40" text-anchor="end" font-size="10"><?php echo number_format($score_step1, 0, ".", " ");?></text>
                                <text x="<?php echo $x_step2;?>%" y="40" text-anchor="end" font-size="10"><?php echo number_format($score_step2, 0, ".", " ");?></text>
                                <text x="100%" y="40" text-anchor="end" font-size="10"><?php echo number_format($score_step3, 0, ".", " ");?></text>
                                <text x="<?php echo $x_score;?>%" y="60" text-anchor="<?php echo ($score<$score_step3/2?'':"end");?>" font-size="12">&nbsp;<?php echo number_format($score, 0, ".", " ");?>&nbsp;</text>
                            </svg>
                            <div class="row">
                            <div class="col s12"><small>
                                <b>Platoons</b>
                                <p class="from-game-status"><?php echo $zone['recon_cmdMsg']; ?></p>
                                <table>
                                    <tr>
                                        <td style="text-align:center;background-color:<?php echo ($zone['recon1_filled']==15?'lightgreen':'orange');?>"><?php echo $zone['recon1_filled'];?></td>
                                        <td style="text-align:center;background-color:<?php echo ($zone['recon4_filled']==15?'lightgreen':'orange');?>"><?php echo $zone['recon4_filled'];?></td>
                                    </tr>
                                    <tr>
                                        <td style="text-align:center;background-color:<?php echo ($zone['recon2_filled']==15?'lightgreen':'orange');?>"><?php echo $zone['recon2_filled'];?></td>
                                        <td style="text-align:center;background-color:<?php echo ($zone['recon5_filled']==15?'lightgreen':'orange');?>"><?php echo $zone['recon5_filled'];?></td>
                                    </tr>
                                    <tr>
                                        <td style="text-align:center;background-color:<?php echo ($zone['recon3_filled']==15?'lightgreen':'orange');?>"><?php echo $zone['recon3_filled'];?></td>
                                        <td style="text-align:center;background-color:<?php echo ($zone['recon6_filled']==15?'lightgreen':'orange');?>"><?php echo $zone['recon6_filled'];?></td>
                                    </tr>
                                </table></small>
                            </div>
                            </div>
                        </div>
                    </div>
                </div>
            <?php }
        }?>
    </div>
</div>

