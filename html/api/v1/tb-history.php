<?php
declare(strict_types=1);

/**
 * Read-only Rise of the Empire TB history API.
 * Authentication/configuration and PDO are shared with the existing TB APIs.
 * Round windows are six consecutive 24-hour periods from tb_history.start_date.
 */
function tbHistoryRespond(int $status, array $payload, array $headers = []): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, private');
    header('X-Content-Type-Options: nosniff');
    foreach ($headers as $name => $value) header($name . ': ' . $value);
    echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

$isHttps = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== '' && strtolower((string)$_SERVER['HTTPS']) !== 'off';
if (!$isHttps) tbHistoryRespond(403, ['success'=>false, 'error'=>'HTTPS required']);
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') tbHistoryRespond(405, ['success'=>false, 'error'=>'Method not allowed'], ['Allow'=>'POST']);
if ((int)($_SERVER['CONTENT_LENGTH'] ?? 0) > 4096) tbHistoryRespond(413, ['success'=>false, 'error'=>'Request body too large']);

$raw = file_get_contents('php://input');
$request = [];
if ($raw === false) tbHistoryRespond(400, ['success'=>false, 'error'=>'Invalid request body']);
if (trim($raw) !== '') {
    $decoded = json_decode($raw, true);
    if (json_last_error() !== JSON_ERROR_NONE || !is_array($decoded) || (array_keys($decoded) !== [] && array_is_list($decoded))) {
        tbHistoryRespond(400, ['success'=>false, 'error'=>'Request body must be a JSON object']);
    }
    $request = $decoded;
}
$allowed = ['tb_id','tb_ids','blocks'];
if (array_diff(array_keys($request), $allowed)) tbHistoryRespond(400, ['success'=>false, 'error'=>'Unknown request field']);
if (isset($request['tb_id']) && (!is_int($request['tb_id']) || $request['tb_id'] < 1)) tbHistoryRespond(400, ['success'=>false, 'error'=>'tb_id must be a positive integer']);
if (isset($request['tb_ids']) && (!is_array($request['tb_ids']) || count($request['tb_ids']) < 1 || count($request['tb_ids']) > 100)) tbHistoryRespond(400, ['success'=>false, 'error'=>'tb_ids must contain 1 to 100 IDs']);
if (isset($request['tb_id'], $request['tb_ids'])) tbHistoryRespond(400, ['success'=>false, 'error'=>'Use tb_id or tb_ids, not both']);
if (isset($request['tb_ids'])) foreach ($request['tb_ids'] as $id) if (!is_int($id) || $id < 1) tbHistoryRespond(400, ['success'=>false, 'error'=>'Every tb_ids value must be a positive integer']);
$validBlocks = ['zones','players','player_zones','strikes','covert'];
$blocks = $request['blocks'] ?? ['zones','players'];
if (!is_array($blocks) || count($blocks) > count($validBlocks)) tbHistoryRespond(400, ['success'=>false, 'error'=>'blocks must be an array']);
foreach ($blocks as $block) if (!is_string($block) || !in_array($block,$validBlocks,true)) tbHistoryRespond(400, ['success'=>false, 'error'=>'Unknown block']);
$blocks = array_values(array_unique($blocks));

$configPath = '/home/pi/GuionBot/SERVER_SECRETS/web_api.php';
if (!is_file($configPath) || !is_readable($configPath)) tbHistoryRespond(503,['success'=>false,'error'=>'Service unavailable']);
$config = require $configPath;
if (!is_array($config) || empty($config['api_key']) || empty($config['guild_id']) || !is_string($config['api_key']) || !is_string($config['guild_id'])) tbHistoryRespond(503,['success'=>false,'error'=>'Service unavailable']);
$headersIn = function_exists('getallheaders') ? getallheaders() : [];
$authorization = '';
foreach ($headersIn as $name=>$value) if (strcasecmp((string)$name,'Authorization')===0) { $authorization=is_string($value)?trim($value):''; break; }
if ($authorization==='' ) $authorization=trim((string)($_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? ''));
if (!preg_match('/^Bearer\s+([^\s]+)$/i',$authorization,$m) || !hash_equals($config['api_key'],$m[1])) tbHistoryRespond(401,['success'=>false,'error'=>'Unauthorized'],['WWW-Authenticate'=>'Bearer']);

// Match the existing API's shared-key rolling limits: 5/minute, 1,000/day.
$rateFile = rtrim(sys_get_temp_dir(), DIRECTORY_SEPARATOR).DIRECTORY_SEPARATOR.'guionbot_tb_history_rate_'.hash('sha256',$config['api_key']).'.json';
$fh=@fopen($rateFile,'c+');
if ($fh===false || !flock($fh,LOCK_EX)) { if(is_resource($fh)) fclose($fh); tbHistoryRespond(503,['success'=>false,'error'=>'Service unavailable']); }
$now=time(); $state=json_decode((string)stream_get_contents($fh),true); $times=[];
foreach (($state['timestamps'] ?? []) as $t) if(is_int($t) && $t>$now-86400 && $t<=$now) $times[]=$t;
$recent=array_values(array_filter($times,static function($t)use($now){return $t>$now-60;}));
$rateError=count($times)>=1000 ? 'Daily request limit exceeded' : (count($recent)>=5 ? 'Rate limit exceeded' : null);
$retry=1;
if($rateError!==null){ sort($rateError==='Daily request limit exceeded'?$times:$recent,SORT_NUMERIC); $list=$rateError==='Daily request limit exceeded'?$times:$recent; $retry=max(1,$list[0]+($rateError==='Daily request limit exceeded'?86400:60)-$now+1); }
else $times[]=$now;
rewind($fh); if($rateError===null){ftruncate($fh,0);fwrite($fh,json_encode(['timestamps'=>$times]));fflush($fh);} flock($fh,LOCK_UN);fclose($fh);
if($rateError!==null) tbHistoryRespond(429,['success'=>false,'error'=>$rateError],['Retry-After'=>(string)$retry,'RateLimit-Limit'=>'5','RateLimit-Remaining'=>'0']);

