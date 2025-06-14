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

// Get the associated TW data
// Prepare the SQL query
$query = "SELECT guild_id, away_guild_id, away_guild_name, homeScore, awayScore,";
$query .= " lastUpdated FROM tw_history";
$query .= " WHERE id=".$tw_id;
#error_log("query = ".$query);
try {
    // Prepare the SQL query
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $tw_list = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $tw = array_values($tw_list)[0];

} catch (PDOException $e) {
    error_log("Error fetching TW data: " . $e->getMessage());
    echo "Error fetching TW data: " . $e->getMessage();
}
$guild_id = $tw['guild_id'];

// The guild page needs to be visited first
if (!isset($_SESSION['guild']) || ($_SESSION['guild']['id']!=$guild_id)){
    error_log("No valid guild data, redirect to g.php?gid=$guild_id");
    header("Location: g.php?gid=$guild_id");
    exit();
}
$guild = $_SESSION['guild'];

// define $isMyGuild, $isOfficer FROM $guild_id
include 'gvariables.php';

// --------------- GET ZONE INFO FOR THE TW -----------
// Prepare the SQL query
$query = "SELECT side, zone_name, size, filled, victories, fails,";
$query .= " zoneState, commandMsg";
$query .= " FROM tw_zones";
$query .= " WHERE tw_id=".$tw_id;
#error_log("query = ".$query);
try {
    // Prepare the SQL query to fetch the zone information
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $zone_list = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    error_log("Error fetching zone data: " . $e->getMessage());
    echo "Error fetching zone data: " . $e->getMessage();
}

// reorganize by side then zone
$zones = [];
foreach($zone_list as $zone) {
    $side = $zone['side'];
    if (!isset($zones[$side])) {
        $zones[$side] = [];
    }
    $zone_name = $zone['zone_name'];
    $zones[$side][$zone_name] = $zone;
}
//error_log(print_r($zones, true));

// --------------- GET ZONE INFO FOR THE SQUADS -----------
// Prepare the SQL query
$query = "SELECT tw_squads.id AS squad_id,";
$query .= " side, zone_name, player_name, defId, cellIndex,";
$query .= " is_beaten, fights, gp";
$query .= " FROM tw_squads";
$query .= " JOIN tw_squad_cells ON tw_squad_cells.squad_id=tw_squads.id";
$query .= " WHERE tw_id=".$tw_id;
$query .= " ORDER BY is_beaten, fights DESC, player_name, cellIndex";
#error_log("query = ".$query);
try {
    // Prepare the SQL query to fetch the zone information
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute();

    // Fetch all the results as an associative array
    $squad_list = $stmt->fetchAll(PDO::FETCH_ASSOC);

} catch (PDOException $e) {
    error_log("Error fetching zone data: " . $e->getMessage());
    echo "Error fetching zone data: " . $e->getMessage();
}

// reorganize by side then zone then team
$squads = [];
foreach($squad_list as $squad_element) {
    $side = $squad_element['side'];
    if (!isset($squads[$side])) {
        $squads[$side] = [];
    }
    $zone_name = $squad_element['zone_name'];
    if (!isset($squads[$side][$zone_name])) {
        $squads[$side][$zone_name] = [];
    }
    $squad_id = $squad_element['squad_id'];
    if (!isset($squads[$side][$zone_name][$squad_id])) {
        $squads[$side][$zone_name][$squad_id] = ["is_beaten" => $squad_element['is_beaten'],
                                                 "fights" => $squad_element['fights'],
                                                 "gp" => $squad_element['gp'],
                                                 "cells" => []];
    }
    $cellIndex = $squad_element['cellIndex'];
    $squads[$side][$zone_name][$squad_id]["cells"][$cellIndex] = $squad_element;
}

