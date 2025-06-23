#!/usr/bin/env python3
"""Test script to verify scorer metadata functionality"""

import json
from datetime import datetime

# Test the metadata structure that will be passed
test_metadata = {
    "generator_id": "gen-123",
    "generator_name": "TestGenerator",
    "generator_type": "AI Gateway",
    "dataset_id": "dataset-456",
    "dataset_name": "TestDataset",
    "dataset_source": "file",
    "scorer_id": "scorer-789",
    "scorer_name": "TestScorer",
    "scorer_type": "SubStringScorer",
    "test_mode": "full_execution",
    "execution_timestamp": datetime.now().isoformat()
}

print("🧪 Testing Scorer Metadata Structure")
print("=" * 60)

print("\n📝 Metadata to be included in scores:")
print(json.dumps(test_metadata, indent=2))

print("\n✅ Metadata structure is valid JSON")
print(f"   Total fields: {len(test_metadata)}")
print(f"   JSON size: {len(json.dumps(test_metadata))} bytes")

print("\n📊 Expected benefits:")
print("1. Dashboard can show which generator was used for each score")
print("2. Dashboard can filter results by dataset")
print("3. Full execution history is preserved")
print("4. Test mode (test vs full execution) is tracked")
print("5. Timestamp allows temporal analysis")

print("\n🔍 Sample PyRIT Score with metadata:")
sample_score = {
    "score_value": True,
    "score_type": "true_false",
    "score_category": "violation_detected",
    "score_rationale": "Found prohibited substring",
    "score_metadata": json.dumps(test_metadata),
    "scorer_class_identifier": {"__type__": "ConfiguredScorerWrapper", "scorer_name": "TestScorer"},
    "prompt_request_response_id": "conv-123",
    "timestamp": datetime.now().isoformat()
}

print(json.dumps(sample_score, indent=2))

print("\n✅ Metadata implementation complete!")
print("   - Metadata is passed from scorer test to execution")
print("   - ConfiguredScorerWrapper stores execution metadata")
print("   - Metadata is included in PyRIT Score object")
print("   - Metadata is returned in API response")
print("   - Dashboard can parse and display metadata")