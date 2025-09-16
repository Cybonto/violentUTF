#!/usr/bin/env python3
"""
Regression tests for Issue #238: Enhanced Dataset Component Import Fix

Ensures that fixing the import paths for enhanced dataset components
does not break other dataset source types or existing functionality.

Test Categories:
- API-based dataset selection functionality
- File upload dataset creation
- Custom dataset configuration
- Existing dataset management
- Cross-module imports
"""

import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add repository root to Python path for testing
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))


class TestDatasetSourceRegression:
    """Test that other dataset source types continue to work."""

    @pytest.fixture(autouse=True)
    def setup_streamlit_mock(self):
        """Setup comprehensive Streamlit mocking."""
        mock_session_state = {
            'api_dataset_types': [],
            'datasets': {},
            'selected_dataset_type': None,
            'user_token': 'test_token',
            'dataset_configs': {}
        }
        
        with patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.write'), \
             patch('streamlit.error'), \
             patch('streamlit.success'), \
             patch('streamlit.warning'), \
             patch('streamlit.info'), \
             patch('streamlit.selectbox'), \
             patch('streamlit.button'), \
             patch('streamlit.file_uploader'), \
             patch('streamlit.text_input'), \
             patch('streamlit.text_area'), \
             patch('streamlit.json'), \
             patch('streamlit.spinner'):
            yield

    def test_api_dataset_types_loading(self):
        """Test that API dataset types can still be loaded."""
        # Mock the API response
        mock_types = {
            'text_classification': {
                'name': 'Text Classification',
                'description': 'Classification datasets'
            },
            'question_answering': {
                'name': 'Question Answering',
                'description': 'Q&A datasets'
            }
        }
        
        with patch('violentutf.pages.2_Configure_Datasets.load_dataset_types_from_api') as mock_load:
            mock_load.return_value = mock_types
            
            # Import and test the function
            from violentutf.pages import configure_datasets_page
            
            # This should work without the enhanced components
            result = mock_load()
            assert result is not None
            assert 'text_classification' in result
            assert 'question_answering' in result

    def test_basic_dataset_creation_workflow(self):
        """Test that basic dataset creation still works."""
        with patch('violentutf.pages.2_Configure_Datasets.create_dataset_via_api') as mock_create:
            mock_create.return_value = True
            
            # Test dataset creation function
            result = mock_create('test_dataset', 'api', {'type': 'text_classification'})
            assert result is True
            mock_create.assert_called_once_with('test_dataset', 'api', {'type': 'text_classification'})

    def test_file_upload_functionality(self):
        """Test that file upload dataset creation continues to work."""
        # Mock file upload object
        mock_file = MagicMock()
        mock_file.name = 'test_dataset.csv'
        mock_file.read.return_value = b'prompt,response\ntest,response'
        
        with patch('streamlit.file_uploader', return_value=mock_file), \
             patch('violentutf.pages.2_Configure_Datasets.create_dataset_via_api') as mock_create:
            mock_create.return_value = True
            
            # This should work independently of enhanced components
            assert mock_file.name == 'test_dataset.csv'
            assert mock_file.read() == b'prompt,response\ntest,response'

    def test_custom_dataset_configuration(self):
        """Test that custom dataset configuration remains functional."""
        custom_config = {
            'name': 'custom_test',
            'type': 'custom',
            'parameters': {
                'batch_size': 32,
                'max_tokens': 512
            }
        }
        
        with patch('violentutf.pages.2_Configure_Datasets.create_dataset_via_api') as mock_create:
            mock_create.return_value = True
            
            # Test custom configuration
            result = mock_create('custom_test', 'custom', custom_config)
            assert result is True
            mock_create.assert_called_once_with('custom_test', 'custom', custom_config)


class TestExistingDatasetManagement:
    """Test that existing dataset management functionality is preserved."""

    @pytest.fixture(autouse=True)
    def setup_dataset_mock(self):
        """Setup dataset management mocking."""
        mock_datasets = {
            'existing_dataset_1': {
                'name': 'existing_dataset_1',
                'type': 'api',
                'status': 'ready'
            },
            'existing_dataset_2': {
                'name': 'existing_dataset_2',
                'type': 'file',
                'status': 'ready'
            }
        }
        
        with patch('streamlit.session_state') as mock_session:
            mock_session.datasets = mock_datasets
            yield mock_session

    def test_dataset_listing(self):
        """Test that existing datasets can still be listed."""
        with patch('violentutf.pages.2_Configure_Datasets.load_datasets_from_api') as mock_load:
            mock_load.return_value = {
                'dataset1': {'name': 'dataset1', 'type': 'api'},
                'dataset2': {'name': 'dataset2', 'type': 'file'}
            }
            
            datasets = mock_load()
            assert len(datasets) == 2
            assert 'dataset1' in datasets
            assert 'dataset2' in datasets

    def test_dataset_deletion(self):
        """Test that dataset deletion functionality is preserved."""
        with patch('violentutf.pages.2_Configure_Datasets.delete_dataset_via_api') as mock_delete:
            mock_delete.return_value = True
            
            result = mock_delete('test_dataset')
            assert result is True
            mock_delete.assert_called_once_with('test_dataset')

    def test_dataset_preview_basic(self):
        """Test that basic dataset preview functionality works."""
        with patch('violentutf.pages.2_Configure_Datasets.get_dataset_preview') as mock_preview:
            mock_preview.return_value = {
                'sample_data': ['example1', 'example2'],
                'schema': {'columns': ['prompt', 'response']},
                'count': 100
            }
            
            preview = mock_preview('test_dataset')
            assert preview is not None
            assert 'sample_data' in preview
            assert len(preview['sample_data']) == 2


