# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TestscenarioMaker is an AI-powered Python tool that automatically generates test scenarios by analyzing Git repository changes. It uses Ollama LLM (specifically Qwen3:14B model) to create Korean-language test scenarios in Excel format.

## Core Architecture

### Module Structure
- `main.py` - Entry point that orchestrates the entire workflow
- `src/git_analyzer.py` - Extracts Git commit messages and code diffs
- `src/llm_handler.py` - Handles Ollama API communication
- `src/excel_writer.py` - Writes LLM results to Excel templates
- `src/document_parser.py` - Parses Word documents (.docx) for change requests

### Key Dependencies
- **LLM**: Ollama (local server at http://localhost:11434)
- **Git Analysis**: GitPython
- **Excel Generation**: openpyxl
- **Document Parsing**: python-docx
- **API Communication**: requests

## Common Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Ollama Setup
```bash
# Install Ollama from https://ollama.ai
# Pull the required model
ollama pull qwen3:14b

# Start Ollama server
ollama serve
```

### Running the Application
```bash
# Execute main script
python main.py

# Test individual modules
python src/git_analyzer.py
python src/document_parser.py
```

## Configuration

### Repository Path Configuration
Update `repo_path` variable in `main.py` to point to the Git repository you want to analyze:
```python
repo_path = "/path/to/your/git/repository"
```

### Model Configuration
Change the LLM model in `main.py`:
```python
model_name = "qwen3:14b"  # or other Ollama models
```

### Git Branch Configuration
Modify branch comparison in `git_analyzer.py`:
```python
base_branch = 'origin/develop'  # base branch for comparison
head_branch = 'HEAD'           # target branch/commit
```

## Development Workflow

1. **Git Analysis**: The system extracts commit messages and code diffs from the specified repository
2. **LLM Processing**: Sends structured prompts to Ollama with Git analysis data
3. **JSON Parsing**: Extracts structured test scenario data from LLM response using regex
4. **Excel Generation**: Populates Excel template with parsed test scenarios

## Output Format

Generated Excel files contain:
- **Scenario Description**: Overall test purpose summary
- **Test Scenario Name**: Representative title for the test suite
- **Test Cases**: Individual test cases with ID, procedures, preconditions, test data, expected results, and test type (unit/integration)

## Important Notes

- Ensure Ollama server is running before executing the main script
- The system expects Korean language responses from the LLM
- Excel templates must be present in the `templates/` directory
- Output files are saved in the `outputs/` directory with timestamp prefixes
- The LLM timeout is set to 600 seconds for complex analysis tasks

## Error Handling

Common issues and solutions:
- **Ollama connection failure**: Verify Ollama server is running on localhost:11434
- **Git repository access**: Ensure proper Git credentials and repository path
- **Model not found**: Run `ollama pull qwen3:14b` to download the required model
- **Template file missing**: Verify `templates/template.xlsx` exists