#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP 서버용 웹 모니터링 크롤러
카페24 API를 호출하여 2초 간격으로 크롤링
"""

import requests
import time
import hashlib
import difflib
from bs4 import BeautifulSoup
from datetime import datetime
import urllib3
import io
from PIL import Image
import html
import re
from datetime import date
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# SSL 경고 메시지 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================
# 설정 (수정 필요)
# ============================================
CAFE24_API_URL = 'https://rofan.mycafe24.com/tracker/api/external_api.php'
API_TOKEN = 'rofan-tracker-token-2025-secure-key'  # config.php의 API_TOKEN과 동일하게 설정

# HTTP 헤더
headers = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json'
}

# ============================================
# 함수 정의
# ============================================

def log(message):
    """로그 출력"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", flush=True)

def check_existing_process():
    """기존 실행 중인 프로세스 확인"""
    pid_file = '/tmp/gcp_crawler.pid'
    
    # PID 파일이 존재하는지 확인
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())
            
            # 프로세스가 실제로 실행 중인지 확인
            try:
                # Linux/Unix: kill -0은 프로세스가 존재하면 에러 없음
                os.kill(old_pid, 0)
                # 프로세스가 실행 중임
                log(f"✗✗✗ Another crawler process is already running (PID: {old_pid}) ✗✗✗")
                log(f"   Please stop it first with: kill {old_pid}")
                log(f"   Or remove the PID file: rm {pid_file}")
                return False
            except OSError:
                # 프로세스가 존재하지 않음 (좀비 PID 파일)
                log(f"⚠ Found stale PID file (PID: {old_pid} not running), removing it...")
                os.remove(pid_file)
        except (ValueError, IOError) as e:
            log(f"⚠ Error reading PID file: {e}, removing it...")
            try:
                os.remove(pid_file)
            except:
                pass
    
    # 현재 PID 저장
    try:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        log(f"✓ PID file created: {pid_file} (PID: {os.getpid()})")
    except Exception as e:
        log(f"⚠ Warning: Could not create PID file: {e}")
    
    return True

def cleanup_pid_file():
    """종료 시 PID 파일 정리"""
    pid_file = '/tmp/gcp_crawler.pid'
    try:
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            if pid == os.getpid():
                os.remove(pid_file)
                log(f"✓ PID file removed: {pid_file}")
    except Exception as e:
        pass  # 무시

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

def get_sites():
    """카페24에서 사이트 목록 가져오기"""
    try:
        response = requests.get(f'{CAFE24_API_URL}?action=get_sites', headers=headers, timeout=10)
        
        if response.status_code != 200:
            log(f"✗✗✗ API Error: HTTP {response.status_code} when getting sites ✗✗✗")
            if response.status_code == 403:
                log(f"  → Possible IP block or authentication failure")
            elif response.status_code == 429:
                log(f"  → Rate limit exceeded")
            elif response.status_code >= 500:
                log(f"  → Cafe24 server error")
            return []
        
        data = response.json()
        if data['success']:
            sites = data['data']
            log(f"✓ Got {len(sites)} active sites from API")
            # 사이트 목록 상세 출력 (디버깅용)
            for site in sites:
                site_id = site.get('site_id', 'N/A')
                site_name = site.get('site_name', 'N/A')
                log(f"  - Site ID {site_id}: {site_name}")
            return sites
        else:
            log(f"✗ API returned error: {data.get('message', 'Unknown error')}")
            return []
    except requests.exceptions.Timeout:
        log(f"✗✗✗ API TIMEOUT: Request to Cafe24 API timed out ✗✗✗")
        return []
    except requests.exceptions.ConnectionError as e:
        log(f"✗✗✗ API CONNECTION ERROR: Failed to connect to Cafe24 API: {str(e)} ✗✗✗")
        return []
    except Exception as e:
        log(f"✗✗✗ Exception in get_sites: {str(e)} ✗✗✗")
        import traceback
        log(f"  Traceback: {traceback.format_exc()}")
        return []

def get_latest_snapshots(site_ids=None):
    """카페24에서 각 사이트의 최신 스냅샷 가져오기 (크롤러 초기화용)"""
    try:
        url = f'{CAFE24_API_URL}?action=get_latest_snapshots'
        if site_ids:
            site_id_str = ','.join(map(str, site_ids))
            url += f'&site_ids={site_id_str}'
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            log(f"✗✗✗ API Error: HTTP {response.status_code} when getting latest snapshots ✗✗✗")
            return {}
        
        data = response.json()
        if data['success']:
            snapshots = {}
            for snapshot in data['data']:
                site_id = snapshot['site_id']
                snapshots[site_id] = (
                    snapshot['content_hash'],
                    snapshot['content_text'],
                    snapshot['snapshot_id']
                )
            log(f"✓ Loaded {len(snapshots)} latest snapshots from DB")
            return snapshots
        else:
            log(f"✗ API returned error getting snapshots: {data.get('message', 'Unknown error')}")
            return {}
    except requests.exceptions.Timeout:
        log(f"✗✗✗ API TIMEOUT getting latest snapshots ✗✗✗")
        return {}
    except requests.exceptions.ConnectionError as e:
        log(f"✗✗✗ API CONNECTION ERROR getting snapshots: {str(e)} ✗✗✗")
        return {}
    except Exception as e:
        log(f"✗✗✗ Exception getting latest snapshots: {str(e)} ✗✗✗")
        import traceback
        log(f"  Traceback: {traceback.format_exc()}")
        return {}

