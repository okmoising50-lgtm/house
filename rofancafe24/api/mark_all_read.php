<?php
require_once(__DIR__ . '/../config.php');
check_admin_access();

$query = "UPDATE monitor_changes SET is_read = 1 WHERE is_read = 0";

if (sql_exec($query)) {
    $affected = sql_affected_rows();
    json_response(true, "$affected 개의 변화를 읽음으로 처리했습니다.");
} else {
    json_response(false, '처리 중 오류가 발생했습니다.');
}
?>


