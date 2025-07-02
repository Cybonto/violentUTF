# setup_macos.sh Refactoring Plan

## Overview
The current `setup_macos.sh` file is 5,687 lines long with 106+ functions. This refactoring will break it into smaller, modular files within the `setup_macos_files/` directory for better maintainability, readability, and testing.

## Current File Analysis
- **Total Lines**: 5,687
- **Functions**: 106+
- **External Dependencies**: 
  - `apisix/configure_routes.sh`
  - Various `.env` files in different directories
  - Docker Compose files in subdirectories
  - Template files and configuration files

## Refactoring Structure

### Main Setup File
- **File**: `setup_macos.sh` (new streamlined version)
- **Purpose**: Entry point that orchestrates the setup process
- **Size**: ~200-300 lines
- **Functions**: Main flow control, argument parsing, high-level orchestration

### Modular Files in `setup_macos_files/`

#### 1. Core Utilities (`utils.sh`)
- **Purpose**: Common utility functions used across modules
- **Functions**:
  - `generate_random_string()`
  - `replace_in_file()`
  - `backup_and_prepare_config()`
  - `graceful_streamlit_shutdown()`
  - `ensure_network_in_compose()`
  - `test_network_connectivity()`
  - `run_test()`

#### 2. Environment Management (`env_management.sh`)
- **Purpose**: Handle all .env file creation, backup, and restoration
- **Functions**:
  - `create_ai_tokens_template()`
  - `load_ai_tokens()`
  - `update_fastapi_env()`
  - `backup_user_configs()`
  - `restore_user_configs()`
  - `create_env_files()`

#### 3. Docker and Network Setup (`docker_setup.sh`)
- **Purpose**: Docker network creation, container management
- **Functions**:
  - `create_shared_network()`
  - `verify_docker_setup()`
  - `cleanup_containers()`
  - `deep_cleanup_docker()`

#### 4. SSL and Certificate Handling (`ssl_setup.sh`)
- **Purpose**: Handle Zscaler/corporate proxy SSL certificates
- **Functions**:
  - `handle_ssl_certificate_issues()`
  - `install_zscaler_certs()`
  - `configure_ssl_bypass()`

#### 5. Keycloak Setup (`keycloak_setup.sh`)
- **Purpose**: Complete Keycloak configuration and realm setup
- **Functions**:
  - `setup_keycloak()`
  - `get_keycloak_admin_token()`
  - `make_api_call()`
  - `import_keycloak_realm()`
  - `disable_ssl_requirements()`

#### 6. APISIX Setup (`apisix_setup.sh`)
- **Purpose**: APISIX gateway configuration and route setup
- **Functions**:
  - `setup_apisix()`
  - `configure_apisix_routes()`
  - `wait_for_apisix_ready()`
  - `verify_apisix_config()`

#### 7. AI Providers Setup (`ai_providers_setup.sh`)
- **Purpose**: AI provider route configuration (OpenAI, Anthropic, etc.)
- **Functions**:
  - `setup_openai_routes()`
  - `setup_anthropic_routes()`
  - `setup_ollama_routes()`
  - `setup_open_webui_routes()`
  - `create_apisix_consumer()`
  - `test_ai_routes()`

#### 8. OpenAPI Integration (`openapi_setup.sh`)
- **Purpose**: OpenAPI specification fetching and route creation
- **Functions**:
  - `fetch_openapi_spec()`
  - `validate_openapi_spec()`
  - `parse_openapi_endpoints()`
  - `create_openapi_routes()`
  - `validate_openapi_providers()`

#### 9. ViolentUTF API Setup (`violentutf_api_setup.sh`)
- **Purpose**: FastAPI service configuration and startup
- **Functions**:
  - `setup_violentutf_api()`
  - `configure_fastapi_env()`
  - `verify_api_health()`

#### 10. Validation and Testing (`validation.sh`)
- **Purpose**: System validation and health checks
- **Functions**:
  - `verify_system_state()`
  - `run_integration_tests()`
  - `validate_all_services()`
  - `check_service_connectivity()`

#### 11. Cleanup Operations (`cleanup.sh`)
- **Purpose**: All cleanup and maintenance operations
- **Functions**:
  - `perform_cleanup()`
  - `perform_deep_cleanup()`
  - `cleanup_specific_service()`

