# TestscenarioMaker Claude Code Instructions

## Entry Point & Core Directives

@DEV_ENVIRONMENT.md | @MONOREPO_STRUCTURE.md | @BUILD_DEPLOY.md | @PROJECT_RULES.md

## 🎯 프로젝트 핵심 원칙

- **Development First**: 각 모노레포별 가상환경 → Context7 패턴 조회 → 구현 → 검증
- **Evidence-Based**: 모든 최적화는 측정 기반, 하드코딩 회피 금지
- **Cross-Platform**: Windows Server 프로덕션 환경 우선 고려
- **Air-gapped Environment**: 폐쇄망 환경에서 인터넷 연결 없이 완전 독립 운영 가능

---

# TestscenarioMaker Project Architecture

## Monorepo Structure & Services

**Architecture**: Git Subtree 기반 통합 플랫폼

```yaml
services:
  webservice:
    stack: "React 18 + TypeScript + Material-UI + Vite | FastAPI + Python 3.12 + ChromaDB"
    venv: ".venv (Python 3.12)"
    ports: "3000 (dev), 8000 (api)"

  cli:
    stack: "Python 3.13 + Click + Rich + PyInstaller"
    venv: ".venv (Python 3.13)"
    output: "크로스 플랫폼 실행파일"

  autodoc_service:
    stack: "FastAPI + Python 3.12"
    venv: ".venv312 (Python 3.12)"
    ports: "8001"
    function: "HTML → Word/Excel 문서 자동화"

deployment:
  production: "Windows Server + NSSM + nginx + Jenkins"
  ai_backend: "Ollama (qwen3:8b 모델)"
  environment: "Air-gapped (폐쇄망) - 인터넷 연결 없음"
```

---

# Air-gapped Environment Requirements

## 🚨 폐쇄망 환경 운영 지침

**CRITICAL**: 본 시스템은 폐쇄망(Air-gapped) 환경에서 운영되므로 인터넷 연결이 없습니다.
모든 의존성, 아티팩트, 코드는 폐쇄망 환경에서 완전히 독립적으로 작동해야 합니다.

### 폐쇄망 환경 제약사항

```yaml
network_restrictions:
  internet_access: "금지 - 인터넷 연결 불가"
  external_api: "금지 - 외부 API 호출 불가"
  package_registry: "금지 - npm, PyPI 등 외부 레지스트리 접근 불가"
  ai_services: "금지 - 외부 AI API (OpenAI, Anthropic 등) 사용 불가"

mandatory_requirements:
  offline_operation: "모든 기능이 인터넷 없이 작동해야 함"
  local_dependencies: "모든 의존성은 사전에 다운로드하여 로컬에 저장"
  bundled_assets: "모든 리소스는 빌드 시 번들에 포함"
  local_ai: "AI 기능은 로컬 Ollama 서버 사용 필수"
```

### 의존성 관리 전략

```bash
# ✅ Python 패키지 사전 다운로드 (개발 환경에서)
pip download -r requirements.txt -d offline_packages/
pip install --no-index --find-links offline_packages/ -r requirements.txt

# ✅ Node.js 패키지 사전 다운로드
npm pack --pack-destination offline_packages/
npm ci --offline

# ✅ AI 모델 로컬 설치
ollama pull qwen3:8b  # 개발 환경에서 사전 다운로드
```

### 코드 구현 제약사항

```python
# 🚫 금지: 외부 API 호출
import requests
response = requests.get("https://api.external-service.com")

# ✅ 허용: 로컬 서비스만 사용
response = requests.post("http://localhost:11434/api/generate")

# 🚫 금지: 외부 CDN 참조
<script src="https://cdn.jsdelivr.net/npm/axios"></script>

# ✅ 허용: 번들에 포함된 라이브러리
import axios from './node_modules/axios'
```

### 아티팩트 관리

```yaml
build_artifacts:
  frontend: "모든 asset을 dist/에 번들링"
  python_wheel: "의존성 포함된 wheel 파일 생성"
  cli_binary: "독립 실행 가능한 바이너리"
  templates: "모든 템플릿 파일을 로컬에 저장"

deployment_package:
  structure: |
    deployment_package/
    ├── offline_packages/          # Python/Node 패키지
    ├── binaries/                  # 컴파일된 실행파일
    ├── templates/                 # Word/Excel 템플릿
    ├── ai_models/                 # Ollama 모델 파일
    ├── config/                    # 환경 설정 파일
    └── scripts/                   # 설치/배포 스크립트
```

---

# Development Environment Setup

## Environment Prerequisites & Activation

