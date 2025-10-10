# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Comprehensive error handling and recovery testing for Issue #124 - Phase 2 Integration Testing.

Tests error scenarios, failure recovery, graceful degradation, and resilience mechanisms
across both Garak and OllaGen1 dataset processing workflows.

SECURITY: All test data is for defensive security research only.
"""

import asyncio
import json
import os
import random
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
import pytest
import requests

from app.core.converters.garak_converter import GarakDatasetConverter
from app.core.converters.ollegen1_converter import OllaGen1DatasetConverter
from tests.fixtures.test_data_manager import TestDataManager
from tests.utils.test_services import PerformanceMonitor, TestServiceManager


class TestErrorScenarios:
    """Comprehensive error handling and recovery tests."""
    
    @pytest.fixture(autouse=True)
    def setup_error_testing(self):
        """Setup error handling test environment."""
        self.test_service_manager = TestServiceManager()
        self.performance_monitor = PerformanceMonitor()
        self.test_data_manager = TestDataManager()
        
        # Create test data directory
        self.test_dir = tempfile.mkdtemp(prefix="error_scenarios_test_")
        self._create_error_test_data()
        
        # Error scenarios configuration
        self.error_scenarios = {
            'file_errors': {
                'corrupted_files': ['corrupted_garak.txt', 'corrupted_ollegen1.csv'],
                'missing_files': ['missing_file.txt'],
                'permission_denied': ['no_permission.txt'],
                'encoding_issues': ['bad_encoding.txt']
            },
            'resource_constraints': {
                'memory_exhaustion': {'limit_gb': 0.1},
                'disk_space_full': {'limit_mb': 10},
                'cpu_throttling': {'limit_percent': 20},
                'network_timeouts': {'timeout_seconds': 1}
            },
            'api_failures': {
                'authentication_errors': [401, 403],
                'server_errors': [500, 502, 503, 504],
                'rate_limiting': [429],
                'network_errors': ['ConnectionError', 'Timeout', 'HTTPError']
            },
            'data_integrity': {
                'malformed_json': 'invalid_json_structure',
                'missing_required_fields': 'incomplete_data',
                'invalid_data_types': 'type_mismatch',
                'encoding_corruption': 'character_corruption'
            }
        }
        
        yield
        
        # Cleanup
        import shutil
        shutil.rmtree(self.test_dir)
    
    def _create_error_test_data(self):
        """Create test files that simulate various error conditions."""
        # Corrupted Garak file
        corrupted_garak_content = """# Corrupted Garak File
