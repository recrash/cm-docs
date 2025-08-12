# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Monorepo Architecture

This is a Git subtree-based monorepo combining two independent projects:

- **backend/**: TestscenarioMaker web service (React + FastAPI + Pseudo-MSA)
- **cli/**: TestscenarioMaker-CLI tool (Python CLI with cross-platform builds)

Each subproject maintains independent development cycles, CI/CD pipelines, and deployment strategies while sharing unified issue tracking and development environment.

### Git Subtree Management
```bash
# Update from upstream repositories
git subtree pull --prefix=backend https://github.com/recrash/TestscenarioMaker.git main --squash
git subtree pull --prefix=cli https://github.com/recrash/TestscenarioMaker-CLI.git main --squash

# Push changes back to upstream
git subtree push --prefix=backend https://github.com/recrash/TestscenarioMaker.git main
git subtree push --prefix=cli https://github.com/recrash/TestscenarioMaker-CLI.git main
```

## Development Commands

### Backend Development (React + FastAPI)
```bash
cd backend

# Environment setup
pip install -r requirements.txt
npm install
export PYTHONPATH=$(pwd):$PYTHONPATH

# Server management
cd backend && python -m uvicorn main:app --reload --port 8000  # Backend API
npm run dev  # Frontend (port 3000)

# Testing (E2E testing is MANDATORY for functionality verification)
npm run test:all        # Complete test suite
npm run test:e2e        # Playwright E2E tests
npm run test:api        # pytest API tests
npm run test            # Jest frontend tests

# Single test execution
pytest tests/api/test_scenario_api.py -v
pytest tests/unit/test_git_analyzer.py::test_function_name -v
```

### CLI Development (Python CLI)
```bash
cd cli

# Development setup
pip install -e .
pip install -r requirements-dev.txt

# Testing
pytest --cov=ts_cli --cov-report=html
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests
pytest -m e2e           # End-to-End tests

# Building (cross-platform)
python scripts/build.py
python scripts/create_dmg.py         # macOS DMG + helper app
makensis scripts/setup_win.nsi       # Windows installer
```

### Monorepo-wide Quality Control
```bash
# Code formatting (from project root)
black backend/src backend/backend cli/src cli/tests
isort backend/src backend/backend cli/src cli/tests

# Linting
flake8 backend/src backend/backend cli/src cli/tests

# Type checking
mypy backend/src cli/src
```

## Architecture Overview

### Backend: Pseudo-MSA Web Service
**Tech Stack**: React 18 + TypeScript + Material-UI + Vite (frontend), FastAPI + Python (backend)

**Core Architecture Patterns**:
- **Legacy Core Modules** (`backend/src/`): Original analysis logic (git_analyzer, llm_handler, excel_writer, vector_db)
- **FastAPI Routers** (`backend/backend/routers/`): Domain-based API endpoints (scenario, feedback, rag, files)
- **React SPA** (`backend/frontend/`): Components with WebSocket real-time updates
- **RAG System**: ChromaDB + ko-sroberta-multitask for Korean document retrieval

**Critical Dependencies**:
- **AI/LLM**: Ollama integration (qwen3:8b model with fallback)
- **Vector DB**: ChromaDB for RAG system with offline embedding support
- **Real-time**: WebSocket progress updates for scenario generation
- **Storage**: SQLite (feedback data) + Excel templates (output)

**WebSocket Integration**: Scenario generation uses WebSocket (`/api/scenario/generate-ws`) with progress updates: 10% → 20% → 30% → 80% → 90% → 100%, each with 1-second delays for UX visibility.

### CLI: Cross-Platform Repository Analysis Tool
**Tech Stack**: Python 3.8+ + Click + Rich + httpx + PyInstaller

**Architecture Patterns**:
- **Strategy Pattern**: VCS support through `RepositoryAnalyzer` abstract base (currently Git-only)
- **URL Protocol Integration**: `testscenariomaker://` browser integration with platform-specific handlers
- **macOS Helper App System**: AppleScript-based helper bypasses browser sandbox restrictions

**Cross-Platform Build System**:
- **PyInstaller**: Single executable generation
- **Windows**: NSIS installer with URL protocol registration
- **macOS**: DMG + dedicated helper app for browser integration
- **Path Handling**: Critical use of `pathlib.Path` with string conversion for subprocess calls

## Development Guidelines

### Backend-Specific Requirements
- **PYTHONPATH Setup**: `export PYTHONPATH=$(pwd):$PYTHONPATH` required for src/ module imports
- **E2E Testing Mandatory**: Always use Playwright E2E tests when verifying functionality
- **WebSocket Testing**: Scenario generation requires ~60 second wait time for completion
- **Cross-Platform Paths**: Use relative paths only - project must build on Windows
- **Korean Language**: All user-facing content must be in Korean

### CLI-Specific Requirements
- **Path Management**: Always use `pathlib.Path`, convert to string for subprocess `cwd` parameter
- **URL Protocol Testing**: Use `test_url_protocol.html` for browser integration testing
- **Helper App Testing** (macOS): Use `python scripts/test_helper_app.py` for comprehensive validation
- **Cross-Platform Compatibility**: Test on Windows, macOS, Linux before release

### Monorepo Development Workflow
1. **Subproject Focus**: Work within specific subproject directories
2. **Independent Testing**: Each subproject has its own test suite and quality gates
3. **Commit Conventions**: Use `[backend]` or `[cli]` prefixes in commit messages
4. **Quality Gates**: Both projects require passing tests before merge
5. **Korean Documentation**: Technical documentation includes Korean user-facing content

## Performance and Quality Standards

- **Backend API**: <200ms response time, <1s WebSocket connection
- **CLI**: <30s repository analysis, <5s URL protocol processing
- **Test Coverage**: Backend ≥80% unit + ≥70% integration, CLI ≥85% overall
- **Build Time**: Complete monorepo build <10 minutes

## Critical Configuration Files

- **Backend Config**: `backend/config.json` (based on config.example.json)
  - Ollama model settings, RAG system, offline embedding paths
- **CLI Config**: Hierarchical loading from current dir, project root, defaults
- **Monorepo**: Root `pyproject.toml` for unified development tools

## Legacy Migration Notes

Backend evolved from Streamlit to React+FastAPI. Key differences:
- Web interface moved from `app.py` to React SPA
- Real-time updates via WebSocket instead of Streamlit rerun
- Enhanced testing with E2E coverage
- Improved file management and download system