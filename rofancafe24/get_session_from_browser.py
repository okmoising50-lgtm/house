#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
현재 브라우저에서 세션 쿠키 가져오기
"""

import sys
import io

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from playwright.sync_api import sync_playwright
import json
import os
from datetime import datetime

def get_session_from_browser():
    """연결된 브라우저에서 세션 가져오기"""
    url = "https://sexbam42.top/main_04"
    
    with sync_playwright() as p:
        # 기존 브라우저에 연결하거나 새로 열기
        print("브라우저를 실행합니다...")
        browser = p.firefox.launch(
            headless=False,
            args=['--remote-debugging-port=9222']  # 디버깅 포트 열기
        )
        
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
            viewport={'width': 1920, 'height': 1080},
            locale='ko-KR',
            timezone_id='Asia/Seoul',
        )
        
        page = context.new_page()
        
        print(f"접속 중: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        print("\n브라우저가 열렸습니다.")
        print("이미 로그인된 상태라면, 페이지가 로드될 것입니다.")
        print("로그인되지 않았다면 로그인해주세요.")
        print("\n5초 후 쿠키를 확인합니다...")
        import time
        time.sleep(5)
        
        # 쿠키 가져오기
        cookies = context.cookies()
        current_url = page.url
        
        print(f"\n현재 URL: {current_url}")
        print(f"쿠키 개수: {len(cookies)}")
        
        if cookies:
            # 세션 정보 저장
            session_data = {
                'url': current_url,
                'cookies': cookies,
                'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # rofancafe24 폴더에 저장
            script_dir = os.path.dirname(os.path.abspath(__file__))
            session_file = os.path.join(script_dir, 'sexbam_session.json')
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n[OK] 세션이 저장되었습니다: {session_file}")
            print(f"\n[OK] 저장된 쿠키:")
            for cookie in cookies:
                name = cookie.get('name', 'N/A')
                value = cookie.get('value', 'N/A')
                domain = cookie.get('domain', 'N/A')
                print(f"  - {name} ({domain}): {value[:80]}...")
        else:
            print("\n[ERROR] 쿠키를 찾을 수 없습니다.")
        
        print("\n브라우저를 열어둡니다. 확인 후 브라우저를 직접 닫으세요.")
        print("스크립트를 종료하려면 Ctrl+C를 누르세요.")
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n브라우저를 닫습니다...")
            browser.close()
            print("완료!")

if __name__ == "__main__":
    try:
        get_session_from_browser()
    except KeyboardInterrupt:
        print("\n\n사용자가 중단했습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()






