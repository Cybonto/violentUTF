#!/usr/bin/env bash
# logging_utils.sh - Logging utilities for ViolentUTF Linux setup
# Provides consistent logging with verbosity control

# Verbosity levels:
# 0 = quiet (errors/warnings only)
# 1 = normal (default)
# 2 = verbose
# 3 = debug

# Default verbosity if not set
export VUTF_VERBOSITY=${VUTF_VERBOSITY:-1}

# Color codes for different log levels
readonly COLOR_RED='\033[0;31m'
readonly COLOR_GREEN='\033[0;32m'
readonly COLOR_YELLOW='\033[0;33m'
readonly COLOR_BLUE='\033[0;34m'
readonly COLOR_MAGENTA='\033[0;35m'
readonly COLOR_CYAN='\033[0;36m'
readonly COLOR_RESET='\033[0m'

# Function to check if we should log at a given level
should_log() {
    local required_level="$1"
    [ "$VUTF_VERBOSITY" -ge "$required_level" ]
}

# Logging functions
log_error() {
    # Always show errors regardless of verbosity
    echo -e "${COLOR_RED}❌ ERROR: $*${COLOR_RESET}" >&2
}

log_warn() {
    # Always show warnings regardless of verbosity
    echo -e "${COLOR_YELLOW}⚠️  WARNING: $*${COLOR_RESET}" >&2
}

log_success() {
    if should_log 1; then
        echo -e "${COLOR_GREEN}✅ $*${COLOR_RESET}"
    fi
}

log_info() {
    if should_log 1; then
        echo -e "${COLOR_BLUE}ℹ️  $*${COLOR_RESET}"
    fi
}

log_progress() {
    if should_log 1; then
        echo -e "${COLOR_CYAN}🔄 $*${COLOR_RESET}"
    fi
}

log_detail() {
    if should_log 2; then
        echo -e "${COLOR_MAGENTA}📋 $*${COLOR_RESET}"
    fi
}

log_debug() {
    if should_log 3; then
        echo -e "${COLOR_YELLOW}🐛 DEBUG: $*${COLOR_RESET}"
    fi
}

log_phase() {
    if should_log 1; then
        echo ""
        echo -e "${COLOR_CYAN}========================================${COLOR_RESET}"
        echo -e "${COLOR_CYAN}$*${COLOR_RESET}"
        echo -e "${COLOR_CYAN}========================================${COLOR_RESET}"
    fi
}

# Function to run a command with appropriate output handling
run_command() {
    local description="$1"
    shift
    local command="$*"

    if should_log 2; then
        log_detail "Running: $command"
    fi

    if should_log 3; then
        # Debug mode - show all output
        eval "$command"
    elif should_log 2; then
        # Verbose mode - show command output but not as detailed
        eval "$command" 2>&1 | sed 's/^/  /'
    else
        # Normal/quiet mode - suppress output unless there's an error
        local output
        output=$(eval "$command" 2>&1)
        local status=$?
        if [ $status -ne 0 ]; then
            log_error "$description failed:"
            echo "$output" | sed 's/^/  /' >&2
        fi
        return $status
    fi
}

# Export functions for use in other scripts
export -f should_log log_error log_warn log_success log_info log_progress log_detail log_debug log_phase run_command
