#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
웹 페이지 가져오기 관련 함수들
"""

import requests
import io
import os
import json
import re
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime

# SSL 경고 메시지 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 세션 파일 경로 (스크립트와 같은 디렉토리 또는 상위 디렉토리)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(SCRIPT_DIR, 'sexbam_session.json')
# 상위 디렉토리에도 확인
if not os.path.exists(SESSION_FILE):
    PARENT_DIR = os.path.dirname(SCRIPT_DIR)
    SESSION_FILE = os.path.join(PARENT_DIR, 'sexbam_session.json')

def log(message):
    """로그 출력"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", flush=True)

# OCR 라이브러리 (선택적 - 설치되어 있으면 사용)
# 우선순위: pytesseract (가벼움) > easyocr (정확도 높음)
OCR_AVAILABLE = False
ocr_reader = None
ocr_type = None

# 1. pytesseract 시도 (가볍고 메모리 효율적)
try:
    import pytesseract
    from PIL import Image
    log("pytesseract imported successfully")
    # Tesseract가 설치되어 있는지 확인
    try:
        version = pytesseract.get_tesseract_version()
        log(f"Tesseract version detected: {version}")
        OCR_AVAILABLE = True
        ocr_type = 'pytesseract'
        log("OCR initialized successfully (pytesseract)")
    except Exception as e:
        log(f"pytesseract found but tesseract not installed: {str(e)}")
        OCR_AVAILABLE = False
        ocr_type = None
except ImportError as e:
    log(f"pytesseract import failed: {str(e)}")
    pass

# 2. easyocr 시도 (정확도 높지만 메모리 많이 사용)
if not OCR_AVAILABLE:
    try:
        import easyocr
        OCR_AVAILABLE = True
        ocr_type = 'easyocr'
        try:
            log("Initializing OCR (easyocr - Korean + English)...")
            ocr_reader = easyocr.Reader(['ko', 'en'], gpu=False)
            log("OCR initialized successfully (easyocr)")
        except Exception as e:
            log(f"OCR initialization failed: {str(e)}, continuing without OCR")
            OCR_AVAILABLE = False
            ocr_reader = None
            ocr_type = None
    except ImportError:
        pass

if not OCR_AVAILABLE:
    log("No OCR library installed. Image text extraction will be skipped.")
    log("Install option 1 (lightweight): sudo apt-get install tesseract-ocr tesseract-ocr-kor && pip3 install pytesseract pillow")
    log("Install option 2 (accurate but heavy): pip3 install easyocr pillow")

def extract_text_from_image(img_url, headers_fetch):
    """이미지에서 OCR로 텍스트 추출"""
    if not OCR_AVAILABLE:
        log(f"      OCR not available, skipping image text extraction")
        return None
    
    try:
        log(f"      Extracting text from image: {img_url}")
        # 이미지 다운로드
        img_response = requests.get(img_url, headers=headers_fetch, timeout=15, verify=False, allow_redirects=True)
        if img_response.status_code != 200:
            log(f"      Failed to download image: {img_response.status_code}")
            return None
        
        # 이미지 로드
        img = Image.open(io.BytesIO(img_response.content))
        
        # OCR 수행 (라이브러리별로 다르게 처리)
        if ocr_type == 'pytesseract':
            # pytesseract 사용
            try:
                # 한국어 + 영어 지원 시도
                try:
                    text = pytesseract.image_to_string(img, lang='kor+eng')
                except:
                    # 한국어 언어가 없으면 영어만 사용
                    try:
                        text = pytesseract.image_to_string(img, lang='eng')
                        log(f"      Warning: Korean language not available, using English only")
                    except:
                        # 언어 지정 없이 시도
                        text = pytesseract.image_to_string(img)
                        log(f"      Warning: Using default language")
                
                if text and text.strip():
                    full_text = ' '.join(text.strip().split())
                    log(f"      OCR extracted text (pytesseract): {full_text[:100]}...")
                    return full_text
                else:
                    log(f"      No text extracted from image (pytesseract)")
                    return None
            except Exception as e:
                log(f"      pytesseract error: {str(e)}")
                return None
        
        elif ocr_type == 'easyocr' and ocr_reader:
            # easyocr 사용
            try:
                results = ocr_reader.readtext(img)
                extracted_texts = []
                for (bbox, text, confidence) in results:
                    if confidence > 0.3:  # 신뢰도 30% 이상만 사용
                        extracted_texts.append(text.strip())
                
                if extracted_texts:
                    full_text = ' '.join(extracted_texts)
                    log(f"      OCR extracted text (easyocr): {full_text[:100]}...")
                    return full_text
                else:
                    log(f"      No text extracted from image (low confidence)")
                    return None
            except Exception as e:
                log(f"      easyocr error: {str(e)}")
                return None
        else:
            return None
            
    except Exception as e:
        log(f"      OCR error: {str(e)}")
        return None

def remove_unwanted_elements(soup):
    """크롤링에서 제외할 요소 제거 (전광판, 광고 등)"""
    # 제거할 클래스 및 태그 목록
    unwanted_selectors = [
        '.notice_board',       # 전광판
        '.updatenews',         # 업데이트 뉴스 (광고)
        '#sidebar',            # 사이드바
        '.sidebar',
        'header',              # 헤더
        'footer',              # 푸터
        '.footer',
        '#footer',
        '.advertisement',      # 명시적 광고 클래스
        '.ads',
        '.banner'
    ]
    
    for selector in unwanted_selectors:
        for element in soup.select(selector):
            element.decompose()

