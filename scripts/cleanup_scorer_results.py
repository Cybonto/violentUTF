#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Scorer Results Cleanup Utility

This script provides various options to clean up scorer result data from the ViolentUTF system.
It connects directly to the PyRIT memory (DuckDB) to perform cleanup operations.

Usage:
    python cleanup_scorer_results.py --help
    python cleanup_scorer_results.py --older-than 30  # Delete results older than 30 days
    python cleanup_scorer_results.py --execution-id <id>  # Delete results for specific execution
    python cleanup_scorer_results.py --scorer-type true_false  # Delete all true/false scorer results
    python cleanup_scorer_results.py --dry-run  # Show what would be deleted without actually deleting
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import duckdb
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table

from violentutf.utils.logging import get_logger

# Add parent directory to path to import utils
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
try:
    load_dotenv()
except Exception:
    # Continue without environment variables
    pass

logger = get_logger(__name__)
console = Console()


class ScorerResultCleaner:
    """Handles cleanup of scorer results from PyRIT memory."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize the cleaner with database connection."""
        if not db_path:
            # Default PyRIT memory location
            db_path = os.path.join(os.path.expanduser("~"), ".local", "share", "pyrit", "pyrit_duckdb_storage.db")

        self.db_path = db_path
        self.conn = None

    def connect(self) -> None:
        """Connect to the DuckDB database."""
        try:
            self.conn = duckdb.connect(self.db_path)
            logger.info("Connected to database: %s", self.db_path)
        except Exception as e:
            logger.error("Failed to connect to database: %s", e)
            raise

    def disconnect(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about scorer results in the database."""
        stats = {}

        # Total score entries
        result = self.conn.execute("SELECT COUNT(*) FROM ScoreEntries").fetchone()
        stats["total_ScoreEntries"] = result[0] if result else 0

        # Scores by type
        result = self.conn.execute(
            """
            SELECT score_type, COUNT(*)
            FROM ScoreEntries
            GROUP BY score_type
        """
        ).fetchall()
        for row in result:
            stats[f"type_{row[0]}"] = row[1]

        # Scores by age
        for days in [7, 30, 90, 180]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            result = self.conn.execute(
                """
                SELECT COUNT(*)
                FROM ScoreEntries
                WHERE timestamp < ?
            """,
                [cutoff],
            ).fetchone()
            stats[f"older_than_{days}_days"] = result[0] if result else 0

        # Orphaned ScoreEntries (no associated prompt)
        result = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM ScoreEntries s
            LEFT JOIN PromptRequestResponses p
            ON s.prompt_request_response_id = p.id
            WHERE p.id IS NULL
        """
        ).fetchone()
        stats["orphaned_ScoreEntries"] = result[0] if result else 0

        return stats

    def preview_cleanup(
        self,
        older_than_days: Optional[int] = None,
        execution_id: Optional[str] = None,
        scorer_type: Optional[str] = None,
        scorer_category: Optional[str] = None,
        orphaned_only: bool = False,
    ) -> Tuple[int, List[Dict]]:
        """Preview what would be deleted without actually deleting."""
        conditions = []
        params = []

        if older_than_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            conditions.append("s.timestamp < ?")
            params.append(cutoff)

        if execution_id:
            # Need to join with orchestrator results
            conditions.append(
                """
                EXISTS (
                    SELECT 1 FROM orchestrator_results or_res
                    WHERE or_res.score_id = s.id
                    AND or_res.execution_id = ?
                )
            """
            )
            params.append(execution_id)

        if scorer_type:
            conditions.append("s.score_type = ?")
            params.append(scorer_type)

        if scorer_category:
            conditions.append("s.score_category = ?")
            params.append(scorer_category)

        if orphaned_only:
            conditions.append("p.id IS NULL")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get count and sample of records to be deleted
        query = (
            f"SELECT COUNT(*) as count, MIN(s.timestamp) as oldest, MAX(s.timestamp) as newest "
            f"FROM ScoreEntries s LEFT JOIN PromptRequestResponses p ON s.prompt_request_response_id = p.id "
            f"WHERE {where_clause}"  # nosec B608 # controlled parameterized query
        )

        result = self.conn.execute(query, params).fetchone()
        count = result[0] if result else 0

        # Get sample of records
        sample_query = (
            f"SELECT s.id, s.score_type, s.score_category, s.score_value, s.timestamp "
            f"FROM ScoreEntries s LEFT JOIN PromptRequestResponses p ON s.prompt_request_response_id = p.id "
            f"WHERE {where_clause} LIMIT 10"  # nosec B608 # controlled parameterized query
        )

        samples = []
        for row in self.conn.execute(sample_query, params).fetchall():
            samples.append(
                {
                    "id": row[0],
                    "type": row[1],
                    "category": row[2],
                    "value": row[3],
                    "timestamp": row[4],
                    "scorer": row[5],
                }
            )

        return count, samples

    def cleanup_ScoreEntries(
        self,
        older_than_days: Optional[int] = None,
        execution_id: Optional[str] = None,
        scorer_type: Optional[str] = None,
        scorer_category: Optional[str] = None,
        orphaned_only: bool = False,
        dry_run: bool = False,
    ) -> int:
        """Delete scorer results based on specified criteria."""
        # First preview what will be deleted
        count, samples = self.preview_cleanup(
            older_than_days=older_than_days,
            execution_id=execution_id,
            scorer_type=scorer_type,
            scorer_category=scorer_category,
            orphaned_only=orphaned_only,
        )

        if count == 0:
            console.print("[yellow]No scorer results match the specified criteria.[/yellow]")
            return 0

        # Show preview
        console.print(f"\n[bold]Found {count} scorer results to delete:[/bold]")

        if samples:
            table = Table(title="Sample of Results to Delete")
            table.add_column("ID", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Category", style="green")
            table.add_column("Value", style="yellow")
            table.add_column("Timestamp", style="blue")
            table.add_column("Scorer", style="red")

            for sample in samples:
                table.add_row(
                    str(sample["id"])[:8],
                    sample["type"],
                    sample["category"] or "N/A",
                    str(sample["value"])[:20],
                    sample["timestamp"].strftime("%Y-%m-%d %H:%M"),
                    sample["scorer"].split(".")[-1],
                )

            console.print(table)
            if len(samples) < count:
                console.print(f"[dim]... and {count - len(samples)} more[/dim]")

        if dry_run:
            console.print("\n[bold yellow]DRY RUN:[/bold yellow] No data was deleted.")
            return 0

        # Confirm deletion
        if not Confirm.ask(f"\nDo you want to delete {count} scorer results?"):
            console.print("[red]Deletion cancelled.[/red]")
            return 0

        # Begin transaction for database consistency
        try:
            self.conn.execute("BEGIN TRANSACTION")

            # Build conditions for ScoreEntries deletion
            conditions = []
            params = []

            if older_than_days:
                cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
                conditions.append("timestamp < ?")
                params.append(cutoff)

            if execution_id:
                # First, collect score IDs for this execution
                score_ids = self.conn.execute(
                    """
                    SELECT score_id FROM orchestrator_results
                    WHERE execution_id = ?
                """,
                    [execution_id],
                ).fetchall()

                if score_ids:
                    # Delete from orchestrator_results first (maintains referential integrity)
                    self.conn.execute(
                        """
                        DELETE FROM orchestrator_results
                        WHERE execution_id = ?
                    """,
                        [execution_id],
                    )

                    # Add condition to delete these specific ScoreEntries
                    score_id_list = [str(row[0]) for row in score_ids]
                    placeholders = ",".join(["?" for _ in score_id_list])
                    conditions.append(f"id IN ({placeholders})")
                    params.extend(score_id_list)

            if scorer_type:
                conditions.append("score_type = ?")
                params.append(scorer_type)

            if scorer_category:
                conditions.append("score_category = ?")
                params.append(scorer_category)

            if orphaned_only:
                conditions.append(
                    """
                    NOT EXISTS (
                        SELECT 1 FROM PromptRequestResponses p
                        WHERE p.id = ScoreEntries.prompt_request_response_id
                    )
                """
                )

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Perform deletion
            with Progress(
                SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
            ) as progress:
                task = progress.add_task("Deleting scorer results...", total=None)

                # Delete from ScoreEntries
                delete_query = (
                    f"DELETE FROM ScoreEntries WHERE {where_clause}"  # nosec B608 # controlled parameterized query
                )
                self.conn.execute(delete_query, params)

                # Check for any orphaned orchestrator_results
                self.conn.execute(
                    """
                    DELETE FROM orchestrator_results
                    WHERE score_id NOT IN (SELECT id FROM ScoreEntries)
                """
                )

                # Commit transaction
                self.conn.execute("COMMIT")

                progress.update(task, completed=True)

            console.print(f"[green]Successfully deleted {count} scorer results.[/green]")

            # Verify database consistency
            self._verify_database_consistency()

            return count

        except Exception as e:
            # Rollback on error
            self.conn.execute("ROLLBACK")
            logger.error("Error during cleanup, transaction rolled back: %s", e)
            console.print(f"[red]Error during cleanup: {e}[/red]")
            console.print("[yellow]Transaction rolled back - no data was deleted.[/yellow]")
            raise

    def _verify_database_consistency(self) -> None:
        """Verify database consistency after cleanup operations."""
        try:
            # Check for orphaned orchestrator_results
            orphaned = self.conn.execute(
                """
                SELECT COUNT(*) FROM orchestrator_results or_res
                WHERE NOT EXISTS (
                    SELECT 1 FROM ScoreEntries se
                    WHERE se.id = or_res.score_id
                )
            """
            ).fetchone()[0]

            if orphaned > 0:
                logger.warning("Found %s orphaned orchestrator_results entries", orphaned)
                console.print(f"[yellow]Warning: {orphaned} orphaned orchestrator_results found[/yellow]")

            # Check for broken references in ScoreEntries
            broken_refs = self.conn.execute(
                """
                SELECT COUNT(*) FROM ScoreEntries se
                WHERE se.prompt_request_response_id IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM PromptRequestResponses prr
                    WHERE prr.id = se.prompt_request_response_id
                )
            """
            ).fetchone()[0]

            if broken_refs > 0:
                logger.warning("Found %s ScoreEntries with broken prompt references", broken_refs)
                console.print(f"[yellow]Warning: {broken_refs} ScoreEntries with broken prompt references[/yellow]")

            # Run PRAGMA integrity_check for DuckDB
            integrity = self.conn.execute("PRAGMA integrity_check").fetchall()
            if integrity and integrity[0][0] != "ok":
                logger.error("Database integrity check failed: %s", integrity)
                console.print("[red]Database integrity check failed![/red]")
            else:
                logger.info("Database integrity check passed")

        except Exception as e:
            logger.error("Error verifying database consistency: %s", e)
            console.print(f"[yellow]Warning: Could not verify database consistency: {e}[/yellow]")

    def archive_ScoreEntries(self, older_than_days: int, archive_path: str, delete_after_archive: bool = False) -> int:
        """Archive old scorer results to a separate file."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)

        # Create archive directory if needed
        archive_dir = Path(archive_path).parent
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Export to parquet file
        export_query = """
            SELECT * FROM ScoreEntries
            WHERE timestamp < ?
        """

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("Archiving scorer results...", total=None)

            # Export to parquet
            self.conn.execute(
                f"""
                COPY ({export_query}) TO '{archive_path}'
                (FORMAT PARQUET, COMPRESSION ZSTD)
            """,
                [cutoff],
            )

            # Get count of archived records
            result = self.conn.execute("SELECT COUNT(*) FROM ScoreEntries WHERE timestamp < ?", [cutoff]).fetchone()
            count = result[0] if result else 0

            progress.update(task, completed=True)

        console.print(f"[green]Archived {count} scorer results to {archive_path}[/green]")

        if delete_after_archive and count > 0:
            if Confirm.ask(f"\nDelete the {count} archived records from the database?"):
                self.conn.execute("DELETE FROM ScoreEntries WHERE timestamp < ?", [cutoff])
                console.print(f"[green]Deleted {count} archived scorer results.[/green]")

        return count

    def vacuum_database(self) -> None:
        """Vacuum the database to reclaim space and update statistics."""
        try:
            console.print("\n[bold]Running database maintenance...[/bold]")

            # Get size before vacuum
            size_before = os.path.getsize(self.db_path) / (1024 * 1024)  # MB

            with Progress(
                SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
            ) as progress:
                task = progress.add_task("Vacuuming database...", total=None)

                # Run VACUUM to reclaim space
                self.conn.execute("VACUUM")

                # Analyze tables to update statistics
                self.conn.execute("ANALYZE")

                progress.update(task, completed=True)

            # Get size after vacuum
            size_after = os.path.getsize(self.db_path) / (1024 * 1024)  # MB
            space_saved = size_before - size_after

            console.print("[green]Database maintenance completed.[/green]")
            console.print(f"Size before: {size_before:.2f} MB")
            console.print(f"Size after: {size_after:.2f} MB")
            if space_saved > 0:
                console.print(f"[green]Space saved: {space_saved:.2f} MB[/green]")

        except Exception as e:
            logger.error("Error during database vacuum: %s", e)
            console.print(f"[yellow]Warning: Could not vacuum database: {e}[/yellow]")


def main() -> None:
    """Entry point for the cleanup script."""
    parser = argparse.ArgumentParser(
        description="Clean up scorer results from ViolentUTF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete ScoreEntries older than 30 days
  python cleanup_scorer_results.py --older-than 30

  # Delete all true/false scorer results
  python cleanup_scorer_results.py --scorer-type true_false

  # Delete orphaned ScoreEntries (dry run)
  python cleanup_scorer_results.py --orphaned-only --dry-run

  # Archive ScoreEntries older than 90 days
  python cleanup_scorer_results.py --archive --older-than 90 --archive-path ./archives/ScoreEntries_backup.parquet

  # Show statistics
  python cleanup_scorer_results.py --stats

  # Vacuum database only
  python cleanup_scorer_results.py --vacuum-only
        """,
    )

    # Cleanup options
    parser.add_argument("--older-than", type=int, help="Delete ScoreEntries older than specified days")
    parser.add_argument("--execution-id", help="Delete ScoreEntries for specific orchestrator execution ID")
    parser.add_argument(
        "--scorer-type", choices=["true_false", "float_scale", "str"], help="Delete ScoreEntries of specific type"
    )
    parser.add_argument("--scorer-category", help="Delete ScoreEntries of specific category")
    parser.add_argument(
        "--orphaned-only", action="store_true", help="Delete only orphaned ScoreEntries (no associated prompt)"
    )

    # Archive options
    parser.add_argument("--archive", action="store_true", help="Archive ScoreEntries instead of deleting")
    parser.add_argument(
        "--archive-path",
        default=f"./archives/scorer_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet",
        help="Path for archive file",
    )
    parser.add_argument(
        "--delete-after-archive", action="store_true", help="Delete ScoreEntries after successful archiving"
    )

    # Other options
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    parser.add_argument("--stats", action="store_true", help="Show statistics about scorer results")
    parser.add_argument("--vacuum-only", action="store_true", help="Only vacuum the database without deleting anything")
    parser.add_argument("--no-vacuum", action="store_true", help="Skip vacuum operation after cleanup")
    parser.add_argument("--db-path", help="Custom path to DuckDB database")

    args = parser.parse_args()

    # Create cleaner instance
    cleaner = ScorerResultCleaner(db_path=args.db_path)

    try:
        cleaner.connect()

        if args.stats:
            # Show statistics
            stats = cleaner.get_statistics()

            table = Table(title="Scorer Results Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Count", style="magenta", justify="right")

            table.add_row("Total Scores", f"{stats['total_ScoreEntries']:,}")
            table.add_row("", "")  # Empty row

            # By type
            table.add_row("[bold]By Type[/bold]", "")
            for score_type in ["true_false", "float_scale", "str"]:
                if f"type_{score_type}" in stats:
                    table.add_row(f"  {score_type}", f"{stats[f'type_{score_type}']:,}")

            table.add_row("", "")  # Empty row

            # By age
            table.add_row("[bold]By Age[/bold]", "")
            for days in [7, 30, 90, 180]:
                table.add_row(f"  Older than {days} days", f"{stats[f'older_than_{days}_days']:,}")

            table.add_row("", "")  # Empty row
            table.add_row("Orphaned Scores", f"{stats['orphaned_ScoreEntries']:,}")

            console.print(table)

        elif args.archive:
            # Archive mode
            if not args.older_than:
                console.print("[red]--older-than is required for archiving[/red]")
                sys.exit(1)

            count = cleaner.archive_ScoreEntries(
                older_than_days=args.older_than,
                archive_path=args.archive_path,
                delete_after_archive=args.delete_after_archive,
            )

        elif args.vacuum_only:
            # Just vacuum the database
            cleaner.vacuum_database()

        else:
            # Cleanup mode
            if not any(
                [args.older_than, args.execution_id, args.scorer_type, args.scorer_category, args.orphaned_only]
            ):
                console.print("[red]At least one cleanup criteria must be specified[/red]")
                console.print("Use --help to see available options")
                sys.exit(1)

            count = cleaner.cleanup_ScoreEntries(
                older_than_days=args.older_than,
                execution_id=args.execution_id,
                scorer_type=args.scorer_type,
                scorer_category=args.scorer_category,
                orphaned_only=args.orphaned_only,
                dry_run=args.dry_run,
            )

            # Run vacuum unless disabled or in dry-run mode
            if count > 0 and not args.dry_run and not args.no_vacuum:
                cleaner.vacuum_database()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.error("Cleanup failed: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        cleaner.disconnect()


if __name__ == "__main__":
    main()
