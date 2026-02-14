-- 출근부 및 예약 시스템 데이터베이스 테이블
-- UTF-8, MariaDB 10.x 호환

-- 1. 매니저 전화번호 테이블 (사이트별로 저장)
CREATE TABLE IF NOT EXISTS staff_phones (
    phone_id INT AUTO_INCREMENT PRIMARY KEY,
    site_id INT NOT NULL COMMENT '모니터링 사이트 ID',
    staff_name VARCHAR(100) NOT NULL COMMENT '매니저 이름',
    phone_number VARCHAR(20) NOT NULL COMMENT '전화번호 (010-1234-5678 형식)',
    extracted_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '추출된 시간',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '업데이트 시간',
    FOREIGN KEY (site_id) REFERENCES monitor_sites(site_id) ON DELETE CASCADE,
    INDEX idx_site_name (site_id, staff_name),
    INDEX idx_phone (phone_number),
    UNIQUE KEY unique_site_staff (site_id, staff_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='매니저 전화번호 저장';

-- 2. 일자별 출근부 기록 테이블
CREATE TABLE IF NOT EXISTS staff_attendance (
    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
    site_id INT NOT NULL COMMENT '모니터링 사이트 ID',
    attendance_date DATE NOT NULL COMMENT '출근 날짜',
    staff_name VARCHAR(100) NOT NULL COMMENT '매니저 이름',
    work_times TEXT COMMENT '출근 시간 (예: 12,13,14 또는 12~14)',
    raw_content TEXT COMMENT '원본 추출 내용',
    snapshot_id INT COMMENT '스냅샷 ID (참조용)',
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '감지된 시간',
    FOREIGN KEY (site_id) REFERENCES monitor_sites(site_id) ON DELETE CASCADE,
    FOREIGN KEY (snapshot_id) REFERENCES monitor_snapshots(snapshot_id) ON DELETE SET NULL,
    INDEX idx_site_date (site_id, attendance_date),
    INDEX idx_staff_date (staff_name, attendance_date),
    UNIQUE KEY unique_site_date_staff (site_id, attendance_date, staff_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='일자별 출근부 기록';

-- 3. 예약 오더 테이블
CREATE TABLE IF NOT EXISTS reservation_orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    staff_name VARCHAR(100) NOT NULL COMMENT '매니저 이름',
    time_range_start INT COMMENT '시간 범위 시작 (예: 18)',
    time_range_end INT COMMENT '시간 범위 끝 (예: 20)',
    condition_type ENUM('earliest', 'latest') DEFAULT 'latest' COMMENT '조건: earliest(가장 빠른시간), latest(가장 늦은시간)',
    time_count INT DEFAULT 1 COMMENT '타임 수 (1타임, 2타임 등)',
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending' COMMENT '상태',
    test_mode TINYINT(1) DEFAULT 0 COMMENT '테스트 모드 여부',
    test_phone VARCHAR(20) COMMENT '테스트 전화번호',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '생성 시간',
    processed_at DATETIME COMMENT '처리 시간',
    completed_at DATETIME COMMENT '완료 시간',
    INDEX idx_status (status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='예약 오더';

-- 4. 예약 발송 로그 테이블
CREATE TABLE IF NOT EXISTS reservation_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL COMMENT '예약 오더 ID',
    site_id INT COMMENT '사이트 ID',
    staff_name VARCHAR(100) NOT NULL COMMENT '매니저 이름',
    phone_number VARCHAR(20) NOT NULL COMMENT '발송된 전화번호',
    message_text TEXT COMMENT '발송된 메시지 내용',
    reservation_time INT COMMENT '예약 시간 (예: 20)',
    send_status ENUM('success', 'failed') DEFAULT 'success' COMMENT '발송 상태',
    send_error TEXT COMMENT '발송 오류 메시지',
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '발송 시간',
    FOREIGN KEY (order_id) REFERENCES reservation_orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (site_id) REFERENCES monitor_sites(site_id) ON DELETE SET NULL,
    INDEX idx_order (order_id),
    INDEX idx_sent (sent_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='예약 발송 로그';

-- 5. 시스템 설정 테이블 (테스트 모드, 테스트 전화번호 등)
CREATE TABLE IF NOT EXISTS system_settings (
    setting_key VARCHAR(100) PRIMARY KEY COMMENT '설정 키',
    setting_value TEXT COMMENT '설정 값',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '업데이트 시간'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='시스템 설정';

-- 초기 설정 데이터
INSERT INTO system_settings (setting_key, setting_value) VALUES
('test_mode_enabled', '0'),
('test_phone_number', ''),
('email_recipient', 'okmoising@gmail.com')
ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value);



