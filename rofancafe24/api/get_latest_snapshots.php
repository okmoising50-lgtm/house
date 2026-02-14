<?php
/**
 * 각 사이트의 최신 스냅샷 조회 API (크롤러 초기화용)
 */
require_once(__DIR__ . '/../config.php');
check_api_auth();

$site_ids = isset($_GET['site_ids']) ? $_GET['site_ids'] : '';
$site_id_array = [];

if ($site_ids) {
    // 콤마로 구분된 site_id 리스트 파싱
    $site_id_array = array_map('intval', explode(',', $site_ids));
    $site_id_list = implode(',', $site_id_array);
    $where_clause = "WHERE s.site_id IN ($site_id_list)";
} else {
    // 모든 활성 사이트의 최신 스냅샷
    $where_clause = "WHERE st.is_active = 1";
}

// 각 사이트별 최신 스냅샷 조회
$query = "SELECT s.snapshot_id, s.site_id, s.content_hash, s.content_text, s.check_time
          FROM monitor_snapshots s
          LEFT JOIN monitor_sites st ON s.site_id = st.site_id
          $where_clause
          AND s.snapshot_id IN (
              SELECT MAX(snapshot_id) 
              FROM monitor_snapshots 
              WHERE site_id = s.site_id
          )
          ORDER BY s.site_id";

$snapshots = sql_fetch($query);

json_response(true, '', $snapshots);
?>

