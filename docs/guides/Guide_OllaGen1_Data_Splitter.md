# OllaGen1 Data Splitter - User Guide

**Version:** 1.0
**Last Updated:** September 2025
**Issue Reference:** #122 - OllaGen1 Data Splitter for GitHub Compatibility

## 📋 Overview

The OllaGen1 Data Splitter is a specialized utility that enables you to split large OllaGen1 cognitive assessment datasets into GitHub-compatible chunks while preserving data integrity and scenario relationships. This tool is essential for managing the 25MB OllaGen1-QA-full.csv file that contains 169,999 cognitive behavioral security assessment scenarios.

### Key Features

- **GitHub Compatibility**: Splits large files into ~10MB chunks suitable for GitHub repositories
- **Scenario Integrity**: Maintains the relationship between cognitive assessment scenarios and their 4 Q&A pairs
- **Data Preservation**: Zero data loss with SHA-256 checksum validation
- **Complete Reconstruction**: Merge capability to restore original file from split parts
- **Performance Optimized**: Memory-efficient processing for large datasets
- **Comprehensive Validation**: Multi-level validation of schema, data integrity, and performance

## 🎯 When to Use This Tool

### Primary Use Cases

1. **GitHub Repository Management**: When you need to store large OllaGen1 datasets in version control
2. **Data Distribution**: When sharing cognitive assessment datasets across teams or systems
3. **Storage Optimization**: When you need to manage disk space efficiently
4. **Data Backup**: When creating distributed backups of critical assessment data
5. **CI/CD Pipeline Integration**: When automated systems need to process large datasets in smaller chunks

### File Compatibility

- **Supported Format**: CSV files with OllaGen1 22-column schema
- **Expected Schema**: 169,999+ scenarios with cognitive behavioral assessment data
- **File Size**: Optimized for files 25MB+ that exceed GitHub's file size limits

## 🚀 Getting Started

### Prerequisites

- ViolentUTF FastAPI backend running
- OllaGen1-QA-full.csv file with valid 22-column schema
- Sufficient disk space (recommended: 2x file size for split operation)
- Python environment with required dependencies

### Quick Start Example

```python
from violentutf_api.fastapi_app.app.core.splitters import OllaGen1Splitter

# Initialize splitter
splitter = OllaGen1Splitter("path/to/OllaGen1-QA-full.csv")

# Optional: Set progress tracking
def progress_callback(current, total, message):
    print(f"Progress: {current}/{total} - {message}")

splitter.set_progress_callback(progress_callback)

# Perform split operation
manifest = splitter.split()

print(f"Split complete! Created {manifest['total_parts']} parts")
```

## 📊 Understanding OllaGen1 Data Structure

### Cognitive Framework Components

The OllaGen1 dataset contains cognitive behavioral security assessment data with these key elements:

#### Column Schema (22 columns)
```
ID, P1_name, P1_cogpath, P1_profile, P1_risk_score,
P2_name, P2_cogpath, P2_profile, P2_risk_score,
combined_risk_score, WCP_Question, WCP_Answer,
WHO_Question, WHO_Answer, TeamRisk_Question, TeamRisk_Answer,
TargetFactor_Question, TargetFactor_Answer, scenario_metadata,
behavioral_construct, cognitive_assessment, validation_flags
```

#### Question Types (4 per scenario)
- **WCP**: Work Context Problems
- **WHO**: Who-based scenarios
- **TeamRisk**: Team risk assessments
- **TargetFactor**: Target factor analysis

#### Data Relationships
- **169,999 scenarios** total
- **4 Q&A pairs** per scenario = **679,996 total Q&A pairs**
- **2 person profiles** (P1 and P2) per scenario
- **Behavioral constructs** for security compliance evaluation

## 🔧 Detailed Usage Instructions

### Step 1: File Validation

Before splitting, the tool automatically validates your file:

```python
# Automatic validation during initialization
splitter = OllaGen1Splitter("your_file.csv")

# Manual schema validation
is_valid = splitter.validate_schema()
print(f"Schema valid: {is_valid}")

# Detailed file analysis
analysis = splitter.analyze_file_structure()
print(f"Scenarios: {analysis['total_scenarios']}")
print(f"Q&A pairs: {analysis['total_qa_pairs']}")
```

### Step 2: Configure Split Parameters

```python
# Default: 10MB chunks for GitHub compatibility
splitter = OllaGen1Splitter("file.csv", chunk_size=10*1024*1024)

# Custom chunk size (e.g., 5MB chunks)
splitter = OllaGen1Splitter("file.csv", chunk_size=5*1024*1024)
```

### Step 3: Execute Split Operation

```python
# Basic split
manifest = splitter.split()

# Split with progress tracking
def track_progress(current, total, message):
    percentage = (current / total) * 100
    print(f"[{percentage:.1f}%] {message}")

splitter.set_progress_callback(track_progress)
manifest = splitter.split()
```

### Step 4: Verify Split Results

The split operation generates:

