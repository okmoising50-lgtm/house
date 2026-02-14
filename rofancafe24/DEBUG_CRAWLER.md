# 크롤러 디버깅 가이드

## 크롤러가 실행되지 않을 때

### 1. 프로세스 확인
```bash
ps aux | grep GCP_CRAWLER.py
```

### 2. 직접 실행해서 에러 확인
```bash
cd /root/mailcenter/sound
python3 GCP_CRAWLER.py
```

### 3. Python 버전 확인
```bash
python3 --version
```

### 4. 필요한 패키지 설치 확인
```bash
pip3 list | grep -E "requests|beautifulsoup4|lxml"
```

필요한 패키지가 없으면:
```bash
pip3 install requests beautifulsoup4 lxml
```

### 5. 로그 파일 확인
```bash
# 로그 파일 크기 확인
ls -lh crawler.log

# 로그 파일 내용 확인
cat crawler.log

# 에러만 확인
grep -i error crawler.log
```

### 6. 크롤러 재시작 (에러 확인 포함)
```bash
# 기존 프로세스 종료
pkill -f GCP_CRAWLER.py

# 직접 실행 (에러 확인)
cd /root/mailcenter/sound
python3 GCP_CRAWLER.py

# 정상 작동하면 Ctrl+C로 종료하고 백그라운드 실행
nohup python3 GCP_CRAWLER.py > crawler.log 2>&1 &
```

### 7. 실시간 로그 확인
```bash
tail -f crawler.log
```

### 8. 일반적인 문제

#### Import 에러
```bash
# 에러: ModuleNotFoundError: No module named 'bs4'
pip3 install beautifulsoup4

# 에러: ModuleNotFoundError: No module named 'lxml'
pip3 install lxml
```

#### 권한 문제
```bash
# 파일 실행 권한 확인
chmod +x GCP_CRAWLER.py
```

#### 경로 문제
```bash
# 현재 디렉토리 확인
pwd

# 파일 존재 확인
ls -la GCP_CRAWLER.py
```



