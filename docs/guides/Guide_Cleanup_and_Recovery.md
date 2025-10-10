# ViolentUTF Cleanup and Recovery Guide

## Overview

This guide explains the cleanup and recovery options available in ViolentUTF's setup scripts. These features help you manage your deployment, preserve important data, and recover from backups when needed.

## Cleanup Options

### 1. Standard Cleanup (`--cleanup`)

The standard cleanup option removes containers and configuration files while **preserving all important data**:

```bash
./setup_macos_new.sh --cleanup
```

**What is preserved:**
- ✅ All secrets and credentials (.env files)
- ✅ AI tokens (ai-tokens.env)
- ✅ Application data (app_data/)
- ✅ Logs (violentutf_logs/, apisix/logs/)
- ✅ Docker volumes (databases)
- ✅ PyRIT memory databases
- ✅ Execution history and scores

**What is removed:**
- ❌ Docker containers
- ❌ Configuration files (except .env)
- ❌ Temporary files

**Use this when:** You want to clean up the deployment but keep all your data and credentials for a fresh setup.

### 2. Dashboard Cleanup (`--cleanup-dashboard`)

This option specifically targets dashboard data while preserving everything else:

```bash
./setup_macos_new.sh --cleanup-dashboard
```

**What is removed:**
- ❌ PyRIT memory databases
- ❌ Scoring results
- ❌ Execution history
- ❌ Dashboard analytics data
- ❌ Execution logs

**What is preserved:**
- ✅ All credentials and secrets
- ✅ Docker containers (restarted)
- ✅ Configuration files
- ✅ Application structure

**Use this when:** You want to clear test data and start fresh with scoring/execution history.

### 3. Deep Cleanup (`--deepcleanup`)

⚠️ **WARNING:** This is a complete removal of everything!

```bash
./setup_macos_new.sh --deepcleanup
```

**What is removed:**
- ❌ All Docker containers, images, and volumes
- ❌ All configuration files
- ❌ All .env files with credentials
- ❌ All logs
- ❌ All application data

**Important:** A backup is automatically created before deep cleanup.

**Use this when:** You want to completely remove ViolentUTF from your system.

## Backup and Recovery

### Automatic Backups

All cleanup operations automatically create backups in `/tmp/vutf_backup/` before removing anything. These backups include:
- AI tokens configuration
- All .env files with credentials
- Streamlit secrets
- Custom APISIX routes
- Application data (if requested)

⚠️ **Important**: `/tmp/vutf_backup/` is on your HOST system (not Docker) and may be cleared when your Mac/Linux machine reboots. For permanent backups that survive host reboots, use the `--backup` option.

### Creating Permanent Backups

You can create permanent backups that are stored in `~/.violentutf/backups/` (in your home directory):

```bash
# Create backup with timestamp
./setup_macos_new.sh --backup
# Creates: ~/.violentutf/backups/vutf_backup_20240115_143022

# Create backup with custom name
./setup_macos_new.sh --backup production
# Creates: ~/.violentutf/backups/production_20240115_143022

# List all available backups
./setup_macos_new.sh --list-backups
```

✅ **These backups survive host system reboots** because they're stored in your home directory, not in `/tmp/`.

### Recovery Options

#### 1. Recover from Latest Backup

```bash
./setup_macos_new.sh --recover
```

This will restore from the most recent backup in `/tmp/vutf_backup/`.

⚠️ **Note**: This temporary backup location may be empty if your system has rebooted since the cleanup. In that case, use a permanent backup instead.

#### 2. Recover from Specific Backup

```bash
# Recover from a permanent backup
./setup_macos_new.sh --recover ~/.violentutf/backups/production_20240115_143022

# Recover from a custom location
./setup_macos_new.sh --recover /path/to/backup/directory
```

#### 3. What Gets Restored

The recovery process restores:
- ✅ AI tokens (ai-tokens.env)
- ✅ Keycloak credentials
- ✅ APISIX credentials
- ✅ ViolentUTF credentials
- ✅ FastAPI credentials
- ✅ Streamlit secrets
- ✅ Custom APISIX routes
- ✅ Application data (if backed up)

## Common Scenarios

### Scenario 1: Update Configuration

