# ViolentUTF Database Cleanup Guide

This guide explains how to properly clean up data in ViolentUTF, including Dashboard data (orchestrator execution results) and PyRIT memory data.

## Overview

ViolentUTF uses a dual database architecture to separate concerns between application configuration/results and framework execution data:

### Database Architecture

1. **ViolentUTF SQLite Database** (`/app/app_data/violentutf.db`)
   - **Purpose**: Application configuration and persistent results
   - **Content**: 
     - Orchestrator execution results (what you see in the Dashboard)
     - Generator, scorer, dataset, and converter configurations
     - API keys and user sessions
   - **Location**: Inside Docker container `violentutf_api`
   - **Persistence**: Survives across sessions

2. **PyRIT DuckDB Databases** (`pyrit_memory_<hash>.db`)
   - **Purpose**: Framework execution data (temporary)
   - **Content**:
     - Active conversation flows
     - Prompt/response pairs during execution
     - Scoring results during execution
   - **Location**: `/app_data/violentutf/` (user-specific files)
   - **Persistence**: Can be cleared after analysis

## Dashboard Data Cleanup

Dashboard data comes from completed orchestrator executions stored in the SQLite database.

### Viewing Dashboard Statistics

```bash
# Check current statistics (Docker deployment)
docker exec violentutf_api python3 -c "
import sqlite3
conn = sqlite3.connect('/app/app_data/violentutf.db')
cursor = conn.cursor()

print('Dashboard Data Statistics:')
print('=' * 40)

# Total executions
cursor.execute('SELECT COUNT(*) FROM orchestrator_executions')
print(f'Total Executions: {cursor.fetchone()[0]}')

# By status
cursor.execute('SELECT status, COUNT(*) FROM orchestrator_executions GROUP BY status')
print('\\nBy Status:')
for status, count in cursor.fetchall():
    print(f'  {status}: {count}')

conn.close()
"
```

### Using the Dashboard Cleanup Script

ViolentUTF includes a dedicated cleanup script for Dashboard data:

```bash
# Make the script executable
chmod +x scripts/cleanup_dashboard_data.py

# Show statistics
python3 scripts/cleanup_dashboard_data.py --docker --stats

# Preview what would be deleted (dry run)
python3 scripts/cleanup_dashboard_data.py --docker --older-than 30 --dry-run

# Delete executions older than 30 days
python3 scripts/cleanup_dashboard_data.py --docker --older-than 30

# Delete failed executions
python3 scripts/cleanup_dashboard_data.py --docker --status failed

# Delete by orchestrator name (partial match)
python3 scripts/cleanup_dashboard_data.py --docker --orchestrator-name "test_"
```

### Cleanup Options

- `--older-than <days>`: Delete executions older than specified days
- `--status <status>`: Delete executions with specific status (pending/running/completed/failed/cancelled)
- `--orchestrator-name <name>`: Delete executions from specific orchestrator (partial match)
- `--dry-run`: Preview what would be deleted without actually deleting
- `--docker`: Access database inside Docker container (required for standard deployments)

## PyRIT Memory Cleanup

PyRIT memory databases store temporary execution data and can grow large during extensive testing.

### Understanding PyRIT Memory

- Each user has their own DuckDB database file
- Files are named `pyrit_memory_<user_hash>.db`
- Contains prompts, responses, and scores from active/recent executions
- Can be safely cleaned up after execution analysis is complete

### Manual PyRIT Memory Cleanup

```bash
# List PyRIT memory databases
ls -lh ./violentutf/app_data/violentutf/pyrit_memory_*.db

# Check size of databases
du -sh ./violentutf/app_data/violentutf/pyrit_memory_*.db

# Remove specific user's database (if no longer needed)
rm ./violentutf/app_data/violentutf/pyrit_memory_<hash>.db

# Remove all PyRIT memory databases (CAUTION: removes all execution data)
rm ./violentutf/app_data/violentutf/pyrit_memory_*.db
```

### PyRIT Memory Best Practices

1. **Regular Cleanup**: PyRIT memory is meant for temporary execution data
2. **Post-Analysis**: Clean up after analyzing execution results
3. **User-Specific**: Each user's data is isolated, clean up only inactive users
4. **Backup First**: Consider backing up before bulk deletion

## Automated Cleanup

### Scheduled Dashboard Cleanup

Add to crontab for regular maintenance:

```bash
# Weekly cleanup of executions older than 90 days
0 2 * * 0 /usr/bin/python3 /path/to/ViolentUTF/scripts/cleanup_dashboard_data.py --docker --older-than 90

# Monthly cleanup of failed executions
0 3 1 * * /usr/bin/python3 /path/to/ViolentUTF/scripts/cleanup_dashboard_data.py --docker --status failed
```

### PyRIT Memory Maintenance

```bash
# Script to clean PyRIT databases older than 30 days
#!/bin/bash
find ./violentutf/app_data/violentutf -name "pyrit_memory_*.db" -mtime +30 -exec rm {} \;
```

## Important Considerations

### Data Relationships

1. **Dashboard Cleanup**: Removes execution results visible in the Dashboard
2. **PyRIT Cleanup**: Removes temporary execution data, not Dashboard results
3. **Independent Systems**: Cleaning one doesn't affect the other

### Safety Precautions

1. **Always Dry Run First**: Use `--dry-run` to preview deletions
2. **Backup Important Data**: Create backups before bulk operations
3. **Check Active Users**: Don't delete PyRIT memory for active sessions
4. **Verify Container**: Ensure correct Docker container when using `--docker`

### Recovery

- **Dashboard Data**: No built-in recovery after deletion (backup SQLite file if needed)
- **PyRIT Memory**: Data is execution-specific and typically reproducible by re-running tests

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Ensure proper permissions on database files
   - Run with appropriate user privileges

2. **Container Not Found**
   - Verify Docker container name: `docker ps | grep violentutf_api`
   - Ensure container is running

3. **Database Locked**
   - Stop active orchestrator executions before cleanup
   - Wait for current operations to complete

### Getting Help

- Check logs: `docker logs violentutf_api`
- Verify database integrity before cleanup
- Test with `--dry-run` first

## Related Documentation

- [Memory Management Guide](../troubleshooting/lesson_memoryManagement.md) - Understanding ViolentUTF memory architecture
- [Dashboard Documentation](../violentutf_Dash.md) - Dashboard features and data sources
- [API Documentation](../api/endpoints.md) - API endpoints for programmatic cleanup