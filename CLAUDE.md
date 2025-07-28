# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TestscenarioMaker is an AI-powered tool that analyzes Git repository changes and automatically generates Korean test scenarios in Excel format. It uses Ollama's LLM (qwen3:8b by default) to process Git commit messages and code diffs, then outputs structured test scenarios.

## Development Commands

### Running the Application
```bash
# Streamlit web interface (recommended)
streamlit run app.py

# Command-line interface
python main.py
```

### Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Ollama setup (required for LLM functionality)
ollama pull qwen3:8b
ollama serve
```

### Testing
No automated test framework is configured. Manual testing is done by running the application and verifying Excel output generation.

## Architecture

### Core Modules (src/)
- **git_analyzer.py**: Extracts Git commit messages and code diffs using GitPython
- **llm_handler.py**: Handles Ollama API communication with configurable timeouts
- **excel_writer.py**: Processes LLM JSON responses and writes to Excel templates using openpyxl
- **prompt_loader.py**: Manages LLM prompts and RAG integration with singleton pattern
- **config_loader.py**: Loads configuration from config.json
- **document_parser.py**: Parses Word documents (변경관리요청서) using python-docx

### Vector DB & RAG (src/vector_db/)
- **chroma_manager.py**: ChromaDB vector database management with Korean embeddings
- **document_chunker.py**: Text chunking for Git analysis, documents, and test scenarios
- **rag_manager.py**: RAG system integration managing vector storage and context retrieval

### User Interfaces
- **app.py**: Streamlit web interface with file upload/download capabilities
- **main.py**: Command-line interface for batch processing

### Configuration
- **config.json**: Contains repo_path, model_name, timeout, and RAG settings
- **prompts/final_prompt.txt**: LLM prompt template for test scenario generation

### Data Flow
1. Git analysis extracts commit messages and diffs
2. **RAG Integration**: Git analysis is chunked and stored in ChromaDB for future reference
3. **Context Retrieval**: Similar past analyses are retrieved for enhanced prompting
4. Prompt template is populated with Git analysis and relevant context
5. Ollama LLM generates structured JSON response with Korean test scenarios
6. Excel writer maps JSON to template.xlsx format
7. Output saved to outputs/ directory with timestamp

### RAG System
- **Vector Storage**: ChromaDB with Korean sentence-transformers (jhgan/ko-sroberta-multitask)
- **Document Types**: Git analysis results, test scenarios, and general documents
- **Chunking Strategy**: 1000 chars with 200 char overlap, section-aware for Git data
- **Context Enhancement**: Top-k similarity search provides relevant historical context

### Output Format
Generated Excel files contain:
- Scenario Description (전체 테스트 목적)
- Test Scenario Name (대표 제목)
- Test Cases with ID, 절차, 사전조건, 데이터, 예상결과, 종류 fields

## Important Notes

- All LLM responses must be in Korean language
- Excel template (templates/template.xlsx) defines output structure
- Ollama server must be running on localhost:11434
- Git repository path is configurable via config.json or UI input
- Default model is qwen3:8b but can be changed in configuration
- Timeout is configurable (default 600 seconds) for LLM processing
- **RAG System**: ChromaDB and sentence-transformers dependencies required
- **Vector DB**: Stored in vector_db_data/ directory, persists across sessions
- **RAG can be disabled** in config.json by setting rag.enabled to false