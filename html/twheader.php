<?php
// --------------- GET ZONE INFO FOR THE TW -----------

$query = "SELECT side, zone_name, size, filled, victories, fails, zoneState, commandMsg
          FROM tw_zones
          WHERE tw_id = :tw_id";

try {
    $stmt = $conn_guionbot->prepare($query);
    $stmt->execute([':tw_id' => $tw_id]);
    $zone_list = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    error_log("Error fetching zone data: " . $e->getMessage());
    $zone_list = [];
}

// Reorganize by side then zone.
$zones = [];
foreach ($zone_list as $zone) {
    $zones[$zone['side']][$zone['zone_name']] = $zone;
}

if (!function_exists('zone_txt')) {
    function zone_txt($zone_name, $side, $zones, $rowspan, $can_show_zone_data, $with_links = true) {
        $zone = $zones[$side][$zone_name] ?? null;

        if (!$zone) {
            $zone_color = $side === 'home' ? 'dodgerblue' : 'red';
            $crossed = '';
            $border_style = '3px solid white';
        } elseif ($zone['zoneState'] === 'ZONECOMPLETE') {
            $zone_color = $side === 'home' ? 'darkblue' : 'darkred';
            $crossed = 'background-image: linear-gradient(to bottom right, transparent calc(50% - 1px), black, transparent calc(50% + 1px));';
            $border_style = '3px solid white';
        } elseif (
            ($can_show_zone_data && $zone['filled'] < $zone['size'])
            || $zone['zoneState'] === 'ZONELOCKED'
        ) {
            $zone_color = $side === 'home' ? 'lightblue' : 'pink';
            $crossed = '';
            $border_style = '3px solid white';
        } else {
            $zone_color = $side === 'home' ? 'dodgerblue' : 'red';
            $crossed = '';
            $border_style = '3px solid white';
        }

        if ($zone && $zone['zoneState'] === 'ZONEOPEN') {
            $border_style = '5px solid yellow';
        }

        $onclick = '';
        if ($with_links) {
            $side_zone_name = substr($side, 0, 1) . $zone_name;
            $onclick = ' onclick="openZone(event, \'' . $side . '\', \'' . $side_zone_name . '\')"';
        }

        echo '<td width="25" rowspan="' . (int) $rowspan . '"'
            . $onclick
            . ' style="background-color:' . htmlspecialchars($zone_color, ENT_QUOTES, 'UTF-8')
            . ';' . $crossed . 'border:' . $border_style . '">';

        echo '<b>' . htmlspecialchars($zone_name, ENT_QUOTES, 'UTF-8') . '</b><br/>';

        if (!$zone) {
            echo '0/0';
        } elseif ($can_show_zone_data) {
            echo (int) $zone['filled'] - (int) $zone['victories'];
            echo '/' . (int) $zone['size'];
        } elseif ($zone['zoneState'] === 'ZONELOCKED') {
            echo '?/' . (int) $zone['size'];
        } else {
            echo (int) $zone['filled'] - (int) $zone['victories'];
            echo '/' . (int) $zone['size'];
        }

        echo '</td>';
    }
}

