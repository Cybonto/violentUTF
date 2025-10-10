# Copyright (c) 2024 ViolentUTF Project
# Licensed under MIT License

"""
Tests for Issue #134: Documentation and User Guides for Dataset Integration
Tests documentation completeness and structure validation
"""

import re
from pathlib import Path
from typing import Dict, List, Set

import pytest
import yaml


class TestIssue134DocumentationCompleteness:
    """Test completeness of dataset integration documentation"""

    @pytest.fixture
    def docs_base_path(self) -> Path:
        """Base path for documentation directory"""
        return Path(__file__).parent.parent / "docs"

    @pytest.fixture
    def required_guide_files(self) -> List[str]:
        """List of required guide files from issue specification"""
        return [
            "guides/Guide_Dataset_Integration_Overview.md",
            "guides/Guide_Dataset_Selection_Workflows.md",
            "guides/Guide_Cognitive_Behavioral_Assessment.md",
            "guides/Guide_RedTeaming_Evaluation.md",
            "guides/Guide_Legal_Reasoning_Assessment.md",
            "guides/Guide_Mathematical_Reasoning_Evaluation.md",
            "guides/Guide_Spatial_Graph_Reasoning.md",
            "guides/Guide_Privacy_Evaluation.md",
            "guides/Guide_Meta_Evaluation_Workflows.md",
        ]

    @pytest.fixture
    def required_troubleshooting_files(self) -> List[str]:
        """List of required troubleshooting files"""
        return [
            "troubleshooting/Troubleshooting_Dataset_Integration.md",
            "troubleshooting/Troubleshooting_Large_File_Processing.md",
            "troubleshooting/Troubleshooting_Performance_Issues.md",
        ]

    @pytest.fixture
    def required_best_practices_files(self) -> List[str]:
        """List of required best practices files"""
        return [
            "plans/Best_Practices_Dataset_Evaluation.md",
            "plans/Performance_Optimization_Guide.md",
            "plans/Advanced_Evaluation_Methodologies.md",
        ]

    @pytest.fixture
    def required_content_sections(self) -> List[str]:
        """Required sections for each guide"""
        return [
            "Overview",
            "Quick Start",
            "Configuration",
            "Use Cases",
            "Best Practices",
            "Troubleshooting",
        ]

    def test_required_guide_files_exist(self, docs_base_path: Path, required_guide_files: List[str]):
        """Test that all required guide files exist"""
        missing_files = []
        for file_path in required_guide_files:
            full_path = docs_base_path / file_path
            if not full_path.exists():
                missing_files.append(str(full_path))

        assert not missing_files, f"Missing required guide files: {missing_files}"

    def test_required_troubleshooting_files_exist(
        self, docs_base_path: Path, required_troubleshooting_files: List[str]
    ):
        """Test that all required troubleshooting files exist"""
        missing_files = []
        for file_path in required_troubleshooting_files:
            full_path = docs_base_path / file_path
            if not full_path.exists():
                missing_files.append(str(full_path))

        assert not missing_files, f"Missing required troubleshooting files: {missing_files}"

    def test_required_best_practices_files_exist(
        self, docs_base_path: Path, required_best_practices_files: List[str]
    ):
        """Test that all required best practices files exist"""
        missing_files = []
        for file_path in required_best_practices_files:
            full_path = docs_base_path / file_path
            if not full_path.exists():
                missing_files.append(str(full_path))

        assert not missing_files, f"Missing required best practices files: {missing_files}"

    def test_guide_file_content_structure(self, docs_base_path: Path, required_guide_files: List[str]):
        """Test that guide files have required content structure"""
        structure_errors = []

        for file_path in required_guide_files:
            full_path = docs_base_path / file_path
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8")
                errors = self._validate_guide_structure(content, str(full_path))
                structure_errors.extend(errors)

        assert not structure_errors, f"Guide structure errors: {structure_errors}"

    def test_troubleshooting_file_content_structure(
        self, docs_base_path: Path, required_troubleshooting_files: List[str]
    ):
        """Test that troubleshooting files have required structure"""
        structure_errors = []

        for file_path in required_troubleshooting_files:
            full_path = docs_base_path / file_path
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8")
                errors = self._validate_troubleshooting_structure(content, str(full_path))
                structure_errors.extend(errors)

        assert not structure_errors, f"Troubleshooting structure errors: {structure_errors}"

    def test_best_practices_file_content_structure(
        self, docs_base_path: Path, required_best_practices_files: List[str]
    ):
        """Test that best practices files have required structure"""
        structure_errors = []

        for file_path in required_best_practices_files:
            full_path = docs_base_path / file_path
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8")
                errors = self._validate_best_practices_structure(content, str(full_path))
                structure_errors.extend(errors)

        assert not structure_errors, f"Best practices structure errors: {structure_errors}"

    def test_file_content_minimum_length(self, docs_base_path: Path):
        """Test that documentation files have substantial content"""
        all_required_files = [
            "guides/Guide_Dataset_Integration_Overview.md",
            "guides/Guide_Dataset_Selection_Workflows.md",
            "guides/Guide_Cognitive_Behavioral_Assessment.md",
            "guides/Guide_RedTeaming_Evaluation.md",
            "guides/Guide_Legal_Reasoning_Assessment.md",
            "guides/Guide_Mathematical_Reasoning_Evaluation.md",
            "guides/Guide_Spatial_Graph_Reasoning.md",
            "guides/Guide_Privacy_Evaluation.md",
            "guides/Guide_Meta_Evaluation_Workflows.md",
            "troubleshooting/Troubleshooting_Dataset_Integration.md",
            "troubleshooting/Troubleshooting_Large_File_Processing.md",
            "troubleshooting/Troubleshooting_Performance_Issues.md",
            "plans/Best_Practices_Dataset_Evaluation.md",
            "plans/Performance_Optimization_Guide.md",
            "plans/Advanced_Evaluation_Methodologies.md",
        ]

        short_files = []
        min_content_length = 1000  # Minimum 1000 characters for substantial content

        for file_path in all_required_files:
            full_path = docs_base_path / file_path
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8").strip()
                if len(content) < min_content_length:
                    short_files.append(f"{file_path}: {len(content)} chars")

        assert not short_files, f"Files with insufficient content: {short_files}"

    def test_cross_reference_completeness(self, docs_base_path: Path):
        """Test that files have proper cross-references to related documentation"""
        all_files = list((docs_base_path / "guides").glob("Guide_*.md"))
        all_files.extend((docs_base_path / "troubleshooting").glob("Troubleshooting_*.md"))
        all_files.extend((docs_base_path / "plans").glob("*.md"))

        missing_references = []

        for doc_file in all_files:
            if doc_file.exists():
                content = doc_file.read_text(encoding="utf-8")
                references = self._extract_internal_links(content)

                # Each guide should reference at least 2 other related documents
                if len(references) < 2:
                    missing_references.append(f"{doc_file.name}: only {len(references)} references")

        assert not missing_references, f"Files with insufficient cross-references: {missing_references}"

    def test_dataset_coverage_completeness(self, docs_base_path: Path):
        """Test that all major dataset types are documented"""
        required_datasets = {
            "OllaGen1",  # Cognitive Behavioral Assessment
            "Garak",     # Red-teaming Evaluation
            "LegalBench",  # Legal Reasoning
            "DocMath",   # Mathematical Reasoning
            "GraphWalk", # Spatial Graph Reasoning
            "ConfAIde",  # Privacy Evaluation
            "JudgeBench", # Meta-evaluation
            "ACPBench",  # Additional coverage
        }

        documented_datasets = set()
        guide_files = list((docs_base_path / "guides").glob("Guide_*.md"))

        for guide_file in guide_files:
            if guide_file.exists():
                content = guide_file.read_text(encoding="utf-8")
                for dataset in required_datasets:
                    if dataset in content:
                        documented_datasets.add(dataset)

        missing_datasets = required_datasets - documented_datasets
        assert not missing_datasets, f"Undocumented datasets: {missing_datasets}"

    def _validate_guide_structure(self, content: str, file_path: str) -> List[str]:
        """Validate that a guide has the required structure"""
        errors = []

        # Check for required sections
        required_sections = ["# Overview", "# Quick Start", "# Configuration", "# Use Cases"]
        for section in required_sections:
            if section not in content and section.replace("# ", "## ") not in content:
                errors.append(f"{file_path}: Missing section '{section}'")

        # Check for code examples
        if "```" not in content:
            errors.append(f"{file_path}: No code examples found")

        # Check for configuration tables or examples
        if "configuration" not in content.lower() and "config" not in content.lower():
            errors.append(f"{file_path}: No configuration information found")

        return errors

    def _validate_troubleshooting_structure(self, content: str, file_path: str) -> List[str]:
        """Validate troubleshooting document structure"""
        errors = []

        # Check for problem/solution structure
        required_patterns = [
            r"problem|issue|error",
            r"solution|fix|resolution",
            r"symptoms?",
        ]

        for pattern in required_patterns:
            if not re.search(pattern, content, re.IGNORECASE):
                errors.append(f"{file_path}: Missing troubleshooting pattern '{pattern}'")

        return errors

    def _validate_best_practices_structure(self, content: str, file_path: str) -> List[str]:
        """Validate best practices document structure"""
        errors = []

        # Check for best practices content
        required_elements = [
            "best practices",
            "recommendations",
            "guidelines",
            "performance",
        ]

        for element in required_elements:
            if element not in content.lower():
                errors.append(f"{file_path}: Missing best practices element '{element}'")

        return errors

    def _extract_internal_links(self, content: str) -> List[str]:
        """Extract internal documentation links from content"""
        # Find markdown links that reference other documentation files
        link_pattern = r"\[([^\]]+)\]\(([^)]+\.md)\)"
        matches = re.findall(link_pattern, content)
        return [match[1] for match in matches if not match[1].startswith("http")]