function zone_txt($zone_name, $side, $zones, $rowspan, $isMyGuildConfirmed) {
    if ($zones[$side][$zone_name]['zoneState'] == 'ZONECOMPLETE') {
        if ($side == 'home') {
            $zone_color = 'darkblue';
        } else {
            $zone_color = 'darkred';
        }

        $crossed = 'background-image: linear-gradient(to bottom right,  transparent calc(50% - 1px), black, transparent calc(50% + 1px))';

    } elseif ($isMyGuildConfirmed & ($zones[$side][$zone_name]['filled'] < $zones[$side][$zone_name]['size']) | ($zones[$side][$zone_name]['zoneState'] == 'ZONELOCKED')) {
        // filling status is only shown for guild players
        if ($side == 'home') {
            $zone_color = 'lightblue';
        } else {
            $zone_color = 'pink';
        }

        $crossed = '';
    } else {
        if ($side == 'home') {
            $zone_color = 'blue';
        } else {
            $zone_color = 'red';
        }
        
        $crossed = '';
    }

    if ($zones[$side][$zone_name]['zoneState'] == 'ZONEOPEN') {
        $border_style = "5px solid yellow";
    } else {
        $border_style = "3px solid white";
    }

    $side_zone_name = substr($side, 0, 1).$zone_name;
    echo '<td width="25" rowspan="'.$rowspan.'" style="background-color:'.$zone_color.';'.$crossed.';border:'.$border_style.'" onclick="openZone(event, \''.$side.'\', \''.$side_zone_name.'\')">';

    if ($isMyGuildConfirmed) {
        echo "<b>".$zone_name."</b><br/>".min($zones[$side][$zone_name]['filled'], ($zones[$side][$zone_name]['size']-$zones[$side][$zone_name]['victories']))."/".$zones[$side][$zone_name]['size'];
        echo "</td'>\n";

    } else {
        // do not share sensitive information
        if ($zones[$side][$zone_name]['victories'] == 0) {
            // considered not open
            echo "<b>".$zone_name."</b><br/>?/".$zones[$side][$zone_name]['size'];
        } else {
            echo "<b>".$zone_name."</b><br/>".($zones[$side][$zone_name]['size']-$zones[$side][$zone_name]['victories'])."/".$zones[$side][$zone_name]['size'];
        }
        echo "</td'>\n";
    }
}

