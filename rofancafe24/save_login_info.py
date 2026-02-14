#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로그인 정보를 파일로 저장 (참고용)
실제 세션은 로그인 후 쿠키로 관리됩니다.
"""

import json
import os
from datetime import datetime

# 사용자가 제공한 로그인 정보
login_info = {
    'login_url': 'https://sexbam42.top/index.php?mid=main_04&act=dispMemberLoginForm',
    'login_endpoint': 'https://sexbam42.top/index.php?mid=main_04&module=member&act=procMemberLogin',
    'login_params': {
        'error_return_url': '/index.php?mid=main_04&act=dispMemberLoginForm',
        'mid': 'main_04',
        'vid': '',
        'module': 'member',
        'act': 'procMemberLogin',
        'redirect_url': 'https://sexbam42.top/main_04',
        'user_id': 'lsh90to',
        'password': 'rlaalsvlf1!',
        'keep_signed': 'Y'
    },
    'note': 'cf-turnstile-response와 g-recaptcha-response는 일회성 토큰이므로 재사용 불가',
    'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
}

# rofancafe24 폴더에 저장
script_dir = os.path.dirname(os.path.abspath(__file__))
login_file = os.path.join(script_dir, 'sexbam_login_info.json')

with open(login_file, 'w', encoding='utf-8') as f:
    json.dump(login_info, f, ensure_ascii=False, indent=2)

print(f"로그인 정보가 저장되었습니다: {login_file}")
print("\n주의: 이 정보는 참고용입니다.")
print("실제 세션은 로그인 후 서버가 발급하는 쿠키입니다.")
print("세션을 얻으려면 get_session_from_browser.py를 실행하세요.")






