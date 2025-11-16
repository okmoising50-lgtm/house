#!/bin/bash
# 크롤러 상태 진단 스크립트

echo "=========================================="
echo "크롤러 상태 진단"
echo "=========================================="
echo ""

echo "1. 크롤러 프로세스 확인:"
ps aux | grep GCP_CRAWLER.py | grep -v grep
if [ $? -ne 0 ]; then
    echo "   ✗ 크롤러가 실행 중이지 않습니다!"
else
    echo "   ✓ 크롤러가 실행 중입니다"
fi
echo ""

echo "2. 로그 파일 존재 확인:"
if [ -f /root/mailcenter/sound/crawler.log ]; then
    echo "   ✓ 로그 파일 존재: /root/mailcenter/sound/crawler.log"
    echo "   파일 크기: $(ls -lh /root/mailcenter/sound/crawler.log | awk '{print $5}')"
else
    echo "   ✗ 로그 파일이 없습니다: /root/mailcenter/sound/crawler.log"
fi
echo ""

echo "3. 최근 로그 확인 (마지막 20줄):"
if [ -f /root/mailcenter/sound/crawler.log ]; then
    tail -20 /root/mailcenter/sound/crawler.log
else
    echo "   로그 파일이 없습니다"
fi
echo ""

echo "4. 로그 파일의 마지막 수정 시간:"
if [ -f /root/mailcenter/sound/crawler.log ]; then
    ls -lh /root/mailcenter/sound/crawler.log | awk '{print "   마지막 수정: " $6 " " $7 " " $8}'
else
    echo "   로그 파일이 없습니다"
fi
echo ""

echo "5. 오늘 날짜의 로그 확인:"
TODAY=$(date +%Y-%m-%d)
if [ -f /root/mailcenter/sound/crawler.log ]; then
    COUNT=$(grep -c "$TODAY" /root/mailcenter/sound/crawler.log 2>/dev/null || echo "0")
    echo "   오늘 날짜($TODAY) 로그 라인 수: $COUNT"
    if [ "$COUNT" -gt 0 ]; then
        echo "   오늘 첫 로그:"
        grep "$TODAY" /root/mailcenter/sound/crawler.log | head -1
        echo "   오늘 마지막 로그:"
        grep "$TODAY" /root/mailcenter/sound/crawler.log | tail -1
    fi
else
    echo "   로그 파일이 없습니다"
fi
echo ""

echo "6. 에러 로그 확인:"
if [ -f /root/mailcenter/sound/crawler.log ]; then
    ERROR_COUNT=$(grep -ci "error\|exception\|failed\|✗" /root/mailcenter/sound/crawler.log 2>/dev/null || echo "0")
    echo "   에러 로그 개수: $ERROR_COUNT"
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo "   최근 에러 로그 (마지막 5개):"
        grep -i "error\|exception\|failed\|✗" /root/mailcenter/sound/crawler.log | tail -5
    fi
else
    echo "   로그 파일이 없습니다"
fi
echo ""

echo "7. 크롤러 디렉토리 확인:"
cd /root/mailcenter/sound
pwd
ls -la GCP_CRAWLER.py 2>/dev/null || echo "   ✗ GCP_CRAWLER.py 파일이 없습니다"
echo ""

echo "8. Python 버전 확인:"
python3 --version
echo ""

echo "=========================================="
echo "진단 완료"
echo "=========================================="

