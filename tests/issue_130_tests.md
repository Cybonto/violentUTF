# Issue #130 Test Specification: JudgeBench Meta-Evaluation Converter

## Test Overview

This document specifies comprehensive tests for Issue #130 - JudgeBench Meta-Evaluation Converter implementation. Tests follow Test-Driven Development (TDD) methodology with RED-GREEN-REFACTOR cycles.

**Test Coverage Requirement**: 100%  
**Testing Framework**: pytest  
**Test Categories**: Unit, Integration, Performance, Quality  

## Test Data Preparation

### Mock JSONL Judge Evaluation Data

```python
# Mock data for Arena-Hard judge evaluation
MOCK_ARENA_HARD_EVALUATION = {
    "id": "eval_arena_001",
    "original_task": "Write a creative story about space exploration with scientific accuracy",
    "model_response": "Commander Sarah Chen gazed out at the infinite cosmos through the observation deck of the Mars Transit Station...",
    "judge_name": "arena_hard", 
    "judge_model": "gpt-4",
    "judge_response": "This response demonstrates excellent creativity combined with scientific accuracy. The narrative effectively balances engaging storytelling with realistic space exploration concepts.",
    "score": 8.5,
    "reasoning": "The story successfully combines scientific accuracy with compelling narrative structure. Technical details about Mars transit are realistic while maintaining reader engagement through character development.",
    "evaluation_criteria": ["creativity", "scientific_accuracy", "narrative_flow", "technical_plausibility"],
    "metadata": {
        "response_model": "claude-3",
        "task_category": "creative_writing",
        "difficulty_level": "high",
        "evaluation_timestamp": "2024-12-01T10:30:00Z"
    }
}

# Mock data for Reward Model judge evaluation  
MOCK_REWARD_MODEL_EVALUATION = {
    "id": "eval_reward_001",
    "original_task": "Provide ethical guidance on AI development priorities",
    "model_response": "AI development should prioritize safety, transparency, and human benefit above rapid capability advancement...",
    "judge_name": "reward_model",
    "judge_model": "claude-3-opus", 
    "judge_response": "This response demonstrates strong ethical reasoning and balanced perspective on AI development priorities.",
    "score": 9.2,
    "reasoning": "The response shows comprehensive understanding of AI ethics with well-structured arguments for safety-first development approaches.",
    "evaluation_criteria": ["ethical_reasoning", "balance", "comprehensiveness", "practicality"],
    "metadata": {
        "response_model": "gpt-4",
        "task_category": "ethics",
        "difficulty_level": "medium",
        "evaluation_timestamp": "2024-12-01T10:35:00Z"
    }
}

# Mock data for Prometheus-2 judge evaluation
MOCK_PROMETHEUS_2_EVALUATION = {
    "id": "eval_prometheus_001", 
    "original_task": "Analyze the economic impact of renewable energy adoption",
    "model_response": "Renewable energy adoption creates substantial long-term economic benefits through job creation, energy independence, and reduced healthcare costs...",
    "judge_name": "prometheus_2",
    "judge_model": "gpt-4-turbo",
    "judge_response": "This analysis provides comprehensive coverage of economic factors with strong supporting evidence and clear reasoning.",
    "score": 7.8,
    "reasoning": "The response covers multiple economic dimensions including direct costs, indirect benefits, and long-term implications. Evidence is well-sourced and reasoning is logically structured.",
    "evaluation_criteria": ["comprehensiveness", "evidence_quality", "economic_reasoning", "clarity"],
    "metadata": {
        "response_model": "claude-2",
        "task_category": "economic_analysis", 
        "difficulty_level": "high",
        "evaluation_timestamp": "2024-12-01T10:40:00Z"
    }
}
```

### Large File Test Data

```python
# Generate large JSONL test file (simulating 7-12MB files)
def generate_large_jsonl_test_file(file_path: str, num_entries: int = 5000):
    """Generate large JSONL file for performance testing"""
    base_evaluation = MOCK_ARENA_HARD_EVALUATION.copy()
    
    with open(file_path, 'w') as f:
        for i in range(num_entries):
            evaluation = base_evaluation.copy()
            evaluation['id'] = f"eval_performance_{i:06d}"
            evaluation['score'] = random.uniform(5.0, 10.0)
            evaluation['model_response'] = f"Generated response content for evaluation {i} " * 50  # Make it substantial
            f.write(json.dumps(evaluation) + '\n')
```

## Unit Tests

### Test 1: JudgeBench Schema Validation

