<?php
session_start();  // Start the session to check if the user is logged in
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
$query = "SELECT side, zone_name, size, filled, victories, fails, commandMsg";
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

    echo "<td rowspan='".$rowspan."' style='background-color:".$zone_color.";".$crossed."'>";

    if ($isMyGuildConfirmed) {
        echo "<b>".$zone_name."</b> - ".min($zones[$side][$zone_name]['filled'], ($zones[$side][$zone_name]['size']-$zones[$side][$zone_name]['victories']))."/".$zones[$side][$zone_name]['size'];
        echo "</td'>\n";

    } else {
        // do not share sensitive information
        if ($zones[$side][$zone_name]['victories'] == 0) {
            // considered not open
            echo "<b>".$zone_name."</b> - ?/".$zones[$side][$zone_name]['size'];
        } else {
            echo "<b>".$zone_name."</b> - ".($zones[$side][$zone_name]['size']-$zones[$side][$zone_name]['victories'])."/".$zones[$side][$zone_name]['size'];
        }
        echo "</td'>\n";
    }
}

?>
<script>
function openZone(evt, zoneSide, zoneName) {
  // Declare all variables
  var i, tabcontent, tablinks;

  // Get all elements with class="tabcontent" and hide them
  tabcontent = document.getElementsByClassName(zoneSide+"tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }

  // Get all elements with class="tablinks" and remove the class "active"
  tablinks = document.getElementsByClassName(zoneSide+"tablinks");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }

  // Show the current tab, and add an "active" class to the button that opened the tab
  document.getElementById(zoneName).style.display = "block";
  evt.currentTarget.className += " active";
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
    <h3 style="color:green;display:inline"><?php echo ($isMyGuild ? 'You are '.($isOfficer ? 'an officer ' : '').'in this guild' : ''); ?></h3><small><?php echo ($isMyGuild && !$isMyGuildConfirmed ? ' (to confirm your identity and access restricted guild data, please run <i>go.register &lt;allyCode&gt; confirm</i>)':''); ?></small>
    <h3 style="color:green;display:inline"><?php echo ($isBonusGuild ? 'You are a guest in this guild' : ''); ?></h3>
    <div><br/><?php echo "(last update on ".$tw['lastUpdated'].")"; ?></div>
    
    <!-- Overview of zones -->
    <table>
    <tr>
        <td style="text-align:center">
            <h3><?php echo $tw['homeScore'];?></h3>
        </td>
        <td style="text-align:center">
            <h3><?php echo $tw['awayScore'];?></h3>
        </td>
    </tr>
    <tr>
        <td>
            <table style="background-color:dodgerblue;color:white">
                <tr>
                    <?php zone_txt('F2', 'home', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('F1', 'home', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('T2', 'home', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('T1', 'home', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <td style="width:0;background-color:black"></td>
                </tr>
                <tr>
                    <td style="width:0;background-color:black"></td>
                </tr>
                <tr>
                    <?php zone_txt('T4', 'home', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('T3', 'home', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <td style="width:0;background-color:black"></td>
                </tr>
                <tr>
                    <?php zone_txt('B2', 'home', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('B1', 'home', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <td style="width:0;background-color:black"></td>
                </tr>
                <tr>
                    <?php zone_txt('B4', 'home', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('B3', 'home', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <td style="width:0;background-color:black"></td>
                </tr>
                <tr>
                    <td style="width:0;background-color:black"></td>
                </tr>
            </table>
        </td>
        <td>
            <table style="background-color:red;color:white">
                <tr>
                    <td style="width:0;background-color:black"></td>
                    <?php zone_txt('T1', 'away', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('T2', 'away', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('F1', 'away', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('F2', 'away', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                </tr>
                <tr>
                    <td style="width:0;background-color:black"></td>
                </tr>
                <tr>
                    <td style="width:0;background-color:black"></td>
                    <?php zone_txt('T3', 'away', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('T4', 'away', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                </tr>
                <tr>
                    <td style="width:0;background-color:black"></td>
                    <?php zone_txt('B1', 'away', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('B2', 'away', $zones, 3, $isMyGuildConfirmed||$isBonusGuild); ?>
                </tr>
                <tr>
                    <td style="width:0;background-color:black"></td>
                    <?php zone_txt('B3', 'away', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                    <?php zone_txt('B4', 'away', $zones, 2, $isMyGuildConfirmed||$isBonusGuild); ?>
                </tr>
                <tr>
                    <td style="width:0;background-color:black"></td>
                </tr>
            </table>
        </td>
    </tr>

    <?php if ($isMyGuildConfirmed||$isBonusGuild): ?>
    <tr>
        <td style="vertical-align:top">
            <!-- HOME ZONES -->
            <!-- Zone links -->
            <div class="tab">
              <button class="hometablinks" onclick="openZone(event, 'home', 'hT1')" id="homedefaultOpen">T1</button>
              <button class="hometablinks" onclick="openZone(event, 'home', 'hT2')">T2</button>
              <button class="hometablinks" onclick="openZone(event, 'home', 'hT3')">T3</button>
              <button class="hometablinks" onclick="openZone(event, 'home', 'hT4')">T4</button>
              <button class="hometablinks" onclick="openZone(event, 'home', 'hB1')">B1</button>
              <button class="hometablinks" onclick="openZone(event, 'home', 'hB2')">B2</button>
              <button class="hometablinks" onclick="openZone(event, 'home', 'hB3')">B3</button>
              <button class="hometablinks" onclick="openZone(event, 'home', 'hB4')">B4</button>
              <button class="hometablinks" onclick="openZone(event, 'home', 'hF1')">F1</button>
              <button class="hometablinks" onclick="openZone(event, 'home', 'hF2')">F2</button>
            </div>

            <!-- Zone content -->
            <?php
            foreach($squads['home'] as $zone_name => $zone_squads) {
                echo "<div id='h".$zone_name."' class='hometabcontent'>";
                echo "<h3>".$zones['home'][$zone_name]['commandMsg']."</h3>";
                echo "<table>";
                foreach($zone_squads as $squad_id => $squad) {
                    echo "<tr>";
                    $display_player = true;
                    foreach($squad["cells"] as $cellIndex => $unit) {
                        if ($display_player) {
                        echo "<td><b>".$unit['player_name']."</b><br/>".$squad["gp"]." (".$squad["fights"].")</td>";
                        $display_player = false;
                        }
                        $unit_short_id = explode(':', $unit['defId'])[0];
                        echo "<td style='font-size:12".($squad['is_beaten']?";opacity:0.5":"")."'><img width='70px' src='IMAGES/CHARACTERS/".$unit_short_id.".png' alt='".$unit_short_id."'></td>";
                    }
                    echo "</tr>";
                }
                echo "</table>";
                echo "</div>";
            }
            ?>
        </td>
        <td style="vertical-align:top">
            <!-- AWAY ZONES -->
            <!-- Zone links -->
            <div class="tab">
              <button class="awaytablinks" onclick="openZone(event, 'away', 'aT1')" id="awaydefaultOpen">T1</button>
              <button class="awaytablinks" onclick="openZone(event, 'away', 'aT2')">T2</button>
              <button class="awaytablinks" onclick="openZone(event, 'away', 'aT3')">T3</button>
              <button class="awaytablinks" onclick="openZone(event, 'away', 'aT4')">T4</button>
              <button class="awaytablinks" onclick="openZone(event, 'away', 'aB1')">B1</button>
              <button class="awaytablinks" onclick="openZone(event, 'away', 'aB2')">B2</button>
              <button class="awaytablinks" onclick="openZone(event, 'away', 'aB3')">B3</button>
              <button class="awaytablinks" onclick="openZone(event, 'away', 'aB4')">B4</button>
              <button class="awaytablinks" onclick="openZone(event, 'away', 'aF1')">F1</button>
              <button class="awaytablinks" onclick="openZone(event, 'away', 'aF2')">F2</button>
            </div>

            <?php
            foreach($squads['away'] as $zone_name => $zone_squads) {
                echo "<div id='a".$zone_name."' class='awaytabcontent'>";
                echo "<h3>".$zones['away'][$zone_name]['commandMsg']."</h3>";
                echo "<table>";
                foreach($zone_squads as $squad_id => $squad) {
                    echo "<tr>";
                    $display_player = true;
                    foreach($squad["cells"] as $cellIndex => $unit) {
                        if ($display_player) {
                        echo "<td><b>".$unit['player_name']."</b><br/>".$squad["gp"]." (".$squad["fights"].")</td>";
                        $display_player = false;
                        }
                        $unit_short_id = explode(':', $unit['defId'])[0];
                        echo "<td style='font-size:12".($squad['is_beaten']?";opacity:0.5":"")."'><img width='70px' src='IMAGES/CHARACTERS/".$unit_short_id.".png' alt='".$unit_short_id."'></td>";

                    }
                    echo "</tr>";
                }
                echo "</table>";
                echo "</div>";
            }
            ?>

        </td>
    </tr>
    <?php endif; ?>
    </table>

    </div> <!-- container -->
    </div> <!-- site-content -->
    <div class="site-cache" id="site-cache" onclick="document.body.classList.toggle('with--sidebar')"></div>

</div>
</div>

<script>
// Get the element with id="homedefaultOpen" and click on it
document.getElementById("homedefaultOpen").click();
// Get the element with id="awaydefaultOpen" and click on it
document.getElementById("awaydefaultOpen").click();
</script>

</body>
</html>
