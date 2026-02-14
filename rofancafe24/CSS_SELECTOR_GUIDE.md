# CSS 선택자 사용 가이드

## 실제 사용 예시

### 예시: XE 게시판 게시물
```html
<article>
  <div class="document_383066343_382953716 xe_content">
    <img src="https://kissinfo.co.kr/yc/data/editor/2511/...gif">
    <img src="https://kissinfo.co.kr/yc/data/editor/2511/...jpg">
  </div>
</article>
```

**선택자 옵션:**
1. `article` - article 태그 전체 (가장 간단)
2. `article .xe_content` - article 안의 xe_content 클래스를 가진 요소 (더 구체적)
3. `.xe_content` - xe_content 클래스를 가진 모든 요소

**권장**: `article` 또는 `article .xe_content`

## 기본 사용법

### 1. 단일 클래스 선택
```html
<div class="rd_body">
```
**선택자**: `.rd_body`

### 2. 여러 클래스 선택 (모두 가진 요소)
```html
<div class="rd_body clear">
```
**선택자**: `.rd_body.clear` (점 사이에 공백 없음!)

⚠️ **주의**: `rd_body clear` (공백 있음)가 아니라 `.rd_body.clear` (점으로 연결)로 입력해야 합니다!

### 3. 태그와 클래스 조합
```html
<div class="rd_body clear">
```
**선택자**: `div.rd_body.clear`

### 4. ID 선택
```html
<div id="main-content">
```
**선택자**: `#main-content`

### 5. 복합 선택자
```html
<div class="container">
  <div class="rd_body clear">
    <p>텍스트</p>
  </div>
</div>
```
**선택자**: `.container .rd_body.clear` (자손 선택)
**선택자**: `.container > .rd_body.clear` (직계 자식 선택)

## 실제 예시

### 예시 1: 출근부 페이지
```html
<div class="rd_body clear">
  <div>1일차 9번 15:00~21:00</div>
  <div>7일차 소다 13시 14시 두타임</div>
</div>
```

**선택자 입력**: `.rd_body.clear`

이렇게 하면 `<div class="rd_body clear">` 안의 모든 텍스트가 인식됩니다:
- "1일차 9번 15:00~21:00"
- "7일차 소다 13시 14시 두타임"
- "이벤트제외(12)" 등 모든 텍스트

### 예시 2: 특정 요소만 선택
```html
<div class="rd_body clear">
  <div class="schedule-item">1일차 9번</div>
  <div class="schedule-item">7일차 소다</div>
</div>
```

**선택자 입력**: `.rd_body.clear .schedule-item`

이렇게 하면 각 `schedule-item`의 텍스트만 인식됩니다.

## 텍스트 인식

✅ **인식 가능한 것들:**
- 선택한 요소 안의 모든 텍스트
- 자식 요소의 텍스트도 모두 포함
- 공백, 줄바꿈은 공백으로 변환됨

**예시:**
```html
<div class="rd_body clear">
  <div>1일차</div>
  <div>9번</div>
  <div>15:00~21:00</div>
</div>
```

선택자 `.rd_body.clear`를 사용하면:
**인식되는 텍스트**: "1일차 9번 15:00~21:00"

## 선택자 테스트 방법

브라우저 개발자 도구(F12)에서 테스트할 수 있습니다:

1. F12를 눌러 개발자 도구 열기
2. Console 탭 선택
3. 다음 명령어 입력:
```javascript
document.querySelector('.rd_body.clear')
```
또는
```javascript
document.querySelectorAll('.rd_body.clear')
```

요소가 선택되면 올바른 선택자입니다!

## 자주 하는 실수

❌ **잘못된 입력:**
- `rd_body clear` (점 없음)
- `.rd_body .clear` (공백 있음 - 자손 선택자가 됨)
- `rd_body.clear` (점 앞에 점 없음)

✅ **올바른 입력:**
- `.rd_body.clear` (두 클래스를 모두 가진 요소)
- `.rd_body` (rd_body 클래스만 가진 요소)
- `.clear` (clear 클래스만 가진 요소)

## 선택자 우선순위

여러 선택자가 매칭될 수 있는 경우:
1. 가장 구체적인 선택자가 우선
2. 여러 요소가 선택되면 모든 요소의 텍스트가 합쳐짐

**예시:**
```html
<div class="rd_body clear">
  <div class="item">항목1</div>
</div>
<div class="rd_body">
  <div class="item">항목2</div>
</div>
```

- 선택자 `.rd_body.clear` → "항목1"만
- 선택자 `.rd_body` → "항목1 항목2" 모두
- 선택자 `.item` → "항목1 항목2" 모두

