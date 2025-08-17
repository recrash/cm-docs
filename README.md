# TestscenarioMaker 모노레포

Git 저장소 변경사항을 분석하여 한국어 테스트 시나리오를 자동 생성하는 AI 기반 통합 솔루션

## 🌟 프로젝트 개요

이 모노레포는 TestscenarioMaker 생태계의 두 가지 주요 컴포넌트를 통합합니다:

- **Webservice (웹 서비스)**: Pseudo-MSA 아키텍처 기반의 풀스택 웹 애플리케이션
- **CLI (명령줄 도구)**: 브라우저 통합 및 URL 프로토콜을 지원하는 크로스플랫폼 CLI 도구

두 프로젝트는 독립적으로 개발되고 배포되지만, 공통된 목표를 가지고 상호 보완적으로 작동합니다.

## 📁 프로젝트 구조

```
cm-docs/
├── webservice/          # TestscenarioMaker 웹 서비스
│   ├── frontend/        # React + TypeScript 프론트엔드
│   ├── backend/         # FastAPI 백엔드 서비스
│   ├── src/             # 핵심 분석 모듈
│   └── tests/           # 테스트 슈트 (E2E, API, 단위)
├── cli/                 # TestscenarioMaker CLI 도구
│   ├── src/ts_cli/      # CLI 핵심 로직
│   ├── scripts/         # 빌드 및 배포 스크립트
│   └── tests/           # CLI 테스트 슈트
├── autodoc_service/     # AutoDoc 문서 자동화 서비스
│   ├── app/             # FastAPI 애플리케이션
│   ├── templates/       # 문서 템플릿 (Word, Excel)
│   ├── documents/       # 생성된 문서 출력
│   └── testHTML/        # HTML 테스트 파일
├── README.md            # 통합 프로젝트 문서
└── pyproject.toml       # 공통 개발 환경 설정
```

## 🎯 Webservice - TestscenarioMaker 웹 서비스

### 기술 스택
- **프론트엔드**: React 18 + TypeScript + Material-UI + Vite
- **백엔드**: FastAPI + Python (Pseudo-MSA 아키텍처)
- **AI/LLM**: Ollama 통합 (qwen3:8b 모델)
- **벡터 DB**: ChromaDB (RAG 시스템)
- **테스팅**: Jest + Playwright (E2E) + pytest (API)

### 주요 기능

#### 🧠 AI 기반 시나리오 생성
- Git 커밋 메시지 및 코드 diff 자동 분석
- Ollama qwen3 모델을 활용한 지능형 시나리오 생성
- 표준화된 Excel 템플릿 기반 테스트 시나리오 출력
- WebSocket 기반 실시간 생성 진행상황 표시

#### 🔍 RAG(검색 증강 생성) 시스템
- ChromaDB를 활용한 벡터 기반 문서 검색
- ko-sroberta-multitask 모델 기반 한국어 임베딩
- DOCX, TXT, PDF 문서 자동 인덱싱
- 오프라인 환경 지원을 위한 로컬 임베딩 모델

#### 📊 피드백 및 분석 시스템
- 5점 척도 사용자 피드백 수집
- 피드백 기반 자동 품질 개선
- 종합적인 분석 대시보드 및 트렌드 시각화
- SQLite 기반 데이터 무결성 보장

### 개발 환경 설정

#### 🔧 MSA 기반 독립 환경 구성

각 서비스는 독립된 Python 가상환경을 사용합니다:

```bash
# Webservice (Python 3.13 환경)
cd webservice
source .venv/bin/activate
python --version  # Python 3.13.5

# CLI (Python 3.13 환경) 
cd cli
source .venv/bin/activate  
python --version  # Python 3.13.5

# AutoDoc Service (Python 3.12 환경 - 문서 생성 안정성)
cd autodoc_service
source .venv312/bin/activate
python --version  # Python 3.12.11
```

#### 📦 서비스별 개발 시작

