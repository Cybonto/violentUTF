#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Simplified Scorer Results Cleanup Utility for ViolentUTF

This script cleans up scorer results from the PyRIT memory database.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import duckdb
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table

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
            console.print(f"[green]Connected to database: {self.db_path}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to connect to database: {e}[/red]")
            raise

    def disconnect(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about scorer results in the database."""
        stats = {}

        # Total scores
        result = self.conn.execute("SELECT COUNT(*) FROM scores").fetchone()
        stats["total_scores"] = result[0] if result else 0

        # Scores by scorer
        result = self.conn.execute(
            """
            SELECT scorer_name, COUNT(*)
            FROM scores
            WHERE scorer_name IS NOT NULL
            GROUP BY scorer_name
        """
        ).fetchall()
        stats["by_scorer"] = {row[0]: row[1] for row in result}

        # Scores by age
        for days in [7, 30, 90, 180]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            result = self.conn.execute(
                """
                SELECT COUNT(*)
                FROM scores
                WHERE timestamp < ?
            """,
                [cutoff],
            ).fetchone()
            stats[f"older_than_{days}_days"] = result[0] if result else 0

        # Orphaned scores (no associated prompt)
        result = self.conn.execute(
            """
            SELECT COUNT(*)
            FROM scores s
            LEFT JOIN prompt_pieces p
            ON s.prompt_piece_id = p.id
            WHERE p.id IS NULL
        """
        ).fetchone()
        stats["orphaned_scores"] = result[0] if result else 0

        return stats

    def cleanup_scores(
        self,
        older_than_days: Optional[int] = None,
        scorer_name: Optional[str] = None,
        orphaned_only: bool = False,
        dry_run: bool = False,
    ) -> int:
        """Delete scorer results based on specified criteria."""
        conditions = []
        params = []

        if older_than_days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
            conditions.append("timestamp < ?")
            params.append(cutoff)

        if scorer_name:
            conditions.append("scorer_name = ?")
            params.append(scorer_name)

        if orphaned_only:
            conditions.append(
                """
                NOT EXISTS (
                    SELECT 1 FROM prompt_pieces p
                    WHERE p.id = scores.prompt_piece_id
                )
            """
            )

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get count first
        count_query = f"SELECT COUNT(*) FROM scores WHERE {where_clause}"  # nosec B608 # controlled parameterized query
        result = self.conn.execute(count_query, params).fetchone()
        count = result[0] if result else 0

        if count == 0:
            console.print("[yellow]No scorer results match the specified criteria.[/yellow]")
            return 0

        # Show preview
        console.print(f"\n[bold]Found {count} scorer results to delete:[/bold]")

        # Get sample
        sample_query = (
            f"SELECT id, scorer_name, score_value, timestamp FROM scores "  # nosec B608
            f"WHERE {where_clause} LIMIT 10"
        )

        samples = self.conn.execute(sample_query, params).fetchall()
        if samples:
            table = Table(title="Sample of Results to Delete")
            table.add_column("ID", style="cyan")
            table.add_column("Scorer", style="magenta")
            table.add_column("Score", style="yellow")
            table.add_column("Timestamp", style="blue")

            for sample in samples:
                table.add_row(
                    str(sample[0]),
                    sample[1] or "N/A",
                    str(sample[2]) if sample[2] is not None else "N/A",
                    sample[3].strftime("%Y-%m-%d %H:%M") if sample[3] else "N/A",
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

        # Perform deletion
        try:
            self.conn.execute("BEGIN TRANSACTION")

            with Progress(
                SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
            ) as progress:
                task = progress.add_task("Deleting scorer results...", total=None)

                delete_query = f"DELETE FROM scores WHERE {where_clause}"  # nosec B608 # controlled parameterized query
                self.conn.execute(delete_query, params)

                self.conn.execute("COMMIT")
                progress.update(task, completed=True)

            console.print(f"[green]Successfully deleted {count} scorer results.[/green]")
            return count

        except Exception as e:
            self.conn.execute("ROLLBACK")
            console.print(f"[red]Error during cleanup: {e}[/red]")
            raise

    def vacuum_database(self) -> None:
        """Vacuum the database to reclaim space."""
        try:
            console.print("\n[bold]Running database maintenance...[/bold]")

            # Get size before vacuum
            size_before = os.path.getsize(self.db_path) / (1024 * 1024)  # MB

            with Progress(
                SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
            ) as progress:
                task = progress.add_task("Vacuuming database...", total=None)

                self.conn.execute("VACUUM")
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
            console.print(f"[yellow]Warning: Could not vacuum database: {e}[/yellow]")


def main() -> None:
    """Run cleanup script for scorer results."""
    parser = argparse.ArgumentParser(description="Clean up scorer results from ViolentUTF PyRIT memory")

    # Cleanup options
    parser.add_argument("--older-than", type=int, help="Delete scores older than specified days")
    parser.add_argument("--scorer-name", help="Delete scores from specific scorer")
    parser.add_argument("--orphaned-only", action="store_true", help="Delete only orphaned scores")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be deleted")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--vacuum-only", action="store_true", help="Only vacuum the database")
    parser.add_argument("--no-vacuum", action="store_true", help="Skip vacuum after cleanup")
    parser.add_argument("--db-path", help="Path to DuckDB database", required=True)

    args = parser.parse_args()

    # Create cleaner
    cleaner = ScorerResultCleaner(db_path=args.db_path)

    try:
        cleaner.connect()

        if args.stats:
            # Show statistics
            stats = cleaner.get_statistics()

            table = Table(title="Scorer Results Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Count", style="magenta", justify="right")

            table.add_row("Total Scores", f"{stats['total_scores']:,}")
            table.add_row("", "")

            # By scorer
            if stats.get("by_scorer"):
                table.add_row("[bold]By Scorer[/bold]", "")
                for scorer, count in stats["by_scorer"].items():
                    table.add_row(f"  {scorer}", f"{count:,}")
                table.add_row("", "")

            # By age
            table.add_row("[bold]By Age[/bold]", "")
            for days in [7, 30, 90, 180]:
                table.add_row(f"  Older than {days} days", f"{stats[f'older_than_{days}_days']:,}")

            table.add_row("", "")
            table.add_row("Orphaned Scores", f"{stats['orphaned_scores']:,}")

            console.print(table)

        elif args.vacuum_only:
            cleaner.vacuum_database()

        else:
            # Cleanup mode
            if not any([args.older_than, args.scorer_name, args.orphaned_only]):
                console.print("[red]At least one cleanup criteria must be specified[/red]")
                sys.exit(1)

            count = cleaner.cleanup_scores(
                older_than_days=args.older_than,
                scorer_name=args.scorer_name,
                orphaned_only=args.orphaned_only,
                dry_run=args.dry_run,
            )

            # Vacuum unless disabled
            if count > 0 and not args.dry_run and not args.no_vacuum:
                cleaner.vacuum_database()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        cleaner.disconnect()


if __name__ == "__main__":
    main()
