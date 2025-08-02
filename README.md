# TestscenarioMaker

AI-powered tool that analyzes Git repository changes and automatically generates Korean test scenarios in Excel format.

## 📋 Project Overview

TestscenarioMaker is a full-stack application that analyzes Git repository changes and automatically generates high-quality Korean test scenarios using AI. The project features a modern React frontend, FastAPI backend, and includes RAG (Retrieval-Augmented Generation) capabilities with a feedback system for continuous improvement.

## 🏗️ Architecture

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

## 🎯 Key Features

### 🔍 **AI-Powered Scenario Generation**
- **Git Analysis**: Automatic extraction of commit messages and code diffs
- **LLM Integration**: Ollama-based qwen3:8b model for intelligent generation
- **Excel Output**: Standardized test scenario format with templates
- **Korean Specialization**: Natural Korean language test scenario generation
- **Real-time Updates**: WebSocket-based progress tracking during generation

### 🧠 **RAG (Retrieval-Augmented Generation) System**
- **Vector Database**: ChromaDB for intelligent document search
- **Korean Embeddings**: ko-sroberta-multitask model for accurate similarity search
- **Context Enhancement**: Historical analysis results for improved scenario generation
- **Document Indexing**: Automatic processing of various formats (DOCX, TXT, PDF)
- **Dynamic Context**: Retrieval of relevant historical data during generation

### 📊 **Feedback System**
- **User Evaluation**: 5-point scale rating system for generated scenarios
- **Automatic Improvement**: Feedback-driven prompt optimization
- **Analytics Dashboard**: Statistical analysis and improvement pattern visualization
- **Backup System**: Automatic data backup for data safety
- **Export Capabilities**: JSON and Excel export of feedback data

### 🌐 **Modern Web Interface**
- **React SPA**: Single-page application with Material-UI components
- **Real-time Progress**: WebSocket integration for live generation updates
- **File Management**: Drag-and-drop file upload and download capabilities
- **Responsive Design**: Mobile-friendly interface with adaptive layouts
- **Error Handling**: Comprehensive error handling with user-friendly messages

### 🧪 **Comprehensive Testing**
- **Unit Testing**: Jest-based frontend tests with Testing Library
- **API Testing**: pytest-based backend API testing with mock support
- **E2E Testing**: Playwright-based end-to-end testing across browsers
- **Integration Testing**: Full workflow testing with database isolation

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **Ollama** with qwen3:8b model installed
- **Git** for repository analysis

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd TestscenarioMaker
   ```

2. **Backend Setup**:
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt
   
   # Configure settings
   cp config.example.json config.json
   # Edit config.json with your settings
   ```

3. **Frontend Setup**:
   ```bash
   # Install Node.js dependencies
   npm install
   ```

4. **Download Korean Embedding Model**:
   ```bash
   python scripts/download_embedding_model.py
   ```

### Running the Application

#### Development Mode

1. **Start Backend Server** (Port 8000):
   ```bash
   cd backend
   python -m uvicorn main:app --reload --port 8000
   ```

2. **Start Frontend Server** (Port 3000):
   ```bash
   npm run dev
   ```

3. **Access Application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

#### Production Mode

```bash
# Build frontend
npm run build

# Start production server
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Server Management

```bash
# Stop all servers
./stop-dev.sh
```

**⚠️ Important**: Do not use `./start-dev.sh` - start servers manually as shown above.

## 📁 Project Structure

```
TestscenarioMaker/
├── frontend/src/                    # React frontend
│   ├── components/                  # Reusable UI components
│   │   ├── ScenarioGenerationTab.tsx
│   │   ├── ScenarioResultViewer.tsx
│   │   ├── FeedbackModal.tsx
│   │   ├── RAGSystemPanel.tsx
│   │   └── FeedbackAnalysisTab.tsx
│   ├── services/api.ts              # Axios-based API client
│   ├── types/index.ts               # TypeScript definitions
│   └── utils/websocket.ts           # WebSocket connection handling
├── backend/                         # FastAPI backend
│   ├── main.py                      # FastAPI app initialization
│   ├── routers/                     # API endpoint modules
│   │   ├── scenario.py              # Generation endpoints + WebSocket
│   │   ├── feedback.py              # Feedback collection & analysis
│   │   ├── rag.py                   # RAG system management
│   │   └── files.py                 # File upload/download/validation
│   └── models/                      # Pydantic response models
├── src/                             # Legacy core modules
│   ├── git_analyzer.py              # Git diff extraction and analysis
│   ├── llm_handler.py               # Ollama LLM integration
│   ├── excel_writer.py              # Template-based Excel generation
│   ├── feedback_manager.py          # SQLite-based feedback storage
│   └── vector_db/                   # RAG system with ChromaDB
├── tests/                           # Test suites
│   ├── unit/                        # Unit tests
│   ├── api/                         # API tests
│   ├── e2e/                         # End-to-end tests
│   └── integration/                 # Integration tests
├── templates/                       # Excel templates
├── outputs/                         # Generated Excel files
├── documents/                       # Sample documents for RAG
└── config.json                      # Application configuration
```

## 🧪 Testing

### Running Tests

```bash
# Frontend unit tests
npm run test
npm run test:watch
npm run test:coverage

