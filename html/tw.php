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
    error_log("No id: redirect to index.php");
    header("Location: index.php");
    exit();
}

$tw_id = $_GET['id'];

// Get the associated TW data (define $tw)
include 'twvariables.php';

// define $isMyGuild, $isOfficer FROM $guild_id
include 'gvariables.php';

// --------------- GET PLAYER INFO FOR THE TW -----------
// Prepare the SQL query
$query = "SELECT name, allyCode, guildName, event_type,";
$query .= " zone_id IN ('tw_jakku01_phase03_conflict01', 'tw_jakku01_phase04_conflict01') as is_ship, ";
$query .= " count(*) FROM tw_events";
$query .= " JOIN players ON players.playerId=tw_events.author_id";
$query .= " WHERE tw_id=".$tw_id." AND guildId='".$guild_id."' AND event_type!='SCORE'";
$query .= " GROUP BY allyCode, event_type, zone_id IN ('tw_jakku01_phase03_conflict01', 'tw_jakku01_phase04_conflict01')";
$query .= " ORDER BY name";
//error_log("query = ".$query);
try {
    // Prepare the SQL query to fetch the zone information
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $player_event_list = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    error_log("Error fetching zone data: " . $e->getMessage());
    echo "Error fetching zone data: " . $e->getMessage();
}

// reorganize by player
$tw_players = [];
foreach($player_event_list as $player_event) {
    $player_name = $player_event['name'];
    $allyCode = $player_event['allyCode'];
    if (!isset($tw_players[$player_name])) {
        $tw_players[$player_name] = array(
            'allyCode' => $allyCode,
            't_fights' => 0,
            'c_fights' => 0,
            's_fights' => 0,
            't_wins' => 0,
            'c_wins' => 0,
            's_wins' => 0,
            't_deploy' => 0,
            'c_deploy' => 0,
            's_deploy' => 0,
        );
    }
    if ($player_event['event_type']=='DEPLOY') {
        $tw_players[$player_name]['t_deploy'] += $player_event['count(*)'];
        if ($player_event['is_ship']) {
            $tw_players[$player_name]['s_deploy'] += $player_event['count(*)'];
        } else {
            $tw_players[$player_name]['c_deploy'] += $player_event['count(*)'];
        }
    } else if ($player_event['event_type']=='SQUADLOCKED') {
        $tw_players[$player_name]['t_fights'] += $player_event['count(*)'];
        if ($player_event['is_ship']) {
            $tw_players[$player_name]['s_fights'] += $player_event['count(*)'];
        } else {
            $tw_players[$player_name]['c_fights'] += $player_event['count(*)'];
        }
    } else if ($player_event['event_type']=='SQUADDEFEATED') {
        $tw_players[$player_name]['t_wins'] += $player_event['count(*)'];
        if ($player_event['is_ship']) {
            $tw_players[$player_name]['s_wins'] += $player_event['count(*)'];
        } else {
            $tw_players[$player_name]['c_wins'] += $player_event['count(*)'];
        }
    }
}
$list_tw_players = [];
foreach($tw_players as $name => $tw_player) {
    $player = array('name'=>$name);
    $player = array_merge($player, $tw_player);
    array_push($list_tw_players, $player);
}

// --------------- SORTING BY COLUMN -----------
// Get sort parameters from URL or set default
$valid_columns = ['name', 't_fights', 't_wins', 'c_fights', 'c_wins', 's_fights', 's_wins'];
$sort_column = isset($_GET['sort']) && in_array($_GET['sort'], $valid_columns) ? $_GET['sort'] : 'name';
$sort_order = isset($_GET['order']) && strtolower($_GET['order']) === 'desc' ? 'DESC' : 'ASC';

// Toggle sort order for next click
$next_order = $sort_order === 'ASC' ? 'DESC' : 'ASC';

