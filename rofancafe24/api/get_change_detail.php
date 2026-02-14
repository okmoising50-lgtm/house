<?php
require_once(__DIR__ . '/../config.php');
check_admin_access();

$change_id = isset($_GET['change_id']) ? intval($_GET['change_id']) : 0;

if (!$change_id) {
    json_response(false, '변화 ID가 필요합니다.');
}

$query = "SELECT mc.*, ms.site_name 
          FROM monitor_changes mc
          LEFT JOIN monitor_sites ms ON mc.site_id = ms.site_id
          WHERE mc.change_id = $change_id";

$change = sql_query($query);

if (!$change) {
    json_response(false, '변화 로그를 찾을 수 없습니다.');
}

json_response(true, '', $change);
?>


