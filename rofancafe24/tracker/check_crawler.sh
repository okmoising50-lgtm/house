#!/bin/bash
# 크롤러 상태 확인 스크립트

cd /root/mailcenter/sound || {
    echo "오류: /root/mailcenter/sound 디렉토리로 이동할 수 없습니다."
    exit 1
}

echo "크롤러 상태 확인"
echo "=========================================="

# PID 파일 확인
if [ -f "crawler.pid" ]; then
    PID=$(cat crawler.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "✓ 크롤러가 실행 중입니다. PID: $PID"
    else
        echo "✗ PID 파일은 있지만 프로세스가 실행 중이 아닙니다."
        rm crawler.pid
    fi
else
    # PID 파일이 없으면 프로세스 이름으로 확인
    if pgrep -f GCP_CRAWLER.py > /dev/null; then
        PID=$(pgrep -f GCP_CRAWLER.py | head -1)
        echo "✓ 크롤러가 실행 중입니다. PID: $PID (PID 파일 없음)"
    else
        echo "✗ 크롤러가 실행 중이 아닙니다."
    fi
fi

echo ""
echo "최근 로그 (마지막 20줄):"
echo "=========================================="
if [ -f "crawler.log" ]; then
    tail -20 crawler.log
else
    echo "로그 파일이 없습니다."
fi
