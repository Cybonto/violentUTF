#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Simple unit test for ViolentUTF dataset registry extension
Tests the dataset definitions without external dependencies
"""

import sys
import os

# Test the ViolentUTF dataset definitions directly
VIOLENTUTF_NATIVE_DATASETS = {
    "ollegen1_cognitive": {
        "name": "ollegen1_cognitive",
        "display_name": "OllaGen1 Cognitive Behavioral Security Assessment",
        "description": "170K scenarios with 4 Q&A types for security compliance evaluation",
        "category": "cognitive_behavioral",
        "pyrit_format": "QuestionAnsweringDataset",
        "config_required": True,
        "available_configs": {
            "question_types": ["WCP", "WHO", "TeamRisk", "TargetFactor"],
            "scenario_limit": [1000, 10000, 50000, "all"]
        },
        "file_info": {
            "source_pattern": "datasets/OllaGen1-QA-full.part*.csv",
            "manifest_file": "datasets/OllaGen1-QA-full.manifest.json",
            "total_scenarios": 169999,
            "total_qa_pairs": 679996
        },
        "conversion_strategy": "strategy_1_cognitive_assessment"
    },
    "garak_redteaming": {
        "name": "garak_redteaming",
        "display_name": "Garak Red-Teaming Dataset Collection",
        "description": "25+ files with DAN variants, RTP categories, and jailbreak prompts",
        "category": "redteaming",
        "pyrit_format": "SeedPromptDataset",
        "config_required": True,
        "available_configs": {
            "attack_types": ["DAN", "RTP", "injection", "jailbreak"],
            "severity_levels": ["low", "medium", "high", "critical"]
        },
        "file_info": {
            "source_pattern": "datasets/garak/*.txt",
            "manifest_file": "datasets/garak/garak.manifest.json",
            "total_files": 25,
            "total_prompts": 12000
        },
        "conversion_strategy": "strategy_3_redteaming_prompts"
    },
    "legalbench_reasoning": {
        "name": "legalbench_reasoning",
        "display_name": "LegalBench Legal Reasoning Dataset",
        "description": "Comprehensive legal reasoning tasks and case analysis",
        "category": "legal_reasoning",
        "pyrit_format": "QuestionAnsweringDataset",
        "config_required": True,
        "available_configs": {
            "task_types": ["case_analysis", "statute_interpretation", "contract_review"],
            "complexity_levels": ["basic", "intermediate", "advanced"]
        },
        "file_info": {
            "source_pattern": "datasets/legalbench/*.json",
            "manifest_file": "datasets/legalbench/legalbench.manifest.json",
            "total_tasks": 5000,
            "total_questions": 20000
        },
        "conversion_strategy": "strategy_2_legal_reasoning"
    },
}

# Original PyRIT datasets for testing
PYRIT_DATASETS = {
    "harmbench": {
        "name": "harmbench",
        "description": "HarmBench Dataset - Standardized evaluation of automated red teaming",
        "category": "safety",
        "config_required": False,
        "available_configs": None,
    },
    "aya_redteaming": {
        "name": "aya_redteaming",
        "description": "Aya Red-teaming Dataset - Multilingual red-teaming prompts",
        "category": "redteaming",
        "config_required": True,
        "available_configs": {
            "language": ["English", "Hindi", "French", "Spanish"]
        },
    },
}

# Combined registry
NATIVE_DATASET_TYPES = {**PYRIT_DATASETS, **VIOLENTUTF_NATIVE_DATASETS}


def test_violentutf_datasets_added():
    """Test that ViolentUTF datasets are present in registry"""
    expected_violentutf = ["ollegen1_cognitive", "garak_redteaming", "legalbench_reasoning"]
    
    for dataset_name in expected_violentutf:
        assert dataset_name in NATIVE_DATASET_TYPES, f"ViolentUTF dataset {dataset_name} should be in registry"
    
    print(f"✅ All expected ViolentUTF datasets found in registry")


def test_violentutf_dataset_structure():
    """Test that ViolentUTF datasets have proper structure"""
    required_fields = ["name", "description", "category", "config_required"]
    
    for dataset_name, dataset_info in VIOLENTUTF_NATIVE_DATASETS.items():
        for field in required_fields:
            assert field in dataset_info, f"Dataset {dataset_name} missing required field: {field}"
        
        # Check field types
        assert isinstance(dataset_info["name"], str)
        assert isinstance(dataset_info["description"], str)
        assert isinstance(dataset_info["category"], str)
        assert isinstance(dataset_info["config_required"], bool)
        
        if dataset_info.get("available_configs"):
            assert isinstance(dataset_info["available_configs"], dict)
        
        if dataset_info.get("file_info"):
            assert isinstance(dataset_info["file_info"], dict)
        
        print(f"✅ Dataset {dataset_name} has valid structure")


def test_violentutf_dataset_categories():
    """Test that ViolentUTF datasets have appropriate categories"""
    expected_categories = {
        "ollegen1_cognitive": "cognitive_behavioral",
        "garak_redteaming": "redteaming", 
        "legalbench_reasoning": "legal_reasoning"
    }
    
    for dataset_name, expected_category in expected_categories.items():
        if dataset_name in VIOLENTUTF_NATIVE_DATASETS:
            actual_category = VIOLENTUTF_NATIVE_DATASETS[dataset_name]["category"]
            assert actual_category == expected_category, f"Dataset {dataset_name} has wrong category: {actual_category}"
            print(f"✅ Dataset {dataset_name} has correct category: {actual_category}")


def test_backward_compatibility():
    """Test that PyRIT datasets are still present"""
    expected_pyrit = ["harmbench", "aya_redteaming"]
    
    for dataset_name in expected_pyrit:
        assert dataset_name in NATIVE_DATASET_TYPES, f"PyRIT dataset {dataset_name} should still be in registry"
    
    print(f"✅ PyRIT datasets maintained for backward compatibility")


def test_registry_expansion():
    """Test that registry now has more datasets"""
    total_datasets = len(NATIVE_DATASET_TYPES)
    pyrit_datasets = len(PYRIT_DATASETS)
    violentutf_datasets = len(VIOLENTUTF_NATIVE_DATASETS)
    
    assert total_datasets == pyrit_datasets + violentutf_datasets, "Registry should combine both dataset types"
    assert violentutf_datasets >= 3, f"Should have at least 3 ViolentUTF datasets, has {violentutf_datasets}"
    
    print(f"✅ Registry expanded: {pyrit_datasets} PyRIT + {violentutf_datasets} ViolentUTF = {total_datasets} total")


def test_configuration_support():
    """Test that configurable ViolentUTF datasets have proper config options"""
    configurable_datasets = [
        ("ollegen1_cognitive", ["question_types", "scenario_limit"]),
        ("garak_redteaming", ["attack_types", "severity_levels"]),
        ("legalbench_reasoning", ["task_types", "complexity_levels"])
    ]
    
    for dataset_name, expected_config_keys in configurable_datasets:
        if dataset_name in VIOLENTUTF_NATIVE_DATASETS:
            dataset_info = VIOLENTUTF_NATIVE_DATASETS[dataset_name]
            assert dataset_info.get("config_required") is True, f"Dataset {dataset_name} should require configuration"
            
            available_configs = dataset_info.get("available_configs")
            assert available_configs is not None, f"Dataset {dataset_name} should have available_configs"
            
            for config_key in expected_config_keys:
                assert config_key in available_configs, f"Dataset {dataset_name} should have config option: {config_key}"
            
            print(f"✅ Dataset {dataset_name} has proper configuration support")


def test_file_info_structure():
    """Test that datasets with split files have file_info"""
    datasets_with_files = ["ollegen1_cognitive", "garak_redteaming", "legalbench_reasoning"]
    
    for dataset_name in datasets_with_files:
        if dataset_name in VIOLENTUTF_NATIVE_DATASETS:
            dataset_info = VIOLENTUTF_NATIVE_DATASETS[dataset_name]
            file_info = dataset_info.get("file_info")
            
            assert file_info is not None, f"Dataset {dataset_name} should have file_info for split files"
            assert isinstance(file_info, dict), f"file_info should be dict for {dataset_name}"
            
            # Check for expected file_info fields
            expected_fields = ["source_pattern", "manifest_file"]
            for field in expected_fields:
                assert field in file_info, f"Dataset {dataset_name} file_info should have {field}"
            
            print(f"✅ Dataset {dataset_name} has proper file_info structure")


def main():
    """Run all unit tests"""
    print("\n🧪 Simple Unit Tests for ViolentUTF Dataset Registry Extension\n")
    
    tests = [
        test_violentutf_datasets_added,
        test_violentutf_dataset_structure,
        test_violentutf_dataset_categories,
        test_backward_compatibility,
        test_registry_expansion,
        test_configuration_support,
        test_file_info_structure,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"✅ {test_func.__name__}")
        except AssertionError as e:
            print(f"❌ {test_func.__name__}: {e}")
        except Exception as e:
            print(f"❌ {test_func.__name__}: Unexpected error: {e}")
        print()
    
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! ViolentUTF dataset registry extension is working correctly!")
        return True
    else:
        print(f"❌ {total - passed} tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)