<!-- Navigation Bar -->
<div class="navbar">
    <a href='/tw.php?id=<?php echo $tw_id; ?>' class="<?php echo (   substr($_SERVER['REQUEST_URI'], 0, strlen('/tw.php'))=='/tw.php'
                                           || $_SERVER['REQUEST_URI']=='/')? 'active' : ''; ?>">Players</a>
    <a href='/twz.php?id=<?php echo $tw_id; ?>' class="<?php echo (   substr($_SERVER['REQUEST_URI'], 0, strlen('/twz.php'))=='/twz.php'
                                           || $_SERVER['REQUEST_URI']=='/')? 'active' : ''; ?>">Zones</a>
</div>
