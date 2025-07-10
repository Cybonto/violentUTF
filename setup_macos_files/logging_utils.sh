#!/usr/bin/env bash
# logging_utils.sh - Centralized logging utility for ViolentUTF setup scripts
# This module provides consistent, verbosity-controlled logging across all setup components

# Global verbosity level (0=quiet, 1=normal, 2=verbose, 3=debug)
VUTF_VERBOSITY=${VUTF_VERBOSITY:-1}

# Color codes for consistent output formatting
readonly LOG_RED='\033[0;31m'
readonly LOG_GREEN='\033[0;32m'
readonly LOG_YELLOW='\033[1;33m'
readonly LOG_BLUE='\033[0;34m'
readonly LOG_CYAN='\033[0;36m'
readonly LOG_PURPLE='\033[0;35m'
readonly LOG_GRAY='\033[0;37m'
readonly LOG_NC='\033[0m' # No Color

# Verbosity level constants
readonly QUIET=0
readonly NORMAL=1
readonly VERBOSE=2
readonly DEBUG=3

# Set verbosity level
set_verbosity() {
    local level="$1"
    case "$level" in
        quiet|0) VUTF_VERBOSITY=0 ;;
        normal|1) VUTF_VERBOSITY=1 ;;
        verbose|2) VUTF_VERBOSITY=2 ;;
        debug|3) VUTF_VERBOSITY=3 ;;
        *) 
            echo "Invalid verbosity level: $level. Using normal." >&2
            VUTF_VERBOSITY=1
            ;;
    esac
    export VUTF_VERBOSITY
}

# Get current verbosity level name
get_verbosity() {
    case "$VUTF_VERBOSITY" in
        0) echo "quiet" ;;
        1) echo "normal" ;;
        2) echo "verbose" ;;
        3) echo "debug" ;;
        *) echo "unknown" ;;
    esac
}

# Check if message should be shown at current verbosity level
should_log() {
    local required_level="$1"
    [ "$VUTF_VERBOSITY" -ge "$required_level" ]
}

# Core logging function
_log() {
    local level="$1"
    local color="$2"
    local prefix="$3"
    local message="$4"
    
    if should_log "$level"; then
        echo -e "${color}${prefix}${message}${LOG_NC}"
    fi
}

# Critical error messages (always shown)
log_error() {
    _log 0 "$LOG_RED" "❌ " "$1" >&2
}

# Warning messages (always shown)
log_warn() {
    _log 0 "$LOG_YELLOW" "⚠️  " "$1" >&2
}

# Success confirmation (always shown)
log_success() {
    _log 0 "$LOG_GREEN" "✅ " "$1"
}

# Progress indicators (normal+)
log_progress() {
    _log 1 "$LOG_BLUE" "🚀 " "$1"
}

# Phase headers (normal+)
log_phase() {
    if should_log 1; then
        echo ""
        echo -e "${LOG_CYAN}=== $1 ===${LOG_NC}"
    fi
}

# Information messages (normal+)
log_info() {
    _log 1 "$LOG_GRAY" "ℹ️  " "$1"
}

# Status messages (normal+)
log_status() {
    _log 1 "$LOG_CYAN" "📊 " "$1"
}

# Detailed information (verbose+)
log_detail() {
    _log 2 "$LOG_PURPLE" "🔍 " "$1"
}

# Debug messages (debug only)
log_debug() {
    _log 3 "$LOG_GRAY" "🐛 " "$1"
}

# Command execution with verbosity control
log_command() {
    local description="$1"
    local command="$2"
    
    log_detail "Executing: $description"
    
    if should_log 3; then
        log_debug "Command: $command"
        eval "$command"
    elif should_log 2; then
        eval "$command" 2>&1 | while read -r line; do
            log_debug "  $line"
        done
    else
        eval "$command" >/dev/null 2>&1
    fi
}

# Docker command execution with verbosity control
log_docker() {
    local description="$1"
    local docker_command="$2"
    
    log_detail "Docker: $description"
    
    if should_log 3; then
        log_debug "Docker command: $docker_command"
        eval "$docker_command"
    elif should_log 2; then
        eval "$docker_command" 2>&1 | while read -r line; do
            log_debug "  $line"
        done
    else
        eval "$docker_command" >/dev/null 2>&1
    fi
}

# Waiting indicators with verbosity control
log_wait() {
    local message="$1"
    local duration="${2:-5}"
    
    if should_log 1; then
        echo -ne "${LOG_YELLOW}⏳ $message"
        for i in $(seq 1 "$duration"); do
            echo -n "."
            sleep 1
        done
        echo -e "${LOG_NC}"
    else
        sleep "$duration"
    fi
}

# Progress spinner for long operations
log_spinner() {
    local message="$1"
    local command="$2"
    
    if should_log 1; then
        echo -ne "${LOG_BLUE}$message "
        local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
        local i=0
        while eval "$command"; do
            printf "\b${spin:$i:1}"
            i=$(( (i+1) % ${#spin} ))
            sleep 0.1
        done
        echo -e "\b✅${LOG_NC}"
    else
        while eval "$command"; do
            sleep 0.5
        done
    fi
}

# Variable dump for debugging
log_vars() {
    if should_log 3; then
        log_debug "Variables:"
        for var in "$@"; do
            if [ -n "${!var:-}" ]; then
                # Safely display first 50 characters of sensitive variables
                if [[ "$var" =~ (KEY|SECRET|PASSWORD|TOKEN) ]]; then
                    local value="${!var}"
                    log_debug "  $var=${value:0:10}..."
                else
                    log_debug "  $var=${!var}"
                fi
            else
                log_debug "  $var=(unset)"
            fi
        done
    fi
}

# Conditional echo replacement
log_echo() {
    local level="$1"
    local message="$2"
    
    if should_log "$level"; then
        echo -e "$message"
    fi
}

# Initialize logging system
init_logging() {
    # Set verbosity from environment or default
    VUTF_VERBOSITY=${VUTF_VERBOSITY:-1}
    
    # Export for child processes
    export VUTF_VERBOSITY
    
    # Show initial verbosity level
    log_debug "Logging initialized at verbosity level: $(get_verbosity)"
}

# Cleanup function
cleanup_logging() {
    # Reset colors on exit
    echo -ne "${LOG_NC}"
}

# Set up trap for cleanup
trap cleanup_logging EXIT

# Auto-initialize if sourced
if [ "${BASH_SOURCE[0]}" != "${0}" ]; then
    init_logging
fi