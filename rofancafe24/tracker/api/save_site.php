<?php
require_once(__DIR__ . '/../config.php');
check_admin_access();

// 데이터베이스 연결 확인
$conn = db_connect();
if (!$conn) {
    json_response(false, '데이터베이스 연결에 실패했습니다. config.php의 DB 설정을 확인하세요.');
}

// POST 데이터 받기
$site_id = isset($_POST['site_id']) ? intval($_POST['site_id']) : 0;
$site_name = trim($_POST['site_name'] ?? '');
$site_url = trim($_POST['site_url'] ?? '');
$site_type = trim($_POST['site_type'] ?? 'normal');
$target_selector = trim($_POST['target_selector'] ?? 'body');
$check_interval = intval($_POST['check_interval'] ?? 5);
$is_active = (isset($_POST['is_active']) && ($_POST['is_active'] == '1' || $_POST['is_active'] == 1)) ? 1 : 0;
$follow_redirect = (isset($_POST['follow_redirect']) && ($_POST['follow_redirect'] == '1' || $_POST['follow_redirect'] == 1)) ? 1 : 0;
$enable_notification = (isset($_POST['enable_notification']) && ($_POST['enable_notification'] == '1' || $_POST['enable_notification'] == 1)) ? 1 : 0;

// 유효성 검사
if (empty($site_name) || empty($site_url)) {
    json_response(false, '사이트 이름과 URL은 필수입니다.');
}

// SQL 인젝션 방지
$site_name = mysqli_real_escape_string($conn, $site_name);
$site_url = mysqli_real_escape_string($conn, $site_url);
$site_type = mysqli_real_escape_string($conn, $site_type);
// site_type 유효성 검사
if (!in_array($site_type, ['normal', 'sexbam'])) {
    $site_type = 'normal';
}
$target_selector = mysqli_real_escape_string($conn, $target_selector);

// 체크 주기 최소값 확인 (1초 이상)
if ($check_interval < 1) {
    $check_interval = 1;
}

if ($site_id > 0) {
    // 수정
    $query = "UPDATE monitor_sites SET 
                site_name = '$site_name',
                site_url = '$site_url',
                site_type = '$site_type',
                target_selector = '$target_selector',
                check_interval = $check_interval,
                is_active = $is_active,
                follow_redirect = $follow_redirect,
                enable_notification = $enable_notification,
                updated_at = NOW()
              WHERE site_id = $site_id";
} else {
    // 추가
    $query = "INSERT INTO monitor_sites 
                (site_name, site_url, site_type, target_selector, check_interval, is_active, follow_redirect, enable_notification, created_at, updated_at)
              VALUES 
                ('$site_name', '$site_url', '$site_type', '$target_selector', $check_interval, $is_active, $follow_redirect, $enable_notification, NOW(), NOW())";
}

if (sql_exec($query)) {
    monitor_log("Site saved: $site_name", 'info');
    json_response(true, '저장되었습니다.');
} else {
    $conn = db_connect();
    $error = $conn ? mysqli_error($conn) : '데이터베이스 연결 실패';
    monitor_log("Site save failed: $error", 'error');
    json_response(false, '저장 중 오류가 발생했습니다: ' . $error);
}
?>


