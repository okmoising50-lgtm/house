<?php
/**
 * 알림 설정 조회 API
 */
require_once(__DIR__ . '/../config.php');
check_admin_access();

// 전체 알림 설정 조회
$global_setting = sql_query("SELECT setting_value FROM monitor_settings WHERE setting_key = 'global_notification_enabled'");
$global_enabled = $global_setting ? intval($global_setting['setting_value']) : 1;

// 각 사이트별 알림 설정 조회
$sites = sql_fetch("SELECT site_id, enable_notification FROM monitor_sites");

$settings = [
    'global_enabled' => $global_enabled,
    'sites' => []
];

foreach ($sites as $site) {
    $settings['sites'][$site['site_id']] = intval($site['enable_notification']);
}

json_response(true, '', $settings);
?>


