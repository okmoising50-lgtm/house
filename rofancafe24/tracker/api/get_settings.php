<?php
/**
 * 시스템 설정 조회 API
 */
require_once(__DIR__ . '/../config.php');
check_admin_access();

$conn = db_connect();
if (!$conn) {
    json_response(false, '데이터베이스 연결 실패');
}

$settings = [];
$query = "SELECT setting_key, setting_value FROM system_settings";
$results = sql_fetch($query);

foreach ($results as $row) {
    $settings[$row['setting_key']] = $row['setting_value'];
}

json_response(true, '', $settings);
?>