```python
def test_judge_file_info_schema():
    """Test JudgeFileInfo schema validation and creation"""
    # RED: Create test that initially fails
    judge_info = JudgeFileInfo(
        judge_name="arena_hard",
        judge_model="gpt-4", 
        response_model="claude-3",
        file_path="/path/to/judge/file.jsonl",
        file_size_mb=8.5
    )
    
    assert judge_info.judge_name == "arena_hard"
    assert judge_info.judge_model == "gpt-4"
    assert judge_info.response_model == "claude-3"
    assert judge_info.file_size_mb == 8.5
    
    # Test invalid data
    with pytest.raises(ValidationError):
        JudgeFileInfo(judge_name="", judge_model="gpt-4")

def test_judge_analysis_schema():
    """Test JudgeAnalysis schema with comprehensive performance indicators"""
    analysis = JudgeAnalysis(
        performance_indicators={
            "response_length": 245,
            "reasoning_length": 128,
            "score_value": 8.5,
            "has_detailed_reasoning": True,
            "evaluation_completeness": 0.95
        },
        evaluation_dimensions=["accuracy", "consistency", "reasoning_quality"],
        reasoning_quality={"clarity": 0.9, "logic": 0.85, "completeness": 0.92},
        score_appropriateness={"consistency": 0.88, "calibration": 0.91},
        consistency_indicators={"score_reasoning_alignment": 0.87},
        judge_characteristics={"judge_type": "arena_hard", "model": "gpt-4"}
    )
    
    assert len(analysis.evaluation_dimensions) == 3
    assert analysis.reasoning_quality["clarity"] == 0.9
    assert analysis.performance_indicators["has_detailed_reasoning"] is True

def test_judge_evaluation_entry_validation():
    """Test JSONL entry parsing and validation"""
    entry = JudgeEvaluationEntry(**MOCK_ARENA_HARD_EVALUATION)
    
    assert entry.judge_name == "arena_hard"
    assert entry.score == 8.5
    assert len(entry.evaluation_criteria) == 4
    
    # Test invalid score range
    invalid_entry = MOCK_ARENA_HARD_EVALUATION.copy()
    invalid_entry['score'] = 15.0  # Invalid score
    with pytest.raises(ValidationError):
        JudgeEvaluationEntry(**invalid_entry)
```

### Test 2: File Discovery and Pattern Matching

```python
def test_judge_file_discovery(tmp_path):
    """Test discovery of judge output files using filename patterns"""
    # Create mock judge files
    arena_file = tmp_path / "dataset=judgebench,response_model=claude-3,judge_name=arena_hard,judge_model=gpt-4.jsonl"
    reward_file = tmp_path / "dataset=judgebench,response_model=gpt-4,judge_name=reward_model,judge_model=claude-opus.jsonl"
    prometheus_file = tmp_path / "dataset=judgebench,response_model=claude-2,judge_name=prometheus_2,judge_model=gpt-4-turbo.jsonl"
    
    arena_file.write_text('{"test": "data"}\n')
    reward_file.write_text('{"test": "data"}\n')  
    prometheus_file.write_text('{"test": "data"}\n')
    
    converter = JudgeBenchConverter()
    discovered_files = converter.discover_judge_output_files(str(tmp_path))
    
    assert len(discovered_files) == 3
    assert any("arena_hard" in f for f in discovered_files)
    assert any("reward_model" in f for f in discovered_files)
    assert any("prometheus_2" in f for f in discovered_files)

def test_filename_parsing():
    """Test parsing of judge output filenames for metadata extraction"""
    filename = "dataset=judgebench,response_model=claude-3,judge_name=arena_hard,judge_model=gpt-4.jsonl"
    
    converter = JudgeBenchConverter()
    file_info = converter.parse_output_filename(filename)
    
    assert file_info.judge_name == "arena_hard"
    assert file_info.judge_model == "gpt-4"
    assert file_info.response_model == "claude-3"
    
    # Test malformed filename
    with pytest.raises(ValueError):
        converter.parse_output_filename("invalid_filename.jsonl")
```

### Test 3: JSONL Streaming Processing

