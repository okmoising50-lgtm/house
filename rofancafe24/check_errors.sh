#!/bin/bash
# 에러 로그 확인 스크립트

echo "=========================================="
echo "크롤러 에러 로그 확인"
echo "=========================================="
echo ""

LOG_FILE="/root/mailcenter/sound/crawler.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "✗ 로그 파일이 없습니다: $LOG_FILE"
    exit 1
fi

echo "1. 최근 에러 로그 (마지막 30줄):"
echo "----------------------------------------"
grep -i "error\|exception\|failed\|✗\|500\|403\|429\|503\|TIMEOUT\|CONNECTION" "$LOG_FILE" | tail -30
echo ""

echo "2. HTTP 500 에러 확인:"
echo "----------------------------------------"
grep -i "500\|SERVER ERROR" "$LOG_FILE" | tail -20
echo ""

echo "3. JSON 디코드 에러 확인:"
echo "----------------------------------------"
grep -i "JSON\|json\|decode" "$LOG_FILE" | tail -20
echo ""

echo "4. API 응답 에러 확인:"
echo "----------------------------------------"
grep -i "API.*error\|API.*failed\|API response" "$LOG_FILE" | tail -20
echo ""

echo "5. 최근 10분간의 에러:"
echo "----------------------------------------"
# 최근 10분간의 로그 (현재 시간 기준)
CURRENT_TIME=$(date +%s)
TEN_MIN_AGO=$((CURRENT_TIME - 600))
# 간단하게 최근 로그만 확인
tail -100 "$LOG_FILE" | grep -i "error\|exception\|failed\|✗\|500" | tail -20
echo ""

echo "6. 오늘 날짜의 모든 에러 개수:"
echo "----------------------------------------"
TODAY=$(date +%Y-%m-%d)
ERROR_COUNT=$(grep "$TODAY" "$LOG_FILE" | grep -ci "error\|exception\|failed\|✗" || echo "0")
echo "오늘($TODAY) 에러 개수: $ERROR_COUNT"
echo ""

echo "=========================================="
echo "카페24 PHP 에러 로그 확인 방법:"
echo "=========================================="
echo ""
echo "카페24 호스팅에서 PHP 에러 로그 확인:"
echo "1. FTP로 접속"
echo "2. /logs/ 또는 /error_log/ 디렉토리 확인"
echo "3. 또는 view_logs.php 페이지에서 확인"
echo "   https://rofan.mycafe24.com/tracker/view_logs.php"
echo ""