# 섹밤 로그인 세션 관리
_sexbam_session = None

def load_sexbam_session():
    """섹밤 세션 파일 로드"""
    if not os.path.exists(SESSION_FILE):
        log(f"Session file not found: {SESSION_FILE}")
        return None
    
    try:
        with open(SESSION_FILE, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        cookies = session_data.get('cookies', [])
        cookie_string = session_data.get('cookie_string', '')
        domain = session_data.get('domain', 'sexbam43.top')
        
        if cookies or cookie_string:
            log(f"Loaded sexbam session from file: {len(cookies) if cookies else 0} cookies, domain: {domain}")
            return {
                'cookies': cookies,
                'cookie_string': cookie_string,
                'domain': domain
            }
        else:
            log("Session file exists but contains no cookies")
            return None
    except Exception as e:
        log(f"Error loading session file: {str(e)}")
        return None

def get_sexbam_session():
    """섹밤 로그인 세션 가져오기 (세션 파일 우선 사용)"""
    global _sexbam_session
    
    if _sexbam_session is not None:
        return _sexbam_session
    
    # 새 세션 생성
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    })
    session.verify = False
    
    # 세션 파일에서 쿠키 로드 시도
    session_data = load_sexbam_session()
    if session_data:
        domain = session_data.get('domain', 'sexbam43.top')
        
        # Cloudflare 헤더 추가 (세션 파일에 있는 경우)
        if session_data.get('headers'):
            headers = session_data['headers']
            if 'cf-chl-out' in headers:
                session.headers['cf-chl-out'] = headers['cf-chl-out']
            if 'cf-chl-out-s' in headers:
                session.headers['cf-chl-out-s'] = headers['cf-chl-out-s']
            log(f"    ✓ Loaded Cloudflare challenge headers from session file")
        
        # 쿠키 문자열이 있으면 사용
        if session_data.get('cookie_string'):
            cookie_string = session_data['cookie_string']
            for cookie_pair in cookie_string.split('; '):
                if '=' in cookie_pair:
                    name, value = cookie_pair.split('=', 1)
                    name = name.strip()
                    value = value.strip()
                    # 도메인 설정 (cf_clearance는 서브도메인 포함)
                    cookie_domain = f'.{domain}' if name == 'cf_clearance' else domain
                    session.cookies.set(name, value, domain=cookie_domain)
            log(f"    ✓ Loaded {len(cookie_string.split('; '))} cookies from session file")
        # 쿠키 객체 리스트가 있으면 사용
        elif session_data.get('cookies'):
            for cookie in session_data['cookies']:
                name = cookie.get('name')
                value = cookie.get('value')
                cookie_domain = cookie.get('domain', domain)
                if name and value:
                    session.cookies.set(name, value, domain=cookie_domain)
            log(f"    ✓ Loaded {len(session_data['cookies'])} cookies from session file")
        
        _sexbam_session = session
        return session
    
    # 세션 파일이 없으면 기존 방식 사용 (하드코딩된 쿠키)
    log("    ⚠ Session file not found, using fallback cookies")
    session.cookies.set('PHPSESSID', 'h7amljjor093c81pjqgdjur723', domain='sexbam43.top')
    session.cookies.set('mobile', 'true', domain='sexbam43.top')
    session.cookies.set('user-agent', 'eedaa60e969370e91b9488b164466966', domain='sexbam43.top')
    session.cookies.set('use_np', 'use_np', domain='sexbam43.top')
    
    _sexbam_session = session
    return session

def has_time_info_in_title(title_text):
    """og:title에 시간 정보가 포함되어 있는지 확인

    시간 패턴 예시:
    - ❤️사랑( 12 1 ) - 괄호 안에 숫자들 (시간)
    - ❤️천예슬( 12 1 2 3 4 5 ) - 여러 시간
    - (1 2 3 4 5 6 7 8 9) - 숫자만 있는 괄호
    """
    if not title_text:
        return False

    # 괄호 안에 숫자(시간)가 있는 패턴 찾기
    # 예: ( 12 1 ), (1 2 3 4 5), ( 12 1 2 3 4 5 )
    time_pattern = re.compile(r'\(\s*\d+(?:\s+\d+)*\s*\)')

    if time_pattern.search(title_text):
        return True

    return False