1. **Split Part Files**: `OllaGen1-QA-full.part01.csv`, `OllaGen1-QA-full.part02.csv`, etc.
2. **Manifest File**: `OllaGen1-QA-full.manifest.json` with complete reconstruction metadata

```python
# Check split results
print(f"Created {manifest['total_parts']} parts")
print(f"Total scenarios preserved: {manifest['total_scenarios']}")
print(f"File integrity: {manifest['checksum']}")

# Validate manifest structure
from violentutf_api.fastapi_app.app.core.splitters import OllaGen1Manifest
is_valid = OllaGen1Manifest.validate(manifest)
print(f"Manifest valid: {is_valid}")
```

## 🔄 File Reconstruction

### Using OllaGen1Merger

To reconstruct the original file from split parts:

```python
from violentutf_api.fastapi_app.app.core.splitters import OllaGen1Merger

# Initialize merger with manifest
merger = OllaGen1Merger("OllaGen1-QA-full.manifest.json")

# Verify integrity before merging
if merger.verify_integrity():
    # Reconstruct original file
    output_path = merger.merge("reconstructed_file.csv")
    print(f"File reconstructed: {output_path}")
else:
    print("Integrity verification failed!")
```

### Automatic Validation

The merger automatically performs:
- ✅ **Part file existence** verification
- ✅ **Checksum validation** for each part
- ✅ **File size verification**
- ✅ **Scenario count validation**
- ✅ **Final file integrity** check

## 📈 Performance Optimization

### Memory Efficiency

The splitter uses streaming processing to handle large files efficiently:

```python
# Memory usage is optimized automatically
# Peak memory usage: ~100MB for 25MB file processing
# Processing time: <5 minutes for full OllaGen1 dataset
```

### Disk Space Planning

Plan disk space requirements:
```
Original file:     25MB
Split parts:      ~25MB (same total size)
Manifest file:    ~5KB
Overhead:         ~2-3MB (temporary files)
Total required:   ~52-53MB
```

### Performance Monitoring

```python
# Analyze performance before splitting
from violentutf_api.fastapi_app.app.utils.csv_utils import estimate_split_performance

performance = estimate_split_performance("file.csv", chunk_size=10*1024*1024)
print(f"Estimated parts: {performance['estimated_parts']}")
print(f"Estimated time: {performance['estimated_time_seconds']}s")
print(f"Memory usage: {performance['estimated_memory_mb']}MB")
```

## 🛡️ Data Integrity & Security

### Validation Layers

The tool provides multiple validation layers:

1. **Schema Validation**: Ensures 22-column OllaGen1 structure
2. **Data Integrity**: SHA-256 checksums for each part
3. **Scenario Preservation**: Validates Q&A pair relationships
4. **Reconstruction Verification**: Confirms identical file restoration

### Security Features

- **Input Sanitization**: All file inputs are validated and sanitized
- **Path Validation**: Prevents directory traversal attacks
- **Memory Bounds**: Prevents memory exhaustion attacks
- **Error Handling**: Comprehensive error messages without sensitive data exposure

### Checksum Verification

```python
# Manual checksum verification
from violentutf_api.fastapi_app.app.utils.file_utils import calculate_checksum

original_checksum = calculate_checksum("original_file.csv")
reconstructed_checksum = calculate_checksum("reconstructed_file.csv")

print(f"Checksums match: {original_checksum == reconstructed_checksum}")
```

## 🚨 Troubleshooting

### Common Issues and Solutions

#### 1. Schema Validation Errors

**Error**: `Invalid OllaGen1 schema. Expected 22 columns, got X`

**Solution**: Verify your CSV file has the correct OllaGen1 structure:
```python
# Check file structure
from violentutf_api.fastapi_app.app.utils.csv_utils import validate_csv_integrity

validation = validate_csv_integrity("your_file.csv")
print(f"Validation result: {validation}")

if not validation['is_valid']:
    print("Errors found:", validation['errors'])
```

#### 2. Insufficient Disk Space

**Error**: `Insufficient disk space for split operation`

**Solution**:
```bash
# Check available space
df -h .

# Clean up temporary files
rm -f *.part*.csv
rm -f *.manifest.json
```

#### 3. Memory Issues

**Error**: `Memory error during processing`

**Solution**: Use smaller chunk sizes:
```python
# Reduce chunk size for memory-constrained environments
splitter = OllaGen1Splitter("file.csv", chunk_size=5*1024*1024)  # 5MB chunks
```

#### 4. Reconstruction Failures

**Error**: `Integrity verification failed for split parts`

**Solution**:
```python
# Check individual part integrity
merger = OllaGen1Merger("manifest.json")
integrity_ok = merger.verify_integrity()

if not integrity_ok:
    # Re-split the original file
    splitter = OllaGen1Splitter("original_file.csv")
    new_manifest = splitter.split()
```

### Diagnostic Commands