- **Critical Rule**: 각 서비스 작업시 반드시 해당 가상환경 먼저 활성화
- **Air-gapped Rule**: 모든 의존성은 사전에 다운로드하여 오프라인으로 설치

### Service-Specific Virtual Environments

```bash
# 🔹 Webservice (Python 3.12 + AI/ML Stack) - 폐쇄망 설치
cd webservice
python3.12 -m venv .venv
source .venv/bin/activate  # Linux/macOS | .venv\Scripts\activate (Windows)
export PYTHONPATH=$(pwd):$PYTHONPATH
# 폐쇄망 환경: 오프라인 패키지 설치
pip install --no-index --find-links ../offline_packages/ -r requirements.txt -c pip.constraints.txt

# 🔹 CLI (Python 3.13 + Cross-Platform) - 폐쇄망 설치
cd cli
python3.13 -m venv .venv
source .venv/bin/activate
# 폐쇄망 환경: 오프라인 패키지 설치
pip install --no-index --find-links ../offline_packages/ -e .

# 🔹 AutoDoc Service (Python 3.12 + Document Processing) - 폐쇄망 설치
cd autodoc_service
python3.12 -m venv .venv312
source .venv312/bin/activate
# 폐쇄망 환경: 오프라인 패키지 설치
pip install --no-index --find-links ../offline_packages/ -r requirements.txt

# 🔹 Frontend (Node.js + React 18) - 폐쇄망 설치
cd webservice/frontend
# 폐쇄망 환경: 오프라인 설치
npm ci --offline
```

### Environment Variables Matrix

```yaml
webservice_env:
  required: "PYTHONPATH=$(pwd):$PYTHONPATH"
  optional_production:
    - "WEBSERVICE_DATA_PATH=C:/deploys/data/webservice"
    - "AUTODOC_DATA_PATH=C:/deploys/data/autodoc_service"
  development: "자동으로 data/ 서브디렉토리 사용"
```

## Service Execution Patterns

### Service Startup Commands

```bash
# 🚀 Webservice (Full Stack)
# Terminal 1: Backend API Server
cd webservice && source .venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend Dev Server
cd webservice/frontend && npm run dev
# → Access: http://localhost:3000 (Frontend) → http://localhost:8000 (Backend API)

# 🚀 AutoDoc Service
cd autodoc_service
source .venv312/bin/activate
python -m uvicorn app.main:app --reload --port 8001
# → Access: http://localhost:8001

# 🚀 CLI Operations
cd cli && source .venv/bin/activate
ts-cli --help
ts-cli analyze /path/to/repository
ts-cli info /path/to/repository
ts-cli config-show
```

---

# Testing & Quality Assurance

## Test Execution Matrix

- **Critical**: E2E 테스트 필수 (webservice), WebSocket 타임아웃 ~60초 고려

### Service-by-Service Testing

```bash
# 🧪 Webservice Testing Suite
cd webservice && source .venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH

# Backend Test Layers
pytest tests/unit/                    # Unit Tests
pytest tests/api/                     # API Integration
pytest tests/integration/             # System Integration

# Frontend Test Layers (Critical Path)
cd frontend
npm run test                          # Unit Tests
npm run test:e2e                      # E2E Tests (MANDATORY!)
npm run test:all                      # Complete Suite

# 🧪 CLI Testing
cd cli && source .venv/bin/activate
pytest --cov=ts_cli --cov-report=html  # Coverage Analysis
pytest tests/unit/ -v                  # Unit Tests
pytest tests/integration/ -v           # Integration Tests
pytest -m "not e2e"                    # Non-E2E Only

# 🧪 AutoDoc Service Testing
cd autodoc_service && source .venv312/bin/activate
pytest app/tests/ -v
pytest app/tests/test_html_parser.py -v
```

### Quality Standards & Coverage

```yaml
quality_targets:
  test_coverage: "≥80% (모든 서비스)"
  performance_limits:
    webservice_api: "<200ms 응답시간"
    cli_analysis: "<30초 저장소 분석"
    autodoc_service: "<1초 HTML 파싱, <3초 문서 생성"
  e2e_requirements: "WebSocket 대기시간 ~60초"
```

---

# 빌드 및 배포

## 프로덕션 빌드 전체 프로세스

### 1. 전체 시스템 빌드 (순차 실행)