def fetch_content_sexbam(url, extraction_mode='both'):
    """섹밤 유형 사이트에서 제목, 전화번호, 본문만 추출

    extraction_mode:
    - 'title': og:title에서만 추출 (로그인 불필요)
    - 'both': 제목+본문에서 추출 (로그인 불필요, og:title에 시간 있으면 본문 건너뛰기)
    """
    try:
        log(f"    Fetching URL (섹밤 유형, mode={extraction_mode}): {url}")

        # 먼저 세션 없이 요청해서 og:title 확인
        headers_fetch = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }

        try:
            log(f"    Sending GET request to {url} (섹밤 유형, 세션 없이)...")
            response = requests.get(url, headers=headers_fetch, timeout=30, verify=False)
            log(f"    Response received: status_code={response.status_code}, content_length={len(response.text)}")
        except requests.exceptions.Timeout:
            log(f"    ✗✗✗ TIMEOUT: Request to {url} timed out after 30 seconds (섹밤 유형) ✗✗✗")
            return None
        except requests.exceptions.ConnectionError as e:
            log(f"    ✗✗✗ CONNECTION ERROR: Failed to connect to {url} (섹밤 유형): {str(e)} ✗✗✗")
            return None
        except requests.exceptions.RequestException as e:
            log(f"    ✗✗✗ REQUEST ERROR: {str(e)} (섹밤 유형) ✗✗✗")
            return None

        if response.status_code != 200:
            log(f"    ✗✗✗ HTTP Status: {response.status_code} for {url} (섹밤 유형) ✗✗✗")
            if response.status_code == 403:
                log(f"    → HTTP 403 FORBIDDEN: Access denied (possibly blocked or requires login)")
            elif response.status_code == 404:
                log(f"    → HTTP 404 NOT FOUND: URL may be incorrect")
            elif response.status_code == 429:
                log(f"    → HTTP 429 TOO MANY REQUESTS: Rate limit exceeded")
            elif response.status_code >= 500:
                log(f"    → HTTP {response.status_code} SERVER ERROR: Server error")
            log(f"    Response text (first 500 chars): {response.text[:500]}")
            return None

        soup = BeautifulSoup(response.text, 'lxml')

        # 불필요한 요소 제거 (전광판 등)
        remove_unwanted_elements(soup)

        log(f"    Parsed HTML with BeautifulSoup (섹밤 유형)")

        parts = []

        # 1. 제목 추출: meta property="og:title"에서 추출 (뒤의 " - 출근부 [키스방] - 섹밤" 제거)
        title_text = None
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            full_title = og_title.get('content', '').strip()
            # " - 출근부" 또는 " - 섹밤" 패턴 제거
            if ' - ' in full_title:
                # 마지막 " - " 이후 부분 제거
                title_text = full_title.rsplit(' - ', 1)[0].strip()
            else:
                title_text = full_title

        # extraction_mode='title'이면 무조건 본문 건너뛰기
        # extraction_mode='both'이면 og:title에 시간 정보가 있을 때만 본문 건너뛰기
        if extraction_mode == 'title':
            title_has_time = True  # 본문 추출 건너뛰기
            log(f"    ✓ extraction_mode='title' - 본문 추출 건너뛰기 (로그인 불필요)")
        else:
            title_has_time = has_time_info_in_title(title_text)
            if title_has_time:
                log(f"    ✓ og:title에 시간 정보 있음 - 본문 추출 건너뛰기 (로그인 불필요)")
            else:
                log(f"    ○ og:title에 시간 정보 없음 - 본문 추출 필요")

        # og:title이 없으면 기존 방식으로 시도
        if not title_text:
            rd_hd = soup.select_one('.rd_hd')
            title_elem = None
            if rd_hd:
                title_elem = rd_hd.select_one('h1.np_18px a span')
                if not title_elem:
                    title_elem = rd_hd.select_one('h1.np_18px a')
            else:
                title_elem = soup.select_one('h1.np_18px a span')
                if not title_elem:
                    title_elem = soup.select_one('h1.np_18px a')

            if title_elem:
                title_text = title_elem.get_text(strip=True)

        if title_text:
            parts.append(f"[제목] {title_text}")
            log(f"    Found title: {title_text[:100]}...")
        
        # 2. 전화번호 추출: .rd_body 내부의 table.et_vars tr 중에서 th가 "전화번호"를 포함하는 행의 td
        phone_elem = None
        
        # 방법 1: .rd_body 내부의 table.et_vars에서 찾기
        rd_body_for_phone = soup.select_one('.rd_body')
        if rd_body_for_phone:
            phone_table = rd_body_for_phone.select_one('table.et_vars')
            if phone_table:
                for tr in phone_table.select('tr'):
                    th = tr.select_one('th')
                    if th and '전화번호' in th.get_text():
                        td = tr.select_one('td')
                        if td:
                            phone_text = td.get_text(strip=True)
                            # 전화번호 패턴 추출 (010-1234-5678 형식)
                            phone_match = re.search(r'0\d{1,2}-?\d{3,4}-?\d{4}', phone_text)
                            if phone_match:
                                phone_elem = phone_match.group(0)
                                # 하이픈 정규화
                                phone_elem = re.sub(r'(\d{3})-?(\d{3,4})-?(\d{4})', r'\1-\2-\3', phone_elem)
                                log(f"    Found phone from table.et_vars: {phone_elem}")
                                break
                            elif phone_text:
                                phone_elem = phone_text.strip()
                                log(f"    Found phone from table.et_vars (raw): {phone_elem}")
                                break
        
        # 방법 2: .rd_body가 없거나 전화번호를 못 찾았으면 전체에서 table.et_vars 찾기
        if not phone_elem:
            for tr in soup.select('table.et_vars tr'):
                th = tr.select_one('th')
                if th and '전화번호' in th.get_text():
                    td = tr.select_one('td')
                    if td:
                        phone_text = td.get_text(strip=True)
                        # 전화번호 패턴 추출
                        phone_match = re.search(r'0\d{1,2}-?\d{3,4}-?\d{4}', phone_text)
                        if phone_match:
                            phone_elem = phone_match.group(0)
                            phone_elem = re.sub(r'(\d{3})-?(\d{3,4})-?(\d{4})', r'\1-\2-\3', phone_elem)
                            log(f"    Found phone from table.et_vars (global): {phone_elem}")
                            break
                        elif phone_text:
                            phone_elem = phone_text.strip()
                            log(f"    Found phone from table.et_vars (global, raw): {phone_elem}")
                            break
        
        # 방법 3: 여전히 못 찾았으면 .rd_body 내부에서만 전화번호 패턴 검색 (광고 제외)
        if not phone_elem:
            rd_body_for_phone_fallback = soup.select_one('.rd_body')
            if rd_body_for_phone_fallback:
                # .rd_body 내부의 텍스트에서만 전화번호 찾기 (광고 섹션 제외)
                rd_body_text = rd_body_for_phone_fallback.get_text()
                phone_matches = re.findall(r'0\d{1,2}-?\d{3,4}-?\d{4}', rd_body_text)
                if phone_matches:
                    # 첫 번째 전화번호 사용 (하이픈 정규화)
                    phone_elem = phone_matches[0]
                    phone_elem = re.sub(r'(\d{3})-?(\d{3,4})-?(\d{4})', r'\1-\2-\3', phone_elem)
                    log(f"    Found phone from .rd_body text: {phone_elem}")
        
        if phone_elem:
            parts.append(f"[전화번호] {phone_elem}")
            log(f"    Final phone: {phone_elem}")
        else:
            log(f"    Warning: Phone number not found")
        
        # 3. 본문 추출: og:title에 시간 정보가 있으면 건너뛰기
        body_text = None

        if title_has_time:
            # og:title에 시간 정보가 있으면 본문 추출 불필요
            log(f"    ✓ 본문 추출 건너뛰기 (og:title에 시간 정보 있음)")
        else:
            # og:title에 시간 정보가 없으면 본문 추출 필요 (로그인 세션 사용)
            log(f"    본문 추출 시도 (og:title에 시간 정보 없음)...")

            # 로그인 세션으로 다시 요청
            session = get_sexbam_session()
            try:
                log(f"    Sending GET request with session to {url}...")
                response_with_session = session.get(url, headers=headers_fetch, timeout=30)
                log(f"    Session response: status_code={response_with_session.status_code}, content_length={len(response_with_session.text)}")

                if response_with_session.status_code == 200:
                    soup_with_session = BeautifulSoup(response_with_session.text, 'lxml')
                    remove_unwanted_elements(soup_with_session)

                    # "권한이 없습니다" 체크
                    page_text = soup_with_session.get_text()
                    if '권한이 없습니다' in page_text or '로그인' in page_text[:500]:
                        log(f"    ⚠ 로그인 필요 - 세션이 만료되었거나 유효하지 않음")
                        log(f"    → og:title만 사용합니다")
                    else:
                        # og:description에서 추출 시도
                        og_description = soup_with_session.find('meta', property='og:description')
                        if og_description and og_description.get('content'):
                            body_text = og_description.get('content', '').strip()
                            if not body_text or body_text.isspace():
                                body_text = None
                            else:
                                log(f"    Found body from og:description: {body_text[:100]}...")

                        # og:description이 없거나 비어있으면 article에서 추출
                        if not body_text:
                            log(f"    og:description is empty, trying to extract from article...")
                            rd_body = soup_with_session.select_one('.rd_body')
                            article_elem = None
                            if rd_body:
                                article_elem = rd_body.find('article')
                                log(f"    .rd_body found, article element: {article_elem is not None}")
                            else:
                                log(f"    Warning: .rd_body not found, trying to find article in full HTML...")
                                article_elem = soup_with_session.find('article')

                            if article_elem:
                                content_elem = article_elem.find('div', class_=lambda x: x and 'xe_content' in x)
                                if not content_elem:
                                    content_elem = article_elem
                                    log(f"    Warning: .xe_content not found in article, using article content")
                                else:
                                    log(f"    Found .xe_content div in article")

                                body_text = content_elem.get_text(separator=' ', strip=True)
                                log(f"    Extracted body text from article: {len(body_text)} characters")

                                # 이미지 OCR 처리
                                img_count = 0
                                for img in content_elem.find_all('img'):
                                    img_count += 1
                                    img_text = ''
                                    if img.get('src'):
                                        src = img.get('src').strip()
                                        if src.startswith('/'):
                                            img_url = urljoin(url, src)
                                        elif not src.startswith('http'):
                                            img_url = urljoin(url, src)
                                        else:
                                            img_url = src

                                        ocr_text = extract_text_from_image(img_url, headers_fetch)
                                        if ocr_text:
                                            img_text += f"[이미지{img_count}: {src} OCR:{ocr_text}]"
                                            log(f"    Found image {img_count}: {src} (OCR text: {ocr_text[:50]}...)")
                                        else:
                                            img_text += f"[이미지{img_count}: {src}]"
                                            log(f"    Found image {img_count}: {src} (no OCR text)")

                                    if img.get('alt'):
                                        img_text += f" alt:{img.get('alt')}"
                                    if img.get('title'):
                                        img_text += f" title:{img.get('title')}"

                                    if img_text:
                                        body_text += ' ' + img_text

                                if img_count > 0:
                                    body_text += f" [총이미지수: {img_count}]"
                                    log(f"    Found article content: {len(body_text)} characters, {img_count} images")
                            else:
                                log(f"    Warning: article element not found in .rd_body")

                        # 세션 응답의 HTML 사용
                        response = response_with_session
                else:
                    log(f"    ⚠ Session request failed: HTTP {response_with_session.status_code}")
            except Exception as e:
                log(f"    ⚠ Session request error: {str(e)}")

        if body_text:
            parts.append(f"[본문] {body_text}")
            log(f"    Found body content: {len(body_text)} characters")
        
        # 모든 부분 합치기
        final_text = ' '.join(parts)
        log(f"    Final sexbam content length: {len(final_text)} characters")
        
        return {
            'content': final_text,
            'html': response.text,
            'final_url': response.url
        }
    except Exception as e:
        log(f"Error fetching sexbam content from {url}: {str(e)}")
        import traceback
        log(f"  Traceback: {traceback.format_exc()}")
        return None

