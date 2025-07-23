#!/usr/bin/env bash
# setup_macos.sh - Refactored ViolentUTF Setup Script
# This is the new modular version that calls specialized setup modules

# Script directory for path resolution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_MODULES_DIR="$SCRIPT_DIR/setup_macos_files"

# --- Global Variables ---
CLEANUP_MODE=false
DEEPCLEANUP_MODE=false
CLEANUP_DASHBOARD_MODE=false
RECOVER_MODE=false
RECOVER_PATH=""
BACKUP_MODE=false
BACKUP_NAME=""
LIST_BACKUPS_MODE=false
SHARED_NETWORK_NAME="vutf-network"
AI_TOKENS_FILE="ai-tokens.env"
SENSITIVE_VALUES=()
CREATED_AI_ROUTES=()

# --- Command Line Argument Processing ---
show_help() {
    echo "ViolentUTF Setup Script for macOS"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help         Show this help message"
    echo "  -q, --quiet        Quiet mode (minimal output)"
    echo "  -v, --verbose      Verbose mode (detailed output)"
    echo "  -d, --debug        Debug mode (full debugging output)"
    echo ""
    echo "Cleanup Options:"
    echo "  --cleanup          Remove containers and configs (preserves data/logs/secrets)"
    echo "  --deepcleanup      Complete removal including all Docker data"
    echo "  --cleanup-dashboard Remove only dashboard data (scores, executions, databases)"
    echo "  --recover [path]   Recover from backup (optional: specify backup path)"
    echo "  --backup [name]    Create a permanent backup (optional: specify name)"
    echo "  --list-backups     List all available backups"
    echo ""
    echo "Verbosity Levels:"
    echo "  quiet    - Errors, warnings, and minimal progress only"
    echo "  normal   - Standard user experience (default)"
    echo "  verbose  - Detailed information and configuration details"
    echo "  debug    - Full debugging output with variable dumps"
    echo ""
    echo "Examples:"
    echo "  $0                 # Normal setup"
    echo "  $0 --quiet         # Quiet setup for automation"
    echo "  $0 --verbose       # Verbose setup with detailed output"
    echo "  $0 --debug         # Debug setup with full output"
    echo "  $0 --cleanup       # Clean up deployment (preserves data)"
    echo "  $0 --cleanup-dashboard # Clean up dashboard data only"
    echo "  $0 --recover       # Recover from latest backup"
    echo "  $0 --recover /path/to/backup # Recover from specific backup"
    echo "  $0 --backup        # Create backup with timestamp"
    echo "  $0 --backup prod   # Create backup named 'prod_timestamp'"
    echo "  $0 --list-backups  # Show all available backups"
    echo ""
}

# Process command line arguments
process_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -q|--quiet)
                export VUTF_VERBOSITY=0
                shift
                ;;
            -v|--verbose)
                export VUTF_VERBOSITY=2
                shift
                ;;
            -d|--debug)
                export VUTF_VERBOSITY=3
                shift
                ;;
            --cleanup)
                CLEANUP_MODE=true
                shift
                ;;
            --deepcleanup)
                DEEPCLEANUP_MODE=true
                shift
                ;;
            --cleanup-dashboard)
                CLEANUP_DASHBOARD_MODE=true
                shift
                ;;
            --recover)
                RECOVER_MODE=true
                # Check if next argument is a path
                if [[ $# -gt 1 && ! "$2" =~ ^-- ]]; then
                    RECOVER_PATH="$2"
                    shift
                fi
                shift
                ;;
            --backup)
                BACKUP_MODE=true
                # Check if next argument is a name
                if [[ $# -gt 1 && ! "$2" =~ ^-- ]]; then
                    BACKUP_NAME="$2"
                    shift
                fi
                shift
                ;;
            --list-backups)
                LIST_BACKUPS_MODE=true
                shift
                ;;
            *)
                echo "Unknown option: $1" >&2
                echo "Use --help for usage information" >&2
                exit 1
                ;;
        esac
    done
    
    # Set default verbosity if not specified
    export VUTF_VERBOSITY=${VUTF_VERBOSITY:-1}
}

