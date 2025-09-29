# TestscenarioMaker 모노레포

Git/SVN 저장소 변경사항을 분석하여 한국어 테스트 시나리오를 자동 생성하는 AI 기반 통합 솔루션

## 🌟 프로젝트 개요

이 모노레포는 TestscenarioMaker 생태계의 세 가지 주요 컴포넌트를 통합합니다:

- **Webservice (웹 서비스)**: Pseudo-MSA 아키텍처 기반의 풀스택 웹 애플리케이션
- **CLI (명령줄 도구)**: Git/SVN 저장소를 지원하는 크로스플랫폼 CLI 도구
- **AutoDoc Service**: HTML 기반 문서 자동화 서비스

세 프로젝트는 독립적으로 개발되고 배포되지만, **다중 VCS 지원**과 **AI 기반 분석**이라는 공통된 목표를 가지고 상호 보완적으로 작동합니다.

## 📁 프로젝트 구조

```
cm-docs/
├── webservice/          # TestscenarioMaker 웹 서비스
│   ├── app/             # 통합 FastAPI 애플리케이션
│   │   ├── main.py      # FastAPI 애플리케이션 진입점 with lifespan manager
│   │   ├── api/         # API 라우터 및 모델
│   │   │   ├── routers/ # 도메인별 API 엔드포인트 (scenario, feedback, rag, files)
│   │   │   └── models/  # Pydantic 데이터 모델
│   │   ├── core/        # 핵심 비즈니스 로직 (리팩토링된 src/)
│   │   │   ├── vector_db/       # RAG 벡터 데이터베이스
│   │   │   ├── config_loader.py, git_analyzer.py
│   │   │   ├── excel_writer.py, llm_handler.py
│   │   │   └── logging_config.py, prompt_*.py
│   │   └── services/    # 비즈니스 로직 레이어
│   ├── frontend/        # React + TypeScript 프론트엔드
│   │   ├── src/         # React 소스 코드
│   │   │   ├── components/  # React 컴포넌트들
│   │   │   ├── services/    # API 클라이언트 서비스
│   │   │   ├── types/       # TypeScript 타입 정의
│   │   │   └── utils/       # 유틸리티 함수들
│   │   └── package.json # Node.js 의존성
│   ├── data/            # 환경변수 기반 데이터 디렉토리 (개발환경 기본값)
│   │   ├── logs/        # 로그 파일
│   │   ├── models/      # AI 임베딩 모델
│   │   ├── documents/   # 생성된 문서
│   │   ├── templates/   # 템플릿 파일
│   │   └── outputs/     # Excel 출력
│   ├── src/             # 기존 핵심 로직 (app/core/로 이관됨)
│   └── tests/           # 테스트 슈트 (단위, API, 통합, E2E)
│       ├── unit/        # 단위 테스트
│       ├── api/         # API 테스트
│       ├── integration/ # 통합 테스트
│       └── e2e/         # E2E 테스트 (미래)
├── cli/                 # TestscenarioMaker CLI 도구
│   ├── src/ts_cli/      # CLI 핵심 로직
│   ├── scripts/         # 빌드 및 배포 스크립트
│   └── tests/           # CLI 테스트 슈트
├── autodoc_service/     # AutoDoc 문서 자동화 서비스
│   ├── app/             # FastAPI 애플리케이션
│   ├── data/            # 환경변수 기반 데이터 디렉토리 (개발환경 기본값)
│   │   ├── logs/        # 로그 파일
│   │   ├── templates/   # 문서 템플릿 (Word, Excel)
│   │   └── documents/   # 생성된 문서 출력
│   └── testHTML/        # HTML 테스트 파일
├── scripts/             # 공통 스크립트 및 유틸리티
├── infra/               # 인프라 설정 (nginx 등)
├── README.md            # 통합 프로젝트 문서
├── CLAUDE.md            # Claude Code 개발 가이드
└── pyproject.toml       # 공통 개발 환경 설정
```

## 🎯 Webservice - TestscenarioMaker 웹 서비스

### 기술 스택
- **프론트엔드**: React 18 + TypeScript + Material-UI + Vite
- **백엔드**: FastAPI + Python 3.12 (Pseudo-MSA 아키텍처, 통합 앱 구조)
- **AI/LLM**: Ollama 통합 (qwen3:8b 모델)
- **벡터 DB**: ChromaDB (RAG 시스템)
- **테스팅**: Vitest + Playwright (E2E) + pytest (API)

