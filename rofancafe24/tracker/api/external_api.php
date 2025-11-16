<?php
/**
 * 외부 API (GCP 서버용)
 * GCP 크롤러가 이 API를 호출하여 사이트 목록 조회 및 결과 저장
 */

// 에러 발생 시에도 JSON 반환하도록 설정
error_reporting(E_ALL);
ini_set('display_errors', 0); // 에러를 화면에 출력하지 않음
ini_set('log_errors', 1); // 에러를 로그에 기록

// 에러 핸들러 설정
set_error_handler(function($errno, $errstr, $errfile, $errline) {
    error_log("PHP Error [$errno]: $errstr in $errfile on line $errline");
    // 500 에러가 아닐 때만 JSON 응답
    if (!headers_sent()) {
        http_response_code(500);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode([
            'success' => false,
            'message' => 'Internal server error: ' . $errstr,
            'error_code' => $errno
        ], JSON_UNESCAPED_UNICODE);
        exit;
    }
});

// 예외 핸들러 설정
set_exception_handler(function($exception) {
    error_log("Uncaught exception: " . $exception->getMessage() . " in " . $exception->getFile() . " on line " . $exception->getLine());
    if (!headers_sent()) {
        http_response_code(500);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode([
            'success' => false,
            'message' => 'Internal server error: ' . $exception->getMessage(),
            'error_type' => get_class($exception)
        ], JSON_UNESCAPED_UNICODE);
        exit;
    }
});

require_once(__DIR__ . '/../config.php');

// API 인증 체크
if (!check_api_auth()) {
    http_response_code(401);
    json_response(false, 'Unauthorized');
}

// 액션 처리
$action = $_GET['action'] ?? '';

switch($action) {
    case 'get_sites':
        get_active_sites();
        break;
        
    case 'save_snapshot':
        save_snapshot();
        break;
        
    case 'save_change':
        save_change();
        break;
        
    case 'update_check_time':
        update_check_time();
        break;
        
    case 'save_attendance':
        save_attendance();
        break;
        
    case 'save_phones':
        save_phones();
        break;
        
    case 'get_latest_snapshots':
        get_latest_snapshots();
        break;
        
    default:
        json_response(false, 'Invalid action');
}

/**
 * 각 사이트의 최신 스냅샷 조회 (크롤러 초기화용)
 */
function get_latest_snapshots() {
    $site_ids = isset($_GET['site_ids']) ? $_GET['site_ids'] : '';
    $site_id_array = [];
    
    if ($site_ids) {
        // 콤마로 구분된 site_id 리스트 파싱
        $site_id_array = array_map('intval', explode(',', $site_ids));
        $site_id_list = implode(',', $site_id_array);
        $where_clause = "WHERE s.site_id IN ($site_id_list)";
    } else {
        // 모든 활성 사이트의 최신 스냅샷
        $where_clause = "WHERE st.is_active = 1";
    }
    
    // 각 사이트별 최신 스냅샷 조회
    $query = "SELECT s.snapshot_id, s.site_id, s.content_hash, s.content_text, s.check_time
              FROM monitor_snapshots s
              LEFT JOIN monitor_sites st ON s.site_id = st.site_id
              $where_clause
              AND s.snapshot_id IN (
                  SELECT MAX(snapshot_id) 
                  FROM monitor_snapshots 
                  WHERE site_id = s.site_id
              )
              ORDER BY s.site_id";
    
    $snapshots = sql_fetch($query);
    
    monitor_log("API: Returned " . count($snapshots) . " latest snapshots", 'info');
    json_response(true, '', $snapshots);
}

/**
 * 활성 사이트 목록 반환
 */
function get_active_sites() {
    $query = "SELECT site_id, site_name, site_url, site_type, target_selector, check_interval, 
                     follow_redirect, last_check_time 
              FROM monitor_sites 
              WHERE is_active = 1 
              ORDER BY site_id";
    
    $sites = sql_fetch($query);
    
    monitor_log("API: Returned " . count($sites) . " active sites", 'info');
    json_response(true, '', $sites);
}

/**
 * 스냅샷 저장
 */