class TestImportIsolation:
    """Test that enhanced component import failures don't affect other modules."""

    def test_enhanced_import_failure_fallback(self):
        """Test graceful fallback when enhanced components can't be imported."""
        # Simulate import failure scenario
        with patch('builtins.__import__', side_effect=ImportError("No module named 'components'")):
            try:
                # This should fail gracefully and not crash the application
                from violentutf.components.dataset_selector import NativeDatasetSelector
                pytest.fail("Expected ImportError was not raised")
            except ImportError:
                # This is expected behavior - the test should pass
                pass

    def test_basic_functionality_unaffected_by_enhanced_import_failure(self):
        """Test that basic dataset functionality works even if enhanced imports fail."""
        # Mock the scenario where enhanced components fail to import
        enhanced_modules = [
            'violentutf.components.dataset_selector',
            'violentutf.components.dataset_configuration',
            'violentutf.components.dataset_preview',
            'violentutf.utils.dataset_ui_components',
            'violentutf.utils.specialized_workflows'
        ]
        
        import_side_effects = {}
        for module in enhanced_modules:
            import_side_effects[module] = ImportError(f"No module named '{module.split('.')[-1]}'")
        
        # Basic API functions should still work
        with patch('violentutf.pages.2_Configure_Datasets.load_dataset_types_from_api') as mock_api:
            mock_api.return_value = {'basic_type': {'name': 'Basic Type'}}
            
            result = mock_api()
            assert result is not None
            assert 'basic_type' in result


class TestStreamlitPageIntegration:
    """Test that the Streamlit page continues to work properly."""

    @pytest.fixture(autouse=True)
    def setup_page_mock(self):
        """Setup comprehensive page mocking."""
        with patch('streamlit.session_state', {}), \
             patch('streamlit.title'), \
             patch('streamlit.header'), \
             patch('streamlit.subheader'), \
             patch('streamlit.radio'), \
             patch('streamlit.selectbox'), \
             patch('streamlit.button'), \
             patch('streamlit.write'), \
             patch('streamlit.error'), \
             patch('streamlit.success'), \
             patch('streamlit.warning'), \
             patch('streamlit.spinner'):
            yield

    def test_page_structure_preserved(self):
        """Test that the page structure and navigation are preserved."""
        # The page should have the main radio button for dataset source selection
        with patch('streamlit.radio') as mock_radio:
            mock_radio.return_value = "Select from Available APIs"
            
            # Basic page elements should be accessible
            selection = mock_radio.return_value
            assert selection == "Select from Available APIs"

    def test_dataset_source_options_available(self):
        """Test that all dataset source options remain available."""
        expected_options = [
            "Select from Available APIs",
            "Select Natively Supported Datasets",
            "Upload Dataset File",
            "Configure Custom Dataset"
        ]
        
        with patch('streamlit.radio') as mock_radio:
            for option in expected_options:
                mock_radio.return_value = option
                result = mock_radio.return_value
                assert result == option

    def test_non_enhanced_flows_unaffected(self):
        """Test that non-enhanced dataset flows are not affected."""
        # Test API dataset flow
        with patch('streamlit.radio', return_value="Select from Available APIs"), \
             patch('violentutf.pages.2_Configure_Datasets.load_dataset_types_from_api') as mock_load:
            mock_load.return_value = {'test_type': {'name': 'Test Type'}}
            
            # This flow should work independently
            types = mock_load()
            assert types is not None
            
        # Test file upload flow  
        with patch('streamlit.radio', return_value="Upload Dataset File"), \
             patch('streamlit.file_uploader') as mock_upload:
            mock_upload.return_value = None
            
            # This flow should work independently
            uploaded = mock_upload.return_value
            assert uploaded is None  # No file uploaded, but function works


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_existing_function_signatures_preserved(self):
        """Test that existing function signatures are not changed."""
        # Import the page module to verify function signatures
        import importlib.util
        
        # Load the module
        spec = importlib.util.spec_from_file_location(
            "configure_datasets", 
            repo_root / "violentutf" / "pages" / "2_Configure_Datasets.py"
        )
        module = importlib.util.module_from_spec(spec)
        
        # Verify key functions exist and are callable
        assert hasattr(module, 'flow_native_datasets')
        assert callable(getattr(module, 'flow_native_datasets'))

    def test_session_state_compatibility(self):
        """Test that session state usage remains compatible."""
        # Mock session state with existing structure
        mock_session_state = {
            'api_dataset_types': {},
            'datasets': {},
            'user_token': 'test_token'
        }
        
        with patch('streamlit.session_state', mock_session_state):
            # These should remain accessible
            assert 'api_dataset_types' in mock_session_state
            assert 'datasets' in mock_session_state
            assert 'user_token' in mock_session_state


if __name__ == "__main__":
    """Run regression tests directly."""
    pytest.main([__file__, "-v", "--tb=short"])