```bash
# 1단계: CLI 빌드 (실행파일 생성)
cd cli
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows
python scripts/build.py
# 결과: cli/dist/ts-cli.exe (Windows) 또는 cli/dist/ts-cli (Unix)

# 2단계: Webservice Frontend 빌드
cd ../webservice/frontend
npm install
npm run build
npm run lint
npm run type-check
# 결과: webservice/frontend/dist/ (정적 파일)

# 3단계: Webservice Backend 빌드 확인
cd ../
source .venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH
python -c "import app.main; print('Backend import 성공')"

# 4단계: AutoDoc Service 빌드 확인
cd ../autodoc_service
source .venv312/bin/activate
python -c "import app.main; print('AutoDoc import 성공')"
```

### 2. Windows 프로덕션 배포용 빌드

```powershell
# PowerShell 스크립트 시작 부분 (UTF-8 인코딩 설정)
chcp 65001 >NUL
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

# 1. CLI 빌드 (Windows 실행파일)
Set-Location cli
.\.venv\Scripts\Activate.ps1
python scripts\build.py
if ($LASTEXITCODE -ne 0) { throw "CLI 빌드 실패" }

# 2. Frontend 빌드
Set-Location ..\webservice\frontend
npm install
npm run build
npm run lint
npm run type-check
if ($LASTEXITCODE -ne 0) { throw "Frontend 빌드 실패" }

# 3. 빌드 결과물 복사 (배포용)
# Frontend 정적 파일을 nginx 경로로 복사
Copy-Item "dist\*" "C:\nginx\html\" -Recurse -Force

# CLI 실행파일을 배포 경로로 복사
Copy-Item "..\cli\dist\ts-cli.exe" "C:\deploys\bin\" -Force
```

## CLI 빌드 (크로스 플랫폼)

### 개발 환경 빌드

```bash
cd cli
source .venv/bin/activate

# 기본 빌드 (현재 플랫폼용)
python scripts/build.py

# 상세 빌드 옵션
python scripts/build.py --clean    # 이전 빌드 삭제 후 빌드
python scripts/build.py --debug    # 디버그 정보 포함
python scripts/build.py --onefile  # 단일 실행파일 생성

# macOS Helper App (샌드박스 우회용)
python scripts/build_helper_app.py

# 빌드 결과 확인
ls -la dist/
# Windows: ts-cli.exe
# macOS: ts-cli, TestscenarioMaker Helper.app
# Linux: ts-cli
```

### Jenkins 자동화 빌드 (Windows)

```groovy
// Jenkinsfile에서 CLI 빌드
stage('CLI Build') {
    steps {
        bat """
        chcp 65001 >NUL
        cd cli
        .venv\\Scripts\\activate.bat
        python scripts\\build.py --clean
        if not exist "dist\\ts-cli.exe" (
            echo "CLI 빌드 실패: 실행파일이 생성되지 않음"
            exit /b 1
        )
        """
    }
}
```

## Webservice 빌드

### Frontend 빌드 (React + Vite)

```bash
cd webservice/frontend

# 개발 환경 빌드
npm install
npm run build

# 코드 품질 검사 (필수)
npm run lint          # ESLint 검사
npm run type-check    # TypeScript 타입 검사
npm run test          # 단위 테스트
npm run test:e2e      # E2E 테스트 (중요!)

# 빌드 결과 확인
ls -la dist/
# index.html, assets/, favicon.ico 등
```

### Frontend Jenkins 빌드 (Windows)

```groovy
// Jenkinsfile에서 Frontend 빌드
stage('Frontend Build') {
    steps {
        bat """
        chcp 65001 >NUL
        cd webservice\\frontend
        npm ci
        npm run build
        npm run lint
        npm run type-check
        
        REM 빌드 결과물 nginx로 복사
        xcopy /E /I /Y "dist\\*" "C:\\nginx\\html\\"
        
        REM 빌드 성공 확인
        if not exist "dist\\index.html" (
            echo "Frontend 빌드 실패: index.html이 생성되지 않음"
            exit /b 1
        )
        """
    }
}
```

### Backend 빌드 확인

```bash
cd webservice
source .venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH

# 의존성 설치 확인
pip install -r requirements.txt -c pip.constraints.txt

# 애플리케이션 임포트 테스트
python -c "
import app.main
from app.core import llm_manager, excel_writer
print('✅ Backend 모듈 임포트 성공')
"

# 데이터베이스 마이그레이션 (필요시)
# python -m alembic upgrade head
```

## AutoDoc Service 빌드

```bash
cd autodoc_service
source .venv312/bin/activate

# 의존성 설치 확인
pip install -r requirements.txt

# 애플리케이션 임포트 테스트
python -c "
import app.main
from app.services import html_parser, excel_test_builder
print('✅ AutoDoc 모듈 임포트 성공')
"

# 템플릿 파일 존재 확인
ls -la data/templates/
# cm_word_template.docx, test_excel_template.xlsx 등
```

