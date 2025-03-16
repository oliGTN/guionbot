<?php
// server should keep session data for AT LEAST 1 hour
ini_set('session.gc_maxlifetime', 3600*24*7);
// each client should remember their session id for EXACTLY 1 hour
session_set_cookie_params(3600*24*7);
// Start the session to check if the user is logged in
session_start();

require 'guionbotdb.php';  // Include the database connection for guionbotdb

// Get the list of TWs
// Prepare the SQL query
$query = "SELECT DISTINCT(tw_id), date(start_date) as start_date";
$query .= " FROM tw_history";
$query .= " ORDER BY start_date DESC";
//error_log("query = ".$query);
try {
    // Prepare the SQL query
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $tw_list = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    error_log("Error fetching TW list: " . $e->getMessage());
    echo "Error fetching TW list: " . $e->getMessage();
}
if (isset($_GET['ts']) && substr($_GET['ts'], 0, 1)=='O' && is_numeric(substr($_GET['ts'], 1, 13)) && strlen($_GET['ts'])==14) {
    $selected_ts = $_GET['ts'];
    $tw_id = null;
    foreach($tw_list as $tw) {
        if (strpos($tw['tw_id'], $_GET['ts'])!==false ) {
            $tw_id = $tw['tw_id'];
            $tw_start_date = $tw['start_date'];
        }
    }
} else {
    $latest_tw = array_values($tw_list)[0];
    $tw_id = $latest_tw['tw_id'];
    $tw_start_date = $latest_tw['start_date'];
    $selected_ts = explode(":", $tw_id)[1];
}


// Get the associated TW data
// Prepare the SQL query
$query = "SELECT tw_history.id AS id, guild_id, gh.name AS homeName,  ga.name AS awayName, homeScore, awayScore,";
$query .= " zone_name, side, size, filled, victories, fails,";
$query .= " zoneState, tw_history.lastUpdated AS lastUpdated";
$query .= " FROM tw_history";
$query .= " JOIN guilds AS gh ON gh.id=guild_id";
$query .= " JOIN guilds AS ga ON ga.id=away_guild_id";
$query .= " JOIN tw_zones ON tw_zones.tw_id=tw_history.id";
$query .= " WHERE tw_history.tw_id='".$tw_id."'";
$query .= " ORDER BY gh.name";
//error_log("query = ".$query);
try {
    // Prepare the SQL query
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $tw_db_data = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    error_log("Error fetching TW data: " . $e->getMessage());
    echo "Error fetching TW data: " . $e->getMessage();
}
$tw_data = [];
foreach($tw_db_data as $tw_line) {
    $guild_id = $tw_line['guild_id'];
    if (!isset($tw_data[$guild_id])) {
        $tw_data[$guild_id] = [];
        $tw_data[$guild_id]['id'] = $tw_line['id'];
        $tw_data[$guild_id]['homeName'] = $tw_line['homeName'];
        $tw_data[$guild_id]['awayName'] = $tw_line['awayName'];
        $tw_data[$guild_id]['homeScore'] = $tw_line['homeScore'];
        $tw_data[$guild_id]['awayScore'] = $tw_line['awayScore'];
        $tw_data[$guild_id]['lastUpdated'] = $tw_line['lastUpdated'];
        $tw_data[$guild_id]['zones'] = ['home'=>[], 'away'=>[]];
    }
    $tw_data[$guild_id]['zones'][$tw_line['side']][$tw_line['zone_name']] = [];
    $tw_data[$guild_id]['zones'][$tw_line['side']][$tw_line['zone_name']]['size'] = $tw_line['size'];
    $tw_data[$guild_id]['zones'][$tw_line['side']][$tw_line['zone_name']]['filled'] = $tw_line['filled'];
    $tw_data[$guild_id]['zones'][$tw_line['side']][$tw_line['zone_name']]['victories'] = $tw_line['victories'];
    $tw_data[$guild_id]['zones'][$tw_line['side']][$tw_line['zone_name']]['fails'] = $tw_line['fails'];
    $tw_data[$guild_id]['zones'][$tw_line['side']][$tw_line['zone_name']]['zoneState'] = $tw_line['zoneState'];
}

