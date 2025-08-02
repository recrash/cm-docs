# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TestscenarioMaker is an AI-powered tool that analyzes Git repository changes and automatically generates Korean test scenarios in Excel format. The project has evolved from a Streamlit-based application to a full-stack React + FastAPI architecture with RAG (Retrieval-Augmented Generation) capabilities and a feedback system for continuous improvement.

## Architecture Overview

### Full-Stack Architecture
- **Frontend**: React 18 + TypeScript + Material-UI + Vite
- **Backend**: FastAPI + Python with modular routers
- **AI/LLM**: Ollama integration (qwen3:8b model) 
- **Vector Database**: ChromaDB for RAG system
- **Storage**: SQLite for feedback data, Excel files for output
- **Testing**: Jest + Playwright (E2E) + pytest (backend)

### Key Components
- **Legacy `src/` modules**: Core analysis logic (git_analyzer, llm_handler, excel_writer, etc.)
- **Backend API**: FastAPI routers for scenario generation, feedback, RAG, and file management
- **Frontend SPA**: React components with real-time WebSocket updates
- **RAG System**: Vector database integration for context-enhanced generation

## Development Commands

### Server Management
```bash
# Backend (Port 8000) - Must be run from backend directory
cd backend && python -m uvicorn main:app --reload --port 8000

# Frontend (Port 3000) - Run from project root
npm run dev

# Server shutdown
./stop-dev.sh

# DO NOT use ./start-dev.sh for starting servers
```

### Testing
```bash
# Frontend unit tests
npm run test
npm run test:watch
npm run test:coverage

# E2E tests (MANDATORY for testing functionality)
npm run test:e2e
npm run test:e2e:ui

# Backend API tests
npm run test:api
# OR: pytest tests/api/

# Single test file
pytest tests/api/test_scenario_api.py -v
pytest tests/unit/test_git_analyzer.py::test_function_name -v

# All tests
npm run test:all
```

### Building and Environment Setup
```bash
# Frontend build
npm run build

# Python module imports setup (required for src/ modules)
export PYTHONPATH=$(pwd):$PYTHONPATH

# Backend tests with coverage
pytest --cov=src --cov-report=html

# Download Korean embedding model (first-time setup)
python scripts/download_embedding_model.py
```

## Critical Development Guidelines

### Fundamental Principles
- **명확한 명령이나 지시가 있기 전까지는 기존에 있는 기능을 삭제하지 말아라** (Never delete existing functionality without explicit instructions)
- **Cross-platform compatibility**: Use relative paths only - this project must build on Windows
- **E2E testing mandatory**: Always perform E2E tests using Playwright MCP when testing functionality

### Path Management
- Use `pathlib.Path` and relative paths for cross-platform compatibility
- Never use absolute paths - the project builds on Windows
- For backend modules: `Path(__file__).parent.parent` pattern for project root references
- Module imports require PYTHONPATH setup: `sys.path.append(os.path.join(os.path.dirname(__file__), '..'))`

### WebSocket Integration
- Scenario generation uses WebSocket for real-time progress updates
- Frontend connects to `ws://localhost:8000/api/scenario/generate-ws`
- Progress updates show: 10% → 20% → 30% → 80% → 90% → 100%
- Each step has 1-second delay for user visibility
- Handle connection states and progress messages appropriately

### Critical WebSocket Implementation Notes
- Backend uses `progress.model_dump()` + `json.dumps()` for proper serialization
- Frontend WebSocket URL adapts to environment (localhost:8000 for development)
- Connection manager prevents duplicate disconnect errors
- Progress delays ensure user can see each step during generation

## Code Architecture Details

### Frontend Structure (React + TypeScript)
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

### Backend Structure (FastAPI)
```
backend/
├── main.py              # FastAPI app initialization
├── routers/             # API endpoint modules
│   ├── scenario.py      # Generation endpoints + WebSocket
│   ├── feedback.py      # Feedback collection & analysis
│   ├── rag.py          # RAG system management
│   └── files.py        # File upload/download/validation
└── models/             # Pydantic response models
```