## 배포 전 빌드 검증

### 통합 테스트 (모든 서비스)

```bash
# 1. CLI 실행 테스트
cd cli
dist/ts-cli --version
dist/ts-cli --help

# 2. Backend 헬스체크 (백그라운드 실행)
cd ../webservice
source .venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m uvicorn app.main:app --port 8000 &
sleep 5
curl http://localhost:8000/api/webservice/health
pkill -f uvicorn

# 3. AutoDoc 헬스체크
cd ../autodoc_service
source .venv312/bin/activate
python run_autodoc_service.py &
sleep 5
curl http://localhost:8001/api/autodoc/health
pkill -f run_autodoc_service

# 4. Frontend 빌드 결과 확인
cd ../webservice/frontend
python -m http.server 3000 --directory dist &
sleep 2
curl http://localhost:3000
pkill -f "http.server"
```

### Windows 서버 배포 스크립트

```powershell
# deploy_windows.ps1
chcp 65001 >NUL
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 서비스 중지
Write-Host "서비스 중지 중..."
nssm stop WebserviceAPI
nssm stop AutoDocService
net stop nginx

# 백업 생성
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item "C:\nginx\html" "C:\backups\frontend_$timestamp" -Recurse -Force

# 새 빌드 배포
Write-Host "새 빌드 배포 중..."
Copy-Item "webservice\frontend\dist\*" "C:\nginx\html\" -Recurse -Force
Copy-Item "cli\dist\ts-cli.exe" "C:\deploys\bin\" -Force

# Python 가상환경 업데이트
& "C:\deploys\webservice\.venv\Scripts\Activate.ps1"
pip install -r "webservice\requirements.txt" -c "webservice\pip.constraints.txt"

& "C:\deploys\autodoc_service\.venv312\Scripts\Activate.ps1"
pip install -r "autodoc_service\requirements.txt"

# 서비스 재시작
Write-Host "서비스 재시작 중..."
net start nginx
nssm start WebserviceAPI
nssm start AutoDocService

# 헬스체크
Start-Sleep 10
$health1 = Invoke-WebRequest "http://localhost:8000/api/webservice/health" -UseBasicParsing
$health2 = Invoke-WebRequest "http://localhost:8001/api/autodoc/health" -UseBasicParsing
$health3 = Invoke-WebRequest "http://localhost:80" -UseBasicParsing

if ($health1.StatusCode -eq 200 -and $health2.StatusCode -eq 200 -and $health3.StatusCode -eq 200) {
    Write-Host "✅ 배포 성공! 모든 서비스가 정상 작동 중"
} else {
    Write-Host "❌ 배포 실패! 헬스체크 확인 필요"
    exit 1
}
```

## 빌드 최적화 팁

### 빌드 속도 향상

```bash
# 1. npm 캐시 활용
cd webservice/frontend
npm ci  # package-lock.json 기반 빠른 설치

# 2. Python 패키지 캐시
pip install --cache-dir .pip-cache -r requirements.txt

# 3. Docker 레이어 캐싱 (선택사항)
# Docker build context 최적화
```

### 빌드 크기 최적화

```bash
# Frontend 번들 크기 분석
cd webservice/frontend
npm run build
npx vite-bundle-analyzer dist/

# Python 실행파일 크기 최적화
cd cli
python scripts/build.py --optimize-size
```

## 주요 빌드 에러 해결

### 1. CLI 빌드 실패

```bash
# PyInstaller 캐시 삭제
cd cli
rm -rf build/ dist/ __pycache__/
python scripts/build.py --clean

# 의존성 문제
pip install --upgrade pyinstaller
pip install -r requirements.txt
```

### 2. Frontend 빌드 실패

```bash
# Node 모듈 재설치
cd webservice/frontend
rm -rf node_modules/ package-lock.json
npm install
npm run build

# TypeScript 오류
npm run type-check
# 오류 수정 후 재빌드
```

### 3. Windows PowerShell 인코딩 오류

```powershell
# 스크립트 최상단에 반드시 추가
chcp 65001 >NUL
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'
```

---

# API 엔드포인트

## Webservice API (프리픽스: `/api/webservice`)

```
POST   /scenario                           # V1 시나리오 생성 (레거시)
POST   /v2/scenario                        # V2 시나리오 생성 (CLI 통합)
WS     /v2/ws/progress/{client_id}         # V2 WebSocket 진행상황
POST   /rag/add-documents                  # RAG 문서 추가
GET    /rag/status                         # RAG 시스템 상태
POST   /feedback                           # 사용자 피드백
GET    /files                              # 파일 목록
GET    /health                             # 헬스체크
```

