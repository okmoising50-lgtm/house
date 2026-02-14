<?php
require_once(__DIR__ . '/../config.php');
check_admin_access();

$site_id = isset($_POST['site_id']) ? intval($_POST['site_id']) : 0;

if (!$site_id) {
    json_response(false, '사이트 ID가 필요합니다.');
}

$query = "DELETE FROM monitor_sites WHERE site_id = $site_id";

if (sql_exec($query)) {
    monitor_log("Site deleted: ID $site_id", 'info');
    json_response(true, '삭제되었습니다.');
} else {
    json_response(false, '삭제 중 오류가 발생했습니다.');
}
?>