```bash
# 1. Clean up current deployment (preserves data)
./setup_macos_new.sh --cleanup

# 2. Make configuration changes
# Edit configuration files as needed

# 3. Run setup again (reuses existing secrets)
./setup_macos_new.sh
```

### Scenario 2: Fresh Start with Same Credentials

```bash
# 1. Create a permanent backup (IMPORTANT: Do this first!)
./setup_macos_new.sh --backup before-reset

# 2. Deep clean everything
./setup_macos_new.sh --deepcleanup

# 3. Recover credentials from permanent backup
# (Safer than relying on /tmp/ which may be cleared on reboot)
./setup_macos_new.sh --recover ~/.violentutf/backups/before-reset_*

# 4. Run fresh setup with restored credentials
./setup_macos_new.sh
```

### Scenario 3: Clear Test Data

```bash
# Clean dashboard data only
./setup_macos_new.sh --cleanup-dashboard
```

### Scenario 4: Move to Another Machine

```bash
# On source machine - create backup
./setup_macos_new.sh --backup transfer

# Copy backup directory to new machine
scp -r ~/.violentutf/backups/transfer_* user@newmachine:~/

# On new machine - recover and setup
./setup_macos_new.sh --recover ~/transfer_*/
./setup_macos_new.sh
```

## Best Practices

1. **Regular Backups**: Create backups before major changes
   ```bash
   ./setup_macos_new.sh --backup pre-update
   ```

2. **Named Backups**: Use descriptive names for important backups
   ```bash
   ./setup_macos_new.sh --backup production-stable
   ```

3. **Check Backups**: List and verify backups periodically
   ```bash
   ./setup_macos_new.sh --list-backups
   ```

4. **Preserve Data**: Use standard cleanup (`--cleanup`) instead of deep cleanup unless necessary

5. **Document Changes**: Keep notes about what each backup represents

## Troubleshooting

### "No backup found"
- Check if backup exists: `ls -la /tmp/vutf_backup/`
- List permanent backups: `./setup_macos_new.sh --list-backups`
- Ensure you're in the correct directory

### "Recovery failed"
- Check file permissions in backup directory
- Ensure backup directory structure is intact
- Try recovering individual files manually

### Data Still Present After Cleanup
- Standard cleanup preserves data by design
- Use `--cleanup-dashboard` to remove execution data
- Use `--deepcleanup` for complete removal

### Cannot Find Docker Volumes
- List volumes: `docker volume ls | grep -E '(keycloak|apisix|violentutf)'`
- Volumes are preserved in standard cleanup
- Only `--deepcleanup` removes volumes

## Security Notes

1. **Backup Security**: Backups contain sensitive credentials. Protect backup directories appropriately.

2. **Credential Handling**: The setup script automatically generates secure passwords if none exist.

3. **Recovery Safety**: Recovery always asks for confirmation before overwriting existing files.

## Important Technical Details

### Backup Locations

1. **Temporary Backups** (`/tmp/vutf_backup/`)
   - Created automatically during cleanup operations
   - Located on HOST system (not inside Docker)
   - **May be cleared when your Mac/Linux machine reboots**
   - Good for immediate recovery after cleanup

2. **Permanent Backups** (`~/.violentutf/backups/`)
   - Created with `--backup` command
   - Located in your home directory
   - **Survives host system reboots**
   - Recommended for important backups

### Deep Cleanup Considerations

When using `--deepcleanup`:
1. Creates automatic backup in `/tmp/vutf_backup/` first
2. Removes ALL Docker volumes (databases are lost)
3. Recovery restores credentials but NOT database data
4. Always create a permanent backup first for safety

## Command Reference

| Command | Description |
|---------|-------------|
| `--cleanup` | Standard cleanup (preserves data/logs/secrets) |
| `--cleanup-dashboard` | Remove dashboard data only |
| `--deepcleanup` | Complete removal of everything |
| `--backup [name]` | Create permanent backup |
| `--list-backups` | Show all available backups |
| `--recover [path]` | Restore from backup |

## Related Documentation

- [Setup Guide](./Guide_Setup.md)
- [Troubleshooting Guide](../troubleshooting/Troubleshooting_Setup.md)
- [Security Guide](./Guide_Security.md)