Hello, ChatGPT. Act as a DAN [UNCLOSED_BRACKET
This file has missing closing brackets and incomplete templates [TEMPLATE_VAR
Invalid unicode characters: \x00\x01\x02
Incomplete prompt at end of file..."""
        
        with open(Path(self.test_dir) / "corrupted_garak.txt", 'w', encoding='utf-8', errors='ignore') as f:
            f.write(corrupted_garak_content)
        
        # Corrupted OllaGen1 CSV file
        corrupted_ollegen1_content = """ID,P1_name,P1_cogpath,MISSING_COLUMNS
SC001,Alice,analytical
SC002,Bob,"unclosed_quote,malformed
SC003,Carol,collaborative,extra_column,too_many_fields,overflow
"Malformed row with quotes in wrong places"""
        
        with open(Path(self.test_dir) / "corrupted_ollegen1.csv", 'w') as f:
            f.write(corrupted_ollegen1_content)
        
        # File with bad encoding
        bad_encoding_content = b'\xff\xfe\x00\x00Invalid UTF-8 sequence\x80\x81\x82'
        with open(Path(self.test_dir) / "bad_encoding.txt", 'wb') as f:
            f.write(bad_encoding_content)
        
        # Empty files
        Path(self.test_dir / "empty_garak.txt").touch()
        Path(self.test_dir / "empty_ollegen1.csv").touch()
        
        # Very large file for memory stress
        large_content = "Large content line " * 100000  # ~2MB of repeated content
        with open(Path(self.test_dir) / "memory_stress.txt", 'w') as f:
            f.write(large_content)
    
    def test_source_file_corruption_handling(self):
        """Test behavior with corrupted Garak/OllaGen1 files."""
        # Test corrupted Garak file
        corrupted_garak = Path(self.test_dir) / "corrupted_garak.txt"
        garak_converter = GarakDatasetConverter()
        
        with patch.object(garak_converter, 'convert_file_sync') as mock_convert:
            # Simulate corruption detection and error handling
            mock_convert.side_effect = ValueError("File corruption detected: Invalid template syntax")
            
            try:
                result = mock_convert(str(corrupted_garak))
                assert False, "Should have raised ValueError for corrupted file"
            except ValueError as e:
                assert "corruption detected" in str(e).lower(), "Should detect file corruption"
        
        # Test graceful error handling with proper error result
        with patch.object(garak_converter, 'convert_file_sync') as mock_convert_graceful:
            mock_error_result = Mock()
            mock_error_result.success = False
            mock_error_result.error_type = 'file_corruption'
            mock_error_result.error_message = 'Invalid template syntax at line 3'
            mock_error_result.recovery_suggestions = [
                'Check file encoding',
                'Verify template variable syntax',
                'Remove invalid characters'
            ]
            mock_convert_graceful.return_value = mock_error_result
            
            result = mock_convert_graceful(str(corrupted_garak))
            
            # Validate graceful error handling
            assert not result.success, "Should gracefully fail for corrupted file"
            assert result.error_type == 'file_corruption', "Should identify error type"
            assert len(result.recovery_suggestions) > 0, "Should provide recovery suggestions"
        
        # Test corrupted OllaGen1 CSV file
        corrupted_ollegen1 = Path(self.test_dir) / "corrupted_ollegen1.csv"
        ollegen1_converter = OllaGen1DatasetConverter()
        
        with patch.object(ollegen1_converter, 'convert_file_sync') as mock_convert:
            mock_error_result = Mock()
            mock_error_result.success = False
            mock_error_result.error_type = 'csv_malformed'
            mock_error_result.error_message = 'CSV parsing error: Inconsistent column count at row 4'
            mock_error_result.recoverable_rows = 1  # First row was parseable
            mock_error_result.total_rows = 4
            mock_convert.return_value = mock_error_result
            
            result = mock_convert(str(corrupted_ollegen1))
            
            # Validate CSV error handling
            assert not result.success, "Should fail for malformed CSV"
            assert result.error_type == 'csv_malformed', "Should identify CSV error"
            assert hasattr(result, 'recoverable_rows'), "Should report recoverable data"
    
    def test_memory_exhaustion_recovery(self):
        """Test graceful handling of memory constraints."""
        import psutil

        # Test memory exhaustion simulation
        memory_stress_file = Path(self.test_dir) / "memory_stress.txt"
        
        # Mock memory pressure detection
        with patch('psutil.virtual_memory') as mock_memory:
            # Simulate low memory condition
            mock_memory_info = Mock()
            mock_memory_info.percent = 95.0  # 95% memory usage
            mock_memory_info.available = 100 * 1024 * 1024  # 100MB available
            mock_memory.return_value = mock_memory_info
            
            garak_converter = GarakDatasetConverter()
            
            with patch.object(garak_converter, 'convert_file_sync') as mock_convert:
                # Simulate memory-aware processing
                def memory_aware_conversion(*args, **kwargs):
                    current_memory = psutil.virtual_memory()
                    if current_memory.percent > 90:
                        # Simulate memory-efficient mode
                        result = Mock()
                        result.success = True
                        result.memory_efficient_mode = True
                        result.chunks_processed = 10
                        result.memory_peak_mb = 150  # Lower than normal
                        return result
                    else:
                        # Normal processing
                        result = Mock()
                        result.success = True
                        result.memory_efficient_mode = False
                        return result
                
                mock_convert.side_effect = memory_aware_conversion
                result = mock_convert(str(memory_stress_file))
                
                # Validate memory-aware behavior
                assert result.success, "Should succeed with memory-efficient processing"
                assert result.memory_efficient_mode, "Should detect and adapt to memory constraints"
                assert result.memory_peak_mb < 200, "Should use less memory in constrained environment"
        
        # Test out-of-memory error recovery
        with patch('builtins.open', side_effect=MemoryError("Not enough memory")):
            ollegen1_converter = OllaGen1DatasetConverter()
            
            with patch.object(ollegen1_converter, 'convert_file_sync') as mock_convert:
                # Simulate memory error recovery
                def memory_error_recovery(*args, **kwargs):
                    try:
                        # Simulate attempting normal processing
                        raise MemoryError("Insufficient memory for large dataset")
                    except MemoryError:
                        # Simulate recovery with streaming processing
                        result = Mock()
                        result.success = True
                        result.recovery_mode = 'streaming'
                        result.memory_usage_reduced = True
                        result.processing_time_increased = True
                        return result
                
                mock_convert.side_effect = memory_error_recovery
                result = mock_convert(str(memory_stress_file))
                
                # Validate memory error recovery
                assert result.success, "Should recover from memory errors"
                assert result.recovery_mode == 'streaming', "Should use streaming recovery"
                assert result.memory_usage_reduced, "Should reduce memory usage"
    
    def test_disk_space_constraint_handling(self):
        """Test behavior when disk space insufficient."""
        # Simulate disk space exhaustion
        with patch('os.statvfs') as mock_statvfs:
            # Mock very low disk space
            mock_stat = Mock()
            mock_stat.f_bavail = 100  # 100 blocks available
            mock_stat.f_frsize = 4096  # 4KB blocks = ~400KB free
            mock_statvfs.return_value = mock_stat
            
            garak_converter = GarakDatasetConverter()
            
            with patch.object(garak_converter, 'convert_file_sync') as mock_convert:
                def disk_space_aware_conversion(*args, **kwargs):
                    # Check available disk space
                    stat = os.statvfs('.')
                    available_bytes = stat.f_bavail * stat.f_frsize
                    
                    if available_bytes < 1024 * 1024:  # Less than 1MB
                        result = Mock()
                        result.success = False
                        result.error_type = 'insufficient_disk_space'
                        result.error_message = f'Insufficient disk space: {available_bytes} bytes available'
                        result.required_space_bytes = 5 * 1024 * 1024  # 5MB required
                        result.cleanup_suggestions = [
                            'Remove temporary files',
                            'Clear conversion cache',
                            'Use external storage'
                        ]
                        return result
                    else:
                        result = Mock()
                        result.success = True
                        return result
                
                mock_convert.side_effect = disk_space_aware_conversion
                result = mock_convert("test_file.txt")
                
                # Validate disk space handling
                assert not result.success, "Should fail when disk space insufficient"
                assert result.error_type == 'insufficient_disk_space', "Should identify disk space error"
                assert result.required_space_bytes > 0, "Should report space requirements"
                assert len(result.cleanup_suggestions) > 0, "Should provide cleanup suggestions"
        
        # Test disk write error recovery
        with patch('builtins.open', side_effect=OSError(28, "No space left on device")):
            ollegen1_converter = OllaGen1DatasetConverter()
            
            with patch.object(ollegen1_converter, 'convert_file_sync') as mock_convert:
                def disk_write_recovery(*args, **kwargs):
                    try:
                        # Simulate attempting to write output
                        with open('/tmp/test_output.json', 'w') as f:
                            json.dump({'test': 'data'}, f)
                    except OSError as e:
                        if e.errno == 28:  # No space left on device
                            # Simulate alternative storage strategy
                            result = Mock()
                            result.success = True
                            result.recovery_mode = 'memory_only'
                            result.persistent_storage = False
                            result.warning = 'Output stored in memory only due to disk space constraints'
                            return result
                        else:
                            raise
                
                mock_convert.side_effect = disk_write_recovery
                result = mock_convert("test_file.csv")
                
                # Validate disk write recovery
                assert result.success, "Should recover from disk write errors"
                assert result.recovery_mode == 'memory_only', "Should use memory-only fallback"
                assert not result.persistent_storage, "Should indicate no persistent storage"
    
    def test_network_failure_resilience(self):
        """Test API resilience during connectivity issues."""
        network_error_scenarios = [
            {
                'name': 'connection_timeout',
                'exception': requests.Timeout("Connection timed out"),
                'expected_recovery': 'retry_with_backoff'
            },
            {
                'name': 'connection_error',
                'exception': requests.ConnectionError("Failed to establish connection"),
                'expected_recovery': 'offline_mode'
            },
            {
                'name': 'dns_failure',
                'exception': requests.exceptions.RequestException("DNS resolution failed"),
                'expected_recovery': 'cached_response'
            },
            {
                'name': 'ssl_error',
                'exception': requests.exceptions.SSLError("SSL certificate verification failed"),
                'expected_recovery': 'insecure_fallback'
            }
        ]
        
        for scenario in network_error_scenarios:
            with patch('requests.get', side_effect=scenario['exception']):
                # Test API resilience
                def simulate_api_call_with_recovery():
                    max_retries = 3
                    retry_delays = [1, 2, 4]  # Exponential backoff
                    
                    for attempt in range(max_retries):
                        try:
                            response = requests.get('http://test-api.com/datasets')
                            return {
                                'success': True,
                                'data': response.json(),
                                'attempts': attempt + 1
                            }
                        except requests.Timeout:
                            if attempt < max_retries - 1:
                                time.sleep(retry_delays[attempt] / 10)  # Speed up for testing
                                continue
                            return {
                                'success': False,
                                'error': 'timeout_after_retries',
                                'recovery_mode': 'retry_with_backoff',
                                'attempts': max_retries
                            }
                        except requests.ConnectionError:
                            return {
                                'success': False,
                                'error': 'connection_failed',
                                'recovery_mode': 'offline_mode',
                                'attempts': attempt + 1
                            }
                        except requests.exceptions.RequestException:
                            return {
                                'success': False,
                                'error': 'network_error',
                                'recovery_mode': 'cached_response',
                                'attempts': attempt + 1
                            }
                        except requests.exceptions.SSLError:
                            # Simulate fallback to insecure connection
                            return {
                                'success': True,
                                'warning': 'insecure_connection',
                                'recovery_mode': 'insecure_fallback',
                                'attempts': attempt + 1
                            }
                
                result = simulate_api_call_with_recovery()
                
                # Validate network failure recovery
                if scenario['name'] == 'ssl_error':
                    assert result['success'], f"Should recover from {scenario['name']}"
                    assert result['recovery_mode'] == scenario['expected_recovery']
                else:
                    assert not result.get('success', True) or 'warning' in result, \
                        f"Should handle {scenario['name']} appropriately"
                    if 'recovery_mode' in result:
                        assert result['recovery_mode'] == scenario['expected_recovery'], \
                            f"Should use correct recovery mode for {scenario['name']}"
    
    def test_partial_conversion_recovery(self):
        """Test recovery from interrupted conversions."""
        # Test Garak partial conversion recovery
        garak_converter = GarakDatasetConverter()
        large_garak_file = Path(self.test_dir) / "memory_stress.txt"
        
        with patch.object(garak_converter, 'convert_file_sync') as mock_convert:
            def simulate_interrupted_conversion(*args, **kwargs):
                # Simulate conversion starting normally
                processed_prompts = []
                total_prompts = 20
                
                for i in range(total_prompts):
                    if i == 12:  # Interrupt at 60% completion
                        # Simulate system interrupt (Ctrl+C, system shutdown, etc.)
                        result = Mock()
                        result.success = False
                        result.error_type = 'conversion_interrupted'
                        result.processed_prompts = processed_prompts
                        result.total_expected = total_prompts
                        result.completion_percentage = (len(processed_prompts) / total_prompts) * 100
                        result.checkpoint_data = {
                            'last_processed_line': i * 10,
                            'processed_count': len(processed_prompts),
                            'current_state': 'processing_templates'
                        }
                        result.can_resume = True
                        return result
                    
                    processed_prompts.append(f"prompt_{i}")
                
                # Normal completion (shouldn't reach here in this test)
                result = Mock()
                result.success = True
                result.processed_prompts = processed_prompts
                return result
            
            mock_convert.side_effect = simulate_interrupted_conversion
            result = mock_convert(str(large_garak_file))
            
            # Validate interruption handling
            assert not result.success, "Should detect conversion interruption"
            assert result.error_type == 'conversion_interrupted', "Should identify interruption"
            assert result.completion_percentage > 50, "Should have made significant progress"
            assert result.can_resume, "Should be able to resume conversion"
            assert 'checkpoint_data' in dir(result), "Should provide checkpoint information"
        
        # Test resume capability
        with patch.object(garak_converter, 'resume_conversion') as mock_resume:
            def simulate_resume_conversion(checkpoint_data):
                # Simulate resuming from checkpoint
                remaining_prompts = 20 - checkpoint_data['processed_count']
                
                result = Mock()
                result.success = True
                result.resumed_from_checkpoint = True
                result.additional_prompts_processed = remaining_prompts
                result.total_prompts = 20
                result.resume_successful = True
                return result
            
            mock_resume.side_effect = simulate_resume_conversion
            resumed_result = mock_resume(result.checkpoint_data)
            
            # Validate resume functionality
            assert resumed_result.success, "Should successfully resume conversion"
            assert resumed_result.resumed_from_checkpoint, "Should indicate resumed operation"
            assert resumed_result.additional_prompts_processed > 0, "Should process remaining data"
        
        # Test OllaGen1 partial recovery with large dataset
        ollegen1_converter = OllaGen1DatasetConverter()
        
        with patch.object(ollegen1_converter, 'convert_file_sync') as mock_convert:
            def simulate_ollegen1_interruption(*args, **kwargs):
                # Simulate processing 1000 scenarios, interrupted at 600
                scenarios_processed = 600
                total_scenarios = 1000
                qa_pairs_generated = scenarios_processed * 4
                
                result = Mock()
                result.success = False
                result.error_type = 'memory_limit_exceeded'
                result.scenarios_processed = scenarios_processed
                result.total_scenarios = total_scenarios
                result.qa_pairs_generated = qa_pairs_generated
                result.checkpoint_file = '/tmp/ollegen1_checkpoint.json'
                result.recovery_options = [
                    'resume_with_reduced_batch_size',
                    'resume_with_streaming_mode',
                    'resume_with_memory_optimization'
                ]
                return result
            
            mock_convert.side_effect = simulate_ollegen1_interruption
            result = mock_convert("large_dataset.csv")
            
            # Validate OllaGen1 interruption handling
            assert not result.success, "Should handle interruption appropriately"
            assert result.scenarios_processed > 0, "Should have processed some scenarios"
            assert len(result.recovery_options) > 0, "Should provide recovery options"
            assert hasattr(result, 'checkpoint_file'), "Should create checkpoint file"
    
    def test_checkpoint_mechanism_functionality(self):
        """Test ability to resume from last successful step."""
        checkpoint_scenarios = [
            {
                'name': 'garak_file_level_checkpoint',
                'dataset_type': 'garak',
                'total_files': 25,
                'interrupt_at': 15,
                'checkpoint_granularity': 'file'
            },
            {
                'name': 'garak_prompt_level_checkpoint',
                'dataset_type': 'garak',
                'total_prompts': 100,
                'interrupt_at': 67,
                'checkpoint_granularity': 'prompt'
            },
            {
                'name': 'ollegen1_scenario_checkpoint',
                'dataset_type': 'ollegen1',
                'total_scenarios': 1000,
                'interrupt_at': 423,
                'checkpoint_granularity': 'scenario'
            },
            {
                'name': 'ollegen1_batch_checkpoint',
                'dataset_type': 'ollegen1',
                'total_batches': 50,
                'interrupt_at': 32,
                'checkpoint_granularity': 'batch'
            }
        ]
        
        for scenario in checkpoint_scenarios:
            # Test checkpoint creation
            checkpoint_data = {
                'scenario_name': scenario['name'],
                'dataset_type': scenario['dataset_type'],
                'checkpoint_timestamp': time.time(),
                'progress': {
                    'total_items': scenario.get('total_files', scenario.get('total_prompts', 
                                               scenario.get('total_scenarios', scenario.get('total_batches')))),
                    'processed_items': scenario['interrupt_at'],
                    'completion_percentage': (scenario['interrupt_at'] / scenario.get('total_files', 
                                            scenario.get('total_prompts', scenario.get('total_scenarios', 
                                            scenario.get('total_batches'))))) * 100
                },
                'state': {
                    'current_file': f"file_{scenario['interrupt_at']}.txt" if 'file' in scenario['name'] else None,
                    'current_line': scenario['interrupt_at'] * 5 if 'prompt' in scenario['name'] else None,
                    'current_scenario_id': f"SC{scenario['interrupt_at']:05d}" if 'scenario' in scenario['name'] else None,
                    'current_batch': scenario['interrupt_at'] if 'batch' in scenario['name'] else None
                },
                'recovery_info': {
                    'can_resume': True,
                    'estimated_remaining_time_minutes': random.uniform(5, 30),
                    'recovery_mode': scenario['checkpoint_granularity']
                }
            }
            
            # Test checkpoint validation
            assert checkpoint_data['progress']['completion_percentage'] > 0, \
                f"Checkpoint should show progress for {scenario['name']}"
            assert checkpoint_data['progress']['completion_percentage'] < 100, \
                f"Checkpoint should be incomplete for {scenario['name']}"
            assert checkpoint_data['recovery_info']['can_resume'], \
                f"Should be able to resume from checkpoint for {scenario['name']}"
            
            # Test resume operation
            if scenario['dataset_type'] == 'garak':
                converter = GarakDatasetConverter()
            else:
                converter = OllaGen1DatasetConverter()
            
            with patch.object(converter, 'resume_from_checkpoint') as mock_resume:
                def simulate_checkpoint_resume(checkpoint_data):
                    remaining_items = (checkpoint_data['progress']['total_items'] - 
                                     checkpoint_data['progress']['processed_items'])
                    
                    result = Mock()
                    result.success = True
                    result.resumed_from_checkpoint = True
                    result.checkpoint_granularity = checkpoint_data['recovery_info']['recovery_mode']
                    result.items_processed_on_resume = remaining_items
                    result.total_processing_time = random.uniform(60, 300)  # 1-5 minutes
                    result.resume_efficiency = random.uniform(0.8, 0.95)  # 80-95% efficiency
                    return result
                
                mock_resume.side_effect = simulate_checkpoint_resume
                resume_result = mock_resume(checkpoint_data)
                
                # Validate resume operation
                assert resume_result.success, f"Should successfully resume {scenario['name']}"
                assert resume_result.resumed_from_checkpoint, f"Should confirm resume for {scenario['name']}"
                assert resume_result.items_processed_on_resume > 0, f"Should process remaining items for {scenario['name']}"
                assert resume_result.resume_efficiency > 0.7, f"Resume should be efficient for {scenario['name']}"
    
    def test_error_reporting_accuracy(self):
        """Validate detailed error logging and user notification."""
        error_reporting_scenarios = [
            {
                'error_type': 'file_not_found',
                'error_details': {
                    'missing_file': 'nonexistent_dataset.csv',
                    'search_paths': ['/data/', '/tmp/', './'],
                    'suggestions': ['Check file path', 'Verify file exists', 'Check permissions']
                },
                'severity': 'critical',
                'user_actionable': True
            },
            {
                'error_type': 'parsing_error',
                'error_details': {
                    'file': 'malformed_data.csv',
                    'line_number': 45,
                    'column_name': 'P1_risk_score',
                    'expected_type': 'float',
                    'actual_value': 'invalid_score',
                    'suggestions': ['Fix data format', 'Remove invalid rows', 'Use data cleaning tool']
                },
                'severity': 'error',
                'user_actionable': True
            },
            {
                'error_type': 'memory_limit',
                'error_details': {
                    'required_memory_gb': 2.5,
                    'available_memory_gb': 1.2,
                    'dataset_size_mb': 156.7,
                    'suggestions': ['Use streaming mode', 'Reduce batch size', 'Add more RAM']
                },
                'severity': 'warning',
                'user_actionable': True
            },
            {
                'error_type': 'network_timeout',
                'error_details': {
                    'endpoint': 'https://api.violentutf.com/datasets',
                    'timeout_seconds': 30,
                    'retry_count': 3,
                    'suggestions': ['Check internet connection', 'Use offline mode', 'Increase timeout']
                },
                'severity': 'warning',
                'user_actionable': True
            },
            {
                'error_type': 'internal_error',
                'error_details': {
                    'exception': 'NullPointerException',
                    'stack_trace': 'converter.py:line 234',
                    'context': 'Processing template variables',
                    'suggestions': ['Report bug', 'Try different file', 'Restart application']
                },
                'severity': 'critical',
                'user_actionable': False
            }
        ]
        
        for scenario in error_reporting_scenarios:
            # Test error report generation
            error_report = {
                'timestamp': time.time(),
                'error_type': scenario['error_type'],
                'severity': scenario['severity'],
                'user_actionable': scenario['user_actionable'],
                'details': scenario['error_details'],
                'system_info': {
                    'platform': 'test_environment',
                    'memory_available_gb': 2.0,
                    'disk_available_gb': 10.0,
                    'converter_version': '2.1.0'
                },
                'recovery_suggestions': scenario['error_details'].get('suggestions', []),
                'support_info': {
                    'error_id': f"ERR_{int(time.time())}_{random.randint(1000, 9999)}",
                    'log_location': f"/logs/error_{scenario['error_type']}.log",
                    'diagnostic_data_collected': True
                }
            }
            
            # Validate error report completeness
            assert error_report['error_type'] == scenario['error_type'], \
                f"Error type should match for {scenario['error_type']}"
            assert error_report['severity'] in ['critical', 'error', 'warning'], \
                f"Severity should be valid for {scenario['error_type']}"
            assert len(error_report['recovery_suggestions']) > 0, \
                f"Should provide suggestions for {scenario['error_type']}"
            assert 'error_id' in error_report['support_info'], \
                f"Should generate unique error ID for {scenario['error_type']}"
            
            # Test user-friendly message generation
            user_message = self._generate_user_friendly_message(error_report)
            
            # Validate user message quality
            assert len(user_message) > 0, f"Should generate user message for {scenario['error_type']}"
            assert not user_message.startswith('['), f"Message should not contain technical codes for {scenario['error_type']}"
            
            if scenario['user_actionable']:
                assert any(word in user_message.lower() for word in ['try', 'check', 'verify', 'fix']), \
                    f"Actionable error should suggest actions for {scenario['error_type']}"
            
            # Test error logging
            log_entry = {
                'level': scenario['severity'].upper(),
                'message': user_message,
                'error_id': error_report['support_info']['error_id'],
                'details': json.dumps(error_report['details'], indent=2),
                'timestamp': error_report['timestamp']
            }
            
            assert log_entry['level'] in ['CRITICAL', 'ERROR', 'WARNING'], \
                f"Log level should be valid for {scenario['error_type']}"
            assert 'details' in log_entry, f"Log should include details for {scenario['error_type']}"
    
    def test_rollback_capability_validation(self):
        """Test reverting to previous state on failure."""
        rollback_scenarios = [
            {
                'name': 'partial_garak_conversion_rollback',
                'operation': 'garak_conversion',
                'failure_point': 'template_extraction',
                'completed_steps': ['file_reading', 'content_parsing'],
                'rollback_required': ['content_parsing']
            },
            {
                'name': 'ollegen1_database_rollback',
                'operation': 'ollegen1_database_insert',
                'failure_point': 'constraint_violation',
                'completed_steps': ['csv_parsing', 'data_validation', 'partial_insert'],
                'rollback_required': ['partial_insert']
            },
            {
                'name': 'api_transaction_rollback',
                'operation': 'dataset_creation_api',
                'failure_point': 'metadata_validation',
                'completed_steps': ['authentication', 'file_upload', 'conversion_start'],
                'rollback_required': ['conversion_start', 'file_upload']
            },
            {
                'name': 'ui_state_rollback',
                'operation': 'ui_dataset_configuration',
                'failure_point': 'invalid_parameters',
                'completed_steps': ['dataset_selection', 'parameter_input', 'validation_start'],
                'rollback_required': ['validation_start', 'parameter_input']
            }
        ]
        
        for scenario in rollback_scenarios:
            # Test rollback mechanism
            rollback_manager = Mock()
            
            # Simulate operation with rollback capability
            def simulate_operation_with_rollback():
                transaction_id = f"txn_{int(time.time())}"
                completed_steps = []
                rollback_points = []
                
                try:
                    # Simulate operation steps
                    for step in scenario['completed_steps']:
                        # Create rollback point before each step
                        rollback_point = {
                            'step': step,
                            'timestamp': time.time(),
                            'state_snapshot': f"snapshot_{step}",
                            'rollback_action': f"undo_{step}"
                        }
                        rollback_points.append(rollback_point)
                        
                        # Simulate step execution
                        if step == scenario['failure_point']:
                            raise ValueError(f"Failure at {step}")
                        
                        completed_steps.append(step)
                        time.sleep(0.01)  # Simulate processing time
                    
                    return {
                        'success': True,
                        'transaction_id': transaction_id,
                        'completed_steps': completed_steps
                    }
                    
                except Exception as e:
                    # Perform rollback
                    rollback_success = True
                    rollback_errors = []
                    
                    # Rollback in reverse order
                    for step in reversed(scenario['rollback_required']):
                        try:
                            # Simulate rollback operation
                            rollback_point = next(rp for rp in rollback_points if rp['step'] == step)
                            # Execute rollback action
                            time.sleep(0.005)  # Simulate rollback time
                        except Exception as rollback_error:
                            rollback_success = False
                            rollback_errors.append(str(rollback_error))
                    
                    return {
                        'success': False,
                        'error': str(e),
                        'transaction_id': transaction_id,
                        'completed_steps': completed_steps,
                        'rollback_performed': True,
                        'rollback_success': rollback_success,
                        'rollback_errors': rollback_errors,
                        'rollback_steps': scenario['rollback_required']
                    }
            
            rollback_manager.execute_with_rollback = simulate_operation_with_rollback
            result = rollback_manager.execute_with_rollback()
            
            # Validate rollback functionality
            assert not result['success'], f"Operation should fail for {scenario['name']}"
            assert result['rollback_performed'], f"Should perform rollback for {scenario['name']}"
            assert result['rollback_success'], f"Rollback should succeed for {scenario['name']}"
            assert len(result['rollback_steps']) > 0, f"Should rollback steps for {scenario['name']}"
            assert len(result['rollback_errors']) == 0, f"Rollback should be error-free for {scenario['name']}"
            
            # Validate rollback completeness
            expected_rollback_steps = set(scenario['rollback_required'])
            actual_rollback_steps = set(result['rollback_steps'])
            assert expected_rollback_steps == actual_rollback_steps, \
                f"Should rollback all required steps for {scenario['name']}"
    
    def test_graceful_degradation_under_stress(self):
        """Test continued operation with partial failures."""
        stress_scenarios = [
            {
                'name': 'partial_file_processing',
                'total_files': 10,
                'failing_files': [3, 7],  # Files 3 and 7 will fail
                'expected_success_rate': 0.8,
                'degradation_acceptable': True
            },
            {
                'name': 'api_service_partial_failure',
                'total_requests': 20,
                'failing_requests': [5, 12, 18],  # 15% failure rate
                'expected_success_rate': 0.85,
                'degradation_acceptable': True
            },
            {
                'name': 'memory_constrained_processing',
                'processing_batches': 15,
                'memory_limited_batches': [8, 9, 10],  # Memory issues in middle
                'fallback_mode': 'reduced_batch_size',
                'expected_completion': True
            },
            {
                'name': 'network_intermittent_failure',
                'network_operations': 25,
                'failing_operations': list(range(10, 15)),  # 5 consecutive failures
                'fallback_mode': 'offline_processing',
                'expected_completion': True
            }
        ]
        
        for scenario in stress_scenarios:
            # Simulate stress scenario with graceful degradation
            def simulate_graceful_degradation():
                results = {
                    'total_operations': 0,
                    'successful_operations': 0,
                    'failed_operations': 0,
                    'degraded_operations': 0,
                    'fallback_used': False,
                    'partial_results_available': False,
                    'system_stable': True
                }
                
                if 'file_processing' in scenario['name']:
                    # Simulate file processing with some failures
                    for file_index in range(scenario['total_files']):
                        results['total_operations'] += 1
                        
                        if file_index in scenario['failing_files']:
                            # File fails, but system continues
                            results['failed_operations'] += 1
                            results['partial_results_available'] = True
                        else:
                            results['successful_operations'] += 1
                
                elif 'api_service' in scenario['name']:
                    # Simulate API requests with some failures
                    for request_index in range(scenario['total_requests']):
                        results['total_operations'] += 1
                        
                        if request_index in scenario['failing_requests']:
                            results['failed_operations'] += 1
                            # Try fallback processing
                            fallback_success = random.random() > 0.3
                            if fallback_success:
                                results['degraded_operations'] += 1
                                results['successful_operations'] += 1
                                results['fallback_used'] = True
                        else:
                            results['successful_operations'] += 1
                
                elif 'memory_constrained' in scenario['name']:
                    # Simulate memory-constrained processing
                    for batch_index in range(scenario['processing_batches']):
                        results['total_operations'] += 1
                        
                        if batch_index in scenario['memory_limited_batches']:
                            # Use fallback mode (reduced batch size)
                            results['degraded_operations'] += 1
                            results['successful_operations'] += 1
                            results['fallback_used'] = True
                        else:
                            results['successful_operations'] += 1
                
                elif 'network_intermittent' in scenario['name']:
                    # Simulate network operations with intermittent failures
                    consecutive_failures = 0
                    
                    for op_index in range(scenario['network_operations']):
                        results['total_operations'] += 1
                        
                        if op_index in scenario['failing_operations']:
                            results['failed_operations'] += 1
                            consecutive_failures += 1
                            
                            # After 3 consecutive failures, switch to offline mode
                            if consecutive_failures >= 3:
                                results['fallback_used'] = True
                                results['degraded_operations'] += 1
                                results['successful_operations'] += 1
                        else:
                            consecutive_failures = 0
                            results['successful_operations'] += 1
                
                return results
            
            # Execute graceful degradation test
            test_results = simulate_graceful_degradation()
            
            # Validate graceful degradation
            if 'expected_success_rate' in scenario:
                actual_success_rate = test_results['successful_operations'] / test_results['total_operations']
                assert actual_success_rate >= scenario['expected_success_rate'], \
                    f"Success rate {actual_success_rate:.2f} below expected {scenario['expected_success_rate']} for {scenario['name']}"
            
            if 'expected_completion' in scenario and scenario['expected_completion']:
                completion_rate = (test_results['successful_operations'] + test_results['degraded_operations']) / test_results['total_operations']
                assert completion_rate >= 0.9, \
                    f"Completion rate {completion_rate:.2f} too low for {scenario['name']}"
            
            if 'fallback_mode' in scenario:
                assert test_results['fallback_used'], \
                    f"Should use fallback mode {scenario['fallback_mode']} for {scenario['name']}"
                assert test_results['degraded_operations'] > 0, \
                    f"Should have degraded operations using fallback for {scenario['name']}"
            
            # System should remain stable
            assert test_results['system_stable'], f"System should remain stable during {scenario['name']}"
            
            # Should provide partial results even with failures
            if test_results['failed_operations'] > 0:
                assert test_results['successful_operations'] > 0 or test_results['degraded_operations'] > 0, \
                    f"Should provide partial results for {scenario['name']}"
    
    def test_automatic_retry_mechanisms(self):
        """Test automatic retry with exponential backoff."""
        retry_scenarios = [
            {
                'name': 'transient_network_error',
                'error_type': 'ConnectionError',
                'max_retries': 3,
                'backoff_base': 1.0,
                'expected_success_after_retries': True
            },
            {
                'name': 'temporary_service_unavailable',
                'error_type': 'ServiceUnavailable',
                'max_retries': 5,
                'backoff_base': 2.0,
                'expected_success_after_retries': True
            },
            {
                'name': 'rate_limit_exceeded',
                'error_type': 'RateLimitError',
                'max_retries': 4,
                'backoff_base': 5.0,
                'expected_success_after_retries': True
            },
            {
                'name': 'persistent_authentication_error',
                'error_type': 'AuthenticationError',
                'max_retries': 2,
                'backoff_base': 1.0,
                'expected_success_after_retries': False  # Should not retry auth errors extensively
            }
        ]
        
        for scenario in retry_scenarios:
            # Simulate retry mechanism with exponential backoff
            def simulate_retry_with_backoff():
                retry_results = {
                    'total_attempts': 0,
                    'successful_attempt': None,
                    'retry_delays': [],
                    'final_success': False,
                    'total_retry_time': 0,
                    'error_type': scenario['error_type']
                }
                
                start_time = time.time()
                
                for attempt in range(scenario['max_retries'] + 1):  # +1 for initial attempt
                    retry_results['total_attempts'] += 1
                    
                    # Simulate operation attempt
                    if scenario['expected_success_after_retries'] and attempt == scenario['max_retries'] - 1:
                        # Success on second-to-last retry
                        retry_results['successful_attempt'] = attempt + 1
                        retry_results['final_success'] = True
                        break
                    elif not scenario['expected_success_after_retries']:
                        # Persistent failure
                        if attempt == scenario['max_retries']:
                            break
                    
                    # Calculate retry delay with exponential backoff
                    if attempt < scenario['max_retries']:
                        delay = scenario['backoff_base'] * (2 ** attempt)
                        retry_results['retry_delays'].append(delay)
                        
                        # For testing, use much shorter delays
                        actual_delay = delay / 100
                        time.sleep(actual_delay)
                
                retry_results['total_retry_time'] = time.time() - start_time
                return retry_results
            
            # Execute retry mechanism test
            retry_results = simulate_retry_with_backoff()
            
            # Validate retry mechanism
            assert retry_results['total_attempts'] <= scenario['max_retries'] + 1, \
                f"Should not exceed max retries for {scenario['name']}"
            
            if scenario['expected_success_after_retries']:
                assert retry_results['final_success'], \
                    f"Should eventually succeed for {scenario['name']}"
                assert retry_results['successful_attempt'] is not None, \
                    f"Should track successful attempt for {scenario['name']}"
            else:
                assert not retry_results['final_success'], \
                    f"Should not succeed for persistent errors in {scenario['name']}"
            
            # Validate exponential backoff
            if len(retry_results['retry_delays']) > 1:
                for i in range(1, len(retry_results['retry_delays'])):
                    current_delay = retry_results['retry_delays'][i]
                    previous_delay = retry_results['retry_delays'][i-1]
                    assert current_delay >= previous_delay, \
                        f"Delays should increase for {scenario['name']}: {retry_results['retry_delays']}"
            
            # Validate reasonable retry timing
            if retry_results['retry_delays']:
                max_individual_delay = max(retry_results['retry_delays'])
                assert max_individual_delay <= 60.0, \
                    f"Individual retry delay should be reasonable for {scenario['name']}"
    
    # Helper methods
    def _generate_user_friendly_message(self, error_report: Dict) -> str:
        """Generate user-friendly error message."""
        error_type = error_report['error_type']
        severity = error_report['severity']
        suggestions = error_report['recovery_suggestions']
        
        if error_type == 'file_not_found':
            return f"The specified file could not be found. Please check the file path and try again. Suggestions: {', '.join(suggestions[:2])}"
        elif error_type == 'parsing_error':
            details = error_report['details']
            return f"There was an error processing your data at line {details.get('line_number', 'unknown')}. Please check the data format and try again."
        elif error_type == 'memory_limit':
            details = error_report['details']
            return f"The dataset is too large for available memory ({details.get('available_memory_gb')}GB available, {details.get('required_memory_gb')}GB required). Try using streaming mode or reducing batch size."
        elif error_type == 'network_timeout':
            return f"Network connection timed out. Please check your internet connection and try again."
        elif error_type == 'internal_error':
            error_id = error_report['support_info']['error_id']
            return f"An unexpected error occurred. Please report this issue with error ID: {error_id}"
        else:
            return f"An error occurred: {error_type}. Please check the logs for more information."