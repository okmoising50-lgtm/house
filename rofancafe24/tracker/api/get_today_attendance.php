<?php
/**
 * 오늘 출근부 조회 API (changes.html용)
 */
require_once(__DIR__ . '/../config.php');
check_admin_access();

$conn = db_connect();
if (!$conn) {
    json_response(false, '데이터베이스 연결 실패');
}

$today = date('Y-m-d');

$query = "SELECT a.*, s.site_name 
          FROM staff_attendance a
          JOIN monitor_sites s ON a.site_id = s.site_id
          WHERE a.attendance_date = '$today'
          ORDER BY s.site_name, a.staff_name";

$records = sql_fetch($query);

json_response(true, '', $records);
?>


