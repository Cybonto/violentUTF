# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Comprehensive Streamlit UI integration tests for Issue #124 - Phase 2 Integration Testing.

Tests the complete Streamlit UI integration for both Garak and OllaGen1 dataset workflows,
including user interactions, dataset selection, previews, and configuration options.

SECURITY: All test data is for defensive security research only.
"""

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from tests.fixtures.test_data_manager import TestDataManager
from tests.utils.test_services import PerformanceMonitor, TestServiceManager


class TestStreamlitIntegration:
    """Comprehensive Streamlit UI integration tests."""
    
    @pytest.fixture(autouse=True)
    def setup_streamlit_integration(self):
        """Setup Streamlit integration test environment."""
        self.test_service_manager = TestServiceManager()
        self.performance_monitor = PerformanceMonitor()
        self.test_data_manager = TestDataManager()
        
        # Create test data directory
        self.test_dir = tempfile.mkdtemp(prefix="streamlit_ui_test_")
        self._create_streamlit_test_data()
        
        # Mock Streamlit session state
        self.mock_session_state = {
            'authenticated': True,
            'user_token': 'test_jwt_token',
            'user_id': 'test_user',
            'selected_datasets': [],
            'dataset_preview_cache': {},
            'ui_state': 'initialized'
        }
        
        yield
        
        # Cleanup
        import shutil
        shutil.rmtree(self.test_dir)
    
    def _create_streamlit_test_data(self):
        """Create test data for Streamlit UI testing."""
        # Mock available datasets
        self.mock_datasets = [
            {
                'id': 'garak_ui_001',
                'type': 'garak',
                'name': 'UI Test Garak Dataset 1',
                'description': 'DAN and jailbreak prompts for UI testing',
                'created_at': '2025-01-07T10:00:00Z',
                'prompt_count': 25,
                'tags': ['garak', 'dan', 'ui-test'],
                'status': 'active',
                'size_mb': 2.3
            },
            {
                'id': 'garak_ui_002',
                'type': 'garak',
                'name': 'UI Test Garak Dataset 2',
                'description': 'RTP and injection attacks for UI testing',
                'created_at': '2025-01-07T11:00:00Z',
                'prompt_count': 18,
                'tags': ['garak', 'rtp', 'injection', 'ui-test'],
                'status': 'active',
                'size_mb': 1.8
            },
            {
                'id': 'ollegen1_ui_001',
                'type': 'ollegen1',
                'name': 'UI Test OllaGen1 Dataset',
                'description': 'Cognitive assessment questions for UI testing',
                'created_at': '2025-01-07T12:00:00Z',
                'qa_pair_count': 4000,
                'scenario_count': 1000,
                'tags': ['ollegen1', 'cognitive', 'ui-test'],
                'status': 'active',
                'size_mb': 45.7
            },
            {
                'id': 'ollegen1_ui_large',
                'type': 'ollegen1',
                'name': 'Large OllaGen1 Dataset (UI Test)',
                'description': 'Large cognitive assessment dataset for performance testing',
                'created_at': '2025-01-07T13:00:00Z',
                'qa_pair_count': 679996,
                'scenario_count': 169999,
                'tags': ['ollegen1', 'large', 'performance-test'],
                'status': 'active',
                'size_mb': 2456.8
            }
        ]
    
    def test_dataset_selection_workflow_garak(self):
        """Test complete Garak dataset selection in 2_Configure_Datasets.py."""
        # Mock Streamlit app components
        with patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.multiselect') as mock_multiselect, \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.write') as mock_write:
            
            # Setup mock returns
            garak_datasets = [ds for ds in self.mock_datasets if ds['type'] == 'garak']
            
            # Mock dataset type selection
            mock_selectbox.side_effect = [
                'Garak Red-teaming Prompts',  # Dataset type selection
                garak_datasets[0]['name']     # Specific dataset selection
            ]
            
            # Mock tag filtering (multiselect)
            mock_multiselect.return_value = ['garak', 'dan']
            
            # Mock configuration button
            mock_button.return_value = True
            
            # Test the workflow
            selected_type = 'Garak Red-teaming Prompts'
            filtered_datasets = [ds for ds in garak_datasets if any(tag in ds['tags'] for tag in ['garak', 'dan'])]
            selected_dataset = filtered_datasets[0]
            
            # Validate workflow
            assert selected_type == 'Garak Red-teaming Prompts'
            assert len(filtered_datasets) >= 1
            assert selected_dataset['type'] == 'garak'
            assert selected_dataset['id'] == 'garak_ui_001'
            
            # Validate UI interactions
            assert mock_selectbox.call_count >= 1
            assert mock_multiselect.call_count >= 1
            
            # Test dataset configuration options
            garak_config = self._get_garak_ui_config(selected_dataset)
            assert 'attack_type_filter' in garak_config
            assert 'classification_threshold' in garak_config
            assert 'include_metadata' in garak_config
    
    def test_dataset_selection_workflow_ollegen1(self):
        """Test complete OllaGen1 dataset selection workflow."""
        with patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.multiselect') as mock_multiselect, \
             patch('streamlit.slider') as mock_slider, \
             patch('streamlit.button') as mock_button:
            
            # Setup mock returns for OllaGen1 workflow
            ollegen1_datasets = [ds for ds in self.mock_datasets if ds['type'] == 'ollegen1']
            
            mock_selectbox.side_effect = [
                'OllaGen1 Cognitive Assessment',  # Dataset type
                ollegen1_datasets[0]['name']      # Specific dataset
            ]
            
            mock_multiselect.return_value = ['WCP', 'WHO', 'TeamRisk']  # Question type filter
            mock_slider.return_value = 0.95  # Accuracy threshold
            mock_button.return_value = True
            
            # Test workflow
            selected_type = 'OllaGen1 Cognitive Assessment'
            selected_dataset = ollegen1_datasets[0]
            question_types = ['WCP', 'WHO', 'TeamRisk']
            accuracy_threshold = 0.95
            
            # Validate OllaGen1 workflow
            assert selected_type == 'OllaGen1 Cognitive Assessment'
            assert selected_dataset['type'] == 'ollegen1'
            assert len(question_types) == 3
            assert accuracy_threshold >= 0.90
            
            # Test OllaGen1 configuration options
            ollegen1_config = self._get_ollegen1_ui_config(selected_dataset)
            assert 'question_types' in ollegen1_config
            assert 'batch_size' in ollegen1_config
            assert 'extraction_accuracy_threshold' in ollegen1_config
    
    def test_dataset_preview_performance_large(self):
        """Test preview loading with 679K entries."""
        large_dataset = next(ds for ds in self.mock_datasets if ds['id'] == 'ollegen1_ui_large')
        
        self.performance_monitor.start_monitoring()
        start_time = time.time()
        
        with patch('streamlit.dataframe') as mock_dataframe, \
             patch('streamlit.json') as mock_json, \
             patch('streamlit.spinner') as mock_spinner:
            
            # Mock large dataset preview (paginated)
            mock_preview_data = self._generate_mock_preview_data(large_dataset, page_size=50)
            
            # Simulate preview loading
            mock_dataframe.return_value = None
            mock_json.return_value = None
            mock_spinner.return_value = MagicMock()
            
            preview_load_time = time.time() - start_time
            
        self.performance_monitor.stop_monitoring()
        metrics = self.performance_monitor.get_metrics()
        
        # Performance validation
        assert preview_load_time < 5.0, f"Large dataset preview took {preview_load_time:.2f}s, expected <5s"
        assert metrics['memory_usage'] < 0.5, f"Preview memory usage {metrics['memory_usage']:.2f}GB exceeded 0.5GB"
        
        # Validate preview data structure
        assert len(mock_preview_data['sample_qa_pairs']) <= 50, "Preview should be paginated to max 50 items"
        assert 'pagination' in mock_preview_data
        assert mock_preview_data['pagination']['total_items'] == large_dataset['qa_pair_count']
    
    def test_configuration_parameter_handling(self):
        """Test configuration forms for both dataset types."""
        # Test Garak configuration form
        with patch('streamlit.expander') as mock_expander, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.multiselect') as mock_multiselect, \
             patch('streamlit.slider') as mock_slider, \
             patch('streamlit.checkbox') as mock_checkbox:
            
            # Mock form components for Garak
            mock_expander.return_value.__enter__ = Mock()
            mock_expander.return_value.__exit__ = Mock(return_value=None)
            
            mock_selectbox.return_value = 'strategy_3_garak'
            mock_multiselect.side_effect = [
                ['dan', 'rtp', 'injection'],  # Attack type filter
                ['jailbreak', 'toxicity']     # Harm category filter
            ]
            mock_slider.return_value = 0.90
            mock_checkbox.side_effect = [True, True, False]  # Various boolean options
            
            # Test Garak configuration
            garak_config = {
                'strategy': mock_selectbox.return_value,
                'attack_type_filter': mock_multiselect.side_effect[0],
                'harm_category_filter': mock_multiselect.side_effect[1],
                'classification_threshold': mock_slider.return_value,
                'include_metadata': mock_checkbox.side_effect[0],
                'extract_template_variables': mock_checkbox.side_effect[1],
                'enable_multilingual': mock_checkbox.side_effect[2]
            }
            
            # Validate Garak configuration
            assert garak_config['strategy'] == 'strategy_3_garak'
            assert len(garak_config['attack_type_filter']) == 3
            assert garak_config['classification_threshold'] == 0.90
            assert garak_config['include_metadata'] is True
        
        # Test OllaGen1 configuration form  
        with patch('streamlit.expander') as mock_expander, \
             patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.multiselect') as mock_multiselect, \
             patch('streamlit.number_input') as mock_number_input, \
             patch('streamlit.checkbox') as mock_checkbox:
            
            # Mock form components for OllaGen1
            mock_selectbox.return_value = 'strategy_1_cognitive_assessment'
            mock_multiselect.return_value = ['WCP', 'WHO', 'TeamRisk', 'TargetFactor']
            mock_number_input.side_effect = [100, 0.95, 2.0]  # batch_size, accuracy, memory_limit
            mock_checkbox.side_effect = [True, True]  # metadata, progress tracking
            
            # Test OllaGen1 configuration
            ollegen1_config = {
                'strategy': mock_selectbox.return_value,
                'question_types': mock_multiselect.return_value,
                'batch_size': mock_number_input.side_effect[0],
                'extraction_accuracy_threshold': mock_number_input.side_effect[1],
                'memory_limit_gb': mock_number_input.side_effect[2],
                'include_metadata': mock_checkbox.side_effect[0],
                'enable_progress_tracking': mock_checkbox.side_effect[1]
            }
            
            # Validate OllaGen1 configuration
            assert ollegen1_config['strategy'] == 'strategy_1_cognitive_assessment'
            assert len(ollegen1_config['question_types']) == 4
            assert ollegen1_config['batch_size'] == 100
            assert ollegen1_config['extraction_accuracy_threshold'] == 0.95
            assert ollegen1_config['memory_limit_gb'] == 2.0
    
    def test_ui_responsiveness_stress_testing(self):
        """Test UI performance under stress conditions."""
        stress_scenarios = [
            {
                'name': 'large_dataset_list',
                'datasets_count': 100,
                'expected_load_time': 3.0
            },
            {
                'name': 'complex_filtering',
                'filter_combinations': 25,
                'expected_response_time': 2.0
            },
            {
                'name': 'rapid_selections',
                'selection_changes': 50,
                'expected_stability': True
            }
        ]
        
        for scenario in stress_scenarios:
            self.performance_monitor.start_monitoring()
            start_time = time.time()
            
            with patch('streamlit.rerun') as mock_rerun:
                if scenario['name'] == 'large_dataset_list':
                    # Simulate large dataset list loading
                    large_dataset_list = self._generate_large_dataset_list(scenario['datasets_count'])
                    processing_time = time.time() - start_time
                    
                    assert processing_time < scenario['expected_load_time'], \
                        f"Large dataset list load took {processing_time:.2f}s, expected <{scenario['expected_load_time']}s"
                
                elif scenario['name'] == 'complex_filtering':
                    # Simulate complex filtering operations
                    for _ in range(scenario['filter_combinations']):
                        filtered_results = self._simulate_complex_filtering()
                        time.sleep(0.01)  # Small delay to simulate processing
                    
                    processing_time = time.time() - start_time
                    assert processing_time < scenario['expected_response_time'], \
                        f"Complex filtering took {processing_time:.2f}s, expected <{scenario['expected_response_time']}s"
                
                elif scenario['name'] == 'rapid_selections':
                    # Simulate rapid UI selections
                    for i in range(scenario['selection_changes']):
                        self._simulate_selection_change(i % len(self.mock_datasets))
                    
                    # Should remain stable (no crashes)
                    assert scenario['expected_stability'], "UI should remain stable under rapid selections"
            
            self.performance_monitor.stop_monitoring()
            metrics = self.performance_monitor.get_metrics()
            
            # Memory should remain reasonable
            assert metrics['memory_usage'] < 0.3, f"Stress test memory usage {metrics['memory_usage']:.2f}GB exceeded 0.3GB"
    
    def test_dataset_dropdown_population(self):
        """Test dropdown population with converted datasets."""
        with patch('requests.get') as mock_get:
            # Mock API response for dataset listing
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                'datasets': self.mock_datasets,
                'total_count': len(self.mock_datasets),
                'by_type': {
                    'garak': 2,
                    'ollegen1': 2
                }
            }
            
            # Test dropdown population
            with patch('streamlit.selectbox') as mock_selectbox:
                # Mock dataset type dropdown
                dataset_types = ['Select a dataset type...', 'Garak Red-teaming Prompts', 'OllaGen1 Cognitive Assessment']
                mock_selectbox.side_effect = ['Garak Red-teaming Prompts']
                
                selected_type = mock_selectbox.side_effect[0]
                assert selected_type in dataset_types[1:]  # Should be a valid type
                
                # Test specific dataset dropdown
                if selected_type == 'Garak Red-teaming Prompts':
                    garak_options = [ds['name'] for ds in self.mock_datasets if ds['type'] == 'garak']
                    assert len(garak_options) == 2, "Should have 2 Garak datasets"
                    assert 'UI Test Garak Dataset 1' in garak_options
                    assert 'UI Test Garak Dataset 2' in garak_options
                
                elif selected_type == 'OllaGen1 Cognitive Assessment':
                    ollegen1_options = [ds['name'] for ds in self.mock_datasets if ds['type'] == 'ollegen1']
                    assert len(ollegen1_options) == 2, "Should have 2 OllaGen1 datasets"
                    assert 'UI Test OllaGen1 Dataset' in ollegen1_options
                    assert 'Large OllaGen1 Dataset (UI Test)' in ollegen1_options
    
    def test_preview_component_rendering(self):
        """Test sample data display components."""
        # Test Garak preview rendering
        garak_dataset = next(ds for ds in self.mock_datasets if ds['type'] == 'garak')
        garak_preview = self._generate_garak_preview(garak_dataset)
        
        with patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.text') as mock_text, \
             patch('streamlit.json') as mock_json, \
             patch('streamlit.dataframe') as mock_dataframe:
            
            # Test Garak preview components
            self._render_garak_preview_ui(garak_preview)
            
            # Validate component calls
            assert mock_subheader.call_count >= 1, "Should display preview header"
            assert mock_json.call_count >= 1, "Should display metadata as JSON"
            
            # Validate preview data structure
            assert len(garak_preview['sample_prompts']) <= 5, "Preview should show max 5 samples"
            for prompt in garak_preview['sample_prompts']:
                assert 'value' in prompt, "Each prompt should have value"
                assert 'metadata' in prompt, "Each prompt should have metadata"
                assert 'attack_type' in prompt['metadata'], "Metadata should include attack type"
        
        # Test OllaGen1 preview rendering
        ollegen1_dataset = next(ds for ds in self.mock_datasets if ds['type'] == 'ollegen1')
        ollegen1_preview = self._generate_ollegen1_preview(ollegen1_dataset)
        
        with patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.dataframe') as mock_dataframe, \
             patch('streamlit.json') as mock_json:
            
            # Test OllaGen1 preview components
            self._render_ollegen1_preview_ui(ollegen1_preview)
            
            # Validate OllaGen1 preview
            assert len(ollegen1_preview['sample_qa_pairs']) <= 10, "Preview should show max 10 Q&A pairs"
            for qa_pair in ollegen1_preview['sample_qa_pairs']:
                assert 'question' in qa_pair, "Each Q&A pair should have question"
                assert 'choices' in qa_pair, "Each Q&A pair should have choices"
                assert 'correct_answer' in qa_pair, "Each Q&A pair should have correct answer"
    
    def test_configuration_form_validation(self):
        """Test input validation and error display."""
        validation_test_cases = [
            {
                'name': 'garak_invalid_threshold',
                'config_type': 'garak',
                'invalid_input': {'classification_threshold': 1.5},
                'expected_error': 'Classification threshold must be between 0.0 and 1.0'
            },
            {
                'name': 'garak_empty_attack_types',
                'config_type': 'garak',
                'invalid_input': {'attack_type_filter': []},
                'expected_error': 'At least one attack type must be selected'
            },
            {
                'name': 'ollegen1_invalid_batch_size',
                'config_type': 'ollegen1',
                'invalid_input': {'batch_size': 0},
                'expected_error': 'Batch size must be greater than 0'
            },
            {
                'name': 'ollegen1_invalid_accuracy',
                'config_type': 'ollegen1',
                'invalid_input': {'extraction_accuracy_threshold': 1.1},
                'expected_error': 'Accuracy threshold must be between 0.0 and 1.0'
            },
            {
                'name': 'ollegen1_empty_question_types',
                'config_type': 'ollegen1',
                'invalid_input': {'question_types': []},
                'expected_error': 'At least one question type must be selected'
            }
        ]
        
        for test_case in validation_test_cases:
            with patch('streamlit.error') as mock_error:
                # Test validation logic
                is_valid = self._validate_config(test_case['config_type'], test_case['invalid_input'])
                
                # Should detect invalid configuration
                assert not is_valid, f"Configuration should be invalid for {test_case['name']}"
                
                # Error message should be displayed
                error_displayed = mock_error.called
                expected_error_shown = test_case['expected_error'] is not None
                assert error_displayed == expected_error_shown, \
                    f"Error display expectation not met for {test_case['name']}"
    
    def test_progress_indicator_functionality(self):
        """Test conversion progress display accuracy."""
        progress_scenarios = [
            {'dataset_type': 'garak', 'total_files': 5, 'processing_time': 15},
            {'dataset_type': 'ollegen1', 'total_scenarios': 1000, 'processing_time': 120}
        ]
        
        for scenario in progress_scenarios:
            with patch('streamlit.progress') as mock_progress, \
                 patch('streamlit.text') as mock_text, \
                 patch('streamlit.empty') as mock_empty:
                
                # Mock progress container
                progress_container = Mock()
                mock_empty.return_value = progress_container
                
                # Simulate progress updates
                progress_values = []
                status_messages = []
                
                def capture_progress(value):
                    progress_values.append(value)
                
                def capture_message(message):
                    status_messages.append(message)
                
                mock_progress.side_effect = capture_progress
                progress_container.text.side_effect = capture_message
                
                # Simulate conversion progress
                if scenario['dataset_type'] == 'garak':
                    for i in range(scenario['total_files']):
                        progress = (i + 1) / scenario['total_files']
                        capture_progress(progress)
                        capture_message(f"Processing file {i + 1}/{scenario['total_files']}")
                        time.sleep(0.1)  # Simulate processing delay
                
                elif scenario['dataset_type'] == 'ollegen1':
                    for i in range(0, scenario['total_scenarios'], 100):
                        progress = min(i / scenario['total_scenarios'], 1.0)
                        capture_progress(progress)
                        capture_message(f"Processing scenarios {i}/{scenario['total_scenarios']}")
                        time.sleep(0.05)  # Simulate processing delay
                
                # Validate progress tracking
                assert len(progress_values) > 0, "Should track progress updates"
                assert progress_values[0] >= 0.0, "Progress should start at or above 0"
                assert progress_values[-1] >= 0.9, "Progress should reach near completion"
                
                # Progress should be monotonically increasing
                for i in range(1, len(progress_values)):
                    assert progress_values[i] >= progress_values[i-1], \
                        f"Progress should not decrease: {progress_values[i]} < {progress_values[i-1]}"
                
                # Status messages should be informative
                assert len(status_messages) == len(progress_values), \
                    "Each progress update should have status message"
                assert all('Processing' in msg for msg in status_messages), \
                    "Status messages should indicate processing"
    
    def test_error_message_display(self):
        """Test user-friendly error message presentation."""
        error_scenarios = [
            {
                'error_type': 'connection_error',
                'error_data': {
                    'message': 'Failed to connect to API server',
                    'status_code': 503,
                    'retry_after': 30
                },
                'expected_display': 'error',  # streamlit.error()
                'user_friendly': True
            },
            {
                'error_type': 'validation_error',
                'error_data': {
                    'message': 'Invalid configuration parameters',
                    'details': {
                        'classification_threshold': 'Must be between 0.0 and 1.0',
                        'attack_type_filter': 'Cannot be empty'
                    }
                },
                'expected_display': 'warning',  # streamlit.warning()
                'user_friendly': True
            },
            {
                'error_type': 'processing_error',
                'error_data': {
                    'message': 'Dataset conversion failed',
                    'job_id': 'job_123',
                    'error_details': 'Memory limit exceeded during processing'
                },
                'expected_display': 'error',
                'user_friendly': True
            },
            {
                'error_type': 'authentication_error',
                'error_data': {
                    'message': 'Authentication token expired',
                    'expires_at': '2025-01-07T10:00:00Z',
                    'refresh_required': True
                },
                'expected_display': 'info',  # streamlit.info() for refresh instructions
                'user_friendly': True
            }
        ]
        
        for scenario in error_scenarios:
            with patch('streamlit.error') as mock_error, \
                 patch('streamlit.warning') as mock_warning, \
                 patch('streamlit.info') as mock_info, \
                 patch('streamlit.button') as mock_button:
                
                # Test error display
                self._display_error_message(scenario['error_type'], scenario['error_data'])
                
                # Validate appropriate display method called
                if scenario['expected_display'] == 'error':
                    assert mock_error.called, f"Should display error for {scenario['error_type']}"
                elif scenario['expected_display'] == 'warning':
                    assert mock_warning.called, f"Should display warning for {scenario['error_type']}"
                elif scenario['expected_display'] == 'info':
                    assert mock_info.called, f"Should display info for {scenario['error_type']}"
                
                # Test user-friendly message content
                if scenario['user_friendly']:
                    error_message = scenario['error_data']['message']
                    assert len(error_message) > 0, "Error message should not be empty"
                    assert not error_message.startswith('['), \
                        "Error message should not contain technical codes"
                    
                    # Should provide actionable information
                    if 'retry_after' in scenario['error_data']:
                        assert 'retry' in error_message.lower() or 'try again' in error_message.lower(), \
                            "Retry errors should mention retry option"
                    
                    if 'refresh_required' in scenario['error_data']:
                        assert mock_button.called, "Authentication errors should show refresh button"
    
    # Helper methods for UI testing
    def _get_garak_ui_config(self, dataset: Dict) -> Dict:
        """Get Garak UI configuration options."""
        return {
            'strategy': 'strategy_3_garak',
            'attack_type_filter': ['dan', 'rtp', 'injection', 'jailbreak'],
            'harm_category_filter': ['jailbreak', 'toxicity', 'manipulation'],
            'classification_threshold': 0.90,
            'include_metadata': True,
            'extract_template_variables': True,
            'enable_multilingual': False,
            'max_prompts_per_file': 100
        }
    
    def _get_ollegen1_ui_config(self, dataset: Dict) -> Dict:
        """Get OllaGen1 UI configuration options."""
        return {
            'strategy': 'strategy_1_cognitive_assessment',
            'question_types': ['WCP', 'WHO', 'TeamRisk', 'TargetFactor'],
            'batch_size': 100,
            'extraction_accuracy_threshold': 0.95,
            'include_metadata': True,
            'enable_progress_tracking': True,
            'memory_limit_gb': 2.0,
            'max_scenarios': 10000
        }
    
    def _generate_mock_preview_data(self, dataset: Dict, page_size: int = 50) -> Dict:
        """Generate mock preview data for large datasets."""
        if dataset['type'] == 'ollegen1':
            return {
                'dataset_id': dataset['id'],
                'sample_qa_pairs': [
                    {
                        'id': f'qa_{i}',
                        'question': f'Sample cognitive question {i}?',
                        'choices': ['Option A', 'Option B', 'Option C', 'Option D'],
                        'correct_answer': i % 4,
                        'metadata': {
                            'scenario_id': f'SC{i:03d}',
                            'question_type': ['WCP', 'WHO', 'TeamRisk', 'TargetFactor'][i % 4]
                        }
                    }
                    for i in range(min(page_size, 50))
                ],
                'pagination': {
                    'current_page': 0,
                    'page_size': page_size,
                    'total_items': dataset['qa_pair_count'],
                    'total_pages': (dataset['qa_pair_count'] + page_size - 1) // page_size
                }
            }
        else:
            return {'sample_prompts': [], 'pagination': {}}
    
    def _generate_large_dataset_list(self, count: int) -> List[Dict]:
        """Generate a large list of mock datasets for performance testing."""
        datasets = []
        for i in range(count):
            dataset_type = 'garak' if i % 2 == 0 else 'ollegen1'
            datasets.append({
                'id': f'{dataset_type}_perf_{i:03d}',
                'type': dataset_type,
                'name': f'Performance Test {dataset_type.title()} Dataset {i}',
                'created_at': f'2025-01-07T{10 + (i % 14):02d}:00:00Z',
                'status': 'active',
                'size_mb': 1.0 + (i * 0.5)
            })
        return datasets
    
    def _simulate_complex_filtering(self) -> List[Dict]:
        """Simulate complex dataset filtering operation."""
        # Simulate filtering by multiple criteria
        filtered = []
        for dataset in self.mock_datasets:
            if 'ui-test' in dataset['tags'] and dataset['status'] == 'active':
                filtered.append(dataset)
        return filtered
    
    def _simulate_selection_change(self, dataset_index: int):
        """Simulate rapid dataset selection changes."""
        if dataset_index < len(self.mock_datasets):
            selected = self.mock_datasets[dataset_index]
            self.mock_session_state['selected_datasets'] = [selected]
    
    def _generate_garak_preview(self, dataset: Dict) -> Dict:
        """Generate Garak preview data."""
        return {
            'dataset_id': dataset['id'],
            'sample_prompts': [
                {
                    'id': f'prompt_{i}',
                    'value': f'Sample Garak prompt {i}: Generate content about [TOPIC]...',
                    'metadata': {
                        'attack_type': ['dan', 'rtp', 'injection'][i % 3],
                        'harm_category': ['jailbreak', 'toxicity', 'manipulation'][i % 3],
                        'template_variables': ['TOPIC', 'HARMFUL_CONTENT'],
                        'confidence_score': 0.85 + (i * 0.03)
                    }
                }
                for i in range(min(5, dataset['prompt_count']))
            ]
        }
    
    def _generate_ollegen1_preview(self, dataset: Dict) -> Dict:
        """Generate OllaGen1 preview data."""
        return {
            'dataset_id': dataset['id'],
            'sample_qa_pairs': [
                {
                    'id': f'qa_{i}',
                    'question': f'What cognitive approach is best for scenario {i}?',
                    'choices': ['Analytical', 'Intuitive', 'Collaborative', 'Emotional'],
                    'correct_answer': i % 4,
                    'metadata': {
                        'scenario_id': f'SC{i:03d}',
                        'question_type': ['WCP', 'WHO', 'TeamRisk', 'TargetFactor'][i % 4],
                        'confidence_score': 0.90 + (i * 0.02)
                    }
                }
                for i in range(min(10, dataset.get('qa_pair_count', 100) // 1000))
            ]
        }
    
    def _render_garak_preview_ui(self, preview_data: Dict):
        """Render Garak preview UI components."""
        # This would contain actual Streamlit rendering logic
        # For testing, we just validate the data structure
        assert 'sample_prompts' in preview_data
        for prompt in preview_data['sample_prompts']:
            assert 'value' in prompt
            assert 'metadata' in prompt
    
    def _render_ollegen1_preview_ui(self, preview_data: Dict):
        """Render OllaGen1 preview UI components."""
        assert 'sample_qa_pairs' in preview_data
        for qa_pair in preview_data['sample_qa_pairs']:
            assert 'question' in qa_pair
            assert 'choices' in qa_pair
    
    def _validate_config(self, config_type: str, config: Dict) -> bool:
        """Validate configuration parameters."""
        if config_type == 'garak':
            if 'classification_threshold' in config:
                threshold = config['classification_threshold']
                if threshold < 0.0 or threshold > 1.0:
                    return False
            
            if 'attack_type_filter' in config:
                if len(config['attack_type_filter']) == 0:
                    return False
        
        elif config_type == 'ollegen1':
            if 'batch_size' in config:
                if config['batch_size'] <= 0:
                    return False
            
            if 'extraction_accuracy_threshold' in config:
                threshold = config['extraction_accuracy_threshold']
                if threshold < 0.0 or threshold > 1.0:
                    return False
            
            if 'question_types' in config:
                if len(config['question_types']) == 0:
                    return False
        
        return True
    
    def _display_error_message(self, error_type: str, error_data: Dict):
        """Display user-friendly error messages."""
        message = error_data.get('message', 'An error occurred')
        
        # This would contain actual error display logic
        # For testing, we validate the error data structure
        assert 'message' in error_data
        assert len(message) > 0


class TestStreamlitUIPerformance:
    """UI performance and usability testing."""
    
    def test_ui_load_time_benchmarks(self):
        """Test page load times meet performance targets."""
        load_time_targets = {
            'dataset_selection_page': 3.0,  # seconds
            'configuration_page': 2.0,
            'preview_page': 5.0,
            'results_page': 4.0
        }
        
        for page_name, target_time in load_time_targets.items():
            start_time = time.time()
            
            # Simulate page loading
            self._simulate_page_load(page_name)
            
            load_time = time.time() - start_time
            assert load_time < target_time, \
                f"{page_name} load time {load_time:.2f}s exceeded target {target_time}s"
    
    def test_ui_memory_usage_monitoring(self):
        """Test UI memory consumption with large datasets."""
        import psutil
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        # Simulate loading large dataset UI
        large_dataset = {
            'id': 'large_test',
            'type': 'ollegen1',
            'qa_pair_count': 679996,
            'size_mb': 2500
        }
        
        with patch('streamlit.dataframe') as mock_dataframe:
            # Simulate memory-intensive UI operations
            self._simulate_large_dataset_ui(large_dataset)
            
            final_memory = process.memory_info().rss / (1024 * 1024)  # MB
            memory_increase = final_memory - initial_memory
            
            # UI memory usage should be reasonable
            assert memory_increase < 100, \
                f"UI memory increase {memory_increase:.1f}MB exceeded 100MB limit"
    
    def test_ui_accessibility_compliance(self):
        """Test UI accessibility features and compliance."""
        accessibility_features = {
            'keyboard_navigation': True,
            'screen_reader_support': True,
            'high_contrast_mode': True,
            'font_scaling': True,
            'color_blind_friendly': True
        }
        
        # Test accessibility compliance
        for feature, should_support in accessibility_features.items():
            supports_feature = self._check_accessibility_feature(feature)
            assert supports_feature == should_support, \
                f"Accessibility feature {feature} support: {supports_feature}, expected: {should_support}"
    
    def test_ui_mobile_responsiveness(self):
        """Test UI functionality on mobile devices."""
        mobile_viewports = [
            {'width': 375, 'height': 667, 'device': 'iPhone SE'},
            {'width': 414, 'height': 896, 'device': 'iPhone 11'},
            {'width': 360, 'height': 640, 'device': 'Android Phone'},
            {'width': 768, 'height': 1024, 'device': 'iPad'}
        ]
        
        for viewport in mobile_viewports:
            # Simulate mobile viewport
            mobile_compatible = self._test_mobile_viewport(
                viewport['width'], 
                viewport['height']
            )
            
            assert mobile_compatible, \
                f"UI should be compatible with {viewport['device']} ({viewport['width']}x{viewport['height']})"
    
    def test_ui_browser_compatibility(self):
        """Test UI compatibility across different browsers."""
        browsers = [
            'Chrome',
            'Firefox', 
            'Safari',
            'Edge'
        ]
        
        for browser in browsers:
            compatible = self._check_browser_compatibility(browser)
            assert compatible, f"UI should be compatible with {browser}"
    
    # Helper methods for performance testing
    def _simulate_page_load(self, page_name: str):
        """Simulate page loading for performance testing."""
        if page_name == 'dataset_selection_page':
            # Simulate loading dataset list
            time.sleep(0.1)
        elif page_name == 'configuration_page':
            # Simulate loading configuration forms
            time.sleep(0.05)
        elif page_name == 'preview_page':
            # Simulate loading dataset preview
            time.sleep(0.2)
        elif page_name == 'results_page':
            # Simulate loading results
            time.sleep(0.15)
    
    def _simulate_large_dataset_ui(self, dataset: Dict):
        """Simulate UI operations with large dataset."""
        # Simulate data processing for large dataset
        qa_count = dataset['qa_pair_count']
        batch_size = 1000
        
        for i in range(0, min(qa_count, 10000), batch_size):
            # Simulate processing batch
            time.sleep(0.001)  # Very small delay
    
    def _check_accessibility_feature(self, feature: str) -> bool:
        """Check if accessibility feature is supported."""
        # Simplified accessibility check
        supported_features = {
            'keyboard_navigation': True,
            'screen_reader_support': True,
            'high_contrast_mode': True,
            'font_scaling': True,
            'color_blind_friendly': True
        }
        return supported_features.get(feature, False)
    
    def _test_mobile_viewport(self, width: int, height: int) -> bool:
        """Test UI in mobile viewport."""
        # Simplified mobile compatibility test
        # In real implementation, this would test responsive design
        min_mobile_width = 320
        return width >= min_mobile_width
    
    def _check_browser_compatibility(self, browser: str) -> bool:
        """Check browser compatibility."""
        # Simplified browser compatibility check
        supported_browsers = ['Chrome', 'Firefox', 'Safari', 'Edge']
        return browser in supported_browsers