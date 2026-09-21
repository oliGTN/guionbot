<?php
require_once 'security.php';

ini_set('session.gc_maxlifetime', 3600 * 24 * 7);
session_set_cookie_params([
    'lifetime' => 3600 * 24 * 7,
    'path' => '/',
    'secure' => true,
    'httponly' => true,
    'samesite' => 'Lax',
]);
session_start();

require 'guionbotdb.php';
include 'pvariables.php';

$isAdmin = !empty($_SESSION['admin']);

if (!isset($_GET['ac'])) {
    header('Location: index.php');
    exit();
}

$allycode = get_required_ally_code();
[$isMyAllycode, $isMyAllycodeConfirmed, $isGuildMate, $isGuildMateConfirmed] = set_session_rights_for_allycode($allycode);

include 'pdata.php';

try {
    $stmt = $conn_guionbot->prepare(
        "SELECT
            ge.timestamp,
            ge.guild_id,
            g.name,
            ge.description
        FROM guild_evolutions AS ge
        JOIN players AS p
            ON p.playerId = ge.playerId
        JOIN guilds AS g
            ON g.id = ge.guild_id
        WHERE p.allyCode = :allycode
        ORDER BY ge.timestamp DESC;"
    );
    $stmt->execute([':allycode' => $allycode]);
    $guild_evo = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    error_log('Error fetching player history: ' . $e->getMessage());
    $guild_evo = [];
}
?>
<!DOCTYPE html>
<html>
<head>
    <title>GuiOn bot for SWGOH</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="basic.css">
    <link rel="stylesheet" href="tables.css">
    <link rel="stylesheet" href="navbar.css">
    <link rel="stylesheet" href="main.1.008.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
</head>
<body>
<div class="site-container">
    <div class="site-pusher">
        <?php include 'navbar.php'; ?>

        <div class="site-content">
            <div class="container">
                <?php include 'pheader.php'; ?>

                <h3>Player past guilds</h3>
                <div class="card">
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Guild</th>
                                <th>Description</th>
                            </tr>
                        </thead>
                        <tbody>
                        <?php
                        if (!empty($guild_evo)) {
                            foreach ($guild_evo as $evo) {
                                $isMyGuild = ($evo['guild_id'] == $player['guild_id']);
                                $line_color = $isMyGuild ? 'lightgray' : '';

                                if ($evo['description'] === 'removed') {
                                    $evo_display = 'leaves the guild';
                                } elseif ($evo['description'] === 'added') {
                                    $evo_display = 'joins the guild';
                                } elseif (
                                    substr(
                                        (string) $evo['description'],
                                        0,
                                        strlen('guildMemberLevel changed')
                                    ) === 'guildMemberLevel changed'
                                ) {
                                    $last = substr((string) $evo['description'], -1);
                                    $evo_display = $last === '4'
                                        ? 'role changed to leader'
                                        : ($last === '3'
                                            ? 'role changed to officer'
                                            : 'role changed to member');
                                } else {
                                    $evo_display = $evo['description'];
                                }

                                echo '<tr style="background-color:' . h($line_color) . '">';
                                echo '<td>' . h($evo['timestamp']) . '</td>';
                                echo "<td><a href='g.php?gid="
                                    . rawurlencode((string) $evo['guild_id'])
                                    . "'>"
                                    . h($evo['name'])
                                    . '</a></td>';
                                echo '<td>' . h($evo_display) . '</td></tr>';
                            }
                        } else {
                            echo '<tr><td colspan="3">No guild history found.</td></tr>';
                        }
                        ?>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="site-cache" id="site-cache"></div>
    </div>
</div>
</body>
<?php include 'sitefooter.php'; ?>
</html>
