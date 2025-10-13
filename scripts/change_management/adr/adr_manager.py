# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
ADR (Architecture Decision Record) Manager.

Manages creation, tracking, and lifecycle of Architecture Decision Records.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ADRStatus(Enum):
    """ADR status values."""

    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"
    DEPRECATED = "deprecated"


class ADRManager:
    """Manages Architecture Decision Records."""

    ADR_TEMPLATE = """# ADR-{number}: {title}

**Status**: {status}
**Date**: {date}
**Author**: {author}
**Change Request**: {change_request_id}

## Context

{context}

## Decision

{decision}

## Consequences

### Positive
{positive_consequences}

### Negative
{negative_consequences}

## Related Decisions
{related_decisions}

## References
{references}
"""

    def __init__(self, adr_dir: Optional[Path] = None) -> None:
        """
        Initialize ADR manager.

        Args:
            adr_dir: Directory for storing ADRs
        """
        self.adr_dir = adr_dir or Path("docs/adr")
        self.adr_dir.mkdir(parents=True, exist_ok=True)
        self.adrs: Dict[int, Dict[str, Any]] = {}

    def create_adr(
        self,
        title: str,
        context: str,
        decision: str = "",
        change_request_id: str = "",
        author: str = "backend_engineer",
    ) -> int:
        """
        Create new ADR.

        Args:
            title: ADR title
            context: Decision context
            decision: Decision made
            change_request_id: Optional related change request
            author: ADR author

        Returns:
            ADR number
        """
        # Get next ADR number
        adr_number = self._get_next_adr_number()

        # Create ADR data
        adr = {
            "number": adr_number,
            "title": title,
            "status": ADRStatus.PROPOSED.value,
            "date": datetime.utcnow().isoformat(),
            "author": author,
            "context": context,
            "decision": decision,
            "change_request_id": change_request_id,
            "positive_consequences": [],
            "negative_consequences": [],
            "related_decisions": [],
            "references": [],
        }

        # Store ADR
        self.adrs[adr_number] = adr

        # Write ADR file
        self._write_adr_file(adr)

        return adr_number

    def update_adr_status(self, adr_id: int, status: ADRStatus) -> bool:
        """
        Update ADR status.

        Args:
            adr_id: ADR number
            status: New status

        Returns:
            Success status
        """
        if adr_id not in self.adrs:
            # Try to load from file
            self._load_adr(adr_id)

        if adr_id not in self.adrs:
            return False

        self.adrs[adr_id]["status"] = status.value
        self._write_adr_file(self.adrs[adr_id])

        return True

    def link_related_decisions(self, adr_id: int, related: List[int]) -> bool:
        """
        Link related ADRs.

        Args:
            adr_id: ADR number
            related: List of related ADR numbers

        Returns:
            Success status
        """
        if adr_id not in self.adrs:
            self._load_adr(adr_id)

        if adr_id not in self.adrs:
            return False

        self.adrs[adr_id]["related_decisions"] = related
        self._write_adr_file(self.adrs[adr_id])

        return True

    def search_adrs(self, query: str, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Search ADRs.

        Args:
            query: Search query
            filters: Optional filters

        Returns:
            List of matching ADRs
        """
        results = []

        # Load all ADRs
        for adr_file in self.adr_dir.glob("*.md"):
            content = adr_file.read_text()
            if query.lower() in content.lower():
                # Parse ADR number from filename
                try:
                    adr_num = int(adr_file.stem.split("-")[0].replace("ADR", ""))
                    if adr_num in self.adrs:
                        results.append(self.adrs[adr_num])
                except (ValueError, IndexError):
                    pass

        return results

    def _get_next_adr_number(self) -> int:
        """Get next ADR number."""
        existing_adrs = list(self.adr_dir.glob("*.md"))
        if not existing_adrs:
            return 1

        max_num = 0
        for adr_file in existing_adrs:
            try:
                num = int(adr_file.stem.split("-")[0])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                pass

        return max_num + 1

    def _write_adr_file(self, adr: Dict[str, Any]) -> None:
        """Write ADR to file."""
        filename = f"{adr['number']:03d}-{adr['title'].lower().replace(' ', '-')}.md"
        filepath = self.adr_dir / filename

        content = self.ADR_TEMPLATE.format(
            number=f"{adr['number']:03d}",
            title=adr["title"],
            status=adr["status"],
            date=adr["date"],
            author=adr["author"],
            change_request_id=adr.get("change_request_id", "N/A"),
            context=adr["context"],
            decision=adr.get("decision", "TBD"),
            positive_consequences="\n".join(f"- {c}" for c in adr.get("positive_consequences", [])) or "- TBD",
            negative_consequences="\n".join(f"- {c}" for c in adr.get("negative_consequences", [])) or "- TBD",
            related_decisions=", ".join(f"ADR-{r:03d}" for r in adr.get("related_decisions", [])) or "None",
            references="\n".join(f"- {r}" for r in adr.get("references", [])) or "- TBD",
        )

        filepath.write_text(content)

    def _load_adr(self, adr_id: int) -> None:
        """Load ADR from file."""
        # Try to find ADR file
        for _ in self.adr_dir.glob(f"{adr_id:03d}-*.md"):
            # Parse ADR from file (simplified)
            self.adrs[adr_id] = {
                "number": adr_id,
                "title": "Loaded ADR",
                "status": "unknown",
            }
            return