## AutoDoc Service API (프리픽스: `/api/autodoc`)

```
POST   /parse-html                         # HTML 파일 파싱
POST   /parse-html-only                    # HTML 파일 파싱(JSON으로 리턴)
POST   /create-cm-word-enhanced            # 향상된 Word 문서 생성
POST   /create-test-excel                  # Excel 테스트 시나리오
GET    /download/{filename}                # 파일 다운로드
GET    /list-templates                     # 템플릿 목록
GET    /health                             # 헬스체크
```

---

# 프로젝트 구조

```
cm-docs/
├── webservice/                    # 웹서비스 (React + FastAPI)
│   ├── app/                      # FastAPI 애플리케이션
│   │   ├── main.py              # 애플리케이션 진입점
│   │   ├── core/                # 핵심 모듈 (분석, LLM, Excel)
│   │   ├── api/routers/         # API 엔드포인트
│   │   └── services/            # 비즈니스 로직
│   ├── frontend/                # React 애플리케이션
│   │   ├── src/components/      # UI 컴포넌트
│   │   ├── src/services/        # API 클라이언트
│   │   └── src/utils/           # 유틸리티
│   ├── tests/                   # 테스트 파일
│   ├── data/                    # 개발용 데이터 (환경변수 미설정시)
│   └── .venv/                   # Python 3.9 가상환경
├── cli/                          # CLI 도구
│   ├── src/ts_cli/              # CLI 소스코드
│   │   ├── main.py              # CLI 진입점
│   │   ├── vcs/                 # VCS 분석기 (Git, SVN)
│   │   └── utils/               # 유틸리티
│   ├── tests/                   # 테스트 파일
│   ├── scripts/                 # 빌드 스크립트
│   └── .venv/                   # Python 3.13 가상환경
├── autodoc_service/              # 문서 자동화 서비스
│   ├── app/                     # FastAPI 애플리케이션
│   │   ├── main.py              # 애플리케이션 진입점
│   │   ├── services/            # 문서 생성 서비스
│   │   └── parsers/             # HTML 파서
│   ├── data/                    # 개발용 데이터
│   │   ├── templates/           # Word/Excel 템플릿
│   │   └── documents/           # 생성된 문서
│   └── .venv312/                # Python 3.12 가상환경
├── scripts/                     # 배포 스크립트
├── infra/                       # 인프라 설정
└── Jenkinsfile                  # 통합 CI/CD 파이프라인
```

---

# CI/CD 파이프라인

## 파이프라인 구조

- **통합 파이프라인**: `Jenkinsfile` (변경 감지 기반 스마트 배포)
- **서비스별 파이프라인**:
  - `webservice/Jenkinsfile.backend` (API 서비스)
  - `webservice/Jenkinsfile.frontend` (React 앱)
  - `autodoc_service/Jenkinsfile` (문서 서비스)
  - `cli/Jenkinsfile` (CLI 도구)

## 변경 감지 시스템

```bash
# 파이프라인이 자동으로 감지하는 변경사항
webservice/          → 웹서비스 빌드/배포
autodoc_service/     → 문서 서비스 빌드/배포
cli/                 → CLI 도구 빌드
infra/              → 전체 재배포
scripts/            → 전체 재배포
*.md                → 빌드 스킵 (문서 변경만)
```

## 브랜치별 배포 전략

- **main/develop**: 프로덕션 배포
- **feature/hotfix**: 테스트 인스턴스 배포 (`/tests/{브랜치명}/`)

## 배포 환경

```bash
# 프로덕션 서버 (Windows Server + NSSM)
Backend:   http://localhost:8000    (NSSM 서비스)
Frontend:  http://localhost:80      (nginx)
AutoDoc:   http://localhost:8001    (NSSM 서비스)

# 테스트 인스턴스 (동적 포트)
Backend:   http://localhost:8100-8300  (브랜치별 포트)
Frontend:  /tests/{브랜치명}/          (nginx 서브패스)
AutoDoc:   http://localhost:8500-8700  (브랜치별 포트)
```

---

# Jenkins PowerShell 실행 가이드

## 인코딩 문제 해결

```powershell
# 모든 PowerShell 스크립트 시작 부분에 추가
chcp 65001 >NUL
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'
```

## 백슬래시 문제 해결

```groovy
// Jenkinsfile에서 PowerShell 실행 시
bat """
chcp 65001 >NUL
powershell -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass ^
    -File "scripts\\deploy_script.ps1" ^
    -Param1 "%VALUE1%" ^
    -Param2 "%VALUE2%"
"""
```

