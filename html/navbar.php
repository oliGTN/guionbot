<!-- Navigation Bar -->
<header class="main">
<div class="container">
    <a href="#" class="icon" id="header__icon" onclick="document.body.classList.toggle('with--sidebar')">&#x2630;</a>
<nav class="menu pushed">
<ul class="nav inverse">
    <li class="<?php echo (   substr($_SERVER['REQUEST_URI'], 0, strlen('/index.php'))=='/index.php' || $_SERVER['REQUEST_URI']=='/')? 'active' : ''; ?>">
        <a href="index.php">Home</a>
    </li>
    <li class="drop">Events
        <ul>
            <li><a href="twall.php">All TWs</a></li>
            <li><a href="tball.php">All TBs</a></li>
        </ul>
    </li>
    <?php if (!isset($_SESSION['user_id'])): ?>
        <li>
            <a href="init-oauth.php">Login</a>
        </li>
    <?php else: ?>
    <li class="drop <?php echo (substr($_SERVER['REQUEST_URI'], 0, strlen('/dashboard.php'))=='/dashboard.php')? 'active' : ''; ?>"><?php echo $_SESSION['user_name']; ?>
        <ul>
            <li><a href="dashboard.php">My account</a></li>
            <li><a href="logout.php">Logout</a></li>
        </ul>
    </li>
    <?php endif; ?>
    <?php if (isset($_SESSION['sql_select']) && $_SESSION['sql_select']): ?>
        <li class="<?php echo (   substr($_SERVER['REQUEST_URI'], 0, strlen('/sqlquery.php'))=='/sqlquery.php' || $_SERVER['REQUEST_URI']=='/')? 'active' : ''; ?>">
            <a href="sqlquery.php">DB consult</a>
        </li>
    <?php endif; ?>
</ul>
</nav>
</div>
</header>