### Legacy Core Modules (src/)
The original core logic remains in `src/` and is imported by backend routers:
- **git_analyzer.py**: Git diff extraction and analysis using GitPython
- **llm_handler.py**: Ollama LLM integration (qwen3:1.7b model)
- **excel_writer.py**: Template-based Excel generation (cross-platform paths)
- **feedback_manager.py**: SQLite-based feedback storage with automatic backups
- **vector_db/**: RAG system with ChromaDB integration
  - **rag_manager.py**: Main RAG orchestration class
  - **chroma_manager.py**: ChromaDB vector database operations
  - **document_chunker.py**: Text chunking for vector storage
  - **document_indexer.py**: Document processing and indexing

### API Integration Patterns

#### Scenario Generation Flow
1. Frontend validates Git repo path via `/api/files/validate/repo-path`
2. WebSocket connection to `/api/scenario/generate-ws`
3. Backend orchestrates: Git analysis → RAG context → LLM generation → Excel output
4. Real-time progress updates sent via WebSocket
5. Final result includes metadata and Excel filename

#### File Download System
- Excel files generated in `outputs/` directory
- Download via `/api/files/download/excel/{filename}`
- Frontend uses `filesApi.downloadExcelFile()` with proper encoding
- Supports Korean filenames with UTF-8 encoding

#### RAG System Integration
- Document indexing via `/api/rag/index`
- Status monitoring via `/api/rag/status`
- Context retrieval integrated into scenario generation prompt
- Uses ko-sroberta-multitask for Korean text embeddings
- Auto-initializes on backend startup if `rag.enabled: true` in config.json
- Supports DOCX, TXT, PDF document formats with chunk_size=1000, chunk_overlap=200

### Testing Architecture

#### E2E Testing (Playwright - Required)
- Use Playwright MCP for all E2E testing
- Test complete user workflows including file downloads
- Verify WebSocket real-time updates
- Cross-browser compatibility testing

#### API Testing (pytest)
- Located in `tests/api/`
- Covers all FastAPI endpoints
- Mock external dependencies (Ollama, file system)
- Database isolation with test fixtures

#### Development Guidelines
- **CRITICAL**: Only perform the functionality requested by the user. NEVER arbitrarily change variable names or delete existing functionality without explicit request
- **ALWAYS**: Use test code to verify implemented results and functionality
- Avoid hardcoding values - use configuration files
- Follow efficient packaging structure for maintainability
- Use Chain of Thought approach for complex problem solving
- Base code changes on the most recent successful implementation
- Ensure Korean language output for all user-facing content
- When modifying UI components, always test modal interactions and session state transitions
- RAG system changes require testing with both enabled/disabled configurations
- Feedback system modifications should maintain backward compatibility with existing SQLite schema

#### Frontend Testing (Jest)
- React component testing with Testing Library
- API service mocking with MSW
- WebSocket connection testing

## Common Development Patterns

### Error Handling
- Backend: FastAPI HTTPException with detailed messages
- Frontend: Try-catch with user-friendly alerts
- WebSocket: Dedicated error callbacks with reconnection logic

### State Management
- React state for UI components
- WebSocket state for real-time updates
- API caching for configuration and status data

### File Processing
- Always check file existence before operations
- Use proper MIME types for Excel downloads
- Handle Korean filenames with URL encoding
- Cross-platform path handling with pathlib

### Database Operations
- SQLite for feedback data with backup system
- ChromaDB for vector storage with proper cleanup
- Transaction-based operations for data integrity

## Migration Notes

This project migrated from Streamlit to React+FastAPI. Key changes:
- Web interface moved from `app.py` (Streamlit) to React SPA
- API endpoints centralized in FastAPI backend
- Real-time updates via WebSocket instead of Streamlit rerun
- Improved testing architecture with E2E coverage
- Enhanced file management and download system

## Common Issues and Solutions

### Frontend Development
- **Node.js Deprecation Warning**: Fixed with `NODE_OPTIONS="--no-deprecation"` in npm scripts
- **WebSocket Progress Stuck at 0%**: Fixed with proper serialization and progress delays
- **Port Configuration**: Frontend runs on port 3000, backend on port 8000

### WebSocket Troubleshooting
- **Progress Updates Not Visible**: Each step has 1-second delay for user visibility
- **JSON Serialization Issues**: Use `progress.model_dump()` instead of `progress.json()`
- **Connection Manager Errors**: Check for duplicate disconnect calls

### Cross-Platform Compatibility
- Always use relative paths with `pathlib.Path`
- Never use absolute paths - project must build on Windows
- Use proper path separators and encoding for Korean filenames

### Import Issues and Solutions
- **Typing imports**: Use `from typing import List, Tuple, Optional` (not `from typing import Tuple` alone)
- **Module path setup**: Backend uses `sys.path.append(os.path.join(os.path.dirname(__file__), '..'))`
- **PYTHONPATH environment**: Set `PYTHONPATH=$(pwd):$PYTHONPATH` for direct module testing
- **Config loading**: RAG system requires config.json with proper `rag.enabled` flag