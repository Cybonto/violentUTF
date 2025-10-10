# Copyright (c) 2024 ViolentUTF Project
# Licensed under MIT License

"""
Tests for Issue #134: Documentation User Workflow Validation
Tests that users can successfully complete tasks following the documentation
"""

import tempfile
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch

import pytest
import yaml


class TestIssue134UserWorkflows:
    """Test user workflow scenarios with dataset integration documentation"""

    @pytest.fixture
    def docs_base_path(self) -> Path:
        """Base path for documentation directory"""
        return Path(__file__).parent.parent / "docs"

    @pytest.fixture
    def user_scenarios(self) -> Dict:
        """Define user scenarios for testing"""
        return {
            "beginner": {
                "goal": "Complete first dataset evaluation",
                "max_time_minutes": 15,
                "success_criteria": [
                    "can_select_dataset",
                    "can_configure_basic_evaluation",
                    "can_understand_results",
                ],
            },
            "intermediate": {
                "goal": "Configure complex evaluation with multiple datasets",
                "max_time_minutes": 30,
                "success_criteria": [
                    "can_select_multiple_datasets",
                    "can_configure_advanced_options",
                    "can_optimize_performance",
                    "can_troubleshoot_issues",
                ],
            },
            "developer": {
                "goal": "Integrate new dataset type",
                "max_time_minutes": 60,
                "success_criteria": [
                    "can_understand_architecture",
                    "can_implement_converter",
                    "can_register_dataset",
                    "can_test_integration",
                ],
            },
            "administrator": {
                "goal": "Set up and maintain system",
                "max_time_minutes": 45,
                "success_criteria": [
                    "can_configure_system",
                    "can_monitor_performance",
                    "can_troubleshoot_system_issues",
                    "can_implement_optimizations",
                ],
            },
        }

    def test_beginner_user_workflow(self, docs_base_path: Path, user_scenarios: Dict):
        """Test that a beginner can complete their first dataset evaluation"""
        scenario = user_scenarios["beginner"]

        # Verify overview guide exists and is beginner-friendly
        overview_path = docs_base_path / "guides" / "Guide_Dataset_Integration_Overview.md"
        assert overview_path.exists(), "Dataset Integration Overview guide must exist"

        content = overview_path.read_text(encoding="utf-8")

        # Check for beginner-friendly sections
        beginner_requirements = [
            "quick start",
            "introduction",
            "first evaluation",
            "getting started",
        ]

        found_sections = []
        for req in beginner_requirements:
            if req in content.lower():
                found_sections.append(req)

        assert len(found_sections) >= 2, f"Overview guide needs beginner sections, found: {found_sections}"

        # Test workflow guidance
        workflow_path = docs_base_path / "guides" / "Guide_Dataset_Selection_Workflows.md"
        assert workflow_path.exists(), "Dataset Selection Workflows guide must exist"

        workflow_content = workflow_path.read_text(encoding="utf-8")

        # Check for decision trees or step-by-step guidance
        workflow_indicators = [
            "step 1",
            "first step",
            "decision tree",
            "workflow",
            "getting started",
        ]

        workflow_found = any(indicator in workflow_content.lower() for indicator in workflow_indicators)
        assert workflow_found, "Workflow guide must provide step-by-step guidance"

    def test_intermediate_user_workflow(self, docs_base_path: Path, user_scenarios: Dict):
        """Test that intermediate users can configure complex evaluations"""
        scenario = user_scenarios["intermediate"]

        # Check multiple dataset guides exist
        dataset_guides = [
            "Guide_Cognitive_Behavioral_Assessment.md",
            "Guide_RedTeaming_Evaluation.md",
            "Guide_Legal_Reasoning_Assessment.md",
            "Guide_Privacy_Evaluation.md",
        ]

        existing_guides = []
        for guide in dataset_guides:
            guide_path = docs_base_path / "guides" / guide
            if guide_path.exists():
                existing_guides.append(guide)

        assert len(existing_guides) >= 3, f"Need multiple dataset guides, found: {existing_guides}"

        # Check advanced configuration options
        for guide in existing_guides[:2]:  # Test first two guides
            guide_path = docs_base_path / "guides" / guide
            content = guide_path.read_text(encoding="utf-8")

            advanced_features = [
                "advanced",
                "configuration",
                "parameters",
                "optimization",
                "performance",
            ]

            found_features = sum(1 for feature in advanced_features if feature in content.lower())
            assert found_features >= 3, f"{guide} needs advanced configuration options"

    def test_developer_integration_workflow(self, docs_base_path: Path, user_scenarios: Dict):
        """Test that developers can integrate new dataset types"""
        scenario = user_scenarios["developer"]

        # Check for technical documentation
        tech_files = [
            "plans/Advanced_Evaluation_Methodologies.md",
            "plans/Performance_Optimization_Guide.md",
        ]

        for tech_file in tech_files:
            tech_path = docs_base_path / tech_file
            assert tech_path.exists(), f"Technical documentation {tech_file} must exist"

            content = tech_path.read_text(encoding="utf-8")

            # Check for developer-specific content
            dev_indicators = [
                "api",
                "implementation",
                "code",
                "class",
                "function",
                "integration",
            ]

            found_dev_content = sum(1 for indicator in dev_indicators if indicator in content.lower())
            assert found_dev_content >= 3, f"{tech_file} needs developer-focused content"

        # Check for code examples in guides
        guide_files = list((docs_base_path / "guides").glob("Guide_*.md"))
        code_examples_found = 0

        for guide_file in guide_files:
            if guide_file.exists():
                content = guide_file.read_text(encoding="utf-8")
                if "```python" in content or "```yaml" in content or "```json" in content:
                    code_examples_found += 1

        assert code_examples_found >= 3, f"Need code examples in guides, found: {code_examples_found}"

    def test_administrator_maintenance_workflow(self, docs_base_path: Path, user_scenarios: Dict):
        """Test that administrators can maintain and configure the system"""
        scenario = user_scenarios["administrator"]

        # Check for administrative documentation
        admin_files = [
            "plans/Performance_Optimization_Guide.md",
            "troubleshooting/Troubleshooting_Performance_Issues.md",
            "troubleshooting/Troubleshooting_Dataset_Integration.md",
        ]

        admin_content_found = 0
        for admin_file in admin_files:
            admin_path = docs_base_path / admin_file
            if admin_path.exists():
                content = admin_path.read_text(encoding="utf-8")

                admin_indicators = [
                    "configuration",
                    "monitoring",
                    "performance",
                    "optimization",
                    "troubleshooting",
                    "maintenance",
                ]

                found_admin_content = sum(1 for indicator in admin_indicators if indicator in content.lower())
                if found_admin_content >= 3:
                    admin_content_found += 1

        assert admin_content_found >= 2, f"Need administrative content in {admin_content_found} files"

    def test_troubleshooting_workflow_completeness(self, docs_base_path: Path):
        """Test that troubleshooting workflows cover common issues"""
        troubleshooting_files = [
            "troubleshooting/Troubleshooting_Dataset_Integration.md",
            "troubleshooting/Troubleshooting_Large_File_Processing.md",
            "troubleshooting/Troubleshooting_Performance_Issues.md",
        ]

        # Define common issues that should be covered
        common_issues = {
            "memory": ["memory", "ram", "out of memory"],
            "performance": ["slow", "performance", "timeout", "speed"],
            "file_processing": ["file", "processing", "upload", "format"],
            "configuration": ["configuration", "config", "setting", "parameter"],
            "connection": ["connection", "network", "api", "service"],
        }

        coverage_results = {}

        for trouble_file in troubleshooting_files:
            trouble_path = docs_base_path / trouble_file
            if trouble_path.exists():
                content = trouble_path.read_text(encoding="utf-8").lower()

                file_coverage = {}
                for issue_type, keywords in common_issues.items():
                    file_coverage[issue_type] = any(keyword in content for keyword in keywords)

                coverage_results[trouble_file] = file_coverage

        # Verify that each file covers relevant issues
        for trouble_file, coverage in coverage_results.items():
            covered_issues = sum(1 for covered in coverage.values() if covered)
            assert covered_issues >= 2, f"{trouble_file} should cover more common issues: {coverage}"

    def test_cross_workflow_navigation(self, docs_base_path: Path):
        """Test that users can navigate between related workflows"""
        all_files = []
        all_files.extend((docs_base_path / "guides").glob("Guide_*.md"))
        all_files.extend((docs_base_path / "troubleshooting").glob("Troubleshooting_*.md"))
        all_files.extend((docs_base_path / "plans").glob("*.md"))

        navigation_scores = {}

        for doc_file in all_files:
            if doc_file.exists():
                content = doc_file.read_text(encoding="utf-8")

                # Count internal links and references
                internal_links = content.count("](")
                see_also_count = content.lower().count("see also")
                reference_count = content.lower().count("refer to") + content.lower().count("see ")

                navigation_score = internal_links + (see_also_count * 2) + reference_count
                navigation_scores[doc_file.name] = navigation_score

        # Each document should have some navigation elements
        poor_navigation = [name for name, score in navigation_scores.items() if score < 2]
        assert not poor_navigation, f"Files with poor navigation: {poor_navigation}"

    def test_workflow_step_clarity(self, docs_base_path: Path):
        """Test that workflow steps are clearly defined and actionable"""
        workflow_files = list((docs_base_path / "guides").glob("Guide_*.md"))

        step_clarity_results = {}

        for workflow_file in workflow_files:
            if workflow_file.exists():
                content = workflow_file.read_text(encoding="utf-8")

                # Look for step indicators
                step_indicators = [
                    r"\d+\.",  # "1.", "2.", etc.
                    "step",
                    "first",
                    "next",
                    "then",
                    "finally",
                ]

                step_count = 0
                for indicator in step_indicators:
                    import re

                    matches = re.findall(indicator, content.lower())
                    step_count += len(matches)

                step_clarity_results[workflow_file.name] = step_count

        # Each workflow guide should have clear steps
        unclear_workflows = [name for name, count in step_clarity_results.items() if count < 5]
        assert not unclear_workflows, f"Workflows with unclear steps: {unclear_workflows}"

    def test_user_feedback_integration_points(self, docs_base_path: Path):
        """Test that documentation includes feedback and improvement mechanisms"""
        all_files = []
        all_files.extend((docs_base_path / "guides").glob("Guide_*.md"))
        all_files.extend((docs_base_path / "troubleshooting").glob("Troubleshooting_*.md"))

        feedback_mechanisms = 0

        for doc_file in all_files:
            if doc_file.exists():
                content = doc_file.read_text(encoding="utf-8").lower()

                feedback_indicators = [
                    "feedback",
                    "suggest",
                    "improve",
                    "report",
                    "issue",
                    "github",
                ]

                if any(indicator in content for indicator in feedback_indicators):
                    feedback_mechanisms += 1

        # At least 50% of files should have feedback mechanisms
        min_feedback_files = len(all_files) // 2
        assert (
            feedback_mechanisms >= min_feedback_files
        ), f"Need feedback mechanisms in more files: {feedback_mechanisms}/{len(all_files)}"


