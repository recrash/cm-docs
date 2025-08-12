# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Development Commands

### Testing
```bash
# Run all tests with coverage
pytest --cov=ts_cli --cov-report=html

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only  
pytest -m e2e           # End-to-End tests only

# Run single test file
pytest tests/unit/test_vcs.py

# Run specific test
pytest tests/unit/test_vcs.py::TestVCSFactory::test_get_analyzer_with_git_repository
```

### Code Quality
```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking (Note: python_version config issue with 3.8)
mypy src/
```

### Building
```bash
# Build executable (cross-platform)
python scripts/build.py

# Build options
python scripts/build.py --no-clean    # Skip cleanup
python scripts/build.py --no-test     # Skip testing

# Create Windows installer (Windows only)
makensis scripts/setup_win.nsi

# Create macOS DMG with helper app (macOS only)  
python scripts/create_dmg.py

# Build helper app separately (macOS only)
python scripts/build_helper_app.py

# Test helper app (macOS only)
python scripts/test_helper_app.py

# Install helper app only
sh scripts/install_helper.sh

# Create DMG without helper app
python scripts/create_dmg.py --no-helper-app

# Build troubleshooting
python scripts/build.py --help
```

### Development Setup
```bash
# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# Test CLI directly
python -m ts_cli.main --help

# Alternative CLI testing
ts-cli --help  # After pip install -e .
```

## Architecture Overview

### Strategy Pattern for VCS Support
The codebase uses the Strategy pattern to support multiple VCS systems through a common interface:

- **Abstract Base**: `ts_cli.vcs.base_analyzer.RepositoryAnalyzer` defines the contract
- **Concrete Implementation**: `ts_cli.vcs.git_analyzer.GitAnalyzer` implements Git support
- **Factory Function**: `ts_cli.vcs.get_analyzer()` returns appropriate analyzer based on repository type
- **Extensibility**: New VCS systems can be added by implementing `RepositoryAnalyzer`

### URL Protocol Integration
The CLI supports `testscenariomaker://` URL protocol for web browser integration:

- **Protocol Handler**: `handle_url_protocol()` in `main.py` processes URL schemes before Click parser
- **Cross-Platform Support**: Windows registry (HKCR) and macOS CFBundleURLTypes integration
- **macOS Helper App System**: Dedicated helper app to bypass browser sandbox restrictions
- **Path Processing**: Platform-specific URL parsing and path normalization
- **Error Handling**: Comprehensive validation for URLs, paths, and repository states

#### macOS Helper App Architecture
To solve macOS browser sandbox restrictions that prevent CLI network communication:

1. **Problem**: Browser-launched CLI inherits sandbox restrictions, blocking API calls
2. **Solution**: AppleScript-based helper app launches CLI as independent process
3. **Implementation**: 
   - `helper_app.applescript`: Core AppleScript URL handler
   - `helper_app_info.plist`: App bundle configuration with URL scheme registration
   - `build_helper_app.py`: Automated helper app builder with CLI embedding
   - `install_helper.sh`: Standalone helper app installation script
   - `test_helper_app.py`: Comprehensive testing and validation framework

**Helper App Workflow**:
```
Browser Click → testscenariomaker:// → Helper App → Independent CLI Process → API Success
```

**Key Features**:
- **Sandbox Breaking**: Runs CLI outside browser process tree
- **Embedded CLI**: Self-contained with CLI executable embedded in Resources
- **Background Operation**: LSBackgroundOnly=true, invisible to user
- **Ad-hoc Signing**: Automatic code signing for macOS compatibility
- **URL Validation**: Comprehensive URL parsing and path validation
- **Cross-Browser Support**: Works with Safari, Chrome, Firefox
- **Automated Testing**: Complete test suite with HTML test interface

### Core Components Flow
1. **CLI Entry** (`main.py`) → URL protocol detection → Click-based Korean UI with command routing
2. **Business Logic** (`cli_handler.py`) → Orchestrates: repo analysis → API call → result processing
3. **VCS Analysis** (`vcs/`) → Strategy pattern for Git/SVN/Mercurial support (currently Git only)
4. **API Client** (`api_client.py`) → httpx + tenacity for robust API communication
5. **Configuration** (`utils/config_loader.py`) → Multi-location config file loading
6. **Logging** (`utils/logger.py`) → Rich console + file logging

### Key Abstractions
- **RepositoryAnalyzer**: Abstract base for VCS-specific analysis
- **CLIHandler**: Main business logic orchestrator
- **APIClient**: Async HTTP client with retry logic
- **ConfigLoader**: Configuration management with fallback hierarchy

