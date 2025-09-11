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
export PYTHONPATH=$(pwd):$PYTHONPATH  # Required for app/ modules

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
**Production Deployment Architecture**:
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

# Development fallback (automatically used if environment variables are not set)
# webservice/data/    - webservice development default
# autodoc_service/data/  - autodoc_service development default
```

**Data Directory Structure**:
```
data/
├── logs/         # Log files (environment variable based)
├── models/       # AI embedding models (webservice only)
├── documents/    # Generated document output
├── templates/    # Template files (environment variable based)
├── outputs/      # Excel output (webservice only)
└── db/           # Vector DB (webservice only)
```

## Webservice Development

### Technology Stack
- **Frontend**: React 18 + TypeScript + Material-UI + Vite
- **Backend**: FastAPI + Python with Pseudo-MSA architecture
- **AI/LLM**: Ollama integration (qwen3:8b model)
- **Vector DB**: ChromaDB for RAG system
- **Testing**: Vitest + Playwright (E2E) + pytest

### ChromaDB Dependency Management
**Constraint file is mandatory**:
```bash
pip install -r requirements.txt -c pip.constraints.txt  # ✅ Correct method
```

### Development Commands
```bash
# Environment setup
cd webservice && source .venv/bin/activate
export PYTHONPATH=$(pwd):$PYTHONPATH  # Required for app.core modules

# Server management  
cd webservice && python -m uvicorn app.main:app --reload --port 8000
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
**Unified app structure** (`app/`):
- **Main Application** (`app/main.py`): FastAPI application entry point with lifespan manager
- **Core modules** (`app/core/`): Refactored analysis logic (config_loader, git_analyzer, excel_writer, llm_handler)
- **API Layer** (`app/api/`): 
  - **Routers** (`app/api/routers/`): Domain-based API endpoints
  - **Models** (`app/api/models/`): Pydantic data models
- **Service Layer** (`app/services/`): Business logic layer

**API Endpoints** (prefix: `/api/webservice`):
- `/scenario` - v1 scenario generation (legacy)
- `/v2/scenario` - v2 scenario generation (CLI integration)  
- `/v2/ws/progress/{client_id}` - WebSocket progress updates
- `/rag` - RAG system management
- `/feedback` - User feedback collection
- `/files` - File management operations
- `/health` - Health check with RAG status

**Frontend Architecture**:
- **React SPA** (`frontend/`): Material-UI components with real-time WebSocket updates
- **RAG System**: ChromaDB + ko-sroberta-multitask embedding model
- **V2 API Architecture**: CLI-focused endpoints with WebSocket-based progress tracking

### Critical WebSocket Integration
- **V1 WebSocket**: `/api/webservice/scenario/generate-ws` (legacy web interface)
- **V2 WebSocket**: `/api/webservice/v2/ws/progress/{client_id}` (CLI integration)
- Progress: 10% → 20% → 30% → 80% → 90% → 100%
- Test requires ~60 second wait time
- V2 uses structured message format with status enums (analyzing_git, generating_scenarios, etc.)

### JSON Parsing & Error Handling
**LLM Response Format Support**:
- Primary: `<json>...</json>` XML-style tags (as specified in prompt)
- Fallback: ````json ... ``` markdown code blocks (actual LLM behavior)
- Both formats supported via dual regex patterns in `scenario_v2.py`

**Frontend Safety Patterns**:
- All text processing functions handle null/undefined values
- `formatText()` function includes defensive null checks
- Test case field rendering protected against missing data

### Phase 2 Document Generation Pipeline
**AutoDoc Service Integration**:
- `AutoDocClient` in `app/services/autodoc_client.py` handles document generation
- `transform_metadata_to_enhanced_request()` function converts webservice metadata to autodoc_service format
- Supports API response structure detection: `{'success': true, 'data': {...}}` format
- Enhanced request format includes both `raw_data` and `change_request` fields

**Pipeline Flow**:
```
HTML parsing → webservice metadata → AutoDocClient transformation → autodoc_service → document generation
```

### Webservice-Specific Guidelines
- **Do not delete existing functionality unless explicitly instructed**
- When modifying frontend code, check ESLint definitions and verify TypeScript compilation after changes
- **E2E testing mandatory** for functionality verification
- **Korean Language**: All user-facing content in Korean
- Use `pathlib.Path` and relative paths for cross-platform compatibility

### Configuration
```bash
webservice/config.json  # Main config (based on config.example.json)
export PYTHONPATH=$(pwd):$PYTHONPATH  # Required for app/ imports

