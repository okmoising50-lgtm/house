#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright로 브라우저를 열고 example.com에 접속하여 제목 가져오기
"""

from playwright.sync_api import sync_playwright

def get_page_title():
    """브라우저를 열고 example.com에 접속하여 제목 가져오기"""
    with sync_playwright() as p:
        # 브라우저 실행 (headless=False로 화면에 표시)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        url = "https://example.com"
        print(f"접속 중: {url}")
        
        # 페이지 접속
        page.goto(url, wait_until="networkidle")
        
        # 제목 가져오기
        title = page.title()
        print(f"\n✓ 페이지 제목: {title}")
        
        # 현재 URL 확인
        current_url = page.url
        print(f"✓ 현재 URL: {current_url}")
        
        # 페이지 내용 일부 확인
        body_text = page.query_selector('body').inner_text()[:200]
        print(f"✓ 페이지 내용 (처음 200자): {body_text}...")
        
        # 브라우저를 잠시 유지 (확인용)
        print("\n브라우저를 3초 후에 닫습니다...")
        import time
        time.sleep(3)
        
        browser.close()
        
        return title

if __name__ == "__main__":
    try:
        title = get_page_title()
        print(f"\n✓ 완료! 제목: {title}")
    except Exception as e:
        print(f"\n✗ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

