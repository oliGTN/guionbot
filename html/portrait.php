<?php

function display_portrait($char_id, $alignment, $rarity, $gear, $relic, $zeta_count) {
    echo "<div class='portrait-container'>";
    echo "<img class='character-avatar' src='IMAGES/CHARACTERS/".$char_id.".png' alt='".$char_id."'>";

    // code gor G11
    if ($gear == 13) {
        // code for relic
        echo "<div class='gear-frame-container'>";
        if ($alignment == 3) {
            echo "<div class='gear-frame-sprite-red'></div>";
        } else if ($alignment == 2) {
            echo "<div class='gear-frame-sprite-blue'></div>";
        } else {
            echo "<div class='gear-frame-sprite-white'></div>";
        }
        echo "</div>";
    } else if ($gear >0) {
        echo "<img class='gear-frame' src='IMAGES/PORTRAIT_FRAME/g".$gear."-frame.png' alt=''>";
    }

    echo "<div class='star-rating'>";
    foreach (range(1, $rarity) as $value) {
        echo "<img class='star' src='IMAGES/PORTRAIT_FRAME/star.png' alt='Active Star'>";
    }
    if ($rarity < 7 ) {
        foreach (range($rarity+1, 7) as $value) {
            echo "<img class='star' src='IMAGES/PORTRAIT_FRAME/star-inactive.png' alt='Inactive Star'>";
        }
    }
    echo "</div></div>";
}

?>
