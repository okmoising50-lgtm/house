#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP_CRAWLER.py를 GCP 서버로 자동 업로드하는 스크립트
파일 저장 시 자동으로 실행되도록 설정 가능
"""

import paramiko
import os
import sys

# 서버 정보
HOST = "45.120.69.179"
PORT = 22
USERNAME = "root"
PASSWORD = "dptmxldps12@@"

# 파일 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_FILE = os.path.join(SCRIPT_DIR, "tracker", "GCP_CRAWLER.py")
REMOTE_PATH = "/root/mailcenter/sound/GCP_CRAWLER.py"

def upload_file():
    """SFTP를 통해 파일 업로드"""
    if not os.path.exists(LOCAL_FILE):
        print(f"✗ 파일을 찾을 수 없습니다: {LOCAL_FILE}")
        return False
    
    try:
        print(f"Uploading {LOCAL_FILE} to {HOST}:{REMOTE_PATH}...")
        
        # SSH 클라이언트 생성
        transport = paramiko.Transport((HOST, PORT))
        transport.connect(username=USERNAME, password=PASSWORD)
        
        # SFTP 클라이언트 생성
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # 파일 업로드
        sftp.put(LOCAL_FILE, REMOTE_PATH)
        
        # 연결 종료
        sftp.close()
        transport.close()
        
        print(f"✓ 업로드 성공!")
        return True
        
    except Exception as e:
        print(f"✗ 업로드 실패: {str(e)}")
        return False

if __name__ == "__main__":
    success = upload_file()
    sys.exit(0 if success else 1)

