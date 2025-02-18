<?php
// server should keep session data for AT LEAST 1 hour
ini_set('session.gc_maxlifetime', 3600*24*7);
// each client should remember their session id for EXACTLY 1 hour
session_set_cookie_params(3600*24*7);
// Start the session to check if the user is logged in
session_start();

require 'guionbotdb.php';  // Include the database connection for guionbotdb

// Get the list of TBs
// Prepare the SQL query
$query = "SELECT DISTINCT(tb_id), date(start_date) as start_date";
$query .= " FROM tb_history";
$query .= " ORDER BY start_date DESC";
#error_log("query = ".$query);
try {
    // Prepare the SQL query
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $tb_list = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    error_log("Error fetching TB list: " . $e->getMessage());
    echo "Error fetching TB list: " . $e->getMessage();
}
if (isset($_GET['ts']) && substr($_GET['ts'], 0, 1)=='O' && is_numeric(substr($_GET['ts'], 1, 13)) && strlen($_GET['ts'])==14) {
    $tb_id = null;
    foreach($tb_list as $tb) {
        if (strpos($tb['tb_id'], $_GET['ts'])!==false ) {
            $tb_id = $tb['tb_id'];
            $tb_start_date = $tb['start_date'];
        }
    }
} else {
    $latest_tb = array_values($tb_list)[0];
    $tb_id = $latest_tb['tb_id'];
    $tb_start_date = $latest_tb['start_date'];
}


// Get the associated TB data
// Prepare the SQL query
$query = "SELECT tb_history.id AS id, guild_id, name, zone_name,";
$query .= " round, score_step1, score_step2, score_step3, score";
$query .= " FROM tb_history";
$query .= " JOIN guilds ON guilds.id=guild_id";
$query .= " JOIN tb_zones ON tb_zones.tb_id=tb_history.id";
$query .= " WHERE tb_history.tb_id='".$tb_id."'";
$query .= " ORDER BY name";
//error_log("query = ".$query);
try {
    // Prepare the SQL query
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $tb_db_data = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    error_log("Error fetching TW data: " . $e->getMessage());
    echo "Error fetching TW data: " . $e->getMessage();
}
$tb_data = [];
foreach($tb_db_data as $tb_line) {
    $guild_id = $tb_line['guild_id'];
    if (!isset($tb_data[$guild_id])) {
        $tb_data[$guild_id] = [];
        $tb_data[$guild_id]['id'] = $tb_line['id'];
        $tb_data[$guild_id]['name'] = $tb_line['name'];
        $tb_data[$guild_id]['zones'] = [];
    }

    $zone = $tb_line;
    $score = $zone['score'];
    $score_step1 = $zone['score_step1'];
    $score_step2 = $zone['score_step2'];
    $score_step3 = $zone['score_step3'];

    //manage symbols for bonus zones
    if (substr($zone['zone_name'], -1)=='b') {
        $empty_star_12 = "&#x26AA;";
        $star_12 = "&#x1F535;";
    } else {
        $empty_star_12 = "&#10025;";
        $star_12 = "&#11088;";
    }

    // prepare display variables
    if ($score >= $score_step3) {
        $step_count = 3;
        $star_txt = "$star_12$star_12&#11088;";
    } elseif ($score >= $score_step2) {
        $step_count = 2;
        $star_txt = "$star_12$star_12&#10025;";
    } elseif ($score >= $score_step1) {
        $step_count = 1;
        $star_txt = "$star_12$empty_star_12&#10025;";
    } else {
        $step_count = 0;
        $star_txt = "$empty_star_12$empty_star_12&#10025;";
    }

    $tb_data[$guild_id]['zones'][$tb_line['zone_name']] = [];
    $tb_data[$guild_id]['zones'][$tb_line['zone_name']]['star_txt'] = $star_txt;
}

// --------------- GET CURRENT SCORE FOR THE TB -----------
// Prepare the SQL query
$query = "SELECT guild_id, sum(case";
$query .= " WHEN score>=score_step3 then CASE WHEN SUBSTRING(zone_name, -1, 1)='b' THEN 1 ELSE 3 END";
$query .= " WHEN score>=score_step2 then CASE WHEN SUBSTRING(zone_name, -1, 1)='b' THEN 0 ELSE 2 END";
$query .= " WHEN score>=score_step1 then CASE WHEN SUBSTRING(zone_name, -1, 1)='b' THEN 0 ELSE 1 END";
$query .= " ELSE 0 END) AS stars";
$query .= " FROM tb_zones";
$query .= " JOIN tb_history ON tb_zones.tb_id=tb_history.id";
$query .= " WHERE tb_history.tb_id='".$tb_id."'";
$query .= " GROUP BY guild_id";
error_log("query = ".$query);
try {
    // Prepare the SQL query to fetch the zone information
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $guild_stars = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    error_log("Error fetching TB data: " . $e->getMessage());
    echo "Error fetching TB data: " . $e->getMessage();
}
foreach($guild_stars as $tb_line) {
    $guild_id = $tb_line['guild_id'];
    $stars = $tb_line['stars'];
    if (isset($tb_data[$guild_id])) {
        $tb_data[$guild_id]['stars'] = $stars;
    } else {
        $tb_data[$guild_id]['stars'] = 0;
    }
}

