<?php
require_once(__DIR__ . '/../config.php');
check_admin_access();

$change_id = isset($_POST['change_id']) ? intval($_POST['change_id']) : 0;

if (!$change_id) {
    json_response(false, '변화 ID가 필요합니다.');
}

$query = "UPDATE monitor_changes SET is_read = 1 WHERE change_id = $change_id";

if (sql_exec($query)) {
    json_response(true, '읽음으로 처리되었습니다.');
} else {
    json_response(false, '처리 중 오류가 발생했습니다.');
}
?>