def fetch_content_sexbam(url):
    """섹밤 유형 사이트에서 제목, 전화번호, 본문만 추출"""
    try:
        log(f"    Fetching URL (섹밤 유형): {url}")
        from urllib.parse import urljoin
        
        # 캐시 방지 헤더
        headers_fetch = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        
        response = requests.get(url, headers=headers_fetch, timeout=30, verify=False)
        if response.status_code != 200:
            log(f"    ✗ HTTP Status: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'lxml')
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
            log(f"    Found title: {title_text[:50]}...")
        
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
        
        # 3. 본문 추출: meta property="og:description"에서 추출 (우선), 없거나 비어있으면 .rd_body 내부의 article .xe_content
        body_text = None
        
        # 먼저 og:description에서 추출 시도
        og_description = soup.find('meta', property='og:description')
        if og_description and og_description.get('content'):
            body_text = og_description.get('content', '').strip()
            # 공백만 있으면 비어있는 것으로 간주
            if not body_text or body_text.isspace():
                body_text = None
            else:
                log(f"    Found body from og:description: {body_text[:100]}...")
        
        # og:description이 없거나 비어있으면 기존 방식으로 시도
        if not body_text:
            log(f"    og:description is empty or not found, trying to extract from article...")
            rd_body = soup.select_one('.rd_body')
            article_elem = None
            if rd_body:
                article_elem = rd_body.find('article')
                log(f"    .rd_body found, article element: {article_elem is not None}")
            else:
                log(f"    Warning: .rd_body not found, trying to find article in full HTML...")
                article_elem = soup.find('article')
            
            if article_elem:
                # article 내부의 .xe_content만 추출
                # div.document_xxx_xxx.xe_content 형식 찾기
                content_elem = article_elem.find('div', class_=lambda x: x and 'xe_content' in x)
                if not content_elem:
                    # .xe_content가 없으면 article 전체 사용
                    content_elem = article_elem
                    log(f"    Warning: .xe_content not found in article, using article content")
                else:
                    log(f"    Found .xe_content div in article")
                
                # 텍스트 추출 (순수 텍스트만)
                body_text = content_elem.get_text(separator=' ', strip=True)
                log(f"    Extracted body text from article: {len(body_text)} characters")
                
                # 이미지 처리 (content_elem 내부의 이미지만)
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
                log(f"    Warning: article element not found in .rd_body")
        
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

def fetch_content(url, target_selector='body'):
    """URL에서 컨텐츠 가져오기"""
    try:
        log(f"    Fetching URL: {url}")
        log(f"    Using selector: '{target_selector}'")
        # 캐시 방지 헤더 추가
        headers_fetch = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        from urllib.parse import urljoin
        
        try:
            response = requests.get(url, headers=headers_fetch, timeout=30, verify=False)
        except requests.exceptions.Timeout:
            log(f"    ✗✗✗ TIMEOUT: Request to {url} timed out after 30 seconds ✗✗✗")
            return None
        except requests.exceptions.ConnectionError as e:
            log(f"    ✗✗✗ CONNECTION ERROR: Failed to connect to {url}: {str(e)} ✗✗✗")
            return None
        except requests.exceptions.RequestException as e:
            log(f"    ✗✗✗ REQUEST ERROR: {str(e)} ✗✗✗")
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
                        # .rd_body .clear 선택자 사용 시 제거할 클래스들
                        unwanted_classes = ['updatenews_author', 'updatenews_date', 'updatenews_title']
                        for unwanted_class in unwanted_classes:
                            for unwanted_elem in elem.find_all(class_=unwanted_class):
                                unwanted_elem.decompose()  # 요소 완전히 제거
                                log(f"    Removed element with class '{unwanted_class}'")
                        
                        # 텍스트 추출 (일반 텍스트 먼저 추출 - OCR과 별개)
                        text_content = elem.get_text(separator=' ', strip=True)
                        log(f"    Extracted text length: {len(text_content)} characters (before adding images)")
                        
                        # 이미지 태그의 src, alt 속성도 텍스트로 포함 (순서대로)
                        img_count = 0
                        for img in elem.find_all('img'):
                            img_count += 1
                            total_img_count += 1
                            img_text = ''
                            # src 속성 (상대/절대 경로 모두 포함)
                            if img.get('src'):
                                src = img.get('src').strip()
                                # 상대 경로를 절대 경로로 변환
                                if src.startswith('/'):
                                    img_url = urljoin(url, src)
                                elif not src.startswith('http'):
                                    img_url = urljoin(url, src)
                                else:
                                    img_url = src
                                
                                # OCR로 이미지에서 텍스트 추출
                                ocr_text = extract_text_from_image(img_url, headers_fetch)
                                if ocr_text:
                                    # OCR로 추출된 텍스트를 포함
                                    img_text += f"[이미지{img_count}: {src} OCR:{ocr_text}]"
                                    log(f"    Found image {img_count}: {src} (OCR text: {ocr_text[:50]}...)")
                                else:
                                    # OCR 실패 시 기본 정보만 포함
                                    img_text += f"[이미지{img_count}: {src}]"
                                    log(f"    Found image {img_count}: {src} (no OCR text)")
                            # alt 속성
                            if img.get('alt'):
                                img_text += f" alt:{img.get('alt')}"
                            # title 속성도 포함
                            if img.get('title'):
                                img_text += f" title:{img.get('title')}"
                            if img_text:
                                text_content += ' ' + img_text
                        
                        # 이미지 개수도 포함 (이미지 추가/삭제 감지용)
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
                            # 상대 경로를 절대 경로로 변환
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
                        # 상대 경로를 절대 경로로 변환
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
            # 선택자가 없거나 'body'면 전체 텍스트 추출 (일반 텍스트 먼저)
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
                    # 상대 경로를 절대 경로로 변환
                    if src.startswith('/'):
                        from urllib.parse import urljoin
                        img_url = urljoin(url, src)
                    elif not src.startswith('http'):
                        from urllib.parse import urljoin
                        img_url = urljoin(url, src)
                    else:
                        img_url = src
                    
                    # OCR로 이미지에서 텍스트 추출
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

def generate_hash(content):
    """컨텐츠 해시 생성"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def generate_diff(old_text, new_text):
    """간단한 diff HTML 생성"""
    old_words = old_text.split()
    new_words = new_text.split()
    
    diff = difflib.SequenceMatcher(None, old_words, new_words)
    html_parts = []
    
    for opcode, i1, i2, j1, j2 in diff.get_opcodes():
        if opcode == 'equal':
            html_parts.append(' '.join(old_words[i1:i2]))
        elif opcode == 'delete':
            for word in old_words[i1:i2]:
                html_parts.append(f'<span class="diff-removed" style="background-color: #f8d7da; color: #721c24; text-decoration: line-through;">{word}</span>')
        elif opcode == 'insert':
            for word in new_words[j1:j2]:
                html_parts.append(f'<span class="diff-added" style="background-color: #d4edda; color: #155724; font-weight: bold;">{word}</span>')
        elif opcode == 'replace':
            for word in old_words[i1:i2]:
                html_parts.append(f'<span class="diff-removed" style="background-color: #f8d7da; color: #721c24; text-decoration: line-through;">{word}</span>')
            for word in new_words[j1:j2]:
                html_parts.append(f'<span class="diff-added" style="background-color: #d4edda; color: #155724; font-weight: bold;">{word}</span>')
    
    return '<div class="diff-content">' + ' '.join(html_parts) + '</div>'

def save_snapshot(site_id, content_hash, content_text, full_html, final_url):
    """카페24에 스냅샷 저장"""
    try:
        data = {
            'site_id': site_id,
            'content_hash': content_hash,
            'content_text': content_text[:500000],  # 500000자로 증가 (약 1.5MB)
            'full_html': full_html[:500000],  # 500000자로 증가 (약 1.5MB)
            'final_url': final_url
        }
        
        log(f"  Sending snapshot to API: site_id={site_id}, hash={content_hash[:16]}..., content_len={len(content_text)}, html_len={len(full_html)}")
        response = requests.post(f'{CAFE24_API_URL}?action=save_snapshot', 
                                json=data, headers=headers, timeout=30)
        
        log(f"  API response status: {response.status_code}")
        
        if response.status_code != 200:
            log(f"✗✗✗ API Error saving snapshot: HTTP {response.status_code} ✗✗✗")
            if response.status_code == 403:
                log(f"  → Possible IP block or authentication failure")
            elif response.status_code == 429:
                log(f"  → Rate limit exceeded")
            elif response.status_code >= 500:
                log(f"  → Server error")
                log(f"  Response text (first 1000 chars): {response.text[:1000]}")
            return None, False
        
        # JSON 파싱 시도
        try:
            result = response.json()
            log(f"  API response: success={result.get('success')}, message={result.get('message', 'N/A')}")
        except ValueError as e:
            log(f"  ✗✗✗ JSON DECODE ERROR: {str(e)} ✗✗✗")
            log(f"  Response is not valid JSON")
            log(f"  Response text (first 2000 chars): {response.text[:2000]}")
            log(f"  Response content type: {response.headers.get('Content-Type', 'unknown')}")
            return None, False
        
        if result.get('success'):
            snapshot_id = result['data'].get('snapshot_id')
            has_previous = result['data'].get('has_previous_snapshot', False)
            log(f"  ✓ Snapshot saved successfully: snapshot_id={snapshot_id}, has_previous={has_previous}")
            return snapshot_id, has_previous
        else:
            error_msg = result.get('message', 'Unknown error')
            log(f"✗✗✗ Snapshot save failed: {error_msg} ✗✗✗")
            log(f"  Full response: {result}")
            return None, False
    except requests.exceptions.Timeout:
        log(f"✗✗✗ API TIMEOUT saving snapshot for site_id {site_id} (timeout: 30s) ✗✗✗")
        return None, False
    except requests.exceptions.ConnectionError as e:
        log(f"✗✗✗ API CONNECTION ERROR saving snapshot: {str(e)} ✗✗✗")
        import traceback
        log(f"  Traceback: {traceback.format_exc()}")
        return None, False
    except Exception as e:
        log(f"✗✗✗ Error saving snapshot: {str(e)} ✗✗✗")
        import traceback
        log(f"  Traceback: {traceback.format_exc()}")
        return None, False

def format_attendance_info(site_id, site_name, current_attendance_records, detected_time_str):
    """출근부 정보를 포맷팅하여 HTML 생성"""
    try:
        today = date.today().isoformat()
        
        # 최초 출근 인원 가져오기 (API 호출)
        try:
            response = requests.get(f'{CAFE24_API_URL}?action=get_first_attendance', 
                                  params={'site_id': site_id, 'attendance_date': today},
                                  headers=headers, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('success') and result.get('data'):
                    first_attendance = result['data']
                else:
                    first_attendance = []
            else:
                first_attendance = []
        except:
            first_attendance = []
        
        # 현재 출근 인원을 딕셔너리로 변환
        current_dict = {}
        for record in current_attendance_records:
            name = record['name']
            times_str = record['times']
            times_set = set(times_str.split(',')) if times_str else set()
            current_dict[name] = times_set
        
        # 최초 출근 인원을 딕셔너리로 변환
        first_dict = {}
        for record in first_attendance:
            name = record.get('staff_name', '')
            times_str = record.get('work_times', '')
            times_set = set(times_str.split(',')) if times_str else set()
            if name:
                first_dict[name] = times_set
        
        # 최초 출근 인원이 없으면 현재 출근 인원을 최초로 설정
        if not first_dict and current_dict:
            first_dict = {name: times.copy() for name, times in current_dict.items()}
        
        # HTML 생성
        html_parts = []
        
        # 날짜 추출 (YYYY-MM-DD 형식)
        # 2025-11-18 -> 11월18일
        try:
            year, month, day = today.split('-')
            date_str = f"{int(month)}월{int(day)}일"
        except:
            date_str = today
        
        html_parts.append(
            f'<div class="attendance-summary-block" data-site-id="{site_id}" '
            f'data-detected-time="{detected_time_str}" '
            f'style="margin: 15px 0; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">'
        )
        html_parts.append(f'<h6 style="margin-bottom: 10px; font-weight: bold;">{site_name} {date_str} {detected_time_str}</h6>')
        
        # 최초 출근 인원 표시
        if first_dict:
            first_list = []
            for name in sorted(first_dict.keys()):
                times_list = sorted([int(t) for t in first_dict[name] if t.isdigit()])
                times_str = ','.join(map(str, times_list))
                first_list.append(f"{name} {times_str}")
            html_parts.append(
                '<div class="attendance-line" data-kind="initial" style="margin-bottom: 8px;">'
                '<span class="attendance-label">[최초출근인원]</span>'
                '<span class="attendance-sep"> : </span>'
                f'<span class="attendance-value">{" / ".join(first_list)}</span>'
                '</div>'
            )
        
        # 현재 예약 가능 인원 표시
        if current_dict:
            current_list = []
            for name in sorted(current_dict.keys()):
                times_list = sorted([int(t) for t in current_dict[name] if t.isdigit()])
                # 최초 출근 인원과 비교하여 예약 불가능한 시간에 <u> 태그 적용
                if name in first_dict:
                    first_times = first_dict[name]
                    formatted_times = []
                    for time_val in times_list:
                        time_str = str(time_val)
                        if time_str not in first_times:
                            formatted_times.append(f'<u>{time_str}</u>')
                        else:
                            formatted_times.append(time_str)
                    times_display = ','.join(formatted_times)
                else:
                    times_display = ','.join(map(str, times_list))
                current_list.append(f"{name} {times_display}")
            html_parts.append(
                f'<div class="attendance-line" data-kind="current" data-time="{detected_time_str}" style="margin-bottom: 6px;">'
                f'<span class="attendance-label">[{detected_time_str} 예약가능인원]</span>'
                '<span class="attendance-sep"> : </span>'
                f'<span class="attendance-value">{" / ".join(current_list)}</span>'
                '</div>'
            )
        
        html_parts.append('</div>')
        
        return ''.join(html_parts)
    except Exception as e:
        log(f"  ✗ Error formatting attendance info: {str(e)}")
        import traceback
        log(f"  Traceback: {traceback.format_exc()}")
        return ""

def save_change(site_id, old_snapshot_id, new_snapshot_id, old_content, new_content, diff_html, change_type=None, site_name=None, attendance_records=None):
    """카페24에 변화 로그 저장"""
    try:
        # change_type이 명시되지 않으면 자동 판단
        if change_type is None:
            change_type = 'initial' if old_snapshot_id is None else 'modified'
        
        # 출근부 정보 추가
        attendance_html = ""
        if attendance_records and site_name:
            try:
                from datetime import datetime
                detected_time = datetime.now().strftime('%H:%M:%S')
                attendance_html = format_attendance_info(site_id, site_name, attendance_records, detected_time)
            except Exception as e:
                log(f"  ✗ Error generating attendance HTML: {str(e)}")
        
        # 출근부 정보를 diff_html 앞에 추가
        if attendance_html:
            final_diff_html = attendance_html + diff_html
        else:
            final_diff_html = diff_html
        
        data = {
            'site_id': site_id,
            'old_snapshot_id': old_snapshot_id,
            'new_snapshot_id': new_snapshot_id,
            'change_type': change_type,
            'old_content': old_content[:50000],  # 50000자로 증가 (약 150KB)
            'new_content': new_content[:50000],  # 50000자로 증가 (약 150KB)
            'diff_html': final_diff_html
        }
        log(f"  Sending change to API: site_id={site_id}, change_type={change_type}, new_snapshot_id={new_snapshot_id}")
        response = requests.post(f'{CAFE24_API_URL}?action=save_change', 
                                json=data, headers=headers, timeout=10)
        
        log(f"  API response status: {response.status_code}")
        
        # 500 에러일 경우 응답 내용 확인
        if response.status_code >= 500:
            log(f"  ✗✗✗ SERVER ERROR: HTTP {response.status_code} ✗✗✗")
            log(f"  Response text (first 1000 chars): {response.text[:1000]}")
            log(f"  Response headers: {dict(response.headers)}")
        
        # JSON 파싱 시도
        try:
            result = response.json()
            log(f"  API response: {result}")
        except ValueError as e:
            log(f"  ✗✗✗ JSON DECODE ERROR: {str(e)} ✗✗✗")
            log(f"  Response is not valid JSON")
            log(f"  Response text (first 2000 chars): {response.text[:2000]}")
            log(f"  Response content type: {response.headers.get('Content-Type', 'unknown')}")
            # JSON이 아니면 에러로 처리
            return False
        
        if result.get('success'):
            change_id = result.get('data', {}).get('change_id', 'unknown')
            log(f"✓ Change saved successfully for site_id {site_id} (change_id: {change_id})")
            return True
        else:
            error_msg = result.get('message', 'Unknown error')
            log(f"✗ Change save failed for site_id {site_id}: {error_msg}")
            log(f"  Full response: {result}")
            return False
    except requests.exceptions.RequestException as e:
        log(f"✗ Network error saving change for site_id {site_id}: {str(e)}")
        return False
    except Exception as e:
        log(f"✗ Error saving change for site_id {site_id}: {str(e)}")
        import traceback
        log(f"  Traceback: {traceback.format_exc()}")
        return False

def extract_attendance_data(content_text, html_content, extraction_mode='both'):
    """출근부 데이터 추출 (다양한 형식 지원, v6, 필터링 강화, 중복 제거)
    
    Args:
        content_text: 제목+본문 텍스트
        html_content: HTML 원본
        extraction_mode: 'both' (제목+본문), 'title' (제목만), 'body' (본문만)
    """
    attendance_records = []
    processed_records = set()
    name_to_times = {}  # 이름별로 시간을 통합하기 위한 딕셔너리
    log(f"  DEBUG (extract_attendance_data): Starting extraction v6, mode: {extraction_mode}")

    try:
        # 불필요한 키워드 목록 (출근부가 아닌 일반 정보) - 강화
        excluded_keywords = {
            'document', '고맙', '첫', '내상zero', '내상률', '영업', '이벤트중', 
            '주대', '집', '카톡', '출근부', '사장', '실장', '대표', '교대',
            '나이아가라', '부천랜드마크', '북창동', '도파민', '빠나나', '여사친',
            '인스타', '이정재', '하니', '홀딱벗은', '나만맛보는', '대100명',
            '청결매장', '워터밤휴게', '올탈하드', '상동', 'dior', '권지용',
            '상동키스고', '키스고', 'nf대거영입', '대거영입', '강남', '전원',
            '출동', '텔래그램', '후불제', 'new', '순수업계', '배우연습생',
            '대학생', '하유진', '올라가면', '고정11'
        }
        
        # 불필요한 이름 패턴 (사장, 실장 등이 포함된 경우)
        excluded_name_patterns = [
            r'.*사장$', r'.*실장$', r'.*대표$', r'.*출근부$', r'.*카톡$',
            r'^Document', r'^고맙', r'^첫\d+', r'^내상', r'^영업', r'^이벤트',
            r'^주대$', r'^집$', r'^출근부$', r'^카톡$', r'^교대$',
            r'^NF대거영입$', r'^대거영입$', r'^강남$', r'^전원$', r'^출동$',
            r'^텔래그램$', r'^후불제$', r'^new$', r'^순수업계$', r'^배우연습생$',
            r'^대학생$', r'^하유진$', r'^올라가면$', r'^고정\d+$'
        ]

        def parse_times_from_string(time_str_raw):
            """입력 문자열에서 시간을 파싱하여 정규화된 쉼표 구분 문자열로 반환 (0-24 범위만 허용)"""
            # '시'와 같은 불필요한 문자 제거
            time_str = re.sub(r'[시분초]', '', time_str_raw)
            
            # 모든 숫자 추출
            numbers = [int(n) for n in re.findall(r'\d+', time_str)]
            if not numbers:
                return None

            # 25 이상의 큰 숫자가 포함되어 있으면 전화번호나 날짜로 간주하여 제외
            if any(n >= 25 for n in numbers):
                return None

            # 범위 형식(~) 처리
            if '~' in time_str and len(numbers) >= 2:
                start, end = numbers[0], numbers[-1] # 처음과 마지막 숫자를 사용
                
                # 시작이나 끝이 25 이상이면 제외
                if start >= 25 or end >= 25:
                    return None
                
                times = []
                if start == 24: # 24시부터 시작하는 경우 (예: 24~03)
                    times.append(24)
                    if end < 24:
                        times.extend(range(1, end))
                elif start > end: # 자정을 넘는 일반적인 경우 (예: 23~03)
                    times.extend(range(start, 24))
                    if end < 24:
                        times.extend(range(0, end))
                else: # 일반 범위 (예: 14~20)
                    times.extend(range(start, end))
                
                # 0-24 범위만 필터링
                times = [t for t in times if 0 <= t <= 24]
                if not times:
                    return None
                
                return ','.join(map(str, sorted(list(set(times)))))
            else:
                # 쉼표, 점, 공백으로 구분된 숫자 리스트
                # 0-24 범위만 필터링
                valid_times = [n for n in numbers if 0 <= n <= 24]
                if not valid_times:
                    return None
                return ','.join(map(str, sorted(list(set(valid_times)))))

        def is_excluded_name(name):
            """이름이 제외 목록에 있는지 확인"""
            name_lower = name.lower()
            
            # 키워드 체크
            for keyword in excluded_keywords:
                if keyword in name_lower:
                    return True
            
            # 패턴 체크
            for pattern in excluded_name_patterns:
                if re.match(pattern, name, re.IGNORECASE):
                    return True
            
            return False

        def normalize_name(name):
            """이름 정규화: NF, ACE 등의 접두사 제거하고 기본 이름 추출"""
            # Queen 다율, 퀸다율 등 처리
            if '다율' in name or 'Queen' in name or '퀸' in name:
                return '다율'
            
            # NF, ACE 등의 접두사 제거
            name_clean = re.sub(r'^(NF|ACE|NEW|new)\s*', '', name, flags=re.IGNORECASE)
            # Queen, 퀸 등의 접두사도 제거
            name_clean = re.sub(r'^(Queen|퀸)\s*', '', name_clean, flags=re.IGNORECASE)
            
            return name_clean.strip()
        
        # 제목과 본문 분리
        title_text = ""
        body_text = ""
        
        if content_text:
            title_match = re.search(r'\[제목\]\s*(.*?)(?=\[본문\]|$)', content_text, re.DOTALL)
            body_match = re.search(r'\[본문\]\s*(.*?)$', content_text, re.DOTALL)
            
            if title_match:
                title_text = title_match.group(1).strip()
            if body_match:
                body_text = body_match.group(1).strip()
            
            if not title_text and not body_text:
                body_text = content_text
        
        soup = None
        html_full_text = ""
        if html_content:
            soup = BeautifulSoup(html_content, 'lxml')
            html_full_text = soup.get_text(separator=' ', strip=True)
        
        def clean_text(raw_text):
            if not raw_text:
                return ""
            text = raw_text
            text = re.sub(r'\d+/\d+/\d+/[A-Za-z가-힣]+/[가-힣]+', ' ', text)
            text = re.sub(r'\d+/\d+/\d+/[A-Za-z가-힣]+', ' ', text)
            text = re.sub(r'\[.*?\]', ' ', text)
            text = re.sub(r'[❤️✅⭐️🎀💛💙💜💚🧡🖤🤍🤎✨]', ' ', text)
            return text
        
        texts_to_parse = []
        if extraction_mode in ('both', 'body'):
            if body_text:
                texts_to_parse.append(('body', body_text))
            elif html_full_text:
                texts_to_parse.append(('body', html_full_text))
        if extraction_mode in ('both', 'title'):
            if title_text:
                texts_to_parse.append(('title', title_text))
            elif soup:
                title_elem = soup.find('title') or soup.find('h1')
                if title_elem:
                    texts_to_parse.append(('title', title_elem.get_text(strip=True)))
        if not texts_to_parse:
            fallback = content_text or html_full_text or ""
            texts_to_parse.append(('fallback', fallback))
        
        name_pattern = r'[a-zA-Z가-힣][a-zA-Z0-9가-힣]*'
        pattern = re.compile(f'({name_pattern})\\s+(.*?)(?=\\s+{name_pattern}|$)')
        
        for source, raw_text in texts_to_parse:
            cleaned_text = clean_text(raw_text)
            if not cleaned_text:
                continue
            matches = pattern.finditer(cleaned_text)

            for match in matches:
                name = match.group(1).strip()
                raw_time_part = match.group(2).strip()

                if len(name) == 1 and name in "시분초월일":
                    continue
                
                if is_excluded_name(name):
                    log(f"  DEBUG (extract_attendance_data): Excluded name: {name}")
                    continue
                
                if re.search(r'\d+/\d+/\d+', raw_time_part):
                    log(f"  DEBUG (extract_attendance_data): Excluded time part (contains age/height/weight): {raw_time_part}")
                    continue
                
                if not any(char.isdigit() for char in raw_time_part):
                    continue

                parsed_times = parse_times_from_string(raw_time_part)
                
                if parsed_times:
                    normalized_name = normalize_name(name)
                    
                    if normalized_name in name_to_times:
                        existing_times = set(name_to_times[normalized_name].split(','))
                        new_times = set(parsed_times.split(','))
                        combined_times = sorted(list(existing_times | new_times))
                        name_to_times[normalized_name] = ','.join(combined_times)
                        log(f"  DEBUG (extract_attendance_data): Merged times for {normalized_name}: {name_to_times[normalized_name]}")
                    else:
                        name_to_times[normalized_name] = parsed_times
                        log(f"  DEBUG (extract_attendance_data): Added record: {normalized_name}, {parsed_times}")
        
        # name_to_times를 attendance_records로 변환
        for name, times in name_to_times.items():
            attendance_records.append({
                'name': name,
                'times': times,
                'raw': f"{name} {times}"
            })

    except Exception as e:
        log(f"✗✗✗ ERROR in extract_attendance_data: {str(e)} ✗✗✗")
        import traceback
        log(f"  Traceback: {traceback.format_exc()}")

    log(f"  DEBUG (extract_attendance_data): Final attendance records count: {len(attendance_records)}")
    return attendance_records

def extract_phone_numbers(html_content):
    """전화번호 추출 (table.et_vars 내에서만 추출하여 광고 번호 제외)"""
    phone_numbers = []
    
    if not html_content:
        log(f"  DEBUG (extract_phone_numbers): No HTML content provided")
        return phone_numbers
    
    log(f"  DEBUG (extract_phone_numbers): HTML content length: {len(html_content)} characters")
    
    soup = BeautifulSoup(html_content, 'lxml')
    
    def normalize_phone(phone_str):
        """전화번호를 표준 형식으로 정규화 (010-1234-5678)"""
        if not phone_str:
            return None
        # 숫자만 추출
        digits = re.sub(r'\D', '', phone_str)
        if len(digits) >= 9 and len(digits) <= 11 and digits.startswith('0'):
            # 010-1234-5678 형식으로 변환
            if len(digits) == 11:  # 01012345678
                return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
            elif len(digits) == 10:  # 0212345678
                return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
            elif len(digits) == 9:  # 021234567
                return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
        # 이미 하이픈이 있는 경우 정규화 시도
        normalized = re.sub(r'(\d{2,3})-?(\d{3,4})-?(\d{4})', r'\1-\2-\3', phone_str)
        # 정규화된 결과가 유효한 전화번호 형식인지 확인
        if re.match(r'0\d{1,2}-\d{3,4}-\d{4}', normalized):
            return normalized
        return None
    
    # 우선순위 1: .rd_body 내부의 table.et_vars에서 추출 (가장 정확)
    # 여러 방법으로 .rd_body 찾기 시도
    rd_body = soup.select_one('.rd_body')
    if not rd_body:
        rd_body = soup.find('div', class_=lambda x: x and 'rd_body' in x)
    log(f"  DEBUG (extract_phone_numbers): .rd_body found: {rd_body is not None}")
    
    if rd_body:
        # 여러 방법으로 table.et_vars 찾기 시도
        phone_table = rd_body.select_one('table.et_vars')
        if not phone_table:
            phone_table = rd_body.find('table', class_=lambda x: x and 'et_vars' in x)
        log(f"  DEBUG (extract_phone_numbers): table.et_vars in .rd_body found: {phone_table is not None}")
        if phone_table:
            log(f"  DEBUG (extract_phone_numbers): Found table.et_vars in .rd_body")
            tr_count = len(phone_table.select('tr'))
            log(f"  DEBUG (extract_phone_numbers): Found {tr_count} tr elements in table.et_vars")
            for idx, tr in enumerate(phone_table.select('tr')):
                th = tr.select_one('th')
                td = tr.select_one('td')
                if th and td:
                    th_text = th.get_text(strip=True)
                    td_text = td.get_text(strip=True)
                    log(f"  DEBUG (extract_phone_numbers): tr[{idx}] th='{th_text}', td='{td_text}'")
                    if '전화번호' in th_text or '전화' in th_text:
                        phone_text = td_text
                        log(f"  DEBUG (extract_phone_numbers): Found '전화번호' row, td text: '{phone_text}'")
                        # 전화번호 패턴 추출
                        phone_match = re.search(r'0\d{1,2}-?\d{3,4}-?\d{4}', phone_text)
                        if phone_match:
                            phone_raw = phone_match.group(0)
                            log(f"  DEBUG (extract_phone_numbers): Raw phone match: '{phone_raw}'")
                            phone = normalize_phone(phone_raw)
                            if phone and phone not in phone_numbers:
                                phone_numbers.append(phone)
                                log(f"  DEBUG (extract_phone_numbers): Found phone from .rd_body table.et_vars: {phone} (normalized from: {phone_raw})")
                                return phone_numbers  # 가장 정확한 위치에서 찾았으므로 즉시 반환
                        else:
                            log(f"  DEBUG (extract_phone_numbers): No phone pattern match in td text: '{phone_text}'")
    
    # 우선순위 2: table.et_vars에서 추출 (.rd_body 밖에 있어도)
    if not phone_numbers:
        all_et_vars_tables = soup.select('table.et_vars')
        if not all_et_vars_tables:
            all_et_vars_tables = soup.find_all('table', class_=lambda x: x and 'et_vars' in x)
        log(f"  DEBUG (extract_phone_numbers): Found {len(all_et_vars_tables)} table.et_vars elements (outside .rd_body check)")
        for table_idx, table in enumerate(all_et_vars_tables):
            tr_count = len(table.select('tr'))
            log(f"  DEBUG (extract_phone_numbers): table.et_vars[{table_idx}] has {tr_count} tr elements")
            for tr_idx, tr in enumerate(table.select('tr')):
                th = tr.select_one('th')
                td = tr.select_one('td')
                if th and td:
                    th_text = th.get_text(strip=True)
                    td_text = td.get_text(strip=True)
                    log(f"  DEBUG (extract_phone_numbers): table[{table_idx}] tr[{tr_idx}] th='{th_text}', td='{td_text}'")
                    if '전화번호' in th_text or '전화' in th_text:
                        phone_text = td_text
                        log(f"  DEBUG (extract_phone_numbers): Found '전화번호' row in table.et_vars, td text: '{phone_text}'")
                        # 전화번호 패턴 추출
                        phone_match = re.search(r'0\d{1,2}-?\d{3,4}-?\d{4}', phone_text)
                        if phone_match:
                            phone_raw = phone_match.group(0)
                            log(f"  DEBUG (extract_phone_numbers): Raw phone match: '{phone_raw}'")
                            phone = normalize_phone(phone_raw)
                            if phone and phone not in phone_numbers:
                                phone_numbers.append(phone)
                                log(f"  DEBUG (extract_phone_numbers): Found phone from table.et_vars: {phone} (normalized from: {phone_raw})")
                                return phone_numbers  # table.et_vars에서 찾았으므로 즉시 반환
                        else:
                            log(f"  DEBUG (extract_phone_numbers): No phone pattern match in td text: '{phone_text}'")
    
    # 우선순위 3: <dl><dt>전화번호</dt><dd>...</dd></dl> 형식 (일반적인 경우)
    if not phone_numbers:
        all_dl = soup.find_all('dl')
        log(f"  DEBUG (extract_phone_numbers): Found {len(all_dl)} dl elements")
        for dl_idx, dl in enumerate(all_dl):
            dt = dl.find('dt')
            if dt:
                dt_text = dt.get_text(strip=True)
                if '전화번호' in dt_text or '전화' in dt_text:
                    log(f"  DEBUG (extract_phone_numbers): Found dl[{dl_idx}] with '전화번호' dt: '{dt_text}'")
                    # dd 내의 링크에서 추출
                    for link in dl.find_all('a', href=re.compile(r'tel:')):
                        phone_raw = link.get('href', '').replace('tel:', '').strip()
                        if phone_raw:
                            phone = normalize_phone(phone_raw)
                            if phone and phone not in phone_numbers:
                                phone_numbers.append(phone)
                                log(f"  DEBUG (extract_phone_numbers): Found phone from dl/dt/dd (link): {phone} (normalized from: {phone_raw})")
                                return phone_numbers
                    # dd 내의 텍스트에서 추출
                    for dd in dl.find_all('dd'):
                        phone_text = dd.get_text(strip=True)
                        phone_match = re.search(r'0\d{1,2}-?\d{3,4}-?\d{4}', phone_text)
                        if phone_match:
                            phone_raw = phone_match.group(0)
                            phone = normalize_phone(phone_raw)
                            if phone and phone not in phone_numbers:
                                phone_numbers.append(phone)
                                log(f"  DEBUG (extract_phone_numbers): Found phone from dl/dt/dd (text): {phone} (normalized from: {phone_raw})")
                                return phone_numbers
    
    # 전체 텍스트 검색은 제거 (광고 번호가 포함될 수 있음)
    # 대신 .rd_body 내부에서만 검색
    if not phone_numbers and rd_body:
        rd_body_text = rd_body.get_text()
        phone_matches = re.findall(r'0\d{1,2}-?\d{3,4}-?\d{4}', rd_body_text)
        log(f"  DEBUG (extract_phone_numbers): Found {len(phone_matches)} phone pattern matches in .rd_body text (fallback)")
        if phone_matches:
            phone_raw = phone_matches[0]  # 첫 번째 전화번호만 사용
            phone = normalize_phone(phone_raw)
            if phone:
                phone_numbers.append(phone)
                log(f"  DEBUG (extract_phone_numbers): Found phone from .rd_body text (fallback): {phone} (normalized from: {phone_raw})")
    
    if not phone_numbers:
        log(f"  DEBUG (extract_phone_numbers): No phone numbers found in HTML")
        # 추가 디버깅: HTML에서 전화번호 패턴이 있는지 확인
        all_phone_matches = re.findall(r'0\d{1,2}-?\d{3,4}-?\d{4}', html_content)
        log(f"  DEBUG (extract_phone_numbers): Found {len(all_phone_matches)} phone pattern matches in entire HTML (for debugging)")
        if all_phone_matches:
            log(f"  DEBUG (extract_phone_numbers): Sample phone matches: {all_phone_matches[:5]}")
    
    return phone_numbers

def save_attendance_data(site_id, attendance_records, snapshot_id):
    """출근부 데이터 저장"""
    if not attendance_records:
        return
    
    try:
        today = date.today().isoformat()
        data = {
            'site_id': site_id,
            'attendance_date': today,
            'attendance_records': attendance_records,
            'snapshot_id': snapshot_id
        }
        response = requests.post(f'{CAFE24_API_URL}?action=save_attendance', 
                                json=data, headers=headers, timeout=10)
        result = response.json()
        if result.get('success'):
            log(f"  ✓ Attendance data saved: {len(attendance_records)} records")
        else:
            log(f"  ✗ Failed to save attendance: {result.get('message', 'Unknown error')}")
    except Exception as e:
        log(f"  ✗ Error saving attendance: {str(e)}")

def save_available_staff(site_id, attendance_records):
    """마지막 예약 가능 인원 저장 (문자 발송용)"""
    if not attendance_records:
        return
    
    try:
        today = date.today().isoformat()
        data = {
            'site_id': site_id,
            'attendance_date': today,
            'attendance_records': attendance_records
        }
        response = requests.post(f'{CAFE24_API_URL}?action=save_available_staff', 
                                json=data, headers=headers, timeout=10)
        result = response.json()
        if result.get('success'):
            log(f"  ✓ Available staff saved: {len(attendance_records)} records")
        else:
            log(f"  ✗ Failed to save available staff: {result.get('message', 'Unknown error')}")
    except Exception as e:
        log(f"  ✗ Error saving available staff: {str(e)}")

def save_phone_numbers(site_id, phone_numbers, html_content, site_name=None):
    """전화번호 저장 (사이트 이름을 staff_name으로 사용)"""
    if not phone_numbers:
        log(f"  DEBUG (save_phone_numbers): No phone numbers to save for site_id {site_id}, site_name: {site_name}")
        return
    
    try:
        phone_staff_map = []
        
        # 각 전화번호를 사이트 이름과 함께 저장
        for phone in phone_numbers:
            # 사이트 이름이 제공되면 사용, 없으면 '알 수 없음'
            staff_name = site_name if site_name else '알 수 없음'
            phone_staff_map.append({
                'staff_name': staff_name,
                'phone_number': phone
            })
            log(f"  DEBUG (save_phone_numbers): Mapping phone {phone} to staff_name: {staff_name} (site_id: {site_id})")
        
        data = {
            'site_id': site_id,
            'phone_data': phone_staff_map
        }
        log(f"  DEBUG (save_phone_numbers): Sending data to API: site_id={site_id}, phone_count={len(phone_staff_map)}")
        log(f"  DEBUG (save_phone_numbers): Data: {data}")
        
        response = requests.post(f'{CAFE24_API_URL}?action=save_phones', 
                                json=data, headers=headers, timeout=10)
        result = response.json()
        log(f"  DEBUG (save_phone_numbers): API response: {result}")
        
        if result.get('success'):
            saved_count = result.get('data', {}).get('count', len(phone_staff_map))
            log(f"  ✓ Phone numbers saved: {saved_count} records for site_id {site_id}, site_name: {site_name}")
        else:
            error_msg = result.get('message', 'Unknown error')
            log(f"  ✗ Failed to save phones for site_id {site_id}, site_name: {site_name}: {error_msg}")
            log(f"  ✗ Full API response: {result}")
    except Exception as e:
        log(f"  ✗ Error saving phones for site_id {site_id}, site_name: {site_name}: {str(e)}")
        import traceback
        log(f"  ✗ Traceback: {traceback.format_exc()}")

def update_check_time(site_id):
    """마지막 체크 시간 업데이트"""
    try:
        data = {'site_id': site_id}
        requests.post(f'{CAFE24_API_URL}?action=update_check_time', 
                     json=data, headers=headers, timeout=10)
    except:
        pass

def check_site(site, last_snapshots):
    """사이트 체크"""
    site_id = site['site_id']
    site_name = site['site_name']
    site_type = site.get('site_type', 'normal')
    target_selector = site.get('target_selector', 'body')
    attendance_extraction_mode = site.get('attendance_extraction_mode', 'both')  # 'both', 'title', 'body'
    
    log(f"Checking {site_name} (site_id: {site_id}, type: {site_type}, selector: '{target_selector}', extraction_mode: '{attendance_extraction_mode}')")
    
    # 컨텐츠 가져오기 (섹밤 유형이면 특별 처리)
    if site_type == 'sexbam':
        content = fetch_content_sexbam(site['site_url'])
    else:
        content = fetch_content(site['site_url'], target_selector)
    if not content:
        log(f"✗ Failed to fetch: {site_name} (site_id: {site_id})")
        return
    
    log(f"  ✓ Content fetched successfully for {site_name} (site_id: {site_id})")
    
    # 해시 생성
    content_hash = generate_hash(content['content'])
    
    # 디버깅: 추출된 내용 확인 (처음 500자만)
    content_preview = content['content'][:500] if len(content['content']) > 500 else content['content']
    log(f"  Content preview: {content_preview}")
    
    # 디버깅: 전체 텍스트 길이
    log(f"  Content length: {len(content['content'])} characters")
    
    # 디버깅: 이미지 개수 확인
    img_count_in_content = content['content'].count('[이미지')
    log(f"  Image count in content: {img_count_in_content}")
    
    # 디버깅: 해시 확인
    log(f"  Content hash: {content_hash[:16]}...")
    log(f"  Full hash: {content_hash}")
    
    # 스냅샷 저장
    snapshot_result = save_snapshot(
        site_id, 
        content_hash, 
        content['content'], 
        content['html'], 
        content['final_url']
    )
    
    if not snapshot_result or snapshot_result[0] is None:
        log(f"✗✗✗ Failed to save snapshot: {site_name} (site_id: {site_id}) ✗✗✗")
        log(f"  snapshot_result: {snapshot_result}")
        return
    
    new_snapshot_id, has_previous_snapshot = snapshot_result
    log(f"  ✓ Snapshot saved: snapshot_id={new_snapshot_id}, has_previous={has_previous_snapshot} for {site_name} (site_id: {site_id})")

    # 출근부 데이터 추출 및 저장 (변화 로그에서도 사용)
    log(f"  DEBUG: Extracting attendance data for {site_name} (site_id: {site_id})...")
    attendance_records = extract_attendance_data(content['content'], content['html'], extraction_mode=attendance_extraction_mode)
    if attendance_records:
        log(f"  ✓ Found {len(attendance_records)} attendance records for {site_name} (site_id: {site_id})")
        for record in attendance_records:
            log(f"    - {record['name']}: {record['times']}")
        log(f"  DEBUG: Saving attendance data for {site_name} (site_id: {site_id})...")
        save_attendance_data(site_id, attendance_records, new_snapshot_id)
        # 마지막 예약 가능 인원 저장 (문자 발송용)
        save_available_staff(site_id, attendance_records)
    else:
        log(f"  ○ No attendance records found for {site_name} (site_id: {site_id})")
        # 디버깅: 출근부 추출 실패 시 내용 일부 출력
        content_sample = content['content'][:500] if len(content['content']) > 500 else content['content']
        log(f"    Content sample: {content_sample}")
    
    # 변화 감지
    if site_id in last_snapshots:
        old_hash, old_content, old_snapshot_id = last_snapshots[site_id]
        
        log(f"  Old hash: {old_hash[:16]}... (full: {old_hash})")
        log(f"  New hash: {content_hash[:16]}... (full: {content_hash})")
        log(f"  Old content length: {len(old_content)}")
        log(f"  New content length: {len(content['content'])}")
        
        if old_hash != content_hash:
            # 변화 발생!
            log(f"  ✓✓✓ HASH CHANGED! ✓✓✓")
            log(f"  Old hash: {old_hash}")
            log(f"  New hash: {content_hash}")
            log(f"  Generating diff...")
            
            # 내용 비교 (처음 200자)
            old_preview = old_content[:200] if len(old_content) > 200 else old_content
            new_preview = content['content'][:200] if len(content['content']) > 200 else content['content']
            log(f"  Old preview: {old_preview}")
            log(f"  New preview: {new_preview}")
            
            diff_html = generate_diff(old_content, content['content'])
            log(f"  Diff HTML length: {len(diff_html)} characters")
            
            # 출근부 데이터가 있으면 변화 로그에 포함
            attendance_for_change = attendance_records if 'attendance_records' in locals() else None
            
            if save_change(site_id, old_snapshot_id, new_snapshot_id, 
                          old_content, content['content'], diff_html, 
                          site_name=site_name, attendance_records=attendance_for_change):
                log(f"✓✓✓ CHANGE DETECTED AND SAVED: {site_name} ✓✓✓")
            else:
                log(f"✗✗✗ FAILED TO SAVE CHANGE: {site_name} ✗✗✗")
        else:
            log(f"○ No change: {site_name} (hash matches)")
            log(f"  Hash: {old_hash}")
            log(f"  DEBUG: About to compare old_content and new_content. old_len={len(old_content)}, new_len={len(content['content'])}")
            # 해시는 같지만 내용이 다를 수 있는지 확인 (디버깅용)
            if old_content != content['content']:
                log(f"  ⚠⚠⚠ WARNING: Hash matches but content differs! This should not happen. ⚠⚠⚠")
                log(f"  Old content length: {len(old_content)}, New content length: {len(content['content'])}")
                # 처음 100자 비교
                if old_content[:100] != content['content'][:100]:
                    log(f"  First 100 chars differ!")
                    log(f"  Old first 100: {old_content[:100]}")
                    log(f"  New first 100: {content['content'][:100]}")
                log(f"  DEBUG: Skipping further comparison for this case and proceeding.")
            # continue  # 다음 사이클로 바로 넘어가도록 변경 (옵션)
    else:
        # 메모리에 없음 - DB에서 확인 필요
        log(f"  Memory has no snapshot for {site_name}, checking DB...")
        
        # has_previous_snapshot가 False면 무조건 초기 로그 생성
        # has_previous_snapshot가 True면 DB에서 최신 스냅샷을 가져와서 비교
        if not has_previous_snapshot:
            # DB에도 스냅샷이 없거나 초기 로그가 없음 - 초기 로그 생성
            log(f"◎ First check: {site_name} (has_previous_snapshot=False, creating initial log)")
            initial_content_escaped = html.escape(content['content'])
            content_display = initial_content_escaped[:2000]
            if len(initial_content_escaped) > 2000:
                content_display += f'<br><span style="color: #6c757d; font-style: italic;">... (총 {len(content["content"])}자, 처음 2000자만 표시)</span>'
            
            initial_diff_html = f'''<div class="diff-content" style="padding: 15px; background-color: #e7f3ff; border-left: 4px solid #5dade2; border-radius: 4px; margin: 10px 0;">
                <div style="font-weight: bold; color: #5dade2; margin-bottom: 10px; font-size: 1.1rem;">
                    <i class="bi bi-info-circle-fill"></i> 초기 감지된 내용 (모니터링 시작)
                </div>
                <div style="white-space: pre-wrap; word-wrap: break-word; font-family: 'Courier New', monospace; font-size: 0.9rem; background-color: white; padding: 10px; border-radius: 3px; border: 1px solid #dee2e6;">
                    {content_display}
                </div>
            </div>'''
            
            # 출근부 데이터가 있으면 변화 로그에 포함
            attendance_for_change = attendance_records if 'attendance_records' in locals() else None
            
            if save_change(site_id, None, new_snapshot_id, 
                          '', content['content'], initial_diff_html, 
                          change_type='initial', site_name=site_name, attendance_records=attendance_for_change):
                log(f"✓ Initial detection logged: {site_name}")
            else:
                log(f"✗ Failed to save initial detection: {site_name}")
        else:
            # DB에 스냅샷이 있고 초기 로그도 있음 - 최신 스냅샷과 비교
            log(f"  DB has previous snapshots and initial log, loading latest snapshot from DB for comparison...")
            db_snapshots = get_latest_snapshots([site_id])
            
            if site_id in db_snapshots:
                db_hash, db_content, db_snapshot_id = db_snapshots[site_id]
                log(f"  DB snapshot found: snapshot_id={db_snapshot_id}, hash={db_hash[:16]}...")
                log(f"  Current hash: {content_hash[:16]}...")
                
                if db_hash != content_hash:
                    # DB의 스냅샷과 현재 내용이 다름 - 변화 감지!
                    log(f"  ✓✓✓ HASH CHANGED (compared with DB)! ✓✓✓")
                    log(f"  DB hash: {db_hash}")
                    log(f"  New hash: {content_hash}")
                    log(f"  Generating diff...")
                    
                    diff_html = generate_diff(db_content, content['content'])
                    log(f"  Diff HTML length: {len(diff_html)} characters")
                    
                    # 출근부 데이터가 있으면 변화 로그에 포함
                    attendance_for_change = attendance_records if 'attendance_records' in locals() else None
                    
                    if save_change(site_id, db_snapshot_id, new_snapshot_id, 
                                  db_content, content['content'], diff_html,
                                  site_name=site_name, attendance_records=attendance_for_change):
                        log(f"✓✓✓ CHANGE DETECTED AND SAVED: {site_name} ✓✓✓")
                    else:
                        log(f"✗✗✗ FAILED TO SAVE CHANGE: {site_name} ✗✗✗")
                else:
                    log(f"○ No change: {site_name} (hash matches DB snapshot)")
            else:
                # DB에서 스냅샷을 찾지 못함 - 초기 로그 생성 (예외 상황)
                log(f"  Warning: has_previous_snapshot=True but no DB snapshot found, creating initial log...")
                initial_content_escaped = html.escape(content['content'])
                content_display = initial_content_escaped[:2000]
                if len(initial_content_escaped) > 2000:
                    content_display += f'<br><span style="color: #6c757d; font-style: italic;">... (총 {len(content["content"])}자, 처음 2000자만 표시)</span>'
                
                initial_diff_html = f'''<div class="diff-content" style="padding: 15px; background-color: #e7f3ff; border-left: 4px solid #5dade2; border-radius: 4px; margin: 10px 0;">
                    <div style="font-weight: bold; color: #5dade2; margin-bottom: 10px; font-size: 1.1rem;">
                        <i class="bi bi-info-circle-fill"></i> 초기 감지된 내용 (모니터링 시작)
                    </div>
                    <div style="white-space: pre-wrap; word-wrap: break-word; font-family: 'Courier New', monospace; font-size: 0.9rem; background-color: white; padding: 10px; border-radius: 3px; border: 1px solid #dee2e6;">
                        {content_display}
                    </div>
                </div>'''
                
                # 출근부 데이터가 있으면 변화 로그에 포함
                attendance_for_change = attendance_records if 'attendance_records' in locals() else None
                
                if save_change(site_id, None, new_snapshot_id, 
                              '', content['content'], initial_diff_html, 
                              change_type='initial', site_name=site_name, attendance_records=attendance_for_change):
                    log(f"✓ Initial detection logged: {site_name}")
                else:
                    log(f"✗ Failed to save initial detection: {site_name}")
    
    # 현재 스냅샷 저장
    last_snapshots[site_id] = (content_hash, content['content'], new_snapshot_id)
    
    # 전화번호 추출 및 저장
    log(f"  DEBUG: Extracting phone numbers for {site_name} (site_id: {site_id})...")
    phone_numbers = extract_phone_numbers(content['html'])
    if phone_numbers:
        log(f"  ✓ Found {len(phone_numbers)} phone numbers for {site_name} (site_id: {site_id})")
        for phone in phone_numbers:
            log(f"    - Phone: {phone}")
        log(f"  DEBUG: Saving phone numbers for {site_name} (site_id: {site_id})...")
        save_phone_numbers(site_id, phone_numbers, content['html'], site_name=site_name)
    else:
        log(f"  ○ No phone numbers found for {site_name} (site_id: {site_id})")
    
    # 체크 시간 업데이트
    update_check_time(site_id)

def main():
    """메인 루프"""
    try:
        log("=" * 50)
        log("Crawler started - 2초 간격으로 실행")
        log("=" * 50)
        
        # 중복 실행 방지
        if not check_existing_process():
            log("Exiting to prevent duplicate crawler processes...")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error in log function: {e}")
        import sys
        sys.exit(1)
    
    last_snapshots = {}  # site_id: (hash, content, snapshot_id)
    last_change_times = {}  # site_id: 마지막 변화 감지 시간 (중복 방지용)
    
    # 크롤러 시작 시 DB에서 최신 스냅샷 로드
    log("Loading latest snapshots from database...")
    initial_snapshots = get_latest_snapshots()
    if initial_snapshots:
        last_snapshots.update(initial_snapshots)
        log(f"✓ Initialized {len(initial_snapshots)} snapshots in memory")
        for site_id, (hash_val, content, snapshot_id) in initial_snapshots.items():
            log(f"  Site {site_id}: snapshot_id={snapshot_id}, hash={hash_val[:16]}...")
    else:
        log("○ No previous snapshots found in DB (will create initial logs)")
    
    while True:
        try:
            # 사이트 목록 조회
            sites = get_sites()
            
            if not sites:
                log("No active sites")
                time.sleep(2)
                continue
            
            log(f"Checking {len(sites)} sites...")
            log(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            # 사이트 목록 출력 (디버깅용)
            site_ids = [s['site_id'] for s in sites]
            log(f"  Site IDs: {site_ids}")
            
            # 메모리에 없는 사이트는 DB에서 최신 스냅샷 로드 (실행 중 추가된 사이트 처리)
            for site in sites:
                site_id = site['site_id']
                if site_id not in last_snapshots:
                    log(f"  Site {site_id} not in memory, fetching from DB before check...")
                    db_snapshots = get_latest_snapshots([site_id])
                    if site_id in db_snapshots:
                        last_snapshots[site_id] = db_snapshots[site_id]
                        log(f"  ✓ Loaded snapshot for site {site_id} from DB")
            
            # 병렬 처리로 사이트 체크 (최대 10개 동시 실행)
            max_workers = min(10, len(sites))  # 사이트 수가 10개 미만이면 사이트 수만큼만
            log(f"  Using {max_workers} parallel workers for site checking")
            
            def process_site(site):
                """개별 사이트 처리 함수"""
                try:
                    site_id = site['site_id']
                    site_name = site.get('site_name', 'Unknown')
                    
                    log(f"Processing site: {site_name} (site_id: {site_id})")
                    
                    check_site(site, last_snapshots)
                    log(f"  ✓ Completed check for {site_name} (site_id: {site_id})")
                    return {'success': True, 'site_id': site_id, 'site_name': site_name}
                except Exception as e:
                    log(f"✗✗✗ ERROR processing site {site.get('site_name', 'N/A')} (site_id: {site.get('site_id', 'N/A')}) ✗✗✗")
                    log(f"  Error details: {str(e)}")
                    import traceback
                    log(f"  Traceback: {traceback.format_exc()}")
                    return {'success': False, 'site_id': site.get('site_id'), 'site_name': site.get('site_name'), 'error': str(e)}
            
            # ThreadPoolExecutor로 병렬 실행
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_site = {executor.submit(process_site, site): site for site in sites}
                
                for future in as_completed(future_to_site):
                    result = future.result()
                    if result['success']:
                        log(f"  ✓ Successfully processed: {result['site_name']} (site_id: {result['site_id']})")
                    else:
                        log(f"  ✗ Failed to process: {result.get('site_name', 'Unknown')} (site_id: {result.get('site_id', 'Unknown')})")

            # 전체 사이클 후 2초 대기
            log("--------------------------------------------------")
            log(f"Finished cycle. Waiting for 2 seconds...")
            time.sleep(2)
            
        except KeyboardInterrupt:
            log("Crawler stopped by user")
            cleanup_pid_file()
            break
        except Exception as e:
            log(f"Main loop error: {str(e)}")
            time.sleep(2)
    
    # 정상 종료 시에도 PID 파일 정리
    cleanup_pid_file()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nCrawler stopped by user")
        cleanup_pid_file()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        cleanup_pid_file()
        raise