```bash
# Webservice 개발 환경
cd webservice
source .venv/bin/activate
pip install -r requirements.txt
npm install

# PYTHONPATH 설정 (필수 - src/ 모듈 임포트용)
export PYTHONPATH=$(pwd):$PYTHONPATH

# 백엔드 서버 시작 (포트 8000)
cd webservice/backend && python -m uvicorn main:app --reload --port 8000

# 프론트엔드 개발 서버 시작 (포트 3000) - 프로젝트 루트에서 실행
npm run dev

# 전체 테스트 실행
npm run test:all
```

### 테스팅
- **E2E 테스트**: `npm run test:e2e` (Playwright 필수)
- **API 테스트**: `npm run test:api` (pytest)
- **프론트엔드 테스트**: `npm run test` (Jest)

## ⚡ CLI - TestscenarioMaker 명령줄 도구

### 기술 스택
- **코어**: Python 3.8+ + Click + Rich
- **네트워킹**: httpx + tenacity (재시도 로직)
- **빌드**: PyInstaller (크로스플랫폼 실행파일)
- **테스팅**: pytest (단위/통합/E2E)

### 주요 기능

#### 🔧 로컬 저장소 분석
- Git 저장소 변경사항 자동 분석
- 브랜치 간 차이점 비교 (기본: origin/develop → HEAD)
- 작업 중인 변경사항 포함 분석

#### 🌐 브라우저 통합
- `testscenariomaker://` 커스텀 URL 프로토콜 지원
- 크로스플랫폼 URL 프로토콜 자동 등록
- macOS 전용 헬퍼 앱으로 브라우저 샌드박스 제약 우회

#### 🎨 사용자 경험
- 한국어 사용자 인터페이스
- Rich 라이브러리 기반 향상된 콘솔 출력
- JSON 및 텍스트 형식 출력 지원

### 설치 및 사용

#### 사전 빌드된 실행파일 사용
```bash
# Windows: TestscenarioMaker-CLI-Setup.exe 설치
# macOS: .dmg 파일 설치 (헬퍼 앱 포함)
# Linux: AppImage 또는 직접 빌드
```

#### 소스코드에서 개발 설치
```bash
# CLI 디렉토리로 이동
cd cli

# 독립 환경 활성화
source .venv/bin/activate

# 개발 모드 설치
pip install -e .

# CLI 실행
ts-cli analyze /path/to/repository
```

#### 빌드
```bash
cd cli

# 크로스플랫폼 실행파일 빌드
python scripts/build.py

# Windows 설치 프로그램 생성 (Windows에서)
makensis scripts/setup_win.nsi

# macOS DMG 및 헬퍼 앱 생성 (macOS에서)
python scripts/create_dmg.py
```

### 테스팅
```bash
cd cli

# 전체 테스트 슈트
pytest --cov=ts_cli --cov-report=html

# 테스트 유형별 실행
pytest -m unit          # 단위 테스트
pytest -m integration   # 통합 테스트  
pytest -m e2e           # End-to-End 테스트
```

## 📄 AutoDoc Service - 문서 자동화 서비스

Office-less 환경에서 동작하는 HTML 기반 문서 자동화 솔루션입니다.

### 기술 스택
- **백엔드**: FastAPI + Python 3.12 + Pydantic (문서 생성 안정성 위해 3.12 사용)
- **문서 생성**: python-docx (Word) + openpyxl (Excel)
- **HTML 파싱**: BeautifulSoup4 + lxml
- **테스팅**: pytest + AsyncHTTPX client

### 주요 기능

#### 📝 자동 문서 생성
- **변경관리 Word 문서**: 라벨 기반 매핑으로 **12개 필드 완전 매핑** 보장하는 `.docx` 생성
- **Enhanced Payload System**: HTML 파싱 데이터에서 누락 필드 자동 보완
- **Excel 테스트 시나리오**: 템플릿 기반 `.xlsx` 파일 생성
- **Excel 변경관리 목록**: 여러 항목을 포함한 목록 파일 생성
- **HTML → JSON 파서**: IT지원의뢰서 HTML을 구조화된 JSON으로 변환

