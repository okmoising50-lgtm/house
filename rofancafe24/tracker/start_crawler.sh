#!/bin/bash
# 크롤러 시작 스크립트

echo "크롤러 시작 중..."

# 기존 프로세스 종료
pkill -f GCP_CRAWLER.py
sleep 2

# 크롤러 디렉토리로 이동
cd /root/mailcenter/sound || {
    echo "오류: /root/mailcenter/sound 디렉토리로 이동할 수 없습니다."
    exit 1
}

# 파일 존재 확인
if [ ! -f "GCP_CRAWLER.py" ]; then
    echo "오류: GCP_CRAWLER.py 파일을 찾을 수 없습니다."
    echo "현재 디렉토리: $(pwd)"
    exit 1
fi

# Python3 경로 확인
PYTHON3=$(which python3)
if [ -z "$PYTHON3" ]; then
    echo "오류: python3를 찾을 수 없습니다."
    exit 1
fi

echo "Python3 경로: $PYTHON3"
echo "작업 디렉토리: $(pwd)"

# 기존 로그 파일 백업 (선택사항)
if [ -f "crawler.log" ]; then
    mv crawler.log "crawler.log.$(date +%Y%m%d_%H%M%S)"
fi

# 백그라운드로 실행
nohup $PYTHON3 GCP_CRAWLER.py > crawler.log 2>&1 &

# 프로세스 ID 저장
PID=$!
echo $PID > crawler.pid

# 프로세스가 실행 중인지 확인
sleep 1
if ps -p $PID > /dev/null 2>&1; then
    echo "✓ 크롤러가 시작되었습니다. PID: $PID"
    echo ""
    echo "실시간 로그를 보려면 다음 명령어를 실행하세요:"
    echo "  tail -f crawler.log"
    echo ""
    echo "또는:"
    echo "  cd /root/mailcenter/sound && tail -f crawler.log"
else
    echo "✗ 크롤러 시작 실패. 로그를 확인하세요:"
    echo "  tail -20 crawler.log"
    exit 1
fi
