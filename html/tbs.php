<?php
require_once 'security.php';
ini_set('session.gc_maxlifetime', 3600*24*7);
session_set_cookie_params(['lifetime'=>3600*24*7,'path'=>'/','secure'=>true,'httponly'=>true,'samesite'=>'Lax']);
session_start();
require 'guionbotdb.php';
include 'gvariables.php';
$isAdmin = !empty($_SESSION['admin']);
if (!isset($_GET['gid'])) { header("Location: index.php"); exit(); }
$guild_id = get_required_guild_id();
if (!isset($_SESSION['guild']) || ($_SESSION['guild']['id'] ?? null) !== $guild_id) include 'gdata.php';
$guild = $_SESSION['guild'];
list($isMyGuild, $isMyGuildConfirmed, $isBonusGuild, $isOfficer) = set_session_rights_for_guild($guild_id);
try {
    $stmt = $conn_guionbot->prepare("SELECT tb_history.id, tb_name, start_date, lastUpdated, MAX(tb_zones.round) AS max_round, CASE WHEN ISNULL(stars_final) THEN sum(CASE WHEN score>=score_step3 THEN CASE WHEN SUBSTRING(tb_zones.zone_name,-1,1)='b' THEN 1 ELSE 3 END WHEN score>=score_step2 THEN CASE WHEN SUBSTRING(tb_zones.zone_name,-1,1)='b' THEN 0 ELSE 2 END WHEN score>=score_step1 THEN CASE WHEN SUBSTRING(tb_zones.zone_name,-1,1)='b' THEN 0 ELSE 1 END ELSE 0 END) ELSE stars_final END AS stars FROM tb_history LEFT JOIN tb_zones ON tb_zones.tb_id=tb_history.id JOIN (SELECT tb_history.id AS id, zone_name, max(round) AS max_round FROM tb_zones JOIN tb_history ON tb_zones.tb_id=tb_history.id WHERE tb_history.guild_id=:guild_id_sub GROUP BY tb_history.id, zone_name) T ON T.id=tb_history.id AND T.zone_name=tb_zones.zone_name AND T.max_round=tb_zones.round WHERE tb_history.guild_id=:guild_id GROUP BY tb_history.id ORDER BY start_date DESC");
    $stmt->execute([':guild_id_sub'=>$guild_id, ':guild_id'=>$guild_id]);
    $tbs = $stmt->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    error_log('Error fetching TB history data: '.$e->getMessage());
    $tbs = [];
}
?>
<!DOCTYPE html><html><head><title>GuiOn bot for SWGOH</title><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="basic.css"><link rel="stylesheet" href="tables.css"><link rel="stylesheet" href="navbar.css"><link rel="stylesheet" href="main.1.008.css"></head><body>
<div class="site-container"><div class="site-pusher"><?php include 'navbar.php'; ?><div class="site-content"><div class="container"><?php include 'gheader.php'; ?><div class="card"><table><thead><tr><th>Start date</th><th>Type</th><th>Result</th></tr></thead><tbody>
<?php if (!empty($tbs)) { foreach ($tbs as $tb) { echo '<tr><td>'.h($tb['start_date']).'</td><td><a href="/tb.php?id='.rawurlencode((string)$tb['id']).'&round='.rawurlencode((string)$tb['max_round']).'">'.h($tb['tb_name']).'</a></td><td>'.h($tb['stars']).'&#11088;</td></tr>'; }} else { echo '<tr><td colspan="3">No TB found.</td></tr>'; } ?>
</tbody></table></div></div></div><div class="site-cache" id="site-cache"></div></div></div></body><?php include 'sitefooter.php'; ?></html>
