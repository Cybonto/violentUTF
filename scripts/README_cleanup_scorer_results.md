# Scorer Results Cleanup Script

## Overview
The `cleanup_scorer_results.py` script provides a secure backend utility to clean up scorer result data from the ViolentUTF system. It connects directly to the PyRIT memory (DuckDB) database and offers various cleanup options.

## Security Features
- Runs locally on the backend server only
- No API exposure - purely command-line based
- Requires confirmation before deleting data
- Supports dry-run mode to preview changes
- Logs all operations for audit trail
- Maintains database consistency with transactional operations
- Automatic rollback on errors
- Verifies referential integrity after operations

## Usage

### Show Statistics
View current scorer result statistics without making any changes:
```bash
python3 scripts/cleanup_scorer_results.py --stats
```

### Preview Cleanup (Dry Run)
See what would be deleted without actually deleting:
```bash
# Preview deletion of scores older than 30 days
python3 scripts/cleanup_scorer_results.py --older-than 30 --dry-run

# Preview deletion of orphaned scores
python3 scripts/cleanup_scorer_results.py --orphaned-only --dry-run
```

### Delete Old Scores
Delete scorer results older than specified days:
```bash
# Delete scores older than 30 days
python3 scripts/cleanup_scorer_results.py --older-than 30

# Delete scores older than 90 days
python3 scripts/cleanup_scorer_results.py --older-than 90
```

### Delete by Type
Delete scores of specific types:
```bash
# Delete all true/false scorer results
python3 scripts/cleanup_scorer_results.py --scorer-type true_false

# Delete all float scale scorer results
python3 scripts/cleanup_scorer_results.py --scorer-type float_scale
```

### Delete by Execution
Delete scores for a specific orchestrator execution:
```bash
python3 scripts/cleanup_scorer_results.py --execution-id <execution-id>
```

### Delete Orphaned Scores
Delete scores that have no associated prompt (orphaned):
```bash
python3 scripts/cleanup_scorer_results.py --orphaned-only
```

### Archive Old Scores
Archive scores to a parquet file before optional deletion:
```bash
# Archive scores older than 90 days
python3 scripts/cleanup_scorer_results.py --archive --older-than 90

# Archive and then delete from database
python3 scripts/cleanup_scorer_results.py --archive --older-than 90 --delete-after-archive

# Archive to specific location
python3 scripts/cleanup_scorer_results.py --archive --older-than 90 --archive-path /backup/scores_2024.parquet
```

### Combine Criteria
Multiple criteria can be combined:
```bash
# Delete true/false scores older than 60 days
python3 scripts/cleanup_scorer_results.py --scorer-type true_false --older-than 60

# Delete orphaned scores older than 30 days (dry run first)
python3 scripts/cleanup_scorer_results.py --orphaned-only --older-than 30 --dry-run
```

### Database Maintenance
Vacuum the database to reclaim space and update statistics:
```bash
# Just vacuum without deleting anything
python3 scripts/cleanup_scorer_results.py --vacuum-only

# Skip vacuum after cleanup (not recommended)
python3 scripts/cleanup_scorer_results.py --older-than 30 --no-vacuum
```

## Schedule Automated Cleanup
For regular maintenance, you can schedule the script using cron:

```bash
# Add to crontab to run weekly cleanup of scores older than 90 days
0 2 * * 0 /usr/bin/python3 /path/to/cleanup_scorer_results.py --older-than 90

# Archive monthly
0 3 1 * * /usr/bin/python3 /path/to/cleanup_scorer_results.py --archive --older-than 180 --archive-path /backup/scores_$(date +\%Y\%m).parquet
```

## Custom Database Path
If your DuckDB database is in a non-standard location:
```bash
python3 scripts/cleanup_scorer_results.py --stats --db-path /custom/path/to/pyrit_duckdb_storage.db
```

## Safety Features
1. **Confirmation Required**: The script asks for confirmation before deleting any data
2. **Dry Run Mode**: Use `--dry-run` to preview what would be deleted
3. **Sample Display**: Shows a sample of records to be deleted before confirmation
4. **Detailed Logging**: All operations are logged for audit purposes
5. **No Network Access**: Runs entirely locally without API calls
6. **Transactional Operations**: All deletions are wrapped in transactions
7. **Automatic Rollback**: Any error causes complete rollback - no partial deletions
8. **Integrity Verification**: Checks database consistency after operations
9. **Referential Integrity**: Maintains relationships between tables
10. **Automatic Vacuum**: Reclaims space after deletions (can be disabled)

## Return Codes
- 0: Success
- 1: Error occurred
- 2: User cancelled operation

## Requirements
- Python 3.8+
- DuckDB
- Rich (for terminal UI)
- Access to PyRIT memory database file

## Notes
- The script connects directly to the PyRIT DuckDB database
- Default database location: `~/.local/share/pyrit/pyrit_duckdb_storage.db`
- Archives are saved in Parquet format with ZSTD compression
- All timestamps are handled in UTC for consistency
- Database vacuum is run automatically after deletions to reclaim space
- The script maintains referential integrity between ScoreEntries and orchestrator_results tables
- Transaction support ensures atomic operations - either all succeed or all fail