### 주요 기능

#### 🧠 AI 기반 시나리오 생성
- **다중 VCS 지원**: Git 및 SVN 저장소 모두 완전 지원
- **자동 저장소 감지**: Git/SVN 저장소 타입 자동 인식 및 분석
- 커밋 메시지 및 코드 diff 자동 분석 (Git 브랜치, SVN 리비전)
- Ollama qwen3 모델을 활용한 지능형 시나리오 생성
- 표준화된 Excel 템플릿 기반 테스트 시나리오 출력
- WebSocket 기반 실시간 생성 진행상황 표시
- **강화된 JSON 파싱**: LLM 응답 다중 형식 지원 (`<json>` 태그, ````json` 블록)

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

각 서비스는 독립된 Python 가상환경과 환경변수 기반 데이터 경로를 사용합니다:

```bash
# Webservice (Python 3.12 환경 - 통합 앱 구조)
cd webservice
source .venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH  # app.core 모듈 임포트용
python --version  # Python 3.12.x

# CLI (Python 3.13 환경) 
cd cli
source .venv/bin/activate  
python --version  # Python 3.13.5

# AutoDoc Service (Python 3.12 환경 - 문서 생성 안정성)
cd autodoc_service
source .venv312/bin/activate
python --version  # Python 3.12.11
```

#### ⚠️ ChromaDB 의존성 주의사항

**중요**: Webservice는 ChromaDB의 jsonschema 의존성 충돌 문제로 인해 **제약조건 파일을 반드시 사용**해야 합니다.

```bash
# ✅ 올바른 설치 방법
pip install -r requirements.txt -c pip.constraints.txt

# ❌ 잘못된 설치 방법 (의존성 충돌 발생)
pip install -r requirements.txt
```

#### 📦 서비스별 개발 시작

```bash
# Webservice 개발 환경
cd webservice
source .venv/bin/activate
pip install -r requirements.txt -c pip.constraints.txt  # 제약조건 파일 필수!
npm install

# PYTHONPATH 설정 (필수 - app.core 모듈 임포트용)
export PYTHONPATH=$(pwd):$PYTHONPATH

# 프로덕션 환경변수 (선택적 - 미설정시 data/ 서브디렉토리 사용)
export WEBSERVICE_DATA_PATH="/path/to/webservice/data"    # 프로덕션 전용
export AUTODOC_DATA_PATH="/path/to/autodoc/data"          # 프로덕션 전용

# 백엔드 서버 시작 (포트 8000) - Webservice API
cd webservice && python -m uvicorn app.main:app --reload --port 8000

# 프론트엔드 개발 서버 시작 (개발: 3000, 운영: nginx 80)
cd webservice/frontend && npm run dev

# 전체 테스트 실행
npm run test:all
```

### 테스팅
- **E2E 테스트**: `npm run test:e2e` (Playwright 필수)
- **API 테스트**: `npm run test:api` (pytest)
- **프론트엔드 테스트**: `npm run test` (Vitest)

## ⚡ CLI - TestscenarioMaker 명령줄 도구

### 기술 스택
- **코어**: Python 3.8+ + Click + Rich
- **VCS 지원**: GitPython (Git), subprocess (SVN)
- **네트워킹**: httpx + tenacity (재시도 로직)
- **빌드**: PyInstaller (크로스플랫폼 실행파일)
- **테스팅**: pytest (단위/통합/E2E)

### 주요 기능

#### 🔧 다중 VCS 저장소 분석
- **Git 저장소**: 브랜치 간 차이점 비교 (기본: origin/develop → HEAD), 커밋 히스토리 분석
- **SVN 저장소**: 리비전 기반 변경사항 분석, 작업 복사본 상태 검사
- **자동 감지**: `.git` 또는 `.svn` 디렉토리 자동 탐지로 저장소 타입 결정
- **크로스 플랫폼**: Windows, macOS, Linux 모든 환경에서 일관된 동작
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

# CLI 실행 (Git 또는 SVN 저장소 모두 지원)
ts-cli analyze /path/to/git-or-svn-repository
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
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

# 브라우저에서 API 문서 확인
open http://localhost:8001/docs
```

### API 사용 예제

#### 권장 워크플로우 (완전한 필드 매핑)
```bash
# 1. HTML 파싱하여 구조화된 데이터 추출
curl -X POST "http://localhost:8001/parse-html" \
     -F "file=@testHTML/충유오더.html"

# 2. 향상된 엔드포인트로 완전한 Word 문서 생성 (12개 필드 모두 매핑)
curl -X POST "http://localhost:8001/create-cm-word-enhanced" \
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
curl -O "http://localhost:8001/download/[250816 홍길동] 변경관리요청서 TEST_001 시스템 구조 개선.docx"
```

#### 단순 워크플로우 (기본 정보만)
```bash
# 기본 정보로만 문서 생성 (일부 필드 누락 가능)
curl -X POST "http://localhost:8001/create-cm-word-enhanced" \
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
- **Webservice (포트 8000)**: Python 3.12 환경 (`webservice/.venv/`) + `requirements.txt` + `package.json` (통합 앱 구조)
- **CLI**: Python 3.13 환경 (`cli/.venv/`) + `requirements.txt` + `requirements-dev.txt`  
- **AutoDoc Service (포트 8001)**: Python 3.12 환경 (`autodoc_service/.venv312/`) + `requirements.txt`
- **공통**: 루트 `pyproject.toml` (개발 도구 설정)

### 통합된 설정 관리
- **개발 가이드**: 루트 `CLAUDE.md` (통합 개발 지침)
- **Git 무시 설정**: 루트 `.gitignore` (모든 프로젝트 패턴 포괄)
- **구성 중복 제거**: 각 하위 프로젝트의 개별 설정 파일 통합 완료
- **환경변수 기반 경로**: 프로덕션/개발 환경 자동 감지 (커밋 f57efef)

### 환경변수 기반 데이터 경로 시스템

**프로덕션 배포 구조**:
```bash
C:\deploys\
├── apps\                    # 애플리케이션 실행 공간 (가상환경 & 코드)
│   ├── webservice\         
│   └── autodoc_service\    
├── data\                   # 영구 데이터 저장소 (업데이트 시 유지)
│   ├── webservice\
│   └── autodoc_service\
└── packages\               # 빌드 아티팩트 (.whl 파일)

# 프로덕션 환경변수 (Jenkins에서 설정)
WEBSERVICE_DATA_PATH=C:\deploys\data\webservice
AUTODOC_DATA_PATH=C:\deploys\data\autodoc_service
```

**개발 환경 기본값** (환경변수 미설정시):
- webservice: `webservice/data/`
- autodoc_service: `autodoc_service/data/`

**자동 디렉토리 생성**:
모든 경로 함수는 필요시 디렉토리를 자동으로 생성하므로 별도 설정이 불필요합니다.

### 코드 품질
```bash
# 코드 포맷팅 (프로젝트 루트에서) - 통합 앱 구조 반영
black webservice/app cli/src cli/tests autodoc_service/app
isort webservice/app cli/src cli/tests autodoc_service/app

# 린팅
flake8 webservice/app cli/src cli/tests autodoc_service/app

# 타입 체크
mypy webservice/app cli/src autodoc_service/app
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

### 🔒 폐쇄망 환경 운영 (Air-gapped)
**CRITICAL**: 본 시스템은 완전 폐쇄망 환경에서 운영되며 인터넷 연결이 전혀 불가능합니다.

#### 폐쇄망 제약사항
- ❌ **인터넷 연결 금지**: 외부 API, CDN, npm/PyPI 레지스트리 접근 불가
- ❌ **외부 AI 서비스 금지**: OpenAI, Anthropic 등 외부 AI API 사용 절대 불가
- ✅ **로컬 AI만 허용**: Ollama 로컬 서버 (qwen3:8b 모델) 사용 필수
- ✅ **오프라인 의존성**: 모든 패키지는 사전 다운로드하여 로컬 설치

### 개발 서버 정보
- **서버**: `34.64.173.97` (GCP VM T4 인스턴스 - vCPU:4, RAM:15GB)
- **오픈 포트**: 8000 (Webservice), 8001 (AutoDoc), 3000 (Dev), 80 (Nginx), 7000 (Jenkins)
- **환경**: Windows Server 2019 with Jenkins CI/CD
- **VCS 지원**: Git 및 SVN 저장소 모두 지원

### NSSM 서비스 구성
- **webservice**: `C:\deploys\apps\webservice\.venv\Scripts\python.exe` (포트 8000)
- **autodoc_service**: `C:\deploys\apps\autodoc_service\.venv312\Scripts\python.exe` (포트 8001)
- **nginx-frontend**: `C:\nginx\nginx.exe` (포트 80)

### Jenkins 설정
- **접속**: http://localhost:7000 (ID: cmdocs / PW: skc123)
- **워크스페이스**: `C:\ProgramData\Jenkins\.jenkins\workspace`

### Jenkins CI/CD 파이프라인

#### 브랜치별 배포 전략
- **main 브랜치**: 프로덕션 배포 (C:\deploys에 NSSM 서비스로 운영)
- **feature/hotfix 브랜치**: 테스트 인스턴스 배포 (동적 포트 할당)

#### 파이프라인 구성
- **통합 파이프라인**: 루트 `Jenkinsfile` (변경 감지 기반 스마트 배포)
- **서비스별 파이프라인**:
  - `webservice/Jenkinsfile.backend` (API 서비스, 포트 8000)
  - `webservice/Jenkinsfile.frontend` (React 앱, nginx 80)
  - `autodoc_service/Jenkinsfile` (문서 서비스, 포트 8001)
  - `cli/Jenkinsfile` (Windows 실행파일 빌드)

#### 변경 감지 시스템
```bash
webservice/          → Webservice 빌드/배포 (Backend + Frontend)
autodoc_service/     → AutoDoc Service 빌드/배포
cli/                 → CLI 도구 빌드 (Windows .exe)
infra/              → 전체 인프라 재배포
scripts/            → 배포 스크립트 업데이트
*.md                → 빌드 스킵 (문서 변경만)
```

#### 배포 환경 구성
**프로덕션 (main 브랜치)**:
- Backend API: http://localhost:8000 (NSSM 서비스)
- Frontend: http://localhost:80 (nginx)
- AutoDoc: http://localhost:8001 (NSSM 서비스)

**테스트 인스턴스 (feature 브랜치)**:
- Backend API: http://localhost:8100-8300 (동적 포트)
- Frontend: `/tests/{브랜치명}/` (nginx 서브패스)
- AutoDoc: http://localhost:8500-8700 (동적 포트)

### 폐쇄망 의존성 관리 시스템
**완전 오프라인 빌드 지원**:
- **Python**: .whl 파일을 `wheelhouse/` 폴더에 수집 (`download-all-dependencies.sh/ps1`)
- **Node.js**: npm 패키지를 `npm-cache/` 폴더에 수집 (**신규 추가**)
- **deploy_test_env.ps1**: npm 캐시 우선 사용 (`--prefer-offline`)

**의존성 수집 스크립트**:
```bash
# Linux/macOS
./download-all-dependencies.sh  # Python + npm 의존성 수집

# Windows  
.\Download-All-Dependencies.ps1  # Python + npm 의존성 수집
```

### 환경별 배포

#### 🚀 Windows 프로덕션 배포 (C:\deploys 구조)

**배포 아키텍처**:
```
C:\deploys\
├── apps\                    # 애플리케이션 실행 공간 (가상환경 & 코드)
│   ├── webservice\          # Python 3.12 환경
│   └── autodoc_service\     # Python 3.12 환경
├── data\                    # 영구 데이터 저장소 (업데이트 시 유지)
│   ├── webservice\          # 로그, 모델, 템플릿, 출력
│   └── autodoc_service\     # 로그, 템플릿, 문서
└── packages\                # 빌드 아티팩트 (.whl 파일)
```

**서비스 실행 명령어**:
```powershell
# Webservice (NSSM 서비스: webservice)
# PATH: C:\deploys\apps\webservice\.venv\Scripts\python.exe
# Arguments: -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# Environment: WEBSERVICE_DATA_PATH=C:\deploys\data\webservice
#              ANONYMIZED_TELEMETRY=False

# AutoDoc Service (NSSM 서비스: autodoc_service)
# PATH: C:\deploys\apps\autodoc_service\.venv312\Scripts\python.exe
# Arguments: -m uvicorn app.main:app --host 0.0.0.0 --port 8001
# Environment: AUTODOC_DATA_PATH=C:\deploys\data\autodoc_service

# Nginx Frontend (NSSM 서비스: nginx-frontend)
# PATH: C:\nginx\nginx.exe
# Startup Directory: C:\nginx
```

**개발 환경 테스트**:
```bash
# 로컬 개발 환경
cd webservice && source .venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m uvicorn app.main:app --reload --port 8000

cd autodoc_service && source .venv312/bin/activate
python -m uvicorn app.main:app --reload --port 8001
```

### Nginx로 프론트엔드 배포

- **운영 환경**: nginx가 포트 80에서 프론트엔드 서빙, `C:\nginx\html`에 React 빌드 결과물 배포
- **개발 환경**: Vite 개발 서버(포트 3000) 사용
- **설정 경로**: `C:\nginx\conf\nginx.conf`

현재 nginx 설정 (운영 중):

```nginx
worker_processes  1;

events {
    worker_connections  1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    keepalive_timeout  65;

    map $http_upgrade $connection_upgrade {
      default upgrade;
      ''      close;
    }

    server {
        listen       80;
        server_name  localhost;

        # React 프론트엔드 (SPA 라우팅 지원)
        root   C:/nginx/html;

        location / {
            try_files $uri $uri/ /index.html;
        }

        # 일반 API 프록시 (새로 추가)
        location /api/ {
          proxy_pass http://127.0.0.1:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;

          # WebSocket 지원
          proxy_http_version 1.1;
          proxy_set_header Upgrade $http_upgrade;
          proxy_set_header Connection $connection_upgrade;
          proxy_read_timeout 600s;  # 시나리오 생성용 장시간 대기
        }

        # Webservice API (포트 8000)
        location /api/webservice/ {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # AutoDoc Service API (포트 8001)
        location /api/autodoc/ {
            proxy_pass http://127.0.0.1:8001;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

참고: 방화벽/보안그룹에서 80 포트를 허용해야 외부에서 접속할 수 있습니다.

## 📊 품질 보증

### 테스트 커버리지 목표
- **Webservice**: ≥80% 단위 테스트, ≥70% 통합 테스트 (Python 3.12 환경, 통합 앱 구조)
- **CLI**: ≥85% 전체 커버리지 (Python 3.13 환경)
- **AutoDoc Service**: ≥85% 전체 커버리지 (Python 3.12 환경)
- **E2E**: 주요 사용자 워크플로우 100% 커버

### 성능 기준
- **Webservice API (포트 8000)**: 응답시간 <200ms, WebSocket 연결 <1초, RAG 초기화 <25초 (Python 3.12)
- **CLI**: Git/SVN 저장소 분석 <30초, URL 프로토콜 처리 <5초 (Python 3.13)
- **AutoDoc Service (포트 8001)**: HTML 파싱 <1초, Word 생성 <3초, Excel 생성 <2초 (Python 3.12)
- **빌드**: 전체 빌드 시간 <10분
- **VCS 호환성**: Git 및 SVN 저장소 모두에서 일관된 성능 보장

## 🤝 기여 가이드라인

### 개발 워크플로우
1. 해당 서브프로젝트 디렉토리에서 독립 환경 활성화
   - `cd webservice && source .venv/bin/activate` (Python 3.12, 통합 앱 구조)
   - `cd cli && source .venv/bin/activate` (Python 3.13)
   - `cd autodoc_service && source .venv312/bin/activate` (Python 3.12)
2. 독립적인 테스트 슈트 실행 및 통과 확인
3. 코드 품질 도구 실행 (black, isort, flake8)
4. 커밋 메시지는 서브프로젝트 접두어 사용: `[webservice]`, `[cli]`, 또는 `[autodoc_service]`

### 이슈 및 PR
- 서브프로젝트별로 라벨링: `webservice`, `cli`, `autodoc_service`, `monorepo`
- 독립적인 Python 환경 및 CI/CD 파이프라인 고려사항 명시
- 크로스플랫폼 호환성 검증 필수 (Windows, macOS, Linux)
- **VCS 호환성 테스트**: Git 및 SVN 저장소 모두에서 동작 확인
- MSA 원칙 준수: 서비스별 독립성 보장

## 🔍 문제 해결 가이드

### Windows 서버 운영 이슈

#### 1. NSSM 서비스 관리
```powershell
# 서비스 상태 확인
nssm status webservice
nssm status autodoc_service
nssm status nginx-frontend

# 서비스 재시작
nssm restart webservice
nssm restart autodoc_service
net stop nginx && net start nginx

# 서비스 로그 확인
Get-Content "C:\deploys\apps\webservice\nssm-stderr.log" -Tail 20
Get-Content "C:\nginx\logs\error.log" -Tail 20
```

#### 2. Python 환경 문제
```powershell
# PYTHONHOME 충돌 해결 (폐쇄망 서버 특화)
# Jenkins에서 Python 명령어 실행 시 환경 변수 격리 필수
set "PYTHONHOME="
set "PYTHONPATH="
C:\deploys\apps\webservice\.venv\Scripts\python.exe --version
```

#### 3. ChromaDB 잠금 오류
```powershell
# 벡터 DB 초기화 (Windows 경로)
Remove-Item "C:\deploys\data\webservice\db\" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "C:\deploys\data\webservice\vector_db_data\" -Recurse -Force -ErrorAction SilentlyContinue
```

#### 4. 포트 충돌 문제
```powershell
# 포트 사용 확인
netstat -ano | findstr ":8000"
netstat -ano | findstr ":8001"
netstat -ano | findstr ":80"

# 프로세스 강제 종료 (필요시)
taskkill /PID [PID번호] /F
```

### 개발 환경 문제 해결

#### 1. 가상환경 활성화 오류
```bash
# Linux/개발 환경
cd webservice && source .venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH

# ChromaDB 제약조건 파일 필수 사용
pip install -r requirements.txt -c pip.constraints.txt
```

#### 2. E2E 테스트 타임아웃
```bash
# WebSocket 연결 대기 시간 조정 (~60초)
cd webservice/frontend
npm run test:e2e -- --timeout 120000
```

#### 3. Jenkins PowerShell 실행 오류
```groovy
// Jenkinsfile에서 안전한 PowerShell 실행
bat '''
    @echo off
    chcp 65001 >NUL
    set "DEPLOY_PATH=%DEPLOY_PATH%"
    powershell -Command "Write-Host 'Deploying to:' $env:DEPLOY_PATH"
'''
```

### 서비스 상태 확인

#### API 헬스체크
```powershell
# Webservice 상태 확인
Invoke-WebRequest "http://localhost:8000/api/webservice/health" -UseBasicParsing

# AutoDoc Service 상태 확인
Invoke-WebRequest "http://localhost:8001/api/autodoc/health" -UseBasicParsing

# Frontend 접근 확인
Invoke-WebRequest "http://localhost:80" -UseBasicParsing
```

#### 로그 모니터링
```powershell
# 실시간 로그 확인
Get-Content "C:\deploys\data\webservice\logs\webservice.log" -Wait -Tail 10
Get-Content "C:\deploys\data\autodoc_service\logs\autodoc.log" -Wait -Tail 10
Get-Content "C:\nginx\logs\access.log" -Wait -Tail 10
```

### 폐쇄망 환경 특화 문제

#### 1. 의존성 설치 실패
```powershell
# 오프라인 패키지 설치 확인
pip install --no-index --find-links wheelhouse\ -r requirements.txt
npm install --offline
```

#### 2. 외부 연결 시도 감지
```powershell
# 네트워크 연결 모니터링
netstat -an | findstr "ESTABLISHED"
# 모든 연결이 localhost(127.0.0.1) 또는 내부 IP만 있어야 함
```

## 📝 라이선스

MIT License - 각 서브프로젝트의 라이선스 파일 참조

## 🔗 관련 링크

- **Webservice Documentation**: [webservice/README.md](webservice/README.md)
- **CLI Documentation**: [cli/README.md](cli/README.md)
- **통합 개발 가이드**: [CLAUDE.md](CLAUDE.md)
- **Pull Request 히스토리**: [PR_HISTORY.md](PR_HISTORY.md)

---

각 서브프로젝트는 독립적으로 개발되고 배포되며, **Git 및 SVN 저장소 모두를 지원**하는 통합된 이슈 트래킹과 개발 환경을 제공합니다.
