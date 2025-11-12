<!-- Navigation Bar -->
<div class="navbar">
    <a href='/g.php?gid=<?php echo $guild_id; ?>' class="<?php echo (   substr($_SERVER['REQUEST_URI'], 0, strlen('/g.php'))=='/g.php'
                                           || $_SERVER['REQUEST_URI']=='/')? 'active' : ''; ?>">Players</a>
    <a href='/tbs.php?gid=<?php echo $guild_id; ?>' class="<?php echo (   substr($_SERVER['REQUEST_URI'], 0, strlen('/tbs.php'))=='/tbs.php'
                                           || $_SERVER['REQUEST_URI']=='/')? 'active' : ''; ?>">TB</a>
    <a href='/tws.php?gid=<?php echo $guild_id; ?>' class="<?php echo (   substr($_SERVER['REQUEST_URI'], 0, strlen('/tws.php'))=='/tws.php'
                                           || $_SERVER['REQUEST_URI']=='/')? 'active' : ''; ?>">TW</a>
    <a href='/groster.php?gid=<?php echo $guild_id; ?>' class="<?php echo (   substr($_SERVER['REQUEST_URI'], 0, strlen('/groster.php'))=='/groster.php'
                                           || $_SERVER['REQUEST_URI']=='/')? 'active' : ''; ?>">Roster</a>
</div>
