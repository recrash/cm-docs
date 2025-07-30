# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TestscenarioMaker is an AI-powered tool that analyzes Git repository changes and automatically generates Korean test scenarios in Excel format. It uses Ollama's LLM (qwen3:8b by default) to process Git commit messages and code diffs, then outputs structured test scenarios using RAG (Retrieval-Augmented Generation) for enhanced context and a feedback system for continuous improvement.

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

### Database Management
```bash
# View feedback database content (SQLite)
sqlite3 feedback.db ".tables"
sqlite3 feedback.db "SELECT * FROM scenario_feedback LIMIT 5;"

# Clear vector database (if needed)
# This is handled through the Streamlit UI RAG management section

# Feedback data management (through UI)
# - Complete reset: All feedback data with automatic backup
# - Category-based reset: good/bad/neutral feedback only
# - Backups saved to backups/ folder with timestamp
```

## Architecture

### Core Modules (src/)
- **git_analyzer.py**: Extracts Git commit messages and code diffs using GitPython
- **llm_handler.py**: Handles Ollama API communication with configurable timeouts
- **excel_writer.py**: Processes LLM JSON responses and writes to Excel templates using openpyxl
- **prompt_loader.py**: Manages LLM prompts and RAG integration with singleton pattern
- **config_loader.py**: Loads configuration from config.json
- **document_parser.py**: Parses Word documents (변경관리요청서) using python-docx
- **feedback_manager.py**: SQLite-based feedback collection, storage, analysis, and reset system with backup functionality
- **prompt_enhancer.py**: Analyzes user feedback to dynamically improve prompts

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
4. **Prompt Enhancement**: Template is populated with Git analysis, RAG context, and feedback-based improvements
5. **LLM Generation**: Ollama generates structured JSON response with Korean test scenarios
6. **Excel Output**: JSON is mapped to Excel template with proper formatting (includes \n to newline conversion)
7. **File Storage**: Output saved to outputs/ directory with timestamp
8. **Feedback Collection**: Users evaluate scenarios through UI, data stored in SQLite database
9. **Continuous Improvement**: Collected feedback automatically improves future prompt generation

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

### Feedback System Architecture
- **Collection**: Modal-based UI with detailed evaluation forms and individual test case ratings
- **Storage**: SQLite database with structured feedback data including scores, categories, and comments
- **Analysis**: Statistical insights including problem areas, success patterns, and improvement recommendations
- **Enhancement**: Automatic prompt improvement using good/bad examples when sufficient feedback is collected (minimum 3 feedback entries)
- **Reset Functionality**: Complete or category-based feedback data clearing with automatic backup to backups/ folder
- **Session Management**: Streamlit session state manages modal visibility and user interactions
- **Cache Management**: Automatic singleton instance reset after feedback operations to maintain state consistency

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
- Feedback database (feedback.db) stores user evaluations and is used for automatic prompt improvement
- Performance mode can be enabled to limit prompt size and improve LLM response times
- Backup system automatically creates timestamped snapshots in backups/ folder before any feedback data modifications

## Key UI/UX Features

### Streamlit Web Interface (app.py)
- **Two-tab layout**: Scenario generation and feedback analysis dashboard
- **RAG system management**: Document indexing, database clearing, and status monitoring
- **Real-time generation**: Progress indicators with status updates during scenario creation
- **Interactive feedback**: Modal-based evaluation system with detailed scoring options
- **Preview functionality**: Generated scenarios displayed with proper text formatting (newline handling)
- **Session state management**: Maintains application state across user interactions
- **Performance monitoring**: LLM response time and prompt size tracking
- **Feedback management**: Complete data export, selective reset with backup, and category-based analysis

## Technical Implementation Details

### Prompt Engineering Architecture
- **Base template**: Located in prompts/final_prompt.txt with structured JSON output format
- **Dynamic enhancement**: PromptEnhancer class analyzes feedback to inject improvement instructions
- **RAG integration**: Similar historical analyses retrieved via vector similarity search
- **Performance optimization**: Optional prompt size limiting for faster LLM responses
- **Chain of Thought**: LLM uses `<thinking>` tags before generating final `<json>` output

### Session State Management (Streamlit)
Key session variables that control application flow:
- `generated`: Boolean indicating if scenario generation is complete
- `result_json`: Generated scenario data structure
- `final_filename`: Path to created Excel file
- `real_modal_visible`: Controls feedback modal display
- `real_modal_type`: Tracks whether feedback is positive ('like') or negative ('dislike')
- `rag_info`: Cached RAG system status information

### Database Schema (SQLite)
- **scenario_feedback**: Main feedback table with scenario_id, scores, comments, and metadata
- **testcase_feedback**: Individual test case evaluations linked to scenarios
- **Scoring system**: 1-5 scale for overall, usefulness, accuracy, and completeness metrics

### Error Handling Patterns
- RAG system initialization with fallback modes (lazy loading)
- LLM timeout handling with configurable limits
- Excel template validation and error recovery
- Git repository access validation
- Modal state management to prevent UI conflicts

## Development Guidelines

- Avoid hardcoding values - use configuration files
- Follow efficient packaging structure for maintainability
- Use Chain of Thought approach for complex problem solving
- Base code changes on the most recent successful implementation
- Ensure Korean language output for all user-facing content
- When modifying UI components, always test modal interactions and session state transitions
- RAG system changes require testing with both enabled/disabled configurations
- Feedback system modifications should maintain backward compatibility with existing SQLite schema

## Important Development Notes

### Feedback System Management
- Always create automatic backups before any feedback data modifications
- Use `reset_feedback_cache()` after feedback operations to maintain singleton consistency
- Backup files are stored in `backups/` folder with timestamp format `feedback_backup_YYYYMMDD_HHMMSS.json`
- Category-based operations support: 'good', 'bad', 'neutral' classifications

### LLM Integration Architecture
- Default model: qwen3:8b running on Ollama (localhost:11434)
- Chain of Thought pattern: LLM uses `<thinking>` tags before `<json>` output
- Prompt enhancement system activates after collecting 3+ feedback entries
- Performance mode available to limit prompt size for faster responses