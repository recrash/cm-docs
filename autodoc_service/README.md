# AutoDoc Service

오프라인(폐쇄망) 환경에서 동작하는 Office-less 문서 자동화 서비스입니다.

## 📋 주요 기능

- **변경관리 Word 문서 생성**: 라벨 기반 매핑으로 템플릿 구조 변경에 강건한 `.docx` 파일 생성
- **테스트 시나리오 Excel 생성**: 템플릿 기반 `.xlsx` 파일 생성  
- **변경관리 문서 목록 Excel 생성**: 여러 항목을 포함한 목록 파일 생성
- **HTML → JSON 파서**: IT지원의뢰서 HTML을 구조화된 JSON으로 변환
- **향상된 필드 매핑**: 신청자 필드에서 부서 자동 추출, 시스템별 배포자 매핑

## 🏗️ 아키텍처

```
autodoc_service/
├── app/                        # FastAPI 애플리케이션
│   ├── main.py                # API 엔드포인트
│   ├── models.py              # Pydantic 데이터 모델
│   ├── parsers/               # HTML 파서
│   │   └── itsupp_html_parser.py
│   ├── services/              # 비즈니스 로직
│   │   ├── paths.py          # 경로 관리
│   │   ├── filename.py       # 파일명 처리
│   │   ├── word_builder.py   # Word 문서 생성 (기본)
│   │   ├── label_based_word_builder.py  # 라벨 기반 Word 생성 (권장)
│   │   ├── word_payload.py   # Word 데이터 변환 로직
│   │   ├── font_styler.py    # Word 문서 폰트 스타일링
│   │   ├── excel_font_styler.py  # Excel 문서 폰트 스타일링
│   │   ├── excel_test_builder.py    # Excel 테스트 시나리오
│   │   └── excel_list_builder.py    # Excel 목록 생성
│   └── tests/                # pytest 테스트 스위트
├── templates/                # 문서 템플릿 (필수)
│   ├── template.docx        # Word 템플릿
│   ├── template.xlsx        # Excel 테스트 시나리오 템플릿  
│   └── template_list.xlsx   # Excel 목록 템플릿
├── documents/               # 생성된 문서 출력 (자동 생성)
└── wheels/                  # 오프라인 설치용 패키지 (선택사항)
```

## 🚀 빠른 시작

### 1. 시스템 요구사항
- **Python**: 3.8 이상
- **운영체제**: Windows, macOS, Linux (크로스플랫폼)
- **Office**: 불필요 (python-docx, openpyxl 사용)

### 2. 설치 및 실행

#### 자동 실행 (권장)
```bash
# macOS/Linux
./run_autodoc_service.sh

# Windows (PowerShell)
.\run_autodoc_service.ps1

# 모든 플랫폼 (Python)
python run_autodoc_service.py
```

#### 수동 설치
```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행  
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. 접속
- **API 서버**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **헬스체크**: http://localhost:8000/health

## 🔧 API 사용법

### 주요 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|------------|------|
| `POST` | `/parse-html` | HTML 파일을 JSON으로 파싱 |
| `POST` | `/create-cm-word` | Word 변경관리 문서 생성 (라벨 기반) |
| `POST` | `/create-cm-word-enhanced` | 향상된 Word 문서 생성 (raw_data 지원) |
| `POST` | `/create-test-excel` | Excel 테스트 시나리오 생성 |
| `POST` | `/create-cm-list` | Excel 변경관리 목록 생성 |
| `GET`  | `/download/{filename}` | 생성된 파일 다운로드 |

### 사용 예제

#### HTML 파싱
```bash
curl -X POST "http://localhost:8000/parse-html" \
     -F "file=@규격_확정일자.html"
```

#### Word 문서 생성
```bash
curl -X POST "http://localhost:8000/create-cm-word" \
     -H "Content-Type: application/json" \
     -d '{
       "change_id": "LIMS_20250814_1",
       "system": "울산 실험정보(LIMS)",
       "title": "시스템 구조 개선",
       "requester": "홍길동"
     }'
```

#### 향상된 Word 문서 생성 (HTML 파싱 데이터 활용)
```bash
curl -X POST "http://localhost:8000/create-cm-word-enhanced" \
     -H "Content-Type: application/json" \
     -d '{
       "change_id": "LIMS_20250814_1",
       "system": "울산 실험정보(LIMS)",
       "title": "시스템 구조 개선",
       "requester": "홍길동",
       "raw_data": {
         "신청자": "홍길동/Manager/IT운영팀/SKAX",
         "요청사유": "시스템 개선이 필요합니다",
         "요구사항 상세분석": "현재 시스템의 문제점을 해결하여..."
       }
     }'
