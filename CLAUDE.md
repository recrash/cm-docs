# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Monorepo Architecture

This is a Git subtree-based monorepo combining three independent projects that share common goals around test automation and document processing:

- **webservice/**: TestscenarioMaker web service (React + FastAPI + Pseudo-MSA)
- **cli/**: TestscenarioMaker-CLI tool (Python CLI with cross-platform builds)
- **autodoc_service/**: Document automation service for HTML parsing and template generation

Each subproject maintains independent development cycles, CI/CD pipelines, and deployment strategies while sharing unified issue tracking and development environment.

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

# Environment setup (CRITICAL: PYTHONPATH required for src/ modules)
pip install -r requirements.txt
npm install
export PYTHONPATH=$(pwd):$PYTHONPATH

# Server management
cd webservice/backend && python -m uvicorn main:app --reload --port 8000  # Backend API
npm run dev  # Frontend (port 3000) - run from project root

# DO NOT use ./start-dev.sh for starting servers
./stop-dev.sh  # Server shutdown

# Testing (E2E testing is MANDATORY for functionality verification)
npm run test:all        # Complete test suite
npm run test:e2e        # Playwright E2E tests (required for functionality verification)
npm run test:e2e:ui     # Playwright UI mode
npm run test:api        # pytest API tests
npm run test            # Jest frontend tests
npm run test:watch      # Jest watch mode
npm run test:coverage   # Jest coverage report

# Single test execution
pytest tests/api/test_scenario_api.py -v
pytest tests/unit/test_git_analyzer.py::test_function_name -v
pytest --cov=src --cov-report=html --cov-report=term

# Building and utilities
npm run build           # Frontend production build
npm run lint           # Frontend linting
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

## CLI Development - TestscenarioMaker CLI Tool

### Technology Stack
- **Core**: Python 3.8+ + Click + Rich + httpx + tenacity
- **Build**: PyInstaller for cross-platform executable generation
- **Testing**: pytest with unit/integration/e2e markers
- **Platforms**: Windows (NSIS installer), macOS (DMG + Helper App), Linux

### Development Commands
```bash
cd cli

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
- **Core**: FastAPI + Python 3.8+ + Pydantic
- **Document Generation**: python-docx (Word), openpyxl (Excel)
- **HTML Parsing**: BeautifulSoup4 + lxml
- **Testing**: pytest with AsyncHTTPX client
- **Deployment**: Uvicorn ASGI server with cross-platform scripts

### Development Commands
```bash
cd autodoc_service

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
/                    # Root info endpoint
/health             # Health check with template validation
/parse-html         # HTML file upload and parsing
/create-cm-word     # Word document generation (ChangeRequest → .docx)
/create-test-excel  # Excel test scenario generation 
/create-cm-list     # Excel list generation (multiple items)
/download/{filename} # Secure file download
/templates          # Available template listing
/documents          # Generated document listing
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
Raw Data → build_word_payload() → Enhanced Payload
                ↓
Enhanced Payload → fill_template_by_labels() → Mapped Document
                ↓
Document → ensure_malgun_gothic_document() → Final Document
```

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
```bash
# Generate Word document
curl -X POST "http://localhost:8000/create-cm-word" \
     -H "Content-Type: application/json" \
     -d '{"change_id": "LIMS_20250814_1", "system": "울산 실험정보(LIMS)", 
          "title": "시스템 구조 개선", "requester": "홍길동"}'

# Download generated file
curl -O "http://localhost:8000/download/[250814 홍길동] 변경관리요청서 LIMS_20250814_1 시스템 구조 개선.docx"
```

### Testing Strategy
- **Template Validation**: SHA-256 hash verification ensures template integrity
- **Parser Accuracy**: Fixture-based HTML parsing validation  
- **API Integration**: FastAPI TestClient with async support
- **Cross-Platform**: Path handling and filename sanitization tests
- **Security**: Path traversal attack prevention tests

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

## Performance and Quality Standards

- **Webservice API**: <200ms response time, <1s WebSocket connection
- **CLI**: <30s repository analysis, <5s URL protocol processing  
- **AutoDoc Service**: <1s HTML parsing, <3s Word generation, <2s Excel generation
- **Test Coverage**: Webservice ≥80% unit + ≥70% integration, CLI ≥85% overall, AutoDoc Service ≥85% overall
- **Build Time**: Complete monorepo build <10 minutes

## Critical Configuration Files

- **Webservice Config**: `webservice/config.json` (based on `webservice/config.example.json`)
  - Ollama model settings (`qwen3:8b`), RAG system configuration, offline embedding paths
- **CLI Config**: Hierarchical loading from current directory, project root, then defaults
- **AutoDoc Service Config**: `autodoc_service/requirements.txt` for dependencies
  - Templates directory must contain: `template.docx`, `template.xlsx`, `template_list.xlsx`
- **Monorepo**: Root `pyproject.toml` for unified development tools (black, isort, pytest)

## Legacy Migration Notes

**Webservice Evolution**: Migrated from Streamlit to React+FastAPI
- Web interface moved from `app.py` (Streamlit) to React SPA
- Real-time updates via WebSocket instead of Streamlit rerun  
- Enhanced testing with E2E coverage using Playwright
- Improved file management and download system with Korean filename support