if (!function_exists('render_tw_map')) {
    function render_tw_map($tw, $zones, $can_show_zone_data, $with_links = true) {
        ?>
        <!-- Overview of zones -->
        <div class="row">
            <div class="col s12">
                <div class="col s6">
                    <div class="card">
                        <h3><?php echo htmlspecialchars($tw['homeScore'], ENT_QUOTES, 'UTF-8'); ?>/<small><?php echo htmlspecialchars($tw['homePotentialScore'], ENT_QUOTES, 'UTF-8'); ?></small></h3>
                        <table height="200" width="200" style="table-layout:fixed;width:200px;height:200px;background-color:dodgerblue;color:white">
                            <tr height="33">
                                <?php zone_txt('F2', 'home', $zones, 2, $can_show_zone_data, $with_links); ?>
                                <?php zone_txt('F1', 'home', $zones, 2, $can_show_zone_data, $with_links); ?>
                                <?php zone_txt('T2', 'home', $zones, 3, $can_show_zone_data, $with_links); ?>
                                <?php zone_txt('T1', 'home', $zones, 3, $can_show_zone_data, $with_links); ?>
                            </tr>
                            <tr height="33"></tr>
                            <tr height="33">
                                <?php zone_txt('T4', 'home', $zones, 2, $can_show_zone_data, $with_links); ?>
                                <?php zone_txt('T3', 'home', $zones, 2, $can_show_zone_data, $with_links); ?>
                            </tr>
                            <tr height="33">
                                <?php zone_txt('B2', 'home', $zones, 3, $can_show_zone_data, $with_links); ?>
                                <?php zone_txt('B1', 'home', $zones, 3, $can_show_zone_data, $with_links); ?>
                            </tr>
                            <tr height="33">
                                <?php zone_txt('B4', 'home', $zones, 3, $can_show_zone_data, $with_links); ?>
                                <?php zone_txt('B3', 'home', $zones, 3, $can_show_zone_data, $with_links); ?>
                            </tr>
                            <tr height="33"></tr>
                        </table>
                    </div>
                </div>

                <div class="col s6">
                    <div class="card">
                        <h3><?php echo htmlspecialchars($tw['awayScore'], ENT_QUOTES, 'UTF-8'); ?>/<small><?php echo htmlspecialchars($tw['awayPotentialScore'], ENT_QUOTES, 'UTF-8'); ?></small></h3>
                        <table height="200" width="200" style="table-layout:fixed;width:200px;height:200px;background-color:red;color:white">
                            <tr height="33">
                                <?php zone_txt('T1', 'away', $zones, 3, $can_show_zone_data, $with_links); ?>
                                <?php zone_txt('T2', 'away', $zones, 3, $can_show_zone_data, $with_links); ?>
                                <?php zone_txt('F1', 'away', $zones, 2, $can_show_zone_data, $with_links); ?>
                                <?php zone_txt('F2', 'away', $zones, 2, $can_show_zone_data, $with_links); ?>
                            </tr>
                            <tr height="33"></tr>
                            <tr height="33">
                                <?php zone_txt('T3', 'away', $zones, 2, $can_show_zone_data, $with_links); ?>
                                <?php zone_txt('T4', 'away', $zones, 2, $can_show_zone_data, $with_links); ?>
                            </tr>
                            <tr height="33">
                                <?php zone_txt('B1', 'away', $zones, 3, $can_show_zone_data, $with_links); ?>
                                <?php zone_txt('B2', 'away', $zones, 3, $can_show_zone_data, $with_links); ?>
                            </tr>
                            <tr height="33">
                                <?php zone_txt('B3', 'away', $zones, 2, $can_show_zone_data, $with_links); ?>
                                <?php zone_txt('B4', 'away', $zones, 2, $can_show_zone_data, $with_links); ?>
                            </tr>
                            <tr height="33"></tr>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        <?php
    }
}

if (empty($twheader_map_only)) {
?>
    <h2>TW for <a href="/g.php?gid=<?php echo (int) $tw['guild_id']; ?>"><?php echo htmlspecialchars($tw['guild_name'], ENT_QUOTES, 'UTF-8'); ?></a>
        vs <a href="/g.php?gid=<?php echo (int) $tw['away_guild_id']; ?>"><?php echo htmlspecialchars($tw['away_guild_name'], ENT_QUOTES, 'UTF-8'); ?></a>
    </h2>

    <div class="card">
        <p style="color:green;display:inline"><?php echo ($isMyGuild ? 'You are ' . ($isOfficer ? 'an officer ' : '') . 'in this guild' : ''); ?>
            <small><?php echo ($isMyGuild && !$isMyGuildConfirmed ? ' (to confirm your identity and access restricted guild data, please run <i>go.register &lt;allyCode&gt; confirm</i> in a Direct Message to <a href="https://discordapp.com/users/752969647233564703/">the bot</a>)' : ''); ?></small>
        </p>

        <p style="color:green;display:inline"><?php echo ($isBonusGuild ? 'You are a guest in this guild' : ''); ?></p>
        <p style="color:red;display:inline"><br/><?php echo ($isAdmin ? 'You are logged as an administrator' : ''); ?></p>
    </div>

    <div><br/><?php echo '(last update on ' . htmlspecialchars($tw['lastUpdated'], ENT_QUOTES, 'UTF-8') . ')'; ?></div>
<?php
}

render_tw_map(
    $tw,
    $zones,
    ($isMyGuildConfirmed ?? false) || ($isBonusGuild ?? false) || ($isAdmin ?? false) || ($isGuildMateConfirmed ?? false),
    empty($twheader_map_only)
);

if (empty($twheader_map_only)) {
    include 'twnavbar.php';
?>
<script>
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
</script>
<?php
}
?>