class TestIssue134WorkflowPerformance:
    """Test performance aspects of documentation workflows"""

    @pytest.fixture
    def docs_base_path(self) -> Path:
        """Base path for documentation directory"""
        return Path(__file__).parent.parent / "docs"

    def test_documentation_load_time(self, docs_base_path: Path):
        """Test that documentation files load quickly"""
        import time

        large_files = []
        load_times = {}

        all_files = []
        all_files.extend((docs_base_path / "guides").glob("Guide_*.md"))
        all_files.extend((docs_base_path / "troubleshooting").glob("Troubleshooting_*.md"))
        all_files.extend((docs_base_path / "plans").glob("*.md"))

        for doc_file in all_files:
            if doc_file.exists():
                start_time = time.time()
                content = doc_file.read_text(encoding="utf-8")
                end_time = time.time()

                load_time = end_time - start_time
                load_times[doc_file.name] = load_time

                # Files should load within 50ms for good UX
                if load_time > 0.05:
                    large_files.append(f"{doc_file.name}: {load_time:.3f}s")

        # Allow some files to be larger, but not too many
        assert len(large_files) <= 2, f"Too many slow-loading files: {large_files}"

    def test_content_size_optimization(self, docs_base_path: Path):
        """Test that documentation files are appropriately sized"""
        oversized_files = []
        undersized_files = []

        all_files = []
        all_files.extend((docs_base_path / "guides").glob("Guide_*.md"))
        all_files.extend((docs_base_path / "troubleshooting").glob("Troubleshooting_*.md"))
        all_files.extend((docs_base_path / "plans").glob("*.md"))

        for doc_file in all_files:
            if doc_file.exists():
                content = doc_file.read_text(encoding="utf-8")
                content_length = len(content)

                # Files should be substantial but not overwhelming
                if content_length < 500:  # Too short
                    undersized_files.append(f"{doc_file.name}: {content_length} chars")
                elif content_length > 50000:  # Too long for single file
                    oversized_files.append(f"{doc_file.name}: {content_length} chars")

        assert not undersized_files, f"Files with insufficient content: {undersized_files}"
        assert not oversized_files, f"Files that may need splitting: {oversized_files}"

    def test_search_optimization(self, docs_base_path: Path):
        """Test that documentation is optimized for searching"""
        all_files = []
        all_files.extend((docs_base_path / "guides").glob("Guide_*.md"))
        all_files.extend((docs_base_path / "troubleshooting").glob("Troubleshooting_*.md"))
        all_files.extend((docs_base_path / "plans").glob("*.md"))

        # Define key terms that should be easily searchable
        key_terms = [
            "dataset",
            "evaluation",
            "configuration",
            "performance",
            "troubleshooting",
            "workflow",
        ]

        search_coverage = {}

        for doc_file in all_files:
            if doc_file.exists():
                content = doc_file.read_text(encoding="utf-8").lower()

                file_coverage = {}
                for term in key_terms:
                    file_coverage[term] = content.count(term)

                search_coverage[doc_file.name] = file_coverage

        # Each file should have good coverage of relevant terms
        for file_name, coverage in search_coverage.items():
            total_key_terms = sum(coverage.values())
            unique_terms = sum(1 for count in coverage.values() if count > 0)

            assert unique_terms >= 3, f"{file_name} should cover more key terms: {coverage}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])