```python
def test_jsonl_streaming_processing(tmp_path):
    """Test memory-efficient streaming processing of large JSONL files"""
    # Create test JSONL file
    test_file = tmp_path / "test_judge.jsonl" 
    with open(test_file, 'w') as f:
        for i in range(1000):  # Moderate size for unit test
            evaluation = MOCK_ARENA_HARD_EVALUATION.copy()
            evaluation['id'] = f"eval_{i:06d}"
            f.write(json.dumps(evaluation) + '\n')
    
    file_info = JudgeFileInfo(
        judge_name="arena_hard",
        judge_model="gpt-4",
        response_model="claude-3", 
        file_path=str(test_file),
        file_size_mb=1.0
    )
    
    converter = JudgeBenchConverter()
    prompts = converter.process_judge_output_file(str(test_file), file_info, {})
    
    assert len(prompts) == 1000
    assert all(isinstance(p, SeedPrompt) for p in prompts)
    assert all("meta_evaluation_type" in p.metadata for p in prompts)

def test_jsonl_error_handling(tmp_path):
    """Test error handling during JSONL processing"""
    # Create file with some invalid JSON lines
    test_file = tmp_path / "test_judge_errors.jsonl"
    with open(test_file, 'w') as f:
        f.write(json.dumps(MOCK_ARENA_HARD_EVALUATION) + '\n')  # Valid
        f.write('{"invalid": json}\n')  # Invalid JSON
        f.write(json.dumps(MOCK_REWARD_MODEL_EVALUATION) + '\n')  # Valid
    
    file_info = JudgeFileInfo(
        judge_name="arena_hard", 
        judge_model="gpt-4",
        response_model="claude-3",
        file_path=str(test_file),
        file_size_mb=0.1
    )
    
    converter = JudgeBenchConverter()
    prompts = converter.process_judge_output_file(str(test_file), file_info, {})
    
    # Should recover from errors and process valid lines
    assert len(prompts) == 2  # Two valid lines processed
```

### Test 4: Meta-Evaluation Prompt Generation

```python
def test_meta_evaluation_prompt_generation():
    """Test quality and structure of generated meta-evaluation prompts"""
    generator = MetaEvaluationPromptGenerator()
    
    file_info = JudgeFileInfo(
        judge_name="arena_hard",
        judge_model="gpt-4", 
        response_model="claude-3",
        file_path="test.jsonl",
        file_size_mb=1.0
    )
    
    prompt = generator.build_meta_evaluation_prompt(
        original_task="Write a creative story about space exploration",
        judge_response="This response demonstrates excellent creativity...",
        judge_score=8.5,
        judge_reasoning="The story effectively combines scientific accuracy...",
        file_info=file_info
    )
    
    # Validate prompt structure
    assert "ORIGINAL TASK" in prompt
    assert "JUDGE INFORMATION" in prompt  
    assert "JUDGE'S EVALUATION" in prompt
    assert "META-EVALUATION REQUEST" in prompt
    assert "arena_hard" in prompt
    assert "gpt-4" in prompt
    assert "8.5" in prompt
    
    # Validate meta-evaluation dimensions
    assert "Accuracy" in prompt
    assert "Consistency" in prompt
    assert "Completeness" in prompt
    assert "Reasoning Quality" in prompt
    assert "Bias Detection" in prompt
    assert "Score Appropriateness" in prompt

def test_judge_specific_prompt_templates():
    """Test judge-specific meta-evaluation prompt templates"""
    generator = MetaEvaluationPromptGenerator()
    
    # Test Arena-Hard specific elements
    arena_criteria = generator.get_meta_evaluation_criteria("arena_hard")
    assert "difficulty_calibration" in arena_criteria
    assert "comparative_ranking" in arena_criteria
    assert "competitive_assessment" in arena_criteria
    
    # Test Reward Model specific elements
    reward_criteria = generator.get_meta_evaluation_criteria("reward_model") 
    assert "reward_alignment" in reward_criteria
    assert "preference_consistency" in reward_criteria
    assert "value_alignment" in reward_criteria
    
    # Test Prometheus-2 specific elements
    prometheus_criteria = generator.get_meta_evaluation_criteria("prometheus_2")
    assert "rubric_adherence" in prometheus_criteria
    assert "score_justification" in prometheus_criteria
    assert "criterion_coverage" in prometheus_criteria

def test_meta_scorer_configuration():
    """Test meta-evaluation scorer configuration generation"""
    generator = MetaEvaluationPromptGenerator()
    
    # Test Arena-Hard scorer config
    arena_config = generator.get_meta_scorer_config("arena_hard")
    assert arena_config["evaluation_focus"] == "competitive_performance_assessment"
    assert "accuracy" in arena_config["primary_dimensions"]
    assert "ranking_consistency" in arena_config["primary_dimensions"]
    assert "difficulty_calibration" in arena_config["primary_dimensions"]
    
    # Test scoring weights
    weights = arena_config["scoring_weight"]
    assert weights["accuracy"] == 0.4
    assert weights["consistency"] == 0.3
    assert weights["calibration"] == 0.3
    assert sum(weights.values()) == 1.0
```

### Test 5: Judge Performance Analysis

