# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Service Management
```bash
# Start service (recommended - handles dependencies)
python run_autodoc_service.py

# Manual start
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Alternative port if 8000 is busy
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Testing
```bash
# Run all tests with coverage
pytest --cov=app --cov-report=html app/tests/

# Run specific test categories  
pytest -m unit app/tests/       # Unit tests only
pytest -m integration app/tests/  # Integration tests only
pytest -m e2e app/tests/        # End-to-end tests only

# Run single test file
pytest app/tests/test_parser_itsupp.py -v

# Run specific test function
pytest app/tests/test_parser_itsupp.py::test_function_name -v
```

### API Testing
```bash
# Health check
curl http://localhost:8000/health

# Parse HTML file
curl -F "file=@testHTML/규격_확정일자.html" http://localhost:8000/parse-html

# Create Word document (enhanced endpoint with raw_data support)
curl -X POST "http://localhost:8000/create-cm-word-enhanced" \
     -H "Content-Type: application/json" \
     -d '{"change_id": "TEST_001", "system": "TEST", "title": "Test Doc", "requester": "User", "raw_data": {...}}'
```

## Architecture Overview

### Core Design Philosophy
AutoDoc Service is built as an **Office-less document automation system** for air-gapped environments. The architecture prioritizes template resilience, field mapping intelligence, and cross-platform compatibility.

### Key Architectural Patterns

#### 1. Label-Based Template Mapping (Primary System)
- **Location**: `app/services/label_based_word_builder.py`
- **Purpose**: Maps data to Word templates by finding label text instead of relying on fixed cell indices
- **Resilience**: Template structure changes don't break the mapping
- **Special Cases**: Table 2 has custom handling for complex date placement logic

#### 2. Enhanced Payload System
- **Location**: `app/services/word_payload.py` 
- **Purpose**: Transforms raw HTML parsing data into Word-compatible format
- **Intelligence**: 
  - Auto-extracts department from applicant field segments (`홍길동/Manager/IT운영팀/SK AX` → `IT운영팀`)
  - System-specific deployer mapping (extensible via `get_system_deployer()`)
  - Structured content generation for purpose/improvement fields

#### 3. Font Styling System
- **Word**: `app/services/font_styler.py` - Applies 맑은 고딕 to all Word content
- **Excel**: `app/services/excel_font_styler.py` - Applies 맑은 고딕 to all Excel content
- **Integration**: Automatically applied during document generation

#### 4. HTML → Structured Data Pipeline
- **Parser**: `app/parsers/itsupp_html_parser.py` - Extracts specific fields from IT지원의뢰서 HTML
- **Validation**: Uses CSS selectors with robust fallback patterns
- **Critical Rule**: Parser logic is fixed and should not be modified without careful testing

### Document Generation Flow

```
HTML File → parse_itsupp_html() → Raw Data Dict
                ↓
Raw Data → build_word_payload() → Enhanced Payload
                ↓
Enhanced Payload → fill_template_by_labels() → Mapped Document
                ↓
Document → ensure_malgun_gothic_document() → Final Document
```

### Template System Requirements

#### Critical Template Files (must exist in `templates/`)
- `template.docx` - Word document template with label-based mapping
- `template.xlsx` - Excel test scenario template  
- `template_list.xlsx` - Excel list template for multiple items

#### Template Validation
Templates are SHA-256 verified in tests to ensure integrity. Any template changes require test updates.

### API Endpoint Strategy

#### Primary Endpoints
- `/create-cm-word` - Uses label-based mapping (current default)
- `/create-cm-word-enhanced` - Accepts raw_data for field enhancement
- `/parse-html` - Converts HTML to structured JSON

#### Legacy Support
- `word_builder.py` contains the original cell index-based approach but `label_based_word_builder.py` is the recommended approach

## Development Guidelines

### Path Management
- Always use `pathlib.Path` for cross-platform compatibility
- Use `app.services.paths` functions for consistent directory resolution
- Templates can be overridden via `AUTODOC_TPL_DIR` environment variable

### Field Mapping Extensions
To add system-specific deployer mapping:
1. Edit `get_system_deployer()` in `word_payload.py`
2. Add entries to `system_deployer_mapping` dictionary
3. Supports both system names and abbreviations

### Template Structure Changes
If Word template structure changes:
1. Test with `debug_*` scripts in root directory for structure analysis
2. Update cell mapping in `get_data_cell_for_label()` function
3. Add special handling functions if needed (like `handle_table2_special()`)

### Testing Strategy
- Template integrity via SHA-256 validation
- HTML parser accuracy via fixture matching
- Document builders via coordinate mapping verification  
- API integration via FastAPI TestClient
- Cross-platform compatibility via path handling tests

### Security Considerations
- Path traversal protection in file downloads
- Filename sanitization (removes `\ / : * ? " < > |`)
- Template integrity verification
- Pydantic validation for all inputs