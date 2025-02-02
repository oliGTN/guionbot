<!-- Navigation Bar -->
<div class="navbar">
    <a href="index.php" class="<?php echo (   substr($_SERVER['REQUEST_URI'], 0, strlen('/index.php'))=='/index.php'
                                           || $_SERVER['REQUEST_URI']=='/')? 'active' : ''; ?>">Home</a>
    <?php if (!isset($_SESSION['user_id'])): ?>
        <a href="init-oauth.php">Login</a>
    <?php else: ?>
        <div class="dropdown">
            <button class="dropbtn <?php echo (substr($_SERVER['REQUEST_URI'], 0, strlen('/dashboard.php'))=='/dashboard.php')? 'active' : ''; ?>">My Account
                <i class="fa fa-caret-down"></i>
            </button>
            <div class="dropdown-content">
                <a href="dashboard.php">My account</a>
                <a href="logout.php">Logout</a>
            </div>
        </div>
        
    <?php endif; ?>
</div>
