<?php
// --------------- GET ZONE INFO FOR THE TW -----------

if (empty($twheader_use_existing_zones)) {
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
}

// Reorganize by side then zone when twheader fetched the data itself.
if (empty($twheader_use_existing_zones)) {
    $zones = [];
    foreach ($zone_list as $zone) {
        $zones[$zone['side']][$zone['zone_name']] = $zone;
    }
}

if (!function_exists('tw_zone_style')) {
    function tw_zone_style($zone, $side, $can_show_zone_data) {
        if (!$zone) {
            return $side === 'home' ? 'dodgerblue' : 'red';
        }

        if ($zone['zoneState'] === 'ZONECOMPLETE') {
            return $side === 'home' ? 'darkblue' : 'darkred';
        }

        if (
            ($can_show_zone_data && $zone['filled'] < $zone['size'])
            || $zone['zoneState'] === 'ZONELOCKED'
        ) {
            return $side === 'home' ? 'lightblue' : 'pink';
        }

        return $side === 'home' ? 'dodgerblue' : 'red';
    }
}

if (!function_exists('tw_zone_label')) {
    function tw_zone_label($zone_name, $side, $zones, $can_show_zone_data) {
        $zone = $zones[$side][$zone_name] ?? null;

        if (!$zone) {
            return '0/0';
        }

        if ($can_show_zone_data || $zone['zoneState'] !== 'ZONELOCKED') {
            return ((int) $zone['filled'] - (int) $zone['victories']) . '/' . (int) $zone['size'];
        }

        return '?/' . (int) $zone['size'];
    }
}

if (!function_exists('tw_zone_svg')) {
    function tw_zone_svg($zone_name, $side, $zones, $can_show_zone_data, $x, $y, $width, $height, $with_links) {
        $zone = $zones[$side][$zone_name] ?? null;
        $fill = tw_zone_style($zone, $side, $can_show_zone_data);
        $score = tw_zone_label($zone_name, $side, $zones, $can_show_zone_data);

        $onclick = '';
        $cursor = 'default';

        if ($with_links) {
            $side_zone_name = substr($side, 0, 1) . $zone_name;
            $onclick = ' onclick="openZone(event, \'' . htmlspecialchars($side, ENT_QUOTES, 'UTF-8') . '\\', \'' . htmlspecialchars($side_zone_name, ENT_QUOTES, 'UTF-8') . '\\')"';
            $cursor = 'pointer';
        }

        $command = '';
        if ($zone && !empty($zone['commandMsg'])) {
            $command = ' · ' . $zone['commandMsg'];
        }

        $label = $zone_name . $command;
        $font_size = 16;

        echo '<g' . $onclick . ' style="cursor:' . $cursor . '">';
        echo '<rect x="' . $x . '" y="' . $y . '" width="' . $width . '" height="' . $height
            . '" fill="' . htmlspecialchars($fill, ENT_QUOTES, 'UTF-8') . '" stroke="white" stroke-width="3"/>';

        if ($zone && $zone['zoneState'] === 'ZONECOMPLETE') {
            echo '<line x1="' . $x . '" y1="' . $y . '" x2="' . ($x + $width) . '" y2="' . ($y + $height)
                . '" stroke="black" stroke-width="2"/>';
        }

        echo '<text x="' . ($x + $width / 2) . '" y="' . ($y + $height / 2 - 5)
            . '" text-anchor="middle" dominant-baseline="middle" fill="white" font-size="' . $font_size
            . '" font-weight="bold">' . htmlspecialchars($label, ENT_QUOTES, 'UTF-8') . '</text>';

        echo '<text x="' . ($x + $width / 2) . '" y="' . ($y + $height / 2 + 18)
            . '" text-anchor="middle" dominant-baseline="middle" fill="white" font-size="15">'
            . htmlspecialchars($score, ENT_QUOTES, 'UTF-8') . '</text>';

        echo '</g>';
    }
}

