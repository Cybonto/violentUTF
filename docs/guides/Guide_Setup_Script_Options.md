# ViolentUTF Setup Script Options Quick Reference

## Overview

This guide provides a quick reference for all options available in the ViolentUTF setup scripts.

## Basic Setup Options

### Standard Setup
```bash
./setup_macos_new.sh              # Normal setup with default verbosity
sudo ./setup_linux_new.sh         # Linux requires sudo
setup_windows.bat                 # Windows batch script
```

### Verbosity Control
```bash
./setup_macos_new.sh --quiet      # Minimal output (errors only)
./setup_macos_new.sh              # Normal output (default)
./setup_macos_new.sh --verbose    # Detailed information
./setup_macos_new.sh --debug      # Full debugging output
```

Short forms:
```bash
./setup_macos_new.sh -q           # --quiet
./setup_macos_new.sh -v           # --verbose
./setup_macos_new.sh -d           # --debug
```

## Cleanup Options

### Standard Cleanup (Safe)
```bash
./setup_macos_new.sh --cleanup
```
**Preserves:**
- ✅ All credentials (.env files)
- ✅ AI tokens (ai-tokens.env)
- ✅ Application data (app_data/)
- ✅ Logs (violentutf_logs/, apisix/logs/)
- ✅ Docker volumes (databases)

**Removes:**
- ❌ Docker containers
- ❌ Configuration files (except .env)

### Dashboard Cleanup
```bash
./setup_macos_new.sh --cleanup-dashboard
```
**Removes only:**
- ❌ PyRIT memory databases
- ❌ Scoring results
- ❌ Execution history
- ❌ Dashboard logs

### Deep Cleanup (Complete Removal)
```bash
./setup_macos_new.sh --deepcleanup
```
⚠️ **WARNING**: Removes EVERYTHING including:
- ❌ All Docker data
- ❌ All credentials
- ❌ All logs and data

## Backup Options

### Create Backup
```bash
# Default backup with timestamp
./setup_macos_new.sh --backup
# Creates: ~/.violentutf/backups/vutf_backup_20240115_143022

# Named backup
./setup_macos_new.sh --backup production
# Creates: ~/.violentutf/backups/production_20240115_143022
```

### List Backups
```bash
./setup_macos_new.sh --list-backups
```

## Recovery Options

### Recover from Backup
```bash
# From latest temporary backup (/tmp/vutf_backup/)
./setup_macos_new.sh --recover

# From specific backup
./setup_macos_new.sh --recover ~/.violentutf/backups/production_20240115_143022
```

## Help Option

### Show Help
```bash
./setup_macos_new.sh --help
./setup_macos_new.sh -h
```

## Important Notes

### Backup Locations

1. **Temporary Backups** (`/tmp/vutf_backup/`)
   - Created automatically during cleanup
   - **Cleared when host system reboots**
   - Good for immediate recovery

2. **Permanent Backups** (`~/.violentutf/backups/`)
   - Created with `--backup` command
   - **Survives system reboots**
   - Recommended for important states

### Recommended Workflows

#### Safe Update
```bash
./setup_macos_new.sh --backup pre-update
./setup_macos_new.sh --cleanup
# Make changes
./setup_macos_new.sh
```

#### Complete Reset (Keep Credentials)
```bash
./setup_macos_new.sh --backup before-reset
./setup_macos_new.sh --deepcleanup
./setup_macos_new.sh --recover ~/.violentutf/backups/before-reset_*
./setup_macos_new.sh
```

#### Clear Test Data Only
```bash
./setup_macos_new.sh --cleanup-dashboard
```

## Environment Variables

You can also control verbosity with environment variables:
```bash
export VUTF_VERBOSITY=0  # Quiet
export VUTF_VERBOSITY=1  # Normal (default)
export VUTF_VERBOSITY=2  # Verbose
export VUTF_VERBOSITY=3  # Debug
```

## Platform-Specific Notes

### Linux
- Most commands require `sudo`
- Backups go to `/root/.violentutf/backups/` when using sudo

### Windows
- Use `setup_windows.bat` instead of `.sh` scripts
- PowerShell may be required for some features

### macOS
- No sudo required for most operations
- `/tmp/` is cleared on reboot

## Troubleshooting

If you encounter issues:
1. Check [Backup and Recovery Troubleshooting](../troubleshooting/Troubleshooting_Backup_Recovery.md)
2. Use `--debug` for detailed output
3. Check service status with `./check_services.sh`

## Related Documentation

- [Cleanup and Recovery Guide](./Guide_Cleanup_and_Recovery.md)
- [Setup Script Migration](../troubleshooting/setup_script_migration.md)
- [Troubleshooting Backup Recovery](../troubleshooting/Troubleshooting_Backup_Recovery.md)