?>
<script>
function openZone(evt, zoneSide, zoneName) {
  // Declare all variables
  var i, tabcontent, tablinks;

  // Get the default message "click a zone" and hide it
  document.getElementById("defaultmessage").style.display = "none";

  // Get all side elements with class="teamside" and hide them
  tabs = document.getElementsByClassName("teamside");
  for (i = 0; i < tabs.length; i++) {
    tabs[i].style.display = "none";
  }

  // Get all zone elements with class="tabcontent" and hide them
  tabcontent = document.getElementsByClassName(zoneSide+"tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }

  // Show the side tab, and add an "active" class to the button that opened the tab
  document.getElementById(zoneSide+"teamside").style.display = "block";

  // Show the current tab, and add an "active" class to the button that opened the tab
  document.getElementById(zoneName).style.display = "block";
}
</script>



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

<style>
/* Style the tab */
.tab {
  overflow: hidden;
  border: 1px solid #ccc;
  background-color: #f1f1f1;
}

/* Style the buttons that are used to open the tab content */
.tab button {
  background-color: inherit;
  float: left;
  border: none;
  outline: none;
  cursor: pointer;
  padding: 14px 16px;
  transition: 0.3s;
}

/* Change background color of buttons on hover */
.tab button:hover {
  background-color: #ddd;
}

/* Create an active/current tablink class */
.tab button.active {
  background-color: #ccc;
}

/* Style the tab content */
.tabcontent {
  display: none;
  padding: 6px 12px;
  border: 1px solid #ccc;
  border-top: none;
}
</style>

</head>
<body>
<div class="site-container">
<div class="site-pusher">

    <!-- Navigation Bar -->
    <?php include 'navbar.php' ; ?>

    <div class="site-content">
    <div class="container">

    <h2>TW for <a href='/g.php?gid=<?php echo $guild['id']; ?>'><?php echo $guild['name']; ?></a> vs <a href='/g.php?gid=<?php echo $tw['away_guild_id']; ?>'><?php echo $tw['away_guild_name']; ?></a></h2>

    <div class="card">
        <p style="color:green;display:inline"><?php echo ($isMyGuild ? 'You are '.($isOfficer ? 'an officer ' : '').'in this guild' : ''); ?><small><?php echo ($isMyGuild && !$isMyGuildConfirmed ? ' (to confirm your identity and access restricted guild data, please run <i>go.register &lt;allyCode&gt; confirm</i>)':''); ?></small>
        </p>

        <p style="color:green;display:inline"><?php echo ($isBonusGuild ? 'You are a guest in this guild' : ''); ?></p>
        <p style="color:red;display:inline"><br/><?php echo ($isAdmin ? 'You are logged as an administrator' : ''); ?></p>
    </div>

    <div><br/><?php echo "(last update on ".$tw['lastUpdated'].")"; ?></div>
    
    <!-- Overview of zones -->
    <div class="row">
    <div class="col s12">
    <div class="col s6">
        <div class="card">
            <h3><?php echo $tw['homeScore'];?></h3>
            <table height="200" width="200" style="table-layout:fixed;width:200px;height:200px;background-color:dodgerblue;color:white">
                <tr height="33">
                    <?php zone_txt('F2', 'home', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('F1', 'home', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('T2', 'home', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('T1', 'home', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                </tr>
                <tr height="33"/>
                <tr height="33">
                    <?php zone_txt('T4', 'home', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('T3', 'home', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                </tr>
                <tr height="33">
                    <?php zone_txt('B2', 'home', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('B1', 'home', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                </tr>
                <tr height="33">
                    <?php zone_txt('B4', 'home', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('B3', 'home', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                </tr>
                <tr height="33"/>
            </table>
        </div>
    </div>

    <div class="col s6">
        <div class="card">
            <h3><?php echo $tw['awayScore'];?></h3>
            <table height="200" width="200" style="table-layout:fixed;width:200px;height:200px;background-color:red;color:white">
                <tr height="33">
                    <?php zone_txt('T1', 'away', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('T2', 'away', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('F1', 'away', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('F2', 'away', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                </tr>
                <tr height="33"/>
                <tr height="33">
                    <?php zone_txt('T3', 'away', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('T4', 'away', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                </tr>
                <tr height="33">
                    <?php zone_txt('B1', 'away', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('B2', 'away', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                </tr>
                <tr height="33">
                    <?php zone_txt('B3', 'away', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('B4', 'away', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                </tr>
                <tr height="33"/>
            </table>
        </div>
    </div>
    </div>
    </div>

    <?php if ($isMyGuildConfirmed||$isBonusGuild): ?>
    <div class="card">
        <div id="defaultmessage">
            Click on a zone to see the teams
        </div>
    <div class="row">
    <div class="col s12">
    <div class="col s6 teamside" style="display:none" id="hometeamside">
            <!-- HOME ZONES -->
            <!-- Zone content -->
            <?php
            //foreach($squads['home'] as $zone_name => $zone_squads) {
            foreach(['B1', 'B2', 'B3', 'B4', 'T1', 'T2', 'T3', 'T4', 'F1', 'F2'] as $zone_name) {
                echo "<div id='h".$zone_name."' class='hometabcontent'>";
                if (isset($squads['home'][$zone_name])) {
                    $zone_squads = $squads['home'][$zone_name];
                    echo "<b>".$zone_name.": ".$zones['home'][$zone_name]['commandMsg']."</br>\n";
                    echo "<table>\n";
                    foreach($zone_squads as $squad_id => $squad) {
                        echo "<tr>";
                        $display_player = true;
                        foreach($squad["cells"] as $cellIndex => $unit) {
                            if ($display_player) {
                            echo "<td><b>".$unit['player_name']."</b><br/>".$squad["gp"]." (".$squad["fights"].")</td>";
                            $display_player = false;
                            }
                            $unit_short_id = explode(':', $unit['defId'])[0];
                            echo "<td style='font-size:12".($squad['is_beaten']?";opacity:0.5":"")."'><img width='50px' src='IMAGES/CHARACTERS/".$unit_short_id.".png' alt='".$unit_short_id."'></td>";
                        }
                        echo "</tr>\n";
                    }
                    echo "</table>\n";
                } else {
                    echo $zone_name.": zone not yet open, you cannot see inside";
                }
                echo "</div>";
            }
            ?>
    </div> <!-- class="col s6" -->

    <div class="col s6 teamside" style="display:none" id="awayteamside">
            <!-- AWAY ZONES -->
            <?php
            foreach(['B1', 'B2', 'B3', 'B4', 'T1', 'T2', 'T3', 'T4', 'F1', 'F2'] as $zone_name) {
                echo "<div id='a".$zone_name."' class='awaytabcontent'>";
                if (isset($squads['away'][$zone_name])) {
                    $zone_squads = $squads['away'][$zone_name];
                    echo "<b>".$zone_name.": ".$zones['away'][$zone_name]['commandMsg']."</br>\n";
                    echo "<table>\n";
                    foreach($zone_squads as $squad_id => $squad) {
                        echo "<tr>";
                        $display_player = true;
                        foreach($squad["cells"] as $cellIndex => $unit) {
                            if ($display_player) {
                            echo "<td><b>".$unit['player_name']."</b><br/>".$squad["gp"]." (".$squad["fights"].")</td>";
                            $display_player = false;
                            }
                            $unit_short_id = explode(':', $unit['defId'])[0];
                            echo "<td style='font-size:12".($squad['is_beaten']?";opacity:0.5":"")."'><img width='50px' src='IMAGES/CHARACTERS/".$unit_short_id.".png' alt='".$unit_short_id."'></td>";

                        }
                        echo "</tr>\n";
                    }
                    echo "</table>\n";
                } else {
                    echo $zone_name.": zone not yet open, you cannot see inside";
                }
                echo "</div>";
            }
            ?>

        </div>
        </div>
        </div>
        </div>
    <?php endif; ?>

    </div> <!-- container -->
    </div> <!-- site-content -->
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>

</div>
</div>

</body>
</html>