class TestIssue134DocumentationQuality:
    """Test quality aspects of documentation"""

    @pytest.fixture
    def docs_base_path(self) -> Path:
        """Base path for documentation directory"""
        return Path(__file__).parent.parent / "docs"

    def test_markdown_syntax_validity(self, docs_base_path: Path):
        """Test that all markdown files have valid syntax"""
        markdown_files = []
        markdown_files.extend((docs_base_path / "guides").glob("Guide_*.md"))
        markdown_files.extend((docs_base_path / "troubleshooting").glob("Troubleshooting_*.md"))
        markdown_files.extend((docs_base_path / "plans").glob("*.md"))

        syntax_errors = []

        for md_file in markdown_files:
            if md_file.exists():
                content = md_file.read_text(encoding="utf-8")
                errors = self._validate_markdown_syntax(content, str(md_file))
                syntax_errors.extend(errors)

        assert not syntax_errors, f"Markdown syntax errors: {syntax_errors}"

    def test_heading_hierarchy_consistency(self, docs_base_path: Path):
        """Test that heading levels are properly structured"""
        markdown_files = []
        markdown_files.extend((docs_base_path / "guides").glob("Guide_*.md"))
        markdown_files.extend((docs_base_path / "troubleshooting").glob("Troubleshooting_*.md"))
        markdown_files.extend((docs_base_path / "plans").glob("*.md"))

        hierarchy_errors = []

        for md_file in markdown_files:
            if md_file.exists():
                content = md_file.read_text(encoding="utf-8")
                errors = self._validate_heading_hierarchy(content, str(md_file))
                hierarchy_errors.extend(errors)

        assert not hierarchy_errors, f"Heading hierarchy errors: {hierarchy_errors}"

    def test_consistent_terminology(self, docs_base_path: Path):
        """Test that documentation uses consistent terminology"""
        markdown_files = []
        markdown_files.extend((docs_base_path / "guides").glob("Guide_*.md"))
        markdown_files.extend((docs_base_path / "troubleshooting").glob("Troubleshooting_*.md"))
        markdown_files.extend((docs_base_path / "plans").glob("*.md"))

        # Define preferred terminology
        terminology_rules = {
            "dataset": ["data set", "data-set"],  # Prefer "dataset"
            "ViolentUTF": ["violent utf", "violentutf"],  # Prefer "ViolentUTF"
            "evaluation": ["assesment"],  # Prefer "evaluation" over "assessment" (except for specific contexts)
        }

        terminology_errors = []

        for md_file in markdown_files:
            if md_file.exists():
                content = md_file.read_text(encoding="utf-8")
                for preferred, alternatives in terminology_rules.items():
                    for alt in alternatives:
                        if alt in content.lower() and preferred.lower() not in content.lower():
                            terminology_errors.append(f"{md_file.name}: Use '{preferred}' instead of '{alt}'")

        assert not terminology_errors, f"Terminology consistency errors: {terminology_errors}"

    def _validate_markdown_syntax(self, content: str, file_path: str) -> List[str]:
        """Validate basic markdown syntax"""
        errors = []
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for unclosed code blocks
            if line.strip().startswith("```") and not line.strip().endswith("```"):
                # This is a code block opener, check if it's closed
                code_block_closed = False
                for j in range(i, len(lines)):
                    if lines[j].strip() == "```":
                        code_block_closed = True
                        break
                if not code_block_closed:
                    errors.append(f"{file_path}:{i}: Unclosed code block")

            # Check for malformed links
            if "[" in line and "]" in line and "(" in line and ")" in line:
                # Basic link format validation
                link_pattern = r"\[([^\]]*)\]\(([^)]*)\)"
                matches = re.findall(link_pattern, line)
                for match in matches:
                    if not match[0]:  # Empty link text
                        errors.append(f"{file_path}:{i}: Empty link text")
                    if not match[1]:  # Empty link URL
                        errors.append(f"{file_path}:{i}: Empty link URL")

        return errors

    def _validate_heading_hierarchy(self, content: str, file_path: str) -> List[str]:
        """Validate heading hierarchy is logical"""
        errors = []
        lines = content.split("\n")
        heading_levels = []

        for i, line in enumerate(lines, 1):
            if line.strip().startswith("#"):
                level = len(line.split()[0])  # Count # characters
                heading_levels.append((level, i))

        # Check for logical hierarchy (no level should jump by more than 1)
        for i in range(1, len(heading_levels)):
            prev_level, prev_line = heading_levels[i - 1]
            curr_level, curr_line = heading_levels[i]

            if curr_level > prev_level + 1:
                errors.append(
                    f"{file_path}:{curr_line}: "
                    f"Heading level jump from {prev_level} to {curr_level} (should be sequential)"
                )

        return errors


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])