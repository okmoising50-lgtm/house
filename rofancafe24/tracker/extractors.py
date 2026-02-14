#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데이터 추출 및 처리 관련 함수들
"""

import hashlib
import difflib
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from fetchers import log, remove_unwanted_elements

# format_attendance_info에서 사용하는 API 설정
CAFE24_API_URL = 'https://rofan.mycafe24.com/tracker/api/external_api.php'
API_TOKEN = 'rofan-tracker-token-2025-secure-key'

headers = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json'
}

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

def extract_attendance_data(content_text, html_content, extraction_mode='both'):
    """출근부 데이터 추출 (다양한 형식 지원, v6, 필터링 강화, 중복 제거)"""
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
            '대학생', '하유진', '올라가면', '고정11', 'hero', '부천', '히어로',
            '월', '화', '수', '목', '금', '토', '일'
        }
        
        # 불필요한 이름 패턴
        excluded_name_patterns = [
            r'.*사장$', r'.*실장$', r'.*대표$', r'.*출근부$', r'.*카톡$',
            r'^Document', r'^고맙', r'^첫\d+', r'^내상', r'^영업', r'^이벤트',
            r'^주대$', r'^집$', r'^출근부$', r'^카톡$', r'^교대$',
            r'^NF대거영입$', r'^대거영입$', r'^강남$', r'^전원$', r'^출동$',
            r'^텔래그램$', r'^후불제$', r'^new$', r'^순수업계$', r'^배우연습생$',
            r'^대학생$', r'^하유진$', r'^올라가면$', r'^고정\d+$',
            r'^\d+월\d+일$', r'^[월화수목금토일]요일$', r'^월\d+일$', r'^\d+일$'
        ]

        def parse_times_from_string(time_str_raw):
            """입력 문자열에서 시간을 파싱하여 정규화된 쉼표 구분 문자열로 반환 (0-24 범위만 허용)"""
            time_str = re.sub(r'[시분초]', '', time_str_raw)
            numbers = [int(n) for n in re.findall(r'\d+', time_str)]
            if not numbers:
                return None

            if any(n >= 25 for n in numbers):
                return None

            if '~' in time_str and len(numbers) >= 2:
                start, end = numbers[0], numbers[-1]
                if start >= 25 or end >= 25:
                    return None
                
                times = []
                if start == 24:
                    times.append(24)
                    if end < 24:
                        times.extend(range(1, end))
                elif start > end:
                    times.extend(range(start, 24))
                    if end < 24:
                        times.extend(range(0, end))
                else:
                    times.extend(range(start, end))
                
                times = [t for t in times if 0 <= t <= 24]
                if not times:
                    return None
                
                return ','.join(map(str, sorted(list(set(times)))))
            else:
                valid_times = [n for n in numbers if 0 <= n <= 24]
                if not valid_times:
                    return None
                return ','.join(map(str, sorted(list(set(valid_times)))))

        def is_excluded_name(name):
            """이름이 제외 목록에 있는지 확인"""
            name_lower = name.lower()
            for keyword in excluded_keywords:
                if keyword in name_lower:
                    return True
            for pattern in excluded_name_patterns:
                if re.match(pattern, name, re.IGNORECASE):
                    return True
            return False

        def normalize_name(name):
            """이름 정규화: NF, ACE 등의 접두사 제거하고 기본 이름 추출"""
            if '다율' in name or 'Queen' in name or '퀸' in name:
                return '다율'
            name_clean = re.sub(r'^(NF|ACE|NEW|new)\s*', '', name, flags=re.IGNORECASE)
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
            remove_unwanted_elements(soup)
            html_full_text = soup.get_text(separator=' ', strip=True)
        
        def clean_text(raw_text):
            if not raw_text:
                return ""
            text = raw_text
            text = re.sub(r'\d+월\s*\d+일', ' ', text)
            text = re.sub(r'\(\d+\.\d+\)', ' ', text)
            text = re.sub(r'\([^)]*\)', ' ', text)
            text = re.sub(r'\d+/\d+/\d+/[A-Za-z가-힣]+/[가-힣]+', ' ', text)
            text = re.sub(r'\d+/\d+/\d+/[A-Za-z가-힣]+', ' ', text)
            text = re.sub(r'\d+/\d+/\d+', ' ', text)
            text = re.sub(r'[❤️✅⭐️🎀💛💙💜💚🧡🖤🤍🤎✨]', ' ', text)
            text = re.sub(r'[\[\]]', ' ', text)
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
    """전화번호 추출 (구조적 검색 -> 텍스트 검색 -> 정규식 검색 순)"""
    phone_numbers = []
    
    if not html_content:
        log(f"  DEBUG (extract_phone_numbers): No HTML content provided")
        return phone_numbers
    
    log(f"  DEBUG (extract_phone_numbers): HTML content length: {len(html_content)} characters")
    
    soup = BeautifulSoup(html_content, 'lxml')
    remove_unwanted_elements(soup)
    
    for script in soup(["script", "style"]):
        script.extract()
    
    def normalize_phone(phone_str):
        """전화번호를 표준 형식으로 정규화 (010-1234-5678)"""
        if not phone_str:
            return None
        phone_str = phone_str.replace('.', '-').replace(' ', '-')
        digits = re.sub(r'\D', '', phone_str)
        
        if len(digits) < 9 or len(digits) > 11 or not digits.startswith('0'):
            return None
            
        if len(digits) == 11:
            return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
        elif len(digits) == 10:
            if digits.startswith('02'):
                return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
            else:
                return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        elif len(digits) == 9:
            if digits.startswith('02'):
                return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
            else:
                return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        return None

    def is_valid_phone(phone):
        return re.match(r'^0(1[016789]|2|[3-6][1-9]|70)-\d{3,4}-\d{4}$', phone)

    # 전략 0: table.et_vars 우선 검색
    for table in soup.select('table.et_vars, table.vars, table.info'):
        has_phone_label = False
        for th in table.select('th'):
            if '전화' in th.get_text():
                has_phone_label = True
                break
        
        if has_phone_label:
            text = table.get_text(separator=' ', strip=True)
            matches = re.findall(r'0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}', text)
            for raw in matches:
                norm = normalize_phone(raw)
                if norm and is_valid_phone(norm) and norm not in phone_numbers:
                    phone_numbers.append(norm)
                    log(f"  DEBUG (extract_phone_numbers): Found phone in table.et_vars (global search): {norm}")
    
    if phone_numbers:
        return phone_numbers

    # 2. 클래스가 없지만 '전화번호'가 포함된 모든 테이블 검색
    for table in soup.find_all('table'):
        has_phone_label = False
        for cell in table.find_all(['th', 'td']):
            if '전화' in cell.get_text():
                has_phone_label = True
                break
        
        if has_phone_label:
            text = table.get_text(separator=' ', strip=True)
            matches = re.findall(r'0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}', text)
            for raw in matches:
                norm = normalize_phone(raw)
                if norm and is_valid_phone(norm) and norm not in phone_numbers:
                    phone_numbers.append(norm)
                    log(f"  DEBUG (extract_phone_numbers): Found phone in general table (global search): {norm}")

    if phone_numbers:
        return phone_numbers

    # Scope Definition
    scope_element = None
    scope_element = soup.select_one('[data-docsrl]')
    if scope_element:
        log(f"  DEBUG (extract_phone_numbers): Scope restricted to [data-docsrl]")
    
    if not scope_element:
        scope_element = soup.select_one('.rd_body')
        if scope_element:
            log(f"  DEBUG (extract_phone_numbers): Scope restricted to .rd_body")
            
    if not scope_element:
        scope_element = soup.select_one('.xe_content')
        if scope_element:
            log(f"  DEBUG (extract_phone_numbers): Scope restricted to .xe_content")
    
    if not scope_element:
        scope_element = soup.find('article')
        if scope_element:
            log(f"  DEBUG (extract_phone_numbers): Scope restricted to article")

    if not scope_element:
        log(f"  DEBUG (extract_phone_numbers): No specific scope found, searching entire document (cleaned)")
        scope_element = soup

    # 전략 1: 명시적인 '전화번호' 레이블 주변 검색
    labels = scope_element.find_all(string=re.compile(r'(전화|연락)'))
    for label in labels:
        parent = label.parent
        if parent is None:
            continue
            
        text = parent.get_text(separator=' ', strip=True)
        matches = re.findall(r'0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}', text)
        for raw in matches:
            norm = normalize_phone(raw)
            if norm and is_valid_phone(norm) and norm not in phone_numbers:
                phone_numbers.append(norm)
                log(f"  DEBUG (extract_phone_numbers): Found phone near label '{label.strip()}' (same tag): {norm}")

        next_elem = parent.find_next_sibling()
        if next_elem:
            text = next_elem.get_text(separator=' ', strip=True)
            matches = re.findall(r'0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}', text)
            for raw in matches:
                norm = normalize_phone(raw)
                if norm and is_valid_phone(norm) and norm not in phone_numbers:
                    phone_numbers.append(norm)
                    log(f"  DEBUG (extract_phone_numbers): Found phone near label '{label.strip()}' (next sibling): {norm}")
        
        tr = parent.find_parent('tr')
        if tr:
            cells = tr.find_all(['th', 'td'])
            for i, cell in enumerate(cells):
                if cell == parent or parent in cell.descendants:
                    if i + 1 < len(cells):
                        next_cell = cells[i+1]
                        text = next_cell.get_text(separator=' ', strip=True)
                        matches = re.findall(r'0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}', text)
                        for raw in matches:
                            norm = normalize_phone(raw)
                            if norm and is_valid_phone(norm) and norm not in phone_numbers:
                                phone_numbers.append(norm)
                                log(f"  DEBUG (extract_phone_numbers): Found phone in table row next cell: {norm}")

    if phone_numbers:
        return phone_numbers

    # 전략 2: Scope 내 텍스트에서 정규식 검색
    scope_text = scope_element.get_text(separator=' ', strip=True)
    
    matches = re.findall(r'010[-.\s]?\d{4}[-.\s]?\d{4}', scope_text)
    for raw in matches:
        norm = normalize_phone(raw)
        if norm and is_valid_phone(norm) and norm not in phone_numbers:
            phone_numbers.append(norm)
            log(f"  DEBUG (extract_phone_numbers): Found 010 phone in scope text: {norm}")
            
    if not phone_numbers:
        matches = re.findall(r'0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}', scope_text)
        for raw in matches:
            norm = normalize_phone(raw)
            if norm and is_valid_phone(norm) and norm not in phone_numbers:
                phone_numbers.append(norm)
                log(f"  DEBUG (extract_phone_numbers): Found general phone in scope text: {norm}")

    if not phone_numbers:
        log(f"  DEBUG (extract_phone_numbers): No phone numbers found in scope")

    return phone_numbers





