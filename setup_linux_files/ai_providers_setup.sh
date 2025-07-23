#!/usr/bin/env bash
# ai_providers_setup.sh - AI provider route configuration

# Function to setup AI provider routes
setup_ai_provider_routes() {
    log_detail "Setting up AI provider routes..."
    
    # Load AI tokens
    if [ -f "$AI_TOKENS_FILE" ]; then
        source "$AI_TOKENS_FILE"
    else
        log_warn "AI tokens file not found, skipping AI provider setup"
        return 0
    fi
    
    # Setup routes for enabled providers
    if [ "${OLLAMA_ENABLED:-false}" = "true" ]; then
        setup_ollama_routes
    fi
    
    if [ "${OPENAI_ENABLED:-false}" = "true" ]; then
        setup_openai_routes
    fi
    
    if [ "${ANTHROPIC_ENABLED:-false}" = "true" ]; then
        setup_anthropic_routes
    fi
    
    log_success "AI provider routes configured"
}

# Function to setup Ollama routes
setup_ollama_routes() {
    log_detail "Setting up Ollama routes..."
    
    # Check if Ollama is running
    if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        log_warn "Ollama is not running at localhost:11434"
        return 1
    fi
    
    log_success "Ollama routes configured"
}

# Function to setup OpenAI routes
setup_openai_routes() {
    log_detail "Setting up OpenAI routes..."
    
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
        log_warn "OpenAI API key not configured"
        return 1
    fi
    
    log_success "OpenAI routes configured"
}

# Function to setup Anthropic routes
setup_anthropic_routes() {
    log_detail "Setting up Anthropic routes..."
    
    if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
        log_warn "Anthropic API key not configured"
        return 1
    fi
    
    log_success "Anthropic routes configured"
}