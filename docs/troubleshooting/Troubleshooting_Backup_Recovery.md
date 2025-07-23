# Troubleshooting Backup and Recovery

## Overview

This guide helps resolve common issues with ViolentUTF's backup and recovery features.

## Common Issues and Solutions

### 1. "No backup found" after system reboot

**Problem**: Running `--recover` shows "No backup found in /tmp/vutf_backup" after your Mac/Linux machine rebooted.

**Cause**: The default temporary backup location `/tmp/vutf_backup/` is cleared when the host system (not Docker) reboots.

**Solutions**:
1. Check if you have permanent backups:
   ```bash
   ./setup_macos_new.sh --list-backups
   ```

2. If permanent backups exist, recover from them:
   ```bash
   ./setup_macos_new.sh --recover ~/.violentutf/backups/backup_name_*
   ```

3. **Prevention**: Always create permanent backups before critical operations:
   ```bash
   ./setup_macos_new.sh --backup important-state
   ./setup_macos_new.sh --deepcleanup
   # Even if system reboots here, backup is safe
   ./setup_macos_new.sh --recover ~/.violentutf/backups/important-state_*
   ```

### 2. Recovery doesn't restore database data

**Problem**: After recovery, credentials are restored but PyRIT memory and execution data are gone.

**Explanation**: This is expected behavior. Recovery restores:
- ✅ Credentials and secrets
- ✅ Configuration files
- ✅ Application preferences

But NOT:
- ❌ Docker volume data (databases)
- ❌ PyRIT conversation history
- ❌ Execution results

**Solution**: 
- For data preservation, use `--cleanup` instead of `--deepcleanup`
- `--cleanup` preserves Docker volumes with your data

### 3. Backup command not found

**Problem**: `--backup: command not found` or similar error.

**Solutions**:
1. Ensure you're using the correct script:
   ```bash
   # macOS
   ./setup_macos_new.sh --backup
   
   # Linux
   sudo ./setup_linux_new.sh --backup
   ```

2. Check script permissions:
   ```bash
   chmod +x setup_macos_new.sh
   ```

3. Verify you're in the ViolentUTF directory:
   ```bash
   pwd  # Should show /path/to/ViolentUTF
   ```

### 4. Cannot write to backup directory

**Problem**: "Permission denied" when creating backups.

**Solutions**:
1. Check home directory permissions:
   ```bash
   ls -la ~/.violentutf/
   ```

2. Create directory if missing:
   ```bash
   mkdir -p ~/.violentutf/backups
   chmod 755 ~/.violentutf/backups
   ```

3. For Linux with sudo:
   ```bash
   # Backups will be in root's home
   sudo ./setup_linux_new.sh --backup
   # Find them at: /root/.violentutf/backups/
   ```

### 5. Backup seems incomplete

**Problem**: Some files missing from backup.

**Diagnosis**:
1. Check what should be backed up:
   ```bash
   ls -la ai-tokens.env
   ls -la keycloak/.env
   ls -la apisix/.env
   ls -la violentutf/.env
   ls -la violentutf_api/fastapi_app/.env
   ```

2. Verify backup contents:
   ```bash
   ls -la ~/.violentutf/backups/latest_backup_*/
   ```

**Solution**: Manually copy any missing files:
```bash
cp ai-tokens.env ~/.violentutf/backups/manual_backup/
```

### 6. Recovery overwrites wrong files

**Problem**: Recovery places files in wrong locations.

**Solution**: Run recovery from ViolentUTF root directory:
```bash
cd /path/to/ViolentUTF
./setup_macos_new.sh --recover
```

## Understanding Backup Types

### Temporary Backups
- **Location**: `/tmp/vutf_backup/` (on host system)
- **Created by**: All cleanup operations automatically
- **Lifetime**: Until host system reboot
- **Use case**: Quick recovery after cleanup

### Permanent Backups
- **Location**: `~/.violentutf/backups/` (home directory)
- **Created by**: `--backup` command
- **Lifetime**: Until manually deleted
- **Use case**: Long-term storage, system reboot protection

## Best Practices

### 1. Before Deep Cleanup
Always create permanent backup:
```bash
# DON'T rely on automatic backup
./setup_macos_new.sh --deepcleanup  # Risk: /tmp/ cleared on reboot

# DO create permanent backup first
./setup_macos_new.sh --backup pre-cleanup
./setup_macos_new.sh --deepcleanup
./setup_macos_new.sh --recover ~/.violentutf/backups/pre-cleanup_*
```

### 2. Regular Backups
Create named backups at milestones:
```bash
./setup_macos_new.sh --backup after-config
./setup_macos_new.sh --backup production-ready
./setup_macos_new.sh --backup before-upgrade
```

### 3. Backup Verification
After creating backup:
```bash
# List backups
./setup_macos_new.sh --list-backups

# Check specific backup
ls -la ~/.violentutf/backups/backup_name_*/
cat ~/.violentutf/backups/backup_name_*/backup_info.txt
```

## Recovery Strategies

### From Temporary Backup (immediate recovery)
```bash
./setup_macos_new.sh --cleanup
./setup_macos_new.sh --recover  # Uses /tmp/vutf_backup/
```

### From Permanent Backup (safe recovery)
```bash
./setup_macos_new.sh --list-backups
./setup_macos_new.sh --recover ~/.violentutf/backups/chosen_backup_*/
```

### Manual Recovery (if automated fails)
```bash
# 1. Find backup
ls ~/.violentutf/backups/

# 2. Copy files manually
cp ~/.violentutf/backups/backup_*/ai-tokens.env .
cp ~/.violentutf/backups/backup_*/keycloak.env keycloak/.env
# ... etc

# 3. Run setup
./setup_macos_new.sh
```

## Platform-Specific Notes

### macOS
- `/tmp/` typically cleared on reboot
- Backups in `~/.violentutf/` persist

### Linux
- `/tmp/` handling varies by distribution
- Some systems clear on reboot, others don't
- When using sudo, backups go to `/root/.violentutf/`

### Docker Desktop
- Restarting Docker does NOT affect `/tmp/`
- Only host system reboot clears `/tmp/`

## Getting Help

If issues persist:
1. Check backup location exists: `ls -la ~/.violentutf/backups/`
2. Verify you're in correct directory: `pwd`
3. Check script permissions: `ls -la setup_*.sh`
4. Review error messages carefully
5. Create manual backup of critical files before experimentation

## Related Documentation

- [Cleanup and Recovery Guide](../guides/Guide_Cleanup_and_Recovery.md)
- [Setup Guide](../guides/Guide_Setup.md)
- [Security Best Practices](../guides/Guide_Security.md)