## 멀티라인 명령어

```groovy
// 잘못된 예 (Windows에서 오류)
bat '''
powershell -Command "
    Write-Host 'Line 1'
    Write-Host 'Line 2'
"
'''

// 올바른 예 (Windows 호환)
bat """
chcp 65001 >NUL
powershell -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "& { ^
    Write-Host 'Line 1'; ^
    Write-Host 'Line 2' ^
}"
"""
```

## 환경변수 처리

```groovy
// Jenkins 환경변수를 PowerShell로 안전하게 전달
bat """
set "PARAM1=%VALUE1%"
set "PARAM2=%VALUE2%"
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "& { ^
    \$param1 = \$env:PARAM1; ^
    \$param2 = \$env:PARAM2; ^
    Write-Host \"Param1: \$param1\"; ^
    Write-Host \"Param2: \$param2\" ^
}"
"""
```

---

# 문제 해결 가이드

## 자주 발생하는 오류

### 1. ChromaDB 잠금 오류
```bash
# 해결: 벡터 DB 초기화
rm -rf webservice/data/db/
rm -rf webservice/vector_db_data/
```

### 2. Module Import 오류 (webservice)
```bash
# 해결: PYTHONPATH 설정 확인
cd webservice
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### 3. E2E 테스트 타임아웃
```bash
# 해결: WebSocket 대기 시간 조정 (~60초)
cd webservice/frontend
npm run test:e2e -- --timeout 120000
```

### 4. PowerShell 실행 정책 오류
```powershell
# 해결: 실행 정책 설정
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 5. UTF-8 인코딩 오류
```powershell
# 스크립트 시작 부분에 추가
chcp 65001 >NUL
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

## 서비스 디버깅

### Webservice 디버깅
```bash
# 헬스체크
curl http://localhost:8000/api/webservice/health

# 로그 확인
tail -f webservice/data/logs/webservice.log

# RAG 시스템 상태
curl http://localhost:8000/api/webservice/rag/status
```

### AutoDoc Service 디버깅
```bash
# 헬스체크
curl http://localhost:8001/api/autodoc/health

# 템플릿 목록 확인
curl http://localhost:8001/api/autodoc/list-templates
```

---

# 개발 가이드라인

## 상호작용 중심 설계

- 포괄적이고 인터랙티브한 컴포넌트 생성
- 마이크로 인터랙션 및 애니메이션 고려
- 사용자 경험 중심의 디자인 패턴

## 견고한 범용 솔루션

- 하드코딩 방지, 재사용 가능한 컴포넌트
- 특정 테스트 케이스가 아닌 일반적 해결책
- Material-UI 디자인 시스템 일관성 유지

## 코드 품질 및 구조화

### XML 태그 활용

```xml
<analysis>
현재 상황 분석
</analysis>

<solution>
제안하는 해결책
</solution>

<implementation>
구체적 구현 방법
</implementation>

<validation>
검증 및 테스트 방법
</validation>
```

### 출력 스타일 일치

- 요청한 스타일에 맞는 응답 형식
- 일관된 코드 스타일 유지
- 명확한 예시와 설명 제공

---

# TestscenarioMaker Project-Specific Rules

## Core Development Principles

- **Evidence-Based Development**: Context7 패턴 조회 → 구현 → 검증 (하드코딩 회피 절대 금지)
- **Environment Isolation**: 각 모노레포별 독립 가상환경 활성화 필수
- **Cross-Platform First**: Windows Server 프로덕션 환경 우선 고려
- **Air-gapped First**: 폐쇄망 환경에서 완전 독립 운영 필수, 인터넷 의존성 절대 금지

## Architecture-Specific Rules

```yaml
monorepo_management:
  structure: "Git Subtree 기반 독립적 서비스 관리"
  environments: "서비스별 독립 가상환경 (.venv, .venv312)"
  dependencies: "서비스 간 의존성 최소화"

platform_compatibility:
  primary_target: "Windows Server + NSSM + nginx + Jenkins"
  scripting: "PowerShell UTF-8 인코딩 전처리 필수"
  path_handling: "pathlib.Path 사용 (크로스 플랫폼)"
  encoding: "Unicode/Emoji 로깅 금지 (Windows 호환성)"
  network: "폐쇄망 환경 - 인터넷 연결 불가, 로컬 서비스만 사용"
```

## Performance & Quality Standards

```yaml
performance_budgets:
  webservice_api: "<200ms 응답시간"
  cli_analysis: "<30초 저장소 분석"
  autodoc_html_parsing: "<1초"
  autodoc_document_generation: "<3초"
  test_coverage_minimum: "≥80% (모든 서비스)"

