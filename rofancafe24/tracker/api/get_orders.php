<?php
/**
 * 예약 오더 목록 조회 API
 */
require_once(__DIR__ . '/../config.php');
check_admin_access();

$conn = db_connect();
if (!$conn) {
    json_response(false, '데이터베이스 연결 실패');
}

$query = "SELECT * FROM reservation_orders ORDER BY created_at DESC LIMIT 100";
$orders = sql_fetch($query);

json_response(true, '', $orders);
?>


