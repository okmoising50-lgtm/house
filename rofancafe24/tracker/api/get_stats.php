<?php
require_once(__DIR__ . '/../config.php');
check_admin_access();

// 총 변화 감지 수
$total_query = "SELECT COUNT(*) as cnt FROM monitor_changes";
$total_result = sql_query($total_query);
$total_changes = $total_result ? $total_result['cnt'] : 0;

// 읽지 않은 변화 수
$unread_query = "SELECT COUNT(*) as cnt FROM monitor_changes WHERE is_read = 0";
$unread_result = sql_query($unread_query);
$unread_changes = $unread_result ? $unread_result['cnt'] : 0;

// 활성화된 사이트 수
$active_query = "SELECT COUNT(*) as cnt FROM monitor_sites WHERE is_active = 1";
$active_result = sql_query($active_query);
$active_sites = $active_result ? $active_result['cnt'] : 0;

json_response(true, '', [
    'total_changes' => $total_changes,
    'unread_changes' => $unread_changes,
    'active_sites' => $active_sites
]);
?>


