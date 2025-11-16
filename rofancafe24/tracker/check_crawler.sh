#!/bin/bash
# 크롤러 상태 확인 스크립트

echo "=== 크롤러 프로세스 확인 ==="
ps aux | grep GCP_CRAWLER.py | grep -v grep

echo ""
echo "=== 최근 크롤러 로그 (마지막 50줄) ==="
if [ -f /root/mailcenter/sound/crawler.log ]; then
    tail -50 /root/mailcenter/sound/crawler.log
else
    echo "로그 파일을 찾을 수 없습니다: /root/mailcenter/sound/crawler.log"
fi

echo ""
echo "=== 크롤러 에러 로그 (마지막 20줄) ==="
if [ -f /root/mailcenter/sound/crawler.log ]; then
    grep -i "error\|exception\|failed\|✗" /root/mailcenter/sound/crawler.log | tail -20
else
    echo "로그 파일을 찾을 수 없습니다"
fi

echo ""
echo "=== 최근 크롤러 활동 (마지막 10줄) ==="
if [ -f /root/mailcenter/sound/crawler.log ]; then
    tail -10 /root/mailcenter/sound/crawler.log
else
    echo "로그 파일을 찾을 수 없습니다"
fi

