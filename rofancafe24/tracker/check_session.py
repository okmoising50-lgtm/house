#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
세션 파일 확인 및 테스트 스크립트
"""

import os
import json
import sys

# GCP_CRAWLER.py와 동일한 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(SCRIPT_DIR, 'sexbam_session.json')

if not os.path.exists(SESSION_FILE):
    PARENT_DIR = os.path.dirname(SCRIPT_DIR)
    SESSION_FILE = os.path.join(PARENT_DIR, 'sexbam_session.json')

print(f"Session file path: {SESSION_FILE}")
print(f"Session file exists: {os.path.exists(SESSION_FILE)}")

if os.path.exists(SESSION_FILE):
    try:
        with open(SESSION_FILE, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        print(f"\nSession data loaded successfully:")
        print(f"  Domain: {session_data.get('domain', 'N/A')}")
        print(f"  Cookies count: {len(session_data.get('cookies', []))}")
        print(f"  Cookie string: {session_data.get('cookie_string', 'N/A')[:100]}...")
        print(f"  Saved at: {session_data.get('saved_at', 'N/A')}")
        
        if session_data.get('headers'):
            print(f"\nHeaders:")
            for key, value in session_data['headers'].items():
                print(f"  - {key}: {value[:80]}...")
        
        if session_data.get('cookies'):
            print(f"\nCookies:")
            for cookie in session_data['cookies']:
                print(f"  - {cookie.get('name')}: {cookie.get('value')[:50]}... (domain: {cookie.get('domain')})")
    except Exception as e:
        print(f"Error loading session file: {str(e)}")
        import traceback
        traceback.print_exc()
else:
    print(f"\nSession file not found!")
    print(f"Please make sure sexbam_session.json is in:")
    print(f"  - {SCRIPT_DIR}")
    print(f"  - {os.path.dirname(SCRIPT_DIR)}")

