#!/bin/bash

# TestscenarioMaker CLI Protocol Handler for Linux
# This script handles testscenariomaker:// URLs with process management
#
# Installation:
# 1. Place this script in /opt/testscenariomaker/cli/
# 2. Make executable: chmod +x testscenariomaker-cli-protocol-handler.sh
# 3. Install the corresponding .desktop file

set -euo pipefail

# Configuration
LOG_FILE="/tmp/testscenariomaker-protocol-handler.log"
CLI_EXECUTABLE="/usr/local/bin/ts-cli"
LOCKFILE_DIR="/tmp/testscenariomaker-sessions"

# Logging function
log_message() {
    local level="$1"
    local message="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" >> "$LOG_FILE"
    echo "[$level] $message" >&2
}

# Create lock directory if it doesn't exist
create_lockdir() {
    if [[ ! -d "$LOCKFILE_DIR" ]]; then
        mkdir -p "$LOCKFILE_DIR"
        log_message "INFO" "Created lock directory: $LOCKFILE_DIR"
    fi
}

# Extract session ID from URL
extract_session_id() {
    local url="$1"
    if [[ "$url" =~ sessionId=([^&]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        echo ""
    fi
}

# Clean up existing processes
cleanup_existing_processes() {
    log_message "INFO" "Cleaning up existing TestscenarioMaker processes..."

    # Find and terminate existing ts-cli processes
    if pgrep -f "ts-cli" > /dev/null; then
        log_message "INFO" "Found existing ts-cli processes, terminating..."
        pkill -TERM -f "ts-cli" || true
        sleep 2

        # Force kill if still running
        if pgrep -f "ts-cli" > /dev/null; then
            log_message "WARN" "Force killing remaining ts-cli processes..."
            pkill -KILL -f "ts-cli" || true
        fi
    else
        log_message "INFO" "No existing ts-cli processes found"
    fi
}

# Clean up session-specific processes
cleanup_session_processes() {
    local session_id="$1"
    if [[ -n "$session_id" ]]; then
        log_message "INFO" "Cleaning up processes for session: $session_id"

        # Find processes with session ID in command line
        if pgrep -f "$session_id" > /dev/null; then
            log_message "INFO" "Found session-specific processes, terminating..."
            pkill -TERM -f "$session_id" || true
            sleep 3

            # Force kill if still running
            if pgrep -f "$session_id" > /dev/null; then
                log_message "WARN" "Force killing remaining session processes..."
                pkill -KILL -f "$session_id" || true
            fi
        else
            log_message "INFO" "No session-specific processes found"
        fi

        # Clean up lock file
        local lockfile="$LOCKFILE_DIR/session-$session_id.lock"
        if [[ -f "$lockfile" ]]; then
            rm -f "$lockfile"
            log_message "INFO" "Removed session lock file: $lockfile"
        fi
    fi
}

# Check if CLI executable exists
check_cli_executable() {
    if [[ ! -f "$CLI_EXECUTABLE" ]]; then
        log_message "ERROR" "TestscenarioMaker CLI not found at: $CLI_EXECUTABLE"

        # Try alternative locations
        for alt_path in "/usr/bin/ts-cli" "/opt/testscenariomaker/ts-cli" "$(which ts-cli 2>/dev/null || echo '')"; do
            if [[ -n "$alt_path" && -f "$alt_path" ]]; then
                CLI_EXECUTABLE="$alt_path"
                log_message "INFO" "Found CLI at alternative location: $CLI_EXECUTABLE"
                return 0
            fi
        done

        log_message "ERROR" "TestscenarioMaker CLI executable not found"
        exit 1
    fi

    if [[ ! -x "$CLI_EXECUTABLE" ]]; then
        log_message "ERROR" "CLI executable is not executable: $CLI_EXECUTABLE"
        exit 1
    fi
}

# Main protocol handler function
handle_protocol() {
    local url="$1"

    log_message "INFO" "TestscenarioMaker Protocol Handler Starting"
    log_message "INFO" "URL: $url"

    # Validate URL format
    if [[ ! "$url" =~ ^testscenariomaker:// ]]; then
        log_message "ERROR" "Invalid URL format: $url"
        exit 1
    fi

    # Create necessary directories
    create_lockdir

    # Check CLI executable
    check_cli_executable

    # Extract session ID and manage processes
    local session_id
    session_id=$(extract_session_id "$url")

    if [[ -n "$session_id" ]]; then
        log_message "INFO" "Session ID detected: $session_id"
        cleanup_session_processes "$session_id"

        # Create session lock file
        local lockfile="$LOCKFILE_DIR/session-$session_id.lock"
        echo "$$" > "$lockfile"
        log_message "INFO" "Created session lock: $lockfile"
    else
        log_message "INFO" "No session ID found, cleaning all ts-cli processes"
        cleanup_existing_processes
    fi

    # Launch CLI with proper environment
    log_message "INFO" "Starting TestscenarioMaker CLI..."
    log_message "INFO" "Command: $CLI_EXECUTABLE \"$url\""

    # Set up environment
    export LANG=en_US.UTF-8
    export LC_ALL=en_US.UTF-8

    # Execute CLI in background with output redirection
    if nohup "$CLI_EXECUTABLE" "$url" >> "$LOG_FILE" 2>&1 &
    then
        local cli_pid=$!
        log_message "INFO" "CLI started successfully with PID: $cli_pid"

        # Store PID for session management
        if [[ -n "$session_id" ]]; then
            echo "$cli_pid" > "$LOCKFILE_DIR/session-$session_id.pid"
        fi
    else
        log_message "ERROR" "Failed to start CLI"
        exit 1
    fi

    log_message "INFO" "Protocol handler completed successfully"
}

# Signal handlers for graceful shutdown
cleanup_on_exit() {
    log_message "INFO" "Protocol handler received exit signal"
    # Clean up any temporary files if needed
}

trap cleanup_on_exit EXIT

# Main execution
if [[ $# -ne 1 ]]; then
    log_message "ERROR" "Usage: $0 <testscenariomaker://url>"
    exit 1
fi

# Start handling the protocol
handle_protocol "$1"