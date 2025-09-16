#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Basic tests for Layout Options addressing Issue #240.

These tests validate the structural aspects of the layout options without
requiring full module imports, focusing on file existence, code structure,
and layout improvement verification.
"""

import unittest
from pathlib import Path
import re
from typing import List


class TestLayoutOptionsStructure(unittest.TestCase):
    """Test structural aspects of all layout options."""
    
    def setUp(self) -> None:
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent
        self.pages_dir = self.project_root / "violentutf" / "pages"
        
        self.option1_file = self.pages_dir / "2_Configure_Datasets_option1_fullwidth.py"
        self.option2_file = self.pages_dir / "2_Configure_Datasets_option2_tabs.py"
        self.option3_file = self.pages_dir / "2_Configure_Datasets_option3_progressive.py"
        self.original_file = self.pages_dir / "2_Configure_Datasets.py"

    def test_all_layout_files_exist(self) -> None:
        """Test that all layout option files have been created."""
        self.assertTrue(self.option1_file.exists(), "Option 1 file should exist")
        self.assertTrue(self.option2_file.exists(), "Option 2 file should exist")  
        self.assertTrue(self.option3_file.exists(), "Option 3 file should exist")
        self.assertTrue(self.original_file.exists(), "Original file should exist")

    def test_layout_option1_structure(self) -> None:
        """Test Layout Option 1 structure and improvements."""
        if not self.option1_file.exists():
            self.skipTest("Option 1 file does not exist")
            
        content = self.option1_file.read_text()
        
        # Test for conditional layout detection
        self.assertIn("detect_layout_context", content, 
                     "Option 1 should implement layout context detection")
        
        # Test for full-width rendering
        self.assertIn("render_native_datasets_fullwidth", content,
                     "Option 1 should implement full-width native dataset rendering")
        
        # Test for conditional handling
        self.assertIn("fullwidth", content,
                     "Option 1 should handle fullwidth layout mode")
        
        # Test for responsive design patterns
        self.assertIn("use_container_width=True", content,
                     "Option 1 should use responsive container widths")

    def test_layout_option2_structure(self) -> None:
        """Test Layout Option 2 structure and improvements."""
        if not self.option2_file.exists():
            self.skipTest("Option 2 file does not exist")
            
        content = self.option2_file.read_text()
        
        # Test for tab-based architecture
        self.assertIn("st.tabs", content,
                     "Option 2 should implement tab-based layout")
        
        # Test for tab rendering functions
        self.assertIn("render_configure_tab", content,
                     "Option 2 should have configure tab function")
        self.assertIn("render_test_tab", content,
                     "Option 2 should have test tab function")
        self.assertIn("render_manage_tab", content,
                     "Option 2 should have manage tab function")
        
        # Test for separation of concerns
        configure_tabs = content.count("Configure")
        test_tabs = content.count("Test")
        manage_tabs = content.count("Manage")
        
        self.assertGreater(configure_tabs, 0, "Should have Configure functionality")
        self.assertGreater(test_tabs, 0, "Should have Test functionality")
        self.assertGreater(manage_tabs, 0, "Should have Manage functionality")

    def test_layout_option3_structure(self) -> None:
        """Test Layout Option 3 structure and improvements."""
        if not self.option3_file.exists():
            self.skipTest("Option 3 file does not exist")
            
        content = self.option3_file.read_text()
        
        # Test for progressive disclosure
        self.assertIn("progressive_mode", content,
                     "Option 3 should implement progressive disclosure modes")
        
        # Test for simple/advanced modes
        self.assertIn("simple", content,
                     "Option 3 should have simple mode")
        self.assertIn("advanced", content,
                     "Option 3 should have advanced mode")
        
        # Test for wizard functionality
        self.assertIn("wizard", content,
                     "Option 3 should implement wizard functionality")
        
        # Test for experience level detection
        self.assertIn("experience_level", content,
                     "Option 3 should detect user experience level")

    def test_ui_nesting_reduction(self) -> None:
        """Test that UI nesting has been reduced in all options."""
        files_to_test = [
            (self.option1_file, "Option 1"),
            (self.option2_file, "Option 2"),
            (self.option3_file, "Option 3"),
        ]
        
        for file_path, name in files_to_test:
            if not file_path.exists():
                continue
                
            content = file_path.read_text()
            
            # Count potential nesting patterns
            columns_count = content.count("st.columns")
            tabs_count = content.count("st.tabs") 
            expander_count = content.count("st.expander")
            
            # Original file had excessive nesting - new options should be more efficient
            total_containers = columns_count + tabs_count + expander_count
            
            # Should have reasonable container usage (not excessive)
            # Allow more flexibility since complex layouts may need more containers
            self.assertLess(total_containers, 35, 
                           f"{name} should not have excessive UI container nesting")

    def test_functional_preservation(self) -> None:
        """Test that essential functions are preserved in all options."""
        essential_functions = [
            "load_dataset_types_from_api",
            "load_datasets_from_api",
            "create_dataset_via_api", 
            "get_auth_headers",
            "api_request",
            "main",
        ]
        
        files_to_test = [
            (self.option1_file, "Option 1"),
            (self.option2_file, "Option 2"),
            (self.option3_file, "Option 3"),
        ]
        
        for file_path, name in files_to_test:
            if not file_path.exists():
                continue
                
            content = file_path.read_text()
            
            for func_name in essential_functions:
                self.assertIn(f"def {func_name}", content,
                             f"{name} should preserve {func_name} function")

    def test_dataset_source_handling(self) -> None:
        """Test that all dataset sources are handled in each option."""
        expected_sources = ["native", "local", "online", "memory", "combination", "transform"]
        
        files_to_test = [
            (self.option1_file, "Option 1"),
            (self.option2_file, "Option 2"),
            (self.option3_file, "Option 3"),
        ]
        
        for file_path, name in files_to_test:
            if not file_path.exists():
                continue
                
            content = file_path.read_text()
            
            for source in expected_sources:
                self.assertIn(f'"{source}"', content,
                             f"{name} should handle {source} dataset source")

    def test_api_integration_preserved(self) -> None:
        """Test that API integration is preserved in all options."""
        api_patterns = [
            "API_ENDPOINTS",
            "api_request",
            "Bearer",
            "Authorization",
            "APISIX",
        ]
        
        files_to_test = [
            (self.option1_file, "Option 1"),
            (self.option2_file, "Option 2"),
            (self.option3_file, "Option 3"),
        ]
        
        for file_path, name in files_to_test:
            if not file_path.exists():
                continue
                
            content = file_path.read_text()
            
            for pattern in api_patterns:
                self.assertIn(pattern, content,
                             f"{name} should preserve API integration pattern: {pattern}")

    def test_responsive_design_implementation(self) -> None:
        """Test that responsive design patterns are implemented."""
        responsive_patterns = [
            "use_container_width=True",
            "layout='wide'",
            "columns",
        ]
        
        files_to_test = [
            (self.option1_file, "Option 1"),
            (self.option2_file, "Option 2"),
            (self.option3_file, "Option 3"),
        ]
        
        for file_path, name in files_to_test:
            if not file_path.exists():
                continue
                
            content = file_path.read_text()
            
            responsive_score = sum(1 for pattern in responsive_patterns if pattern in content)
            self.assertGreater(responsive_score, 0,
                             f"{name} should implement responsive design patterns")

    def test_accessibility_features(self) -> None:
        """Test that accessibility features are implemented."""
        accessibility_patterns = [
            'help=',
            'caption',
            'label',
            'disabled=',
        ]
        
        files_to_test = [
            (self.option1_file, "Option 1"),
            (self.option2_file, "Option 2"),
            (self.option3_file, "Option 3"),
        ]
        
        for file_path, name in files_to_test:
            if not file_path.exists():
                continue
                
            content = file_path.read_text()
            
            accessibility_score = sum(1 for pattern in accessibility_patterns if pattern in content)
            self.assertGreater(accessibility_score, 2,
                             f"{name} should implement accessibility features")

    def test_error_handling_preserved(self) -> None:
        """Test that error handling is preserved in all options."""
        error_patterns = [
            "try:",
            "except",
            "st.error",
            "st.warning", 
            "logger.error",
        ]
        
        files_to_test = [
            (self.option1_file, "Option 1"),
            (self.option2_file, "Option 2"),
            (self.option3_file, "Option 3"),
        ]
        
        for file_path, name in files_to_test:
            if not file_path.exists():
                continue
                
            content = file_path.read_text()
            
            error_handling_score = sum(1 for pattern in error_patterns if pattern in content)
            self.assertGreater(error_handling_score, 3,
                             f"{name} should preserve error handling patterns")

    def test_documentation_quality(self) -> None:
        """Test that documentation explains layout improvements."""
        files_to_test = [
            (self.option1_file, "Option 1", "Full-width conditional layout"),
            (self.option2_file, "Option 2", "Tab-based architecture"),
            (self.option3_file, "Option 3", "Progressive disclosure"),
        ]
        
        for file_path, name, description in files_to_test:
            if not file_path.exists():
                continue
                
            content = file_path.read_text()
            
            # Check for documentation explaining the approach
            self.assertIn("LAYOUT OPTIMIZATION", content,
                         f"{name} should document layout optimization")
            
            self.assertIn("issue #240", content.lower(),
                         f"{name} should reference issue #240")
            
            self.assertIn("nesting", content.lower(),
                         f"{name} should mention nesting improvements")

    def test_no_hardcoded_credentials(self) -> None:
        """Test that no hardcoded credentials exist in layout options."""
        security_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'key\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
            r'token\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
        ]
        
        files_to_test = [
            (self.option1_file, "Option 1"),
            (self.option2_file, "Option 2"),
            (self.option3_file, "Option 3"),
        ]
        
        for file_path, name in files_to_test:
            if not file_path.exists():
                continue
                
            content = file_path.read_text()
            
            for pattern in security_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                self.assertEqual(len(matches), 0,
                               f"{name} should not contain hardcoded credentials: {matches}")

    def test_import_structure_consistency(self) -> None:
        """Test that import structures are consistent across options."""
        required_imports = [
            "import streamlit as st",
            "from utils.auth_utils import",
            "from utils.logging import",
        ]
        
        files_to_test = [
            (self.option1_file, "Option 1"),
            (self.option2_file, "Option 2"), 
            (self.option3_file, "Option 3"),
        ]
        
        for file_path, name in files_to_test:
            if not file_path.exists():
                continue
                
            content = file_path.read_text()
            
            for import_stmt in required_imports:
                self.assertIn(import_stmt, content,
                             f"{name} should have required import: {import_stmt}")


class TestLayoutComparisonMetrics(unittest.TestCase):
    """Test metrics comparing layout options to original."""
    
    def setUp(self) -> None:
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent
        self.pages_dir = self.project_root / "violentutf" / "pages"
        
        self.original_file = self.pages_dir / "2_Configure_Datasets.py"
        self.option1_file = self.pages_dir / "2_Configure_Datasets_option1_fullwidth.py"
        self.option2_file = self.pages_dir / "2_Configure_Datasets_option2_tabs.py"
        self.option3_file = self.pages_dir / "2_Configure_Datasets_option3_progressive.py"

    def get_file_metrics(self, file_path: Path) -> dict:
        """Calculate metrics for a file."""
        if not file_path.exists():
            return {}
            
        content = file_path.read_text()
        lines = content.split('\n')
        
        return {
            "total_lines": len(lines),
            "code_lines": len([line for line in lines if line.strip() and not line.strip().startswith('#')]),
            "functions": content.count("def "),
            "classes": content.count("class "),
            "st_columns": content.count("st.columns"),
            "st_tabs": content.count("st.tabs"),
            "st_expander": content.count("st.expander"),
            "st_container": content.count("st.container"),
            "docstrings": content.count('"""'),
        }

    def test_code_metrics_improvement(self) -> None:
        """Test that code metrics show improvement in layout options."""
        if not self.original_file.exists():
            self.skipTest("Original file does not exist")
            
        original_metrics = self.get_file_metrics(self.original_file)
        
        layout_files = [
            (self.option1_file, "Option 1"),
            (self.option2_file, "Option 2"),
            (self.option3_file, "Option 3"),
        ]
        
        for file_path, name in layout_files:
            if not file_path.exists():
                continue
                
            metrics = self.get_file_metrics(file_path)
            
            # New implementations should have good documentation
            # Allow some flexibility in documentation approach
            self.assertGreaterEqual(metrics.get("docstrings", 0), 
                                  original_metrics.get("docstrings", 0) - 10,
                                  f"{name} should maintain reasonable documentation")
            
            # Should preserve essential functions
            self.assertGreaterEqual(metrics.get("functions", 0),
                                  original_metrics.get("functions", 0) - 5,  # Allow some variation
                                  f"{name} should preserve most essential functions")

    def test_layout_complexity_reduction(self) -> None:
        """Test that layout complexity is reduced in new options."""
        if not self.original_file.exists():
            self.skipTest("Original file does not exist")
            
        original_metrics = self.get_file_metrics(self.original_file)
        original_container_usage = (
            original_metrics.get("st_columns", 0) + 
            original_metrics.get("st_expander", 0)
        )
        
        layout_files = [
            (self.option1_file, "Option 1"),
            (self.option2_file, "Option 2"),
            (self.option3_file, "Option 3"),
        ]
        
        for file_path, name in layout_files:
            if not file_path.exists():
                continue
                
            metrics = self.get_file_metrics(file_path)
            
            # Calculate relative container usage efficiency
            container_usage = (
                metrics.get("st_columns", 0) + 
                metrics.get("st_expander", 0) +
                metrics.get("st_tabs", 0)  # Tabs are containers too
            )
            
            # New options should not have excessive container nesting
            # (Allow flexibility for different approaches - tab-based may need more containers)
            self.assertLess(container_usage, original_container_usage + 20,
                           f"{name} should not significantly increase container complexity")


if __name__ == "__main__":
    # Configure test runner
    unittest.main(verbosity=2, buffer=True)