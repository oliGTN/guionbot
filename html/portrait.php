<?php

function display_portrait($char_id, $alignment, $rarity, $gear, $relic, $zeta_count, $omicron_count, $is_ship, $unit_name, $small = false) {
    $unit_name = htmlspecialchars($unit_name, ENT_QUOTES, 'UTF-8');

    // unitRelicTier is stored using the SWGOH tier numbering:
    // 2 = no relic, 3 = R1, ..., 11 = R9.
    // Keep support for callers that already pass a 0-9 relic level.
    $relic_level = 0;
    if (is_numeric($relic)) {
        $relic = (int) $relic;
        if ($relic >= 3) {
            $relic_level = $relic - 2;
        } else if ($relic > 0) {
            $relic_level = $relic;
        }
    }

    $small_class = $small ? ' portrait-small' : '';

    echo "<div class='portrait-container".$small_class."' title='".$unit_name."'>";
    echo "<div class='portrait-art'>";
    echo "<img class='character-avatar' src='IMAGES/CHARACTERS/".$char_id.".png' alt='".$char_id."'>";

    // Gear frame
    if ($gear == 13) {
        echo "<div class='gear-frame-container'>";
        if ($alignment == 3) {
            echo "<div class='gear-frame-sprite-red'></div>";
        } else if ($alignment == 2) {
            echo "<div class='gear-frame-sprite-blue'></div>";
        } else {
            echo "<div class='gear-frame-sprite-white'></div>";
        }
        echo "</div>";
    } else if ($gear > 0) {
        echo "<img class='gear-frame' src='IMAGES/PORTRAIT_FRAME/g".$gear."-frame.png' alt=''>";
    }

    // Display the gear tier when the character is not reliced.
    // For relic characters the relic badge replaces this badge.
    if (!$is_ship) {
        if ($relic_level > 0) {
            if ($alignment == 3) {
                $relic_badge_class = ' relic-badge-red';
            } else if ($alignment == 2) {
                $relic_badge_class = ' relic-badge-blue';
            } else {
                $relic_badge_class = ' relic-badge-white';
            }
            echo "<div class='relic-badge".$relic_badge_class."'>";
            echo "<span>R".$relic_level."</span>";
            echo "</div>";
        } else if ($gear > 0) {
            echo "<div class='gear-level-badge'>G".(int)$gear."</div>";
        }
    }

    if (is_numeric($zeta_count) && (int)$zeta_count > 0) {
        echo "<div class='zeta-badge'>";
        echo "<img src='IMAGES/PORTRAIT_FRAME/tex.skill_zeta_glow.png' alt='Zetas'>";
        echo "<span>".(int)$zeta_count."</span>";
        echo "</div>";
    }

    if (is_numeric($omicron_count) && (int)$omicron_count > 0) {
        echo "<div class='omicron-badge'>";
        echo "<img src='IMAGES/PORTRAIT_FRAME/tex.skill_omicron.png' alt='Omicrons'>";
        echo "<span>".(int)$omicron_count."</span>";
        echo "</div>";
    }

    echo "<div class='star-rating'>";
    if ($rarity > 0) {
        foreach (range(1, min(7, (int) $rarity)) as $value) {
            echo "<img class='star' src='IMAGES/PORTRAIT_FRAME/star.png' alt='Active Star'>";
        }
    }
    if ($rarity < 7) {
        foreach (range(max(1, (int) $rarity + 1), 7) as $value) {
            echo "<img class='star' src='IMAGES/PORTRAIT_FRAME/star-inactive.png' alt='Inactive Star'>";
        }
    }
    echo "</div>";
    echo "</div>";
    echo "<div class='portrait-name'>".$unit_name."</div>";
    echo "</div>";
}


