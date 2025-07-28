# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TestscenarioMaker is an AI-powered tool that analyzes Git repository changes and automatically generates Korean test scenarios in Excel format. It uses Ollama's LLM (qwen3:8b by default) to process Git commit messages and code diffs, then outputs structured test scenarios using RAG (Retrieval-Augmented Generation) for enhanced context.

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

### Vector DB & RAG System (src/vector_db/)
- **chroma_manager.py**: ChromaDB vector database management with Korean embeddings
- **document_chunker.py**: Text chunking for Git analysis, documents, and test scenarios
- **rag_manager.py**: RAG system integration managing vector storage and context retrieval
- **document_indexer.py**: Batch processes and indexes documents into ChromaDB
- **document_reader.py**: Extracts text content from various document formats (DOCX, TXT, PDF)

### User Interfaces  
- **app.py**: Streamlit web interface with file upload/download capabilities
- **main.py**: Command-line interface for batch processing

### Configuration
- **config.json**: Contains repo_path, model_name, timeout, and RAG settings
- **prompts/final_prompt.txt**: LLM prompt template for test scenario generation

## Data Flow

1. **Git Analysis**: Extracts commit messages and code diffs from specified repository
2. **RAG Integration**: Git analysis is chunked and stored in ChromaDB for future reference
3. **Context Retrieval**: Similar past analyses are retrieved using vector similarity search
4. **Prompt Enhancement**: Template is populated with Git analysis and relevant historical context
5. **LLM Generation**: Ollama generates structured JSON response with Korean test scenarios
6. **Excel Output**: JSON is mapped to Excel template with proper formatting
7. **File Storage**: Output saved to outputs/ directory with timestamp

## RAG System Details

### Vector Storage
- **Database**: ChromaDB with persistent storage
- **Embedding Model**: Korean sentence-transformers (jhgan/ko-sroberta-multitask)
- **Storage Location**: vector_db_data/ directory
- **Document Types**: Git analysis results, test scenarios, and general documents

### Text Processing
- **Chunking Strategy**: 1000 characters with 200 character overlap
- **Section Awareness**: Git data is chunked by meaningful sections (commits, files)
- **Context Enhancement**: Top-k similarity search provides relevant historical context

### Excel Output Processing
The excel_writer.py module handles newline formatting by converting `\\n` escape sequences to actual newlines for proper display in Excel cells. This affects all text fields including 절차, 사전조건, 데이터, and 예상결과.

## Output Format

Generated Excel files contain:
- **Scenario Description**: 전체 테스트 목적 (overall test purpose)
- **Test Scenario Name**: 대표 제목 (representative title)
- **Test Cases**: Structured data with ID, 절차, 사전조건, 데이터, 예상결과, 종류 fields

## Important Configuration Notes

- All LLM responses are generated in Korean language
- Excel template (templates/template.xlsx) defines the output structure
- Ollama server must be running on localhost:11434
- Git repository path is configurable via config.json or UI input
- Default model is qwen3:8b but can be changed in configuration
- Timeout is configurable (default 600 seconds) for LLM processing
- RAG system requires ChromaDB and sentence-transformers dependencies
- Vector DB persists across sessions in vector_db_data/ directory
- RAG can be disabled in config.json by setting rag.enabled to false
- Document processing supports DOCX, TXT, and PDF files in the documents/ folder

## Development Guidelines

- Avoid hardcoding values - use configuration files
- Follow efficient packaging structure for maintainability
- Use Chain of Thought approach for complex problem solving
- Base code changes on the most recent successful implementation
- Ensure Korean language output for all user-facing content