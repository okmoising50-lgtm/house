# 웹 모니터링 시스템 (카페24 + GCP)

## 🏗️ 시스템 구조

```
┌─────────────────────────────┐
│  카페24 호스팅               │
│  - 관리자 페이지             │
│  - 변화 로그 페이지          │
│  - MariaDB 데이터베이스      │
│  - API (external_api.php)   │
└─────────────────────────────┘
         ↑
         │ HTTPS API
         ↓
┌─────────────────────────────┐
│  GCP 서버                    │
│  - GCP_CRAWLER.py           │
│  - 5초 간격 크롤링           │
└─────────────────────────────┘
```

## 📦 설치 방법

### 1. 카페24 설정

#### 1-1. 파일 업로드
FTP로 `tracker` 폴더 전체를 업로드:
```
/public_html/tracker/
├── index.html
├── admin.html
├── logs.html
├── config.php
├── monitor_lib.php
├── database.sql
└── api/
    ├── external_api.php
    ├── get_sites.php
    ├── get_changes.php
    └── ...
```

#### 1-2. 데이터베이스 설정
1. 카페24 phpMyAdmin 접속
2. `database.sql` 파일 내용 복사
3. SQL 탭에서 실행

#### 1-3. config.php 수정
```php
define('DB_HOST', 'localhost');
define('DB_USER', 'rofan');
define('DB_PASS', 'your_db_password');  // ← 수정
define('DB_NAME', 'rofan');

define('API_TOKEN', 'your-secret-token-here');  // ← 보안 토큰 생성
define('ALLOWED_IPS', ['45.120.69.179', '127.0.0.1']);  // GCP IP 추가
```

### 2. GCP 서버 설정

#### 2-1. 파일 업로드
```bash
# GCP 서버에 접속
cd /root/mailcenter/sound

# 파일 복사 (로컬에서 GCP로)
# tracker/GCP_CRAWLER.py 파일을 GCP 서버로 업로드
```

#### 2-2. Python 패키지 설치
```bash
pip3 install requests beautifulsoup4 lxml
```

#### 2-3. 크롤러 설정
`GCP_CRAWLER.py` 파일 수정:
```python
CAFE24_API_URL = 'https://rofan.mycafe24.com/tracker/api/external_api.php'
API_TOKEN = 'your-secret-token-here'  # config.php와 동일하게
```

#### 2-4. 실행
```bash
# 테스트 실행
python3 GCP_CRAWLER.py

# 백그라운드 실행
nohup python3 GCP_CRAWLER.py > crawler.log 2>&1 &

# 프로세스 확인
ps aux | grep GCP_CRAWLER

# 로그 확인
tail -f crawler.log
```

## 🌐 사용 방법

### 웹 접속
```
https://rofan.mycafe24.com/tracker/          ← 메인 페이지
https://rofan.mycafe24.com/tracker/admin.html   ← 관리자 페이지
https://rofan.mycafe24.com/tracker/logs.html    ← 변화 로그
```

### 사이트 추가
1. 관리자 페이지 접속
2. "새 사이트 추가" 클릭
3. 정보 입력:
   - 사이트 이름
   - URL
   - CSS 선택자 (예: body, #main, .content)
   - 체크 주기: **5초** (GCP 크롤러가 5초 간격으로 실행)
4. 저장

### 변화 확인
- 변화 로그 페이지에서 실시간 확인
- 변경사항은 녹색(추가) / 빨강(삭제)로 표시

## 🔒 보안

### API 토큰 생성 (권장)
```bash
# 랜덤 토큰 생성
openssl rand -hex 32
```

생성된 토큰을:
- `config.php`의 `API_TOKEN`에 입력
- `GCP_CRAWLER.py`의 `API_TOKEN`에 동일하게 입력

### IP 화이트리스트
`config.php`의 `ALLOWED_IPS`에 GCP 서버 IP만 추가

## 📊 데이터베이스 테이블

- `monitor_sites`: 모니터링 사이트 목록
- `monitor_snapshots`: 페이지 스냅샷
- `monitor_changes`: 변화 감지 로그
- `monitor_redirects`: URL 리다이렉트 히스토리

## 🔧 문제 해결

### 크롤러가 작동하지 않음
```bash
# 로그 확인
tail -f crawler.log

# API 토큰 확인
# config.php와 GCP_CRAWLER.py의 API_TOKEN이 동일한지 확인

# IP 확인
curl ifconfig.me  # GCP 서버 IP 확인
```

### DB 연결 오류
- `config.php`의 DB 정보 확인
- phpMyAdmin에서 DB 연결 테스트

## 💡 특징

✅ **5초 간격 크롤링** - GCP 서버에서 무제한 실행
✅ **카페24에서 관리** - 소스 보안 유지
✅ **실시간 변화 감지** - 즉시 알림
✅ **자동 리다이렉트 추적** - URL 변경 자동 감지
✅ **다중 사이트 모니터링** - 30개 이상 가능

## 📞 지원

문제 발생 시:
1. `logs/monitor_*.log` 확인 (카페24)
2. `crawler.log` 확인 (GCP)
3. API 토큰 및 IP 확인

---

**버전**: 1.0.0  
**개발일**: 2025.11.15


