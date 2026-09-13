<?php
require 'guionbotdb.php';

function get_round_from_get($tb_id) {
    global $conn_guionbot;
    $tb_id=(int)$tb_id;
    if (!isset($_GET['round'])) {
        try {
            $stmt=$conn_guionbot->prepare('SELECT current_round FROM tb_history WHERE id=:tb_id');
            $stmt->execute([':tb_id'=>$tb_id]);
            $rounds=$stmt->fetchAll(PDO::FETCH_ASSOC);
            if (!$rounds) { header('Location: index.php'); exit(); }
            return (int)$rounds[0]['current_round'];
        } catch(PDOException $e) { error_log('Error fetching TB round: '.$e->getMessage()); return 1; }
    }
    return (isset($_GET['round']) && preg_match('/^[1-9]\d*$/',(string)$_GET['round'])) ? (int)$_GET['round'] : 1;
}
function get_tb_round_score($tb_id,$round) {
    global $conn_guionbot; $tb_id=(int)$tb_id; $round=(int)$round;
    try {
        $stmt=$conn_guionbot->prepare('SELECT sum(score_strikes) AS strikes,sum(score_platoons) AS platoons,sum(score_deployed) AS deployed,availableShipDeploy,availableCharDeploy,availableMixDeploy,remainingShipPlayers,remainingCharPlayers,remainingMixPlayers,deploymentType,totalPlayers FROM tb_player_score JOIN tb_phases ON tb_phases.tb_id=tb_player_score.tb_id AND tb_phases.round=tb_player_score.round WHERE tb_player_score.tb_id=:tb_id AND tb_player_score.round=:round');
        $stmt->execute([':tb_id'=>$tb_id,':round'=>$round]); return $stmt->fetch(PDO::FETCH_ASSOC) ?: [];
    } catch(PDOException $e) { error_log('Error fetching round data: '.$e->getMessage()); return []; }
}
function get_tb_players($tb_id,$round,$sort_column,$sort_order) {
    global $conn_guionbot; $tb_id=(int)$tb_id; $round=(int)$round;
    $allowed=['name'=>'name','allyCode'=>'allyCode','deployed_gp'=>'deployed_gp','gp'=>'tb_player_score.gp','ship_gp'=>'tb_player_score.ship_gp','char_gp'=>'tb_player_score.char_gp','score'=>'score_strikes+score_deployed','strikes'=>'strikes','waves'=>'waves','deployment'=>'deployed_gp/gp'];
    $sort_column=$allowed[$sort_column] ?? 'name'; $sort_order=(strtoupper($sort_order)==='DESC')?'DESC':'ASC';
    try {
        $stmt=$conn_guionbot->prepare('SELECT name,allyCode,deployed_gp,tb_player_score.gp AS gp,tb_player_score.ship_gp AS ship_gp,tb_player_score.char_gp AS char_gp,score_strikes+score_deployed AS score,strikes,waves FROM tb_player_score JOIN players ON players.playerId=tb_player_score.player_id WHERE tb_id=:tb_id AND round=:round ORDER BY '.$sort_column.' '.$sort_order);
        $stmt->execute([':tb_id'=>$tb_id,':round'=>$round]); return $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch(PDOException $e) { error_log('Error fetching player data: '.$e->getMessage()); return []; }
}
function get_tb_from_id($tb_id) {
    global $conn_guionbot; $tb_id=(int)$tb_id;
    try {
        $stmt=$conn_guionbot->prepare('SELECT guild_id,guilds.name AS guild_name,tb_name,start_date,tb_history.lastUpdated,current_round,max(round) AS max_round,tb_zones.tb_id AS tb_id FROM tb_history JOIN tb_zones ON tb_zones.tb_id=tb_history.id JOIN guilds ON guilds.id=tb_history.guild_id WHERE tb_zones.tb_id=:tb_id');
        $stmt->execute([':tb_id'=>$tb_id]); $rows=$stmt->fetchAll(PDO::FETCH_ASSOC); return $rows[0] ?? [];
    } catch(PDOException $e) { error_log('Error fetching TB data: '.$e->getMessage()); return []; }
}
function get_tb_round_zones($tb_id,$round) {
    global $conn_guionbot; $tb_id=(int)$tb_id; $round=(int)$round;
    try {
        $stmt=$conn_guionbot->prepare("SELECT zone_name,zone_id,zone_phase,score_step1,score_step2,score_step3,score,estimated_platoons,estimated_strikes,estimated_deployments,recon1_filled,recon2_filled,recon3_filled,recon4_filled,recon5_filled,recon6_filled,recon_cmdMsg FROM tb_zones WHERE tb_id=:tb_id AND round=:round ORDER BY CASE WHEN INSTR(zone_name,'DS')>0 THEN 0 WHEN INSTR(zone_name,'MS')>0 THEN 1 ELSE 2 END + CASE WHEN is_bonus THEN 0.5 ELSE 0 END");
        $stmt->execute([':tb_id'=>$tb_id,':round'=>$round]); return $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch(PDOException $e) { error_log('Error fetching zone data: '.$e->getMessage()); return []; }
}
function get_tb_round_stars($tb_id,$round) {
    global $conn_guionbot; $tb_id=(int)$tb_id; $round=(int)$round;
    try {
        $stmt=$conn_guionbot->prepare("SELECT sum(CASE WHEN score>=score_step3 THEN CASE WHEN SUBSTRING(tb_zones.zone_name,-1,1)='b' THEN 1 ELSE 3 END WHEN score>=score_step2 THEN CASE WHEN SUBSTRING(tb_zones.zone_name,-1,1)='b' THEN 0 ELSE 2 END WHEN score>=score_step1 THEN CASE WHEN SUBSTRING(tb_zones.zone_name,-1,1)='b' THEN 0 ELSE 1 END ELSE 0 END) AS stars FROM tb_zones JOIN (SELECT tb_zones.tb_id AS tb_id,zone_name,max(round) AS max_round FROM tb_zones JOIN tb_history ON tb_zones.tb_id=tb_history.id WHERE tb_zones.tb_id=:sub_tb_id GROUP BY tb_id,zone_name) T ON T.tb_id=tb_zones.tb_id AND T.zone_name=tb_zones.zone_name AND T.max_round=tb_zones.round WHERE tb_zones.tb_id=:tb_id AND round<=:round");
        $stmt->execute([':sub_tb_id'=>$tb_id,':tb_id'=>$tb_id,':round'=>$round]); $row=$stmt->fetch(PDO::FETCH_ASSOC); return $row['stars'] ?? 0;
    } catch(PDOException $e) { error_log('Error fetching TB stars: '.$e->getMessage()); return 0; }
}
?>
