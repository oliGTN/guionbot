<?php
// Secure server-side proxy for the Codex Remod API. The API secret never reaches the browser.
ini_set('session.gc_maxlifetime', 3600 * 24 * 7);
session_set_cookie_params([
    'lifetime' => 3600 * 24 * 7,
    'path' => '/',
    'secure' => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
    'httponly' => true,
    'samesite' => 'Lax',
]);
session_start();

header('Cache-Control: no-store, private');
header('X-Content-Type-Options: nosniff');

function codex_json_response($status, $data) {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
    exit;
}

function codex_api_secret() {
    include 'codex_secret.php'; // defines $REMOD_API_SECRET
    $secret = $REMOD_API_SECRET;
    if ($secret === false || trim($secret) === '') {
        $secretFile = '/etc/remod-secret.txt';
        if (is_readable($secretFile)) {
            $secret = file_get_contents($secretFile);
        }
    }
    $secret = trim((string) $secret);
    return $secret === '' ? null : $secret;
}

function codex_api_request($method, $path, $fields = null, $isUpload = false) {
    $secret = codex_api_secret();
    if ($secret === null) {
        return ['ok' => false, 'http' => 503, 'data' => ['detail' => 'Remod API is not configured on this server.']];
    }

    $url = 'https://remod.swgoh-codex.com/api' . $path;
    $ch = curl_init($url);
    $headers = ['Authorization: Bearer ' . $secret, 'Accept: application/json'];
    $options = [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_HTTPHEADER => $headers,
        CURLOPT_CONNECTTIMEOUT => 5,
        CURLOPT_TIMEOUT => 60,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2,
    ];

    if ($method === 'POST') {
        if ($isUpload) {
            $options[CURLOPT_POSTFIELDS] = $fields;
        } elseif ($fields !== null) {
            $headers[] = 'Content-Type: application/json';
            $options[CURLOPT_HTTPHEADER] = $headers;
            $options[CURLOPT_POSTFIELDS] = json_encode($fields);
        }
    }
    curl_setopt_array($ch, $options);
    $body = curl_exec($ch);
    $curlError = curl_error($ch);
    $http = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($body === false) {
        error_log('Codex Remod API connection error: ' . $curlError);
        return ['ok' => false, 'http' => 502, 'data' => ['detail' => 'Unable to contact the remod service. Please try again later.']];
    }
    $data = json_decode($body, true);
    if ($http < 200 || $http >= 300) {
        $detail = is_array($data) ? ($data['detail'] ?? $data['error'] ?? null) : null;
        $message = is_string($detail) && $detail !== '' ? $detail : 'The remod service returned HTTP ' . $http . '.';
        return ['ok' => false, 'http' => $http, 'data' => ['detail' => $message]];
    }
    return ['ok' => true, 'http' => $http, 'data' => $data];
}

function codex_require_user() {
    if (empty($_SESSION['user_id'])) {
        codex_json_response(401, ['error' => 'Please log in to use Codex remod.']);
    }
}

function codex_check_csrf() {
    $token = $_POST['csrf'] ?? '';
    if ($token === '' && isset($_SERVER['CONTENT_TYPE']) && strpos($_SERVER['CONTENT_TYPE'], 'application/json') !== false) {
        $input = json_decode(file_get_contents('php://input'), true);
        $token = is_array($input) ? ($input['csrf'] ?? '') : '';
        if (is_array($input)) {
            $_POST = $input;
        }
    }
    if (!is_string($token) || empty($_SESSION['codex_remod_csrf']) ||
        !hash_equals($_SESSION['codex_remod_csrf'], $token)) {
        codex_json_response(403, ['error' => 'Your session has expired. Refresh the page and try again.']);
    }
}

codex_require_user();
$action = $_POST['action'] ?? '';
if (!is_string($action) || $action === '') {
    codex_json_response(400, ['error' => 'Missing action.']);
}
codex_check_csrf();

