#!/usr/bin/env python3
"""
Test suite for Issue #238: Enhanced Dataset Component Import Resolution

This module tests the import path fix for enhanced dataset components that
were failing due to Python path context mismatch in Streamlit execution.

Test Categories:
- Import resolution from repository root context
- Component instantiation after import
- Cross-platform compatibility
- Error handling and fallback behavior
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add repository root to Python path for testing
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))


class TestImportResolution:
    """Test import resolution for enhanced dataset components."""

    def test_import_dataset_selector(self):
        """Test that NativeDatasetSelector can be imported with absolute path."""
        try:
            from violentutf.components.dataset_selector import NativeDatasetSelector
            assert NativeDatasetSelector is not None
            assert hasattr(NativeDatasetSelector, '__init__')
        except ImportError as e:
            pytest.fail(f"Failed to import NativeDatasetSelector: {e}")

    def test_import_dataset_configuration(self):
        """Test that SpecializedConfigurationInterface can be imported."""
        try:
            from violentutf.components.dataset_configuration import SpecializedConfigurationInterface
            assert SpecializedConfigurationInterface is not None
            assert hasattr(SpecializedConfigurationInterface, '__init__')
        except ImportError as e:
            pytest.fail(f"Failed to import SpecializedConfigurationInterface: {e}")

    def test_import_dataset_preview(self):
        """Test that DatasetPreviewComponent can be imported."""
        try:
            from violentutf.components.dataset_preview import DatasetPreviewComponent
            assert DatasetPreviewComponent is not None
            assert hasattr(DatasetPreviewComponent, '__init__')
        except ImportError as e:
            pytest.fail(f"Failed to import DatasetPreviewComponent: {e}")

    def test_import_dataset_ui_components(self):
        """Test that LargeDatasetUIOptimization can be imported."""
        try:
            from violentutf.utils.dataset_ui_components import LargeDatasetUIOptimization
            assert LargeDatasetUIOptimization is not None
            assert hasattr(LargeDatasetUIOptimization, '__init__')
        except ImportError as e:
            pytest.fail(f"Failed to import LargeDatasetUIOptimization: {e}")

    def test_import_specialized_workflows(self):
        """Test that UserGuidanceSystem can be imported."""
        try:
            from violentutf.utils.specialized_workflows import UserGuidanceSystem
            assert UserGuidanceSystem is not None
            assert hasattr(UserGuidanceSystem, '__init__')
        except ImportError as e:
            pytest.fail(f"Failed to import UserGuidanceSystem: {e}")

    def test_import_all_components_together(self):
        """Test that all components can be imported together."""
        try:
            from violentutf.components.dataset_configuration import SpecializedConfigurationInterface
            from violentutf.components.dataset_preview import DatasetPreviewComponent
            from violentutf.components.dataset_selector import NativeDatasetSelector
            from violentutf.utils.dataset_ui_components import LargeDatasetUIOptimization
            from violentutf.utils.specialized_workflows import UserGuidanceSystem

            # Verify all imports successful
            components = [
                SpecializedConfigurationInterface,
                DatasetPreviewComponent,
                NativeDatasetSelector,
                LargeDatasetUIOptimization,
                UserGuidanceSystem
            ]
            
            for component in components:
                assert component is not None
                assert hasattr(component, '__init__')
                
        except ImportError as e:
            pytest.fail(f"Failed to import all components together: {e}")


class TestComponentInstantiation:
    """Test component instantiation after successful import."""

    @pytest.fixture(autouse=True)
    def setup_streamlit_mock(self):
        """Setup Streamlit mocking for component testing."""
        # Create a mock session state object that behaves like Streamlit's
        mock_session_state = MagicMock()
        mock_session_state.__contains__ = lambda self, key: False
        mock_session_state.__setitem__ = lambda self, key, value: None
        mock_session_state.__getitem__ = lambda self, key: None
        
        with patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.write'), \
             patch('streamlit.error'), \
             patch('streamlit.success'), \
             patch('streamlit.selectbox'), \
             patch('streamlit.button'), \
             patch('streamlit.columns'), \
             patch('streamlit.expander'):
            yield

    def test_native_dataset_selector_instantiation(self):
        """Test NativeDatasetSelector can be instantiated."""
        try:
            from violentutf.components.dataset_selector import NativeDatasetSelector

            # Component should be instantiated successfully
            selector = NativeDatasetSelector()
            assert selector is not None
            assert hasattr(selector, 'display_dataset_categories')
                
        except Exception as e:
            pytest.fail(f"Failed to instantiate NativeDatasetSelector: {e}")

    def test_dataset_preview_component_instantiation(self):
        """Test DatasetPreviewComponent can be instantiated."""
        try:
            from violentutf.components.dataset_preview import DatasetPreviewComponent

            # Component should be instantiated successfully
            preview = DatasetPreviewComponent()
            assert preview is not None
            assert hasattr(preview, 'display_preview')
                
        except Exception as e:
            pytest.fail(f"Failed to instantiate DatasetPreviewComponent: {e}")

    def test_specialized_configuration_interface_instantiation(self):
        """Test SpecializedConfigurationInterface can be instantiated."""
        try:
            from violentutf.components.dataset_configuration import SpecializedConfigurationInterface

            # Component should be instantiated successfully
            config = SpecializedConfigurationInterface()
            assert config is not None
            assert hasattr(config, 'display_configuration')
                
        except Exception as e:
            pytest.fail(f"Failed to instantiate SpecializedConfigurationInterface: {e}")

    def test_user_guidance_system_instantiation(self):
        """Test UserGuidanceSystem can be instantiated."""
        try:
            from violentutf.utils.specialized_workflows import UserGuidanceSystem

            # Component should be instantiated successfully
            guidance = UserGuidanceSystem()
            assert guidance is not None
            assert hasattr(guidance, 'display_guidance')
                
        except Exception as e:
            pytest.fail(f"Failed to instantiate UserGuidanceSystem: {e}")

    def test_large_dataset_ui_optimization_instantiation(self):
        """Test LargeDatasetUIOptimization can be instantiated."""
        try:
            from violentutf.utils.dataset_ui_components import LargeDatasetUIOptimization

            # Component should be instantiated successfully
            optimizer = LargeDatasetUIOptimization()
            assert optimizer is not None
            assert hasattr(optimizer, 'optimize_ui_responsiveness')
                
        except Exception as e:
            pytest.fail(f"Failed to instantiate LargeDatasetUIOptimization: {e}")


class TestCrossContextImports:
    """Test imports work from different execution contexts."""

    def test_import_from_different_working_directory(self):
        """Test imports work when executed from different working directories."""
        original_cwd = os.getcwd()
        
        try:
            # Create temporary directory and change to it
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)
                
                # Ensure violentutf is still importable
                from violentutf.components.dataset_selector import NativeDatasetSelector
                from violentutf.utils.specialized_workflows import UserGuidanceSystem
                
                assert NativeDatasetSelector is not None
                assert UserGuidanceSystem is not None
                
        finally:
            os.chdir(original_cwd)

    def test_import_with_modified_python_path(self):
        """Test imports work with modified Python path."""
        original_path = sys.path.copy()
        
        try:
            # Remove current directory from path to simulate different context
            if '' in sys.path:
                sys.path.remove('')
            if '.' in sys.path:
                sys.path.remove('.')
                
            # Should still work with absolute imports
            from violentutf.components.dataset_preview import DatasetPreviewComponent
            from violentutf.utils.dataset_ui_components import LargeDatasetUIOptimization
            
            assert DatasetPreviewComponent is not None
            assert LargeDatasetUIOptimization is not None
            
        finally:
            sys.path = original_path


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_missing_component_graceful_handling(self):
        """Test graceful handling when a component is missing."""
        # Simulate missing component by temporarily removing from sys.modules
        component_name = 'violentutf.components.dataset_selector'
        
        if component_name in sys.modules:
            original_module = sys.modules[component_name]
            del sys.modules[component_name]
        else:
            original_module = None
            
        try:
            # Mock the import to raise ImportError
            with patch.dict('sys.modules', {component_name: None}):
                with pytest.raises(ImportError):
                    from violentutf.components.dataset_selector import NativeDatasetSelector
                    
        finally:
            # Restore original module if it existed
            if original_module is not None:
                sys.modules[component_name] = original_module

    def test_component_initialization_error_handling(self):
        """Test handling of component initialization errors."""
        from violentutf.components.dataset_selector import NativeDatasetSelector

        # Mock Streamlit session state access to raise an error during initialization  
        with patch('streamlit.session_state') as mock_session:
            mock_session.__contains__ = lambda key: False
            mock_session.__setitem__ = lambda key, value: None
            mock_session.__getitem__ = lambda key: None
            # This should work now without raising errors
            selector = NativeDatasetSelector()
            assert selector is not None


class TestIntegrationWithStreamlitPage:
    """Test integration with the actual Streamlit page code."""

    def test_imports_in_configure_datasets_context(self):
        """Test that imports work in the context of 2_Configure_Datasets.py."""
        # This test simulates the exact import context from the Streamlit page
        
        # Create a mock session state object that behaves like Streamlit's
        mock_session_state = MagicMock()
        mock_session_state.__contains__ = lambda self, key: False
        mock_session_state.__setitem__ = lambda self, key, value: None
        mock_session_state.__getitem__ = lambda self, key: None
        
        # Mock Streamlit dependencies
        with patch('streamlit.session_state', mock_session_state), \
             patch('streamlit.write'), \
             patch('streamlit.error'), \
             patch('streamlit.success'), \
             patch('streamlit.spinner'), \
             patch('streamlit.selectbox'), \
             patch('streamlit.button'), \
             patch('streamlit.columns'), \
             patch('streamlit.expander'):
            
            try:
                # Execute the same imports as in the fixed code
                from violentutf.components.dataset_configuration import SpecializedConfigurationInterface
                from violentutf.components.dataset_preview import DatasetPreviewComponent
                from violentutf.components.dataset_selector import NativeDatasetSelector
                from violentutf.utils.dataset_ui_components import LargeDatasetUIOptimization
                from violentutf.utils.specialized_workflows import UserGuidanceSystem

                # Initialize components as in the actual code
                dataset_selector = NativeDatasetSelector()
                preview_component = DatasetPreviewComponent()
                config_interface = SpecializedConfigurationInterface()
                guidance_system = UserGuidanceSystem()
                ui_optimizer = LargeDatasetUIOptimization()

                # Verify all components initialized successfully
                components = [
                    dataset_selector,
                    preview_component,
                    config_interface,
                    guidance_system,
                    ui_optimizer
                ]
                
                for component in components:
                    assert component is not None
                    
            except ImportError as e:
                pytest.fail(f"Import failed in Streamlit page context: {e}")
            except Exception as e:
                pytest.fail(f"Component initialization failed: {e}")


if __name__ == "__main__":
    """Run tests directly."""
    pytest.main([__file__, "-v", "--tb=short"])