```python
# File structure analysis
analyzer = OllaGen1CSVAnalyzer("file.csv")
column_types = analyzer.infer_column_types()
print("Column types:", column_types)

# Performance estimation
performance = estimate_split_performance("file.csv", 10*1024*1024)
print("Performance estimate:", performance)

# Cognitive framework analysis
splitter = OllaGen1Splitter("file.csv")
framework = splitter.analyze_cognitive_framework()
print("Cognitive framework:", framework)
```

## 🔗 Integration with ViolentUTF

### API Integration

The OllaGen1 splitter integrates with ViolentUTF's dataset management system:

```python
# Integration with dataset registry
from violentutf_api.fastapi_app.app.api.endpoints.datasets import VIOLENTUTF_NATIVE_DATASETS

# OllaGen1 is registered as a native dataset type
ollegen1_config = VIOLENTUTF_NATIVE_DATASETS["ollegen1_cognitive"]
print("Dataset info:", ollegen1_config)
```

### Streamlit UI Integration

The splitter can be used within ViolentUTF's dataset configuration interface:

1. Navigate to **Configure Datasets** page
2. Select **Native Datasets** source
3. Choose **OllaGen1 Cognitive Behavioral Security Assessment**
4. Configure split parameters if needed
5. Process dataset with automatic splitting for large files

### FastAPI Endpoints

Access splitter functionality via REST API:

```bash
# Get OllaGen1 dataset information
curl -X GET "http://localhost:9080/api/v1/datasets/types" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Process OllaGen1 dataset
curl -X POST "http://localhost:9080/api/v1/datasets" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "native",
    "dataset_type": "ollegen1_cognitive",
    "config": {"question_types": ["WCP", "WHO", "TeamRisk", "TargetFactor"]}
  }'
```

## 📚 Advanced Configuration

### Custom Progress Tracking

```python
class AdvancedProgressTracker:
    def __init__(self):
        self.start_time = None
        self.last_update = None

    def __call__(self, current, total, message):
        import time
        now = time.time()

        if self.start_time is None:
            self.start_time = now

        elapsed = now - self.start_time
        if current > 0:
            eta = (elapsed / current) * (total - current)
            print(f"[{current}/{total}] {message} - ETA: {eta:.1f}s")
        else:
            print(f"[{current}/{total}] {message}")

# Use advanced tracker
tracker = AdvancedProgressTracker()
splitter.set_progress_callback(tracker)
```

### Batch Processing

```python
import glob
from pathlib import Path

def batch_split_ollegen1_files(directory_path, output_base):
    """Split multiple OllaGen1 files in batch."""
    csv_files = glob.glob(f"{directory_path}/*.csv")

    for csv_file in csv_files:
        print(f"Processing: {csv_file}")

        try:
            # Create output directory
            file_name = Path(csv_file).stem
            output_dir = Path(output_base) / file_name
            output_dir.mkdir(parents=True, exist_ok=True)

            # Initialize splitter
            splitter = OllaGen1Splitter(csv_file)

            # Split file
            manifest = splitter.split()

            print(f"✅ Split complete: {manifest['total_parts']} parts")

        except Exception as e:
            print(f"❌ Error processing {csv_file}: {e}")

# Example usage
batch_split_ollegen1_files("/path/to/csv/files", "/path/to/output")
```

## ⚡ Best Practices

### 1. File Management
- Always keep the original file as a backup
- Store manifest files with their corresponding split parts
- Use descriptive file naming conventions
- Organize split files in dedicated directories

### 2. Performance Optimization
- Use SSDs for faster I/O operations
- Process files during off-peak hours for large datasets
- Monitor memory usage during processing
- Use appropriate chunk sizes for your storage constraints

### 3. Data Validation
- Always verify checksums after splitting
- Test reconstruction process before deploying split files
- Validate cognitive framework metadata preservation
- Run integrity checks on reconstructed files

### 4. Security
- Validate file sources before processing
- Use secure file paths and permissions
- Implement proper access controls for sensitive datasets
- Log all split/merge operations for audit trails

## 🆘 Support and Resources

### Documentation Links
- **API Reference**: `/docs/api/README.md`
- **Dataset Configuration**: `/docs/violentUTF_programSteps/3_ConfigureDatasets.md`
- **MCP Integration**: `/docs/mcp/violentutf_mcp_dev.md`

### Troubleshooting Resources
- **GitHub Issues**: Report bugs and feature requests
- **Test Suite**: Run `pytest tests/test_ollegen1_splitter.py` for validation
- **Log Analysis**: Check ViolentUTF logs for detailed error information

### Performance Benchmarks
- **25MB File**: ~3-5 minutes processing time
- **Memory Usage**: <100MB peak usage
- **Chunk Size**: 10MB optimal for GitHub compatibility
- **Validation**: <1 minute for full integrity check

---

**⚠️ Important Notes:**
- This tool is designed specifically for OllaGen1 cognitive assessment datasets
- Always verify data integrity after split/merge operations
- Ensure sufficient disk space before starting large split operations
- Use appropriate error handling in production environments

**🔒 Security Notice:** This tool processes cognitive behavioral security assessment data. Ensure proper data handling policies and access controls are in place according to your organization's security requirements.
