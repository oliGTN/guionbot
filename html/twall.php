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
$query .= " zoneState, tw_history.lastUpdated AS lastUpdated,";
$query .= " TIMESTAMPDIFF(HOUR, tw_history.lastUpdated, CURRENT_TIMESTAMP) >=1 AS oldData";
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
        $tw_data[$guild_id]['oldData'] = $tw_line['oldData'];
        $tw_data[$guild_id]['zones'] = ['home'=>[], 'away'=>[]];
    }
    $tw_data[$guild_id]['zones'][$tw_line['side']][$tw_line['zone_name']] = [];
    $tw_data[$guild_id]['zones'][$tw_line['side']][$tw_line['zone_name']]['size'] = $tw_line['size'];
    $tw_data[$guild_id]['zones'][$tw_line['side']][$tw_line['zone_name']]['filled'] = $tw_line['filled'];
    $tw_data[$guild_id]['zones'][$tw_line['side']][$tw_line['zone_name']]['victories'] = $tw_line['victories'];
    $tw_data[$guild_id]['zones'][$tw_line['side']][$tw_line['zone_name']]['fails'] = $tw_line['fails'];
    $tw_data[$guild_id]['zones'][$tw_line['side']][$tw_line['zone_name']]['zoneState'] = $tw_line['zoneState'];
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

    <div class="card">
    <div class="row">
    <div class="dropdown">
        <form>
        <select style="width:200px" id="list" accesskey="target" onchange="twSelected()">
            <?php foreach($tw_list as $tw) {
                $tw_id_short = explode(":", $tw['tw_id'])[1];
                echo "<option value='".$tw_id_short."' ".($tw_id_short==$selected_ts?"selected='selected'":"").">".$tw['start_date']."</option>\n";
            }?>
        </select>
        </form>
    </div> <!-- dropdown -->
    </div> <!-- row -->
    </div> <!-- card -->
    <script>
        function twSelected(){
            let userPicked = document.getElementById("list").value;
            new_url ="twall.php?ts="+userPicked;
            //console.log(new_url);
            window.location.href=new_url;
        }
    </script>


    <?php
    // Reuse the common TW map renderer, but keep twall.php public:
    // no confidential zone data and no zone links.
    $twheader_use_existing_zones = true;
    include 'twheader.php';
    ?>

    <?php foreach ($tw_data as $guild_id => $tw) {
        $zones = $tw['zones'];

        $tw_header_data = [
            'guild_id' => $guild_id,
            'away_guild_id' => null,
            'guild_name' => $tw['homeName'],
            'away_guild_name' => $tw['awayName'],
            'homeScore' => $tw['homeScore'],
            'awayScore' => $tw['awayScore'],
            'lastUpdated' => $tw['lastUpdated'],
        ];
    ?>
        <h2>
            <a href="/g.php?gid=<?php echo (int) $guild_id; ?>">
                <?php echo htmlspecialchars($tw['homeName'], ENT_QUOTES, 'UTF-8'); ?>
            </a>
            vs
            <?php echo htmlspecialchars($tw['awayName'], ENT_QUOTES, 'UTF-8'); ?>
        </h2>

        <div><br/>
            <?php echo '(last update on ' . htmlspecialchars($tw['lastUpdated'], ENT_QUOTES, 'UTF-8') . ')'; ?>
        </div>

        <?php render_tw_map($tw_header_data, $zones, false, false); ?>
    <?php } ?>

    </div> <!-- container -->
    </div> <!-- site-content -->
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>

</div>
</div>

</body>
</html>