function zone_txt($zone_name, $side, $zones, $rowspan, $isMyGuildConfirmed) {
    if ($zones[$side][$zone_name]['victories'] == $zones[$side][$zone_name]['size']) {
        $zone_color = 'dark';
        $crossed = 'background-image: linear-gradient(to bottom right,  transparent calc(50% - 1px), black, transparent calc(50% + 1px))';
    } elseif ($zones[$side][$zone_name]['filled'] < $zones[$side][$zone_name]['size']) {
        $zone_color = 'light';
        $crossed = '';
    } else {
        $zone_color = '';
        $crossed = '';
    }
    if ($side == 'home') {
        $zone_color .= 'blue';
    } else {
        $zone_color .= 'red';
    }

    $side_zone_name = substr($side, 0, 1).$zone_name;
    echo '<td width="25" rowspan="'.$rowspan.'" style="background-color:'.$zone_color.';'.$crossed.';border:3px solid white" onclick="openZone(event, \''.$side.'\', \''.$side_zone_name.'\')">';

        // do not share sensitive information
        if ($zones[$side][$zone_name]['zoneState'] == 'ZONELOCKED') {
            // considered not open
            echo "<b>".$zone_name."</b><br/>?/".$zones[$side][$zone_name]['size'];
        } else {
            echo "<b>".$zone_name."</b><br/>".($zones[$side][$zone_name]['size']-$zones[$side][$zone_name]['victories'])."/".$zones[$side][$zone_name]['size'];
        }
        echo "</td'>\n";
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

    <h2>All TWs</h2>

    <div class="dropdown">
        <form>
        <select style="width:200px" name="list" id="list" accesskey="target" onchange="twSelected()">
            <?php foreach($tw_list as $tw) {
                $tw_id_short = explode(":", $tw['tw_id'])[1];
                echo "<option value='".$tw_id_short."' ".($tw_id_short==$selected_ts?"selected='selected'":"").">".$tw['start_date']."</option>\n";
            }?>
        </select>
        </form>
    </div>
    <script>
        function twSelected(){
            let userPicked = document.getElementById("list").value;
            new_url ="twall.php?ts="+userPicked;
            console.log(new_url);
            window.location.href=new_url;
        }
    </script>


    <?php foreach($tw_data as $guild_id => $tw) {
        $zones = $tw['zones'];
    ?>
    <!-- Overview of zones -->
    <div class="card">
    <div class="row">
    <div class="col s12">
            <p><a href="tw.php?id=<?php echo $tw['id'];?>"><?php echo ($tw['homeScore']>=$tw['awayScore']?'&#9989;':'&#10060;')."<b>".$tw['homeName']." vs ".$tw['awayName']."</b>";?></a></p>
            <p>(last Update on <?php echo $tw['lastUpdated'];?>)</p>
    <div class="card">
    <div class="col s6">
            <b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<?php echo $tw['homeScore'];?></b>
            <table height="200" width="200" style="table-layout:fixed;width:200px;height:200px;background-color:dodgerblue;color:white">
                <tr height="33">
                    <?php zone_txt('F2', 'home', $zones, 2, false); ?>
                    <?php zone_txt('F1', 'home', $zones, 2, false); ?>
                    <?php zone_txt('T2', 'home', $zones, 3, false); ?>
                    <?php zone_txt('T1', 'home', $zones, 3, false); ?>
                </tr>
                <tr height="33"/>
                <tr height="33">
                    <?php zone_txt('T4', 'home', $zones, 2, false); ?>
                    <?php zone_txt('T3', 'home', $zones, 2, false); ?>
                </tr>
                <tr height="33">
                    <?php zone_txt('B2', 'home', $zones, 3, false); ?>
                    <?php zone_txt('B1', 'home', $zones, 3, false); ?>
                </tr>
                <tr height="33">
                    <?php zone_txt('B4', 'home', $zones, 3, false); ?>
                    <?php zone_txt('B3', 'home', $zones, 3, false); ?>
                </tr>
                <tr height="33"/>
            </table>
    </div> <!-- col s6 -->
    </div> <!-- card -->

    <div class="card">
    <div class="col s6">
            <b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<?php echo $tw['awayScore'];?></b>
            <table height="200" width="200" style="table-layout:fixed;width:200px;height:200px;background-color:red;color:white">
                <tr height="33">
                    <?php zone_txt('T1', 'away', $zones, 3, false); ?>
                    <?php zone_txt('T2', 'away', $zones, 3, false); ?>
                    <?php zone_txt('F1', 'away', $zones, 2, false); ?>
                    <?php zone_txt('F2', 'away', $zones, 2, false); ?>
                </tr>
                <tr height="33"/>
                <tr height="33">
                    <?php zone_txt('T3', 'away', $zones, 2, false); ?>
                    <?php zone_txt('T4', 'away', $zones, 2, false); ?>
                </tr>
                <tr height="33">
                    <?php zone_txt('B1', 'away', $zones, 3, false); ?>
                    <?php zone_txt('B2', 'away', $zones, 3, false); ?>
                </tr>
                <tr height="33">
                    <?php zone_txt('B3', 'away', $zones, 2, false); ?>
                    <?php zone_txt('B4', 'away', $zones, 2, false); ?>
                </tr>
                <tr height="33"/>
            </table>
    </div> <!-- col s6 -->
    </div> <!-- card -->
    </div> <!-- col s12 -->
    </div> <!-- row -->
    </div> <!-- card -->

    <?php } ?>

    </div> <!-- container -->
    </div> <!-- site-content -->
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>

</div>
</div>

</body>
</html>
