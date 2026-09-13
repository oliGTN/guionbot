<?php
require_once 'security.php';
ini_set('session.gc_maxlifetime', 3600*24*7);
session_set_cookie_params(['lifetime'=>3600*24*7,'path'=>'/','secure'=>true,'httponly'=>true,'samesite'=>'Lax']);
session_start();
require 'guionbotdb.php';
include 'gvariables.php';

$isAdmin = !empty($_SESSION['admin']);
if (!isset($_GET['gid'])) {
    header("Location: index.php");
    exit();
}
$guild_id = get_required_guild_id();
list($isMyGuild, $isMyGuildConfirmed, $isBonusGuild, $isOfficer) = set_session_rights_for_guild($guild_id);
if (isset($_SESSION['guild'])) unset($_SESSION['guild']);
include 'gdata.php';

$valid_columns = ['name', 'gp', 'lastUpdated'];
$sort_column = isset($_GET['sort']) && is_string($_GET['sort']) && in_array($_GET['sort'], $valid_columns, true) ? $_GET['sort'] : 'name';
$sort_order = isset($_GET['order']) && is_string($_GET['order']) && strtolower($_GET['order']) === 'desc' ? 'DESC' : 'ASC';
$next_order = $sort_order === 'ASC' ? 'desc' : 'asc';

try {
    $stmt = $conn_guionbot->prepare("SELECT name, playerId, allyCode, char_gp+ship_gp AS gp, lastUpdated FROM players WHERE guildId = :guild_id ORDER BY $sort_column $sort_order");
    $stmt->execute([':guild_id' => $guild_id]);
    $players = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    error_log('Error fetching player data: '.$e->getMessage());
    $players = [];
}
?>
<!DOCTYPE html>
<html>
<head>
    <title>GuiOn bot for SWGOH</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="basic.css"><link rel="stylesheet" href="tables.css"><link rel="stylesheet" href="navbar.css"><link rel="stylesheet" href="main.1.008.css">
</head>
<body>
<div class="site-container"><div class="site-pusher">
<?php include 'navbar.php'; ?>
<div class="site-content"><div class="container">
<?php include 'gheader.php'; ?>
<h3>Player List</h3>
<div class="card"><table><thead><tr>
<th>#</th>
<th class="<?php echo $sort_column === 'name' ? 'active-sort' : ''; ?>"><a href="g.php?gid=<?php echo rawurlencode($guild_id); ?>&sort=name&order=<?php echo $next_order; ?>">Name</a></th>
<th>allyCode</th>
<th class="<?php echo $sort_column === 'gp' ? 'active-sort' : ''; ?>"><a href="g.php?gid=<?php echo rawurlencode($guild_id); ?>&sort=gp&order=<?php echo $next_order; ?>">GP</a></th>
<th class="<?php echo $sort_column === 'lastUpdated' ? 'active-sort' : ''; ?>"><a href="g.php?gid=<?php echo rawurlencode($guild_id); ?>&sort=lastUpdated&order=<?php echo $next_order; ?>">Last Updated</a></th>
</tr></thead><tbody>
<?php if (!empty($players)) { $i_player=1; if (!isset($_SESSION['allyCodes'])) $_SESSION['allyCodes']=[]; foreach ($players as $player) {
$allyCode_display = substr($player['allyCode'],0,3).'-'.substr($player['allyCode'],3,3).'-'.substr($player['allyCode'],6,3);
$isMyallyCode = in_array((int)$player['allyCode'], array_keys($_SESSION['allyCodes']), true);
$line_color = $isMyallyCode ? 'lightgray' : '';
echo "<tr style='background-color:".h($line_color)."'>";
echo '<td>'.h($i_player).'</td>';
echo "<td><a href='p.php?ac=".rawurlencode((string)$player['allyCode'])."'>".h($player['name']).'</a></td>';
echo '<td>'.h($allyCode_display).'</td>';
echo '<td style="text-align:right" class="hide-on-large-only">'.h(round($player['gp']/1000000,1)).'M</td>';
echo '<td style="text-align:right" class="hide-on-med-and-down">'.h(number_format($player['gp'],0,'.',' ')).'</td>';
echo '<td>'.h($player['lastUpdated']).'</td></tr>';
$i_player++; }} else { echo '<tr><td colspan="5">No players found.</td></tr>'; } ?>
</tbody></table></div>
</div></div><div class="site-cache" id="site-cache"></div></div></div>
</body><?php include 'sitefooter.php'; ?></html>
