#!/bin/bash

# TestscenarioMaker CLI Cross-Platform Protocol Handler Validation Script
# This script validates that the CLI process management works correctly across platforms

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TEST_SESSION_ID="test-session-123"
TEST_REPO_PATH="/Users/recrash/Documents/Workspace/cm-docs"
TEST_HTML_PATH="/Users/recrash/Downloads/0_FW_ Hub HTML_250813/Drum 재고 관리.html"
TEST_SERVER_URL="https://cm-docs.cloud/tests/feature_HTMLupload"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Platform detection
detect_platform() {
    case "$(uname -s)" in
        Darwin)
            echo "macOS"
            ;;
        Linux)
            echo "Linux"
            ;;
        CYGWIN*|MINGW*|MSYS*)
            echo "Windows"
            ;;
        *)
            echo "Unknown"
            ;;
    esac
}

# Check if CLI is installed and accessible
check_cli_installation() {
    log_info "Checking CLI installation..."

    local cli_paths=("ts-cli" "/usr/local/bin/ts-cli" "/opt/testscenariomaker/ts-cli")
    local found_cli=""

    for path in "${cli_paths[@]}"; do
        if command -v "$path" &> /dev/null; then
            found_cli="$path"
            break
        fi
    done

    if [[ -n "$found_cli" ]]; then
        log_success "CLI found at: $found_cli"
        "$found_cli" --version || log_warning "Version check failed"
        return 0
    else
        log_error "CLI not found in any expected location"
        return 1
    fi
}

# Test process cleanup functionality
test_process_cleanup() {
    log_info "Testing process cleanup functionality..."

    # Start a test CLI process in background
    log_info "Starting test CLI process..."

    # Create a test URL with session ID
    local test_url="testscenariomaker://full-generate?sessionId=${TEST_SESSION_ID}&repoPath=${TEST_REPO_PATH}&htmlPath=${TEST_HTML_PATH}&serverUrl=${TEST_SERVER_URL}"

    if command -v ts-cli &> /dev/null; then
        # Start CLI process in background (it should exit on its own)
        timeout 10s ts-cli "$test_url" &
        local cli_pid=$!
        log_info "Started CLI process with PID: $cli_pid"

        # Let it run for a moment
        sleep 2

        # Check if process is still running
        if kill -0 "$cli_pid" 2>/dev/null; then
            log_info "CLI process is running, testing cleanup..."

            # Kill the process to simulate cleanup
            kill "$cli_pid" 2>/dev/null || true
            sleep 1

            if ! kill -0 "$cli_pid" 2>/dev/null; then
                log_success "Process cleanup successful"
            else
                log_warning "Process still running after cleanup attempt"
            fi
        else
            log_info "CLI process already completed"
        fi
    else
        log_warning "CLI not available for process testing"
    fi
}

# Test URL protocol handling (platform-specific)
test_url_protocol() {
    local platform="$1"
    log_info "Testing URL protocol handling for $platform..."

    local test_url="testscenariomaker://full-generate?sessionId=${TEST_SESSION_ID}&repoPath=${TEST_REPO_PATH}&htmlPath=${TEST_HTML_PATH}&serverUrl=${TEST_SERVER_URL}"

    case "$platform" in
        "macOS")
            test_macos_protocol "$test_url"
            ;;
        "Linux")
            test_linux_protocol "$test_url"
            ;;
        "Windows")
            test_windows_protocol "$test_url"
            ;;
        *)
            log_warning "Platform-specific protocol testing not available for: $platform"
            ;;
    esac
}

# macOS protocol testing
test_macos_protocol() {
    local test_url="$1"
    log_info "Testing macOS Helper App protocol handling..."

    # Check if Helper App exists
    local helper_app_path="/Applications/TestscenarioMaker Helper.app"
    if [[ -d "$helper_app_path" ]]; then
        log_success "Helper App found at: $helper_app_path"

        # Test URL handling
        log_info "Testing URL protocol with Helper App..."
        open "$test_url" || log_warning "Failed to open URL with Helper App"

        # Check for log files
        local log_file="$(getconf DARWIN_USER_TEMP_DIR)TestscenarioMaker_Helper.log"
        if [[ -f "$log_file" ]]; then
            log_success "Helper App log file found"
            log_info "Recent log entries:"
            tail -5 "$log_file" || true
        else
            log_warning "Helper App log file not found"
        fi
    else
        log_warning "Helper App not installed at expected location"
        log_info "Install Helper App first to test macOS protocol handling"
    fi
}