## File Moves Required

### Files to Move to `setup_macos_files/`
1. **`apisix/configure_routes.sh`** → **`setup_macos_files/apisix_configure_routes.sh`**
   - Update all references in main setup
   - Modify path references within the script

### Template and Configuration Files
- Create `setup_macos_files/templates/` for configuration templates
- Move any inline configuration generation to separate template files

## Dependencies and Path Updates

### Current External File References
1. **APISIX**:
   - `apisix/configure_routes.sh` → Update to `setup_macos_files/apisix_configure_routes.sh`
   - `apisix/conf/` directory access → Keep relative paths
   - `apisix/.env` → Keep relative paths

2. **Keycloak**:
   - `keycloak/.env` → Keep relative paths
   - `keycloak/realm-export.json` → Keep relative paths
   - `keycloak/docker-compose.yml` → Keep relative paths

3. **ViolentUTF**:
   - `violentutf/.env` → Keep relative paths
   - `violentutf_api/fastapi_app/.env` → Keep relative paths

### Environment Variables and Paths
- All scripts will be called from the main directory
- Use `$SCRIPT_DIR` variable for consistent path resolution
- Maintain relative paths to service directories (keycloak/, apisix/, etc.)

## Refactoring Steps

### Phase 1: Infrastructure Setup
1. Create `setup_macos_files/` directory
2. Create modular script files with function stubs
3. Move `apisix/configure_routes.sh` to `setup_macos_files/`

### Phase 2: Function Migration
1. Extract utility functions to `utils.sh`
2. Extract environment management to `env_management.sh`
3. Extract Docker operations to `docker_setup.sh`
4. Extract SSL handling to `ssl_setup.sh`

### Phase 3: Service Setup Migration
1. Extract Keycloak setup to `keycloak_setup.sh`
2. Extract APISIX setup to `apisix_setup.sh`
3. Extract AI providers to `ai_providers_setup.sh`
4. Extract OpenAPI handling to `openapi_setup.sh`

### Phase 4: Validation and Cleanup
1. Extract validation functions to `validation.sh`
2. Extract cleanup operations to `cleanup.sh`
3. Update main `setup_macos.sh` to orchestrate modules

### Phase 5: Testing and Integration
1. Test each module independently
2. Test integrated setup process
3. Verify all path references work correctly
4. Update documentation

## Benefits of Refactoring

### Maintainability
- Smaller, focused files easier to understand and modify
- Clear separation of concerns
- Easier to debug specific components

### Reusability
- Individual modules can be used independently
- Functions can be tested in isolation
- Easier to extend with new providers or services

### Reliability
- Reduced complexity in each file
- Better error handling per module
- Easier to implement proper logging

### Development
- Multiple developers can work on different modules
- Easier to add new features without affecting existing code
- Better version control with smaller change sets

## File Size Estimates (After Refactoring)

- `setup_macos.sh`: ~250 lines
- `utils.sh`: ~400 lines
- `env_management.sh`: ~300 lines
- `docker_setup.sh`: ~200 lines
- `ssl_setup.sh`: ~200 lines
- `keycloak_setup.sh`: ~500 lines
- `apisix_setup.sh`: ~400 lines
- `ai_providers_setup.sh`: ~800 lines
- `openapi_setup.sh`: ~600 lines
- `violentutf_api_setup.sh`: ~300 lines
- `validation.sh`: ~400 lines
- `cleanup.sh`: ~400 lines

**Total**: ~4,600 lines (reduction from 5,687 lines due to eliminated redundancy)

## Implementation Timeline

1. **Phase 1-2**: 2-3 hours (Infrastructure and basic functions)
2. **Phase 3**: 3-4 hours (Service setup migration)
3. **Phase 4**: 2-3 hours (Validation and cleanup)
4. **Phase 5**: 2-3 hours (Testing and integration)

**Total Estimated Time**: 10-13 hours

## Risk Mitigation

- Keep original `setup_macos.sh` as `setup_macos_original.sh` backup
- Test each phase incrementally
- Maintain compatibility with existing file structure
- Document all path changes clearly