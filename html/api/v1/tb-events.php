<?php
declare(strict_types=1);
require_once dirname(__DIR__) . '/includes/rpc_api_proxy.php';
rpcApiRun('ApiTBEvents', 'tb-events');
