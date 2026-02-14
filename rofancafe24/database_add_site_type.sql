-- monitor_sites 테이블에 site_type 컬럼 추가
ALTER TABLE monitor_sites 
ADD COLUMN site_type ENUM('normal', 'sexbam') DEFAULT 'normal' COMMENT '사이트 유형 (normal: 일반, sexbam: 섹밤유형)' 
AFTER target_selector;

-- 기존 데이터는 모두 'normal'로 설정
UPDATE monitor_sites SET site_type = 'normal' WHERE site_type IS NULL;


