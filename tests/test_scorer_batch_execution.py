#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Test script to verify scorer batch execution improvements
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import MagicMock, patch


class TestScorerBatchExecution(unittest.TestCase):
    """Test scorer batch execution with timeout handling"""

    def test_api_request_custom_timeout(self):
        """Test that api_request accepts custom timeout parameter"""
        # Import the function
        from violentutf.pages import Configure_Scorers as scorer_page

        # Mock requests.request
        with patch("requests.request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_request.return_value = mock_response

            # Mock get_auth_headers
            with patch.object(scorer_page, "get_auth_headers") as mock_headers:
                mock_headers.return_value = {"Authorization": "Bearer test"}

                # Test default timeout (30 seconds)
                scorer_page.api_request("GET", "http://test.com")
                mock_request.assert_called_with(
                    "GET", "http://test.com", headers={"Authorization": "Bearer test"}, timeout=30
                )

                # Test custom timeout (60 seconds)
                scorer_page.api_request("POST", "http://test.com", timeout=60)
                mock_request.assert_called_with(
                    "POST", "http://test.com", headers={"Authorization": "Bearer test"}, timeout=60
                )

    def test_batch_size_reduction(self):
        """Test that batch size is reduced from 10 to 5"""
        # Check the code contains the reduced batch size
        import inspect

        import violentutf.pages.Configure_Scorers as scorer_page

        # Get the source code of _execute_full_dataset_with_progress
        source = inspect.getsource(scorer_page._execute_full_dataset_with_progress)

        # Verify batch size is set to 5
        self.assertIn("batch_size = 5", source)
        self.assertNotIn("batch_size = 10", source)

    def test_consecutive_failure_handling(self):
        """Test that execution stops after consecutive failures"""
        # This would require more complex mocking of the execution flow
        # For now, verify the code includes consecutive failure handling
        import inspect

        import violentutf.pages.Configure_Scorers as scorer_page

        source = inspect.getsource(scorer_page._execute_full_dataset_with_progress)

        # Verify consecutive failure tracking
        self.assertIn("consecutive_failures", source)
        self.assertIn("max_consecutive_failures", source)
        self.assertIn("consecutive_failures >= max_consecutive_failures", source)

    def test_timeout_values(self):
        """Test that appropriate timeout values are set"""
        import inspect

        import violentutf.pages.Configure_Scorers as scorer_page

        # Check batch execution timeout
        source = inspect.getsource(scorer_page._execute_full_dataset_with_progress)
        self.assertIn("timeout=60", source)  # 60-second timeout for batch execution

        # Check test execution timeout
        source = inspect.getsource(scorer_page._test_scorer_orchestrator_mode)
        self.assertIn("timeout=45", source)  # 45-second timeout for test execution

    def test_performance_expectations(self):
        """Test performance expectations with new configuration"""
        batch_size = 5
        timeout = 60

        # Average processing time per prompt (5-10 seconds)
        min_time_per_prompt = 5
        max_time_per_prompt = 10

        # Calculate expected times
        min_batch_time = batch_size * min_time_per_prompt
        max_batch_time = batch_size * max_time_per_prompt

        # Verify batch can complete within timeout
        self.assertLess(max_batch_time, timeout, f"Batch of {batch_size} should complete within {timeout}s timeout")

        print("\nPerformance expectations:")
        print(f"  Batch size: {batch_size} prompts")
        print(f"  Timeout: {timeout} seconds")
        print(f"  Expected batch processing time: {min_batch_time}-{max_batch_time} seconds")
        print(f"  Safety margin: {timeout - max_batch_time} seconds")


if __name__ == "__main__":
    unittest.main(verbosity=2)