## Testing Strategy

### Test Structure (Test Pyramid)
- **Unit Tests** (`tests/unit/`): Mock-based isolated component testing
- **Integration Tests** (`tests/integration/`): API communication with mock servers
- **E2E Tests** (`tests/e2e/`): Full CLI workflow using subprocess

### Test Markers
- `@pytest.mark.unit`: Individual module functionality
- `@pytest.mark.integration`: Cross-module interaction
- `@pytest.mark.e2e`: Complete user workflows

### Key Test Patterns
- Mock external dependencies (subprocess, HTTP calls)
- Use `tmp_path` fixture for filesystem tests
- `httpx_mock` for API client testing
- Subprocess-based E2E testing (not Playwright since this is CLI, not web)
- Cross-platform path compatibility tests in `test_path_compatibility.py`
- **macOS Helper App Testing**: Comprehensive validation framework in `test_helper_app.py`
  - AppleScript syntax validation
  - App bundle structure verification
  - URL protocol registration testing
  - Embedded CLI executable validation
  - Browser compatibility testing with HTML interface

## Configuration System

### Config File Hierarchy (first found wins)
1. Current directory `config.ini`
2. Project root `config/config.ini`
3. Auto-generated defaults

### Key Config Sections
- `[api]`: base_url, timeout, max_retries
- `[cli]`: default_output_format, verbose, show_progress  
- `[logging]`: level, file_enabled (format uses %% escaping for ConfigParser)
- `[vcs]`: git_timeout, max_diff_size

### Additional Commands
- `ts-cli analyze`: Main analysis command with branch comparison support
- `ts-cli info <path>`: Show repository information without analysis
- `ts-cli config-show`: Display current configuration
- `ts-cli version`: Show version information
- `ts-cli "testscenariomaker://path"`: Direct URL protocol handling for testing
- **Helper App Commands (macOS only)**:
  - `python scripts/build_helper_app.py`: Build helper app with embedded CLI
  - `python scripts/test_helper_app.py`: Run comprehensive helper app tests
  - `sh scripts/install_helper.sh`: Install helper app to Applications folder
  - `open 'testscenariomaker:///path/to/repo'`: Test URL protocol handling

### CLI Features
- **Korean UI**: All user interface text is in Korean for better accessibility
- **Rich Console**: Uses Rich library for enhanced console output with colors and formatting
- **URL Protocol**: Supports `testscenariomaker://` protocol for integration with web browsers
  - Cross-platform URL parsing and path handling
  - Automatic protocol registration during installation
  - Support for URL-encoded paths with spaces and special characters
  - **macOS Helper App**: Dedicated helper app bypasses browser sandbox restrictions
- **Branch Comparison**: Analyzes differences between base and head branches (default: origin/develop → HEAD)
- **Working State**: Includes uncommitted changes in analysis

## Cross-Platform Development Guidelines

### Path Management with pathlib
**CRITICAL**: Always use `pathlib.Path` for cross-platform compatibility. Never use string concatenation or `os.path.join()` for path operations.

#### ✅ Correct Path Usage
```python
from pathlib import Path

# Project structure with relative paths
project_root = Path(__file__).parent.parent  # Relative to current file
src_dir = project_root / "src"
config_file = project_root / "config" / "config.ini"

# Cross-platform file operations
if config_file.exists():
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()

# Resolve to absolute when needed for external tools
absolute_path = project_root.resolve()
subprocess.run(['tool', str(absolute_path)])  # Convert to string for subprocess

# CRITICAL: Always convert Path to string for subprocess cwd parameter
subprocess.run(
    ['git', 'status'], 
    cwd=str(repo_path),  # Essential for cross-platform compatibility
    capture_output=True
)
```

#### ❌ Avoid These Patterns
```python
# DON'T: String concatenation
config_path = project_root + "/config/config.ini"

# DON'T: os.path methods
import os
config_path = os.path.join(project_root, "config", "config.ini")

# DON'T: Hard-coded separators
config_path = f"{project_root}/config/config.ini"

# DON'T: Passing Path objects to subprocess without str()
subprocess.run(['tool', project_root])  # Will fail!

# DON'T: Path object as cwd parameter
subprocess.run(['git', 'status'], cwd=repo_path)  # Cross-platform issues!
```

### Build System Path Handling
The build scripts (`scripts/build.py`, `scripts/create_dmg.py`, `scripts/build_helper_app.py`) demonstrate proper cross-platform path management:

- **Relative Structure**: Maintain project structure using relative paths from project root
- **String Conversion**: Convert Path objects to strings when interfacing with external tools
- **File Validation**: Check file existence before operations
- **Platform Detection**: Use `platform.system()` for platform-specific logic