if ($action === 'submit') {
    if (isset($_SESSION['codex_remod_job']) && is_array($_SESSION['codex_remod_job']) &&
        in_array($_SESSION['codex_remod_job']['status'] ?? '', ['queued', 'running'], true)) {
        codex_json_response(409, ['error' => 'A remod job is already running in this session.']);
    }

    if (!isset($_FILES['file']) || !is_array($_FILES['file'])) {
        codex_json_response(400, ['error' => 'Please select a restoreMyProgress.json file.']);
    }
    $file = $_FILES['file'];
    if (($file['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
        $uploadErrors = [
            UPLOAD_ERR_INI_SIZE => 'The file exceeds the server upload limit.',
            UPLOAD_ERR_FORM_SIZE => 'The file is too large.',
            UPLOAD_ERR_PARTIAL => 'The upload was incomplete. Please try again.',
            UPLOAD_ERR_NO_FILE => 'Please select a file.',
            UPLOAD_ERR_NO_TMP_DIR => 'The server could not receive the upload.',
            UPLOAD_ERR_CANT_WRITE => 'The server could not save the upload.',
            UPLOAD_ERR_EXTENSION => 'The upload was blocked by server configuration.',
        ];
        codex_json_response(400, ['error' => $uploadErrors[$file['error']] ?? 'File upload failed.']);
    }
    if (!is_uploaded_file($file['tmp_name']) || (int) $file['size'] < 2 || (int) $file['size'] > 30 * 1024 * 1024) {
        codex_json_response(400, ['error' => 'The file must be a valid JSON file no larger than 30 MB.']);
    }

    $originalName = basename((string) ($file['name'] ?? ''));
    if (strtolower(pathinfo($originalName, PATHINFO_EXTENSION)) !== 'json') {
        codex_json_response(400, ['error' => 'Please choose a .json file.']);
    }
    $raw = file_get_contents($file['tmp_name']);
    $progress = json_decode($raw, true);
    if (!is_array($progress) || !isset($progress['profiles'][0]['mods']) ||
        !isset($progress['profiles'][0]['characters']) ||
        !is_array($progress['profiles'][0]['mods']) ||
        !is_array($progress['profiles'][0]['characters'])) {
        codex_json_response(400, ['error' => 'This does not look like a valid restoreMyProgress file: profiles[0].mods and profiles[0].characters are required.']);
    }
    unset($raw, $progress);

    $mode = $_POST['mode'] ?? 'full';
    if (!is_string($mode) || !in_array($mode, ['full', 'light', 'statq'], true)) {
        codex_json_response(400, ['error' => 'Choose full remod, light remod, or StatQ.']);
    }
    $fields = ['file' => new CURLFile($file['tmp_name'], 'application/json', 'restoreMyProgress.json')];

    if ($mode === 'statq') {
        $options = ['mode' => 'statq', 'cible' => 'moyenne', 'tri' => 'alpha', 'lang' => 'fr'];
        foreach ($options as $key => $default) {
            if (!isset($_POST[$key]) || !is_string($_POST[$key])) continue;
            $value = $_POST[$key];
            if ($key === 'cible' && in_array($value, ['moyenne', 'mediane', 'p75'], true)) $options[$key] = $value;
            if ($key === 'tri' && in_array($value, ['alpha', 'points'], true)) $options[$key] = $value;
            if ($key === 'lang' && in_array($value, ['fr', 'en'], true)) $options[$key] = $value;
        }
    } elseif ($mode === 'light') {
        if (!isset($_FILES['cibles']) || !is_array($_FILES['cibles']) || ($_FILES['cibles']['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
            codex_json_response(400, ['error' => 'Light remod requires cibles.json.']);
        }
        $targetFile = $_FILES['cibles'];
        if (!is_uploaded_file($targetFile['tmp_name']) || (int)$targetFile['size'] < 2 || (int)$targetFile['size'] > 262144 ||
            strtolower(pathinfo((string)($targetFile['name'] ?? ''), PATHINFO_EXTENSION)) !== 'json') {
            codex_json_response(400, ['error' => 'cibles.json must be a JSON file no larger than 256 KB.']);
        }
        $targetData = json_decode(file_get_contents($targetFile['tmp_name']), true);
        if (!is_array($targetData) || !isset($targetData['heroes']) || !is_array($targetData['heroes']) || count($targetData['heroes']) < 1 || count($targetData['heroes']) > 40) {
            codex_json_response(400, ['error' => 'cibles.json must contain 1 to 40 heroes.']);
        }
        $seen = [];
        foreach ($targetData['heroes'] as $hero) {
            if (!is_array($hero) || !isset($hero['id']) || !is_string($hero['id']) || trim($hero['id']) === '' ||
                !isset($hero['stats']) || !is_array($hero['stats']) || count($hero['stats']) < 1 || count($hero['stats']) > 12) {
                codex_json_response(400, ['error' => 'Each target needs an id and 1 to 12 positive numeric stats.']);
            }
            $id = strtolower(trim($hero['id']));
            if (isset($seen[$id])) codex_json_response(400, ['error' => 'Duplicate hero in cibles.json: ' . $hero['id']]);
            $seen[$id] = true;
            foreach ($hero['stats'] as $stat => $value) {
                if (!is_string($stat) || $stat === '' || (!is_int($value) && !is_float($value)) || !is_finite((float)$value) || (float)$value <= 0) {
                    codex_json_response(400, ['error' => 'Target stat values must be positive numbers.']);
                }
            }
        }
        $fields['cibles'] = new CURLFile($targetFile['tmp_name'], 'application/json', 'cibles.json');
        $options = ['lang' => 'fr', 'sans_bot' => 'false', 'sans_emprunt' => 'false', 'time_limit' => '8'];
        foreach ($options as $key => $default) {
            if (!isset($_POST[$key]) || !is_string($_POST[$key])) continue;
            $value = $_POST[$key];
            if ($key === 'lang' && in_array($value, ['fr', 'en'], true)) $options[$key] = $value;
            if (in_array($key, ['sans_bot', 'sans_emprunt'], true) && in_array($value, ['true', 'false'], true)) $options[$key] = $value;
            if ($key === 'time_limit' && ctype_digit($value) && (int)$value >= 2 && (int)$value <= 15) $options[$key] = $value;
        }
    } else {
        $options = ['sans_bot' => 'false', 'cible' => 'moyenne', 'time_limit' => '8', 'max_heroes' => '0', 'suppr_vitesse_max' => '10', 'lang' => 'fr'];
        foreach ($options as $key => $default) {
            if (!isset($_POST[$key]) || !is_string($_POST[$key])) continue;
            $value = $_POST[$key];
            if ($key === 'sans_bot' && in_array($value, ['true', 'false'], true)) $options[$key] = $value;
            if ($key === 'cible' && in_array($value, ['moyenne', 'mediane', 'p75'], true)) $options[$key] = $value;
            if ($key === 'lang' && in_array($value, ['fr', 'en'], true)) $options[$key] = $value;
            if ($key === 'time_limit' && ctype_digit($value) && (int)$value >= 2 && (int)$value <= 15) $options[$key] = $value;
            if ($key === 'max_heroes' && ctype_digit($value) && (int)$value <= 500) $options[$key] = $value;
            if ($key === 'suppr_vitesse_max' && ctype_digit($value) && (int)$value <= 30) $options[$key] = $value;
        }
        if (isset($_POST['depart_stats']) && $_POST['depart_stats'] !== '') {
            $value = $_POST['depart_stats'];
            if (!is_string($value) || !ctype_digit($value) || (int)$value > 9999) codex_json_response(400, ['error' => 'depart_stats must be an integer between 0 and 9999.']);
            $options['depart_stats'] = (string)(int)$value;
        }
    }
    foreach ($options as $key => $value) $fields[$key] = $value;

    $result = codex_api_request('POST', '/jobs', $fields, true);
    if (!$result['ok']) {
        $status = $result['http'] === 429 ? 429 : ($result['http'] === 503 ? 503 : 502);
        codex_json_response($status, ['error' => $result['data']['detail']]);
    }
    $job = $result['data'];
    if (empty($job['id']) || !is_string($job['id']) || !preg_match('/^[a-fA-F0-9-]{16,80}$/', $job['id'])) {
        error_log('Codex Remod API returned an invalid job ID.');
        codex_json_response(502, ['error' => 'The remod service returned an invalid job identifier.']);
    }
    $_SESSION['codex_remod_job'] = ['id' => $job['id'], 'status' => $job['status'] ?? 'queued', 'mode' => $mode, 'created_at' => time()];
    codex_json_response(202, [
        'id' => $job['id'],
        'status' => $job['status'] ?? 'queued',
        'queue_position' => $job['queue_position'] ?? null,
    ]);
}

if ($action === 'portraits') {
    $raw = $_POST['characters'] ?? '';
    if (!is_string($raw) || strlen($raw) > 262144) {
        codex_json_response(400, ['error' => 'Invalid portrait request.']);
    }
    $characters = json_decode($raw, true);
    if (!is_array($characters) || count($characters) > 500) {
        codex_json_response(400, ['error' => 'Invalid portrait list.']);
    }
    require_once __DIR__ . '/portrait.php';
    $unitsFile = __DIR__ . '/../DATA/unitsList_dict.json';
    $units = [];
    if (is_readable($unitsFile)) {
        $decodedUnits = json_decode(file_get_contents($unitsFile), true);
        if (is_array($decodedUnits)) {
            $units = $decodedUnits;
        }
    }
    $portraits = [];
    foreach ($characters as $character) {
        if (!is_array($character) || !isset($character['id']) || !is_string($character['id']) ||
            !preg_match('/^[A-Za-z0-9_]+$/', $character['id'])) {
            continue;
        }
        $id = $character['id'];
        $stars = max(0, min(7, (int)($character['stars'] ?? 0)));
        $gear = max(0, min(13, (int)($character['gearLevel'] ?? 0)));
        $relicTier = max(0, min(11, (int)($character['relicTier'] ?? 0)));
        $alignment = (int)($units[$id]['forceAlignment'] ?? 0);
        ob_start();
        display_portrait($id, $alignment, $stars, $gear, $relicTier, 0, 0, false, true);
        $portraits[$id] = ob_get_clean();
    }
    codex_json_response(200, ['portraits' => $portraits]);
}

if ($action === 'status') {
    $job = $_SESSION['codex_remod_job'] ?? null;
    if (!is_array($job) || empty($job['id'])) codex_json_response(404, ['error' => 'No remod job was found in this session.']);
    $result = codex_api_request('GET', '/jobs/' . rawurlencode($job['id']));
    if (!$result['ok']) codex_json_response($result['http'] === 404 ? 404 : 502, ['error' => $result['data']['detail']]);
    $data = is_array($result['data']) ? $result['data'] : [];
    $_SESSION['codex_remod_job']['status'] = $data['status'] ?? 'unknown';
    $safe = [
        'status' => $data['status'] ?? 'unknown',
        'mode' => $_SESSION['codex_remod_job']['mode'] ?? 'full',
        'queue_position' => $data['queue_position'] ?? null,
        'progress' => $data['progress'] ?? null,
        'error' => $data['error'] ?? null,
        // Forward only bounded diagnostic fields if the service exposes them.
        'log' => $data['log'] ?? $data['logs'] ?? null,
        'error_detail' => $data['error_detail'] ?? $data['detail'] ?? null,
        'traceback' => $data['traceback'] ?? null,
        'files' => $data['files'] ?? null,
        'expires_at' => $data['expires_at'] ?? null,
    ];
    codex_json_response(200, $safe);
}

if ($action === 'download') {
    $job = $_SESSION['codex_remod_job'] ?? null;
    if (!is_array($job) || empty($job['id'])) codex_json_response(404, ['error' => 'No remod job was found in this session.']);
    $statusResult = codex_api_request('GET', '/jobs/' . rawurlencode($job['id']));
    if (!$statusResult['ok'] || ($statusResult['data']['status'] ?? '') !== 'done') {
        codex_json_response(409, ['error' => 'The remod calculation is not finished yet.']);
    }
    $secret = codex_api_secret();
    if ($secret === null) codex_json_response(503, ['error' => 'Remod API is not configured on this server.']);
    $ch = curl_init('https://remod.swgoh-codex.com/api/jobs/' . rawurlencode($job['id']) . '/zip');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $secret, 'Accept: application/zip, application/octet-stream'],
        CURLOPT_CONNECTTIMEOUT => 5,
        CURLOPT_TIMEOUT => 120,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2,
    ]);
    $zip = curl_exec($ch);
    $curlError = curl_error($ch);
    $http = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $contentType = curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
    curl_close($ch);
    if ($zip === false || $http < 200 || $http >= 300 || strlen($zip) < 4 || substr($zip, 0, 2) !== "PK") {
        error_log('Codex Remod ZIP download failed: HTTP ' . $http . ' ' . $curlError);
        codex_json_response(502, ['error' => 'Unable to download the result archive. Please try again.']);
    }

    $jobId = $job['id'];
    unset($_SESSION['codex_remod_job']);
    session_write_close();
    header('Content-Type: application/zip');
    header('Content-Disposition: attachment; filename="codex-remod-results.zip"');
    header('Content-Length: ' . strlen($zip));
    header('X-Content-Type-Options: nosniff');
    echo $zip;
    unset($zip);
    // The complete archive is already safely fetched; remove the remote result after serving it.
    $delete = curl_init('https://remod.swgoh-codex.com/api/jobs/' . rawurlencode($jobId));
    curl_setopt_array($delete, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST => 'DELETE',
        CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $secret, 'Accept: application/json'],
        CURLOPT_CONNECTTIMEOUT => 5,
        CURLOPT_TIMEOUT => 10,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2,
    ]);
    curl_exec($delete);
    curl_close($delete);
    exit;
}

if ($action === 'forget') {
    $job = $_SESSION['codex_remod_job'] ?? null;
    if (is_array($job) && !empty($job['id'])) {
        $result = codex_api_request('DELETE', '/jobs/' . rawurlencode($job['id']));
        if (!$result['ok'] && $result['http'] !== 404) {
            codex_json_response(502, ['error' => $result['data']['detail']]);
        }
    }
    unset($_SESSION['codex_remod_job']);
    codex_json_response(200, ['ok' => true]);
}

codex_json_response(400, ['error' => 'Unknown action.']);
