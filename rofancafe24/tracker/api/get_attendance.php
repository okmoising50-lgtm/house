<?php
/**
 * 일자별 출근부 조회 API
 */
require_once(__DIR__ . '/../config.php');
check_admin_access();

$date = $_GET['date'] ?? date('Y-m-d');
$site_id = isset($_GET['site_id']) ? intval($_GET['site_id']) : 0;

$conn = db_connect();
if (!$conn) {
    json_response(false, '데이터베이스 연결 실패');
}

$date_escaped = mysqli_real_escape_string($conn, $date);

if ($site_id > 0) {
    $query = "SELECT a.*, s.site_name 
              FROM staff_attendance a
              JOIN monitor_sites s ON a.site_id = s.site_id
              WHERE a.attendance_date = '$date_escaped' AND a.site_id = $site_id
              ORDER BY a.staff_name";
} else {
    $query = "SELECT a.*, s.site_name 
              FROM staff_attendance a
              JOIN monitor_sites s ON a.site_id = s.site_id
              WHERE a.attendance_date = '$date_escaped'
              ORDER BY s.site_name, a.staff_name";
}

$records = sql_fetch($query);

json_response(true, '', $records);
?>


