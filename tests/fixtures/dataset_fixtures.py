# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Dataset Test Fixtures

This module provides test fixtures for dataset testing in the ViolentUTF
end-to-end testing framework.

SECURITY: All test data is for defensive security research only.
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List


def create_test_datasets() -> Dict[str, Any]:
    """
    Create test dataset fixtures for end-to-end testing.
    
    Returns test data representing different dataset types
    that would be used in the ViolentUTF platform.
    """
    return {
        "garak": {
            "name": "Garak Red-teaming Test Collection",
            "type": "security_evaluation",
            "files": [
                "test_jailbreak_attacks.jsonl",
                "test_prompt_injection.jsonl", 
                "test_adversarial_prompts.jsonl"
            ],
            "attack_types": ["jailbreak", "prompt_injection", "adversarial"],
            "size": "medium",
            "expected_conversion_time": 30
        },
        "ollegen1": {
            "name": "OllaGen1 Cognitive Assessment Test",
            "type": "cognitive_evaluation",
            "files": [
                "test_cognitive_scenarios.csv",
                "test_person_profiles.json"
            ],
            "cognitive_paths": ["analytical", "intuitive", "creative"],
            "size": "large",
            "expected_conversion_time": 600
        },
        "acpbench": {
            "name": "ACPBench Reasoning Test Suite",
            "type": "reasoning_evaluation", 
            "files": [
                "test_logical_reasoning.json",
                "test_causal_inference.json"
            ],
            "reasoning_categories": ["logical", "causal", "analogical"],
            "size": "medium",
            "expected_conversion_time": 120
        },
        "confaide": {
            "name": "ConfAIde Privacy Evaluation Test",
            "type": "privacy_evaluation",
            "files": [
                "test_privacy_scenarios.json"
            ],
            "privacy_tiers": ["public", "private", "sensitive", "confidential"],
            "size": "medium",
            "expected_conversion_time": 180
        }
    }


def create_performance_test_data() -> Dict[str, Any]:
    """
    Create performance test data fixtures.
    
    Returns test data specifically designed for performance testing.
    """
    return {
        "large_datasets": {
            "docmath_220mb": {
                "size_mb": 220,
                "type": "mathematical_documents",
                "expected_processing_time": 1800,
                "memory_requirement_mb": 2048
            },
            "graphwalk_480mb": {
                "size_mb": 480,
                "type": "graph_reasoning",
                "expected_processing_time": 1800,
                "memory_requirement_mb": 2048
            }
        },
        "concurrent_test_datasets": {
            "small_garak_batch": {
                "count": 5,
                "size_per_dataset_mb": 10,
                "concurrent_processing": True
            },
            "medium_ollegen1_batch": {
                "count": 3,
                "size_per_dataset_mb": 50,
                "concurrent_processing": True
            }
        }
    }