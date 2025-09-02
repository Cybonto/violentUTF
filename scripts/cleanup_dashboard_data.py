#!/usr/bin/env python3
# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Dashboard Data Cleanup Utility for ViolentUTF

This script cleans up orchestrator execution data from the ViolentUTF API SQLite database.
The Dashboard displays this data, which is stored separately from PyRIT memory.
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table

console = Console()


class DashboardDataCleaner:
    """Handles cleanup of Dashboard data from ViolentUTF API database."""

    def __init__(self, db_path: str = None, in_docker: bool = False):
        """Initialize the cleaner with database connection."""
        self.in_docker = in_docker

        if in_docker:
            # Access database inside Docker container
            self.container_name = "violentutf_api"
            self.db_path = "/app/app_data/violentutf.db"
        else:
            # Local database path
            self.db_path = db_path or "./violentutf_api/fastapi_app/app_data/violentutf.db"

        self.conn = None

    def connect(self):
        """Connect to the SQLite database."""
        try:
            if self.in_docker:
                console.print(
                    f"[yellow]Note: This will operate on the database inside Docker container '{self.container_name}'[/yellow]"
                )
                # For Docker, we'll execute commands via docker exec
                # Check if container exists
                result = os.system(f"docker ps -q -f name={self.container_name} > /dev/null 2>&1")
                if result != 0:
                    raise Exception(f"Docker container '{self.container_name}' not found or not running")
                console.print(f"[green]Docker container '{self.container_name}' is accessible[/green]")
            else:
                # Direct SQLite connection
                if not os.path.exists(self.db_path):
                    raise Exception(f"Database not found at {self.db_path}")
                self.conn = sqlite3.connect(self.db_path)
                console.print(f"[green]Connected to database: {self.db_path}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to connect to database: {e}[/red]")
            raise

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def _execute_query(self, query: str, params: List = None) -> List[Tuple]:
        """Execute a query, handling both local and Docker scenarios."""
        if self.in_docker:
            # Execute via docker exec
            import subprocess
            import tempfile

            # Create a Python script to execute in the container
            script = f"""
import sqlite3
import json
conn = sqlite3.connect('{self.db_path}')
cursor = conn.cursor()
cursor.execute('''{query}''', {params or []})
results = cursor.fetchall()
print(json.dumps(results))
conn.close()
"""
            # Execute directly via docker exec with escaped script
            escaped_script = script.replace('"', '\\"').replace("$", "\\$")

            result = subprocess.run(
                ["docker", "exec", self.container_name, "python3", "-c", script], capture_output=True, text=True
            )

            if result.returncode != 0:
                raise Exception(f"Query failed: {result.stderr}")

            # Parse JSON results
            return json.loads(result.stdout) if result.stdout.strip() else []
        else:
            # Direct SQLite execution
            cursor = self.conn.cursor()
            cursor.execute(query, params or [])
            return cursor.fetchall()

    def _execute_update(self, query: str, params: List = None) -> int:
        """Execute an update/delete query."""
        if self.in_docker:
            # Execute via docker exec
            import subprocess
            import tempfile

            script = f"""
import sqlite3
conn = sqlite3.connect('{self.db_path}')
cursor = conn.cursor()
cursor.execute('''{query}''', {params or []})
affected = cursor.rowcount
conn.commit()
conn.close()
print(affected)
"""
            # Execute directly via docker exec
            result = subprocess.run(
                ["docker", "exec", self.container_name, "python3", "-c", script], capture_output=True, text=True
            )

            if result.returncode != 0:
                raise Exception(f"Update failed: {result.stderr}")

            return int(result.stdout.strip()) if result.stdout.strip() else 0
        else:
            cursor = self.conn.cursor()
            cursor.execute(query, params or [])
            self.conn.commit()
            return cursor.rowcount

    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about orchestrator executions in the database."""
        stats = {}

        # Total executions
        result = self._execute_query("SELECT COUNT(*) FROM orchestrator_executions")
        stats["total_executions"] = result[0][0] if result else 0

        # By status
        result = self._execute_query(
            """
            SELECT status, COUNT(*)
            FROM orchestrator_executions
            GROUP BY status
        """
        )
        stats["by_status"] = {row[0]: row[1] for row in result}

        # By age
        for days in [7, 30, 90, 180]:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            result = self._execute_query(
                """
                SELECT COUNT(*)
                FROM orchestrator_executions
                WHERE started_at < ?
            """,
                [cutoff],
            )
            stats[f"older_than_{days}_days"] = result[0][0] if result else 0

        # With results
        result = self._execute_query(
            """
            SELECT COUNT(*)
            FROM orchestrator_executions
            WHERE results IS NOT NULL AND results != '{}'
        """
        )
        stats["with_results"] = result[0][0] if result else 0

        # Calculate total scores and responses
        try:
            result = self._execute_query(
                """
                SELECT results
                FROM orchestrator_executions
                WHERE status = 'completed' AND results IS NOT NULL
            """
            )

            total_scores = 0
            total_responses = 0

            for row in result:
                try:
                    results = json.loads(row[0]) if row[0] else {}
                    total_scores += len(results.get("scores", []))
                    total_responses += len(results.get("prompt_request_responses", []))
                except:
                    pass

            stats["total_scores"] = total_scores
            stats["total_responses"] = total_responses

        except Exception as e:
            console.print(f"[yellow]Warning: Could not calculate score statistics: {e}[/yellow]")
            stats["total_scores"] = 0
            stats["total_responses"] = 0

        return stats

    def cleanup_executions(
        self,
        older_than_days: Optional[int] = None,
        status: Optional[str] = None,
        orchestrator_name: Optional[str] = None,
        dry_run: bool = False,
    ) -> int:
        """Delete orchestrator executions based on specified criteria."""
        conditions = []
        params = []

        if older_than_days:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
            conditions.append("started_at < ?")
            params.append(cutoff)

        if status:
            conditions.append("status = ?")
            params.append(status)

        if orchestrator_name:
            # Need to join with orchestrator_configurations
            conditions.append(
                """
                orchestrator_id IN (
                    SELECT id FROM orchestrator_configurations
                    WHERE name LIKE ?
                )
            """
            )
            params.append(f"%{orchestrator_name}%")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get count and sample first
        count_query = f"SELECT COUNT(*) FROM orchestrator_executions WHERE {where_clause}"
        result = self._execute_query(count_query, params)
        count = result[0][0] if result else 0

        if count == 0:
            console.print("[yellow]No executions match the specified criteria.[/yellow]")
            return 0

        # Show preview
        console.print(f"\n[bold]Found {count} executions to delete:[/bold]")

        # Get sample
        if orchestrator_name:
            # Use subquery to avoid ambiguous column names
            sample_query = f"""
                SELECT
                    id,
                    execution_name,
                    status,
                    started_at,
                    orchestrator_id
                FROM orchestrator_executions
                WHERE {where_clause}
                ORDER BY started_at DESC
                LIMIT 10
            """
        else:
            # Need to rewrite where clause with table prefix for JOIN query
            prefixed_conditions = []
            for condition in conditions:
                if "orchestrator_id IN" in condition:
                    prefixed_conditions.append(f"oe.{condition}")
                elif any(col in condition for col in ["started_at", "status"]):
                    prefixed_conditions.append(f"oe.{condition}")
                else:
                    prefixed_conditions.append(condition)

            prefixed_where = " AND ".join(prefixed_conditions) if prefixed_conditions else "1=1"

            sample_query = f"""
                SELECT
                    oe.id,
                    oe.execution_name,
                    oe.status,
                    oe.started_at,
                    oc.name as orchestrator_name
                FROM orchestrator_executions oe
                LEFT JOIN orchestrator_configurations oc ON oe.orchestrator_id = oc.id
                WHERE {prefixed_where}
                ORDER BY oe.started_at DESC
                LIMIT 10
            """

        samples = self._execute_query(sample_query, params)

        if samples:
            table = Table(title="Sample of Executions to Delete")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Status", style="yellow")
            table.add_column("Started", style="blue")
            table.add_column("Orchestrator", style="green")

            for sample in samples:
                exec_id = sample[0] if sample[0] else "N/A"
                if orchestrator_name:
                    # When filtering by orchestrator, we don't have the name in results
                    table.add_row(
                        exec_id[:8] + "..." if len(exec_id) > 8 else exec_id,
                        sample[1] or "N/A",
                        sample[2] or "N/A",
                        sample[3][:16] if sample[3] else "N/A",
                        f"ID: {sample[4]}" if sample[4] else "N/A",
                    )
                else:
                    table.add_row(
                        exec_id[:8] + "..." if len(exec_id) > 8 else exec_id,
                        sample[1] or "N/A",
                        sample[2] or "N/A",
                        sample[3][:16] if sample[3] else "N/A",
                        sample[4] or "N/A",
                    )

            console.print(table)
            if len(samples) < count:
                console.print(f"[dim]... and {count - len(samples)} more[/dim]")

        if dry_run:
            console.print("\n[bold yellow]DRY RUN:[/bold yellow] No data was deleted.")
            return 0

        # Confirm deletion
        if not Confirm.ask(f"\nDo you want to delete {count} executions and all their results?"):
            console.print("[red]Deletion cancelled.[/red]")
            return 0

        # Perform deletion
        try:
            with Progress(
                SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
            ) as progress:
                task = progress.add_task("Deleting executions...", total=None)

                delete_query = f"DELETE FROM orchestrator_executions WHERE {where_clause}"
                deleted = self._execute_update(delete_query, params)

                progress.update(task, completed=True)

            console.print(f"[green]Successfully deleted {deleted} orchestrator executions.[/green]")
            return deleted

        except Exception as e:
            console.print(f"[red]Error during cleanup: {e}[/red]")
            raise

    def vacuum_database(self):
        """Vacuum the database to reclaim space (local only)."""
        if self.in_docker:
            console.print("[yellow]Vacuum operation not available for Docker databases[/yellow]")
            return

        try:
            console.print("\n[bold]Running database maintenance...[/bold]")

            # Get size before vacuum
            size_before = os.path.getsize(self.db_path) / (1024 * 1024)  # MB

            with Progress(
                SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
            ) as progress:
                task = progress.add_task("Vacuuming database...", total=None)

                self.conn.execute("VACUUM")

                progress.update(task, completed=True)

            # Get size after vacuum
            size_after = os.path.getsize(self.db_path) / (1024 * 1024)  # MB
            space_saved = size_before - size_after

            console.print(f"[green]Database maintenance completed.[/green]")
            console.print(f"Size before: {size_before:.2f} MB")
            console.print(f"Size after: {size_after:.2f} MB")
            if space_saved > 0:
                console.print(f"[green]Space saved: {space_saved:.2f} MB[/green]")

        except Exception as e:
            console.print(f"[yellow]Warning: Could not vacuum database: {e}[/yellow]")


def main():
    """Main entry point for the cleanup script."""
    parser = argparse.ArgumentParser(
        description="Clean up Dashboard data from ViolentUTF API database",
        epilog="""
