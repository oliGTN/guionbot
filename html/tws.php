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
include 'gvariables.php';

$isAdmin = !empty($_SESSION['admin']);

if (!isset($_GET['gid'])) {
    header('Location: index.php');
    exit();
}

$guild_id = get_required_guild_id();

if (!isset($_SESSION['guild']) || ($_SESSION['guild']['id'] ?? null) !== $guild_id) {
    include 'gdata.php';
}

$guild = $_SESSION['guild'];
[$isMyGuild, $isMyGuildConfirmed, $isBonusGuild, $isOfficer] = set_session_rights_for_guild($guild_id);

try {
    $stmt = $conn_guionbot->prepare(
        "SELECT tw_history.id, start_date, away_guild_name,
                homeScore, awayScore, lastUpdated
         FROM tw_history
         WHERE guild_id = :guild_id
         ORDER BY start_date DESC"
    );
    $stmt->execute([':guild_id' => $guild_id]);
    $tws = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    error_log('Error fetching TW history data: ' . $e->getMessage());
    $tws = [];
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
                <?php include 'gheader.php'; ?>

                <div class="card">
                    <table>
                        <thead>
                            <tr>
                                <th>Start date</th>
                                <th>Opponent</th>
                                <th>Score</th>
                            </tr>
                        </thead>
                        <tbody>
                        <?php
                        if (!empty($tws)) {
                            foreach ($tws as $tw) {
                                $score_color = $tw['homeScore'] >= $tw['awayScore']
                                    ? 'green'
                                    : 'red';
                                $start_date = explode(' ', (string) $tw['start_date'])[0];

                                echo '<tr>';
                                echo '<td>' . h($start_date) . '</td>';
                                echo '<td><a href="/tw.php?id='
                                    . rawurlencode((string) $tw['id'])
                                    . '">' . h($tw['away_guild_name']) . '</a></td>';
                                echo '<td style="color:' . h($score_color) . '">'
                                    . '<b>'
                                    . h($tw['homeScore'])
                                    . '/'
                                    . h($tw['awayScore'])
                                    . '</b></td>';
                                echo '</tr>';
                            }
                        } else {
                            echo '<tr><td colspan="3">No TW found.</td></tr>';
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
