<?php

function display_portrait($char_id, $alignment, $rarity, $gear, $relic, $zeta_count) {
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

    echo "<div class='portrait-container'>";
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
    if ($relic_level > 0) {
        echo "<div class='relic-badge'>";
        echo "<span>R".$relic_level."</span>";
        echo "</div>";
    } else if ($gear > 0) {
        echo "<div class='gear-level-badge'>G".(int)$gear."</div>";
    }

    // Zeta count, displayed only when at least one zeta is present.
    if (is_numeric($zeta_count) && (int)$zeta_count > 0) {
        echo "<div class='zeta-badge'>";
        echo "<img src='IMAGES/PORTRAIT_FRAME/tex.skill_zeta_glow.png' alt='Zetas'>";
        echo "<span>".(int)$zeta_count."</span>";
        echo "</div>";
    }

    // Star rating
    echo "<div class='star-rating'>";
    foreach (range(1, $rarity) as $value) {
        echo "<img class='star' src='IMAGES/PORTRAIT_FRAME/star.png' alt='Active Star'>";
    }
    if ($rarity < 7) {
        foreach (range($rarity + 1, 7) as $value) {
            echo "<img class='star' src='IMAGES/PORTRAIT_FRAME/star-inactive.png' alt='Inactive Star'>";
        }
    }
    echo "</div>";
    echo "</div>";
}

?>
