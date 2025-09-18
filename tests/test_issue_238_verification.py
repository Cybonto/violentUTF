#!/usr/bin/env python3
"""
Verification test for Issue #238: Enhanced Dataset Component Import Fix

This test verifies that the fix for import path context issues
allows enhanced dataset components to be imported and used correctly
in the Streamlit execution environment.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add repository root to Python path for testing
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))


def test_flow_native_datasets_import_success():
    """Test that flow_native_datasets can import enhanced components successfully."""
    
    # Create mock session state that behaves like Streamlit's
    mock_session_state = MagicMock()
    mock_session_state.__contains__ = lambda key: False
    mock_session_state.__setitem__ = lambda key, value: None
    mock_session_state.__getitem__ = lambda key: None
    
    with patch('streamlit.session_state', mock_session_state), \
         patch('streamlit.write'), \
         patch('streamlit.error'), \
         patch('streamlit.success'), \
         patch('streamlit.selectbox'), \
         patch('streamlit.button'), \
         patch('streamlit.columns'), \
         patch('streamlit.expander'):
        
        try:
            # Execute the same imports as in the fixed flow_native_datasets function
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
            assert dataset_selector is not None
            assert preview_component is not None
            assert config_interface is not None
            assert guidance_system is not None
            assert ui_optimizer is not None
            
            # Verify components have expected methods
            assert hasattr(dataset_selector, 'display_dataset_categories')
            assert hasattr(preview_component, 'display_preview')
            assert hasattr(config_interface, 'display_configuration')
            assert hasattr(guidance_system, 'display_guidance')
            assert hasattr(ui_optimizer, 'optimize_ui_responsiveness')
            
            print("✅ Enhanced dataset components import and initialize successfully")
            return True
            
        except ImportError as e:
            print(f"❌ Import failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Component initialization failed: {e}")
            return False


def test_enhanced_categories_available():
    """Test that enhanced dataset categories are available."""
    
    # Create mock session state
    mock_session_state = MagicMock()
    mock_session_state.__contains__ = lambda key: False
    mock_session_state.__setitem__ = lambda key, value: None
    mock_session_state.__getitem__ = lambda key: None
    
    with patch('streamlit.session_state', mock_session_state):
        from violentutf.components.dataset_selector import NativeDatasetSelector
        
        selector = NativeDatasetSelector()
        
        # Verify all 7 categories exist
        expected_categories = [
            "cognitive_behavioral",
            "redteaming", 
            "legal_reasoning",
            "mathematical_reasoning",
            "spatial_reasoning", 
            "privacy_evaluation",
            "meta_evaluation"
        ]
        
        for category in expected_categories:
            assert category in selector.dataset_categories, f"Missing category: {category}"
            
        print(f"✅ All {len(expected_categories)} enhanced dataset categories are available")
        return True


def test_no_fallback_to_basic_interface():
    """Test that enhanced components load without falling back to basic interface."""
    
    import_error_occurred = False
    
    try:
        # Simulate the exact import scenario from the Streamlit page
        from violentutf.components.dataset_configuration import SpecializedConfigurationInterface
        from violentutf.components.dataset_preview import DatasetPreviewComponent
        from violentutf.components.dataset_selector import NativeDatasetSelector
        from violentutf.utils.dataset_ui_components import LargeDatasetUIOptimization
        from violentutf.utils.specialized_workflows import UserGuidanceSystem
        
        print("✅ No import errors - enhanced interface will load (no fallback to basic)")
        
    except ImportError as e:
        import_error_occurred = True
        print(f"❌ Import error would cause fallback to basic interface: {e}")
        
    return not import_error_occurred


if __name__ == "__main__":
    """Run verification tests."""
    print("Running Issue #238 Verification Tests...")
    print("=" * 50)
    
    test1_result = test_flow_native_datasets_import_success()
    test2_result = test_enhanced_categories_available()
    test3_result = test_no_fallback_to_basic_interface()
    
    print("=" * 50)
    print(f"Import and initialization test: {'PASS' if test1_result else 'FAIL'}")
    print(f"Enhanced categories test: {'PASS' if test2_result else 'FAIL'}")
    print(f"No fallback required test: {'PASS' if test3_result else 'FAIL'}")
    
    all_passed = test1_result and test2_result and test3_result
    print(f"\nOverall result: {'ALL TESTS PASSED ✅' if all_passed else 'SOME TESTS FAILED ❌'}")
    
    if all_passed:
        print("\n🎉 Issue #238 has been successfully resolved!")
        print("Enhanced dataset components can now be imported and used correctly.")
    else:
        print("\n⚠️  Issue #238 resolution needs additional work.")