# --- Load all modules ---
load_modules() {
    local modules=(
        "logging_utils.sh"
        "utils.sh"
        "env_management.sh" 
        "docker_setup.sh"
        "ssl_setup.sh"
        "keycloak_setup.sh"
        "apisix_setup.sh"
        "ai_providers_setup.sh"
        "openapi_setup.sh"
        "route_management.sh"
        "violentutf_api_setup.sh"
        "streamlit_setup.sh"
        "validation.sh"
        "cleanup.sh"
        "pre_download_packages.sh"
    )
    
    # Load logging utilities first (silently)
    if [ -f "$SETUP_MODULES_DIR/logging_utils.sh" ]; then
        source "$SETUP_MODULES_DIR/logging_utils.sh"
    fi
    
    log_detail "Loading setup modules..."
    for module in "${modules[@]}"; do
        if [ -f "$SETUP_MODULES_DIR/$module" ]; then
            # Skip logging_utils.sh since it's already loaded
            if [ "$module" != "logging_utils.sh" ]; then
                source "$SETUP_MODULES_DIR/$module"
                log_debug "Loaded module: $module"
            fi
        else
            log_warn "Module $module not found in $SETUP_MODULES_DIR"
        fi
    done
    log_detail "All modules loaded successfully"
    
    # Export variables for use in modules
    export SETUP_MODULES_DIR
    export SHARED_NETWORK_NAME
    export AI_TOKENS_FILE
}

# Use the enhanced show_help function defined above

# Use the enhanced process_arguments function defined above

