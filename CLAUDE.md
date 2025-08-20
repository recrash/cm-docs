# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Monorepo Architecture

This is a Git subtree-based monorepo combining three independent projects that share common goals around test automation and document processing:

- **webservice/**: TestscenarioMaker web service (React + FastAPI + Pseudo-MSA)
- **cli/**: TestscenarioMaker-CLI tool (Python CLI with cross-platform builds)
- **autodoc_service/**: Document automation service for HTML parsing and template generation

Each subproject maintains independent development cycles, CI/CD pipelines, and deployment strategies while sharing unified issue tracking and development environment.

### Inter-Service Data Flow
- **CLI → Webservice**: Repository analysis data via HTTP API (`/api/v2/scenario/generate`)
- **Webservice → Files**: Generated Excel scenarios with Korean filenames in `outputs/`
- **AutoDoc Service**: Standalone HTML→Document conversion (no direct integration with other services)
- **RAG System**: Independent document indexing within webservice for enhanced scenario generation

### Git Subtree Management
```bash
# Update from upstream repositories
git subtree pull --prefix=webservice https://github.com/recrash/TestscenarioMaker.git main --squash
git subtree pull --prefix=cli https://github.com/recrash/TestscenarioMaker-CLI.git main --squash

# Push changes back to upstream
git subtree push --prefix=webservice https://github.com/recrash/TestscenarioMaker.git main
git subtree push --prefix=cli https://github.com/recrash/TestscenarioMaker-CLI.git main
```

## Webservice Development - TestscenarioMaker Web Service

### Technology Stack
- **Frontend**: React 18 + TypeScript + Material-UI + Vite
- **Backend**: FastAPI + Python with Pseudo-MSA architecture
- **AI/LLM**: Ollama integration (qwen3:8b model, fallback to qwen3:1.7b)
- **Vector Database**: ChromaDB for RAG system with Korean embeddings
- **Storage**: SQLite for feedback data, Excel files for output
- **Testing**: Jest + Playwright (E2E) + pytest (backend)

### Development Commands
```bash
cd webservice

# Environment setup (CRITICAL: Activate independent Python 3.13 environment first)
source .venv/bin/activate
python --version  # Verify Python 3.13.5
pip install -r requirements.txt
cd webservice/frontend && npm install
export PYTHONPATH=$(pwd):$PYTHONPATH  # Required for src/ modules

# Server management
cd webservice/backend && python -m uvicorn main:app --reload --port 8000  # Backend API
cd webservice/frontend && npm run dev  # Frontend (dev 3000, deploy 80)

# DO NOT use ./start-dev.sh for starting servers
./stop-dev.sh  # Server shutdown

# Testing (E2E testing is MANDATORY for functionality verification)
cd webservice/frontend && npm run test:all        # Complete test suite
cd webservice/frontend && npm run test:e2e        # Playwright E2E tests (required for functionality verification)
cd webservice/frontend && npm run test:e2e:ui     # Playwright UI mode
cd webservice/frontend && npm run test:api        # pytest API tests
cd webservice/frontend && npm run test            # Jest frontend tests
cd webservice/frontend && npm run test:watch      # Jest watch mode
cd webservice/frontend && npm run test:coverage   # Jest coverage report

# Single test execution
pytest tests/api/test_scenario_api.py -v
pytest tests/unit/test_git_analyzer.py::test_function_name -v
pytest --cov=src --cov-report=html --cov-report=term

# Building and utilities
cd webservice/frontend && npm run build           # Frontend production build
cd webservice/frontend && npm run lint           # Frontend linting
python scripts/download_embedding_model.py  # Korean embedding model for offline
curl http://localhost:8000/api/health       # Application health check
```

### Architecture Details

#### Core Architecture Patterns
- **Legacy `src/` modules**: Core analysis logic (git_analyzer, llm_handler, excel_writer, vector_db)
- **FastAPI Routers** (`backend/routers/`): Domain-based API endpoints (scenario, feedback, rag, files, v2)
- **React SPA** (`frontend/`): Components with real-time WebSocket updates
- **RAG System**: ChromaDB + ko-sroberta-multitask for Korean document retrieval

#### Frontend Structure
```
frontend/src/
├── components/          # Reusable UI components
│   ├── ScenarioGenerationTab.tsx    # Main generation interface
│   ├── ScenarioResultViewer.tsx     # Results display with download
│   ├── FeedbackModal.tsx            # User feedback collection
│   ├── RAGSystemPanel.tsx           # RAG system management
│   └── FeedbackAnalysisTab.tsx      # Analytics dashboard
├── services/api.ts      # Axios-based API client
├── types/index.ts       # TypeScript definitions
└── utils/websocket.ts   # WebSocket connection handling
```

#### Backend Structure
```
webservice/backend/
├── main.py              # FastAPI app initialization
├── routers/             # API endpoint modules
│   ├── scenario.py      # Generation endpoints + WebSocket
│   ├── feedback.py      # Feedback collection & analysis
│   ├── rag.py          # RAG system management
│   ├── files.py        # File upload/download/validation
│   └── v2/             # V2 API with CLI integration
└── models/             # Pydantic response models
```

#### Critical WebSocket Integration
- Scenario generation uses WebSocket (`/api/scenario/generate-ws`) for real-time progress
- Progress updates: 10% → 20% → 30% → 80% → 90% → 100% (each with 1-second delay)
- Backend uses `progress.model_dump()` + `json.dumps()` for proper serialization
- Frontend WebSocket URL adapts to environment (localhost:8000 for development)
- Test scenario generation requires ~60 second wait time for completion

#### RAG System Integration
- Document indexing via `/api/rag/index`
- Uses ko-sroberta-multitask for Korean text embeddings
- Supports DOCX, TXT, PDF document formats
- Auto-initializes on backend startup if `rag.enabled: true` in config.json
- Offline environment support with local embedding models

### Webservice-Specific Development Guidelines

#### Fundamental Principles
- **명확한 명령이나 지시가 있기 전까지는 기존에 있는 기능을 삭제하지 말아라** (Never delete existing functionality without explicit instructions)
- **E2E testing mandatory**: Always perform E2E tests using Playwright when testing functionality
- **Korean Language**: All user-facing content must be in Korean

#### Critical Path Management
- Use `pathlib.Path` and relative paths for cross-platform compatibility
- Never use absolute paths - project must build on Windows
- Module imports require PYTHONPATH setup: `export PYTHONPATH=$(pwd):$PYTHONPATH`

#### File Processing and Downloads
- Excel files generated in `outputs/` directory
- Download via `/api/files/download/excel/{filename}`
- Supports Korean filenames with UTF-8 encoding
- Backup files stored in `backups/` directory with security validation

### Configuration and Environment
```bash
# Configuration files
webservice/config.json  # Main config (based on webservice/config.example.json)
# Key settings: model_name (qwen3:8b), rag.enabled, rag.embedding_model

# Environment variables
export PYTHONPATH=$(pwd):$PYTHONPATH  # Required for src/ module imports
export NODE_OPTIONS="--no-deprecation"  # Optional: suppress Node.js warnings

# Offline environment setup
python scripts/download_embedding_model.py  # Downloads ~500MB Korean model
```

### Nginx 기반 프론트엔드 배포

- 운영 환경에서는 프론트엔드를 Node.js 개발 서버가 아닌 nginx로 서빙합니다.
- 기본 포트는 80이며, 개발 모드에서는 여전히 Vite 개발 서버(포트 3000)를 사용합니다.
- Jenkins 파이프라인(`webservice/Jenkinsfile.frontend`)이 `npm run build`로 생성된 `dist/` 결과물을 zip으로 패키징하여 `NGINX_ROOT`(기본값: `C:\nginx\html`)에 전개하고, `FRONTEND_URL`(`http://localhost`)로 배포 검증을 수행합니다.

예시 nginx 설정(Windows 경로 기준):

```nginx
events {
    worker_connections  1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    keepalive_timeout  65;

    # ⭐️ 여기가 핵심 설정 부분!
    server {
        listen       80; # 사용자의 요청을 80 포트에서 받는다
        server_name  localhost;

        # 1. 프론트엔드(React) 처리 규칙
        # React 빌드 결과물(dist 폴더 안의 내용)이 위치할 폴더
        root   C:/nginx/html;

        location / {
            # 이 설정은 React Router 같은 SPA 라우팅을 위한 필수 설정!
            try_files $uri $uri/ /index.html;
        }

        # 2. webservice 백엔드(API) 처리 규칙
        # 주소에 /api/webservice/ 가 포함되면 백엔드로 넘겨준다
        location /api/webservice/ {
            # 백엔드가 실행 중인 8000 포트로 요청을 전달
            proxy_pass http://127.0.0.1:8000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 3. autodoc_service 백엔드(API) 처리 규칙
        # 주소에 /api/autodoc/ 가 포함되면 백엔드로 넘겨준다
        location /api/autodoc/ {
            # autodoc 서비스가 실행 중인 8001 포트로 요청을 전달
            proxy_pass http://127.0.0.1:8001/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

참고:
- Linux 환경에서는 `root /usr/share/nginx/html;` 등 환경에 맞는 경로로 변경하세요.
- 방화벽/보안그룹에서 80 포트가 허용되어야 외부 접속이 가능합니다.

## CLI Development - TestscenarioMaker CLI Tool

### Technology Stack
- **Core**: Python 3.8+ + Click + Rich + httpx + tenacity
- **Build**: PyInstaller for cross-platform executable generation
- **Testing**: pytest with unit/integration/e2e markers
- **Platforms**: Windows (NSIS installer), macOS (DMG + Helper App), Linux

### Development Commands
```bash
cd cli

# Environment setup (CRITICAL: Activate independent Python 3.13 environment first)
source .venv/bin/activate
python --version  # Verify Python 3.13.5

# Development setup
pip install -e .
pip install -r requirements-dev.txt

# Testing
pytest --cov=ts_cli --cov-report=html    # All tests with coverage
pytest -m unit                           # Unit tests only
pytest -m integration                    # Integration tests
pytest -m e2e                           # End-to-End tests
pytest tests/unit/test_vcs.py           # Single test file
pytest tests/unit/test_vcs.py::TestVCSFactory::test_get_analyzer_with_git_repository  # Specific test

# Code quality
black src/ tests/        # Format code
isort src/ tests/        # Sort imports
flake8 src/ tests/       # Lint code
mypy src/                # Type checking

# CLI execution
python -m ts_cli.main --help     # Direct module execution
ts-cli --help                    # After pip install -e .
```

### Building and Distribution
```bash
cd cli

# Cross-platform executable build
python scripts/build.py
python scripts/build.py --no-clean    # Skip cleanup
python scripts/build.py --no-test     # Skip testing

# Platform-specific installers
makensis scripts/setup_win.nsi        # Windows installer (Windows only)
python scripts/create_dmg.py          # macOS DMG + helper app (macOS only)

# macOS Helper App System (solves browser sandbox restrictions)
python scripts/build_helper_app.py    # Build helper app with embedded CLI
python scripts/test_helper_app.py     # Comprehensive helper app testing
sh scripts/install_helper.sh          # Install helper app to Applications
open dist/helper_test.html             # Test URL protocol in browser

# DMG options
python scripts/create_dmg.py --no-helper-app  # DMG without helper app
```

### Architecture Details

#### Strategy Pattern for VCS Support
- **Abstract Base**: `ts_cli.vcs.base_analyzer.RepositoryAnalyzer` defines contract
- **Git Implementation**: `ts_cli.vcs.git_analyzer.GitAnalyzer` (currently the only implementation)
- **Factory Function**: `ts_cli.vcs.get_analyzer()` returns appropriate analyzer
- **Extensibility**: New VCS systems can be added by implementing `RepositoryAnalyzer`

#### URL Protocol Integration (`testscenariomaker://`)
- **Protocol Handler**: `handle_url_protocol()` in `main.py` processes URL schemes
- **Cross-Platform Support**: Windows registry (HKCR) and macOS CFBundleURLTypes
- **macOS Helper App**: AppleScript-based helper bypasses browser sandbox restrictions

#### Core Components Flow
1. **CLI Entry** (`main.py`) → URL protocol detection → Click-based Korean UI
2. **Business Logic** (`cli_handler.py`) → Orchestrates repo analysis → API call → result processing
3. **VCS Analysis** (`vcs/`) → Strategy pattern for repository analysis
4. **API Client** (`api_client.py`) → httpx + tenacity for robust communication
5. **Configuration** (`utils/config_loader.py`) → Multi-location config file loading
6. **Logging** (`utils/logger.py`) → Rich console + file logging

#### macOS Helper App System
Solves macOS browser sandbox restrictions that prevent CLI network communication:

**Problem**: Browser-launched CLI inherits sandbox restrictions, blocking API calls
**Solution**: AppleScript-based helper app launches CLI as independent process

**Key Files**:
- `scripts/helper_app.applescript`: Core AppleScript URL handler
- `scripts/helper_app_info.plist`: App bundle configuration with URL scheme registration  
- `scripts/build_helper_app.py`: Automated helper app builder with CLI embedding
- `scripts/test_helper_app.py`: Comprehensive testing framework

**Workflow**: Browser Click → testscenariomaker:// → Helper App → Independent CLI Process → API Success

### CLI-Specific Development Guidelines

#### Critical Cross-Platform Path Management
**ALWAYS use `pathlib.Path` for cross-platform compatibility**

✅ **Correct Usage**:
```python
from pathlib import Path

# Project structure with relative paths
project_root = Path(__file__).parent.parent
config_file = project_root / "config" / "config.ini"

# CRITICAL: Convert Path to string for subprocess cwd parameter
subprocess.run(['git', 'status'], cwd=str(repo_path), capture_output=True)
```

❌ **Avoid These Patterns**:
```python
# DON'T: String concatenation or os.path methods
config_path = project_root + "/config/config.ini"
config_path = os.path.join(project_root, "config", "config.ini")

# DON'T: Path object as cwd parameter (causes cross-platform issues)
subprocess.run(['git', 'status'], cwd=repo_path)  # Will fail!
```

#### Configuration System
**Hierarchical Config Loading** (first found wins):
1. Current directory `config.ini`
2. Project root `config/config.ini`  
3. Auto-generated defaults

**Key Config Sections**:
- `[api]`: base_url, timeout, max_retries
- `[cli]`: default_output_format, verbose, show_progress
- `[logging]`: level, file_enabled (format uses %% escaping for ConfigParser)
- `[vcs]`: git_timeout, max_diff_size

#### CLI Commands
- `ts-cli analyze`: Main analysis command with branch comparison (default: origin/develop → HEAD)
- `ts-cli info <path>`: Show repository information without analysis
- `ts-cli config-show`: Display current configuration  
- `ts-cli version`: Show version information
- `ts-cli "testscenariomaker://path"`: Direct URL protocol handling for testing

### Testing Strategy
- **Unit Tests** (`tests/unit/`): Mock-based isolated component testing
- **Integration Tests** (`tests/integration/`): API communication with mock servers  
- **E2E Tests** (`tests/e2e/`): Full CLI workflow using subprocess (not Playwright - this is CLI, not web)
- **Cross-Platform Tests**: `test_path_compatibility.py` for path handling validation
- **Helper App Tests**: `test_helper_app.py` for comprehensive macOS helper app validation

## AutoDoc Service Development - Document Automation Service

### Technology Stack
- **Core**: FastAPI + Python 3.12 + Pydantic (Python 3.12 for document generation stability)
- **Document Generation**: python-docx (Word), openpyxl (Excel)
- **HTML Parsing**: BeautifulSoup4 + lxml
- **Testing**: pytest with AsyncHTTPX client
- **Deployment**: Uvicorn ASGI server with cross-platform scripts

### Development Commands
```bash
cd autodoc_service

# Environment setup (CRITICAL: Activate independent Python 3.12 environment first)
source .venv312/bin/activate
python --version  # Verify Python 3.12.11

# Automatic startup (recommended)
python run_autodoc_service.py          # Cross-platform Python script
./run_autodoc_service.sh              # macOS/Linux
.\run_autodoc_service.ps1             # Windows PowerShell

# Manual setup
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Testing
pytest app/tests/ -v                   # All tests
pytest --cov=app --cov-report=html app/tests/  # With coverage

# API access
curl http://localhost:8000/health      # Health check
open http://localhost:8000/docs        # FastAPI auto-generated docs
```

### Architecture Details

#### Core Service Flow
1. **HTML Parser** (`app/parsers/itsupp_html_parser.py`) → Extracts structured data from IT지원의뢰서 HTML
2. **Document Builders** (`app/services/`) → Template-based Word/Excel generation
3. **Path Management** (`app/services/paths.py`) → Cross-platform file handling with security
4. **File Management** (`app/main.py`) → Download endpoint with path traversal protection

#### API Endpoints Structure
```
/                         # Root info endpoint
/health                  # Health check with template validation
/parse-html              # HTML file upload and parsing
/create-cm-word-enhanced # Enhanced Word document generation (완전한 12개 필드 매핑)
/create-test-excel       # Excel test scenario generation 
/create-cm-list          # Excel list generation (multiple items)
/download/{filename}     # Secure file download
/templates               # Available template listing
/documents               # Generated document listing
```

#### Core Architecture Patterns

##### 1. Label-Based Template Mapping (Primary System)
- **Location**: `app/services/label_based_word_builder.py`
- **Purpose**: Maps data to Word templates by finding label text instead of relying on fixed cell indices
- **Resilience**: Template structure changes don't break the mapping
- **Special Cases**: Table 2 has custom handling for complex date placement logic

##### 2. Enhanced Payload System
- **Location**: `app/services/word_payload.py` 
- **Purpose**: Transforms raw HTML parsing data into Word-compatible format
- **Intelligence**: 
  - Auto-extracts department from applicant field segments (`홍길동/Manager/IT운영팀/SK AX` → `IT운영팀`)
  - System-specific deployer mapping (extensible via `get_system_deployer()`)
  - Structured content generation for purpose/improvement fields

##### 3. Font Styling System
- **Word**: `app/services/font_styler.py` - Applies 맑은 고딕 to all Word content
- **Excel**: `app/services/excel_font_styler.py` - Applies 맑은 고딕 to all Excel content
- **Integration**: Automatically applied during document generation for 100% font consistency

##### 4. HTML → Structured Data Pipeline
- **Parser**: `app/parsers/itsupp_html_parser.py` - Extracts specific fields from IT지원의뢰서 HTML
- **Validation**: Uses CSS selectors with robust fallback patterns
- **Critical Rule**: Parser logic is fixed and should not be modified without careful testing

#### Document Generation Flow

```
HTML File → parse_itsupp_html() → Raw Data Dict
                ↓
Raw Data → build_word_payload() → Enhanced Payload (12개 필드 보완)
                ↓
Enhanced Payload → fill_template_by_labels() → Fully Mapped Document
                ↓
Document → ensure_malgun_gothic_document() → Final Document
```

**핵심 개선사항**:
- **완전한 필드 매핑**: 12개 필드 모두 정상 매핑 (작업일시, 배포일시, 처리자 포함)
- **Enhanced Payload**: raw_data를 통한 누락 필드 자동 보완
- **구조화된 내용**: 목적-개선내용을 "1. 목적\n2. 주요 내용" 형식으로 자동 구조화
- **HTML 태그 변환**: `<br>` 태그를 줄바꿈으로 자동 변환

#### Template System Requirements
- **Word Template** (`templates/template.docx`): Label-based mapping with comprehensive field support
- **Excel Templates**: 
  - `template.xlsx`: Test scenarios with predefined cell coordinates
  - `template_list.xlsx`: 11-column list format for multiple items

#### Security and Validation
- **Path Traversal Protection**: `file_path.resolve().relative_to(documents_dir.resolve())`
- **Template Integrity**: SHA-256 verification in tests
- **Input Sanitization**: Filename cleanup for cross-platform compatibility
- **Pydantic Validation**: Strict data model enforcement

### AutoDoc Service-Specific Development Guidelines

#### 로깅 및 테스트 표준 (Logging and Testing Standards)
- **로깅 의무**: 모든 API 엔드포인트와 서비스 모듈에서 로그 기록 필수
- **로그 위치**: `autodoc_service/logs/YYYYMMDD_autodoc.log` (일별 파일)
- **로그 형식**: `"%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"`
- **로깅 패턴**: 요청 수신 → 처리 과정 → 성공/실패 결과 (처리 시간, 파일 크기 포함)
- **테스트 완성도**: 기능 변경 시 테스트 코드 함께 작성하여 안정성 확보
- **디버깅 지원**: 상세한 로그를 통한 문제 상황 추적 및 해결 지원

#### Offline Environment Support
**Office-less Design**: No Microsoft Office dependency, uses python-docx and openpyxl
```bash
# Offline wheel preparation (internet-connected environment)
pip download -r requirements.txt -d wheels

# Offline installation (air-gapped environment)  
pip install --no-index --find-links ./wheels -r requirements.txt
```

#### Template Requirements
**Critical Template Files** (must exist in `templates/` directory):
- `template.docx`: Word document template with predefined table structure
- `template.xlsx`: Excel test scenario template  
- `template_list.xlsx`: Excel list template for multiple items

**Template Validation**: All templates verified with SHA-256 hashes in test suite

#### Path Management
- Always use `pathlib.Path` for cross-platform compatibility
- Use `app.services.paths` functions for consistent directory resolution
- Templates can be overridden via `AUTODOC_TPL_DIR` environment variable

#### Field Mapping Extensions
To add system-specific deployer mapping:
1. Edit `get_system_deployer()` in `word_payload.py`
2. Add entries to `system_deployer_mapping` dictionary
3. Supports both system names and abbreviations

#### Template Structure Changes
If Word template structure changes:
1. Test with `debug_*` scripts in root directory for structure analysis
2. Update cell mapping in `get_data_cell_for_label()` function
3. Add special handling functions if needed (like `handle_table2_special()`)

#### Font Consistency Guidelines
- **Document-wide Application**: Use `ensure_malgun_gothic_document()` for 100% font consistency
- **Individual Cell Styling**: Use `apply_malgun_gothic_to_cell()` for specific cells
- **Excel Styling**: Use `Font(name='맑은 고딕')` for Excel cell formatting

### API Usage Patterns

#### HTML Parsing Workflow
```bash
# Upload HTML file and get structured JSON
curl -X POST "http://localhost:8000/parse-html" \
     -F "file=@규격_확정일자.html"
```

#### Document Generation Workflow

**권장 워크플로우** (완전한 필드 매핑):
```bash
# 1. HTML 파싱하여 구조화된 데이터 추출
curl -X POST "http://localhost:8000/parse-html" \
     -F "file=@testHTML/충유오더.html"

# 2. 향상된 엔드포인트로 완전한 Word 문서 생성
curl -X POST "http://localhost:8000/create-cm-word-enhanced" \
     -H "Content-Type: application/json" \
     -d '{
       "raw_data": {
         "제목": "[Bug 개선] 시스템 구조 개선",
         "처리자_약칭": "홍길동",
         "작업일시": "08/06 18:00",
         "배포일시": "08/07 13:00",
         "요청사유": "현재 시스템 개선 필요",
         "요구사항 상세분석": "1. 성능 개선<br>2. 안정성 향상"
       },
       "change_request": {
         "change_id": "LIMS_20250814_1",
         "system": "울산 실험정보(LIMS)", 
         "title": "시스템 구조 개선",
         "requester": "홍길동"
       }
     }'

# 3. 생성된 완전한 문서 다운로드
curl -O "http://localhost:8000/download/[250814 홍길동] 변경관리요청서 LIMS_20250814_1 시스템 구조 개선.docx"
```

**단순 워크플로우** (기본 정보만):
```bash
# 기본 정보로만 문서 생성 (일부 필드 누락 가능)
curl -X POST "http://localhost:8000/create-cm-word-enhanced" \
     -H "Content-Type: application/json" \
     -d '{
       "change_request": {
         "change_id": "LIMS_20250814_1",
         "system": "울산 실험정보(LIMS)",
         "title": "시스템 구조 개선",
         "requester": "홍길동"
       }
     }'
```

### Testing Strategy
- **Template Validation**: SHA-256 hash verification ensures template integrity
- **Parser Accuracy**: Fixture-based HTML parsing validation  
- **API Integration**: FastAPI TestClient with async support
- **Cross-Platform**: Path handling and filename sanitization tests
- **Security**: Path traversal attack prevention tests

## CI/CD Pipeline (Jenkins)

### Enterprise-Grade Pseudo MSA CI/CD Architecture
The project implements a sophisticated Jenkins-based CI/CD system designed specifically for Pseudo MSA architecture with NSSM service management:

#### NSSM Service Integration
**Windows Service Management**: All Python applications run as native Windows services through NSSM (Non-Sucking Service Manager)

**Service Configuration**:
- **webservice**: NSSM-managed service on port 8000 (Backend) 
- **autodoc_service**: NSSM-managed service on port 8001
- **Frontend**: nginx-served static files on port 80

**Service Control Commands**:
```bash
# Service management via Jenkins
nssm stop webservice && nssm start webservice     # Backend deployment
nssm stop autodoc_service && nssm start autodoc_service  # AutoDoc deployment
# Frontend: Direct nginx file replacement
```

#### Advanced Pipeline Features

##### 1. **Intelligent Change Detection & Routing**
- **Git-based Analysis**: Compares `HEAD~1` vs `HEAD` for precise change detection
- **Service-Specific Triggers**: Only builds/deploys modified services
- **Dependency-Aware**: Root config changes trigger full system rebuild
- **Parallel Optimization**: Independent services build simultaneously

##### 2. **Dependency Management & Validation**
- **Smart Dependency Updates**: Detects `requirements.txt`/`package.json` changes
- **Compatibility Verification**: Python version-specific validation (3.12 vs 3.13)
- **Conflict Detection**: `pip check` and `npm audit` integration
- **Template Integrity**: SHA-256 verification for critical template files

##### 3. **Multi-Layer Testing Strategy**
```bash
# Testing Hierarchy
├── Unit Tests: pytest/Jest individual component testing
├── Integration Tests: FastAPI TestClient + cross-service validation
├── API Tests: Full endpoint validation with health checks
├── E2E Tests: Playwright browser automation
├── Security Tests: npm audit + dependency vulnerability scanning
└── Document Generation Tests: Real-world template processing
```

##### 4. **Production-Ready Deployment**
- **Blue-Green Strategy**: Backup creation before deployment
- **Automatic Rollback**: Failed deployments trigger immediate previous version restoration
- **Health Check Validation**: Multi-endpoint verification with retry logic
- **Service Verification**: Real document generation testing post-deployment

#### Pipeline Architecture

##### **통합 멀티브랜치 파이프라인** (`Jenkinsfile`)
**Master orchestration pipeline** that coordinates all service deployments:

```groovy
// Change Detection Logic
AUTODOC_CHANGED = changedFiles.contains('autodoc_service/')
WEBSERVICE_CHANGED = changedFiles.contains('webservice/')  
CLI_CHANGED = changedFiles.contains('cli/')
ROOT_CHANGED = changedFiles.contains('Jenkinsfile') || changedFiles.contains('README.md')

// Parallel Service Deployment
parallel {
    stage('Backend') { build job: 'webservice-backend-pipeline' }
    stage('Frontend') { build job: 'webservice-frontend-pipeline' }
}
```

##### **Service-Specific Pipelines**

**Webservice Backend** (`webservice/Jenkinsfile.backend`):
```bash
Stage 1: Dependency Check (requirements.txt change detection)
Stage 2: Test (pytest tests/api/ -v --tb=short)
Stage 3: Build Validation (PYTHONPATH + module import verification)
Stage 4: Create Backup (current service state preservation)
Stage 5: Build (python -m build)
Stage 6: Deploy (NSSM service restart with new wheel)
Stage 7: Health Check (5-retry API validation)
```

**Webservice Frontend** (`webservice/Jenkinsfile.frontend`):
```bash
Stage 1: Dependency Check (npm cache optimization)
Stage 2: Security Check (npm audit with auto-fix)
Stage 3: Lint & Type Check (ESLint + TypeScript validation)
Stage 4: Test (npm run test -- --run --reporter=verbose)
Stage 5: Create Backup (nginx file backup)
Stage 6: Build & Package (npm run build + zip creation)
Stage 7: Deploy (nginx static file replacement)
Stage 8: Deployment Verification (HTTP response validation)
```

**AutoDoc Service** (`autodoc_service/Jenkinsfile`):
```bash
Stage 1: Template Validation (SHA-256 integrity + existence check)
Stage 2: Dependency Check (Python 3.12 specific validation)
Stage 3: Test (pytest with coverage + document generation testing)
Stage 4: Integration Test (FastAPI + logging system validation)
Stage 5: Create Backup (service state preservation)
Stage 6: Build (python -m build with validation)
Stage 7: Deploy (NSSM service restart)
Stage 8: API Health Check (multi-endpoint validation)
Stage 9: Document Generation Test (real Word document creation)
```

#### Development Server Environment
- **Server**: `34.64.173.97` (GCP VM T4 instance: vCPU:4, RAM:15GB)
- **Service Ports**: 
  - `8000`: Webservice Backend (FastAPI with NSSM)
  - `8001`: AutoDoc Service (FastAPI with NSSM)
  - `80`: Webservice Frontend (nginx static)
- **OS**: Windows Server with PowerShell-based automation
- **Service Management**: NSSM for reliable service lifecycle management

#### Enhanced Jenkins Workflow
```bash
# Complete Pipeline Flow
1. 📥 소스코드 체크아웃 및 변경 감지
   └── Git diff analysis + service-specific change detection

2. 🔧 AutoDoc Service CI/CD (Python 3.12)
   ├── Template integrity validation (SHA-256)
   ├── Python-docx/openpyxl compatibility check
   ├── Comprehensive testing (unit/integration/API)
   ├── NSSM service deployment
   └── Real document generation verification

3. 🌐 Webservice CI/CD (Python 3.13 + React) - Parallel Execution
   ├── Backend Pipeline:
   │   ├── API testing with pytest
   │   ├── PYTHONPATH validation
   │   ├── NSSM service deployment  
   │   └── Health check validation
   └── Frontend Pipeline:
       ├── npm security audit
       ├── ESLint + TypeScript validation
       ├── React build optimization
       ├── nginx deployment
       └── Static file verification

4. ⚡ CLI CI/CD (Python 3.13)
   ├── Cross-platform testing
   ├── Build executable creation
   └── Artifact archival

5. 🔍 통합 테스트
   ├── E2E testing with Playwright
   ├── Service communication validation
   └── End-to-end workflow verification

6. 🚀 스마트 배포 상태 확인
   ├── Deployment success confirmation
   ├── Service health validation
   └── Performance metric collection

7. 📊 배포 리포트 및 알림
   ├── Detailed deployment summary
   ├── Service status reporting
   └── Failure notification (Slack integration ready)
```

#### Advanced Error Handling & Recovery

##### **Automatic Rollback System**
```bash
# Deployment Failure Recovery
try {
    nssm stop service && deploy_new_version && nssm start service
} catch (Exception) {
    nssm stop service && restore_backup_version && nssm start service
    throw "Deployment failed - automatically rolled back"
}
```

##### **Multi-Retry Health Checks**
```bash
# Health Validation with Exponential Backoff
for (int i = 0; i < 5; i++) {
    response = curl -s -w "%{http_code}" ${HEALTH_URL}
    if (response == "200") break
    sleep(5 * (i + 1))  # 5s, 10s, 15s, 20s, 25s
}
```

#### Jenkins Project Structure
```
Jenkins Projects:
├── cm-docs-integration          # Master orchestration pipeline
├── webservice-backend-pipeline  # Backend-specific CI/CD
├── webservice-frontend-pipeline # Frontend-specific CI/CD
└── autodoc-service-pipeline     # AutoDoc-specific CI/CD
```

#### Performance Optimizations
- **Parallel Pipeline Execution**: Backend/Frontend build simultaneously
- **npm Cache Management**: Aggressive caching with offline fallback
- **Incremental Building**: Only changed services are rebuilt
- **Resource Management**: Memory and CPU usage optimization
- **Artifact Caching**: Wheel files and build artifacts preserved

#### Quality Gates & Validation
- **Code Quality**: ESLint, Black, isort, mypy integration
- **Security Scanning**: npm audit, pip vulnerability checks  
- **Test Coverage**: Minimum 80% coverage requirements
- **Performance Testing**: Response time validation
- **Integration Testing**: Cross-service communication validation

#### Manual Pipeline Testing
```bash
# Pre-deployment validation commands
cd webservice && source .venv/bin/activate && npm run test:all
cd cli && source .venv/bin/activate && pytest --cov=ts_cli
cd autodoc_service && source .venv312/bin/activate && pytest app/tests/ -v
```

#### Deployment URLs (Development Server)
- **AutoDoc Service**: `http://34.64.173.97:8001` (NSSM-managed)
- **Webservice Backend**: `http://34.64.173.97:8000` (NSSM-managed)
- **Webservice Frontend**: `http://34.64.173.97` (nginx-served)

#### Enterprise Features
- **Audit Trail**: Complete deployment history with rollback capability
- **Monitoring Integration**: Ready for Prometheus/Grafana integration
- **Notification System**: Slack/Email alerts for deployment status
- **Resource Monitoring**: CPU/Memory usage tracking during deployment
- **Security Compliance**: Vulnerability scanning and dependency validation

## Monorepo-wide Quality Control

### Code Quality Commands (from project root)
```bash
# Code formatting
black webservice/src webservice/backend cli/src cli/tests autodoc_service/app
isort webservice/src webservice/backend cli/src cli/tests autodoc_service/app

# Linting  
flake8 webservice/src webservice/backend cli/src cli/tests autodoc_service/app

# Type checking
mypy webservice/src cli/src autodoc_service/app

# Unified testing (all three projects)
cd webservice && npm run test:all
cd cli && pytest --cov=ts_cli --cov-report=html
cd autodoc_service && pytest --cov=app --cov-report=html app/tests/
```

### Development Workflow Guidelines
1. **Subproject Focus**: Work within specific subproject directories (`cd webservice`, `cd cli`, or `cd autodoc_service`)
2. **Independent Testing**: Each subproject has its own test suite and quality gates
3. **Commit Conventions**: Use `[webservice]`, `[cli]`, or `[autodoc_service]` prefixes in commit messages  
4. **Quality Gates**: All projects require passing tests before merge
5. **Korean Documentation**: Technical documentation includes Korean user-facing content

## Pseudo MSA 서비스 개발 원칙 (Pseudo MSA Development Principles)

### 핵심 개발 원칙
- **로깅 의무화**: 모든 백엔드 서비스는 업무 수행 시마다 로그 기록 필수
- **테스트 의무화**: 기능 추가/변경 시 테스트 코드 생성 무조건 수반
- **안정성 우선**: 로깅과 테스트를 통한 유지보수성과 디버깅 용이성 확보

### 로깅 가이드라인
- **기본 요구사항**: 모든 API 엔드포인트에서 요청 수신, 처리 과정, 결과 로그
- **오류 처리**: 예외 발생 시 상세한 스택 트레이스와 컨텍스트 정보 로그
- **성능 메트릭스**: 처리 시간, 리소스 사용량, 데이터 크기 등 기록
- **상황별 최적화**: 서비스 특성에 맞는 로그 형식, 로테이션, 보관 정책 적용

### 테스트 가이드라인
- **동시 개발**: 기능 구현과 테스트 코드는 동시에 작성
- **포괄적 커버리지**: Unit, Integration, E2E 테스트 모두 포함
- **로깅 테스트**: 로그 생성 및 내용 검증 테스트 포함
- **품질 게이트**: 테스트 통과 없이는 기능 완성 인정 안함

### 구현 가이드라인
- **새 서비스 생성 시**: 로깅 시스템 구성을 첫 번째 작업으로 수행
- **API 엔드포인트**: 요청 수신/처리 성공/실패 로그 필수
- **예외 처리**: `logger.exception()` 사용하여 스택 트레이스 포함
- **성능 추적**: 처리 시간 측정 및 로그 기록으로 성능 모니터링

## 로깅 시스템 가이드라인 (중요)

### Unicode 및 Emoji 사용 금지 (필수)
**Windows 환경에서 콘솔 출력 시 Unicode 인코딩 오류(UnicodeEncodeError)를 방지하기 위해 다음을 반드시 준수:**

- **이모지 사용 금지**: 로그 메시지에서 🚀, ✅, ❌, ⚠️, 💡, 📊, 🔍, 🎯 등 모든 이모지 제거
- **Unicode 특수문자 최소화**: 기본 ASCII 문자 사용 권장
- **한국어는 허용**: 한국어 텍스트는 사용 가능하나 이모지는 제거

#### 올바른 로깅 예시
```python
# ❌ 잘못된 예시 (이모지 포함)
logger.info("🚀 서비스 시작...")
logger.error("❌ 처리 실패")

# ✅ 올바른 예시 (이모지 제거)
logger.info("서비스 시작...")
logger.error("처리 실패")
```

### 적용 범위
- **webservice/**: 모든 backend 로깅 시스템
- **cli/**: CLI 출력 및 로깅 시스템
- **autodoc_service/**: FastAPI 로깅 시스템
- **테스트 코드**: 테스트 출력 메시지에서도 이모지 제거

## Performance and Quality Standards

- **Webservice API**: <200ms response time, <1s WebSocket connection
- **CLI**: <30s repository analysis, <5s URL protocol processing  
- **AutoDoc Service**: <1s HTML parsing, <3s Word generation, <2s Excel generation
- **Test Coverage**: Webservice ≥80% unit + ≥70% integration, CLI ≥85% overall, AutoDoc Service ≥85% overall
- **Build Time**: Complete monorepo build <10 minutes
- **Logging Coverage**: 모든 API 엔드포인트와 서비스 모듈에서 로그 기록 100%

## Critical Configuration Files

- **Webservice Config**: `webservice/config.json` (based on `webservice/config.example.json`)
  - Ollama model settings (`qwen3:8b`), RAG system configuration, offline embedding paths
- **CLI Config**: Hierarchical loading from current directory, project root, then defaults
- **AutoDoc Service Config**: `autodoc_service/requirements.txt` for dependencies
  - Templates directory must contain: `template.docx`, `template.xlsx`, `template_list.xlsx`
- **Monorepo**: Root `pyproject.toml` for unified development tools (black, isort, pytest)

## Python 환경 관리 (Claude 작업 지침)

### MSA 기반 서비스별 독립 환경 구조

이 모노래포는 **Pseudo MSA 아키텍처**를 따르므로 각 서비스가 완전히 독립된 가상환경을 사용합니다.

```
cm-docs/
├── webservice/
│   ├── .venv/          # Python 3.13 + AI/ML 의존성
│   └── requirements.txt
├── cli/
│   ├── .venv/          # Python 3.13 + CLI 도구 의존성  
│   └── requirements.txt
└── autodoc_service/
    ├── .venv312/       # Python 3.12 + 문서처리 의존성 (안정성 보장)
    └── requirements.txt
```

### 작업 전 필수 체크리스트

**모든 개발/테스트 작업 전에 다음을 반드시 수행:**

1. **프로젝트 디렉토리 확인**
2. **올바른 가상환경 활성화** 
3. **Python 버전 검증**

### 서비스별 환경 활성화 명령어

#### Webservice 작업 시
```bash
cd webservice
source .venv/bin/activate
python --version  # 3.13.5 확인
# AI/ML 최신 기능 및 성능 활용
# 이후 개발/테스트 명령 수행
```

#### CLI 작업 시
```bash
cd cli
source .venv/bin/activate
python --version  # 3.13.5 확인
# 크로스플랫폼 도구 최신 기능 활용
# 이후 개발/테스트 명령 수행
```

#### AutoDoc Service 작업 시
```bash
cd autodoc_service
source .venv312/bin/activate
python --version  # 3.12.11 확인 (문서 생성 안정성을 위한 고정 버전)
# python-docx, openpyxl 호환성 보장
# 이후 개발/테스트 명령 수행
```

### 신규 서비스 추가 가이드라인

새로운 서비스를 모노래포에 추가할 때:

1. **Python 3.13 기본 정책**: 특별한 호환성 이슈가 없는 한 Python 3.13 사용
2. **독립 가상환경**: `{service_name}/.venv` 구조로 생성
3. **독립 의존성**: 서비스별 최소 필요 패키지만 포함
4. **MSA 원칙**: 다른 서비스와 의존성 공유 금지

### 개발 워크플로 예시

#### 시나리오 1: Webservice 기능 개발
```bash
# 1. 환경 설정 및 서버 시작
cd webservice
source .venv/bin/activate
python --version  # 3.13.5 확인
export PYTHONPATH=$(pwd):$PYTHONPATH

# 2. 개발 서버 시작 (터미널 2개 필요)
cd backend && python -m uvicorn main:app --reload --port 8000  # 터미널 1
cd frontend && npm run dev  # 터미널 2

# 3. 기능 개발 후 테스트
cd webservice/frontend && npm run test:all  # 전체 테스트
cd webservice/frontend && npm run test:e2e  # E2E 테스트 (필수)
pytest tests/api/test_scenario_api.py -v    # 특정 API 테스트
```

#### 시나리오 2: CLI 도구 개발
```bash
# 1. 환경 설정 및 개발 설치
cd cli
source .venv/bin/activate
python --version  # 3.13.5 확인
pip install -e .

# 2. 기능 개발 후 테스트
pytest tests/unit/test_vcs.py -v            # 단위 테스트
pytest -m integration                       # 통합 테스트
ts-cli analyze --help                       # CLI 동작 확인

# 3. 크로스플랫폼 빌드
python scripts/build.py                     # 실행파일 빌드
```

#### 시나리오 3: AutoDoc Service 개발
```bash
# 1. 환경 설정 및 서버 시작
cd autodoc_service
source .venv312/bin/activate
python --version  # 3.12.11 확인 (안정성을 위한 고정 버전)
python run_autodoc_service.py              # 서버 시작

# 2. 기능 개발 후 테스트
pytest app/tests/ -v                        # 전체 테스트
pytest --cov=app --cov-report=html app/tests/  # 커버리지 확인
curl http://localhost:8000/health           # 헬스체크
```

#### 시나리오 4: 모노레포 전체 품질 관리
```bash
# 코드 포매팅 (프로젝트 루트에서)
black webservice/src webservice/backend cli/src cli/tests autodoc_service/app
isort webservice/src webservice/backend cli/src cli/tests autodoc_service/app

# 린팅
flake8 webservice/src webservice/backend cli/src cli/tests autodoc_service/app

# 타입 체킹
mypy webservice/src cli/src autodoc_service/app

# 전체 테스트 실행
cd webservice && npm run test:all
cd ../cli && pytest --cov=ts_cli --cov-report=html
cd ../autodoc_service && pytest --cov=app --cov-report=html app/tests/
```

### AutoDoc Service 특별 고려사항

**Python 3.12 고정 이유:**
- `python-docx 1.1.0`, `openpyxl 3.1.2`의 Python 3.13 호환성 미검증
- 워드/엑셀 문서 생성의 안정성이 비즈니스 크리티컬
- 향후 라이브러리 업데이트 후 3.13 마이그레이션 고려

### Template System Architecture (Cross-Service)

**Webservice Excel Templates**: Uses coordinate-based cell mapping for test scenario generation
**AutoDoc Service Templates**: Uses label-based mapping for robust Word document generation
- **Key Difference**: AutoDoc's label-based system is more resilient to template structure changes
- **Template Dependencies**: Both services require specific template files in their respective `templates/` directories
- **Font Consistency**: Both enforce 맑은 고딕 font across all generated documents

## Legacy Migration Notes

**Webservice Evolution**: Migrated from Streamlit to React+FastAPI
- Web interface moved from `app.py` (Streamlit) to React SPA
- Real-time updates via WebSocket instead of Streamlit rerun  
- Enhanced testing with E2E coverage using Playwright
- Improved file management and download system with Korean filename support