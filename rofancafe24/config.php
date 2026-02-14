<?php
// 웹 모니터링 시스템 설정 파일 (카페24용)

// 세션 시작
if (session_status() == PHP_SESSION_NONE) {
    session_start();
}

// 타임존 설정
date_default_timezone_set('Asia/Seoul');

// 카페24 데이터베이스 설정
// ⚠️ 아래 정보를 카페24 DB 정보로 수정하세요
define('DB_HOST', 'localhost');  // 또는 카페24 제공 DB 호스트
define('DB_USER', 'rofan');      // DB 사용자명
define('DB_PASS', 'wlsfkaus1@');  // DB 비밀번호 (수정 필요)
define('DB_NAME', 'rofan');      // DB 이름

// API 인증 토큰 (GCP 서버와 통신용)
// ⚠️ 보안을 위해 반드시 변경하세요!
// GCP_CRAWLER.py의 API_TOKEN과 동일하게 설정해야 합니다!
define('API_TOKEN', 'rofan-tracker-token-2025-secure-key');

// GCP 서버 IP (보안 - IP 화이트리스트)
define('ALLOWED_IPS', ['45.120.69.179', '127.0.0.1']);

// 디렉토리 설정
define('BASE_PATH', __DIR__);
define('LOG_PATH', BASE_PATH . '/logs');
define('CACHE_PATH', BASE_PATH . '/cache');

// 디렉토리 생성
if (!is_dir(LOG_PATH)) {
    @mkdir(LOG_PATH, 0755, true);
}
if (!is_dir(CACHE_PATH)) {
    @mkdir(CACHE_PATH, 0755, true);
}

// 데이터베이스 연결
function db_connect() {
    static $conn = null;
    
    if ($conn === null) {
        $conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS, DB_NAME);
        
        if (!$conn) {
            error_log("DB Connection failed: " . mysqli_connect_error());
            return false;
        }
        
        mysqli_set_charset($conn, "utf8mb4");
    }
    
    return $conn;
}

// SQL 쿼리 실행 (단일 결과)
function sql_query($query) {
    $conn = db_connect();
    if (!$conn) return false;
    
    $result = mysqli_query($conn, $query);
    if (!$result) {
        error_log("SQL Error: " . mysqli_error($conn));
        return false;
    }
    
    if (mysqli_num_rows($result) > 0) {
        return mysqli_fetch_assoc($result);
    }
    
    return false;
}

// SQL 쿼리 실행 (여러 결과)
function sql_fetch($query) {
    $conn = db_connect();
    if (!$conn) return [];
    
    $result = mysqli_query($conn, $query);
    if (!$result) {
        error_log("SQL Error: " . mysqli_error($conn));
        return [];
    }
    
    $rows = [];
    while ($row = mysqli_fetch_assoc($result)) {
        $rows[] = $row;
    }
    
    return $rows;
}

// SQL 실행 (INSERT, UPDATE, DELETE)
function sql_exec($query) {
    $conn = db_connect();
    if (!$conn) {
        if (function_exists('monitor_log')) {
            monitor_log("sql_exec: Database connection failed", 'error');
        }
        return false;
    }
    
    $result = mysqli_query($conn, $query);
    if (!$result) {
        $error = mysqli_error($conn);
        error_log("SQL Error: " . $error);
        if (function_exists('monitor_log')) {
            monitor_log("sql_exec: SQL Error - " . $error, 'error');
            monitor_log("sql_exec: Failed query (first 500 chars): " . substr($query, 0, 500), 'error');
        }
        return false;
    }
    
    return true;
}

// INSERT ID 가져오기
function sql_insert_id() {
    $conn = db_connect();
    if (!$conn) return 0;
    return mysqli_insert_id($conn);
}

// 영향받은 행 수
function sql_affected_rows() {
    $conn = db_connect();
    if (!$conn) return 0;
    return mysqli_affected_rows($conn);
}

// 로그 함수
function monitor_log($message, $type = 'info') {
    $log_file = LOG_PATH . '/monitor_' . date('Y-m-d') . '.log';
    $timestamp = date('Y-m-d H:i:s');
    $log_message = "[$timestamp] [$type] $message" . PHP_EOL;
    @file_put_contents($log_file, $log_message, FILE_APPEND);
}

// JSON 응답 함수
function json_response($success, $message = '', $data = null) {
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode([
        'success' => $success,
        'message' => $message,
        'data' => $data
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

// API 인증 체크
function check_api_auth() {
    // IP 체크
    $client_ip = $_SERVER['REMOTE_ADDR'] ?? '';
    if (!in_array($client_ip, ALLOWED_IPS)) {
        monitor_log("Unauthorized IP: $client_ip", 'warning');
        return false;
    }
    
    // 토큰 체크
    $headers = getallheaders();
    $auth_header = $headers['Authorization'] ?? '';
    
    if ($auth_header !== 'Bearer ' . API_TOKEN) {
        monitor_log("Invalid API token from IP: $client_ip", 'warning');
        return false;
    }
    
    return true;
}

// 접근 권한 체크 (관리자 페이지용)
function check_admin_access() {
    // 여기에 로그인 체크 로직 추가 가능
    // 간단한 HTTP Basic Auth 예시:
    /*
    if (!isset($_SERVER['PHP_AUTH_USER']) || 
        $_SERVER['PHP_AUTH_USER'] !== 'admin' || 
        $_SERVER['PHP_AUTH_PW'] !== 'your_password') {
        header('WWW-Authenticate: Basic realm="Monitor Admin"');
        header('HTTP/1.0 401 Unauthorized');
        die('Access Denied');
    }
    */
    return true;
}
?>


