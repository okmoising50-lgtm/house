# GCP_CRAWLER.py 자동 업로드 가이드

## 방법 1: VS Code 명령 팔레트 사용 (가장 간단)

1. `tracker/GCP_CRAWLER.py` 파일을 열고 수정
2. `Ctrl+Shift+P` (또는 `F1`) 눌러서 명령 팔레트 열기
3. `SFTP: Upload Active File` 입력
4. 서버 선택 (stnonecall 또는 직접 입력)

## 방법 2: Python 스크립트 사용 (자동화)

### 설치
```bash
pip install paramiko
```

### 사용
```bash
python upload_to_gcp.py
```

### VS Code에서 파일 저장 시 자동 실행 설정

1. VS Code 확장 설치: **"Run on Save"** (emeraldwalk.RunOnSave)
2. `.vscode/settings.json`에 다음 추가:
```json
{
  "emeraldwalk.runonsave": {
    "commands": [
      {
        "match": "tracker/GCP_CRAWLER.py",
        "cmd": "python ${workspaceFolder}/upload_to_gcp.py"
      }
    ]
  }
}
```

## 방법 3: 키보드 단축키 사용

1. `tracker/GCP_CRAWLER.py` 파일 열기
2. `Ctrl+Shift+U` 누르기 (설정된 단축키)
3. 서버 선택

## 방법 4: WinSCP 사용 (Windows)

WinSCP가 설치되어 있다면:
```powershell
winscp.exe /command "open sftp://root:dptmxldps12@@@45.120.69.179" "put tracker\GCP_CRAWLER.py /root/mailcenter/sound/GCP_CRAWLER.py" "exit"
```

## 추천 방법

**가장 간단**: 방법 1 (VS Code 명령 팔레트)
**가장 자동화**: 방법 2 (Run on Save 확장 사용)