if (!function_exists('render_tw_map')) {
    function render_tw_map($tw, $zones, $can_show_zone_data, $with_links = true) {
        if (isset($zones['home']) || isset($zones['away'])) {
            $render_zones = $zones;
        } else {
            $render_zones = [];
            foreach ($zones as $zone) {
                $render_zones[$zone['side']][$zone['zone_name']] = $zone;
            }
        }

        ?>
        <style>
            .tw-map-pair {
                display: flex;
                justify-content: center;
                align-items: flex-start;
                gap: 1rem;
                flex-wrap: wrap;
            }

            .tw-map-card {
                flex: 0 1 323px;
                min-width: 260px;
                text-align: center;
            }

            .tw-map-svg {
                display: block;
                width: 100%;
                max-width: 323px;
                height: auto;
                margin: 0 auto;
            }

            .tw-map-svg text {
                font-family: Arial, sans-serif;
                pointer-events: none;
            }

            @media (max-width: 700px) {
                .tw-map-card {
                    flex-basis: min(323px, 90vw);
                }
            }
        </style>

        <div class="row">
            <div class="col s12">
                <div class="tw-map-pair">
                    <div class="tw-map-card">
                        <h3><?php echo htmlspecialchars($tw['homeScore'], ENT_QUOTES, 'UTF-8'); ?><?php if (isset($tw['homePotentialScore'])): ?>/<small><?php echo htmlspecialchars($tw['homePotentialScore'], ENT_QUOTES, 'UTF-8'); ?><?php endif; ?></small></h3>
                        <svg class="tw-map-svg" viewBox="0 0 400 400" role="img" aria-label="Home Territory War map">
                            <defs>
                                <clipPath id="tw-home-circle-<?php echo (int) $tw['guild_id']; ?>">
                                    <circle cx="200" cy="200" r="198"/>
                                </clipPath>
                            </defs>
                            <g clip-path="url(#tw-home-circle-<?php echo (int) $tw['guild_id']; ?>)">
                                <?php
                                tw_zone_svg('F2', 'home', $render_zones, $can_show_zone_data, 0, 0, 100, 133.333, $with_links);
                                tw_zone_svg('F1', 'home', $render_zones, $can_show_zone_data, 100, 0, 100, 133.333, $with_links);
                                tw_zone_svg('T2', 'home', $render_zones, $can_show_zone_data, 200, 0, 100, 200, $with_links);
                                tw_zone_svg('T1', 'home', $render_zones, $can_show_zone_data, 300, 0, 100, 200, $with_links);
                                tw_zone_svg('T4', 'home', $render_zones, $can_show_zone_data, 0, 133.333, 100, 133.334, $with_links);
                                tw_zone_svg('T3', 'home', $render_zones, $can_show_zone_data, 100, 133.333, 100, 133.334, $with_links);
                                tw_zone_svg('B4', 'home', $render_zones, $can_show_zone_data, 200, 200, 100, 200, $with_links);
                                tw_zone_svg('B3', 'home', $render_zones, $can_show_zone_data, 300, 200, 100, 200, $with_links);
                                tw_zone_svg('B2', 'home', $render_zones, $can_show_zone_data, 0, 266.667, 100, 133.333, $with_links);
                                tw_zone_svg('B1', 'home', $render_zones, $can_show_zone_data, 100, 266.667, 100, 133.333, $with_links);
                                ?>
                            </g>
                            <circle cx="200" cy="200" r="198" fill="none" stroke="white" stroke-width="4"/>
                        </svg>
                    </div>

                    <div class="tw-map-card">
                        <h3><?php echo htmlspecialchars($tw['awayScore'], ENT_QUOTES, 'UTF-8'); ?><?php if (isset($tw['awayPotentialScore'])): ?>/<small><?php echo htmlspecialchars($tw['awayPotentialScore'], ENT_QUOTES, 'UTF-8'); ?><?php endif; ?></small></h3>
                        <svg class="tw-map-svg" viewBox="0 0 400 400" role="img" aria-label="Away Territory War map">
                            <defs>
                                <clipPath id="tw-away-circle-<?php echo (int) $tw['guild_id']; ?>">
                                    <circle cx="200" cy="200" r="198"/>
                                </clipPath>
                            </defs>
                            <g clip-path="url(#tw-away-circle-<?php echo (int) $tw['guild_id']; ?>)">
                                <?php
                                tw_zone_svg('T1', 'away', $render_zones, $can_show_zone_data, 0, 0, 100, 200, $with_links);
                                tw_zone_svg('T2', 'away', $render_zones, $can_show_zone_data, 100, 0, 100, 200, $with_links);
                                tw_zone_svg('F1', 'away', $render_zones, $can_show_zone_data, 200, 0, 100, 133.333, $with_links);
                                tw_zone_svg('F2', 'away', $render_zones, $can_show_zone_data, 300, 0, 100, 133.333, $with_links);
                                tw_zone_svg('T3', 'away', $render_zones, $can_show_zone_data, 0, 200, 100, 200, $with_links);
                                tw_zone_svg('T4', 'away', $render_zones, $can_show_zone_data, 100, 200, 100, 200, $with_links);
                                tw_zone_svg('B1', 'away', $render_zones, $can_show_zone_data, 200, 133.333, 100, 133.334, $with_links);
                                tw_zone_svg('B2', 'away', $render_zones, $can_show_zone_data, 300, 133.333, 100, 133.334, $with_links);
                                tw_zone_svg('B3', 'away', $render_zones, $can_show_zone_data, 200, 266.667, 100, 133.333, $with_links);
                                tw_zone_svg('B4', 'away', $render_zones, $can_show_zone_data, 300, 266.667, 100, 133.333, $with_links);
                                ?>
                            </g>
                            <circle cx="200" cy="200" r="198" fill="none" stroke="white" stroke-width="4"/>
                        </svg>
                    </div>
                </div>
            </div>
        </div>
        <?php
    }
}