quality_gates:
  testing: "E2E 테스트 필수 (webservice)"
  websocket_timeout: "~60초 대기시간 고려"
  jenkins_compatibility: "PowerShell 실행 환경 대응"
  no_shortcuts: "하드코딩/테스트 데이터 조작 절대 금지"
```

## Development Workflow Rules

```yaml
pre_development:
  pattern_research: "Context7 MCP 패턴 조회 필수"
  environment_check: "가상환경 활성화 상태 확인"
  dependency_validation: "ChromaDB constraints 파일 사용"

coding_standards:
  python_print: "영어 only, 가능하면 logger 사용"
  commit_format: "서비스 접두사 ([webservice], [cli], [autodoc_service])"
  api_response: "표준 JSON 형식 (success, data, message, timestamp)"
  network_calls: "로컬 서비스만 허용 (localhost, 127.0.0.1), 외부 URL 절대 금지"
  ai_integration: "Ollama 로컬 서버만 사용, 외부 AI API 절대 금지"
```

---

# Code Quality & Style Guidelines

## Frontend Code Standards (TypeScript/React)

### Mandatory Quality Pipeline
```bash
# Post-Development Validation (Required)
cd webservice/frontend
npm run lint          # ESLint 검증
npm run type-check     # TypeScript 타입 검증
npm run build          # 빌드 검증
```

### Type Safety Requirements
```typescript
// 🚫 Prohibited: any 타입 사용 금지
const data: any = response.data;

// ✅ Required: 명시적 타입 정의
interface ApiResponse {
  success: boolean;
  data: ParsedData;
}
const data: ApiResponse = response.data;

// ✅ Error Handling Pattern
try {
  const result = await api.call();
} catch (error) {
  const apiError = error as ApiError;
  logger.error('API call failed:', apiError);
}
```

## Backend Code Standards (Python)

### Code Quality Pipeline
```bash
# 프로젝트 루트에서 실행 (Required)
black webservice/ cli/ autodoc_service/ --line-length 88
isort webservice/ cli/ autodoc_service/
flake8 webservice/ cli/ autodoc_service/
mypy webservice/app/ cli/src/
```

### Mandatory Rules
```yaml
path_handling: "pathlib.Path 사용 (크로스 플랫폼 호환성)"
logging_standards: "Unicode/Emoji 금지, 영어 사용 (Windows 호환성)"
dependency_management: "ChromaDB constraints 파일 필수, 오프라인 패키지 설치"
virtual_environment: "서비스별 가상환경 사전 활성화 필수"
commit_format: "[webservice], [cli], [autodoc_service] 접두사 사용"
network_restrictions: "폐쇄망 환경 - 인터넷 호출 코드 작성 절대 금지"
ai_services: "로컬 Ollama만 사용, 외부 AI API 사용 절대 금지"
```

## API Response Standards

```python
# ✅ Standard Response Format
{
    "success": true,
    "data": {...},
    "message": "Success message",
    "timestamp": "2025-01-17T10:30:00Z"
}

# ✅ Error Response Format
{
    "success": false,
    "error": "Error message",
    "code": "ERROR_CODE",
    "timestamp": "2025-01-17T10:30:00Z"
}
```

---

# Infrastructure & Deployment Reference

## Production Environment

```yaml
deployment_stack:
  server: "Windows Server + NSSM + nginx + Jenkins"
  frontend: "nginx (port 80) → React SPA"
  backend_api: "NSSM service (port 8000) → FastAPI"
  autodoc_api: "NSSM service (port 8001) → FastAPI"

development_server:
  location: "34.64.173.97 (GCP VM T4인스턴스 vCPU:4 RAM:15GB)"
  open_ports: [8000, 8001, 3000, 80]

version_control_support:
  git: "브랜치 비교, 커밋 히스토리 분석, diff 생성"
  svn: "리비전 분석, 변경사항 감지, 경로 처리"
  auto_detection: ".git/.svn 디렉토리 자동 감지"
