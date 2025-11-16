# OCR 설치 가이드

이미지에서 텍스트를 추출하여 변화를 감지하기 위해 OCR 기능이 추가되었습니다.

## 설치 옵션

두 가지 OCR 라이브러리를 지원합니다:

### 옵션 1: pytesseract (권장 - 가볍고 메모리 효율적)

```bash
# GCP 서버에 접속
cd /root/mailcenter/sound

# Tesseract OCR 엔진 설치 (시스템 패키지)
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-kor

# Python 래퍼 설치
pip3 install pytesseract pillow
```

**장점:**
- 메모리 사용량 적음
- 설치 빠름
- 시스템 패키지로 관리 가능

**단점:**
- 한국어 인식률이 easyocr보다 약간 낮을 수 있음

### 옵션 2: easyocr (정확도 높지만 메모리 많이 사용)

```bash
# GCP 서버에 접속
cd /root/mailcenter/sound

# 필요한 패키지 설치
pip3 install easyocr pillow
```

**장점:**
- 한국어 인식률 높음
- 딥러닝 기반

**단점:**
- 메모리 많이 사용 (설치 시 MemoryError 발생 가능)
- 첫 실행 시 모델 다운로드 필요 (약 100MB)
- 설치 시간 오래 걸림

## 메모리 부족 오류 발생 시

`easyocr` 설치 중 `MemoryError`가 발생하면:
1. **옵션 1 (pytesseract) 사용 권장**
2. 또는 스왑 메모리 추가 후 easyocr 설치

## 설치 확인

```bash
python3 -c "import easyocr; import PIL; print('OCR libraries installed successfully')"
```

## 첫 실행 시

`easyocr`는 첫 실행 시 모델 파일을 다운로드합니다 (약 100MB). 
이 과정은 시간이 걸릴 수 있지만, 한 번만 다운로드됩니다.

## 작동 방식

1. 크롤러가 이미지 태그를 발견하면
2. 이미지 파일을 다운로드
3. OCR로 텍스트 추출 (예: "반가 12~15 그래 12,13,14,15 맞아요 15,16,19")
4. 추출된 텍스트를 컨텐츠에 포함
5. 텍스트가 변경되면 해시가 달라져서 변화 감지

## 예상 로그

```
[2025-11-16 03:10:55] Checking 세번재 (selector: 'body')
[2025-11-16 03:10:55]     Found image 1: tracker/6v.jpg
[2025-11-16 03:10:55]       Extracting text from image: https://...
[2025-11-16 03:10:56]       OCR extracted text: 반가 12~15 그래 12,13,14,15 맞아요 15,16,19...
[2025-11-16 03:10:56]     Found image 1: tracker/6v.jpg (OCR text: 반가 12~15 그래 12,13,14,15...)
```

## 문제 해결

### ImportError: No module named 'easyocr'
```bash
pip3 install easyocr
```

### ImportError: No module named 'PIL'
```bash
pip3 install pillow
```

### OCR이 너무 느림
- 첫 실행 시 모델 다운로드로 인해 느릴 수 있습니다
- 이후 실행은 더 빠릅니다
- GPU가 있으면 `gpu=True`로 설정 가능 (GCP_CRAWLER.py 수정)

### OCR이 텍스트를 인식하지 못함
- 이미지 품질이 낮으면 인식률이 떨어질 수 있습니다
- 신뢰도 30% 이상만 사용하도록 설정되어 있습니다
- 필요시 `extract_text_from_image` 함수의 `confidence > 0.3` 값을 조정

