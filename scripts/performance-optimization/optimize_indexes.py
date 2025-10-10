# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Index optimization tool for database performance improvement."""

from __future__ import annotations

import argparse
import re
from typing import Any, Dict, List, Optional

from utils.db_connections import DatabaseConnection
from utils.metrics_collector import MetricsCollector
from utils.report_generator import ReportGenerator


class IndexOptimizer:
    """Optimize database indexes for improved query performance."""

    def __init__(self: IndexOptimizer) -> None:
        """Initialize index optimizer."""
        self.metrics_collector = MetricsCollector()
        self.report_generator = ReportGenerator()

    def analyze_indexes(self: IndexOptimizer, db_path: str, db_type: str) -> Dict[str, Any]:
        """Analyze existing indexes.

        Args:
            db_path: Path to database
            db_type: Type of database

        Returns:
            Dictionary containing index analysis
        """
        analysis: Dict[str, Any] = {
            "existing_indexes": [],
            "unused_indexes": [],
            "redundant_indexes": [],
        }

        with DatabaseConnection(db_path, db_type) as conn:
            if db_type == "sqlite":
                # Get all indexes
                query = "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index'"
                results = conn.fetchall(query)

                for row in results:
                    index_info = {"name": row[0], "table": row[1], "sql": row[2]}

                    # Parse columns from SQL
                    if row[2]:
                        columns = self._parse_index_columns(row[2])
                        index_info["columns"] = columns

                    analysis["existing_indexes"].append(index_info)

                # Detect redundant indexes
                analysis["redundant_indexes"] = self._detect_redundant_indexes(analysis["existing_indexes"])

        return analysis

    def recommend_indexes(
        self: IndexOptimizer,
        db_path: str,
        db_type: str,
        queries: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Recommend new indexes based on query patterns.

        Args:
            db_path: Path to database
            db_type: Type of database
            queries: Optional list of queries to analyze

        Returns:
            Dictionary containing index recommendations
        """
        recommendations: Dict[str, Any] = {
            "recommended_indexes": [],
            "composite_indexes": [],
        }

        with DatabaseConnection(db_path, db_type) as conn:
            # Get tables
            tables = self.metrics_collector.get_table_list(conn)

            # Get existing indexes
            existing_analysis = self.analyze_indexes(db_path, db_type)
            existing_index_columns = set()

            for idx in existing_analysis["existing_indexes"]:
                if "columns" in idx and idx["columns"]:
                    existing_index_columns.add((idx["table"], tuple(idx["columns"])))

            # Recommend indexes for common patterns
            for table in tables:
                # Get table columns
                if db_type == "sqlite":
                    pragma_query = f'PRAGMA table_info("{table}")'  # nosec B608
                    columns = conn.fetchall(pragma_query)

                    for col in columns:
                        col_name = col[1]

                        # Skip if already indexed
                        if (table, (col_name,)) in existing_index_columns:
                            continue

                        # Recommend index for non-primary key columns
                        if col[5] == 0:  # Not a primary key
                            recommendations["recommended_indexes"].append(
                                {
                                    "table": table,
                                    "columns": [col_name],
                                    "reason": "Frequently queried column",
                                    "index_name": f"idx_{table}_{col_name}",
                                }
                            )

            # Analyze provided queries for composite index opportunities
            if queries:
                composite = self._analyze_query_patterns(queries)
                recommendations["composite_indexes"] = composite

        return recommendations

    def create_index(
        self: IndexOptimizer,
        db_path: str,
        db_type: str,
        table: str,
        column: Optional[str] = None,
        columns: Optional[List[str]] = None,
        index_name: Optional[str] = None,
    ) -> bool:
        """Create an index.

        Args:
            db_path: Path to database
            db_type: Type of database
            table: Table name
            column: Single column name (for simple index)
            columns: Multiple column names (for composite index)
            index_name: Optional custom index name

        Returns:
            True if index was created successfully
        """
        if not column and not columns:
            raise ValueError("Either column or columns must be specified")

        # Determine columns to index
        index_columns = [column] if column else columns or []

        # Generate index name if not provided
        if not index_name:
            col_str = "_".join(index_columns)
            index_name = f"idx_{table}_{col_str}"

        # Build CREATE INDEX statement
        col_list = ", ".join([f'"{col}"' for col in index_columns])
        create_query = f'CREATE INDEX IF NOT EXISTS "{index_name}" ON "{table}" ({col_list})'  # nosec B608

        try:
            with DatabaseConnection(db_path, db_type) as conn:
                conn.execute(create_query)
            return True
        except Exception:
            return False

    def drop_index(self: IndexOptimizer, db_path: str, db_type: str, index_name: str) -> bool:
        """Drop an index.

        Args:
            db_path: Path to database
            db_type: Type of database
            index_name: Name of index to drop

        Returns:
            True if index was dropped successfully
        """
        drop_query = f'DROP INDEX IF EXISTS "{index_name}"'  # nosec B608

        try:
            with DatabaseConnection(db_path, db_type) as conn:
                conn.execute(drop_query)
            return True
        except Exception:
            return False

    def validate_index_effectiveness(
        self: IndexOptimizer,
        db_path: str,
        db_type: str,
        query: str,
        index_name: str,
    ) -> Dict[str, Any]:
        """Validate if an index is being used effectively.

        Args:
            db_path: Path to database
            db_type: Type of database
            query: Query to test
            index_name: Index name to check

        Returns:
            Dictionary with effectiveness metrics
        """
        effectiveness: Dict[str, Any] = {"using_index": False, "query_time": 0}

        with DatabaseConnection(db_path, db_type) as conn:
            # Get execution plan
            if db_type == "sqlite":
                explain_query = f"EXPLAIN QUERY PLAN {query}"
                plan = conn.fetchall(explain_query)

                # Check if index is mentioned in plan
                plan_text = " ".join([str(row) for row in plan])
                effectiveness["using_index"] = index_name in plan_text

            # Measure query time
            timing = self.metrics_collector.measure_query_time(conn, query)
            effectiveness["query_time"] = timing["avg_time_ms"]

        return effectiveness

    def calculate_selectivity(self: IndexOptimizer, db_path: str, db_type: str, table: str, column: str) -> float:
        """Calculate index selectivity for a column.

        Args:
            db_path: Path to database
            db_type: Type of database
            table: Table name
            column: Column name

        Returns:
            Selectivity ratio (0.0 to 1.0)
        """
        with DatabaseConnection(db_path, db_type) as conn:
            # Get distinct count
            distinct_query = f'SELECT COUNT(DISTINCT "{column}") FROM "{table}"'  # nosec B608
            distinct_result = conn.fetchone(distinct_query)
            distinct_count = distinct_result[0] if distinct_result else 0

            # Get total count
            total_query = f'SELECT COUNT(*) FROM "{table}"'  # nosec B608
            total_result = conn.fetchone(total_query)
            total_count = total_result[0] if total_result else 0

            if total_count == 0:
                return 0.0

            return distinct_count / total_count

    def estimate_index_size(self: IndexOptimizer, db_path: str, db_type: str, index_name: str) -> int:
        """Estimate index size in bytes.

        Args:
            db_path: Path to database
            db_type: Type of database
            index_name: Index name

        Returns:
            Estimated size in bytes
        """
        # Placeholder implementation
        return 0

    def generate_report(self: IndexOptimizer, analysis: Dict[str, Any], output_path: str) -> None:
        """Generate index optimization report.

        Args:
            analysis: Analysis results
            output_path: Path to save report
        """
        self.report_generator.generate_json_report(analysis, output_path)

    def _parse_index_columns(self: IndexOptimizer, sql: str) -> List[str]:
        """Parse column names from CREATE INDEX SQL.

        Args:
            sql: CREATE INDEX SQL statement

        Returns:
            List of column names
        """
        # Extract columns from SQL
        match = re.search(r"\((.*?)\)", sql)
        if match:
            col_str = match.group(1)
            # Split by comma and clean up
            columns = [col.strip().strip('"').strip("'") for col in col_str.split(",")]
            return columns
        return []

    def _detect_redundant_indexes(self: IndexOptimizer, indexes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect redundant indexes.

        Args:
            indexes: List of existing indexes

        Returns:
            List of redundant indexes
        """
        redundant = []

        # Group indexes by table
        by_table: Dict[str, List[Dict[str, Any]]] = {}
        for idx in indexes:
            table = idx.get("table", "")
            if table not in by_table:
                by_table[table] = []
            by_table[table].append(idx)

        # Check for redundancy within each table
        for table, table_indexes in by_table.items():
            for i, idx1 in enumerate(table_indexes):
                cols1 = idx1.get("columns", [])
                if not cols1:
                    continue

                for idx2 in table_indexes[i + 1 :]:
                    cols2 = idx2.get("columns", [])
                    if not cols2:
                        continue

                    # Check if one is a prefix of the other
                    if cols1 == cols2[: len(cols1)] or cols2 == cols1[: len(cols2)]:
                        redundant.append(
                            {
                                "index1": idx1["name"],
                                "index2": idx2["name"],
                                "reason": "Overlapping columns",
                            }
                        )

        return redundant

    def _analyze_query_patterns(self: IndexOptimizer, queries: List[str]) -> List[Dict[str, Any]]:
        """Analyze query patterns for composite index opportunities.

        Args:
            queries: List of SQL queries

        Returns:
            List of composite index recommendations
        """
        recommendations = []

        for query in queries:
            # Look for WHERE clauses with multiple conditions
            where_match = re.search(r"WHERE\s+(.*?)(?:GROUP BY|ORDER BY|LIMIT|$)", query, re.IGNORECASE)

            if where_match:
                where_clause = where_match.group(1)

                # Extract column names
                columns = re.findall(r"(\w+)\s*=", where_clause)

                if len(columns) >= 2:
                    recommendations.append(
                        {
                            "columns": columns,
                            "reason": "Multi-column WHERE clause",
                            "query": query,
                        }
                    )

        return recommendations


def calculate_index_benefit(query_time_without: float, query_time_with: float) -> float:
    """Calculate index benefit as percentage improvement.

    Args:
        query_time_without: Query time without index
        query_time_with: Query time with index

    Returns:
        Percentage improvement
    """
    if query_time_without == 0:
        return 0.0

    return ((query_time_without - query_time_with) / query_time_without) * 100


def identify_covering_indexes(query: str, table_columns: List[str]) -> List[str]:
    """Identify columns that would benefit from covering indexes.

    Args:
        query: SQL query
        table_columns: Available table columns

    Returns:
        List of column names for covering index
    """
    columns = []

    # Extract columns from SELECT clause
    select_match = re.search(r"SELECT\s+(.*?)\s+FROM", query, re.IGNORECASE)
    if select_match:
        select_clause = select_match.group(1)

        if select_clause.strip() != "*":
            # Extract column names
            cols = [col.strip() for col in select_clause.split(",")]
            columns.extend([col for col in cols if col in table_columns])

    # Extract columns from WHERE clause
    where_match = re.search(r"WHERE\s+(.*?)(?:GROUP BY|ORDER BY|LIMIT|$)", query, re.IGNORECASE)
    if where_match:
        where_clause = where_match.group(1)
        where_cols = re.findall(r"(\w+)\s*=", where_clause)
        columns.extend([col for col in where_cols if col in table_columns])

    return list(set(columns))


def main() -> None:
    """Optimize database indexes."""
    parser = argparse.ArgumentParser(description="Optimize database indexes")
    parser.add_argument("--db-path", required=True, help="Path to database")
    parser.add_argument("--db-type", default="sqlite", help="Database type")
    parser.add_argument("--implement-changes", action="store_true", help="Actually create indexes")
    parser.add_argument("--output", default="index_report.json", help="Output report path")

    args = parser.parse_args()

    optimizer = IndexOptimizer()

    print(f"Analyzing indexes in: {args.db_path}")

    # Analyze existing indexes
    analysis = optimizer.analyze_indexes(args.db_path, args.db_type)
    print(f"\nFound {len(analysis['existing_indexes'])} existing indexes")
    print(f"Found {len(analysis['redundant_indexes'])} redundant indexes")

    # Get recommendations
    recommendations = optimizer.recommend_indexes(args.db_path, args.db_type)
    print(f"\nRecommending {len(recommendations['recommended_indexes'])} new indexes")

    # Implement changes if requested
    if args.implement_changes:
        print("\nImplementing index changes...")

        for rec in recommendations["recommended_indexes"]:
            print(f"  Creating index: {rec['index_name']}")
            success = optimizer.create_index(
                args.db_path,
                args.db_type,
                rec["table"],
                columns=rec["columns"],
                index_name=rec["index_name"],
            )
            print(f"  Result: {'Success' if success else 'Failed'}")

    # Generate report
    report_data = {"analysis": analysis, "recommendations": recommendations}
    optimizer.generate_report(report_data, args.output)
    print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()