# Linux protocol testing
test_linux_protocol() {
    local test_url="$1"
    log_info "Testing Linux .desktop protocol handling..."

    # Check if .desktop file exists
    local desktop_file="$HOME/.local/share/applications/testscenariomaker-protocol.desktop"
    if [[ -f "$desktop_file" ]]; then
        log_success ".desktop file found"

        # Check if handler script exists
        local handler_script="/opt/testscenariomaker/cli/testscenariomaker-cli-protocol-handler.sh"
        if [[ -f "$handler_script" && -x "$handler_script" ]]; then
            log_success "Protocol handler script found and executable"

            # Test direct script execution
            log_info "Testing protocol handler script..."
            "$handler_script" "$test_url" &
            local handler_pid=$!

            sleep 2

            # Check for log files
            local log_file="/tmp/testscenariomaker-protocol-handler.log"
            if [[ -f "$log_file" ]]; then
                log_success "Protocol handler log file found"
                log_info "Recent log entries:"
                tail -5 "$log_file" || true
            else
                log_warning "Protocol handler log file not found"
            fi

            # Clean up
            kill "$handler_pid" 2>/dev/null || true
        else
            log_warning "Protocol handler script not found or not executable"
        fi
    else
        log_warning ".desktop file not installed"
        log_info "Install .desktop file first to test Linux protocol handling"
    fi
}

# Windows protocol testing (placeholder)
test_windows_protocol() {
    local test_url="$1"
    log_info "Testing Windows registry protocol handling..."
    log_warning "Windows protocol testing requires PowerShell and registry access"
    log_info "Test URL: $test_url"

    # Could add PowerShell-based testing here if running on Windows
    if command -v powershell &> /dev/null; then
        log_info "PowerShell available for Windows testing"
        # Add Windows-specific tests here
    else
        log_warning "PowerShell not available for Windows testing"
    fi
}

# Test session management
test_session_management() {
    log_info "Testing session management functionality..."

    if [[ -f "/Users/recrash/Documents/Workspace/cm-docs/cli/src/ts_cli/core/process_manager.py" ]]; then
        log_success "Process manager module found"

        # Test Python import
        if command -v python3 &> /dev/null; then
            cd "/Users/recrash/Documents/Workspace/cm-docs/cli" || return 1

            if python3 -c "from src.ts_cli.core.process_manager import ProcessManager; print('Import successful')" 2>/dev/null; then
                log_success "Process manager module imports correctly"
            else
                log_warning "Process manager module import failed"
            fi
        else
            log_warning "Python3 not available for testing"
        fi
    else
        log_error "Process manager module not found"
    fi
}

# Comprehensive validation
run_comprehensive_validation() {
    local platform
    platform=$(detect_platform)

    log_info "Starting comprehensive validation for $platform..."
    echo "================================================"

    # Run all tests
    check_cli_installation
    echo

    test_session_management
    echo

    test_process_cleanup
    echo

    test_url_protocol "$platform"
    echo

    log_info "Validation complete!"
    echo "================================================"

    # Summary
    log_info "Test Summary:"
    log_info "- Platform: $platform"
    log_info "- Session ID: $TEST_SESSION_ID"
    log_info "- Test URL: testscenariomaker://full-generate?sessionId=$TEST_SESSION_ID&..."

    echo
    log_success "All tests completed. Check the output above for any warnings or errors."
}

# Main execution
main() {
    if [[ $# -eq 0 ]]; then
        run_comprehensive_validation
    else
        case "$1" in
            "cli")
                check_cli_installation
                ;;
            "process")
                test_process_cleanup
                ;;
            "protocol")
                local platform
                platform=$(detect_platform)
                test_url_protocol "$platform"
                ;;
            "session")
                test_session_management
                ;;
            *)
                echo "Usage: $0 [cli|process|protocol|session]"
                echo "Run without arguments for comprehensive validation"
                exit 1
                ;;
        esac
    fi
}

# Execute main function
main "$@"