function load_datacron_icons($conn) {
    $icons = [];

    try {
        $stmt = $conn->prepare(
            "SELECT targetRule, scopeIcon FROM datacron_icons"
        );
        $stmt->execute();

        foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $icon) {
            $target_rule = strtolower(trim((string) $icon['targetRule']));
            $scope_icon = trim((string) $icon['scopeIcon']);

            if ($target_rule !== '' && $scope_icon !== '') {
                $icons[$target_rule] = $scope_icon;
            }
        }
    } catch (PDOException $e) {
        error_log("Error loading datacron icons: " . $e->getMessage());
    }

    return $icons;
}

function load_categories() {
    $dict_categories_file = __DIR__ . '/../DATA/categoryList_dict.json';
    if (is_readable($dict_categories_file)) {
        $dict_categories = json_decode(file_get_contents($dict_categories_file), true);
    }
    return $dict_categories;
}
function load_loc($loc_name) {
    $loc_file = __DIR__ . '/../DATA/'.$loc_name.'.json';
    if (is_readable($loc_file)) {
        $loc = json_decode(file_get_contents($loc_file), true);
    }
    return $loc;
}
function display_datacron($datacron, $icons, $categories, $abilities, $loc, $small = false) {
    $escape = function ($value) {
        return htmlspecialchars((string) $value, ENT_QUOTES, 'UTF-8');
    };
    if (empty($datacron) || empty($datacron['setId'])) {
        return;
    }

    $target_rule = '';
    $img_title = '';
    foreach ([3, 6, 9, 12, 15] as $level) {
        $value = trim((string) ($datacron['level_' . $level] ?? ''));

        if ($value !== '') {
            $parts = explode(':', $value, 2);
            $abilityId = $parts[0];
            $targetRule = $parts[1];

            $target_rule = trim($targetRule ?? '');

            $target_name_cat = $categories[$targetRule];
            $target_name = $target_name_cat['descKey'];
            $ability_loc_name = $abilities[$abilityId]['descKey'];
            $ability_text_empty = $loc[$ability_loc_name];
            $ability_text = str_replace('{0}', $target_name, $ability_text_empty);
            $img_title = $img_title.'&#013;&#013;'.$ability_text;
        }
    }

    $remainder = ((int) $datacron['setId']) % 4;
    $suffix = [1 => 'a', 2 => 'b', 3 => 'c', 0 => 'd'][$remainder];
    $background = 'IMAGES/DATACRONS/tex.datacron_' . $suffix . '.png';

    $icon = null;
    $icon_type = null;

    if ($target_rule !== '') {
        $icon_value = $icons[strtolower($target_rule)] ?? null;

        if ($icon_value !== null && $icon_value !== '') {
            $icon_type = stripos($icon_value, 'IMAGES/CHARACTERS/') !== false
                ? 'character'
                : 'datacron';

            $icon = preg_match('#^https?://#i', $icon_value)
                ? $icon_value
                : (
                    strpos($icon_value, 'IMAGES/') === 0
                        ? $icon_value
                        : 'IMAGES/DATACRONS/' . ltrim($icon_value, '/')
                );

            if (!preg_match('#^https?://#i', $icon) &&
                !preg_match('/\\.[a-z0-9]+$/i', $icon)) {
                $icon .= '.png';
            }
        }
    }

    $dot_count = 0;
    foreach ([3, 6, 9, 12, 15] as $level) {
        if (trim((string) ($datacron['level_' . $level] ?? '')) !== '') {
            $dot_count++;
        }
    }

    $size_class = $small ? ' datacron-display-small' : '';
    echo "<div class='datacron-display" . $size_class . "'>";
    echo "<div class='datacron-art'>";
    echo "<img class='datacron-background' src='" . $escape($background) . "' alt='' title=\"".$img_title."\">";

    if ($icon !== null) {
        echo "<div class='datacron-level-icon " . $escape($icon_type) . "'>";
        echo "<img src='" . $escape($icon) . "' alt=''>";
        echo "</div>";
    }

    echo "<div class='datacron-dots'>";

    for ($i = 0; $i < $dot_count; $i++) {
        echo "<span class='datacron-dot'></span>";
    }

    echo "</div>";
    echo "</div>";
    echo "</div>";
}

?>
