<!-- Navigation Bar -->
<div class="navbar">
<a href='/tb.php?id=<?php echo $tb_id; ?>&round=<?php echo $round; ?>' class="<?php echo (   substr($_SERVER['REQUEST_URI'], 0, strlen('/tb.php'))=='/tb.php'
                                           || $_SERVER['REQUEST_URI']=='/')? 'active' : ''; ?>">Score</a>
<a href='/tbcmd.php?id=<?php echo $tb_id; ?>&round=<?php echo $round; ?>' class="<?php echo (   substr($_SERVER['REQUEST_URI'], 0, strlen('/tbcmd.php'))=='/tbcmd.php'
                                           || $_SERVER['REQUEST_URI']=='/')? 'active' : ''; ?>">Commands</a>
</div>
