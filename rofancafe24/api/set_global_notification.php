<?php
/**
 * 전체 알림 on/off 설정 API
 */
require_once(__DIR__ . '/../config.php');
check_admin_access();

$enabled = isset($_POST['enabled']) ? intval($_POST['enabled']) : 0;

$conn = db_connect();
if (!$conn) {
    json_response(false, '데이터베이스 연결 실패');
}

$enabled_str = $enabled ? '1' : '0';
$query = "INSERT INTO monitor_settings (setting_key, setting_value) 
          VALUES ('global_notification_enabled', '$enabled_str')
          ON DUPLICATE KEY UPDATE setting_value = '$enabled_str'";

if (sql_exec($query)) {
    json_response(true, '전체 알림 설정이 변경되었습니다.');
} else {
    json_response(false, '설정 변경에 실패했습니다.');
}
?>