# Production environment variables (optional, fallback to data/ subdirectories)
export WEBSERVICE_DATA_PATH="/path/to/webservice/data"  # Production only
export AUTODOC_DATA_PATH="/path/to/autodoc/data"        # Production only
```

### Nginx-based Frontend Deployment
- Production environment: nginx serving on port 80
- Development environment: Vite dev server (port 3000)
- Jenkins pipeline deploys `dist/` artifacts to `C:\nginx\html`

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

### CLI Commands & VCS Support
- `ts-cli analyze`: Main analysis with branch comparison
- `ts-cli info <path>`: Show repository information
- `ts-cli config-show`: Display configuration
- `ts-cli version`: Version information

**VCS Support**:
- **Git repositories**: Full support with branch comparison and commit analysis
- **SVN repositories**: Full support with revision analysis and change detection
- **Auto-detection**: CLI automatically detects repository type (Git vs SVN)
- **Cross-platform paths**: Uses `pathlib.Path` for Windows/macOS/Linux compatibility

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
- `/create-cm-word-enhanced`: Enhanced Word generation (12-field mapping)
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
**Unified multi-branch pipeline** (`Jenkinsfile`):
- Change detection via Git diff
- Parallel service deployment
- Automatic rollback on failure

**Service Pipelines**:
- `webservice/Jenkinsfile.backend`: API testing → NSSM deployment (main/develop only)
- `webservice/Jenkinsfile.frontend`: Branch-specific build strategy (main/develop → production deployment, feature/hotfix → testing only)
- `autodoc_service/Jenkinsfile`: Template validation → NSSM deployment
- `cli/Jenkinsfile`: Windows environment optimized pipeline
  - UTF-8 encoding environment setup (`PYTHONIOENCODING`, `LANG`)
  - Test failure tolerance (`returnStatus: true`)
  - Automatic coverage report generation (htmlcov)
  - NSIS installer build and automatic path detection
  - Wheelhouse-based offline dependency installation support

**Branch-specific deployment strategy**:
- **main/develop**: `/` root path build → `C:\nginx\html` production deployment
- **feature/hotfix**: `/tests/${BRANCH_NAME}/` sub-path build → deployment skip (testing only)

### Closed Network Dependency Management System
**Complete offline build support**:
- **Python**: .whl files collected in `wheelhouse/` folder (`download-all-dependencies.sh/ps1`)
- **Node.js**: npm packages collected in `npm-cache/` folder (newly added)
- **deploy_test_env.ps1**: npm cache priority usage (`--prefer-offline`)

**Dependency collection scripts**:
```bash
# Linux/macOS
./download-all-dependencies.sh  # Python + npm dependency collection

# Windows  
.\Download-All-Dependencies.ps1  # Python + npm dependency collection
```

### Development Server
- **Server**: `34.64.173.97` (GCP VM)
- **Ports**: 8000 (Backend), 8001 (AutoDoc), 80 (Frontend)

## Quality Standards

### Logging System Guidelines
**No Unicode and Emoji usage** (Windows compatibility):
```python
# ❌ Wrong example
logger.info("🚀 Service starting...")

# ✅ Correct example
logger.info("Service starting...")
```

### Pseudo MSA Development Principles
- **Mandatory logging**: Log recording required for all API endpoints
- **Mandatory testing**: Test code required when adding/changing functionality
- **Stability priority**: Ensuring maintainability through logging and testing

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

### Path Management
**Production Environment Variables**:
- `WEBSERVICE_DATA_PATH`: webservice data root path
- `AUTODOC_DATA_PATH`: autodoc_service data root path

**Development Fallback** (when environment variables are not set):
- webservice: `webservice/data/`
- autodoc_service: `autodoc_service/data/`

**Path Functions** (automatic directory creation):
- `get_data_root()`: Environment variable-based data root
- `get_logs_dir()`, `get_templates_dir()`, `get_documents_dir()`
- `get_models_dir()`, `get_outputs_dir()`, `get_vector_db_dir()` (webservice only)

## Template System Architecture

- **Webservice**: Coordinate-based Excel mapping
- **AutoDoc**: Label-based Word mapping (more resilient)
- **Font Consistency**: 맑은 고딕 enforced across all documents

## Key Debugging Patterns

### Webservice Startup Issues
- **RAG System Failures**: Check `startup_rag_system()` in app/main.py:31
- **Module Import Errors**: Verify `PYTHONPATH=$(pwd):$PYTHONPATH` for app.core modules
- **WebSocket Connection Issues**: Check v2 progress endpoints vs legacy endpoints
- **Config Loading**: Use `test_config_paths.py` to debug environment variable paths

### Service Communication
- **Port Conflicts**: Webservice (8000), AutoDoc (8001), Frontend (80)
- **NSSM Service Status**: `nssm status webservice`, `nssm status autodoc_service`
- **Health Endpoints**: `/api/webservice/health` (webservice), `/health` (autodoc_service)
- **CORS Issues**: Check FastAPI middleware settings for React dev server

### Testing Patterns
- **E2E Test Failures**: Often indicate WebSocket timing issues (~60s scenarios)
- **ChromaDB Lock Issues**: Clear vector database: `rm -rf webservice/vector_db_data/`  
- **Dependency Conflicts**: Always use `pip install -r requirements.txt -c pip.constraints.txt`

### CLI Integration Issues
- **V2 API Mismatch**: Check client_id parameter consistency between CLI and WebSocket
- **URL Protocol Handler**: macOS requires helper app for `testscenariomaker://` URLs
- **Cross-platform Paths**: Always use `pathlib.Path`, convert to string for subprocess
- **Jenkins Build Failures**: 
  - Check UTF-8 encoding settings in Jenkinsfile
  - Verify NSIS installer path (scripts/ vs dist/)
  - Ensure Lightweight checkout is disabled for branch switching
  - Check Python version compatibility (3.13 required)

