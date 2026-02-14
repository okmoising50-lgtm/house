#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
헤더에서 가져온 쿠키를 세션 파일로 저장
"""

import sys
import io
import json
import os
from datetime import datetime
from urllib.parse import urlparse

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 사용자가 제공한 쿠키 문자열
cookie_string = "PHPSESSID=tqd0pp01s6erf8s33i22o0uk14; mobile=true; user-agent=eedaa60e969370e91b9488b164466966; cf_clearance=1yL5TD8JgA9UXpH6A6Ty6Ccdc1z9O0ye.tGBIMhNrmM-1766941116-1.2.1.1-Oy4NMMbjsZ.rGDjWpPGDxLMnyFuUPmkmuBESV9zyWDnKeaWdq8OmmicJSRs.VvUttnTGcKU6gD41v362oJA.nYDxSFsNcxWZ8ihglNEt5joKBZ6EAPudoWBkcvxEjbJHlTSxPQu_RpJu8qA9FddTtXZqUH801d1NEv_ZbSX2KKRH2zL25_5VuDDMdT4Y1oeA7Uir_jiaukYLuu._LsM8maBe6IJ7eaKugArtbgOQffg"

origin = "https://sexbam42.top"
domain = urlparse(origin).netloc

# 쿠키 문자열을 파싱하여 Playwright/requests 형식으로 변환
cookies = []
for cookie_pair in cookie_string.split('; '):
    if '=' in cookie_pair:
        name, value = cookie_pair.split('=', 1)
        cookies.append({
            'name': name,
            'value': value,
            'domain': domain,
            'path': '/',
            'httpOnly': True,
            'secure': True,
            'sameSite': 'Lax'
        })

# 세션 정보 저장
session_data = {
    'url': origin,
    'domain': domain,
    'cookies': cookies,
    'cookie_string': cookie_string,  # 원본 쿠키 문자열도 저장
    'origin': origin,
    'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'note': '헤더에서 추출한 세션 쿠키'
}

# rofancafe24 폴더에 저장
script_dir = os.path.dirname(os.path.abspath(__file__))
session_file = os.path.join(script_dir, 'sexbam_session.json')

with open(session_file, 'w', encoding='utf-8') as f:
    json.dump(session_data, f, ensure_ascii=False, indent=2)

print(f"[OK] 세션이 저장되었습니다: {session_file}")
print(f"\n[OK] 저장된 쿠키:")
for cookie in cookies:
    name = cookie['name']
    value = cookie['value']
    print(f"  - {name}: {value[:80]}...")

print(f"\n[INFO] 총 {len(cookies)}개의 쿠키가 저장되었습니다.")
print(f"[INFO] cf_clearance 쿠키가 포함되어 있어 Cloudflare 우회가 가능합니다.")






