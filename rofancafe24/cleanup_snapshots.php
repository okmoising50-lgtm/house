<?php
/**
 * 스냅샷 정리 스크립트
 * 10분마다 content_text가 동일한 스냅샷 중 가장 오래된 것 1개만 남기고 나머지 삭제
 * 
 * 사용법:
 * 1. cron에 등록: */10 * * * * php /path/to/cleanup_snapshots.php
 * 2. 또는 수동 실행: php cleanup_snapshots.php
 */

require_once(__DIR__ . '/config.php');

function cleanup_duplicate_snapshots() {
    $conn = db_connect();
    if (!$conn) {
        echo "데이터베이스 연결 실패\n";
        return false;
    }
    
    // 10분 이내에 생성된 스냅샷 중 content_text가 동일한 것들 찾기
    $query = "SELECT snapshot_id, site_id, content_text, content_hash, created_at
              FROM monitor_snapshots
              WHERE created_at > DATE_SUB(NOW(), INTERVAL 10 MINUTE)
              ORDER BY site_id, content_hash, created_at ASC";
    
    $result = mysqli_query($conn, $query);
    if (!$result) {
        echo "쿼리 실행 실패: " . mysqli_error($conn) . "\n";
        return false;
    }
    
    $snapshots_by_hash = [];
    $deleted_count = 0;
    
    // content_hash별로 그룹화
    while ($row = mysqli_fetch_assoc($result)) {
        $key = $row['site_id'] . '_' . $row['content_hash'];
        
        if (!isset($snapshots_by_hash[$key])) {
            $snapshots_by_hash[$key] = [];
        }
        
        $snapshots_by_hash[$key][] = $row;
    }
    
    // 각 그룹에서 가장 오래된 것 1개만 남기고 나머지 삭제
    foreach ($snapshots_by_hash as $key => $snapshots) {
        if (count($snapshots) <= 1) {
            continue; // 1개만 있으면 삭제할 필요 없음
        }
        
        // 가장 오래된 것 (첫 번째)은 유지, 나머지 삭제
        $keep_snapshot = $snapshots[0];
        $delete_snapshots = array_slice($snapshots, 1);
        
        foreach ($delete_snapshots as $snapshot) {
            // monitor_changes에서 참조하는지 확인
            $check_query = "SELECT COUNT(*) as cnt FROM monitor_changes 
                           WHERE old_snapshot_id = {$snapshot['snapshot_id']} 
                              OR new_snapshot_id = {$snapshot['snapshot_id']}";
            $check_result = mysqli_query($conn, $check_query);
            $check_row = mysqli_fetch_assoc($check_result);
            
            if ($check_row['cnt'] > 0) {
                // 참조되고 있으면 삭제하지 않음
                continue;
            }
            
            // 삭제
            $delete_query = "DELETE FROM monitor_snapshots WHERE snapshot_id = {$snapshot['snapshot_id']}";
            if (mysqli_query($conn, $delete_query)) {
                $deleted_count++;
                monitor_log("스냅샷 정리: snapshot_id {$snapshot['snapshot_id']} 삭제 (site_id: {$snapshot['site_id']}, 중복)", 'info');
            } else {
                echo "스냅샷 삭제 실패 (snapshot_id: {$snapshot['snapshot_id']}): " . mysqli_error($conn) . "\n";
            }
        }
    }
    
    echo date('Y-m-d H:i:s') . " - 스냅샷 정리 완료: {$deleted_count}개 삭제\n";
    monitor_log("스냅샷 정리 완료: {$deleted_count}개 삭제", 'info');
    
    return true;
}

// 스크립트 직접 실행 시
if (php_sapi_name() === 'cli' || !isset($_SERVER['REQUEST_METHOD'])) {
    cleanup_duplicate_snapshots();
} else {
    // 웹 요청 시 (API로 사용 가능)
    require_once(__DIR__ . '/config.php');
    check_admin_access();
    
    if (cleanup_duplicate_snapshots()) {
        json_response(true, '스냅샷 정리 완료');
    } else {
        json_response(false, '스냅샷 정리 실패');
    }
}
?>



