-- 출근부 추출 방식 컬럼 추가
-- 실행 방법: mysql -u 사용자명 -p 데이터베이스명 < database_add_attendance_extraction_mode.sql

ALTER TABLE monitor_sites 
ADD COLUMN attendance_extraction_mode VARCHAR(10) DEFAULT 'both' 
COMMENT '출근부 추출 방식: both(제목+본문), title(제목만), body(본문만)' 
AFTER target_selector;

-- 기존 데이터에 기본값 설정
UPDATE monitor_sites 
SET attendance_extraction_mode = 'both' 
WHERE attendance_extraction_mode IS NULL OR attendance_extraction_mode = '';