// sort players
if ($sort_column<>'name') {
    usort($list_tw_players, function ($item1, $item2) use ($sort_order, $sort_column) {
        if ($item1[$sort_column] == $item2[$sort_column]) return 0;
        if ($sort_order == 'DESC') {
            return $item1[$sort_column] > $item2[$sort_column] ? -1 : 1;
        } else {
            return $item1[$sort_column] < $item2[$sort_column] ? -1 : 1;
        }
    });
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

    <?php include 'twheader.php' ; ?>

    <?php if ($isMyGuildConfirmed||$isBonusGuild): ?>
    <h3> Player stats</h3>
    <div class="card">
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th class="<?php echo ($sort_column === 'name') ? 'active-sort' : ''; ?>"><a href="tw.php?id=<?php echo $_GET['id'];?>&sort=name&order=<?php echo ($sort_column=='name'?$next_order:'ASC'); ?>">Name</a></th>
                <th class="<?php echo ($sort_column === 't_fights') ? 'active-sort' : ''; ?>"><a href="tw.php?id=<?php echo $_GET['id'];?>&sort=t_fights&order=<?php echo ($sort_column=='t_fights'?$next_order:'DESC'); ?>">Total fights</a></th>
                <th class="<?php echo ($sort_column === 't_wins') ? 'active-sort' : ''; ?>"><a href="tw.php?id=<?php echo $_GET['id'];?>&sort=t_wins&order=<?php echo ($sort_column=='t_wins'?$next_order:'DESC'); ?>">Total wins</a></th>
                <th class="hide-on-med-and-down <?php echo ($sort_column === 'c_fights') ? 'active-sort' : ''; ?>"><a href="tw.php?id=<?php echo $_GET['id'];?>&sort=c_fights&order=<?php echo ($sort_column=='c_fights'?$next_order:'DESC'); ?>">Ground fights</a></th>
                <th class="hide-on-med-and-down <?php echo ($sort_column === 'c_wins') ? 'active-sort' : ''; ?>"><a href="tw.php?id=<?php echo $_GET['id'];?>&sort=c_wins&order=<?php echo ($sort_column=='c_wins'?$next_order:'DESC'); ?>">Ground wins</a></th>
                <th class="hide-on-med-and-down <?php echo ($sort_column === 's_fights') ? 'active-sort' : ''; ?>"><a href="tw.php?id=<?php echo $_GET['id'];?>&sort=s_fights&order=<?php echo ($sort_column=='s_wins'?$next_order:'DESC'); ?>">Ship fights</a></th>
                <th class="hide-on-med-and-down <?php echo ($sort_column === 's_wins') ? 'active-sort' : ''; ?>"><a href="tw.php?id=<?php echo $_GET['id'];?>&sort=s_wins&order=<?php echo ($sort_column=='s_wins'?$next_order:'DESC'); ?>">Ship wins</a></th>

            </tr>
        </thead>
        <tbody>
            <?php
            echo "\n";
            // Loop through each player and display in a table row
            if (!empty($tw_players)) {
                $i_player = 1;
                if (!isset($_SESSION['allyCodes'])) {
                    $_SESSION['allyCodes'] = [];
                }
                foreach ($list_tw_players as $player) {
                    $isMyallyCode = in_array(intval($player['allyCode']), array_keys($_SESSION['allyCodes']), true);
                    $line_color = ($isMyallyCode?'lightgray':'');
                    echo "\t\t\t<tr style='background-color:".$line_color."'>\n";
                    echo "\t\t\t<td>".$i_player."</td>\n";
                    echo "\t\t\t<td>".htmlspecialchars($player['name'])."</td>\n";
                    echo "\t\t\t\t<td>".$player['t_fights']."</td>\n";
                    echo "\t\t\t\t<td>".$player['t_wins']."</td>\n";
                    echo "\t\t\t\t<td class='hide-on-med-and-down'>".$player['c_fights']."</td>\n";
                    echo "\t\t\t\t<td class='hide-on-med-and-down'>".$player['c_wins']."</td>\n";
                    echo "\t\t\t\t<td class='hide-on-med-and-down'>".$player['s_fights']."</td>\n";
                    echo "\t\t\t\t<td class='hide-on-med-and-down'>".$player['s_wins']."</td></tr>\n";
                    $i_player += 1;
                }
            } else {
                echo "<tr><td colspan='2'>No players found.</td></tr>\n";
            }
            ?>
        </tbody>
    </table>
    </div>
    <?php else: ?>
        You are not allowed to see player stats for this guild
    <?php endif; //($isMyGuildConfirmed||$isBonusGuild) ?>

    </div> <!-- container -->
    </div> <!-- site-content -->
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>

</div>
</div>

</body>

</html>