function zone_txt($zone_name, $zones, $colspan) {
    if (isset($zones[$zone_name])) {
        // the zone exists, so it is open
        if (strpos($zone_name, 'DS')!==false) {
            $zone_color='red';
        } else if (strpos($zone_name, 'MS')!==false) {
            $zone_color='yellow';
        } else { // LS
            $zone_color='dodgerblue';
        }
        $star_txt = $zones[$zone_name]['star_txt'];
    } else {
        // zone is closed
        if (strpos($zone_name, 'DS')!==false) {
            $zone_color='darkred';
        } else if (strpos($zone_name, 'MS')!==false) {
            $zone_color='darkorange';
        } else { // LS
            $zone_color='blue';
        }
        $star_txt = '';
    }

    echo '<td colspan="'.$colspan.'" style="background-color:'.$zone_color.';text-align:center;border:3px solid white">'.$zone_name.'<br/>'.$star_txt.'</td>';
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

    <h2>All TBs</h2>

    <div class="dropdown">
        <form>
        <select style="width:200px" name="list" id="list" accesskey="target" onchange="tbSelected()">
            <?php foreach($tb_list as $tb) {
                $tb_id_short = explode(":", $tb['tb_id'])[1];
                echo "<option value='".$tb_id_short."' ".($tb_id_short==$_GET['ts']?"selected='selected'":"").">".$tb['start_date']."</option>\n";
            }?>
        </select>
        </form>
    </div>
    <script>
        function tbSelected(){
            let userPicked = document.getElementById("list").value;
            new_url ="tball.php?ts="+userPicked;
            console.log(new_url);
            window.location.href=new_url;
        }
    </script>

    <?php foreach($tb_data as $guild_id => $tb) {
        $zones = $tb['zones'];
    ?>
    <!-- Overview of zones -->
    <div class="row">
    <div class="col s12">
    <div class="col s6">
    <div class="card">
    <h3><a href="tb.php?id=<?php echo $tb['id'];?>"><?php echo $tb['name'];?></a>: <?php echo $tb_data[$guild_id]['stars']; ?>&#11088</h3>

    <table style="display:block">
        <colgroup>
            <col span="1" style="width:10%"/>
            <col span="1" style="width:10%"/>
            <col span="1" style="width:10%"/>
            <col span="1" style="width:10%"/>
            <col span="1" style="width:10%"/>
            <col span="1" style="width:10%"/>
            <col span="1" style="width:10%"/>
            <col span="1" style="width:10%"/>
            <col span="1" style="width:10%"/>
            <col span="1" style="width:10%"/>
        </colgroup>
        <tbody>
        <tr style="border:3px solid white">
            <td style="background-color:black;border:3px solid white" colspan="1"></td>
            <?php zone_txt('ROTE6-DS', $zones, 2); ?>
            <td style="background-color:black;border:3px solid white" colspan="2"></td>
            <?php zone_txt('ROTE6-MS', $zones, 2); ?>
            <?php zone_txt('ROTE6-LS', $zones, 2); ?>
            <td style="background-color:black;border:3px solid white" colspan="1"></td>
        </tr>
        <tr>
            <?php zone_txt('ROTE5-DS', $zones, 2); ?>
            <td style="background-color:black;border:3px solid white" colspan="2"></td>
            <?php zone_txt('ROTE5-MS', $zones, 2); ?>
            <td style="background-color:black;border:3px solid white" colspan="2"></td>
            <?php zone_txt('ROTE5-LS', $zones, 2); ?>
        <tr>
            <td style="background-color:black;border:3px solid white" colspan="1"></td>
            <?php zone_txt('ROTE4-DS', $zones, 2); ?>
            <?php zone_txt('ROTE4-MSb', $zones, 2); ?>
            <?php zone_txt('ROTE4-MS', $zones, 2); ?>
            <?php zone_txt('ROTE4-LS', $zones, 2); ?>
            <td style="background-color:black;border:3px solid white" colspan="1"></td>
        </tr>
        <tr>
            <?php zone_txt('ROTE3-DS', $zones, 2); ?>
            <td style="background-color:black;border:3px solid white" colspan="2"></td>
            <?php zone_txt('ROTE3-MS', $zones, 2); ?>
            <?php zone_txt('ROTE3-LSb', $zones, 2); ?>
            <?php zone_txt('ROTE3-LS', $zones, 2); ?>
        </tr>
        <tr>
            <td style="background-color:black;border:3px solid white" colspan="1"></td>
            <?php zone_txt('ROTE2-DS', $zones, 2); ?>
            <?php zone_txt('ROTE2-MS', $zones, 4); ?>
            <?php zone_txt('ROTE2-LS', $zones, 2); ?>
            <td style="background-color:black;border:3px solid white" colspan="1"></td>
        </tr>
        <tr>
            <td style="background-color:black;border:3px solid white" colspan="2"></td>
            <?php zone_txt('ROTE1-DS', $zones, 2); ?>
            <?php zone_txt('ROTE1-MS', $zones, 2); ?>
            <?php zone_txt('ROTE1-LS', $zones, 2); ?>
            <td style="background-color:black;border:3px solid white" colspan="2"></td>
        </tr>
        </tbody>
    </table>
    </div>
    </div>
    </div>
    </div>

    <?php } ?>

    </div> <!-- container -->
    </div> <!-- site-content -->
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>

</div>
</div>

</body>
</html>