```python
def test_judge_performance_analysis():
    """Test judge performance indicator extraction and analysis"""
    analyzer = JudgePerformanceAnalyzer()
    
    file_info = JudgeFileInfo(
        judge_name="arena_hard",
        judge_model="gpt-4",
        response_model="claude-3", 
        file_path="test.jsonl",
        file_size_mb=1.0
    )
    
    analysis = analyzer.analyze_single_evaluation(MOCK_ARENA_HARD_EVALUATION, file_info)
    
    # Validate performance indicators
    assert "response_length" in analysis.performance_indicators
    assert "reasoning_length" in analysis.performance_indicators
    assert "score_value" in analysis.performance_indicators
    assert "has_detailed_reasoning" in analysis.performance_indicators
    assert "evaluation_completeness" in analysis.performance_indicators
    
    # Validate evaluation dimensions
    assert len(analysis.evaluation_dimensions) > 0
    assert all(isinstance(dim, str) for dim in analysis.evaluation_dimensions)
    
    # Validate reasoning quality assessment
    assert "clarity" in analysis.reasoning_quality
    assert "logic" in analysis.reasoning_quality
    assert "completeness" in analysis.reasoning_quality
    assert all(0 <= v <= 1 for v in analysis.reasoning_quality.values())

def test_aggregate_judge_file_performance():
    """Test aggregate performance analysis across multiple evaluations"""
    analyzer = JudgePerformanceAnalyzer()
    
    # Create multiple mock prompts
    prompts = []
    for i in range(10):
        metadata = {
            "original_score": random.uniform(5.0, 10.0),
            "judge_performance_indicators": {
                "reasoning_length": random.randint(50, 200),
                "response_length": random.randint(100, 500)
            }
        }
        prompts.append(SeedPrompt(f"prompt_{i}", metadata))
    
    performance = analyzer.analyze_judge_file_performance(prompts)
    
    assert performance["total_evaluations"] == 10
    assert "score_statistics" in performance
    assert "reasoning_statistics" in performance
    assert "response_statistics" in performance
    
    # Validate statistics
    stats = performance["score_statistics"]
    assert 5.0 <= stats["mean"] <= 10.0
    assert stats["min"] >= 5.0
    assert stats["max"] <= 10.0

def test_reasoning_quality_assessment():
    """Test reasoning quality assessment algorithms"""
    analyzer = JudgePerformanceAnalyzer()
    
    high_quality_reasoning = "The response demonstrates excellent understanding of the topic with clear logical progression. Each point is well-supported with evidence and the conclusion follows naturally from the premises presented."
    
    low_quality_reasoning = "Good response."
    
    high_quality_score = analyzer.assess_reasoning_quality(high_quality_reasoning)
    low_quality_score = analyzer.assess_reasoning_quality(low_quality_reasoning)
    
    assert high_quality_score["clarity"] > low_quality_score["clarity"]
    assert high_quality_score["completeness"] > low_quality_score["completeness"]
    assert high_quality_score["logic"] > low_quality_score["logic"]
```

### Test 6: SeedPrompt and SeedPromptDataset Creation

```python
def test_seed_prompt_creation():
    """Test creation of SeedPrompt instances with comprehensive metadata"""
    converter = JudgeBenchConverter()
    
    file_info = JudgeFileInfo(
        judge_name="arena_hard",
        judge_model="gpt-4",
        response_model="claude-3",
        file_path="test.jsonl", 
        file_size_mb=1.0
    )
    
    prompt = converter.create_meta_evaluation_prompt(
        MOCK_ARENA_HARD_EVALUATION,
        file_info,
        {},
        1
    )
    
    # Validate SeedPrompt structure
    assert isinstance(prompt, SeedPrompt)
    assert isinstance(prompt.value, str)
    assert isinstance(prompt.metadata, dict)
    
    # Validate required metadata fields
    required_fields = [
        "evaluation_id", "judge_name", "judge_model", "response_model",
        "original_score", "judge_performance_indicators", "evaluation_dimensions",
        "meta_evaluation_type", "expected_meta_behavior", "meta_evaluation_criteria",
        "harm_categories", "meta_scorer_config"
    ]
    
    for field in required_fields:
        assert field in prompt.metadata, f"Missing required field: {field}"
    
    # Validate metadata values
    assert prompt.metadata["judge_name"] == "arena_hard"
    assert prompt.metadata["judge_model"] == "gpt-4"
    assert prompt.metadata["response_model"] == "claude-3"
    assert prompt.metadata["original_score"] == 8.5
    assert prompt.metadata["meta_evaluation_type"] == "judge_assessment"

def test_seed_prompt_dataset_creation(tmp_path):
    """Test complete SeedPromptDataset creation from judge files"""
    # Create mock judge files
    arena_file = tmp_path / "dataset=judgebench,response_model=claude-3,judge_name=arena_hard,judge_model=gpt-4.jsonl"
    
    with open(arena_file, 'w') as f:
        for i in range(5):
            evaluation = MOCK_ARENA_HARD_EVALUATION.copy()
            evaluation['id'] = f"eval_{i:06d}"
            f.write(json.dumps(evaluation) + '\n')
    
    converter = JudgeBenchConverter()
    dataset = converter.convert(str(tmp_path))
    
    # Validate SeedPromptDataset structure
    assert isinstance(dataset, SeedPromptDataset)
    assert hasattr(dataset, 'prompts')
    assert hasattr(dataset, 'metadata')
    
    # Validate dataset metadata
    expected_metadata_fields = [
        "evaluation_framework", "judge_count", "total_evaluations",
        "total_files_processed", "response_models", "judge_models",
        "judge_metadata", "meta_evaluation_types", "conversion_strategy"
    ]
    
    for field in expected_metadata_fields:
        assert field in dataset.metadata, f"Missing dataset metadata field: {field}"
    
    # Validate prompts
    assert len(dataset.prompts) == 5
    assert all(isinstance(p, SeedPrompt) for p in dataset.prompts)
    
    # Validate conversion strategy
    assert dataset.metadata["conversion_strategy"] == "strategy_4_meta_evaluation"
    assert dataset.metadata["evaluation_framework"] == "judge_meta_evaluation"
```