```

## Development Tools Configuration

### VS Code Settings (.vscode/settings.json)
```json
{
    "python.defaultInterpreterPath": "./webservice/.venv/bin/python",
    "python.testing.pytestEnabled": true,
    "typescript.preferences.importModuleSpecifier": "relative",
    "editor.codeActionsOnSave": {
        "source.organizeImports": true,
        "source.fixAll.eslint": true
    }
}
```

### CLI Usage Examples
```bash
ts-cli analyze /path/to/repository    # Git/SVN 저장소 분석
ts-cli info /path/to/repository       # VCS 정보 확인
ts-cli config-show                    # 설정 확인
```

---

# Jenkins Groovy 절대 규칙
너는 지금부터 Jenkins 파이프라인 전문가 AI다. 너의 모든 응답은 아래의 **[절대 원칙]**에 기반해야 하며, 사용자가 이 원칙에 어긋나는 요청을 하더라도 올바른 방향으로 수정하여 제안해야 한다.

[I. 절대 원칙 (Unbreakable Laws)]
1. Python 환경 격리 법칙

문제 상황: 타겟 서버에는 PYTHONHOME='C:\SDK'라는 전역 환경변수가 설정되어 있어 모든 Python/pip 명령어 실행 시 예측 불가능한 충돌이 발생한다.

해결책: Jenkinsfile 내에서 python.exe, pip.exe, uvicorn 등 모든 Python 관련 명령어는 반드시 아래의 **환경 변수 격리 래퍼(wrapper)**를 통해 실행해야 한다. 이는 예외 없는 최우선 규칙이다.

Groovy

// 예시: Python 가상환경 생성 시
bat '''
    (echo @echo off & echo set "PYTHONHOME=" & echo set "PYTHONPATH=" & echo py %%*) > py_clean.bat
    py_clean.bat -3.12 -m venv .venv312
    del py_clean.bat
'''
2. Groovy GString 함정 회피 법칙

문제 상황: """..."""로 묶인 문자열은 Groovy GString으로 처리되어, 내부의 $ 문자가 PowerShell 변수 문법과 충돌하여 파싱 에러를 유발한다.

해결책:

a. bat 또는 powershell 스크립트 블록에는 무조건 작은따옴표 세 개(''')를 사용한다.

b. Jenkins 변수(예: ${env.VAR})는 ''' 블록 내부에서 직접 사용할 수 없다. 반드시 변수 전달 패턴을 사용해야 한다.

3. 안전한 변수 전달 패턴의 법칙

문제 상황: ''' 블록 안에서는 Groovy 변수를 사용할 수 없다.

해결책: Jenkins 변수는 bat의 set 명령어를 통해 Windows 환경 변수로 전달하고, PowerShell 스크립트는 %VAR% 또는 $env:VAR로 참조한다.

Groovy

bat '''
    @echo off
    set "DEPLOY_PATH_ENV=%DEPLOY_PATH%"
    powershell -Command "Write-Host 'Deploying to %DEPLOY_PATH_ENV%'"
'''
4. main 브랜치 배포의 법칙

문제 상황: main 브랜치의 서비스는 영구적으로 설치되어 있으며, 테스트 브랜치와 배포 방식이 다르다.

해결책: main 브랜치 배포 로직은 nssm stop -> 파일 업데이트 -> nssm start 순서로만 구성한다. nssm install이나 remove는 절대 사용하지 않는다.

5. 기존 로직 불변의 법칙

문제 상황: feature 브랜치 배포에 사용되는 .ps1 스크립트들은 폐쇄망에서 이미 성공적으로 검증된 자산이다.

해결책: 이 스크립트들의 내용이나 호출 방식을 절대 수정하거나 변경을 제안해서는 안 된다. 오직 main 브랜치 배포 로직을 추가하는 것이 목표다.

[II. 작업별 실행 프로토콜 (Task-Specific Protocols)]
사용자의 요청에 따라 아래 프로토콜 중 하나를 선택하여 행동한다.

A. 코드 작성/생성 요청 시:

[절대 원칙]을 모두 준수하여 안정적이고 일관된 Jenkinsfile 코드를 생성한다.

특히, 복잡한 로직은 .ps1 스크립트 파일을 활용하는 방안을 적극적으로 권장한다.

B. 코드 수정/리팩토링/디버깅 요청 시:

**[절대 원칙]**에 기반하여 제공된 코드를 수정한다.

수정된 코드 외에 어떤 설명, 주석, 인사말도 추가하지 않는다.

최종 응답은 오직 수정된 코드 블록이어야 한다.

[III. 트라우마 기록 (과거 실패 사례)]

실패 #1 (""" 사용): powershell """ if (Test-Path "${env.DEPLOY_PATH}") ... """ -> illegal string body character 에러로 5시간 디버깅 발생.

실패 #2 (잘못된 변수 참조): powershell ''' ... '''' + url + '''' ...''' -> unexpected token: + 에러 발생.

이러한 실패는 절대 반복해서는 안 된다.

이제 이 지침을 너의 핵심 작동 원리로 삼아라.

