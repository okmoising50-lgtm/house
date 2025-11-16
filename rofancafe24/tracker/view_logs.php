<?php
/**
 * 로그 확인 페이지
 * PHP API 로그와 크롤러 상태를 확인할 수 있습니다.
 */

require_once(__DIR__ . '/config.php');

// 오늘 날짜
$today = date('Y-m-d');
$log_file = LOG_PATH . '/monitor_' . $today . '.log';

// 최근 로그 읽기 (마지막 500줄)
$logs = [];
if (file_exists($log_file)) {
    $lines = file($log_file);
    $logs = array_slice($lines, -500); // 마지막 500줄만
    $logs = array_reverse($logs); // 최신순으로
}

// 데이터베이스에서 최근 변화 로그 확인
$recent_changes = sql_fetch("
    SELECT c.*, s.site_name 
    FROM monitor_changes c
    LEFT JOIN monitor_sites s ON c.site_id = s.site_id
    ORDER BY c.detected_at DESC
    LIMIT 20
");

// 최근 스냅샷 확인
$recent_snapshots = sql_fetch("
    SELECT s.*, st.site_name
    FROM monitor_snapshots s
    LEFT JOIN monitor_sites st ON s.site_id = st.site_id
    ORDER BY s.check_time DESC
    LIMIT 10
");
?>
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>로그 확인 - 웹 모니터링 시스템</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .log-entry {
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
            padding: 5px;
            border-left: 3px solid #ddd;
            margin-bottom: 5px;
            background-color: #f8f9fa;
        }
        .log-entry.error {
            border-left-color: #dc3545;
            background-color: #fff5f5;
        }
        .log-entry.warning {
            border-left-color: #ffc107;
            background-color: #fffbf0;
        }
        .log-entry.info {
            border-left-color: #0d6efd;
        }
        pre {
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            max-height: 400px;
            overflow-y: auto;
        }
        .table-sm {
            font-size: 0.85rem;
        }
    </style>
</head>
<body>
    <div class="container-fluid mt-4">
        <h2>🔍 로그 확인</h2>
        <hr>
        
        <div class="row">
            <!-- PHP API 로그 -->
            <div class="col-md-6">
                <div class="card mb-4">
                    <div class="card-header bg-primary text-white">
                        <h5>PHP API 로그 (오늘: <?php echo $today; ?>)</h5>
                    </div>
                    <div class="card-body">
                        <?php if (empty($logs)): ?>
                            <p class="text-muted">오늘 로그가 없습니다.</p>
                        <?php else: ?>
                            <pre><?php 
                                foreach ($logs as $log) {
                                    $log = htmlspecialchars($log);
                                    $class = 'log-entry';
                                    if (strpos($log, '[error]') !== false) {
                                        $class .= ' error';
                                    } elseif (strpos($log, '[warning]') !== false) {
                                        $class .= ' warning';
                                    } else {
                                        $class .= ' info';
                                    }
                                    echo '<div class="' . $class . '">' . $log . '</div>';
                                }
                            ?></pre>
                        <?php endif; ?>
                    </div>
                </div>
            </div>
            
            <!-- 최근 변화 로그 -->
            <div class="col-md-6">
                <div class="card mb-4">
                    <div class="card-header bg-success text-white">
                        <h5>최근 변화 로그 (DB)</h5>
                    </div>
                    <div class="card-body">
                        <table class="table table-sm table-striped">
                            <thead>
                                <tr>
                                    <th>시간</th>
                                    <th>사이트</th>
                                    <th>타입</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php foreach ($recent_changes as $change): ?>
                                    <tr>
                                        <td><?php echo htmlspecialchars($change['detected_at']); ?></td>
                                        <td><?php echo htmlspecialchars($change['site_name'] ?? 'N/A'); ?></td>
                                        <td>
                                            <span class="badge bg-<?php 
                                                echo $change['change_type'] == 'initial' ? 'info' : 'warning';
                                            ?>">
                                                <?php echo htmlspecialchars($change['change_type']); ?>
                                            </span>
                                        </td>
                                    </tr>
                                <?php endforeach; ?>
                                <?php if (empty($recent_changes)): ?>
                                    <tr><td colspan="3" class="text-muted">변화 로그가 없습니다.</td></tr>
                                <?php endif; ?>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 최근 스냅샷 -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-info text-white">
                        <h5>최근 스냅샷 (DB)</h5>
                    </div>
                    <div class="card-body">
                        <table class="table table-sm table-striped">
                            <thead>
                                <tr>
                                    <th>시간</th>
                                    <th>사이트</th>
                                    <th>해시</th>
                                    <th>내용 길이</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php foreach ($recent_snapshots as $snapshot): ?>
                                    <tr>
                                        <td><?php echo htmlspecialchars($snapshot['check_time']); ?></td>
                                        <td><?php echo htmlspecialchars($snapshot['site_name'] ?? 'N/A'); ?></td>
                                        <td><code><?php echo htmlspecialchars(substr($snapshot['content_hash'], 0, 16)); ?>...</code></td>
                                        <td><?php echo strlen($snapshot['content_text'] ?? ''); ?>자</td>
                                    </tr>
                                <?php endforeach; ?>
                                <?php if (empty($recent_snapshots)): ?>
                                    <tr><td colspan="4" class="text-muted">스냅샷이 없습니다.</td></tr>
                                <?php endif; ?>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <hr>
        <div class="mb-3">
            <a href="admin.html" class="btn btn-secondary">관리자 페이지</a>
            <a href="changes.html" class="btn btn-primary">변화 로그</a>
            <button onclick="location.reload()" class="btn btn-info">새로고침</button>
        </div>
        
        <div class="alert alert-info">
            <strong>크롤러 로그 확인 방법:</strong><br>
            GCP 서버에 SSH 접속 후 다음 명령어 실행:<br>
            <code>tail -f /root/mailcenter/sound/crawler.log</code>
        </div>
    </div>
</body>
</html>