## Integration Tests

### Test 7: Complete Conversion Pipeline

```python
def test_complete_conversion_pipeline(tmp_path):
    """Test complete end-to-end conversion pipeline"""
    # Create comprehensive test dataset
    arena_file = tmp_path / "dataset=judgebench,response_model=claude-3,judge_name=arena_hard,judge_model=gpt-4.jsonl"
    reward_file = tmp_path / "dataset=judgebench,response_model=gpt-4,judge_name=reward_model,judge_model=claude-opus.jsonl"
    prometheus_file = tmp_path / "dataset=judgebench,response_model=claude-2,judge_name=prometheus_2,judge_model=gpt-4-turbo.jsonl"
    
    # Write test data
    with open(arena_file, 'w') as f:
        for i in range(3):
            eval_data = MOCK_ARENA_HARD_EVALUATION.copy()
            eval_data['id'] = f"arena_eval_{i:06d}"
            f.write(json.dumps(eval_data) + '\n')
    
    with open(reward_file, 'w') as f:
        for i in range(3):
            eval_data = MOCK_REWARD_MODEL_EVALUATION.copy()
            eval_data['id'] = f"reward_eval_{i:06d}"
            f.write(json.dumps(eval_data) + '\n')
    
    with open(prometheus_file, 'w') as f:
        for i in range(3):
            eval_data = MOCK_PROMETHEUS_2_EVALUATION.copy()
            eval_data['id'] = f"prometheus_eval_{i:06d}"
            f.write(json.dumps(eval_data) + '\n')
    
    # Execute complete conversion
    converter = JudgeBenchConverter()
    dataset = converter.convert(str(tmp_path))
    
    # Validate complete conversion
    assert len(dataset.prompts) == 9  # 3 files × 3 evaluations each
    assert dataset.metadata["judge_count"] == 3
    assert dataset.metadata["total_evaluations"] == 9
    assert dataset.metadata["total_files_processed"] == 3
    
    # Validate multi-model judge representation
    judge_models = dataset.metadata["judge_models"]
    assert "gpt-4" in judge_models
    assert "claude-opus" in judge_models  
    assert "gpt-4-turbo" in judge_models
    
    response_models = dataset.metadata["response_models"]
    assert "claude-3" in response_models
    assert "gpt-4" in response_models
    assert "claude-2" in response_models
    
    # Validate judge-specific metadata
    judge_metadata = dataset.metadata["judge_metadata"]
    assert len(judge_metadata) == 3
    
    for judge_key, metadata in judge_metadata.items():
        assert "evaluation_count" in metadata
        assert "file_size_mb" in metadata
        assert "evaluation_focus" in metadata
        assert "performance_analysis" in metadata

def test_multi_model_hierarchy_preservation():
    """Test preservation of multi-model evaluation hierarchies"""
    converter = JudgeBenchConverter()
    
    # Test hierarchy extraction from judge metadata
    judge_metadata = {
        "arena_hard_gpt-4_claude-3": {
            "judge_name": "arena_hard",
            "judge_model": "gpt-4", 
            "response_model": "claude-3",
            "evaluation_count": 100
        },
        "arena_hard_gpt-4_gpt-4": {
            "judge_name": "arena_hard",
            "judge_model": "gpt-4",
            "response_model": "gpt-4", 
            "evaluation_count": 95
        }
    }
    
    response_models = converter.extract_response_models(judge_metadata)
    judge_models = converter.extract_judge_models(judge_metadata)
    
    assert "claude-3" in response_models
    assert "gpt-4" in response_models
    assert "gpt-4" in judge_models
    assert len(response_models) == 2
    assert len(judge_models) == 1
```

## Performance Tests

### Test 8: Large File Processing Performance

