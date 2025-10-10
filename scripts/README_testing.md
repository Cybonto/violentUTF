# Testing Scripts for ViolentUTF

This directory contains various testing scripts for different aspects of the ViolentUTF platform.

## 🔧 Production API Testing

### `test_production_endpoints.sh` 
**Primary production debugging script**
- **Purpose**: Comprehensive testing of FastAPI endpoints through APISIX in production
- **Use Case**: Debug empty model options and 404 conversation errors  
- **Features**: Interactive prompts, colored output, detailed analysis
- **Usage**: `./test_production_endpoints.sh`

### `quick_endpoint_test.sh`
**Fast production health check**  
- **Purpose**: 30-second test of critical endpoints
- **Use Case**: Quick verification after fixes or deployment
- **Usage**: `./quick_endpoint_test.sh <fastapi_token> <apisix_admin_key>`

## 🛠️ Setup and Development Testing

### `test_openapi_setup.sh`
**Setup function testing**
- **Purpose**: Test the OpenAPI route setup process directly
- **Use Case**: Debug setup script issues during development
- **Usage**: `./test_openapi_setup.sh` (requires ai-tokens.env)

### `test_gsai_auth_format.sh`  
**GSAi authentication testing**
- **Purpose**: Test different authentication header formats for GSAi API
- **Use Case**: Determine correct auth format when integrating new GSAi endpoints
- **Usage**: `./test_gsai_auth_format.sh` (requires ai-tokens.env)

## 📊 Other Testing Tools

### `check_api_scorers.py`
**API scorer validation**
- **Purpose**: Test scorer API endpoints and functionality
- **Use Case**: Validate scoring pipeline integrity

### `run_code_quality_checks.py` 
**Code quality automation**
- **Purpose**: Run comprehensive code quality checks
- **Use Case**: Pre-commit validation and CI/CD

## 🚀 Quick Start

For production issues:
```bash
# Quick health check
./scripts/quick_endpoint_test.sh $FASTAPI_TOKEN $APISIX_ADMIN_KEY

# Detailed debugging  
./scripts/test_production_endpoints.sh
```

For development setup issues:
```bash
# Test setup process
./scripts/test_openapi_setup.sh

# Test GSAi authentication  
./scripts/test_gsai_auth_format.sh
```

## 📋 Dependencies

All scripts require:
- `curl` - HTTP requests
- `jq` - JSON processing  
- Bash 4.0+ - Script execution

Production scripts additionally require:
- Valid FastAPI Bearer token
- APISIX admin API key
- Access to running ViolentUTF services

## 🎯 Script Selection Guide

| Problem | Script |
|---------|--------|  
| Empty model options in Configure Generator | `test_production_endpoints.sh` |
| 404 errors in test conversations | `test_production_endpoints.sh` |  
| Quick production health check | `quick_endpoint_test.sh` |
| Setup script not creating routes | `test_openapi_setup.sh` |
| GSAi integration auth issues | `test_gsai_auth_format.sh` |
| Code quality before commit | `run_code_quality_checks.py` |

## ⚠️ Security Notes

- Never commit tokens or API keys to repository
- Production scripts prompt for credentials interactively
- Test scripts may output sanitized credential info (first 20 chars)
- Always verify script contents before running in production

## 🔄 Maintenance

When adding new test scripts:
1. Place in `/scripts/` directory
2. Make executable with `chmod +x`
3. Update this README with description and usage
4. Follow naming convention: `test_<component>_<purpose>.sh`
5. Include help text and error handling