#### 🎨 폰트 일관성 보장
- **전체 문서 맑은 고딕**: 템플릿 텍스트와 매핑 데이터 모두에 일관된 폰트 적용
- **향상된 필드 매핑**: 신청자 필드에서 부서 자동 추출, 시스템별 배포자 매핑
- **구조화된 내용 생성**: 목적/개선내용을 "1. 목적\n2. 주요 내용" 형식으로 자동 변환
- **HTML 태그 처리**: `<br>` 태그를 줄바꿈으로 자동 변환하여 올바른 문서 형식 보장

### 빠른 시작

```bash
# AutoDoc Service 디렉토리로 이동
cd autodoc_service

# 독립 환경 활성화 (Python 3.12)
source .venv312/bin/activate

# 자동 실행 (권장)
python run_autodoc_service.py

# 수동 실행
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 브라우저에서 API 문서 확인
open http://localhost:8000/docs
```

### API 사용 예제

#### 권장 워크플로우 (완전한 필드 매핑)
```bash
# 1. HTML 파싱하여 구조화된 데이터 추출
curl -X POST "http://localhost:8000/parse-html" \
     -F "file=@testHTML/충유오더.html"

# 2. 향상된 엔드포인트로 완전한 Word 문서 생성 (12개 필드 모두 매핑)
curl -X POST "http://localhost:8000/create-cm-word-enhanced" \
     -H "Content-Type: application/json" \
     -d '{
       "raw_data": {
         "제목": "[Bug 개선] 시스템 구조 개선",
         "처리자_약칭": "홍길동",
         "작업일시": "08/06 18:00",
         "배포일시": "08/07 13:00",
         "요청사유": "시스템 성능 개선 필요",
         "요구사항 상세분석": "1. 성능 최적화<br>2. 안정성 향상"
       },
       "change_request": {
         "change_id": "TEST_001",
         "system": "테스트 시스템", 
         "title": "시스템 구조 개선",
         "requester": "홍길동"
       }
     }'

# 3. 생성된 완전한 문서 다운로드
curl -O "http://localhost:8000/download/[250816 홍길동] 변경관리요청서 TEST_001 시스템 구조 개선.docx"
```

#### 단순 워크플로우 (기본 정보만)
```bash
# 기본 정보로만 문서 생성 (일부 필드 누락 가능)
curl -X POST "http://localhost:8000/create-cm-word-enhanced" \
     -H "Content-Type: application/json" \
     -d '{
       "change_request": {
         "change_id": "TEST_001",
         "system": "테스트",
         "title": "제목",
         "requester": "작성자"
       }
     }'
```

### 테스트

```bash
# 전체 테스트 실행
pytest app/tests/ -v

# 커버리지 포함 테스트
pytest --cov=app --cov-report=html app/tests/
```

## 🛠 공통 개발 환경

### MSA 기반 독립 환경 관리
- **Webservice**: Python 3.13 환경 (`webservice/.venv/`) + `requirements.txt` + `package.json`
- **CLI**: Python 3.13 환경 (`cli/.venv/`) + `requirements.txt` + `requirements-dev.txt`  
- **AutoDoc Service**: Python 3.12 환경 (`autodoc_service/.venv312/`) + `requirements.txt`
- **공통**: 루트 `pyproject.toml` (개발 도구 설정)

### 통합된 설정 관리
- **개발 가이드**: 루트 `CLAUDE.md` (통합 개발 지침)
- **Git 무시 설정**: 루트 `.gitignore` (모든 프로젝트 패턴 포괄)
- **구성 중복 제거**: 각 하위 프로젝트의 개별 설정 파일 통합 완료

### 코드 품질
```bash
# 코드 포맷팅 (프로젝트 루트에서)
black webservice/src webservice/backend cli/src cli/tests autodoc_service/app
isort webservice/src webservice/backend cli/src cli/tests autodoc_service/app

# 린팅
flake8 webservice/src webservice/backend cli/src cli/tests autodoc_service/app

# 타입 체크
mypy webservice/src cli/src autodoc_service/app
```

### Git 관리
이 모노레포는 Git subtree를 사용하여 구성되었습니다:

