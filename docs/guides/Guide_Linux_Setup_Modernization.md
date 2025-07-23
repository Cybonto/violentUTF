# Linux Setup Modernization Guide

## Overview
The Linux setup has been modernized to match the macOS setup feature parity, including credential preservation, modular architecture, and enhanced verbosity control.

## New Features

### 1. Modular Architecture
The monolithic `setup_linux.sh` script has been replaced with `setup_linux_new.sh` which uses modular components stored in `setup_linux_files/`:

- **logging_utils.sh** - Logging functions with verbosity control
- **utils.sh** - Common utilities including credential management
- **env_management.sh** - Environment file creation and management
- **docker_setup.sh** - Docker installation and configuration
- **keycloak_setup.sh** - Keycloak setup and configuration
- **apisix_setup.sh** - APISIX gateway setup
- **ai_providers_setup.sh** - AI provider route configuration
- **violentutf_api_setup.sh** - FastAPI service setup
- **streamlit_setup.sh** - Streamlit application setup
- **cleanup.sh** - Cleanup operations with credential preservation
- **validation.sh** - Service validation functions
- **route_management.sh** - Route configuration management

### 2. Credential Preservation
The setup now preserves credentials during cleanup operations:
- `.env` files are NOT removed during standard cleanup
- Only `--deepcleanup` will remove all credentials
- Credentials are automatically backed up before cleanup
- Existing credentials are reused on subsequent setups

### 3. Verbosity Control
Four verbosity levels are now supported:
- `--quiet` (-q) - Minimal output (errors/warnings only)
- Default - Standard user experience
- `--verbose` (-v) - Detailed information
- `--debug` (-d) - Full debugging output

### 4. Enhanced Linux Support
- Automatic detection of Linux distribution
- Support for multiple package managers (apt, yum, dnf, zypper, pacman)
- Automatic Docker installation if not present
- Terminal emulator detection for launching Streamlit

## Usage

### Basic Setup
```bash
sudo ./setup_linux_new.sh
```

### Setup with Verbosity
```bash
# Quiet mode
sudo ./setup_linux_new.sh --quiet

# Verbose mode
sudo ./setup_linux_new.sh --verbose

# Debug mode
sudo ./setup_linux_new.sh --debug
```

### Cleanup Operations
```bash
# Standard cleanup (preserves credentials)
sudo ./setup_linux_new.sh --cleanup

# Deep cleanup (removes everything)
sudo ./setup_linux_new.sh --deepcleanup

# Dashboard cleanup only
sudo ./setup_linux_new.sh --cleanup-dashboard
```

## Key Differences from Old Setup

### Old Setup (setup_linux.sh)
- Monolithic script (1000+ lines)
- No credential preservation
- Limited verbosity control
- No modular structure

### New Setup (setup_linux_new.sh)
- Modular architecture
- Credential preservation
- Full verbosity control
- Better error handling
- Automatic backup/restore

## Migration Guide

### For Users
1. The new setup is backward compatible
2. Run `sudo ./setup_linux_new.sh` instead of `sudo ./setup_linux.sh`
3. Your existing credentials will be preserved
4. No need to reconfigure after cleanup

### For Developers
1. Modifications should be made to individual modules in `setup_linux_files/`
2. Follow the same patterns as macOS setup modules
3. Use logging functions for consistent output
4. Test with different verbosity levels

## Platform-Specific Considerations

### Docker Installation
The setup automatically installs Docker based on your Linux distribution:
- Ubuntu/Debian: Uses Docker's official APT repository
- RHEL/CentOS/Fedora: Uses Docker's official YUM repository
- Arch/Manjaro: Uses pacman
- openSUSE: Uses zypper

### Terminal Emulators
The setup attempts to launch Streamlit in a new terminal window using:
1. gnome-terminal (GNOME)
2. konsole (KDE)
3. xfce4-terminal (XFCE)
4. xterm (fallback)
5. x-terminal-emulator (generic)

If no suitable terminal is found, manual launch instructions are provided.

## Troubleshooting

### Permission Issues
The setup requires root/sudo access:
```bash
sudo ./setup_linux_new.sh
```

### Docker Group
The setup automatically adds the current user to the docker group. You may need to log out and back in for this to take effect.

### Credential Recovery
If you accidentally run `--deepcleanup`, credentials are backed up to `/tmp/vutf_backup/` during the session and can be manually recovered if needed.

## Best Practices

1. **Always use standard cleanup** (`--cleanup`) for regular maintenance
2. **Only use deep cleanup** (`--deepcleanup`) when you need to completely reset
3. **Back up your ai-tokens.env** file externally as it contains your API keys
4. **Use verbose mode** (`--verbose`) when troubleshooting issues
5. **Check service health** with validation functions after setup

## Future Enhancements

The modular structure allows for easy addition of new features:
- Additional AI provider support
- Custom authentication providers
- Enhanced monitoring and logging
- Automated testing integration