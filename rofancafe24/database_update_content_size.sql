-- monitor_changes 테이블의 old_content와 new_content 컬럼을 LONGTEXT로 변경
-- TEXT 타입은 최대 65KB만 저장 가능하므로, 긴 내용을 저장하기 위해 LONGTEXT로 변경

ALTER TABLE monitor_changes 
MODIFY COLUMN old_content LONGTEXT COMMENT '이전 내용',
MODIFY COLUMN new_content LONGTEXT COMMENT '새 내용';

-- 변경 확인
-- SELECT COLUMN_NAME, COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH 
-- FROM INFORMATION_SCHEMA.COLUMNS 
-- WHERE TABLE_SCHEMA = 'rofan' AND TABLE_NAME = 'monitor_changes' 
-- AND COLUMN_NAME IN ('old_content', 'new_content');