Examples:
  # Show statistics (Docker)
  python cleanup_dashboard_data.py --docker --stats

  # Delete executions older than 30 days
  python cleanup_dashboard_data.py --docker --older-than 30

  # Delete failed executions
  python cleanup_dashboard_data.py --docker --status failed

  # Dry run to preview deletions
  python cleanup_dashboard_data.py --docker --older-than 90 --dry-run
        """,
    )

    # Database location
    parser.add_argument(
        "--docker", action="store_true", help="Access database inside Docker container 'violentutf_api'"
    )
    parser.add_argument("--db-path", help="Path to SQLite database (for local access)")

    # Cleanup options
    parser.add_argument("--older-than", type=int, help="Delete executions older than specified days")
    parser.add_argument(
        "--status",
        choices=["pending", "running", "completed", "failed", "cancelled"],
        help="Delete executions with specific status",
    )
    parser.add_argument("--orchestrator-name", help="Delete executions from specific orchestrator (partial match)")

    # Other options
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be deleted")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--vacuum", action="store_true", help="Vacuum database after cleanup (local only)")

    args = parser.parse_args()

    # Create cleaner
    cleaner = DashboardDataCleaner(db_path=args.db_path, in_docker=args.docker)

    try:
        cleaner.connect()

        if args.stats:
            # Show statistics
            stats = cleaner.get_statistics()

            table = Table(title="Dashboard Data Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Count", style="magenta", justify="right")

            table.add_row("Total Executions", f"{stats['total_executions']:,}")
            table.add_row("", "")

            # By status
            if stats.get("by_status"):
                table.add_row("[bold]By Status[/bold]", "")
                for status, count in stats["by_status"].items():
                    table.add_row(f"  {status}", f"{count:,}")
                table.add_row("", "")

            # By age
            table.add_row("[bold]By Age[/bold]", "")
            for days in [7, 30, 90, 180]:
                table.add_row(f"  Older than {days} days", f"{stats[f'older_than_{days}_days']:,}")

            table.add_row("", "")
            table.add_row("With Results", f"{stats['with_results']:,}")
            table.add_row("Total Scores", f"{stats['total_scores']:,}")
            table.add_row("Total Responses", f"{stats['total_responses']:,}")

            console.print(table)

        else:
            # Cleanup mode
            if not any([args.older_than, args.status, args.orchestrator_name]):
                console.print("[red]At least one cleanup criteria must be specified[/red]")
                console.print("Use --help to see available options")
                sys.exit(1)

            count = cleaner.cleanup_executions(
                older_than_days=args.older_than,
                status=args.status,
                orchestrator_name=args.orchestrator_name,
                dry_run=args.dry_run,
            )

            # Vacuum if requested and not in Docker
            if count > 0 and not args.dry_run and args.vacuum and not args.docker:
                cleaner.vacuum_database()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        cleaner.disconnect()


if __name__ == "__main__":
    main()