# E2E tests (MANDATORY for functionality testing)
npm run test:e2e
npm run test:e2e:ui

# Backend API tests
npm run test:api
# OR: pytest tests/api/

# All tests
npm run test:all
```

### Test Coverage
- **Unit Tests**: React components, core business logic
- **API Tests**: All FastAPI endpoints with mock dependencies
- **E2E Tests**: Complete user workflows including file downloads
- **Integration Tests**: Full system workflow with database operations

## ⚙️ Configuration

### config.json
```json
{
    "ollama_base_url": "http://localhost:11434",
    "model_name": "qwen3:8b",
    "timeout_seconds": 600,
    "max_tokens": 4000,
    "temperature": 0.7,
    "rag_enabled": true,
    "feedback_enabled": true
}
```

### Environment Variables
- `NODE_OPTIONS="--no-deprecation"`: Suppress Node.js warnings
- `PYTHONPATH`: Set to project root for module imports

## 🔄 API Integration

### WebSocket Scenario Generation
1. Frontend connects to `ws://localhost:8000/api/scenario/generate-ws`
2. Real-time progress updates: 10% → 20% → 30% → 80% → 90% → 100%
3. Each progress step includes descriptive messages
4. Final result includes metadata and Excel filename

### File Management
- Excel files generated in `outputs/` directory
- Download via `/api/files/download/excel/{filename}`
- Korean filename support with UTF-8 encoding
- Proper MIME type handling for Excel files

### RAG System Integration
- Document indexing via `/api/rag/index`
- Status monitoring via `/api/rag/status`
- Context retrieval integrated into scenario generation
- Korean text processing with specialized embeddings

## 🛠️ Development Guidelines

### Critical Principles
- **Cross-platform compatibility**: Use relative paths only - project must build on Windows
- **E2E testing mandatory**: Always perform E2E tests using Playwright when testing functionality
- **Never delete existing functionality** without explicit instructions
- **Path management**: Use `pathlib.Path` and relative paths

### WebSocket Implementation
- Backend uses `progress.model_dump()` + `json.dumps()` for serialization
- Frontend adapts WebSocket URL to environment
- Connection manager prevents duplicate disconnect errors
- Progress delays ensure user visibility of each step

### Error Handling
- **Backend**: FastAPI HTTPException with detailed messages
- **Frontend**: Try-catch with user-friendly alerts
- **WebSocket**: Dedicated error callbacks with reconnection logic

## 📊 Performance & Monitoring

### Performance Metrics
- **Load Time**: <3s on 3G, <1s on WiFi
- **Bundle Size**: <500KB initial, <2MB total
- **API Response**: <200ms for standard operations
- **Generation Time**: ~30-60 seconds for complete scenarios

### Monitoring
- Real-time WebSocket progress tracking
- Error logging with structured format
- Performance metrics collection
- User feedback analytics

## 🔒 Security

- **Input Validation**: All user inputs validated and sanitized
- **Path Security**: Relative paths only, no directory traversal
- **CORS Configuration**: Proper CORS setup for development/production
- **Error Handling**: No sensitive information in error messages

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with appropriate tests
4. Run all test suites
5. Submit a pull request with description

### Development Workflow
- Use TypeScript for all new frontend code
- Follow existing code patterns and conventions
- Add tests for new functionality
- Update documentation as needed

## 📝 Migration Notes

This project successfully migrated from Streamlit to React+FastAPI architecture:
- ✅ Web interface moved from Streamlit to React SPA
- ✅ API endpoints centralized in FastAPI backend
- ✅ Real-time updates via WebSocket instead of Streamlit rerun
- ✅ Enhanced testing architecture with E2E coverage
- ✅ Improved file management and download system
- ✅ Legacy Streamlit files removed (app.py, main.py, app_streamlit_backup.py)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues
- **WebSocket Connection Failed**: Check backend server is running on port 8000
- **Generation Stuck at 0%**: Verify Ollama is running and model is available
- **File Download Issues**: Check outputs directory permissions
- **Korean Text Issues**: Ensure UTF-8 encoding is properly configured

### Support
For issues and questions, please check the existing documentation or create an issue in the repository.