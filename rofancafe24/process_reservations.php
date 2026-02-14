<?php
/**
 * 예약 오더 처리 스크립트
 * 크론잡으로 실행하거나, API에서 호출
 * 
 * 사용법: php process_reservations.php
 * 또는 크론: */1 * * * * php /path/to/process_reservations.php
 */

require_once(__DIR__ . '/config.php');

// 처리할 오더 조회 (pending 또는 processing 상태)
$conn = db_connect();
if (!$conn) {
    die("Database connection failed\n");
}

$query = "SELECT * FROM reservation_orders 
          WHERE status IN ('pending', 'processing')
          ORDER BY created_at ASC
          LIMIT 10";

$orders = sql_fetch($query);

if (empty($orders)) {
    exit("No orders to process\n");
}

foreach ($orders as $order) {
    process_order($order);
}

function process_order($order) {
    global $conn;
    
    $order_id = $order['order_id'];
    $staff_name = $order['staff_name'];
    $time_range_start = intval($order['time_range_start']);
    $time_range_end = intval($order['time_range_end']);
    $condition_type = $order['condition_type'];
    $time_count = intval($order['time_count']);
    $test_mode = $order['test_mode'] == '1';
    $test_phone = $order['test_phone'] ?? '';
    
    // 오늘 날짜의 출근부에서 해당 매니저 찾기
    $today = date('Y-m-d');
    $staff_name_escaped = mysqli_real_escape_string($conn, $staff_name);
    $query = "SELECT a.*, s.site_id, s.site_name, p.phone_number
              FROM staff_attendance a
              JOIN monitor_sites s ON a.site_id = s.site_id
              LEFT JOIN staff_phones p ON a.site_id = p.site_id AND a.staff_name = p.staff_name
              WHERE a.attendance_date = '$today' 
              AND a.staff_name LIKE '%$staff_name_escaped%'
              ORDER BY s.site_id";
    
    $attendance_records = sql_fetch($query);
    
    if (empty($attendance_records)) {
        // 매니저를 찾지 못함
        $query = "UPDATE reservation_orders SET status = 'failed' WHERE order_id = $order_id";
        sql_exec($query);
        return;
    }
    
    // 각 사이트별로 처리
    foreach ($attendance_records as $record) {
        $work_times_str = $record['work_times'] ?? '';
        $work_times = parse_work_times($work_times_str);
        
        // 시간 범위 내의 시간만 필터링
        $available_times = array_filter($work_times, function($time) use ($time_range_start, $time_range_end) {
            return $time >= $time_range_start && $time <= $time_range_end;
        });
        
        if (empty($available_times)) {
            continue; // 해당 사이트에는 시간이 없음
        }
        
        // 조건에 따라 시간 선택
        $selected_times = select_times($available_times, $condition_type, $time_count);
        
        if (empty($selected_times)) {
            continue;
        }
        
        // 전화번호 가져오기
        $phone_number = $record['phone_number'] ?? '';
        if (empty($phone_number)) {
            continue; // 전화번호가 없으면 건너뛰기
        }
        
        // 테스트 모드 체크
        if ($test_mode && !empty($test_phone)) {
            $phone_number = $test_phone;
        }
        
        // 웹문자 발송
        $reservation_time = $selected_times[0]; // 첫 번째 시간 사용
        // 시간 형식 변환 (24시는 "24시"로 표시, 나머지는 그대로)
        if ($reservation_time == 24) {
            $display_time = 24;
        } else {
            $display_time = $reservation_time; // 이미 01, 02, 03 형식으로 저장됨
        }
        $message = "$staff_name $display_time시";
        
        $send_result = send_web_message($phone_number, $message);
        
        // 로그 저장
        $phone_escaped = mysqli_real_escape_string($conn, $phone_number);
        $message_escaped = mysqli_real_escape_string($conn, $message);
        $site_id = intval($record['site_id']);
        $staff_name_escaped = mysqli_real_escape_string($conn, $staff_name);
        
        $log_query = "INSERT INTO reservation_logs 
                      (order_id, site_id, staff_name, phone_number, message_text, reservation_time, send_status, sent_at)
                      VALUES 
                      ($order_id, $site_id, '$staff_name_escaped', '$phone_escaped', '$message_escaped', $reservation_time, 
                       '" . ($send_result ? 'success' : 'failed') . "', NOW())";
        sql_exec($log_query);
        
        // 메일 발송
        send_reservation_email($order, $record, $reservation_time, $phone_number, $send_result);
    }
    
    // 오더 상태 업데이트
    $query = "UPDATE reservation_orders SET status = 'completed', completed_at = NOW() WHERE order_id = $order_id";
    sql_exec($query);
}

