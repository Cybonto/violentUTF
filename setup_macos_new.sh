#!/usr/bin/env bash
# setup_macos.sh - Refactored ViolentUTF Setup Script
# This is the new modular version that calls specialized setup modules

# Script directory for path resolution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_MODULES_DIR="$SCRIPT_DIR/setup_macos_files"

# --- Global Variables ---
CLEANUP_MODE=false
DEEPCLEANUP_MODE=false
SHARED_NETWORK_NAME="vutf-network"
AI_TOKENS_FILE="ai-tokens.env"
SENSITIVE_VALUES=()
CREATED_AI_ROUTES=()

# --- Load all modules ---
load_modules() {
    local modules=(
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
    )
    
    for module in "${modules[@]}"; do
        if [ -f "$SETUP_MODULES_DIR/$module" ]; then
            source "$SETUP_MODULES_DIR/$module"
            echo "Loaded module: $module"
        else
            echo "Warning: Module $module not found in $SETUP_MODULES_DIR"
        fi
    done
    
    # Export variables for use in modules
    export SETUP_MODULES_DIR
    export SHARED_NETWORK_NAME
    export AI_TOKENS_FILE
}

# --- Help function ---
show_help() {
    echo "ViolentUTF macOS Setup Script (Refactored)"
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  (no options)     Normal setup - Install and configure ViolentUTF platform"
    echo "  --cleanup        Standard cleanup - Remove containers, volumes, and config files"
    echo "  --deepcleanup    Deep cleanup - Complete Docker environment reset"
    echo "  --help, -h       Show this help message"
    echo ""
    echo "This refactored version uses modular components in setup_macos_files/"
}

# --- Parse command line arguments ---
parse_arguments() {
    for arg in "$@"; do
        case $arg in
            --cleanup)
                CLEANUP_MODE=true
                shift
                ;;
            --deepcleanup)
                DEEPCLEANUP_MODE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo "Unknown option: $arg"
                show_help
                exit 1
                ;;
        esac
    done
}

# --- Main setup orchestration ---
main_setup() {
    echo "🚀 Starting ViolentUTF Setup (Refactored Version)"
    echo "📁 Using modules from: $SETUP_MODULES_DIR"
    
    # Phase 1: Prerequisites and Environment Preparation  
    echo ""
    echo "=== Phase 1: Prerequisites and Environment Preparation ==="
    verify_docker_setup
    handle_ssl_certificate_issues
    create_shared_network
    backup_existing_configs
    
    # Phase 2: AI Configuration Loading (CRITICAL: Must happen before env files)
    echo ""
    echo "=== Phase 2: AI Configuration Loading ==="
    # Create AI tokens template if it doesn't exist and load existing tokens
    create_ai_tokens_template
    load_ai_tokens  # This must happen before env file generation
    
    # Phase 3: Secret Generation (CRITICAL: Must happen before env files)
    echo ""
    echo "=== Phase 3: Secret Generation ==="
    generate_all_secrets  # All secrets must be generated upfront
    
    # Phase 4: Configuration File Creation (CRITICAL: After secrets, before services)
    echo ""
    echo "=== Phase 4: Configuration File Creation ==="
    generate_all_env_files  # Now we can create .env files with proper secrets
    
    # Phase 5: Service Deployment (CRITICAL: After all configs are ready)
    echo ""
    echo "=== Phase 5: Service Deployment ==="
    setup_keycloak
    setup_apisix
    setup_violentutf_api
    
    # Phase 5b: Service Stabilization (CRITICAL: Wait for all services to be fully ready)
    echo ""
    echo "=== Phase 5b: Service Stabilization ==="
    echo "⏳ Allowing services to fully stabilize before route configuration..."
    sleep 15  # Additional stabilization time
    
    # Verify core services are stable
    echo "🔍 Verifying core services are stable..."
    if ! curl -s --max-time 10 http://localhost:9080/health >/dev/null 2>&1; then
        echo "⚠️  APISIX gateway not responding, waiting longer..."
        sleep 10
    fi
    
    if ! curl -s --max-time 10 http://localhost:9080/api/v1/health >/dev/null 2>&1; then
        echo "⚠️  ViolentUTF API not responding, waiting longer..."
        sleep 10
    fi
    
    echo "✅ Core services appear stable, proceeding with route configuration"
    
    # Phase 6: Route and Integration Setup (CRITICAL: After services are running and stable)
    echo ""
    echo "=== Phase 6: Route and Integration Setup ==="
    configure_apisix_routes
    configure_openapi_routes
    setup_openapi_routes  # Setup OpenAPI provider routes (if configured)
    
    # AI Routes with enhanced readiness checking
    echo ""
    echo "=== Phase 6a: AI Provider Route Setup ==="
    echo "🤖 Setting up AI provider routes with enhanced readiness verification..."
    
    # Perform pre-flight checks for AI route setup
    if ai_route_preflight_check; then
        echo "✅ AI route pre-flight checks passed, proceeding with setup..."
        setup_openai_routes
        setup_anthropic_routes
        setup_ollama_routes
    else
        echo "❌ AI route pre-flight checks failed, skipping AI route setup"
        echo "💡 You can manually set up AI routes later by running:"
        echo "   source setup_macos_files/ai_providers_setup.sh"
        echo "   setup_openai_routes && setup_anthropic_routes"
    fi
    
    # Enhanced route verification and management
    echo ""
    echo "=== Phase 6b: Comprehensive Route Verification ==="
    comprehensive_ai_route_verification  # Enhanced AI route verification
    comprehensive_route_management       # Full route discovery and verification
    
    # Phase 7: Validation and Verification
    echo ""
    echo "=== Phase 7: Validation and Verification ==="
    verify_system_state
    validate_all_services
    
    # Phase 8: Cleanup and Restoration
    echo ""
    echo "=== Phase 8: Cleanup and Restoration ==="
    restore_user_configs
    
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "📋 ViolentUTF Platform Access:"
    echo "   • Application: http://localhost:8501"
    echo "     Login with: violentutf.web / [see password below]"
    echo "   • API Documentation: http://localhost:9080/api/docs"
    echo "   • Keycloak Admin: http://localhost:8080/auth/admin"
    echo "     Login with: admin / admin"
    
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
    else
        perform_cleanup
    fi
    
    echo "✅ Cleanup completed"
}

# --- Main execution ---
main() {
    # Load all modules first
    load_modules
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Execute based on mode
    if [ "$CLEANUP_MODE" = true ] || [ "$DEEPCLEANUP_MODE" = true ]; then
        main_cleanup
    else
        main_setup
    fi
}

# Execute main function with all arguments
main "$@"