```bash
# 서브트리 업데이트 (필요시)
git subtree pull --prefix=webservice https://github.com/recrash/TestscenarioMaker.git main --squash
git subtree pull --prefix=cli https://github.com/recrash/TestscenarioMaker-CLI.git main --squash

# 서브트리 푸시 (필요시)
git subtree push --prefix=webservice https://github.com/recrash/TestscenarioMaker.git main
git subtree push --prefix=cli https://github.com/recrash/TestscenarioMaker-CLI.git main
```

## 🚀 배포 및 CI/CD

### 독립적인 배포 파이프라인
각 서브프로젝트는 독립적인 CI/CD 파이프라인을 가집니다:

- **Webservice**: Pseudo-MSA 서비스별 독립 배포
  - API 테스트, E2E 테스트, 서비스별 배포 검증
  - WebSocket 연결 및 실시간 기능 검증

- **CLI**: 크로스플랫폼 패키지 및 설치 프로그램 빌드
  - Windows 설치 프로그램 (.exe)
  - macOS 디스크 이미지 (.dmg) + 헬퍼 앱
  - Linux AppImage 또는 패키지

### 환경별 배포

#### 🚀 MSA 기반 독립 배포

```bash
# Webservice 프로덕션 배포 (Python 3.13)
cd webservice
source .venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH  # 필수: src/ 모듈 임포트
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# 한국어 임베딩 모델 다운로드 (오프라인 환경용)
python scripts/download_embedding_model.py

# CLI 배포 버전 생성 (Python 3.13)
cd cli
source .venv/bin/activate
python scripts/build.py

# macOS 헬퍼 앱 포함 DMG 생성 (macOS)
python scripts/create_dmg.py

# AutoDoc Service 배포 (Python 3.12)
cd autodoc_service
source .venv312/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📊 품질 보증

### 테스트 커버리지 목표
- **Webservice**: ≥80% 단위 테스트, ≥70% 통합 테스트 (Python 3.13 환경)
- **CLI**: ≥85% 전체 커버리지 (Python 3.13 환경)
- **AutoDoc Service**: ≥85% 전체 커버리지 (Python 3.12 환경)
- **E2E**: 주요 사용자 워크플로우 100% 커버

### 성능 기준
- **Webservice API**: 응답시간 <200ms, WebSocket 연결 <1초 (Python 3.13)
- **CLI**: 저장소 분석 <30초, URL 프로토콜 처리 <5초 (Python 3.13)
- **AutoDoc Service**: HTML 파싱 <1초, Word 생성 <3초, Excel 생성 <2초 (Python 3.12)
- **빌드**: 전체 빌드 시간 <10분

## 🤝 기여 가이드라인

### 개발 워크플로우
1. 해당 서브프로젝트 디렉토리에서 독립 환경 활성화
   - `cd webservice && source .venv/bin/activate` (Python 3.13)
   - `cd cli && source .venv/bin/activate` (Python 3.13)
   - `cd autodoc_service && source .venv312/bin/activate` (Python 3.12)
2. 독립적인 테스트 슈트 실행 및 통과 확인
3. 코드 품질 도구 실행 (black, isort, flake8)
4. 커밋 메시지는 서브프로젝트 접두어 사용: `[webservice]`, `[cli]`, 또는 `[autodoc_service]`

### 이슈 및 PR
- 서브프로젝트별로 라벨링: `webservice`, `cli`, `autodoc_service`, `monorepo`
- 독립적인 Python 환경 및 CI/CD 파이프라인 고려사항 명시
- 크로스플랫폼 호환성 검증 필수
- MSA 원칙 준수: 서비스별 독립성 보장

## 📝 라이선스

MIT License - 각 서브프로젝트의 라이선스 파일 참조

## 🔗 관련 링크

- **Webservice Documentation**: [webservice/README.md](webservice/README.md)
- **CLI Documentation**: [cli/README.md](cli/README.md)
- **통합 개발 가이드**: [CLAUDE.md](CLAUDE.md)
- **Pull Request 히스토리**: [PR_HISTORY.md](PR_HISTORY.md)

---

각 서브프로젝트는 독립적으로 개발되고 배포되며, 이 모노레포는 통합된 이슈 트래킹과 개발 환경을 제공합니다.
