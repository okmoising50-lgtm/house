#!/bin/bash
# 실시간 로그 보기 스크립트

cd /root/mailcenter/sound

if [ ! -f crawler.log ]; then
    echo "로그 파일이 없습니다. 크롤러가 실행 중인지 확인하세요."
    exit 1
fi

echo "실시간 로그를 표시합니다. 종료하려면 Ctrl+C를 누르세요."
echo "=========================================="
tail -f crawler.log