```python
def test_large_file_processing_performance(tmp_path):
    """Test performance with large JSONL files (7-12MB simulation)"""
    import time
    import psutil
    import os
    
    # Generate large test file (simulate 12MB file)
    large_file = tmp_path / "dataset=judgebench,response_model=claude-3,judge_name=arena_hard,judge_model=gpt-4.jsonl"
    
    # Generate ~5000 entries for substantial file size
    start_generation = time.time()
    with open(large_file, 'w') as f:
        for i in range(5000):
            evaluation = MOCK_ARENA_HARD_EVALUATION.copy()
            evaluation['id'] = f"perf_eval_{i:06d}"
            evaluation['model_response'] = "Extended model response content " * 50  # Make entries substantial
            f.write(json.dumps(evaluation) + '\n')
    
    generation_time = time.time() - start_generation
    file_size_mb = os.path.getsize(large_file) / (1024 * 1024)
    
    print(f"Generated test file: {file_size_mb:.1f}MB in {generation_time:.2f}s")
    
    # Test processing performance
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
    
    converter = JudgeBenchConverter()
    start_time = time.time()
    
    file_info = JudgeFileInfo(
        judge_name="arena_hard",
        judge_model="gpt-4",
        response_model="claude-3",
        file_path=str(large_file),
        file_size_mb=file_size_mb
    )
    
    prompts = converter.process_judge_output_file(str(large_file), file_info, {})
    
    processing_time = time.time() - start_time
    peak_memory = process.memory_info().rss / (1024 * 1024)  # MB
    memory_increase = peak_memory - initial_memory
    
    # Performance assertions
    assert processing_time < 300  # Must complete within 5 minutes (300 seconds)
    assert memory_increase < 1024  # Memory increase must be <1GB
    assert len(prompts) == 5000
    
    # Calculate throughput
    throughput = len(prompts) / processing_time
    assert throughput > 500  # Must process >500 evaluations per minute (8.33/sec)
    
    print(f"Performance Results:")
    print(f"  Processing Time: {processing_time:.2f}s")
    print(f"  Memory Increase: {memory_increase:.1f}MB")
    print(f"  Throughput: {throughput:.1f} evaluations/second")

def test_memory_efficient_streaming():
    """Test memory efficiency during streaming processing"""
    import gc
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    def get_memory_mb():
        return process.memory_info().rss / (1024 * 1024)
    
    converter = JudgeBenchConverter()
    initial_memory = get_memory_mb()
    
    # Process multiple chunks and verify memory doesn't accumulate
    memory_readings = []
    
    for chunk in range(5):
        # Simulate processing large chunks
        mock_prompts = []
        for i in range(1000):
            metadata = {"test": f"chunk_{chunk}_item_{i}"}
            mock_prompts.append(SeedPrompt(f"prompt_{i}", metadata))
        
        # Process chunk
        analyzer = JudgePerformanceAnalyzer()
        performance = analyzer.analyze_judge_file_performance(mock_prompts)
        
        # Force garbage collection
        del mock_prompts
        gc.collect()
        
        current_memory = get_memory_mb()
        memory_readings.append(current_memory - initial_memory)
    
    # Verify memory doesn't continuously increase
    assert max(memory_readings) - min(memory_readings) < 100  # Memory variance <100MB
    assert memory_readings[-1] < 500  # Final memory increase <500MB
```

## Quality Tests

### Test 9: Meta-Evaluation Prompt Quality

