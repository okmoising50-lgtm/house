# 스냅샷 정리 스크립트 사용법

## 개요
`cleanup_snapshots.php`는 `monitor_snapshots` 테이블에서 10분 이내에 생성된 동일한 `content_text`를 가진 스냅샷 중 가장 오래된 것 1개만 남기고 나머지를 삭제합니다.

## 사용 방법

### 1. 수동 실행
```bash
php cleanup_snapshots.php
```

### 2. Cron에 등록 (10분마다 자동 실행)
카페24 호스팅의 경우, cPanel의 Cron Jobs에서 설정하거나 SSH 접속이 가능한 경우:

```bash
# 10분마다 실행
*/10 * * * * php /home/rofan/www/tracker/cleanup_snapshots.php >> /home/rofan/www/tracker/logs/cleanup.log 2>&1
```

### 3. 웹 API로 실행
브라우저에서 접속:
```
https://rofan.mycafe24.com/tracker/cleanup_snapshots.php
```

## 동작 방식
1. 10분 이내에 생성된 스냅샷만 대상으로 함
2. `site_id`와 `content_hash`가 동일한 스냅샷들을 그룹화
3. 각 그룹에서 가장 오래된 것(첫 번째)만 유지
4. 나머지는 삭제 (단, `monitor_changes`에서 참조 중인 것은 삭제하지 않음)

## 주의사항
- `monitor_changes` 테이블에서 참조 중인 스냅샷은 삭제하지 않습니다
- 삭제된 스냅샷은 복구할 수 없으므로 주의하세요
- 정리 작업은 로그에 기록됩니다 (`logs/monitor_YYYY-MM-DD.log`)


