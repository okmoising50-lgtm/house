<?php
require_once(__DIR__ . '/../config.php');
check_admin_access();

$site_id = isset($_GET['site_id']) ? intval($_GET['site_id']) : 0;

if (!$site_id) {
    json_response(false, '사이트 ID가 필요합니다.');
}

$query = "SELECT * FROM monitor_sites WHERE site_id = $site_id";
$site = sql_query($query);

if (!$site) {
    json_response(false, '사이트를 찾을 수 없습니다.');
}

json_response(true, '', $site);
?>


