<?php
/**
 * 예약 오더 삭제 API
 */
require_once(__DIR__ . '/../config.php');
check_admin_access();

$order_id = intval($_POST['order_id'] ?? 0);

if ($order_id <= 0) {
    json_response(false, '오더 ID가 필요합니다.');
}

$conn = db_connect();
if (!$conn) {
    json_response(false, '데이터베이스 연결 실패');
}

$query = "DELETE FROM reservation_orders WHERE order_id = $order_id";

if (sql_exec($query)) {
    json_response(true, '삭제되었습니다.');
} else {
    json_response(false, '삭제에 실패했습니다.');
}
?>


