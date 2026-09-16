<!-- Player navigation Bar -->
<div class="navbar">
    <a href="/p.php?ac=<?php echo rawurlencode((string) $allycode); ?>" class="<?php echo substr($_SERVER['REQUEST_URI'], 0, strlen('/p.php')) == '/p.php' ? 'active' : ''; ?>">Guild history</a>
    <a href="/pmods.php?ac=<?php echo rawurlencode((string) $allycode); ?>" class="<?php echo substr($_SERVER['REQUEST_URI'], 0, strlen('/pmods.php')) == '/pmods.php' ? 'active' : ''; ?>">Mods</a>
</div>