function parse_work_times($work_times_str) {
    // "12,13,14" 또는 "12~14" 또는 "24~03" 형식 파싱
    $times = [];
    
    if (strpos($work_times_str, '~') !== false) {
        // 범위 형식
        $parts = explode('~', $work_times_str);
        if (count($parts) == 2) {
            $start = intval(trim($parts[0]));
            $end = intval(trim($parts[1]));
            
            // 24시 이후 시간 처리 (24~03시 같은 경우)
            if ($start >= 24 && $end < 24) {
                // 24시부터 시작해서 다음날로 넘어가는 경우
                // 예: 24~03시 -> 24, 01, 02, 03 (03시는 마감이므로 예약 불가)
                // 예약 가능한 시간: 24, 01, 02 (03시는 마감이므로 제외)
                // 24시는 그대로, 25=01시, 26=02시, 27=03시
                for ($i = $start; $i <= ($end + 24); $i++) { // 24부터 (end+24)까지
                    if ($i == $start) {
                        // 24시는 그대로
                        $times[] = 24;
                    } else if ($i > 24) {
                        // 25=01, 26=02, 27=03
                        $actual_time = $i - 24;
                        // 마감 시간(end)은 제외 (예: 03시는 마감이므로 예약 불가)
                        if ($actual_time < $end) {
                            $times[] = $actual_time;
                        }
                    }
                }
            } else {
                // 일반 범위 (12~14 같은 경우)
                $times = range($start, $end);
            }
        }
    } else {
        // 리스트 형식: "24,01,02" 또는 "12,13,14"
        $parts = explode(',', $work_times_str);
        foreach ($parts as $part) {
            $time = intval(trim($part));
            if ($time >= 0 && $time <= 27) { // 0~27 허용 (24시 이후 포함)
                $times[] = $time;
            }
        }
    }
    
    return $times;
}

function select_times($available_times, $condition_type, $time_count) {
    $available_times = array_values($available_times); // 인덱스 재정렬
    
    // 시간 정렬 (24시 이후 시간 고려)
    // 24시 이후 시간(25=01, 26=02, 27=03)을 올바르게 정렬하기 위해
    // 실제 시간 값으로 변환하여 정렬
    $time_map = [];
    foreach ($available_times as $time) {
        // 24시 이후 시간을 실제 시간으로 변환 (25->25, 26->26, 27->27로 유지하되 정렬 시 고려)
        // 정렬: 0~23은 그대로, 24~27은 24+로 처리
        $sort_key = $time >= 24 ? (100 + $time) : $time; // 24~27을 100+로 처리하여 뒤로
        $time_map[$sort_key] = $time;
    }
    
    ksort($time_map); // 오름차순 정렬
    $sorted_times = array_values($time_map);
    
    if ($condition_type == 'latest') {
        // 가장 늦은 시간부터 선택 (내림차순)
        rsort($sorted_times);
        return array_slice($sorted_times, 0, $time_count);
    } else {
        // 가장 빠른 시간부터 선택 (오름차순)
        sort($sorted_times);
        return array_slice($sorted_times, 0, $time_count);
    }
}

function send_web_message($phone_number, $message) {
    // TODO: 웹문자 발송 API 연동
    // 현재는 로그만 남김
    error_log("Web message to $phone_number: $message");
    
    // 실제 웹문자 발송은 나중에 구현
    // 예: 카카오톡 비즈니스 API, 알리고, 문자나라 등
    
    return true; // 임시로 성공 반환
}

function send_reservation_email($order, $attendance_record, $reservation_time, $phone_number, $send_result) {
    $to = 'okmoising@gmail.com';
    $subject = '[예약 발송] ' . $order['staff_name'] . ' ' . $reservation_time . '시 예약';
    
    $message = "
    예약 오더가 처리되었습니다.
    
    매니저: {$order['staff_name']}
    예약 시간: {$reservation_time}시
    사이트: {$attendance_record['site_name']}
    전화번호: {$phone_number}
    발송 상태: " . ($send_result ? '성공' : '실패') . "
    
    오더 정보:
    - 시간 범위: {$order['time_range_start']}시 ~ {$order['time_range_end']}시
    - 조건: " . ($order['condition_type'] == 'latest' ? '가장 늦은시간' : '가장 빠른시간') . "
    - 타임 수: {$order['time_count']}
    - 테스트 모드: " . ($order['test_mode'] == '1' ? '예' : '아니오') . "
    ";
    
    $headers = "From: noreply@rofan.mycafe24.com\r\n";
    $headers .= "Content-Type: text/plain; charset=UTF-8\r\n";
    
    mail($to, $subject, $message, $headers);
}
?>