### Platform-Specific Considerations

#### Windows
- File paths may contain spaces and special characters
- Case-insensitive filesystem (usually)
- Backslash separators (handled automatically by pathlib)
- `.exe` extension required for executables

#### macOS/Linux
- Case-sensitive filesystem
- Forward slash separators
- No file extension required for executables
- Different permission model

## Extension Points

### Adding New VCS Support
1. Create new analyzer class inheriting from `RepositoryAnalyzer`
2. Implement abstract methods: `validate_repository()`, `get_changes()`, `get_repository_info()`
3. Add detection logic to `get_analyzer()` factory function
4. Add comprehensive tests following existing patterns
5. **IMPORTANT**: Use `pathlib.Path` for all file system operations

### Adding New Commands
1. Add Click command in `main.py`
2. Implement business logic in `cli_handler.py`
3. Add Korean help text and error messages
4. Write unit, integration, and E2E tests
5. **IMPORTANT**: Ensure cross-platform compatibility using pathlib

## Build System

The project uses PyInstaller for cross-platform executable generation with robust error handling and path management:

### Build Script Features (`scripts/build.py`)
- **Automatic File Validation**: Checks for required files before build
- **Conditional Resource Inclusion**: Optional files (config.ini, icons) included only if present
- **Cross-Platform Path Handling**: Uses pathlib with proper string conversion for PyInstaller
- **Detailed Logging**: Progress tracking and error reporting at each step
- **Build Information**: Generates build metadata in JSON format

### DMG Creation (`scripts/create_dmg.py`)
- **Robust Mount Point Detection**: Uses regex patterns to parse hdiutil output
- **Error Recovery**: Automatic cleanup on failures
- **App Bundle Generation**: Proper macOS app structure with Info.plist
- **Helper App Integration**: Automatic helper app building and inclusion
- **URL Protocol Registration**: Automatic CFBundleURLTypes configuration for testscenariomaker:// protocol
- **Installation Scripts**: Automated install/uninstall shell scripts with helper app support
- **Dual App Support**: Handles both main CLI app and helper app in single DMG

### Helper App Builder (`scripts/build_helper_app.py`)
- **AppleScript Compilation**: Automated osacompile integration
- **CLI Embedding**: Embeds PyInstaller-built CLI into helper app Resources
- **Info.plist Management**: Template-based plist generation with version substitution
- **Code Signing**: Automatic ad-hoc signing for macOS compatibility
- **Quarantine Removal**: Removes com.apple.quarantine attribute
- **Validation Scripts**: Generates verification scripts for testing
- **Build Metadata**: Creates detailed JSON build information

### Key Improvements
- **Path Object String Conversion**: All Path objects explicitly converted to strings for external tools
- **File Existence Validation**: Pre-flight checks prevent build failures
- **Relative Path Preservation**: Maintains project portability across environments
- **Platform Detection**: Automatic platform-specific handling
- **URL Protocol Integration**: Automatic protocol registration in Windows NSIS and macOS Info.plist

### Build Troubleshooting
Common issues and solutions are documented in README.md build section.

## Development Best Practices

### When Working with File Paths
1. **Always import pathlib**: `from pathlib import Path`
2. **Use relative paths for project structure**: `project_root / "src" / "module"`
3. **Convert to string for external tools**: `str(path)` when calling subprocess
4. **Check file existence**: `path.exists()` before operations
5. **Use `.resolve()` sparingly**: Only when absolute paths are required

### Code Quality Standards
- **Type Hints**: Use pathlib.Path for path parameters, proper async return types
- **Error Handling**: Provide clear error messages with path information
- **Testing**: Include cross-platform path tests (see `test_path_compatibility.py`)
- **Documentation**: Comment platform-specific behavior
- **ConfigParser**: Use %% escaping for logging format strings to avoid interpolation errors

### PyInstaller Compatibility
The codebase uses conditional imports to handle PyInstaller's different module resolution:

```python
# PyInstaller compatibility pattern
try:
    from . import __version__
    from .cli_handler import CLIHandler
except ImportError:
    # PyInstaller environment uses absolute imports
    import ts_cli
    from ts_cli import __version__
    from ts_cli.cli_handler import CLIHandler
```

### Example Path-Safe Function
```python
from pathlib import Path
from typing import Optional

def find_config_file(project_root: Path) -> Optional[Path]:
    """Find configuration file using cross-platform path handling."""
    candidates = [
        project_root / "config.ini",
        project_root / "config" / "config.ini",
    ]
    
    for config_path in candidates:
        if config_path.exists() and config_path.is_file():
            return config_path
    
    return None
```

