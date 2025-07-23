# Setup Script Migration and Troubleshooting Guide

## Overview
This guide helps users migrate from the old setup scripts to the new modular versions and troubleshoot common issues.

## Migration from Old to New Scripts

### macOS Migration
```bash
# Old script
./setup_macos.sh

# New script
./setup_macos_new.sh
```

### Linux Migration
```bash
# Old script
./setup_linux.sh

# New script  
sudo ./setup_linux_new.sh
```

## Key Differences

### 1. Credential Preservation
**Old Scripts**: 
- `--cleanup` removes all .env files
- Requires reconfiguration after cleanup
- No credential reuse

**New Scripts**:
- `--cleanup` preserves .env files
- Credentials automatically reused on re-setup
- Only `--deepcleanup` removes credentials

### 2. Verbosity Control
**Old Scripts**: 
- Limited output control
- No quiet mode for automation

**New Scripts**:
- Four verbosity levels: `--quiet`, default, `--verbose`, `--debug`
- Environment variable support: `VUTF_VERBOSITY`
- Better for CI/CD and automation

### 3. Modular Architecture
**Old Scripts**: 
- Monolithic single file (1000+ lines)
- Hard to maintain and debug

**New Scripts**:
- Modular design with separate function files
- Easier debugging and maintenance
- Platform-specific modules in `setup_*/files/`

## Common Migration Issues

### Issue 1: Permission Denied (Linux)
**Problem**: New Linux script requires sudo
```bash
# Error
./setup_linux_new.sh
Error: This script must be run as root or with sudo
```

**Solution**:
```bash
sudo ./setup_linux_new.sh
```

### Issue 2: Existing Credentials Not Found
**Problem**: Script doesn't find existing credentials after migration

**Solution**: The new scripts look for .env files in standard locations:
- `keycloak/.env`
- `apisix/.env`
- `violentutf/.env`
- `violentutf_api/fastapi_app/.env`

If your credentials are elsewhere, move them to these locations before running the new setup.

### Issue 3: Docker Group Issues (Linux)
**Problem**: User not in docker group after setup

**Solution**: The script adds users to docker group, but you need to log out and back in:
```bash
# Verify group membership
groups

# If docker not listed, manually add
sudo usermod -aG docker $USER

# Log out and back in
```

### Issue 4: Terminal Not Found (Linux)
**Problem**: Streamlit won't launch in new terminal
```
No suitable terminal emulator found
```

**Solution**: Install one of the supported terminals:
```bash
# Ubuntu/Debian
sudo apt install gnome-terminal

# Or alternatives
sudo apt install konsole     # KDE
sudo apt install xterm       # Basic
```

## Troubleshooting Cleanup Issues

### Standard Cleanup Not Working
If `--cleanup` isn't preserving credentials:

1. Check backup location:
```bash
ls -la /tmp/vutf_backup/
```

2. Manually backup credentials:
```bash
cp keycloak/.env /tmp/keycloak.env.backup
cp apisix/.env /tmp/apisix.env.backup
# etc.
```

3. Run cleanup and restore:
```bash
./setup_*_new.sh --cleanup
cp /tmp/*.env.backup .
```

### Deep Cleanup Recovery
If you accidentally ran `--deepcleanup`:

1. Check for backups:
```bash
ls -la /tmp/vutf_backup/
```

2. Restore from backup (if available):
```bash
cp /tmp/vutf_backup/*.env .
```

3. If no backup, you'll need to regenerate credentials by running setup again

## Debugging Setup Issues

### Enable Debug Mode
```bash
# Maximum verbosity
./setup_macos_new.sh --debug

# Or with environment variable
export VUTF_VERBOSITY=3
./setup_macos_new.sh
```

### Check Module Loading
Debug mode shows which modules are loaded:
```
🐛 DEBUG: Loaded module: logging_utils.sh
🐛 DEBUG: Loaded module: utils.sh
...
```

### Service-Specific Issues
The modular design allows debugging specific services:

1. Check the specific module in `setup_*/files/`
2. Look for the relevant function
3. Add debug logging if needed

## Best Practices for Migration

### 1. Backup First
```bash
# Backup all credentials
cp -r keycloak/.env keycloak/.env.backup
cp -r apisix/.env apisix/.env.backup
cp -r violentutf/.env violentutf/.env.backup
cp -r violentutf_api/fastapi_app/.env violentutf_api/fastapi_app/.env.backup
```

### 2. Test with Dry Run
Use `--verbose` to see what will happen without making changes

### 3. Gradual Migration
1. Run new script with existing deployment
2. Verify credential preservation with `--cleanup`
3. Test full cycle: cleanup → setup → cleanup → setup

### 4. Update CI/CD
Replace old script calls with new ones:
```yaml
# Old
- run: ./setup_linux.sh

# New
- run: sudo ./setup_linux_new.sh --quiet
```

## Getting Help

### Log Locations
- Setup logs: Check console output with `--verbose` or `--debug`
- Service logs: `docker logs <container_name>`
- Module errors: Check specific module file in `setup_*/files/`

### Common Commands
```bash
# Check what the script will do
./setup_*_new.sh --help

# Verify services after setup
./check_services.sh

# Check credentials were preserved
ls -la */.env

# Verify Docker networking
docker network ls | grep vutf-network
```

## Related Documentation
- [Credential Preservation](credential_preservation_setup.md)
- [Linux Setup Modernization](../guides/Guide_Linux_Setup_Modernization.md)
- [Database Cleanup Guide](../guides/Guide_Database_Cleanup.md)