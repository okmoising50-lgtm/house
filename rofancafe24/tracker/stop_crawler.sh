#!/bin/bash
# 크롤러 중지 스크립트

cd /root/mailcenter/sound

if [ -f crawler.pid ]; then
    PID=$(cat crawler.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        echo "크롤러를 중지했습니다. (PID: $PID)"
        rm crawler.pid
    else
        echo "프로세스가 실행 중이 아닙니다."
        rm crawler.pid
    fi
else
    # PID 파일이 없으면 프로세스 이름으로 찾아서 종료
    pkill -f GCP_CRAWLER.py
    echo "크롤러 프로세스를 종료했습니다."
fi





