# 크롤러 실행 가이드

## 빠른 시작

### 1. 크롤러 시작
```bash
cd /root/mailcenter/sound
chmod +x start_crawler.sh
./start_crawler.sh
```

### 2. 실시간 로그 보기
```bash
# 방법 1: 별도 터미널에서
cd /root/mailcenter/sound
tail -f crawler.log

# 방법 2: 스크립트 사용
chmod +x view_logs.sh
./view_logs.sh
```

### 3. 크롤러 상태 확인
```bash
chmod +x check_crawler.sh
./check_crawler.sh
```

### 4. 크롤러 중지
```bash
chmod +x stop_crawler.sh
./stop_crawler.sh
```

## 수동 실행 방법

### 백그라운드 실행 (로그 파일로 저장)
```bash
cd /root/mailcenter/sound
pkill -f GCP_CRAWLER.py
nohup python3 GCP_CRAWLER.py > crawler.log 2>&1 &
```

### 실시간 로그 보기
```bash
cd /root/mailcenter/sound
tail -f crawler.log
```

### 프로세스 확인
```bash
ps aux | grep GCP_CRAWLER.py
```

### 프로세스 종료
```bash
pkill -f GCP_CRAWLER.py
# 또는
kill $(pgrep -f GCP_CRAWLER.py)
```

## 문제 해결

### "명령을 찾을 수 없습니다" 오류
```bash
# Python3 경로 확인
which python3

# Python3가 없으면 설치
yum install python3 -y  # CentOS/RHEL
# 또는
apt-get install python3 -y  # Ubuntu/Debian
```

### 로그 파일이 잘렸을 때
```bash
# 로그 파일 확인
ls -lh crawler.log

# 로그 파일이 너무 크면 백업 후 새로 시작
mv crawler.log crawler.log.backup
```

### 프로세스가 시작되지 않을 때
```bash
# 에러 로그 확인
tail -50 crawler.log

# Python 스크립트 직접 실행해서 에러 확인
cd /root/mailcenter/sound
python3 GCP_CRAWLER.py
```

## 유용한 명령어

### 로그 실시간 모니터링 (색상 포함)
```bash
tail -f crawler.log | grep --color=always -E "ERROR|WARNING|✓|✗|$"
```

### 특정 키워드 검색
```bash
grep "ERROR" crawler.log
grep "CHANGE DETECTED" crawler.log
```

### 로그 파일 크기 확인
```bash
du -h crawler.log
```

### 로그 파일 로테이션 (크기가 너무 클 때)
```bash
# 현재 로그 백업
mv crawler.log crawler.log.$(date +%Y%m%d)

# 크롤러 재시작하면 새 로그 파일 생성됨
```