def fetch_content_sexbam2(url):
    """섹밤 유형2 사이트에서 data-docSrl 영역 기준으로 제목, 전화번호, 본문 추출"""
    try:
        log(f"    Fetching URL (섹밤 유형2): {url}")
        
        # 섹밤 로그인 세션 가져오기
        session = get_sexbam_session()
        
        # 캐시 방지 헤더
        headers_fetch = {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        
        response = session.get(url, headers=headers_fetch, timeout=30)
        if response.status_code != 200:
            log(f"    ✗✗✗ HTTP Status: {response.status_code} for {url} (섹밤 유형2) ✗✗✗")
            if response.status_code == 403:
                log(f"    → HTTP 403 FORBIDDEN: Access denied (possibly blocked or requires login)")
            elif response.status_code == 404:
                log(f"    → HTTP 404 NOT FOUND: URL may be incorrect")
            elif response.status_code == 429:
                log(f"    → HTTP 429 TOO MANY REQUESTS: Rate limit exceeded")
            elif response.status_code >= 500:
                log(f"    → HTTP {response.status_code} SERVER ERROR: Server error")
            log(f"    Response text (first 500 chars): {response.text[:500]}")
            return None
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        log(f"    Parsed HTML with BeautifulSoup (섹밤 유형2)")
        
        parts = []
        phone_elem = None
        
        # 1. data-docSrl 영역 찾기 (이 영역만 크롤링)
        doc_srl_elem = soup.find(attrs={'data-docsrl': True})
        if not doc_srl_elem:
            # data-docsrl 대소문자 변형 시도
            doc_srl_elem = soup.find(attrs={'data-docSrl': True})
        
        if not doc_srl_elem:
            log(f"    Warning: data-docSrl element not found, falling back to .rd class")
            # .rd 클래스로 대체 시도
            doc_srl_elem = soup.select_one('.rd')
        
        if not doc_srl_elem:
            log(f"    Warning: No suitable container found, using full page")
            doc_srl_elem = soup
        else:
            log(f"    Found data-docSrl container")
        
        # 2. 제목 추출: h1.np_18px 안의 a 태그 텍스트
        title_text = None
        title_elem = doc_srl_elem.select_one('h1.np_18px a')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            log(f"    Found title from h1.np_18px: {title_text[:50]}...")
        else:
            # 대안: h1.np_18px 직접 텍스트
            title_elem = doc_srl_elem.select_one('h1.np_18px')
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                log(f"    Found title from h1.np_18px (direct): {title_text[:50]}...")
        
        if title_text:
            parts.append(f"[제목] {title_text}")
        else:
            log(f"    Warning: Title not found in h1.np_18px")
        
        # 3. 전화번호 추출: table.et_vars (bd_tb 클래스 있을 수도 있음)
        phone_table = doc_srl_elem.select_one('table.et_vars')
        if phone_table:
            for tr in phone_table.select('tr'):
                th = tr.select_one('th')
                if th and '전화번호' in th.get_text():
                    td = tr.select_one('td')
                    if td:
                        phone_text = td.get_text(strip=True)
                        # 전화번호 패턴 추출 (010-1234-5678 형식)
                        phone_match = re.search(r'0\d{1,2}-?\d{3,4}-?\d{4}', phone_text)
                        if phone_match:
                            phone_elem = phone_match.group(0)
                            # 하이픈 정규화
                            phone_elem = re.sub(r'(\d{3})-?(\d{3,4})-?(\d{4})', r'\1-\2-\3', phone_elem)
                            log(f"    Found phone from table.et_vars: {phone_elem}")
                            break
                        elif phone_text:
                            phone_elem = phone_text.strip()
                            log(f"    Found phone from table.et_vars (raw): {phone_elem}")
                            break
        
        if phone_elem:
            parts.append(f"[전화번호] {phone_elem}")
            log(f"    Final phone: {phone_elem}")
        else:
            log(f"    Warning: Phone number not found in table.et_vars")
        
        # 4. 본문 추출: article 내부만 (article 이후는 무시)
        body_text = ""
        article_elem = doc_srl_elem.find('article')
        
        if article_elem:
            log(f"    Found article element")
            
            # article 내부의 .xe_content 찾기
            content_elem = article_elem.find('div', class_=lambda x: x and 'xe_content' in x)
            if content_elem:
                log(f"    Found .xe_content div in article")
            else:
                # .xe_content가 없으면 article 전체 사용
                content_elem = article_elem
                log(f"    Using article content directly")
            
            # 텍스트 추출
            body_text = content_elem.get_text(separator=' ', strip=True)
            log(f"    Extracted body text from article: {len(body_text)} characters")
            
            # 이미지 처리 (OCR)
            img_count = 0
            for img in content_elem.find_all('img'):
                img_count += 1
                img_text = ''
                if img.get('src'):
                    src = img.get('src').strip()
                    if src.startswith('/'):
                        img_url = urljoin(url, src)
                    elif not src.startswith('http'):
                        img_url = urljoin(url, src)
                    else:
                        img_url = src
                    
                    # OCR로 이미지에서 텍스트 추출
                    ocr_text = extract_text_from_image(img_url, headers_fetch)
                    if ocr_text:
                        img_text += f"[이미지{img_count}: {src} OCR:{ocr_text}]"
                        log(f"    Found image {img_count}: {src} (OCR text: {ocr_text[:50]}...)")
                    else:
                        img_text += f"[이미지{img_count}: {src}]"
                        log(f"    Found image {img_count}: {src} (no OCR text)")
                
                if img.get('alt'):
                    img_text += f" alt:{img.get('alt')}"
                if img.get('title'):
                    img_text += f" title:{img.get('title')}"
                
                if img_text:
                    body_text += ' ' + img_text
            
            if img_count > 0:
                body_text += f" [총이미지수: {img_count}]"
                log(f"    Found article content: {len(body_text)} characters, {img_count} images")
        else:
            log(f"    Warning: article element not found")
        
        if body_text:
            parts.append(f"[본문] {body_text}")
            log(f"    Found body content: {len(body_text)} characters")
        
        # 모든 부분 합치기
        final_text = ' '.join(parts)
        log(f"    Final sexbam2 content length: {len(final_text)} characters")
        
        # full_html은 data-docSrl 영역부터 article까지만 저장 (불필요한 부분 제거)
        cleaned_html = ""
        if doc_srl_elem and doc_srl_elem != soup:
            # article까지만 포함된 HTML 생성
            if article_elem:
                cleaned_html = str(doc_srl_elem)
            else:
                cleaned_html = str(doc_srl_elem)
        else:
            cleaned_html = response.text
        
        return {
            'content': final_text,
            'html': cleaned_html,  # data-docSrl 영역만 저장
            'final_url': response.url
        }
    except Exception as e:
        log(f"Error fetching sexbam2 content from {url}: {str(e)}")
        import traceback
        log(f"  Traceback: {traceback.format_exc()}")
        return None

def parse_attendance_from_og_title(title_text):
    """og:title에서 매니저 이름과 시간 추출

    패턴: ❤️이름( 숫자 숫자 ... ) 또는 ❤️이름 ( 숫자 숫자 ... )
    예: ❤️사랑( 12 1 ) → {'name': '사랑', 'times': '12,1'}
    예: ❤️천예슬( 12 1 2 3 4 5 ) → {'name': '천예슬', 'times': '12,1,2,3,4,5'}
    """
    if not title_text:
        return []

    attendance_records = []

    # 패턴: ❤️이름( 숫자들 ) 또는 ❤️이름 ( 숫자들 )
    # 이름에는 한글, 영문, 숫자, 공백 가능
    # 예: ❤️사랑( 12 1 ), ❤️천예슬( 12 1 2 3 4 5 ), ❤️신예나 ( 3 4 5 6 )
    pattern = re.compile(r'❤️\s*([가-힣a-zA-Z0-9]+)\s*\(\s*([\d\s]+)\s*\)')

    matches = pattern.findall(title_text)
    for match in matches:
        name = match[0].strip()
        times_str = match[1].strip()

        # 공백으로 구분된 숫자들을 쉼표로 변환
        times_list = times_str.split()
        times = ','.join(times_list)

        # 제외할 이름 필터링
        excluded_names = ['모집중', '출근부', '매니저', '상시', '구인', 'SBJUSO']
        if name and name not in excluded_names and len(name) >= 2:
            attendance_records.append({
                'name': name,
                'times': times
            })
            log(f"      Parsed: {name} → {times}")

    return attendance_records

def fetch_content_sexbam_title(url):
    """섹밤 유형 - og:title에서만 출근부 추출 (로그인 불필요)

    og:title에서 매니저 이름과 시간만 추출
    본문 추출 없이 제목만 사용하므로 로그인이 필요 없음
    """
    try:
        log(f"    Fetching URL (섹밤-제목만): {url}")

        # 세션 없이 요청 (로그인 불필요)
        headers_fetch = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }

        try:
            log(f"    Sending GET request to {url} (세션 없이)...")
            response = requests.get(url, headers=headers_fetch, timeout=30, verify=False)
            log(f"    Response received: status_code={response.status_code}, content_length={len(response.text)}")
        except requests.exceptions.Timeout:
            log(f"    ✗✗✗ TIMEOUT: Request to {url} timed out ✗✗✗")
            return None
        except requests.exceptions.ConnectionError as e:
            log(f"    ✗✗✗ CONNECTION ERROR: {str(e)} ✗✗✗")
            return None
        except requests.exceptions.RequestException as e:
            log(f"    ✗✗✗ REQUEST ERROR: {str(e)} ✗✗✗")
            return None

        if response.status_code != 200:
            log(f"    ✗✗✗ HTTP Status: {response.status_code} ✗✗✗")
            return None

        soup = BeautifulSoup(response.text, 'lxml')
        log(f"    Parsed HTML with BeautifulSoup (섹밤-제목만)")

        # og:title 추출
        title_text = None
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            full_title = og_title.get('content', '').strip()
            # " - 출근부" 또는 " - 섹밤" 패턴 제거
            if ' - ' in full_title:
                title_text = full_title.rsplit(' - ', 1)[0].strip()
            else:
                title_text = full_title
            log(f"    Found og:title: {title_text[:100]}...")
        else:
            log(f"    ✗ og:title not found")
            return None

        # og:title에서 출근부 데이터 추출
        attendance_records = parse_attendance_from_og_title(title_text)
        if attendance_records:
            log(f"    ✓ Found {len(attendance_records)} attendance records from og:title")
            for record in attendance_records:
                log(f"      - {record['name']}: {record['times']}")
        else:
            log(f"    ○ No attendance records found in og:title")

        # 콘텐츠는 og:title 전체 사용
        final_text = f"[제목] {title_text}"
        log(f"    Final content length: {len(final_text)} characters")

        return {
            'content': final_text,
            'html': response.text,
            'final_url': response.url,
            'attendance_from_title': attendance_records  # 출근부 데이터 직접 전달
        }
    except Exception as e:
        log(f"Error fetching sexbam_title content from {url}: {str(e)}")
        import traceback
        log(f"  Traceback: {traceback.format_exc()}")
        return None

