<?php
/**
 * 새로운 변화 로그 조회 API (알림용)
 * 마지막으로 확인한 change_id 이후의 새로운 변화만 반환
 */
require_once(__DIR__ . '/../config.php');
check_admin_access();

$last_change_id = isset($_GET['last_change_id']) ? intval($_GET['last_change_id']) : 0;

// 전체 알림 설정 확인
$global_setting = sql_query("SELECT setting_value FROM monitor_settings WHERE setting_key = 'global_notification_enabled'");
$global_enabled = $global_setting ? intval($global_setting['setting_value']) : 1;

if (!$global_enabled) {
    json_response(true, '', []);
}

// 새로운 변화 조회 (읽지 않은 것만, 알림이 활성화된 사이트만)
$query = "SELECT mc.*, COALESCE(ms.site_name, '알 수 없음') as site_name, ms.enable_notification
          FROM monitor_changes mc
          LEFT JOIN monitor_sites ms ON mc.site_id = ms.site_id
          WHERE mc.change_id > $last_change_id 
            AND mc.is_read = 0
            AND (ms.enable_notification = 1 OR ms.enable_notification IS NULL)
          ORDER BY mc.detected_at DESC, mc.change_id DESC
          LIMIT 50";

$changes = sql_fetch($query);

json_response(true, '', $changes);
?>