if (empty($twheader_map_only)) {
?>
    <h2>TW for <a href="/g.php?gid=<?php echo htmlspecialchars($tw['guild_id']); ?>"><?php echo htmlspecialchars($tw['guild_name'], ENT_QUOTES, 'UTF-8'); ?></a>
        vs <a href="/g.php?gid=<?php echo htmlspecialchars($tw['away_guild_id']); ?>"><?php echo htmlspecialchars($tw['away_guild_name'], ENT_QUOTES, 'UTF-8'); ?></a>
    </h2>

<?php if (empty($twheader_use_existing_zones)) : ?>
    <div class="card">
        <p style="color:green;display:inline"><?php echo ($isMyGuild ? 'You are ' . ($isOfficer ? 'an officer ' : '') . 'in this guild' : ''); ?>
            <small><?php echo ($isMyGuild && !$isMyGuildConfirmed ? ' (to confirm your identity and access restricted guild data, please run <i>go.register &lt;allyCode&gt; confirm</i> in a Direct Message to <a href="https://discordapp.com/users/752969647233564703/">the bot</a>)' : ''); ?></small>
        </p>

        <p style="color:green;display:inline"><?php echo ($isBonusGuild ? 'You are a guest in this guild' : ''); ?></p>
        <p style="color:red;display:inline"><br/><?php echo ($isAdmin ? 'You are logged as an administrator' : ''); ?></p>
    </div>
<?php endif ; ?> <!-- empty($twheader_use_existing_zones -->


    <div><?php echo '(last update on ' . htmlspecialchars($tw['lastUpdated'], ENT_QUOTES, 'UTF-8') . ')'; ?></div>
<?php
}

render_tw_map(
    $tw,
    $zones,
    ($isMyGuildConfirmed ?? false) || ($isBonusGuild ?? false) || ($isAdmin ?? false) || ($isGuildMateConfirmed ?? false),
    empty($twheader_map_only)
);

if (empty($twheader_no_navbar)) {
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
