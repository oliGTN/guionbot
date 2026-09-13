<?php
require_once 'security.php';
session_set_cookie_params(['lifetime'=>3600*24*7,'path'=>'/','secure'=>true,'httponly'=>true,'samesite'=>'Lax']);
session_start();
require 'guionbotdb.php';
header('Content-Type: application/json; charset=utf-8');
if (!isset($_SESSION['user_id'])) { http_response_code(401); echo json_encode(['err_code'=>1,'err_txt'=>'You need to be logged to use this page']); exit(); }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); echo json_encode(['err_code'=>1,'err_txt'=>'POST required']); exit(); }
$body = json_decode(file_get_contents('php://input'), true);
if (!is_array($body) || ($body['request_type'] ?? '') !== 'guild_roster') { http_response_code(400); echo json_encode(['err_code'=>1,'err_txt'=>'Malformed request']); exit(); }
$guild_id = $body['guild_id'] ?? null;
$units_list = $body['units_list'] ?? null;
if (!is_string($guild_id) || !preg_match('/^[A-Za-z0-9_-]{1,22}$/',$guild_id) || !is_array($units_list) || count($units_list) < 1 || count($units_list) > 100) { http_response_code(400); echo json_encode(['err_code'=>1,'err_txt'=>'Invalid request']); exit(); }
$unit_ids=[];
foreach ($units_list as $unit) {
    if (!is_array($unit) || !isset($unit['unit_id']) || (!is_int($unit['unit_id']) && !(is_string($unit['unit_id']) && preg_match('/^\d+$/',$unit['unit_id'])))) { http_response_code(400); echo json_encode(['err_code'=>1,'err_txt'=>'Invalid unit list']); exit(); }
    $unit_id=(int)$unit['unit_id'];
    if ($unit_id < 1 || $unit_id > 100000000) { http_response_code(400); echo json_encode(['err_code'=>1,'err_txt'=>'Invalid unit list']); exit(); }
    $unit_ids[]=$unit_id;
}
$unit_ids=array_values(array_unique($unit_ids));
$placeholders=implode(',',array_fill(0,count($unit_ids),'?'));
try {
    $sql="SELECT name, defId, rarity, CASE WHEN combatType=2 THEN null ELSE gear END AS gear, CASE WHEN combatType=2 THEN null ELSE greatest(0,relic_currentTier-2) END AS relic FROM players LEFT JOIN roster ON players.allyCode=roster.allyCode WHERE guildId=? AND defId IN ($placeholders) ORDER BY name";
    $stmt=$conn_guionbot->prepare($sql);
    $stmt->execute(array_merge([$guild_id],$unit_ids));
    $roster=$stmt->fetchAll(PDO::FETCH_ASSOC);
} catch(PDOException $e) {
    error_log('Roster request DB error: '.$e->getMessage()); http_response_code(500); echo json_encode(['err_code'=>1,'err_txt'=>'Database error']); exit();
}
echo json_encode(['err_code'=>0,'err_txt'=>'','roster'=>$roster]);
?>
