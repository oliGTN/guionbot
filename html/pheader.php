<h2>
    <?php echo h($player['name']); ?>
    <a href="https://swgoh.gg/p/<?php echo rawurlencode($allycode); ?>">
        <img src="IMAGES/LOGOS/swgohgg_logo.png" width="50" alt="swgoh.gg" />
    </a>
</h2>

<div class="card">
    <p style="color:green;display:inline">
        <?php echo $isMyAllycode ? 'This is your account' : ''; ?>
    </p>
    <p style="color:red;display:inline">
        <br/>
        <?php echo $isAdmin ? 'You are logged as an administrator' : ''; ?>
    </p>
</div>

<div class="row player-header mb-10">
    <div class="col s8 m8 l8">
        <div class="card stat player">
            <div class="card-content">
                <div class="card-title">Player current guild</div>
                <div class="stat-detail">
                    <div class="value">
                        <a href="g.php?gid=<?php echo rawurlencode((string) $player['guild_id']); ?>">
                            <?php echo h($player['guild_name']); ?>
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="col s4 m4 l4">
        <div class="card stat player">
            <div class="card-content">
                <div class="card-title">allyCode</div>
                <div class="stat-detail">
                    <div class="value">
                        <?php echo h($allycode); ?>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<?php include 'pnavbar.php'; ?>
