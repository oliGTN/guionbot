<?php
// --------------- GET ZONE INFO FOR THE TW -----------
// Prepare the SQL query
$query = "SELECT side, zone_name, size, filled, victories, fails,";
$query .= " zoneState, commandMsg";
$query .= " FROM tw_zones";
$query .= " WHERE tw_id=".$tw_id;
//error_log("query = ".$query);
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
                    <?php zone_txt('F2', 'home', $zones, 2, $isMyGuildConfirmed|$isBonusGuild|$isAdmin); ?>
                    <?php zone_txt('F1', 'home', $zones, 2, $isMyGuildConfirmed|$isBonusGuild|$isAdmin); ?>
                    <?php zone_txt('T2', 'home', $zones, 3, $isMyGuildConfirmed|$isBonusGuild|$isAdmin); ?>
                    <?php zone_txt('T1', 'home', $zones, 3, $isMyGuildConfirmed|$isBonusGuild|$isAdmin); ?>
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

    <?php include 'twnavbar.php' ; ?>

<script>
/* event listener for all collapsible buttons */
var coll = document.getElementsByClassName("collapsible");
var i;

for (i = 0; i < coll.length; i++) {
  coll[i].addEventListener("click", function() {
    this.classList.toggle("active");
    var content = this.nextElementSibling;
    if (content.style.display === "block") {
      content.style.display = "none";
    } else {
      content.style.display = "block";
    }
  });
}
/* end of collapsible buttons */
</script>
