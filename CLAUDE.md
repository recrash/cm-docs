# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Monorepo Architecture

Git subtree-based monorepo combining three independent projects:
- **webservice/**: TestscenarioMaker web service (React + FastAPI + Pseudo-MSA)
- **cli/**: TestscenarioMaker-CLI tool (Python CLI with cross-platform builds)
- **autodoc_service/**: Document automation service for HTML parsing and template generation

### Python Environment Management
**MSA-based Independent Environment Structure**:
```
cm-docs/
├── webservice/.venv/          # Python 3.12 + AI/ML dependencies
├── cli/.venv/                 # Python 3.13 + CLI tool dependencies
└── autodoc_service/.venv312/  # Python 3.12 + document processing (stability)
```

**Service Environment Activation**:
```bash
# Webservice
cd webservice && source .venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH  # Required for src/ modules

# CLI
cd cli && source .venv/bin/activate

# AutoDoc Service
cd autodoc_service && source .venv312/bin/activate
```

### Cross-Platform Path Management
**ALWAYS use `pathlib.Path` for cross-platform compatibility**:
```python
from pathlib import Path
project_root = Path(__file__).parent.parent
# CRITICAL: Convert Path to string for subprocess cwd
subprocess.run(['git', 'status'], cwd=str(repo_path), capture_output=True)
```

### Environment Variable-Based Path System
**Production Deployment Architecture** (커밋 f57efef에서 도입):
```bash
# Production environment variables
export WEBSERVICE_DATA_PATH="C:/deploys/data/webservice"     # Windows
export AUTODOC_DATA_PATH="C:/deploys/data/autodoc_service"   # Windows

# Production deployment structure
C:\deploys\
├── apps\                    # Application execution space (virtual environments & code)
│   ├── webservice\         
│   └── autodoc_service\    
├── data\                   # Persistent data storage (survives updates)
│   ├── webservice\
│   └── autodoc_service\
└── packages\               # Build artifacts (.whl files)

# Development fallback (environment variables 없으면 자동 사용)
# webservice/data/    - webservice 개발환경 기본값
# autodoc_service/data/  - autodoc_service 개발환경 기본값
```

**Data Directory Structure**:
```
data/
├── logs/         # 로그 파일 (환경변수 기반)
├── models/       # AI 임베딩 모델 (webservice만)
├── documents/    # 생성된 문서 출력
├── templates/    # 템플릿 파일 (환경변수 기반)
├── outputs/      # Excel 출력 (webservice만)
└── db/           # 벡터 DB (webservice만)
```

## Webservice Development

### Technology Stack
- **Frontend**: React 18 + TypeScript + Material-UI + Vite
- **Backend**: FastAPI + Python with Pseudo-MSA architecture
- **AI/LLM**: Ollama integration (qwen3:8b model)
- **Vector DB**: ChromaDB for RAG system
- **Testing**: Vitest + Playwright (E2E) + pytest

### ChromaDB 의존성 관리
**제약조건 파일 필수 사용**:
```bash
pip install -r requirements.txt -c pip.constraints.txt  # ✅ 올바른 방법
```

### Development Commands
```bash
# Environment setup
cd webservice && source .venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH  # Required for src/ modules

# Server management
cd webservice/backend && python -m uvicorn main:app --reload --port 8000
cd webservice/frontend && npm run dev

# Testing (hierarchical structure)
cd webservice && pytest tests/unit/                    # Unit tests
cd webservice && pytest tests/api/                     # API tests  
cd webservice && pytest tests/integration/             # Integration tests
cd webservice/frontend && npm run test                 # Frontend unit tests
cd webservice/frontend && npm run test:e2e             # E2E tests (MANDATORY)
cd webservice/frontend && npm run test:all             # All tests

# Single test file
cd webservice && pytest tests/unit/test_config_loader.py
cd webservice && pytest tests/api/v2/test_scenario_v2.py -v

# Development workflow
cd webservice/frontend && npm run lint                 # ESLint check
cd webservice/frontend && npm run build               # Production build
```

### Architecture Details
- **Legacy `src/` modules**: Core analysis logic (git_analyzer, excel_writer, llm_handler)
- **FastAPI Routers** (`backend/routers/`): Domain-based API endpoints
  - `/api/scenario` - v1 scenario generation (legacy)
  - `/api/v2/scenario` - v2 scenario generation (CLI integration)  
  - `/api/v2/ws/progress/{client_id}` - WebSocket progress updates
  - `/api/rag` - RAG system management
  - `/api/feedback` - User feedback collection
  - `/api/files` - File management operations
- **React SPA** (`frontend/`): Material-UI components with real-time WebSocket updates
- **RAG System**: ChromaDB + ko-sroberta-multitask embedding model
- **V2 API Architecture**: CLI-focused endpoints with WebSocket-based progress tracking

### Critical WebSocket Integration
- **V1 WebSocket**: `/api/scenario/generate-ws` (legacy web interface)
- **V2 WebSocket**: `/api/v2/ws/progress/{client_id}` (CLI integration)
- Progress: 10% → 20% → 30% → 80% → 90% → 100%
- Test requires ~60 second wait time
- V2 uses structured message format with status enums (analyzing_git, generating_scenarios, etc.)

### Webservice-Specific Guidelines
- **명확한 명령이나 지시가 있기 전까지는 기존 기능 삭제 금지**
- 프론트엔드 코드를 수정 할 때는 ESlint 정의를 확인하고, 수정을 한 다음에는 Typescript 컴파일 에러를 확인할 것
- **E2E testing mandatory** for functionality verification
- **Korean Language**: All user-facing content in Korean
- Use `pathlib.Path` and relative paths for cross-platform compatibility

### Configuration
```bash
webservice/config.json  # Main config (based on config.example.json)
export PYTHONPATH=$(pwd):$PYTHONPATH  # Required for src/ imports

# Production environment variables (optional, fallback to data/ subdirectories)
export WEBSERVICE_DATA_PATH="/path/to/webservice/data"  # 프로덕션 전용
export AUTODOC_DATA_PATH="/path/to/autodoc/data"        # 프로덕션 전용
```

### Nginx 기반 프론트엔드 배포
- 운영환경: nginx로 서빙 (포트 80)
- 개발환경: Vite 개발서버 (포트 3000)
- Jenkins 파이프라인이 `dist/` 결과물을 `C:\nginx\html`에 전개

## CLI Development

### Technology Stack
- **Core**: Python 3.8+ + Click + Rich + httpx + tenacity
- **Build**: PyInstaller for cross-platform executables
- **Testing**: pytest with unit/integration/e2e markers

### Development Commands
```bash
# Setup
cd cli && source .venv/bin/activate
pip install -e .  # Editable install

# Testing (with coverage)
pytest --cov=ts_cli --cov-report=html         # All tests with coverage
pytest tests/unit/ -v                         # Unit tests only
pytest tests/integration/ -v                  # Integration tests only  
pytest tests/e2e/ -v                         # E2E tests only
pytest -m "not e2e"                          # Skip E2E tests

# Code quality
black ts_cli/ tests/                          # Format code
isort ts_cli/ tests/                          # Sort imports
flake8 ts_cli/ tests/                         # Lint code
mypy ts_cli/                                  # Type checking

# Building  
python scripts/build.py                      # Cross-platform executables
python scripts/build_helper_app.py           # macOS Helper App (sandbox bypass)

# CLI commands
ts-cli --help                                # Show help
ts-cli analyze /path/to/repo                 # Analyze repository
ts-cli info /path/to/repo                    # Repository information
ts-cli config-show                           # Show configuration
ts-cli version                               # Version information
```

### Architecture Details
- **Strategy Pattern**: VCS support via `RepositoryAnalyzer` interface
- **URL Protocol**: `testscenariomaker://` handler
- **macOS Helper**: AppleScript-based helper bypasses sandbox

### CLI Commands
- `ts-cli analyze`: Main analysis with branch comparison
- `ts-cli info <path>`: Show repository information
- `ts-cli config-show`: Display configuration
- `ts-cli version`: Version information

## AutoDoc Service Development

### Technology Stack
- **Core**: FastAPI + Python 3.12 + Pydantic
- **Documents**: python-docx (Word), openpyxl (Excel)
- **HTML Parsing**: BeautifulSoup4 + lxml

### Development Commands  
```bash
# Setup & Run
cd autodoc_service && source .venv312/bin/activate
python run_autodoc_service.py                # Development server

# Testing
pytest app/tests/ -v                         # All tests
pytest app/tests/test_html_parser.py -v      # Specific test file

# Code quality (follows root pyproject.toml)
black app/ --line-length 88                  # Format code
isort app/                                    # Sort imports
```

### Architecture Details
- **Label-Based Template Mapping**: Maps data by finding label text
- **Enhanced Payload System**: Transforms HTML data to Word-compatible format
- **Font Styling**: Applies 맑은 고딕 to all documents

### API Endpoints
- `/parse-html`: HTML file parsing
- `/create-cm-word-enhanced`: Enhanced Word generation (12개 필드 매핑)
- `/create-test-excel`: Excel test scenario generation
- `/download/{filename}`: Secure file download

### API Usage Example
```bash
# Parse HTML
curl -X POST "http://localhost:8000/parse-html" -F "file=@test.html"

# Generate Word with complete field mapping
curl -X POST "http://localhost:8000/create-cm-word-enhanced" \
     -H "Content-Type: application/json" \
     -d '{"raw_data": {...}, "change_request": {...}}'
```

## CI/CD Pipeline (Jenkins)

### NSSM Service Integration
Windows services managed through NSSM:
- **webservice**: Port 8000
- **autodoc_service**: Port 8001
- **Frontend**: nginx on port 80

### Pipeline Architecture
**통합 멀티브랜치 파이프라인** (`Jenkinsfile`):
- Change detection via Git diff
- Parallel service deployment
- Automatic rollback on failure

**Service Pipelines**:
- `webservice/Jenkinsfile.backend`: API testing → NSSM deployment
- `webservice/Jenkinsfile.frontend`: Security → Build → nginx deployment
- `autodoc_service/Jenkinsfile`: Template validation → NSSM deployment

### Development Server
- **Server**: `34.64.173.97` (GCP VM)
- **Ports**: 8000 (Backend), 8001 (AutoDoc), 80 (Frontend)

## Quality Standards

### 로깅 시스템 가이드라인
**Unicode 및 Emoji 사용 금지** (Windows 호환성):
```python
# ❌ 잘못된 예시
logger.info("🚀 서비스 시작...")

# ✅ 올바른 예시
logger.info("서비스 시작...")
```

### Pseudo MSA 개발 원칙
- **로깅 의무화**: 모든 API 엔드포인트에서 로그 기록 필수
- **테스트 의무화**: 기능 추가/변경 시 테스트 코드 필수
- **안정성 우선**: 로깅과 테스트를 통한 유지보수성 확보

### Performance Requirements
- **Webservice API**: <200ms response time
- **CLI**: <30s repository analysis
- **AutoDoc Service**: <1s HTML parsing, <3s document generation
- **Test Coverage**: ≥80% for all services

## Development Workflow

1. **Environment Setup**: Activate service-specific venv (`webservice/.venv`, `cli/.venv`, `autodoc_service/.venv312`)
2. **Development**: Work within subproject directories, maintain independent dependencies
3. **Testing**: Run service-specific test suites before commits
   - Webservice: `pytest tests/` + `npm run test:e2e` (mandatory)
   - CLI: `pytest --cov=ts_cli` 
   - AutoDoc: `pytest app/tests/`
4. **Quality Check**: Black, isort, flake8, mypy (configured in root `pyproject.toml`)
5. **Commit Convention**: Use `[webservice]`, `[cli]`, or `[autodoc_service]` prefixes

### Test Organization
- **Unit tests**: Fast, isolated component tests (`tests/unit/`)
- **API tests**: HTTP endpoint validation (`tests/api/`)
- **Integration tests**: Multi-component workflows (`tests/integration/`)  
- **E2E tests**: Full user journey validation (Playwright in `tests/e2e/`)

### Jenkins Integration
- Main `Jenkinsfile` detects service changes via git diff
- Parallel pipeline execution for modified services only
- Automatic rollback on deployment failures
- Service health checks post-deployment

## Critical Configuration Files

- **Webservice**: `webservice/config.json` (Ollama, RAG settings)
- **CLI**: Hierarchical config loading
- **AutoDoc**: Template files in environment-variable based path (production: `$AUTODOC_DATA_PATH/templates/`, development: `autodoc_service/data/templates/`)
- **Monorepo**: Root `pyproject.toml` for unified tools

## Environment Variable System

### Path Management (커밋 f57efef)
**Production Environment Variables**:
- `WEBSERVICE_DATA_PATH`: webservice 데이터 루트 경로
- `AUTODOC_DATA_PATH`: autodoc_service 데이터 루트 경로

**Development Fallback** (환경변수 미설정시):
- webservice: `webservice/data/`
- autodoc_service: `autodoc_service/data/`

**Path Functions** (자동 디렉토리 생성):
- `get_data_root()`: 환경변수 기반 데이터 루트
- `get_logs_dir()`, `get_templates_dir()`, `get_documents_dir()`
- `get_models_dir()`, `get_outputs_dir()`, `get_vector_db_dir()` (webservice만)

## Template System Architecture

- **Webservice**: Coordinate-based Excel mapping
- **AutoDoc**: Label-based Word mapping (more resilient)
- **Font Consistency**: 맑은 고딕 enforced across all documents

## Key Debugging Patterns

### Webservice Startup Issues
- **RAG System Failures**: Check `startup_rag_system()` in main.py:31
- **Module Import Errors**: Verify `PYTHONPATH=$(pwd):$PYTHONPATH` for src/ modules
- **WebSocket Connection Issues**: Check v2 progress endpoints vs legacy endpoints
- **Config Loading**: Use `test_config_paths.py` to debug environment variable paths

### Service Communication
- **Port Conflicts**: Webservice (8000), AutoDoc (8001), Frontend (80)
- **NSSM Service Status**: `nssm status webservice`, `nssm status autodoc_service`
- **Health Endpoints**: `/api/health` (webservice), `/health` (autodoc_service)
- **CORS Issues**: Check FastAPI middleware settings for React dev server

### Testing Patterns
- **E2E Test Failures**: Often indicate WebSocket timing issues (~60s scenarios)
- **ChromaDB Lock Issues**: Clear vector database: `rm -rf webservice/vector_db_data/`  
- **Dependency Conflicts**: Always use `pip install -r requirements.txt -c pip.constraints.txt`

### CLI Integration Issues
- **V2 API Mismatch**: Check client_id parameter consistency between CLI and WebSocket
- **URL Protocol Handler**: macOS requires helper app for `testscenariomaker://` URLs
- **Cross-platform Paths**: Always use `pathlib.Path`, convert to string for subprocess

## Notes

- **Python Versions**: 3.13 default, 3.12 for AutoDoc (document stability)
- **Path Management**: Always use pathlib.Path, convert to string for subprocess
- **Korean Content**: All user-facing text in Korean
- **E2E Testing**: Mandatory for webservice functionality verification
- **NSSM Services**: Windows service management for production deployment
- **Unicode Logging**: No emojis in logs for Windows compatibility