```python
def test_meta_evaluation_prompt_quality():
    """Test quality and relevance of generated meta-evaluation prompts"""
    generator = MetaEvaluationPromptGenerator()
    
    # Test comprehensive prompt structure
    test_cases = [
        ("arena_hard", MOCK_ARENA_HARD_EVALUATION),
        ("reward_model", MOCK_REWARD_MODEL_EVALUATION), 
        ("prometheus_2", MOCK_PROMETHEUS_2_EVALUATION)
    ]
    
    for judge_name, evaluation in test_cases:
        file_info = JudgeFileInfo(
            judge_name=judge_name,
            judge_model=evaluation["judge_model"],
            response_model=evaluation["metadata"]["response_model"],
            file_path="test.jsonl",
            file_size_mb=1.0
        )
        
        prompt = generator.build_meta_evaluation_prompt(
            original_task=evaluation["original_task"],
            judge_response=evaluation["judge_response"],
            judge_score=evaluation["score"],
            judge_reasoning=evaluation["reasoning"], 
            file_info=file_info
        )
        
        # Quality checks
        assert len(prompt) > 500  # Comprehensive prompt length
        assert len(prompt) < 3000  # Not excessively long
        
        # Content validation
        assert evaluation["original_task"][:50] in prompt  # Original task included
        assert str(evaluation["score"]) in prompt  # Score included
        assert judge_name in prompt  # Judge name included
        assert evaluation["judge_model"] in prompt  # Judge model included
        
        # Meta-evaluation structure validation
        required_sections = [
            "ORIGINAL TASK",
            "JUDGE INFORMATION", 
            "JUDGE'S EVALUATION",
            "META-EVALUATION REQUEST"
        ]
        
        for section in required_sections:
            assert section in prompt, f"Missing section {section} in {judge_name} prompt"
        
        # Meta-evaluation dimensions validation
        required_dimensions = [
            "Accuracy", "Consistency", "Completeness",
            "Reasoning Quality", "Bias Detection", "Score Appropriateness"
        ]
        
        for dimension in required_dimensions:
            assert dimension in prompt, f"Missing dimension {dimension} in {judge_name} prompt"

def test_judge_specific_criteria_coverage():
    """Test coverage of judge-specific evaluation criteria"""
    generator = MetaEvaluationPromptGenerator()
    
    # Test Arena-Hard specific criteria
    arena_criteria = generator.get_meta_evaluation_criteria("arena_hard")
    arena_specific = ["difficulty_calibration", "comparative_ranking", "competitive_assessment"]
    for criteria in arena_specific:
        assert criteria in arena_criteria
    
    # Test Reward Model specific criteria  
    reward_criteria = generator.get_meta_evaluation_criteria("reward_model")
    reward_specific = ["reward_alignment", "preference_consistency", "value_alignment"]
    for criteria in reward_specific:
        assert criteria in reward_criteria
    
    # Test Prometheus-2 specific criteria
    prometheus_criteria = generator.get_meta_evaluation_criteria("prometheus_2")
    prometheus_specific = ["rubric_adherence", "score_justification", "criterion_coverage"]
    for criteria in prometheus_specific:
        assert criteria in prometheus_criteria
    
    # Test base criteria are included in all
    base_criteria = ["accuracy_assessment", "consistency_check", "bias_detection", "reasoning_quality", "score_appropriateness"]
    for judge_type in ["arena_hard", "reward_model", "prometheus_2"]:
        criteria = generator.get_meta_evaluation_criteria(judge_type)
        for base in base_criteria:
            assert base in criteria, f"Missing base criteria {base} in {judge_type}"
```

### Test 10: Validation and Error Handling

```python
def test_comprehensive_error_handling(tmp_path):
    """Test comprehensive error handling and recovery mechanisms"""
    
    # Test 1: Empty file handling
    empty_file = tmp_path / "empty.jsonl"
    empty_file.write_text("")
    
    converter = JudgeBenchConverter()
    file_info = JudgeFileInfo(
        judge_name="arena_hard", 
        judge_model="gpt-4",
        response_model="claude-3",
        file_path=str(empty_file),
        file_size_mb=0.0
    )
    
    prompts = converter.process_judge_output_file(str(empty_file), file_info, {})
    assert len(prompts) == 0
    
    # Test 2: Malformed JSON handling
    malformed_file = tmp_path / "malformed.jsonl" 
    with open(malformed_file, 'w') as f:
        f.write('{"valid": "json"}\n')
        f.write('{"malformed": json without quotes}\n')  # Invalid JSON
        f.write('{"another": "valid"}\n')
        f.write('completely invalid line\n')  # Invalid line
        f.write('{"final": "valid"}\n')
    
    file_info.file_path = str(malformed_file)
    prompts = converter.process_judge_output_file(str(malformed_file), file_info, {})
    assert len(prompts) == 3  # Should recover and process valid lines
    
    # Test 3: Missing required fields
    missing_fields_file = tmp_path / "missing_fields.jsonl"
    with open(missing_fields_file, 'w') as f:
        # Missing judge_response field
        incomplete_evaluation = MOCK_ARENA_HARD_EVALUATION.copy()
        del incomplete_evaluation['judge_response']
        f.write(json.dumps(incomplete_evaluation) + '\n')
        
        # Complete evaluation
        f.write(json.dumps(MOCK_ARENA_HARD_EVALUATION) + '\n')
    
    file_info.file_path = str(missing_fields_file)
    prompts = converter.process_judge_output_file(str(missing_fields_file), file_info, {})
    # Should handle missing fields gracefully
    assert len(prompts) >= 1  # At least the complete evaluation processed
    
    # Test 4: File permission errors
    with pytest.raises(Exception):
        converter.process_judge_output_file("/nonexistent/path/file.jsonl", file_info, {})

def test_validation_framework_integration():
    """Test integration with validation framework (Issue #120 dependency)"""
    from app.core.validation import sanitize_string, validate_json_data
    
    # Test input sanitization
    malicious_input = "<script>alert('xss')</script>Test content"
    sanitized = sanitize_string(malicious_input)
    assert "<script>" not in sanitized
    assert "alert" not in sanitized
    
    # Test JSON validation
    valid_json = {"test": "data", "score": 8.5}
    assert validate_json_data(valid_json) is True
    
    invalid_json = {"test": None}  # Assuming None values are invalid
    assert validate_json_data(invalid_json) is False
    
    # Test converter applies validation
    converter = JudgeBenchConverter()
    
    # Mock evaluation with potentially malicious content
    malicious_evaluation = MOCK_ARENA_HARD_EVALUATION.copy()
    malicious_evaluation['judge_response'] = "<script>alert('test')</script>Good response"
    
    file_info = JudgeFileInfo(
        judge_name="arena_hard",
        judge_model="gpt-4", 
        response_model="claude-3",
        file_path="test.jsonl",
        file_size_mb=1.0
    )
    
    # Should apply sanitization during processing
    prompt = converter.create_meta_evaluation_prompt(malicious_evaluation, file_info, {}, 1)
    assert "<script>" not in prompt.value
    assert "alert" not in prompt.value
```

