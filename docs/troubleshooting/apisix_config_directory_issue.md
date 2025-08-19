# APISIX Configuration Files Created as Directories Issue

## Problem Description

During setup on some macOS systems, the APISIX configuration files (`config.yaml`, `dashboard.yaml`, `prometheus.yml`) are being created as directories instead of files. This causes:

1. Docker mount failures with error: "not a directory: unknown: Are you trying to mount a directory onto a file (or vice-versa)?"
2. `sed` errors: "in-place editing only works for regular files"
3. APISIX container fails to start

## Root Cause

This can happen when:
1. A previous failed setup attempt created these as directories
2. File system permissions or attributes cause `cp` or file creation to behave unexpectedly
3. Shell aliases or functions override standard commands

## Solution

### Immediate Fix

Run these commands before running setup:

```bash
cd /path/to/violentUTF

# Remove incorrectly created directories
rm -rf apisix/conf/config.yaml
rm -rf apisix/conf/dashboard.yaml
rm -rf apisix/conf/prometheus.yml

# Verify they're gone
ls -la apisix/conf/

# Run setup again
./setup_macos_new.sh --deepcleanup
./setup_macos_new.sh
```

### Prevention

The setup scripts have been updated to:
1. Check for and remove directories that should be files
2. Verify files are created correctly before proceeding
3. Provide clear error messages when this issue is detected

## Diagnostic Commands

If the issue persists:

```bash
# Check for shell aliases that might interfere
alias | grep -E "cp|mkdir|touch"

# Check file system
df -h .
mount | grep " on $(pwd)"

# Test file creation
touch test.txt && [ -f test.txt ] && echo "File creation works" || echo "File creation failed"
rm -f test.txt
```

## Additional Notes

- This issue is more likely to occur after an incomplete setup or when switching between different ViolentUTF versions
- Always use `--deepcleanup` when switching environments or after failed setups
- The setup script now includes automatic detection and cleanup of this issue