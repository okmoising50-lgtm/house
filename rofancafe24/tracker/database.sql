-- 웹 모니터링 시스템 데이터베이스 테이블 (카페24용)
-- UTF-8, MariaDB 10.x 호환

-- 1. 모니터링 대상 사이트 관리 테이블
CREATE TABLE IF NOT EXISTS monitor_sites (
    site_id INT AUTO_INCREMENT PRIMARY KEY,
    site_name VARCHAR(255) NOT NULL COMMENT '사이트 이름',
    site_url TEXT NOT NULL COMMENT '모니터링 URL',
    target_selector VARCHAR(500) DEFAULT 'body' COMMENT '모니터링할 div 선택자',
    check_interval INT DEFAULT 5 COMMENT '체크 주기(초) - 기본 5초',
    is_active TINYINT(1) DEFAULT 1 COMMENT '활성화 여부',
    follow_redirect TINYINT(1) DEFAULT 1 COMMENT 'redirect 자동 추적 여부',
    last_check_time DATETIME COMMENT '마지막 체크 시간',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_active (is_active),
    INDEX idx_last_check (last_check_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='모니터링 사이트 목록';

-- 2. 페이지 컨텐츠 스냅샷 테이블
CREATE TABLE IF NOT EXISTS monitor_snapshots (
    snapshot_id INT AUTO_INCREMENT PRIMARY KEY,
    site_id INT NOT NULL,
    content_hash VARCHAR(64) NOT NULL COMMENT 'SHA256 해시',
    content_text LONGTEXT COMMENT '텍스트 내용',
    full_html LONGTEXT COMMENT '전체 HTML',
    final_url TEXT COMMENT '최종 URL (redirect 후)',
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES monitor_sites(site_id) ON DELETE CASCADE,
    INDEX idx_site_time (site_id, check_time),
    INDEX idx_hash (content_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='페이지 스냅샷 기록';

-- 3. 변화 감지 로그 테이블
CREATE TABLE IF NOT EXISTS monitor_changes (
    change_id INT AUTO_INCREMENT PRIMARY KEY,
    site_id INT NOT NULL,
    old_snapshot_id INT,
    new_snapshot_id INT NOT NULL,
    change_type ENUM('added', 'removed', 'modified', 'initial') NOT NULL COMMENT '변경 타입',
    old_content TEXT COMMENT '이전 내용',
    new_content TEXT COMMENT '새 내용',
    diff_html LONGTEXT COMMENT 'diff HTML (강조 표시 포함)',
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read TINYINT(1) DEFAULT 0 COMMENT '읽음 여부',
    FOREIGN KEY (site_id) REFERENCES monitor_sites(site_id) ON DELETE CASCADE,
    FOREIGN KEY (old_snapshot_id) REFERENCES monitor_snapshots(snapshot_id) ON DELETE SET NULL,
    FOREIGN KEY (new_snapshot_id) REFERENCES monitor_snapshots(snapshot_id) ON DELETE CASCADE,
    INDEX idx_site_detected (site_id, detected_at),
    INDEX idx_is_read (is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='변화 감지 로그';

-- 4. URL 리다이렉트 히스토리 테이블
CREATE TABLE IF NOT EXISTS monitor_redirects (
    redirect_id INT AUTO_INCREMENT PRIMARY KEY,
    site_id INT NOT NULL,
    original_url TEXT NOT NULL,
    final_url TEXT NOT NULL,
    redirect_chain TEXT COMMENT 'JSON 형식의 리다이렉트 체인',
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES monitor_sites(site_id) ON DELETE CASCADE,
    INDEX idx_site_detected (site_id, detected_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='URL 리다이렉트 히스토리';

-- 테스트용 샘플 데이터 (선택사항)
-- INSERT INTO monitor_sites (site_name, site_url, target_selector, check_interval) VALUES
-- ('테스트 사이트', 'https://example.com', 'body', 5);