# --- Main setup orchestration ---
main_setup() {
    log_progress "Starting ViolentUTF Setup (Refactored Version)"
    log_info "Using modules from: $SETUP_MODULES_DIR"
    
    # Phase 1: Prerequisites and Environment Preparation  
    log_phase "Phase 1: Prerequisites and Environment Preparation"
    verify_docker_setup
    handle_ssl_certificate_issues
    create_shared_network
    backup_existing_configs
    
    # Phase 2: AI Configuration Loading (CRITICAL: Must happen before env files)
    log_phase "Phase 2: AI Configuration Loading"
    # Create AI tokens template if it doesn't exist and load existing tokens
    create_ai_tokens_template
    load_ai_tokens  # This must happen before env file generation
    
    # Phase 3: Secret Generation (CRITICAL: Must happen before env files)
    log_phase "Phase 3: Secret Generation"
    generate_all_secrets  # All secrets must be generated upfront
    
    # Phase 4: Configuration File Creation (CRITICAL: After secrets, before services)
    log_phase "Phase 4: Configuration File Creation"
    generate_all_env_files  # Now we can create .env files with proper secrets
    update_fastapi_env      # Update FastAPI env with AI tokens and flags
    
    # Phase 5: Service Deployment (CRITICAL: After all configs are ready)
    log_phase "Phase 5: Service Deployment"
    
    # Pre-download large packages if network is slow
    if [ -f "$SETUP_MODULES_DIR/pre_download_packages.sh" ]; then
        source "$SETUP_MODULES_DIR/pre_download_packages.sh"
        pre_download_large_packages
    fi
    
    setup_keycloak
    setup_apisix
    setup_violentutf_api
    
    # Phase 5b: Service Stabilization (CRITICAL: Wait for all services to be fully ready)
    log_detail "Waiting for services to stabilize..."
    sleep 15  # Additional stabilization time
    
    # Verify core services are stable
    log_debug "Verifying core services are stable..."
    if ! curl -s --max-time 10 http://localhost:9080/health >/dev/null 2>&1; then
        log_warn "APISIX gateway not responding, waiting longer..."
        sleep 10
    fi
    
    if ! curl -s --max-time 10 http://localhost:9080/api/v1/health >/dev/null 2>&1; then
        log_warn "ViolentUTF API not responding, waiting longer..."
        sleep 10
    fi
    
    log_success "Core services appear stable, proceeding with route configuration"
    
    # Phase 6: Route and Integration Setup (CRITICAL: After services are running and stable)
    log_phase "Phase 6: Route and Integration Setup"
    configure_apisix_routes
    configure_openapi_routes
    
    # Initialize AI Gateway if present (important after deep cleanup)
    initialize_ai_gateway
    
    setup_openapi_routes  # Setup OpenAPI provider routes (if configured)
    
    # AI Routes with enhanced readiness checking
    log_detail "Setting up AI provider routes..."
    
    # Perform pre-flight checks for AI route setup
    if ai_route_preflight_check; then
        log_debug "AI route pre-flight checks passed, proceeding with setup..."
        setup_openai_routes
        setup_anthropic_routes
        setup_ollama_routes
    else
        log_warn "AI route pre-flight checks failed, skipping AI route setup"
        log_info "You can manually set up AI routes later by running:"
        log_info "   source setup_macos_files/ai_providers_setup.sh"
        log_info "   setup_openai_routes && setup_anthropic_routes"
    fi
    
    # Enhanced route verification and management
    log_detail "Verifying route configuration..."
    comprehensive_ai_route_verification  # Enhanced AI route verification
    comprehensive_route_management       # Full route discovery and verification
    
    # Phase 7: Validation and Verification
    log_detail "Validating system state..."
    verify_system_state
    validate_all_services
    
    # Phase 8: Cleanup and Restoration
    log_detail "Restoring user configurations..."
    restore_user_configs
    
    log_success "Setup completed successfully! 🎉"
    
    # Show access points in normal+ mode
    if should_log 1; then
        echo "📋 ViolentUTF Platform Access:"
        echo "   • Application: http://localhost:8501"
        echo "     Login with: violentutf.web / [see password below]"
        echo "   • API Documentation: http://localhost:9080/api/docs"
        echo "   • Keycloak Admin: http://localhost:8080/auth/admin"
        echo "     Login with: admin / admin"
    fi
    
    # Display all generated secrets
    display_generated_secrets
    
    # Launch Streamlit in a new terminal window
    launch_streamlit_in_new_terminal
}

# --- Cleanup orchestration ---
main_cleanup() {
    echo "🧹 Starting Cleanup Operations"
    
    if [ "$DEEPCLEANUP_MODE" = true ]; then
        perform_deep_cleanup
    elif [ "$CLEANUP_DASHBOARD_MODE" = true ]; then
        perform_dashboard_cleanup
    else
        perform_cleanup
    fi
    
    echo "✅ Cleanup completed"
}

# --- Recovery orchestration ---
main_recovery() {
    echo "🔄 Starting Recovery Operations"
    
    # Pass the backup path if specified
    if [ -n "$RECOVER_PATH" ]; then
        perform_recovery "$RECOVER_PATH"
    else
        perform_recovery
    fi
}

# --- Main execution ---
main() {
    # Load all modules first
    load_modules
    
    # Process command line arguments (includes verbosity settings)
    process_arguments "$@"
    
    # Execute based on mode
    if [ "$CLEANUP_MODE" = true ] || [ "$DEEPCLEANUP_MODE" = true ] || [ "$CLEANUP_DASHBOARD_MODE" = true ]; then
        main_cleanup
    elif [ "$RECOVER_MODE" = true ]; then
        main_recovery
    elif [ "$BACKUP_MODE" = true ]; then
        create_permanent_backup "$BACKUP_NAME"
    elif [ "$LIST_BACKUPS_MODE" = true ]; then
        list_backups
    else
        main_setup
    fi
}

# Execute main function with all arguments
main "$@"