function save_snapshot() {
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    
    if (!$data || !isset($data['site_id'])) {
        json_response(false, 'Invalid data');
    }
    
    $conn = db_connect();
    if (!$conn) {
        json_response(false, 'Database connection failed');
    }
    
    $site_id = intval($data['site_id']);
    $content_hash = mysqli_real_escape_string($conn, $data['content_hash']);
    $content_text = mysqli_real_escape_string($conn, $data['content_text']);
    $full_html = mysqli_real_escape_string($conn, $data['full_html'] ?? '');
    $final_url = mysqli_real_escape_string($conn, $data['final_url']);
    
    // 이전 스냅샷이 있었는지 확인 (초기 감지 로그 생성 여부 판단용)
    // INSERT 전에 확인해야 함 (현재 저장하려는 스냅샷을 제외하고)
    $previous_snapshot_check = sql_query("SELECT COUNT(*) as count FROM monitor_snapshots WHERE site_id = $site_id");
    $previous_count = ($previous_snapshot_check ? intval($previous_snapshot_check['count']) : 0);
    
    // 이미 초기 감지 로그가 있는지 확인
    $initial_log_check = sql_query("SELECT change_id FROM monitor_changes WHERE site_id = $site_id AND change_type = 'initial' LIMIT 1");
    $has_initial_log = ($initial_log_check !== false);
    
    // 이전 스냅샷이 없으면 초기 감지 (has_previous_snapshot = false)
    // 이전 스냅샷이 있지만 초기 로그가 없으면 초기 감지 (has_previous_snapshot = false)
    // 이전 스냅샷이 있고 초기 로그도 있으면 일반 변화 (has_previous_snapshot = true)
    $has_previous_snapshot = ($previous_count > 0) && $has_initial_log;
    
    // 상세 로깅
    monitor_log("API save_snapshot: site_id=$site_id, previous_count=$previous_count, has_initial_log=" . ($has_initial_log ? 'yes' : 'no') . ", has_previous_snapshot=" . ($has_previous_snapshot ? 'yes' : 'no'), 'info');
    
    // 스냅샷 저장 전 로그
    monitor_log("API save_snapshot: Attempting to save snapshot for site_id $site_id, hash: " . substr($content_hash, 0, 16) . "...", 'info');
    monitor_log("API save_snapshot: Content text length: " . strlen($content_text) . " bytes", 'info');
    monitor_log("API save_snapshot: Full HTML length: " . strlen($full_html) . " bytes", 'info');
    
    $query = "INSERT INTO monitor_snapshots 
              (site_id, content_hash, content_text, full_html, final_url, check_time)
              VALUES 
              ($site_id, '$content_hash', '$content_text', '$full_html', '$final_url', NOW())";
    
    monitor_log("API save_snapshot: Executing INSERT query (length: " . strlen($query) . " bytes)", 'info');
    
    $result = sql_exec($query);
    monitor_log("API save_snapshot: sql_exec returned: " . ($result ? 'true' : 'false'), 'info');
    
    if ($result) {
        $snapshot_id = sql_insert_id();
        monitor_log("API save_snapshot: sql_insert_id returned: $snapshot_id", 'info');
        
        if ($snapshot_id > 0) {
            // 실제로 DB에 저장되었는지 확인
            $verify = sql_query("SELECT snapshot_id, content_hash FROM monitor_snapshots WHERE snapshot_id = $snapshot_id LIMIT 1");
            if ($verify) {
                monitor_log("API: Snapshot saved for site_id $site_id (snapshot_id: $snapshot_id, hash: " . substr($verify['content_hash'], 0, 16) . "..., has_previous: " . ($has_previous_snapshot ? 'yes' : 'no') . ", previous_count: $previous_count, has_initial_log: " . ($has_initial_log ? 'yes' : 'no') . ") - VERIFIED", 'info');
                json_response(true, 'Snapshot saved', [
                    'snapshot_id' => $snapshot_id,
                    'has_previous_snapshot' => $has_previous_snapshot
                ]);
            } else {
                monitor_log("API save_snapshot: INSERT succeeded but snapshot_id $snapshot_id not found in DB", 'error');
                json_response(false, 'Snapshot saved but not found in database');
            }
        } else {
            monitor_log("API save_snapshot: INSERT succeeded but snapshot_id is 0 for site_id $site_id", 'error');
            json_response(false, 'Failed to get snapshot_id');
        }
    } else {
        $conn = db_connect();
        $error = $conn ? mysqli_error($conn) : 'Unknown error';
        $errno = $conn ? mysqli_errno($conn) : 0;
        monitor_log("API save_snapshot: Failed to save snapshot. SQL Error: $error (Error #$errno)", 'error');
        monitor_log("API save_snapshot: Failed query (first 500 chars): " . substr($query, 0, 500), 'error');
        json_response(false, 'Failed to save snapshot: ' . $error);
    }
}