try {
    require_once dirname(__DIR__,2).'/guionbotdb.php';
    if(!isset($conn_guionbot) || !($conn_guionbot instanceof PDO)) throw new RuntimeException('PDO unavailable');
    $where='h.guild_id=:guild_id'; $params=[':guild_id'=>$config['guild_id']];
    if(isset($request['tb_id'])) { $where.=' AND h.id=:tb_id'; $params[':tb_id']=$request['tb_id']; }
    elseif(isset($request['tb_ids'])) { $marks=[]; foreach($request['tb_ids'] as $i=>$id){$key=':tb'.$i;$marks[]=$key;$params[$key]=$id;} $where.=' AND h.id IN ('.implode(',',$marks).')'; }
    $st=$conn_guionbot->prepare('SELECT h.id,h.tb_id,h.tb_name,h.start_date,h.lastUpdated,h.current_round,h.stars_final FROM tb_history h WHERE '.$where.' ORDER BY h.start_date DESC LIMIT 501');
    $st->execute($params); $history=$st->fetchAll(PDO::FETCH_ASSOC);
    if(count($history)>500) tbHistoryRespond(503,['success'=>false,'error'=>'Result exceeds the API TB limit']);
    $tbs=[];
    foreach($history as $h){
        $start=$h['start_date']!==null ? new DateTimeImmutable($h['start_date'],new DateTimeZone('UTC')) : null;
        $rounds=[];
        for($r=1;$r<=6;$r++){
            $rs=$start ? $start->modify('+'.(($r-1)*24).' hours') : null;
            $re=$rs ? $rs->modify('+24 hours') : null;
            $rounds[]=['round'=>$r,'start'=>$rs?$rs->format('Y-m-d\TH:i:s\Z'):null,'end'=>$re?$re->format('Y-m-d\TH:i:s\Z'):null];
        }
        $tb=['tb_id'=>(int)$h['id'],'game_tb_id'=>$h['tb_id'],'name'=>$h['tb_name'],'status'=>$h['stars_final']===null?'current':'finished','started'=>$start?$start->format('Y-m-d\TH:i:s\Z'):null,'ended'=>($h['stars_final']!==null && $start)?$start->modify('+144 hours')->format('Y-m-d\TH:i:s\Z'):null,'rounds'=>$rounds,'members'=>null,'events_complete'=>null];
        if(in_array('zones',$blocks,true)){
            $zs=$conn_guionbot->prepare('SELECT zone_id,zone_name,zone_phase,round,score_step1,score_step2,score_step3,score,is_bonus,cmdMsg,cmdCmd,recon1_filled,recon2_filled,recon3_filled,recon4_filled,recon5_filled,recon6_filled FROM tb_zones WHERE tb_id=:id ORDER BY round,zone_id');
            $zs->execute([':id'=>$h['id']]); $zones=[];
            foreach($zs->fetchAll(PDO::FETCH_ASSOC) as $z){
                $zones[]=['zone_id'=>$z['zone_id'],'name'=>$z['zone_name'],'alignment'=>null,'is_bonus'=>(bool)$z['is_bonus'],'thresholds'=>[$z['score_step1']===null?null:(int)$z['score_step1'],$z['score_step2']===null?null:(int)$z['score_step2'],$z['score_step3']===null?null:(int)$z['score_step3']],'rounds'=>[['round'=>(int)$z['round'],'score_end'=>$z['score']===null?null:(int)$z['score'],'score_raw'=>null,'stars_end'=>($z['score_step3']!==null && $z['score']!==null && $z['score']>=$z['score_step3'])?3:(($z['score_step2']!==null && $z['score']>=$z['score_step2'])?2:(($z['score_step1']!==null && $z['score']>=$z['score_step1'])?1:0)),'strategy'=>$z['cmdMsg'],'strategy_code'=>$z['cmdCmd'],'recon_filled'=>array_map('intval',[$z['recon1_filled'],$z['recon2_filled'],$z['recon3_filled'],$z['recon4_filled'],$z['recon5_filled'],$z['recon6_filled']]),'platoon_points'=>null]]];
            }
            $tb['zones']=$zones;
        }
        if(in_array('players',$blocks,true)) $tb['players']=[]; // Player roster/stat rows are added once their persisted source is confirmed.
        foreach(['player_zones','strikes','covert'] as $optional) if(in_array($optional,$blocks,true)) $tb[$optional]=[];
        $tbs[]=$tb;
    }
} catch(PDOException $e){error_log('TB history API query failed; SQLSTATE='.(string)$e->getCode());tbHistoryRespond(500,['success'=>false,'error'=>'Unable to retrieve TB history']);}
catch(Throwable $e){error_log('TB history API setup failed; exception='.get_class($e));tbHistoryRespond(500,['success'=>false,'error'=>'Unable to retrieve TB history']);}

tbHistoryRespond(200,['success'=>true,'generated'=>gmdate('Y-m-d\TH:i:s\Z'),'tbs'=>$tbs],['RateLimit-Limit'=>'5','RateLimit-Remaining'=>(string)max(0,4-count($recent))]);
