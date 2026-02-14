#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
세션을 사용한 fetch 테스트 스크립트
"""

import sys
import os

# GCP_CRAWLER.py의 함수들을 import하기 위해 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# GCP_CRAWLER.py에서 필요한 함수들 import
from urllib.parse import urlparse

# 간단한 테스트
test_urls = [
    "https://sexbam42.top/index.php?mid=sschkiss&category=159596652&document_srl=346127738",
    "https://sexbam42.top/index.php?mid=sschkiss&category=12782286&document_srl=362022979"
]

print("Testing URL parsing...")
for url in test_urls:
    parsed = urlparse(url)
    print(f"URL: {url}")
    print(f"  Domain: {parsed.netloc}")
    print(f"  Is sexbam42.top: {'sexbam42.top' in parsed.netloc}")
    print(f"  Should use session: {'sexbam42.top' in parsed.netloc or 'sexbam41.top' in parsed.netloc}")
    print()





