-- 마지막 예약 가능 인원 저장 테이블
-- 실행 방법: mysql -u 사용자명 -p 데이터베이스명 < database_add_available_staff.sql

CREATE TABLE IF NOT EXISTS available_staff (
    available_id INT AUTO_INCREMENT PRIMARY KEY,
    site_id INT NOT NULL COMMENT '모니터링 사이트 ID',
    attendance_date DATE NOT NULL COMMENT '출근 날짜',
    staff_name VARCHAR(100) NOT NULL COMMENT '매니저 이름',
    available_times TEXT COMMENT '예약 가능 시간 (예: 13,14,15,16)',
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '감지된 시간',
    FOREIGN KEY (site_id) REFERENCES monitor_sites(site_id) ON DELETE CASCADE,
    INDEX idx_site_date (site_id, attendance_date),
    INDEX idx_staff_date (staff_name, attendance_date),
    UNIQUE KEY unique_site_date_staff (site_id, attendance_date, staff_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='마지막 예약 가능 인원 저장 (문자 발송용)';

