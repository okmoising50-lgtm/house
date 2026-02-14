<?php
/**
 * 예약 오더 저장 API
 */
require_once(__DIR__ . '/../config.php');
check_admin_access();

$staff_name = trim($_POST['staff_name'] ?? '');
$time_range_start = intval($_POST['time_range_start'] ?? 0);
$time_range_end = intval($_POST['time_range_end'] ?? 0);
$condition_type = $_POST['condition_type'] ?? 'latest';
$time_count = intval($_POST['time_count'] ?? 1);
$test_mode = (isset($_POST['test_mode']) && $_POST['test_mode'] == '1') ? 1 : 0;
$test_phone = trim($_POST['test_phone'] ?? '');

if (empty($staff_name) || $time_range_start < 0 || $time_range_end < 0 || $time_count < 1) {
    json_response(false, '필수 항목을 입력하세요.');
}

$conn = db_connect();
if (!$conn) {
    json_response(false, '데이터베이스 연결 실패');
}

$staff_name_escaped = mysqli_real_escape_string($conn, $staff_name);
$condition_type_escaped = mysqli_real_escape_string($conn, $condition_type);
$test_phone_escaped = mysqli_real_escape_string($conn, $test_phone);

$query = "INSERT INTO reservation_orders 
          (staff_name, time_range_start, time_range_end, condition_type, time_count, status, test_mode, test_phone, created_at)
          VALUES 
          ('$staff_name_escaped', $time_range_start, $time_range_end, '$condition_type_escaped', $time_count, 'pending', $test_mode, '$test_phone_escaped', NOW())";

if (sql_exec($query)) {
    $order_id = mysqli_insert_id($conn);
    
    // 예약 오더 처리 시작 (백그라운드)
    process_reservation_order($order_id);
    
    json_response(true, '예약 오더가 추가되었습니다.', ['order_id' => $order_id]);
} else {
    json_response(false, '저장에 실패했습니다.');
}

function process_reservation_order($order_id) {
    // 예약 오더 처리 로직은 별도 스크립트에서 실행
    // 여기서는 상태만 업데이트
    $conn = db_connect();
    if (!$conn) return;
    
    $query = "UPDATE reservation_orders SET status = 'processing', processed_at = NOW() WHERE order_id = $order_id";
    sql_exec($query);
}
?>



