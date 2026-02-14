#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCP 서버용 웹 모니터링 크롤러
카페24 API를 호출하여 2초 간격으로 크롤링
pkill -f GCP_CRAWLER.py && cd /root/mailcenter/sound && nohup python3 GCP_CRAWLER.py > crawler.log 2>&1 &

pkill -f GCP_CRAWLER.py 
python3 GCP_CRAWLER.py
"""

import requests
import time
import html
import os
import sys
from datetime import datetime, date
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# 다른 모듈에서 함수 import
from fetchers import fetch_content, fetch_content_sexbam, fetch_content_sexbam2, parse_attendance_from_og_title
from extractors import generate_hash, generate_diff, extract_attendance_data, extract_phone_numbers, format_attendance_info

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
    # Windows와 Linux 모두 지원하는 PID 파일 경로
    import tempfile
    pid_file = os.path.join(tempfile.gettempdir(), 'gcp_crawler.pid')
    
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
    import tempfile
    pid_file = os.path.join(tempfile.gettempdir(), 'gcp_crawler.pid')
    try:
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            if pid == os.getpid():
                os.remove(pid_file)
                log(f"✓ PID file removed: {pid_file}")
    except Exception as e:
        pass  # 무시

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
    """사이트 체크
    
    Returns:
        bool: 성공하면 True, 실패하면 False
    """
    site_id = site['site_id']
    site_name = site['site_name']
    site_type = site.get('site_type', 'normal')
    target_selector = site.get('target_selector', 'body')
    attendance_extraction_mode = site.get('attendance_extraction_mode', 'both')  # 'both', 'title', 'body'
    site_url = site['site_url']
    
    log(f"Checking {site_name} (site_id: {site_id}, type: {site_type}, selector: '{target_selector}', extraction_mode: '{attendance_extraction_mode}')")
    log(f"  URL: {site_url}")
    
    # 컨텐츠 가져오기 (섹밤 유형이면 특별 처리)
    content = None
    fetch_error = None
    attendance_from_title = None  # extraction_mode='title'일 때 사용
    try:
        log(f"  Attempting to fetch content from: {site_url}")
        if site_type == 'sexbam':
            content = fetch_content_sexbam(site_url, extraction_mode=attendance_extraction_mode)
            # extraction_mode='title'이면 og:title에서 출근부 추출
            if content and attendance_extraction_mode == 'title':
                # og:title 파싱해서 출근부 데이터 추출
                soup = BeautifulSoup(content['html'], 'lxml')
                og_title = soup.find('meta', property='og:title')
                if og_title and og_title.get('content'):
                    title_text = og_title.get('content', '').strip()
                    if ' - ' in title_text:
                        title_text = title_text.rsplit(' - ', 1)[0].strip()
                    attendance_from_title = parse_attendance_from_og_title(title_text)
                    if attendance_from_title:
                        log(f"  ✓ Parsed {len(attendance_from_title)} records from og:title")
        elif site_type == 'sexbam2':
            content = fetch_content_sexbam2(site_url)
        else:
            content = fetch_content(site_url, target_selector)
    except requests.exceptions.Timeout as e:
        fetch_error = f"TIMEOUT: {str(e)}"
        log(f"✗✗✗ TIMEOUT while fetching {site_name} (site_id: {site_id}, URL: {site_url}): {str(e)} ✗✗✗")
    except requests.exceptions.ConnectionError as e:
        fetch_error = f"CONNECTION ERROR: {str(e)}"
        log(f"✗✗✗ CONNECTION ERROR while fetching {site_name} (site_id: {site_id}, URL: {site_url}): {str(e)} ✗✗✗")
    except requests.exceptions.RequestException as e:
        fetch_error = f"REQUEST ERROR: {str(e)}"
        log(f"✗✗✗ REQUEST ERROR while fetching {site_name} (site_id: {site_id}, URL: {site_url}): {str(e)} ✗✗✗")
    except Exception as e:
        fetch_error = f"EXCEPTION: {str(e)}"
        log(f"✗✗✗ Exception while fetching {site_name} (site_id: {site_id}, URL: {site_url}): {str(e)} ✗✗✗")
        import traceback
        log(f"  Traceback: {traceback.format_exc()}")
    
    if not content:
        if fetch_error:
            log(f"✗✗✗ Failed to fetch: {site_name} (site_id: {site_id}, URL: {site_url}) ✗✗✗")
            log(f"  → Error: {fetch_error}")
        else:
            log(f"✗✗✗ Failed to fetch: {site_name} (site_id: {site_id}, URL: {site_url}) ✗✗✗")
            log(f"  → Possible reasons: Connection timeout, HTTP error, or content parsing failed")
            log(f"  → Check the fetch function logs above for more details")
        return False
    
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

    # extraction_mode='title'이면 og:title에서 이미 추출된 데이터 사용
    if attendance_extraction_mode == 'title' and attendance_from_title:
        attendance_records = attendance_from_title
        log(f"  ✓ Using attendance data from og:title for {site_name} (site_id: {site_id})")
    else:
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
        # 디버깅: 전화번호를 못 찾은 경우 HTML 일부 출력 (패턴 확인용)
        # rd_body 부분만 찾아서 출력
        soup = BeautifulSoup(content['html'], 'lxml')
        rd_body = soup.select_one('.rd_body')
        if rd_body:
            log(f"    rd_body text preview: {rd_body.get_text()[:200]}")
        else:
            log(f"    rd_body not found in HTML")
    
    # 체크 시간 업데이트
    update_check_time(site_id)
    
    return True

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
                    
                    # check_site의 반환값 확인
                    success = check_site(site, last_snapshots)
                    
                    if success:
                        log(f"  ✓ Completed check for {site_name} (site_id: {site_id})")
                        return {'success': True, 'site_id': site_id, 'site_name': site_name}
                    else:
                        log(f"  ✗ Failed to check {site_name} (site_id: {site_id}) - fetch failed")
                        return {'success': False, 'site_id': site_id, 'site_name': site_name, 'error': 'Failed to fetch content'}
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