def fetch_content(url, target_selector='body'):
    """URL에서 컨텐츠 가져오기"""
    try:
        log(f"    Fetching URL: {url}")
        log(f"    Using selector: '{target_selector}'")
        
        # sexbam42.top 도메인인 경우 세션 사용
        parsed_url = urlparse(url)
        use_session = 'sexbam43.top' in parsed_url.netloc or 'sexbam42.top' in parsed_url.netloc or 'sexbam41.top' in parsed_url.netloc
        
        if use_session:
            log(f"    Detected sexbam domain ({parsed_url.netloc}), using session with cookies")
            session = get_sexbam_session()
            # 세션 쿠키 확인
            cookie_count = len(session.cookies)
            log(f"    Session has {cookie_count} cookies")
            if cookie_count > 0:
                for cookie in session.cookies:
                    log(f"      - Cookie: {cookie.name} (domain: {cookie.domain})")
        else:
            session = None
            log(f"    Using regular requests (no session)")
        
        # 캐시 방지 헤더 추가
        headers_fetch = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        
        try:
            log(f"    Sending GET request to {url}...")
            if session:
                response = session.get(url, headers=headers_fetch, timeout=30)
            else:
                response = requests.get(url, headers=headers_fetch, timeout=30, verify=False)
            log(f"    Response received: status_code={response.status_code}, content_length={len(response.text)}")
        except requests.exceptions.Timeout:
            log(f"    ✗✗✗ TIMEOUT: Request to {url} timed out after 30 seconds ✗✗✗")
            log(f"    → The server may be slow or unresponsive")
            return None
        except requests.exceptions.ConnectionError as e:
            log(f"    ✗✗✗ CONNECTION ERROR: Failed to connect to {url} ✗✗✗")
            log(f"    → Error details: {str(e)}")
            log(f"    → Possible causes: DNS resolution failed, server is down, or network issue")
            return None
        except requests.exceptions.RequestException as e:
            log(f"    ✗✗✗ REQUEST ERROR: {str(e)} ✗✗✗")
            log(f"    → Request failed for unknown reason")
            return None
        except Exception as e:
            log(f"    ✗✗✗ UNEXPECTED ERROR: {str(e)} ✗✗✗")
            import traceback
            log(f"    Traceback: {traceback.format_exc()}")
            return None
        
        # HTTP 상태 코드별 상세 처리
        if response.status_code == 200:
            log(f"    ✓ HTTP Status: {response.status_code}, Content length: {len(response.text)}")
        elif response.status_code == 403:
            log(f"    ✗✗✗ HTTP 403 FORBIDDEN: Access denied (possibly blocked by server) ✗✗✗")
            log(f"    Response headers: {dict(response.headers)}")
            return None
        elif response.status_code == 429:
            log(f"    ✗✗✗ HTTP 429 TOO MANY REQUESTS: Rate limit exceeded ✗✗✗")
            log(f"    Response headers: {dict(response.headers)}")
            return None
        elif response.status_code == 503:
            log(f"    ✗✗✗ HTTP 503 SERVICE UNAVAILABLE: Server overloaded ✗✗✗")
            return None
        elif response.status_code >= 500:
            log(f"    ✗✗✗ HTTP {response.status_code} SERVER ERROR: Server error ✗✗✗")
            return None
        else:
            log(f"    ✗ HTTP Status: {response.status_code} (unexpected)")
            log(f"    Response text (first 500 chars): {response.text[:500]}")
            return None
            
        # BeautifulSoup으로 파싱
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 불필요한 요소 제거 (전광판 등)
        remove_unwanted_elements(soup)
        
        log(f"    Parsed HTML with BeautifulSoup")
        
        # target_selector가 지정되어 있으면 해당 요소만 선택
        if target_selector and target_selector.strip() and target_selector.strip() != 'body':
            try:
                selected_elements = soup.select(target_selector.strip())
                if selected_elements:
                    log(f"  Found {len(selected_elements)} element(s) with selector '{target_selector}'")
                    # 선택된 요소들의 내용 추출 (텍스트 + 이미지/링크 정보)
                    text_parts = []
                    total_img_count = 0
                    for elem in selected_elements:
                        # 불필요한 부분 제거 (작성자, 날짜, 제목 등)
                        unwanted_classes = ['updatenews_author', 'updatenews_date', 'updatenews_title']
                        for unwanted_class in unwanted_classes:
                            for unwanted_elem in elem.find_all(class_=unwanted_class):
                                unwanted_elem.decompose()
                                log(f"    Removed element with class '{unwanted_class}'")
                        
                        # 텍스트 추출
                        text_content = elem.get_text(separator=' ', strip=True)
                        log(f"    Extracted text length: {len(text_content)} characters (before adding images)")
                        
                        # 이미지 태그의 src, alt 속성도 텍스트로 포함
                        img_count = 0
                        for img in elem.find_all('img'):
                            img_count += 1
                            total_img_count += 1
                            img_text = ''
                            if img.get('src'):
                                src = img.get('src').strip()
                                if src.startswith('/'):
                                    img_url = urljoin(url, src)
                                elif not src.startswith('http'):
                                    img_url = urljoin(url, src)
                                else:
                                    img_url = src
                                
                                # OCR로 이미지에서 텍스트 추출
                                ocr_text = extract_text_from_image(img_url, headers_fetch)
                                if ocr_text:
                                    img_text += f"[이미지{img_count}: {src} OCR:{ocr_text}]"
                                    log(f"    Found image {img_count}: {src} (OCR text: {ocr_text[:50]}...)")
                                else:
                                    img_text += f"[이미지{img_count}: {src}]"
                                    log(f"    Found image {img_count}: {src} (no OCR text)")
                            if img.get('alt'):
                                img_text += f" alt:{img.get('alt')}"
                            if img.get('title'):
                                img_text += f" title:{img.get('title')}"
                            if img_text:
                                text_content += ' ' + img_text
                        
                        if img_count > 0:
                            text_content += f" [총이미지수: {img_count}]"
                        
                        # 링크 태그의 href도 포함
                        for link in elem.find_all('a'):
                            if link.get('href'):
                                text_content += f" [링크: {link.get('href')}]"
                        
                        text_parts.append(text_content)
                    
                    text = ' '.join(text_parts)
                    if total_img_count > 0:
                        log(f"  Total images found in selected elements: {total_img_count}")
                    else:
                        log(f"  No images found in selected elements")
                else:
                    # 선택자가 매칭되지 않으면 전체 텍스트 사용
                    log(f"Warning: Selector '{target_selector}' not found, using full page")
                    text = soup.get_text(separator=' ', strip=True)
                    # 전체 페이지에서도 이미지 태그 포함
                    img_count = 0
                    for img in soup.find_all('img'):
                        img_count += 1
                        img_text = ''
                        if img.get('src'):
                            src = img.get('src').strip()
                            if src.startswith('/'):
                                img_url = urljoin(url, src)
                            elif not src.startswith('http'):
                                img_url = urljoin(url, src)
                            else:
                                img_url = src
                            
                            ocr_text = extract_text_from_image(img_url, headers_fetch)
                            if ocr_text:
                                img_text += f"[이미지{img_count}: {src} OCR:{ocr_text}]"
                            else:
                                img_text += f"[이미지{img_count}: {src}]"
                        if img.get('alt'):
                            img_text += f" alt:{img.get('alt')}"
                        if img.get('title'):
                            img_text += f" title:{img.get('title')}"
                        if img_text:
                            text += ' ' + img_text
                    if img_count > 0:
                        text += f" [총이미지수: {img_count}]"
            except Exception as e:
                log(f"Error with selector '{target_selector}': {str(e)}, using full page")
                text = soup.get_text(separator=' ', strip=True)
                # 전체 페이지에서도 이미지 태그 포함
                img_count = 0
                for img in soup.find_all('img'):
                    img_count += 1
                    img_text = ''
                    if img.get('src'):
                        src = img.get('src').strip()
                        if src.startswith('/'):
                            img_url = urljoin(url, src)
                        elif not src.startswith('http'):
                            img_url = urljoin(url, src)
                        else:
                            img_url = src
                        
                        ocr_text = extract_text_from_image(img_url, headers_fetch)
                        if ocr_text:
                            img_text += f"[이미지{img_count}: {src} OCR:{ocr_text}]"
                        else:
                            img_text += f"[이미지{img_count}: {src}]"
                    if img.get('alt'):
                        img_text += f" alt:{img.get('alt')}"
                    if img.get('title'):
                        img_text += f" title:{img.get('title')}"
                    if img_text:
                        text += ' ' + img_text
                if img_count > 0:
                    text += f" [총이미지수: {img_count}]"
        else:
            # 선택자가 없거나 'body'면 전체 텍스트 추출
            text = soup.get_text(separator=' ', strip=True)
            log(f"  Extracted full page text length: {len(text)} characters (before adding images)")
            
            # 전체 페이지에서도 이미지 태그 포함
            img_count = 0
            all_imgs = soup.find_all('img')
            log(f"  Found {len(all_imgs)} image(s) in full page")
            for img in all_imgs:
                img_count += 1
                img_text = ''
                if img.get('src'):
                    src = img.get('src').strip()
                    if src.startswith('/'):
                        img_url = urljoin(url, src)
                    elif not src.startswith('http'):
                        img_url = urljoin(url, src)
                    else:
                        img_url = src
                    
                    ocr_text = extract_text_from_image(img_url, headers_fetch)
                    if ocr_text:
                        img_text += f"[이미지{img_count}: {src} OCR:{ocr_text}]"
                        log(f"    Image {img_count}: {src} (OCR text: {ocr_text[:50]}...)")
                    else:
                        img_text += f"[이미지{img_count}: {src}]"
                        log(f"    Image {img_count}: {src} (no OCR text)")
                if img.get('alt'):
                    img_text += f" alt:{img.get('alt')}"
                if img.get('title'):
                    img_text += f" title:{img.get('title')}"
                if img_text:
                    text += ' ' + img_text
            if img_count > 0:
                text += f" [총이미지수: {img_count}]"
                log(f"  Added {img_count} image(s) to content")
            else:
                log(f"  No images found in page")
        
        # 최종 텍스트에 이미지 정보가 포함되었는지 확인
        final_img_count = text.count('[이미지')
        log(f"  Final text length: {len(text)}, Image markers in text: {final_img_count}")
        if final_img_count > 0:
            log(f"  Final text preview (last 200 chars): {text[-200:]}")
        
        return {
            'content': text,
            'html': response.text,
            'final_url': response.url
        }
    except Exception as e:
        log(f"Error fetching {url}: {str(e)}")
        return None