/**
 * 변화 로그 저장
 */
function save_change() {
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    
    // 디버깅: 받은 데이터 로그
    monitor_log("API save_change called. Raw input: " . substr($input, 0, 500), 'info');
    
    if (!$data || !isset($data['site_id'])) {
        monitor_log("API save_change: Invalid data or missing site_id", 'error');
        json_response(false, 'Invalid data');
    }
    
    $conn = db_connect();
    if (!$conn) {
        monitor_log("API save_change: Database connection failed", 'error');
        json_response(false, 'Database connection failed');
    }
    
    $site_id = intval($data['site_id']);
    // old_snapshot_id가 null이거나 0이면 초기 감지
    $old_snapshot_id = (isset($data['old_snapshot_id']) && $data['old_snapshot_id'] !== null && $data['old_snapshot_id'] !== '') ? intval($data['old_snapshot_id']) : 'NULL';
    $new_snapshot_id = intval($data['new_snapshot_id']);
    $change_type = mysqli_real_escape_string($conn, $data['change_type'] ?? 'modified');
    $old_content = mysqli_real_escape_string($conn, $data['old_content'] ?? '');
    $new_content = mysqli_real_escape_string($conn, $data['new_content'] ?? '');
    $diff_html_raw = $data['diff_html'] ?? '';
    
    // diff_html 길이 확인 및 제한 (LONGTEXT는 최대 4GB이지만, 실제로는 더 작게 제한)
    $diff_html_length = strlen($diff_html_raw);
    monitor_log("API save_change: diff_html length = $diff_html_length bytes", 'info');
    
    // 너무 길면 잘라내기 (50MB 제한으로 증가)
    if ($diff_html_length > 52428800) {
        monitor_log("API save_change: diff_html too long ($diff_html_length bytes), truncating to 50MB", 'warning');
        $diff_html_raw = substr($diff_html_raw, 0, 52428800) . '<br><div style="color: red;">[내용이 너무 길어 일부가 잘렸습니다. 총 ' . number_format($diff_html_length) . ' 바이트]</div>';
    }
    
    // mysqli_real_escape_string이 실패할 수 있으므로 try-catch 추가
    try {
        $diff_html = mysqli_real_escape_string($conn, $diff_html_raw);
        if ($diff_html === false) {
            $error = mysqli_error($conn);
            monitor_log("API save_change: mysqli_real_escape_string failed for diff_html: $error", 'error');
            json_response(false, 'Failed to escape diff_html: ' . $error);
        }
    } catch (Exception $e) {
        monitor_log("API save_change: Exception escaping diff_html: " . $e->getMessage(), 'error');
        json_response(false, 'Exception escaping diff_html: ' . $e->getMessage());
    }
    
    // 디버깅: 파싱된 데이터 로그
    monitor_log("API save_change: site_id=$site_id, old_snapshot_id=$old_snapshot_id, new_snapshot_id=$new_snapshot_id, change_type=$change_type, diff_html_length=$diff_html_length", 'info');
    
    // 중복 체크 1: 같은 new_snapshot_id로 이미 저장된 변화가 있는지 확인 (초기 감지는 제외)
    if ($change_type != 'initial') {
        monitor_log("API save_change: Checking duplicate for non-initial change (snapshot_id: $new_snapshot_id)", 'info');
        $duplicate_check = sql_query("SELECT change_id FROM monitor_changes WHERE new_snapshot_id = $new_snapshot_id LIMIT 1");
        if ($duplicate_check) {
            monitor_log("API: Duplicate change skipped for site_id $site_id (snapshot_id: $new_snapshot_id)", 'info');
            json_response(true, 'Change already logged', ['change_id' => $duplicate_check['change_id']]);
            return;
        }
    } else {
        monitor_log("API save_change: Initial change type detected, skipping duplicate check 1", 'info');
    }
    
    // 중복 체크 2: 같은 사이트에서 최근 10초 내에 같은 snapshot_id로 저장된 변화가 있는지 확인
    // (너무 짧은 시간 내 같은 snapshot_id로 여러 번 저장되는 것만 방지)
    // 초기 감지 로그는 항상 저장되어야 하므로 이 체크를 건너뜀
    if ($change_type != 'initial') {
        monitor_log("API save_change: Checking recent duplicate for non-initial change", 'info');
        $recent_check = sql_query("SELECT change_id, new_snapshot_id FROM monitor_changes 
                                    WHERE site_id = $site_id 
                                    AND new_snapshot_id = $new_snapshot_id
                                    AND detected_at > DATE_SUB(NOW(), INTERVAL 10 SECOND)
                                    ORDER BY detected_at DESC
                                    LIMIT 1");
        if ($recent_check) {
            // 같은 snapshot_id로 최근 10초 내에 이미 저장됨
            monitor_log("API: Recent duplicate snapshot skipped for site_id $site_id (recent change_id: " . $recent_check['change_id'] . ")", 'info');
            json_response(true, 'Recent duplicate snapshot skipped', ['change_id' => $recent_check['change_id']]);
            return;
        }
    } else {
        monitor_log("API save_change: Initial change type detected, skipping recent duplicate check", 'info');
    }
    
    $query = "INSERT INTO monitor_changes 
              (site_id, old_snapshot_id, new_snapshot_id, change_type, old_content, new_content, diff_html, detected_at)
              VALUES 
              ($site_id, $old_snapshot_id, $new_snapshot_id, '$change_type', '$old_content', '$new_content', '$diff_html', NOW())";
    
    monitor_log("API save_change: Executing INSERT query for site_id $site_id, change_type $change_type", 'info');
    monitor_log("API save_change: Query length = " . strlen($query) . " bytes", 'info');
    
    $result = sql_exec($query);
    monitor_log("API save_change: sql_exec returned: " . ($result ? 'true' : 'false'), 'info');
    
    if ($result) {
        $change_id = sql_insert_id();
        monitor_log("API save_change: sql_insert_id returned: $change_id", 'info');
        
        if ($change_id > 0) {
            // 실제로 DB에 저장되었는지 확인
            $verify = sql_query("SELECT change_id, change_type, is_read FROM monitor_changes WHERE change_id = $change_id LIMIT 1");
            if ($verify) {
                monitor_log("API: Change detected for site_id $site_id (change_id: $change_id, change_type: $change_type, is_read: " . $verify['is_read'] . ") - SUCCESS (verified in DB)", 'info');
                json_response(true, 'Change logged', ['change_id' => $change_id]);
            } else {
                monitor_log("API save_change: INSERT succeeded but change_id $change_id not found in DB", 'error');
                json_response(false, 'Change saved but not found in database');
            }
        } else {
            monitor_log("API save_change: INSERT succeeded but change_id is 0 for site_id $site_id", 'error');
            json_response(false, 'Failed to get change_id');
        }
    } else {
        $conn = db_connect();
        $error = $conn ? mysqli_error($conn) : 'Unknown error';
        monitor_log("API save_change: Failed to log change. SQL Error: $error", 'error');
        monitor_log("API save_change: Failed query was: " . substr($query, 0, 500), 'error');
        // SQL 에러 상세 정보
        if ($conn) {
            $errno = mysqli_errno($conn);
            monitor_log("API save_change: MySQL Error Number: $errno", 'error');
        }
        json_response(false, 'Failed to log change: ' . $error);
    }
}

/**
 * 마지막 체크 시간 업데이트
 */
function update_check_time() {
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    
    if (!$data || !isset($data['site_id'])) {
        json_response(false, 'Invalid data');
    }
    
    $site_id = intval($data['site_id']);
    
    $query = "UPDATE monitor_sites SET last_check_time = NOW() WHERE site_id = $site_id";
    
    if (sql_exec($query)) {
        json_response(true, 'Check time updated');
    } else {
        json_response(false, 'Failed to update check time');
    }
}

/**
 * 출근부 데이터 저장
 */
function save_attendance() {
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    
    if (!$data || !isset($data['site_id']) || !isset($data['attendance_records'])) {
        json_response(false, 'Invalid data');
    }
    
    $conn = db_connect();
    if (!$conn) {
        json_response(false, 'Database connection failed');
    }
    
    $site_id = intval($data['site_id']);
    $attendance_date = $data['attendance_date'] ?? date('Y-m-d');
    $snapshot_id = isset($data['snapshot_id']) ? intval($data['snapshot_id']) : 'NULL';
    $attendance_records = $data['attendance_records'];
    
    $saved_count = 0;
    $attendance_date_escaped = mysqli_real_escape_string($conn, $attendance_date);
    
    foreach ($attendance_records as $record) {
        $staff_name = mysqli_real_escape_string($conn, $record['name'] ?? '');
        $work_times = mysqli_real_escape_string($conn, $record['times'] ?? '');
        $raw_content = mysqli_real_escape_string($conn, $record['raw'] ?? '');
        
        if (empty($staff_name)) continue;
        
        // 중복 체크 후 INSERT 또는 UPDATE
        $query = "INSERT INTO staff_attendance 
                  (site_id, attendance_date, staff_name, work_times, raw_content, snapshot_id, detected_at)
                  VALUES 
                  ($site_id, '$attendance_date_escaped', '$staff_name', '$work_times', '$raw_content', $snapshot_id, NOW())
                  ON DUPLICATE KEY UPDATE 
                  work_times = '$work_times',
                  raw_content = '$raw_content',
                  snapshot_id = $snapshot_id,
                  detected_at = NOW()";
        
        if (sql_exec($query)) {
            $saved_count++;
        }
    }
    
    monitor_log("API: Saved $saved_count attendance records for site_id $site_id on $attendance_date", 'info');
    json_response(true, "Saved $saved_count records", ['count' => $saved_count]);
}

/**
 * 전화번호 저장
 */
function save_phones() {
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    
    if (!$data || !isset($data['site_id']) || !isset($data['phone_data'])) {
        json_response(false, 'Invalid data');
    }
    
    $conn = db_connect();
    if (!$conn) {
        json_response(false, 'Database connection failed');
    }
    
    $site_id = intval($data['site_id']);
    $phone_data = $data['phone_data'];
    
    $saved_count = 0;
    
    foreach ($phone_data as $item) {
        $staff_name = mysqli_real_escape_string($conn, $item['staff_name'] ?? '알 수 없음');
        $phone_number = mysqli_real_escape_string($conn, $item['phone_number'] ?? '');
        
        if (empty($phone_number)) continue;
        
        // 전화번호 형식 검증
        if (!preg_match('/^0\d{1,2}-\d{3,4}-\d{4}$/', $phone_number)) {
            continue;
        }
        
        // 중복 체크 후 INSERT 또는 UPDATE
        $query = "INSERT INTO staff_phones 
                  (site_id, staff_name, phone_number, extracted_at, updated_at)
                  VALUES 
                  ($site_id, '$staff_name', '$phone_number', NOW(), NOW())
                  ON DUPLICATE KEY UPDATE 
                  phone_number = '$phone_number',
                  updated_at = NOW()";
        
        if (sql_exec($query)) {
            $saved_count++;
        }
    }
    
    monitor_log("API: Saved $saved_count phone numbers for site_id $site_id", 'info');
    json_response(true, "Saved $saved_count phone numbers", ['count' => $saved_count]);
}
?>


