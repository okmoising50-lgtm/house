<?php
/**
 * 알림 on/off 토글 API
 */
require_once(__DIR__ . '/../config.php');
check_admin_access();

$site_id = isset($_POST['site_id']) ? intval($_POST['site_id']) : 0;
$enable = isset($_POST['enable']) ? intval($_POST['enable']) : 0;

if ($site_id <= 0) {
    json_response(false, '사이트 ID가 필요합니다.');
}

$conn = db_connect();
if (!$conn) {
    json_response(false, '데이터베이스 연결 실패');
}

$query = "UPDATE monitor_sites SET enable_notification = $enable WHERE site_id = $site_id";

if (sql_exec($query)) {
    json_response(true, '알림 설정이 변경되었습니다.');
} else {
    json_response(false, '설정 변경에 실패했습니다.');
}
?>


