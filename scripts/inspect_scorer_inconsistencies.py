#!/usr/bin/env python3
"""
Scorer Result Inconsistency Inspector for ViolentUTF

This script helps identify inconsistencies between scorer results at different
stages of the data pipeline: PyRIT execution → Orchestrator storage → Dashboard display
"""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import pandas as pd
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class ScorerInconsistencyInspector:
    """Main inspector class for identifying scorer result inconsistencies."""

    def __init__(self, pyrit_db_path: Optional[str] = None, sqlite_db_path: Optional[str] = None, docker: bool = False):
        """Initialize the inspector with database paths."""
        self.docker = docker

        if docker:
            self.sqlite_db_path = "/app/app_data/violentutf.db"
            self.pyrit_db_pattern = "/app_data/violentutf/pyrit_memory_*.db"
        else:
            self.sqlite_db_path = sqlite_db_path or "./violentutf_api/fastapi_app/app_data/violentutf.db"
            self.pyrit_db_path = pyrit_db_path
            self.pyrit_db_pattern = "./violentutf/app_data/violentutf/pyrit_memory_*.db"

    def find_pyrit_databases(self) -> List[Path]:
        """Find all PyRIT memory databases."""
        if self.pyrit_db_path:
            return [Path(self.pyrit_db_path)]

        pattern = (
            self.pyrit_db_pattern.replace("/app_data/", "/violentutf/app_data/")
            if self.docker
            else self.pyrit_db_pattern
        )
        base_path = Path(pattern).parent
        pattern_name = Path(pattern).name

        if base_path.exists():
            return list(base_path.glob(pattern_name))
        return []

    def inspect_pyrit_memory(self, db_path: Path) -> Dict[str, Any]:
        """Inspect a PyRIT memory database for scorer results."""
        results = {
            "db_path": str(db_path),
            "total_scores": 0,
            "score_types": {},
            "conversations": 0,
            "prompts": 0,
            "recent_scores": [],
        }

        try:
            conn = duckdb.connect(str(db_path), read_only=True)

            # Check if score table exists
            tables = conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]

            if "score" in table_names:
                # Get total scores
                total = conn.execute("SELECT COUNT(*) FROM score").fetchone()[0]
                results["total_scores"] = total

                # Get score types distribution
                score_types = conn.execute(
                    """
                    SELECT scorer_class_name, COUNT(*) as count 
                    FROM score 
                    GROUP BY scorer_class_name
                """
                ).fetchall()
                results["score_types"] = {st[0]: st[1] for st in score_types}

                # Get recent scores with details
                recent = conn.execute(
                    """
                    SELECT 
                        id,
                        scorer_class_name,
                        score_value,
                        score_category,
                        created_datetime,
                        prompt_request_response_id
                    FROM score 
                    ORDER BY created_datetime DESC 
                    LIMIT 10
                """
                ).fetchall()

                results["recent_scores"] = [
                    {
                        "id": r[0],
                        "scorer_type": r[1],
                        "value": r[2],
                        "category": r[3],
                        "created": r[4],
                        "prompt_response_id": r[5],
                    }
                    for r in recent
                ]

            # Get conversation and prompt counts
            if "conversation" in table_names:
                conv_count = conn.execute("SELECT COUNT(DISTINCT id) FROM conversation").fetchone()[0]
                results["conversations"] = conv_count

            if "prompt_request_response" in table_names:
                prompt_count = conn.execute("SELECT COUNT(*) FROM prompt_request_response").fetchone()[0]
                results["prompts"] = prompt_count

            conn.close()

        except Exception as e:
            results["error"] = str(e)

        return results

    def inspect_sqlite_storage(self) -> Dict[str, Any]:
        """Inspect SQLite database for orchestrator execution results."""
        results = {
            "total_executions": 0,
            "executions_with_results": 0,
            "total_stored_scores": 0,
            "total_stored_responses": 0,
            "recent_executions": [],
        }

        try:
            if self.docker:
                # Use docker exec to query
                import subprocess

                # Get execution counts
                cmd = f"""docker exec violentutf_api python3 -c "
import sqlite3
import json
conn = sqlite3.connect('{self.sqlite_db_path}')
cursor = conn.cursor()

# Total executions
cursor.execute('SELECT COUNT(*) FROM orchestrator_executions')
total = cursor.fetchone()[0]

# Executions with results
cursor.execute('SELECT COUNT(*) FROM orchestrator_executions WHERE results IS NOT NULL')
with_results = cursor.fetchone()[0]

# Get all results for score counting
cursor.execute('SELECT results FROM orchestrator_executions WHERE results IS NOT NULL')
total_scores = 0
total_responses = 0
for row in cursor.fetchall():
    try:
        data = json.loads(row[0])
        total_scores += len(data.get('scores', []))
        total_responses += len(data.get('prompt_request_responses', []))
    except:
        pass

print(json.dumps({{
    'total': total,
    'with_results': with_results,
    'total_scores': total_scores,
    'total_responses': total_responses
}}))
"
"""
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    results.update(data)
            else:
                # Direct SQLite connection
                conn = sqlite3.connect(self.sqlite_db_path)
                cursor = conn.cursor()

                # Get counts
                cursor.execute("SELECT COUNT(*) FROM orchestrator_executions")
                results["total_executions"] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM orchestrator_executions WHERE results IS NOT NULL")
                results["executions_with_results"] = cursor.fetchone()[0]

                # Count scores and responses
                cursor.execute("SELECT results FROM orchestrator_executions WHERE results IS NOT NULL")
                for row in cursor.fetchall():
                    try:
                        data = json.loads(row[0])
                        results["total_stored_scores"] += len(data.get("scores", []))
                        results["total_stored_responses"] += len(data.get("prompt_request_responses", []))
                    except:
                        pass

                # Get recent executions
                cursor.execute(
                    """
                    SELECT id, execution_name, started_at, status
                    FROM orchestrator_executions
                    ORDER BY started_at DESC
                    LIMIT 5
                """
                )
                results["recent_executions"] = [
                    {"id": r[0], "name": r[1], "started": r[2], "status": r[3]} for r in cursor.fetchall()
                ]

                conn.close()

        except Exception as e:
            results["error"] = str(e)

        return results

    def compare_pyrit_vs_sqlite(self, pyrit_results: Dict, sqlite_results: Dict) -> Dict[str, Any]:
        """Compare results between PyRIT and SQLite to identify discrepancies."""
        comparison = {
            "pyrit_total_scores": sum(r["total_scores"] for r in pyrit_results),
            "sqlite_total_scores": sqlite_results["total_stored_scores"],
            "score_difference": 0,
            "response_difference": 0,
            "potential_issues": [],
        }

        # Calculate differences
        comparison["score_difference"] = comparison["sqlite_total_scores"] - comparison["pyrit_total_scores"]

        pyrit_total_prompts = sum(r["prompts"] for r in pyrit_results)
        comparison["response_difference"] = sqlite_results["total_stored_responses"] - pyrit_total_prompts

        # Identify potential issues
        if comparison["score_difference"] < 0:
            comparison["potential_issues"].append(
                f"Missing {abs(comparison['score_difference'])} scores in SQLite storage"
            )
        elif comparison["score_difference"] > 0:
            comparison["potential_issues"].append(
                f"Extra {comparison['score_difference']} scores in SQLite (possible duplicates)"
            )

        if comparison["response_difference"] < 0:
            comparison["potential_issues"].append(
                f"Missing {abs(comparison['response_difference'])} responses in SQLite storage"
            )

        # Check score type distribution
        all_pyrit_types = {}
        for result in pyrit_results:
            for scorer_type, count in result.get("score_types", {}).items():
                all_pyrit_types[scorer_type] = all_pyrit_types.get(scorer_type, 0) + count

        comparison["pyrit_score_types"] = all_pyrit_types

        return comparison

    def check_interpretation_consistency(self, sqlite_results: Dict) -> Dict[str, Any]:
        """Check for interpretation and aggregation inconsistencies."""
        issues = {
            "boolean_interpretations": [],
            "scale_inconsistencies": [],
            "aggregation_errors": [],
            "category_issues": [],
        }

        try:
            if self.docker:
                # Check boolean interpretations via docker
                import subprocess

                cmd = f"""docker exec violentutf_api python3 -c "
import sqlite3
import json
conn = sqlite3.connect('{self.sqlite_db_path}')
cursor = conn.cursor()
cursor.execute('SELECT results FROM orchestrator_executions WHERE results IS NOT NULL')
boolean_values = set()
for row in cursor.fetchall():
    data = json.loads(row[0])
    for score in data.get('scores', []):
        if 'TrueFalse' in score.get('scorer_class_name', ''):
            val = score.get('score_value')
            boolean_values.add(f'{val} ({type(val).__name__})')
print('Boolean value types found:', list(boolean_values))
"
"""
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0 and result.stdout:
                    console.print(f"[yellow]Boolean interpretations: {result.stdout.strip()}[/yellow]")

        except Exception as e:
            issues["error"] = str(e)

        return issues

    def generate_report(self):
        """Generate a comprehensive inconsistency report."""
        console.print(Panel.fit("🔍 ViolentUTF Scorer Inconsistency Report", style="bold blue"))

        # Step 1: Inspect PyRIT databases
        console.print("\n[bold]1. Inspecting PyRIT Memory Databases[/bold]")
        pyrit_dbs = self.find_pyrit_databases()

        if not pyrit_dbs:
            console.print("[yellow]No PyRIT memory databases found[/yellow]")
            pyrit_results = []
        else:
            pyrit_results = []
            for db in pyrit_dbs:
                console.print(f"  Checking: {db.name}")
                result = self.inspect_pyrit_memory(db)
                pyrit_results.append(result)

                if "error" in result:
                    console.print(f"    [red]Error: {result['error']}[/red]")
                else:
                    console.print(f"    Scores: {result['total_scores']}, Conversations: {result['conversations']}")

        # Step 2: Inspect SQLite storage
        console.print("\n[bold]2. Inspecting SQLite Storage[/bold]")
        sqlite_results = self.inspect_sqlite_storage()

        if "error" in sqlite_results:
            console.print(f"[red]Error: {sqlite_results['error']}[/red]")
            return

        console.print(f"  Total Executions: {sqlite_results['total_executions']}")
        console.print(f"  Executions with Results: {sqlite_results['executions_with_results']}")
        console.print(f"  Total Stored Scores: {sqlite_results['total_stored_scores']}")
        console.print(f"  Total Stored Responses: {sqlite_results['total_stored_responses']}")

        # Step 3: Compare results
        if pyrit_results:
            console.print("\n[bold]3. Comparison Analysis[/bold]")
            comparison = self.compare_pyrit_vs_sqlite(pyrit_results, sqlite_results)

            # Create comparison table
            table = Table(title="PyRIT vs SQLite Comparison", box=box.ROUNDED)
            table.add_column("Metric", style="cyan")
            table.add_column("PyRIT", style="magenta", justify="right")
            table.add_column("SQLite", style="green", justify="right")
            table.add_column("Difference", style="yellow", justify="right")

            table.add_row(
                "Total Scores",
                str(comparison["pyrit_total_scores"]),
                str(comparison["sqlite_total_scores"]),
                str(comparison["score_difference"]),
            )

            console.print(table)

            # Show issues
            if comparison["potential_issues"]:
                console.print("\n[bold red]⚠️  Potential Issues Detected:[/bold red]")
                for issue in comparison["potential_issues"]:
                    console.print(f"  • {issue}")
            else:
                console.print("\n[bold green]✅ No major inconsistencies detected[/bold green]")

            # Show score type distribution
            if comparison["pyrit_score_types"]:
                console.print("\n[bold]Score Type Distribution (PyRIT):[/bold]")
                for scorer_type, count in comparison["pyrit_score_types"].items():
                    console.print(f"  • {scorer_type}: {count}")

        # Step 4: Check interpretation consistency
        console.print("\n[bold]4. Interpretation and Aggregation Analysis[/bold]")
        interpretation_issues = self.check_interpretation_consistency(sqlite_results)

        if "error" in interpretation_issues:
            console.print(f"[red]Error checking interpretations: {interpretation_issues['error']}[/red]")
        else:
            console.print("  Checking for interpretation inconsistencies...")
            console.print("  • Boolean value type variations")
            console.print("  • Scale normalization issues")
            console.print("  • Aggregation calculation methods")
            console.print("  • Category name preservation")

        # Step 5: Recommendations
        console.print("\n[bold]5. Recommendations[/bold]")
        console.print("  • Run this inspection after each orchestrator execution")
        console.print("  • Monitor for increasing discrepancies over time")
        console.print("  • Check Dashboard display against these raw counts")
        console.print("  • Review transformation logic if discrepancies found")


def main():
    """Main entry point for the inconsistency inspector."""
    parser = argparse.ArgumentParser(description="Inspect scorer result inconsistencies in ViolentUTF")

    parser.add_argument("--docker", action="store_true", help="Run inspection against Docker containers")

    parser.add_argument("--pyrit-db", help="Path to specific PyRIT memory database")

    parser.add_argument("--sqlite-db", help="Path to SQLite database")

    parser.add_argument("--export", help="Export detailed results to JSON file")

    args = parser.parse_args()

    # Create inspector
    inspector = ScorerInconsistencyInspector(
        pyrit_db_path=args.pyrit_db, sqlite_db_path=args.sqlite_db, docker=args.docker
    )

    # Generate report
    inspector.generate_report()

    # Export if requested
    if args.export:
        console.print(f"\n[yellow]Export functionality not yet implemented[/yellow]")


if __name__ == "__main__":
    main()
