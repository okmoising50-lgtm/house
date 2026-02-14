<?php
require_once(__DIR__ . '/../config.php');
check_admin_access();

$site_id = isset($_GET['site_id']) ? intval($_GET['site_id']) : 0;
$is_read = isset($_GET['is_read']) ? $_GET['is_read'] : '';
$limit = isset($_GET['limit']) ? intval($_GET['limit']) : 100;

$where = [];
if ($site_id > 0) {
    $where[] = "mc.site_id = $site_id";
}
if ($is_read !== '') {
    $is_read_val = intval($is_read);
    $where[] = "mc.is_read = $is_read_val";
}

$where_clause = count($where) > 0 ? 'WHERE ' . implode(' AND ', $where) : '';

$query = "SELECT mc.*, COALESCE(ms.site_name, '알 수 없음') as site_name 
          FROM monitor_changes mc
          LEFT JOIN monitor_sites ms ON mc.site_id = ms.site_id
          $where_clause
          ORDER BY mc.detected_at DESC, mc.change_id DESC
          LIMIT $limit";

$changes = sql_fetch($query);

json_response(true, '', $changes);
?>