```

#### 파일 다운로드
```bash
curl -O "http://localhost:8000/download/[250814 홍길동] 변경관리요청서 LIMS_20250814_1 시스템 구조 개선.docx"
```

## 📐 템플릿 시스템

### 라벨 기반 매핑 시스템

#### Word 템플릿 (`template.docx`)
- **라벨 기반 매핑**: 셀 인덱스 대신 라벨 텍스트를 찾아서 매핑하는 방식으로 템플릿 구조 변경에 강건
- **Table 2 특별 처리**: 기안 날짜를 Table 2, Row 3, Cell 1에 정확히 배치
- **필드 자동 보완**: 
  - 신청자 필드에서 부서명 자동 추출 (예: `홍길동/Manager/IT운영팀/SK AX` → 요청부서: `IT운영팀`)
  - 시스템별 배포자 매핑 지원 (확장 가능한 구조)
  - 목적/개선내용을 구조화된 형식으로 생성 (`1. 목적\n{요청사유}\n\n2. 주요내용\n{상세분석}`)
- **주요 매핑 필드**: 제목, 변경관리번호, 작업일시, 배포일시, 고객사, 요청부서, 요청자, 대상시스템, 작업자/배포자, 목적/개선내용

#### Excel 테스트 템플릿 (`template.xlsx`)
- **C2** ← 시스템
- **F2** ← 변경관리번호  
- **B7** ← 현업_테스트_일자 (없으면 오늘)
- **K7** ← 테스트일자 유무 (1 또는 2)

#### Excel 목록 템플릿 (`template_list.xlsx`)
- **11개 열 순서**: 배포종류, 시스템, 현업 테스트 일자, 배포일자, 요청자, IT지원의뢰서, Program, 소스명, 배포자, 변경관리번호, 변경관리문서유무

## 🧪 테스트

### 전체 테스트 실행
```bash
pytest app/tests/ -v
```

### 테스트 범위
- ✅ 템플릿 존재 및 무변경 검증 (SHA-256)
- ✅ HTML 파서 정확도 (픽스처 매칭)
- ✅ Word/Excel 빌더 좌표 매핑
- ✅ FastAPI 엔드포인트 통합 테스트
- ✅ 파일명 규칙 및 sanitize
- ✅ 에러 처리 및 검증

### 테스트 커버리지
```bash
pytest --cov=app --cov-report=html app/tests/
```

## 🔒 보안 고려사항

- **경로 순회 공격 방어**: 파일 다운로드 시 디렉터리 외부 접근 차단
- **파일명 Sanitize**: 금지 문자 제거 (`\ / : * ? " < > |`)
- **템플릿 무변경**: SHA-256 해시로 템플릿 파일 무결성 보장
- **입력 검증**: Pydantic을 통한 엄격한 데이터 검증

## 📊 성능 기준

- **HTML 파싱**: <1초
- **Word 문서 생성**: <3초
- **Excel 파일 생성**: <2초
- **메모리 사용량**: <100MB (중간 규모 문서)

## 🔧 오프라인 환경 설정

### 의존성 다운로드 (인터넷 연결된 환경)
```bash
pip download -r requirements.txt -d wheels
```

### 오프라인 설치 (폐쇄망 환경)  
```bash
pip install --no-index --find-links ./wheels -r requirements.txt
```

## 🐛 문제 해결

### 자주 발생하는 문제

1. **템플릿 파일 없음**
   ```
   FileNotFoundError: 템플릿 파일을 찾을 수 없습니다
   ```
   → `templates/` 디렉터리에 3개 템플릿 파일 확인

2. **Python 버전 문제** 
   ```
   Python 3.8 이상이 필요합니다
   ```
   → Python 버전 업그레이드 필요

3. **포트 충돌**
   ```
   OSError: [Errno 48] Address already in use
   ```
   → 다른 포트 사용: `--port 8001`

### 로그 확인
```bash
# 서버 로그는 콘솔에 실시간 출력됨
# 추가 디버깅이 필요한 경우 uvicorn 로그 레벨 조정
python -m uvicorn app.main:app --log-level debug
```

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 제공됩니다.

## 👥 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해 주세요.