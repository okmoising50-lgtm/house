#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright로 브라우저를 열고 로그인 후 세션 저장
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
import time

def save_session():
    """브라우저를 열고 로그인 후 세션 저장"""
    url = "https://sexbam43.top/index.php?mid=main_04&act=dispMemberLoginForm"
    
    with sync_playwright() as p:
        # Firefox 브라우저 실행 (headless=False로 화면에 표시)
        print("Firefox 브라우저를 실행합니다...")
        browser = p.firefox.launch(headless=False)
        
        # Cloudflare 우회를 위한 설정
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
            viewport={'width': 1920, 'height': 1080},
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            permissions=['geolocation'],
            extra_http_headers={
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        page = context.new_page()
        
        print(f"접속 중: {url}")
        # Cloudflare 체크를 기다리기 위해 더 긴 타임아웃 설정
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Cloudflare 체크가 완료될 때까지 대기
        print("Cloudflare 체크 대기 중...")
        import time
        time.sleep(5)  # Cloudflare JavaScript 실행 대기
        
        print("\n" + "="*50)
        print("로그인 페이지가 열렸습니다.")
        print("브라우저에서 로그인을 완료해주세요.")
        print("로그인 완료를 감지하는 중...")
        print("="*50)
        
        # 로그인 완료 감지 (URL이 변경되거나 특정 요소가 나타날 때까지 대기)
        login_detected = False
        initial_url = page.url
        max_wait_time = 300  # 최대 5분 대기
        start_time = time.time()
        
        while not login_detected and (time.time() - start_time) < max_wait_time:
            try:
                current_url = page.url
                # URL이 변경되었거나 로그인 폼이 사라졌는지 확인
                if current_url != initial_url or not page.query_selector('input[type="password"]'):
                    login_detected = True
                    break
                time.sleep(2)
            except:
                time.sleep(2)
        
        if not login_detected:
            print("\n로그인 완료를 감지하지 못했습니다.")
            print("수동으로 확인 후 브라우저를 닫지 말고 스크립트를 종료하세요 (Ctrl+C)")
            # 브라우저를 열어둔 채로 대기
            try:
                while True:
                    time.sleep(5)
                    # 쿠키가 있는지 확인
                    cookies = context.cookies()
                    if len(cookies) > 0:
                        print("쿠키가 감지되었습니다. 세션을 저장합니다...")
                        break
            except KeyboardInterrupt:
                print("\n세션 저장 중...")
        
        # 현재 URL 확인
        current_url = page.url
        print(f"\n현재 URL: {current_url}")
        
        # 쿠키 가져오기
        cookies = context.cookies()
        print(f"\n쿠키 개수: {len(cookies)}")
        
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
            print(f"[OK] 저장된 쿠키:")
            for cookie in cookies:
                print(f"  - {cookie.get('name', 'N/A')}: {cookie.get('value', 'N/A')[:50]}...")
        else:
            print("\n[ERROR] 쿠키를 찾을 수 없습니다. 로그인이 완료되었는지 확인해주세요.")
        
        # 브라우저를 열어둔 채로 유지 (사용자가 확인할 수 있도록)
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
        save_session()
    except KeyboardInterrupt:
        print("\n\n사용자가 중단했습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