## Recent Cross-Platform Improvements

### Critical Fixes Implemented
1. **subprocess.run cwd Parameter**: All Path objects converted to strings before passing to subprocess.run cwd parameter
2. **ConfigParser Interpolation**: Logging format strings use %% escaping to prevent interpolation errors
3. **Path Resolution**: Added `.resolve()` calls for symlink handling in tests (macOS compatibility)
4. **Type Annotations**: Fixed missing async return types and parameter annotations

### Key Files Modified/Added
- `src/ts_cli/main.py`: Added URL protocol handling with `handle_url_protocol()` function
- `src/ts_cli/vcs/git_analyzer.py`: Fixed `_run_git_command()` cwd parameter
- `src/ts_cli/utils/config_loader.py`: Fixed logging format string escaping
- `tests/test_url_parsing.py`: Comprehensive URL protocol parsing tests
- `tests/unit/test_path_compatibility.py`: Comprehensive cross-platform path testing
- `scripts/setup_win.nsi`: Windows NSIS script with URL protocol registration
- `scripts/create_dmg.py`: Enhanced macOS DMG script with helper app integration
- `test_url_protocol.html`: E2E testing webpage for URL protocol validation

**New Helper App System Files:**
- `scripts/helper_app.applescript`: Core AppleScript URL protocol handler
- `scripts/helper_app_info.plist`: Helper app bundle configuration template
- `scripts/build_helper_app.py`: Comprehensive helper app builder (400+ lines)
- `scripts/install_helper.sh`: Standalone helper app installation script
- `scripts/test_helper_app.py`: Complete testing and validation framework (650+ lines)
- Additional cross-platform tests in existing test files

### Testing Coverage
- 10 new URL protocol parsing tests (8 passing, 2 Windows-specific skipped on macOS)
- 18 cross-platform path compatibility tests
- Edge cases: Unicode paths, URL encoding, special characters, symlinks
- Mock subprocess testing to verify string conversion
- Platform-specific path separator validation
- URL protocol error handling and validation

**Helper App Testing Framework:**
- AppleScript syntax validation with osacompile
- App bundle structure verification (Contents/MacOS/Resources)
- URL scheme registration testing with lsregister
- Info.plist validation with plutil
- Embedded CLI executable verification
- Code signing status validation
- Interactive HTML test interface generation
- Cross-browser compatibility testing
- Comprehensive JSON test reporting

## Dependencies and Stack

### Core Dependencies
- **Click**: Command-line interface framework with Korean support
- **Rich**: Enhanced console output with colors and formatting
- **httpx**: Modern async HTTP client with retry support
- **tenacity**: Retry logic for robust API communication

### Development Dependencies
- **pytest**: Testing framework with markers (unit/integration/e2e)
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mock object support
- **httpx-mock**: HTTP client mocking for API tests
- **black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

### Build Tools
- **PyInstaller**: Cross-platform executable generation
- **NSIS**: Windows installer creation (Windows only)
- **hdiutil**: macOS DMG creation (macOS only)
- **osacompile**: AppleScript compilation (macOS helper app)
- **codesign**: macOS code signing (macOS helper app)
- **lsregister**: URL scheme registration testing (macOS helper app)
- **plutil**: Property list validation (macOS helper app)

## macOS Helper App System Commands

When working with the macOS helper app system, use these commands:

```bash
# Build main CLI first (required for helper app)
python scripts/build.py

# Build helper app with embedded CLI
python scripts/build_helper_app.py

# Test helper app system comprehensively
python scripts/test_helper_app.py

# Install helper app separately
sh scripts/install_helper.sh

# Create DMG with both main CLI and helper app
python scripts/create_dmg.py

# Test URL protocol in browser
open dist/helper_test.html

# Verify URL scheme registration
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -dump | grep testscenariomaker
```

**Helper App System Architecture:**
- Main CLI (`dist/ts-cli`) - Built with PyInstaller
- Helper App (`dist/TestscenarioMaker Helper.app`) - AppleScript app with embedded CLI
- Test Framework (`scripts/test_helper_app.py`) - Comprehensive validation
- Installation Scripts (`scripts/install_helper.sh`, DMG installer) - Automated deployment

**Key Benefits:**
- Bypasses macOS browser sandbox restrictions
- Enables network communication from browser-launched CLI
- Provides seamless user experience for `testscenariomaker://` links
- Comprehensive testing and validation framework

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

For macOS helper app development, use the dedicated helper app scripts instead of general agents.