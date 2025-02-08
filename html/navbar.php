<!-- Navigation Bar -->
<header class="main">
<div class="container">
    <a href="#" class="icon" id="header__icon" onclick="document.body.classList.toggle('with--sidebar')">&#x2630;</a>
<nav class="menu pushed">
<ul class="nav inverse">
    <li class="<?php echo (   substr($_SERVER['REQUEST_URI'], 0, strlen('/index.php'))=='/index.php'
                                           || $_SERVER['REQUEST_URI']=='/')? 'active' : ''; ?>">
        <a href="index.php">Home</a>
    </li>
    <?php if (!isset($_SESSION['user_id'])): ?>
        <li>
        <a href="init-oauth.php">Login</a>
        </li>
    <?php else: ?>
    <li class="drop <?php echo (substr($_SERVER['REQUEST_URI'], 0, strlen('/dashboard.php'))=='/dashboard.php')? 'active' : ''; ?>">My Account
        <ul>
            <li><a href="dashboard.php">My account</a></li>
            <li><a href="logout.php">Logout</a></li>
        </ul>
    </li>
    <?php endif; ?>
</ul>
</nav>
</div>
</header>