### SVN-Specific Debugging Patterns
- **JSON Parsing Issues**: LLM responses may use ````json` blocks instead of `<json>` tags
- **Repository Detection**: SVN repositories detected via `.svn` directory presence
- **Path Handling**: SVN working copies require absolute paths for analysis
- **Revision Analysis**: SVN uses revision numbers instead of commit hashes
- **Frontend Error Recovery**: Null/undefined values in test case fields cause JavaScript errors

### Phase 2 Pipeline Debugging
- **Data Transformation Issues**: Check `transform_metadata_to_enhanced_request()` function in AutoDocClient
- **API Response Structure**: Verify `raw_data` contains `{'success': true, 'data': {...}}` format
- **Document Generation**: Check autodoc_service logs for template mapping errors
- **File Naming**: Ensure actual HTML parsing data (e.g., "이대경") is used instead of fallback metadata (e.g., "테스터")

## VCS Repository Support

### Supported Version Control Systems
- **Git**: Full support with branch comparison, commit history analysis, and diff generation
- **SVN**: Full support with revision analysis, change detection, and path handling
- **Auto-Detection**: Repository type automatically detected via `.git` or `.svn` directories

### VCS-Specific Implementation Details
**Git Integration** (`git_analyzer.py`):
- Uses GitPython library for repository operations
- Supports branch comparison (default: `origin/develop` → `HEAD`)
- Extracts commit messages and code diffs between commits
- Handles merge base detection for accurate comparisons

**SVN Integration** (`cli/src/ts_cli/vcs/svn_analyzer.py`):
- Uses subprocess calls to `svn` command-line client
- Analyzes working copy changes and committed revisions
- Supports path-based change detection and diff generation
- Handles SVN-specific revision numbering system

### Cross-Platform Path Considerations
- Always use `pathlib.Path` for cross-platform compatibility
- Convert `Path` objects to strings when passing to subprocess calls
- SVN working copies require absolute paths for reliable analysis
- Git repositories work with both relative and absolute paths

## Notes

- **Python Versions**: 3.13 default, 3.12 for AutoDoc (document stability)
- **VCS Support**: Both Git and SVN repositories fully supported with auto-detection
- **Path Management**: Always use pathlib.Path, convert to string for subprocess
- **Korean Content**: All user-facing text in Korean
- **E2E Testing**: Mandatory for webservice functionality verification
- **NSSM Services**: Windows service management for production deployment
- **Unicode Logging**: No emojis in logs for Windows compatibility
- **JSON Parsing**: Dual format support for LLM responses (XML tags + markdown blocks)
- **MCP Server Usage**: Use Context7 MCP for official documentation and latest documentation when developing
- After receiving tool results, carefully reflect on their quality and decide on the optimal next steps before proceeding. Use thinking to plan and iterate based on this new information, then take the best next action.
- For maximum efficiency, whenever you need to perform multiple independent tasks, call all relevant tools simultaneously rather than sequentially.
- When creating temporary new files, scripts, or helper files for iteration, clean up by removing these files at the end of your work.
- Write high-quality, general-purpose solutions. Implement solutions that work correctly for all valid inputs, not just test cases. 
  Do not hardcode values or create solutions that only work for specific test inputs. Instead, implement real logic that solves the problem generally.
  Focus on understanding the problem requirements and implementing the correct algorithm. Tests are meant to verify correctness, not define the solution. Provide principled implementations that follow best practices and software design principles.
- If a task is unreasonable, infeasible, or some tests are incorrect, let me know. Solutions should be robust, maintainable, and scalable.