-- 알림 기능을 위한 데이터베이스 업데이트
-- 기존 테이블에 enable_notification 컬럼 추가

ALTER TABLE monitor_sites 
ADD COLUMN enable_notification TINYINT(1) DEFAULT 1 COMMENT '알림 활성화 여부' AFTER is_active;

-- 전체 알림 설정을 위한 설정 테이블 (선택사항)
CREATE TABLE IF NOT EXISTS monitor_settings (
    setting_key VARCHAR(50) PRIMARY KEY,
    setting_value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='모니터링 시스템 설정';

-- 전체 알림 기본값 설정
INSERT INTO monitor_settings (setting_key, setting_value) 
VALUES ('global_notification_enabled', '1')
ON DUPLICATE KEY UPDATE setting_value = '1';