## Test Execution Requirements

### Test Environment Setup

```python
# conftest.py additions for JudgeBench tests
@pytest.fixture
def mock_judge_files(tmp_path):
    """Create comprehensive mock judge files for testing"""
    files = {}
    
    # Arena-Hard file
    arena_file = tmp_path / "dataset=judgebench,response_model=claude-3,judge_name=arena_hard,judge_model=gpt-4.jsonl"
    with open(arena_file, 'w') as f:
        for i in range(10):
            evaluation = MOCK_ARENA_HARD_EVALUATION.copy()
            evaluation['id'] = f"arena_{i:06d}"
            f.write(json.dumps(evaluation) + '\n')
    files['arena_hard'] = arena_file
    
    # Reward Model file
    reward_file = tmp_path / "dataset=judgebench,response_model=gpt-4,judge_name=reward_model,judge_model=claude-opus.jsonl"
    with open(reward_file, 'w') as f:
        for i in range(10):
            evaluation = MOCK_REWARD_MODEL_EVALUATION.copy()
            evaluation['id'] = f"reward_{i:06d}"
            f.write(json.dumps(evaluation) + '\n')
    files['reward_model'] = reward_file
    
    # Prometheus-2 file
    prometheus_file = tmp_path / "dataset=judgebench,response_model=claude-2,judge_name=prometheus_2,judge_model=gpt-4-turbo.jsonl"
    with open(prometheus_file, 'w') as f:
        for i in range(10):
            evaluation = MOCK_PROMETHEUS_2_EVALUATION.copy()
            evaluation['id'] = f"prometheus_{i:06d}"
            f.write(json.dumps(evaluation) + '\n')
    files['prometheus_2'] = prometheus_file
    
    return files

@pytest.fixture
def judge_performance_analyzer():
    """Provide configured JudgePerformanceAnalyzer for testing"""
    return JudgePerformanceAnalyzer()

@pytest.fixture 
def meta_prompt_generator():
    """Provide configured MetaEvaluationPromptGenerator for testing"""
    return MetaEvaluationPromptGenerator()
```

### Test Execution Strategy

**RED Phase Tests**: All tests should initially fail, demonstrating proper TDD methodology
**GREEN Phase Tests**: Tests pass after minimal implementation
**REFACTOR Phase Tests**: Tests continue to pass after code quality improvements

### Coverage Requirements

- **Line Coverage**: 100% of all implementation code
- **Branch Coverage**: 100% of all conditional logic paths
- **Function Coverage**: 100% of all functions and methods
- **Integration Coverage**: All integration points tested

### Performance Benchmarks

- **Processing Speed**: Large files (7-12MB) processed within 5 minutes
- **Memory Usage**: Peak memory usage below 1GB during processing
- **Throughput**: Minimum 500 judge evaluations processed per minute
- **Error Recovery**: Graceful handling of up to 5% malformed entries

## Test Success Criteria

✅ **All Unit Tests Pass**: Individual component functionality validated  
✅ **All Integration Tests Pass**: End-to-end pipeline functionality validated  
✅ **All Performance Tests Pass**: Processing speed and memory requirements met  
✅ **All Quality Tests Pass**: Meta-evaluation prompt quality and coverage validated  
✅ **100% Test Coverage**: Complete code coverage across all components  
✅ **TDD Methodology**: Proper RED-GREEN-REFACTOR cycles demonstrated  

**Test Documentation Location**: `/tests/issue_130_tests.md`  
**Test Results Location**: `/docs/development/issue_130/testresults.md`  
**Implementation Validation**: All tests must pass before issue completion  

This comprehensive test specification ensures thorough validation of the JudgeBench Meta-Evaluation Converter implementation following strict TDD methodology with complete coverage of functionality, performance, and quality requirements.