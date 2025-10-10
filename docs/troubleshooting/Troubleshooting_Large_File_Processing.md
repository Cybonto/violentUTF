# Troubleshooting: Large File Processing Issues

## Overview

This guide addresses specific challenges when processing large datasets in ViolentUTF. Large file processing requires careful memory management, efficient I/O operations, and robust error handling. This guide covers optimization strategies, resource management, and troubleshooting techniques for datasets exceeding standard processing capabilities.

## Large File Processing Thresholds

### File Size Categories and Considerations

```yaml
File_Size_Categories:
  small_files:
    size_range: "< 10MB"
    processing_mode: "Standard in-memory processing"
    memory_requirements: "< 100MB RAM"
    processing_time: "< 30 seconds"

  medium_files:
    size_range: "10MB - 50MB"
    processing_mode: "Enhanced memory management"
    memory_requirements: "100MB - 500MB RAM"
    processing_time: "30 seconds - 5 minutes"

  large_files:
    size_range: "50MB - 500MB"
    processing_mode: "Streaming and chunked processing"
    memory_requirements: "500MB - 2GB RAM"
    processing_time: "5 - 30 minutes"

  very_large_files:
    size_range: "500MB - 5GB"
    processing_mode: "Advanced streaming with disk buffering"
    memory_requirements: "1GB - 4GB RAM"
    processing_time: "30 minutes - 2 hours"

  massive_files:
    size_range: "> 5GB"
    processing_mode: "Distributed processing or cloud-based"
    memory_requirements: "> 4GB RAM"
    processing_time: "> 2 hours"
```

## Common Large File Processing Issues

### Memory Exhaustion Problems

#### Issue: Out of Memory During Dataset Loading

**Symptoms:**
- `MemoryError` exceptions during dataset loading
- System becomes unresponsive or swaps excessively
- Process killed by system OOM (Out of Memory) killer
- Gradual memory consumption leading to system slowdown

**Diagnostic Steps:**
```bash
# Monitor memory usage during processing
python -m violentutf.utils.memory_monitor \
  --process-name "dataset_processor" \
  --interval 5 \
  --output memory_trace.log

# Check available system memory
free -h
cat /proc/meminfo | grep -E "MemTotal|MemAvailable|SwapTotal|SwapFree"

# Estimate dataset memory requirements
python -m violentutf.utils.dataset_analyzer \
  --file-path /path/to/large_dataset \
  --estimate-memory-usage
```

**Solutions:**

1. **Enable Automatic File Splitting**
   ```yaml
   # Configuration for automatic file splitting
   large_file_processing:
     enable_splitting: true
     max_chunk_size: "50MB"
     chunk_overlap: 100  # Records
     preserve_order: true
     cleanup_temporary_files: true
   ```

2. **Streaming Data Processing**
   ```python
   # Implement streaming data processing
   def process_large_dataset_streaming(file_path, chunk_size=1000):
       with open(file_path, 'r') as file:
           chunk = []
           for line_num, line in enumerate(file):
               chunk.append(process_line(line))

               if len(chunk) >= chunk_size:
                   yield process_chunk(chunk)
                   chunk = []

                   # Force garbage collection
                   import gc
                   gc.collect()

           # Process remaining data
           if chunk:
               yield process_chunk(chunk)
   ```

3. **Memory-Mapped File Access**
   ```python
   # Use memory-mapped files for large datasets
   import mmap

   def process_with_mmap(file_path):
       with open(file_path, 'rb') as file:
           with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
               # Process data without loading entire file into memory
               return process_mapped_data(mmapped_file)
   ```

#### Issue: Memory Leaks During Long Processing Sessions

**Symptoms:**
- Memory usage increases continuously during processing
- Performance degrades over time
- Eventually leads to memory exhaustion
- Python garbage collection not releasing memory

**Diagnostic Steps:**
```bash
# Profile memory usage over time
python -m violentutf.utils.memory_profiler \
  --target-function process_large_dataset \
  --duration 300 \
  --output memory_profile.txt

# Check for memory leaks
python -m violentutf.utils.leak_detector \
  --iterations 10 \
  --memory-threshold 100MB
```

**Solutions:**

1. **Explicit Memory Management**
   ```python
   # Implement explicit memory cleanup
   import gc
   import weakref

   def process_with_cleanup(data_chunk):
       try:
           result = process_data(data_chunk)
           return result
       finally:
           # Explicit cleanup
           del data_chunk
           gc.collect()

   # Use weak references to avoid circular references
   def create_weak_reference_processor():
       cache = weakref.WeakValueDictionary()
       return cache
   ```

2. **Batch Processing with Memory Bounds**
   ```python
   # Process in bounded batches
   def bounded_batch_processor(dataset, max_memory_mb=500):
       import psutil
       process = psutil.Process()

       batch = []
       for item in dataset:
           batch.append(item)

           # Check memory usage
           memory_mb = process.memory_info().rss / 1024 / 1024
           if memory_mb > max_memory_mb:
               # Process current batch and clear memory
               yield process_batch(batch)
               batch = []
               gc.collect()

       # Process remaining items
       if batch:
           yield process_batch(batch)
   ```

### Disk I/O and Storage Issues

#### Issue: Slow File Reading Performance

**Symptoms:**
- Very slow dataset loading times
- High disk I/O wait times
- System appears to hang during file operations
- Inconsistent processing speeds

**Diagnostic Steps:**
```bash
# Monitor I/O performance
iostat -x 1 10  # Monitor for 10 seconds

# Check file system performance
hdparm -tT /dev/sda  # Test disk read performance

# Analyze file access patterns
python -m violentutf.utils.io_profiler \
  --file-path /path/to/large_dataset \
  --access-pattern sequential
```

**Solutions:**

1. **Optimized File Reading**
   ```python
   # Use buffered reading for better performance
   def optimized_file_reader(file_path, buffer_size=8192):
       with open(file_path, 'r', buffering=buffer_size) as file:
           while True:
               chunk = file.read(buffer_size)
               if not chunk:
                   break
               yield chunk

   # Use appropriate read methods for file type
   def read_large_json(file_path):
       import ijson  # Streaming JSON parser
       with open(file_path, 'rb') as file:
           parser = ijson.parse(file)
           for prefix, event, value in parser:
               yield prefix, event, value
   ```

2. **Parallel File Processing**
   ```python
   # Parallel file reading with threading
   import threading
   from queue import Queue

   def parallel_file_processor(file_path, num_threads=4):
       def worker():
           while True:
               chunk = queue.get()
               if chunk is None:
                   break
               process_chunk(chunk)
               queue.task_done()

       queue = Queue()
       threads = []

       # Start worker threads
       for i in range(num_threads):
           t = threading.Thread(target=worker)
           t.start()
           threads.append(t)

       # Feed data to workers
       for chunk in read_file_chunks(file_path):
           queue.put(chunk)

       # Wait for completion
       queue.join()

       # Stop workers
       for i in range(num_threads):
           queue.put(None)
       for t in threads:
           t.join()
   ```

#### Issue: Insufficient Disk Space for Temporary Files

**Symptoms:**
- "No space left on device" errors
- Processing fails during file splitting operations
- Temporary files accumulate and fill disk
- System performance degrades due to low disk space

**Diagnostic Steps:**
```bash
# Check disk space usage
df -h
du -sh /tmp /var/tmp ~/.cache

# Monitor disk usage during processing
watch -n 5 'df -h | grep -E "(Filesystem|/dev/)"'

# Find large temporary files
find /tmp -type f -size +100M -exec ls -lh {} \;
```

**Solutions:**

1. **Temporary File Management**
   ```python
   # Proper temporary file handling
   import tempfile
   import os

   def process_with_temp_files(dataset_path):
       with tempfile.TemporaryDirectory(prefix="violentutf_") as temp_dir:
           # Process with automatic cleanup
           temp_file = os.path.join(temp_dir, "temp_data.tmp")

           try:
               # Processing operations
               result = process_dataset(dataset_path, temp_file)
               return result
           finally:
               # Temporary directory automatically cleaned up
               pass
   ```

2. **Disk Space Monitoring**
   ```python
   # Monitor disk space during processing
   def check_disk_space(path="/tmp", min_free_gb=1):
       import shutil
       free_bytes = shutil.disk_usage(path).free
       free_gb = free_bytes / (1024**3)

       if free_gb < min_free_gb:
           raise RuntimeError(f"Insufficient disk space: {free_gb:.2f}GB free")

       return free_gb

   def process_with_space_monitoring(dataset):
       for chunk in dataset:
           check_disk_space()  # Check before processing each chunk
           yield process_chunk(chunk)
   ```

3. **Alternative Storage Locations**
   ```yaml
   # Configure alternative temporary storage
   storage_config:
     temp_directory: "/path/to/large_storage/temp"
     cache_directory: "/path/to/fast_storage/cache"
     max_temp_size: "10GB"
     cleanup_interval: 3600  # seconds
   ```

### Processing Timeout and Performance Issues

#### Issue: Processing Timeouts with Large Datasets

**Symptoms:**
- Operations timeout before completion
- "TimeoutError" exceptions
- Processing appears to hang indefinitely
- Inconsistent completion times

**Diagnostic Steps:**
```bash
# Monitor processing progress
python -m violentutf.utils.progress_monitor \
  --dataset-size 1000000 \
  --update-interval 10 \
  --estimate-completion

# Profile processing bottlenecks
python -m cProfile -o profile_output.prof \
  -m violentutf.processors.dataset_processor \
  --dataset-path /path/to/large_dataset
```

**Solutions:**

1. **Adaptive Timeout Configuration**
   ```python
   # Calculate timeout based on dataset size
   def calculate_timeout(dataset_size_mb, base_timeout=300):
       # Base timeout + additional time per MB
       additional_time = dataset_size_mb * 2  # 2 seconds per MB
       total_timeout = base_timeout + additional_time
       return min(total_timeout, 3600)  # Cap at 1 hour

   # Use adaptive timeout
   dataset_size = get_dataset_size_mb(dataset_path)
   timeout = calculate_timeout(dataset_size)
   ```

2. **Progress Monitoring and Checkpointing**
   ```python
   # Implement checkpointing for long operations
   def process_with_checkpoints(dataset, checkpoint_interval=1000):
       checkpoint_file = "processing_checkpoint.json"

       # Load previous checkpoint if exists
       start_index = load_checkpoint(checkpoint_file)

       for i, item in enumerate(dataset[start_index:], start_index):
           result = process_item(item)

           # Save checkpoint periodically
           if i % checkpoint_interval == 0:
               save_checkpoint(checkpoint_file, i)

           yield result

       # Remove checkpoint file when complete
       if os.path.exists(checkpoint_file):
           os.remove(checkpoint_file)
   ```

3. **Asynchronous Processing**
   ```python
   # Use asyncio for non-blocking processing
   import asyncio
   import aiofiles

   async def async_dataset_processor(dataset_path):
       async with aiofiles.open(dataset_path, 'r') as file:
           async for line in file:
               # Non-blocking processing
               result = await process_line_async(line)
               yield result

   # Run with timeout
   async def process_with_timeout(dataset_path, timeout=3600):
       try:
           async for result in async_dataset_processor(dataset_path):
               yield result
       except asyncio.TimeoutError:
           print(f"Processing timed out after {timeout} seconds")
           raise
   ```

## Optimization Strategies for Large Files

### File Splitting and Chunking

#### Automatic File Splitting Configuration

```yaml
# Comprehensive file splitting configuration
file_splitting_config:
  enabled: true
  strategies:
    size_based:
      max_chunk_size: "50MB"
      size_calculation: "uncompressed"

    record_based:
      max_records_per_chunk: 10000
      preserve_record_boundaries: true

    memory_based:
      max_memory_usage: "500MB"
      dynamic_adjustment: true

  overlap_handling:
    overlap_records: 100
    overlap_strategy: "duplicate"  # or "reference"

  output_management:
    temporary_directory: "/tmp/violentutf_chunks"
    cleanup_policy: "automatic"
    compression: "gzip"  # optional

  error_handling:
    continue_on_chunk_error: true
    max_retries: 3
    fallback_chunk_size: "25MB"
```

#### Custom File Splitter Implementation

```python
class LargeFileProcessor:
    def __init__(self, max_chunk_size_mb=50, overlap_records=100):
        self.max_chunk_size = max_chunk_size_mb * 1024 * 1024  # Convert to bytes
        self.overlap_records = overlap_records

    def split_file(self, file_path):
        """Split large file into manageable chunks"""
        import os
        import tempfile

        file_size = os.path.getsize(file_path)
        if file_size <= self.max_chunk_size:
            yield file_path  # File is small enough
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            chunk_num = 0
            current_chunk_size = 0
            current_chunk_records = []
            overlap_buffer = []

            with open(file_path, 'r') as input_file:
                for line_num, line in enumerate(input_file):
                    current_chunk_records.append(line)
                    current_chunk_size += len(line.encode('utf-8'))

                    # Check if chunk is large enough
                    if current_chunk_size >= self.max_chunk_size:
                        # Write chunk file
                        chunk_file = os.path.join(temp_dir, f"chunk_{chunk_num}.txt")
                        self._write_chunk(chunk_file, overlap_buffer + current_chunk_records)
                        yield chunk_file

                        # Prepare overlap for next chunk
                        overlap_buffer = current_chunk_records[-self.overlap_records:]
                        current_chunk_records = []
                        current_chunk_size = 0
                        chunk_num += 1

                # Write final chunk
                if current_chunk_records:
                    chunk_file = os.path.join(temp_dir, f"chunk_{chunk_num}.txt")
                    self._write_chunk(chunk_file, overlap_buffer + current_chunk_records)
                    yield chunk_file

    def _write_chunk(self, chunk_file, records):
        """Write records to chunk file"""
        with open(chunk_file, 'w') as f:
            f.writelines(records)
```

### Memory-Efficient Processing Patterns

#### Streaming Data Processing

```python
class StreamingDatasetProcessor:
    def __init__(self, memory_limit_mb=500):
        self.memory_limit = memory_limit_mb * 1024 * 1024

    def process_streaming(self, dataset_path):
        """Process dataset using streaming approach"""
        import psutil
        process = psutil.Process()

        with open(dataset_path, 'r') as file:
            batch = []
            batch_size = 0

            for line in file:
                record = self.parse_line(line)
                batch.append(record)
                batch_size += len(line.encode('utf-8'))

                # Check memory usage
                memory_usage = process.memory_info().rss

                if memory_usage > self.memory_limit or batch_size > self.memory_limit:
                    # Process current batch
                    yield from self.process_batch(batch)

                    # Clear batch and force garbage collection
                    batch = []
                    batch_size = 0
                    import gc
                    gc.collect()

            # Process remaining records
            if batch:
                yield from self.process_batch(batch)

    def parse_line(self, line):
        """Parse a single line of data"""
        import json
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return {"raw_line": line.strip()}

    def process_batch(self, batch):
        """Process a batch of records"""
        for record in batch:
            # Apply transformations
            processed_record = self.transform_record(record)
            yield processed_record

    def transform_record(self, record):
        """Transform individual record"""
        # Implement specific transformations
        return record
```

#### Generator-Based Processing

```python
def memory_efficient_dataset_loader(file_path, chunk_size=1000):
    """Memory-efficient dataset loading using generators"""

    def read_chunks():
        with open(file_path, 'r') as file:
            chunk = []
            for line in file:
                chunk.append(line.strip())
                if len(chunk) >= chunk_size:
                    yield chunk
                    chunk = []
            if chunk:
                yield chunk

    def process_chunk(chunk):
        for line in chunk:
            yield process_line(line)

    # Chain generators for memory efficiency
    for chunk in read_chunks():
        yield from process_chunk(chunk)

        # Optional: Force garbage collection between chunks
        import gc
        gc.collect()

def process_line(line):
    """Process individual line"""
    import json
    try:
        data = json.loads(line)
        # Apply processing logic
        return transform_data(data)
    except (json.JSONDecodeError, KeyError) as e:
        return {"error": str(e), "raw_line": line}

def transform_data(data):
    """Transform data record"""
    # Implement data transformation logic
    return data
```

### Performance Monitoring and Optimization

#### Real-Time Performance Monitoring

```python
class PerformanceMonitor:
    def __init__(self, update_interval=10):
        self.update_interval = update_interval
        self.start_time = None
        self.processed_count = 0
        self.last_update = 0

    def start_monitoring(self):
        import time
        self.start_time = time.time()
        self.last_update = self.start_time

    def update_progress(self, items_processed=1):
        import time
        self.processed_count += items_processed
        current_time = time.time()

        if current_time - self.last_update >= self.update_interval:
            self._report_progress(current_time)
            self.last_update = current_time

    def _report_progress(self, current_time):
        elapsed_time = current_time - self.start_time
        processing_rate = self.processed_count / elapsed_time if elapsed_time > 0 else 0

        print(f"Processed: {self.processed_count} items")
        print(f"Elapsed: {elapsed_time:.2f} seconds")
        print(f"Rate: {processing_rate:.2f} items/second")

        # Memory usage
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        print(f"Memory usage: {memory_mb:.2f} MB")
        print("-" * 40)

# Usage example
def process_large_dataset_with_monitoring(dataset_path):
    monitor = PerformanceMonitor(update_interval=30)  # Update every 30 seconds
    monitor.start_monitoring()

    for item in memory_efficient_dataset_loader(dataset_path):
        result = process_item(item)
        monitor.update_progress()
        yield result
```

## Emergency Recovery Procedures

### Data Recovery from Failed Processing

```python
def recover_from_failed_processing(checkpoint_dir, output_file):
    """Recover data from failed large file processing"""
    import os
    import json

    recovered_data = []
    checkpoint_files = sorted([f for f in os.listdir(checkpoint_dir) if f.startswith('checkpoint_')])

    for checkpoint_file in checkpoint_files:
        checkpoint_path = os.path.join(checkpoint_dir, checkpoint_file)
        try:
            with open(checkpoint_path, 'r') as f:
                data = json.load(f)
                recovered_data.extend(data.get('processed_items', []))
                print(f"Recovered {len(data.get('processed_items', []))} items from {checkpoint_file}")
        except Exception as e:
            print(f"Failed to recover from {checkpoint_file}: {e}")

    # Save recovered data
    with open(output_file, 'w') as f:
        json.dump(recovered_data, f, indent=2)

    print(f"Total recovered items: {len(recovered_data)}")
    return recovered_data
```

### Cleanup Procedures for Large File Processing

```bash
#!/bin/bash
# cleanup_large_file_processing.sh

echo "Starting cleanup of large file processing artifacts..."

# Clean temporary directories
echo "Cleaning temporary directories..."
rm -rf /tmp/violentutf_chunks_*
rm -rf /tmp/violentutf_temp_*
find /tmp -name "violentutf_*" -type d -mtime +1 -exec rm -rf {} \; 2>/dev/null

# Clean checkpoint files older than 24 hours
echo "Cleaning old checkpoint files..."
find . -name "*checkpoint*.json" -mtime +1 -delete
find . -name "*checkpoint*.tmp" -mtime +1 -delete

# Clean cached data
echo "Cleaning cached data..."
rm -rf app_data/violentutf/cache/large_file_*
rm -rf ~/.cache/violentutf/large_datasets/*

# Clean memory-mapped files
echo "Cleaning memory-mapped files..."
find /dev/shm -name "violentutf_*" -delete 2>/dev/null || true

# Report disk space recovered
echo "Cleanup complete. Current disk usage:"
df -h | grep -E "(Filesystem|/dev/|/tmp)"
```

## Best Practices for Large File Processing

### Configuration Recommendations

```yaml
# Optimal configuration for different system specifications
large_file_configurations:
  low_memory_system:
    max_memory_usage: "512MB"
    chunk_size: "10MB"
    parallel_processing: false
    streaming_mode: true

  medium_memory_system:
    max_memory_usage: "2GB"
    chunk_size: "50MB"
    parallel_processing: true
    max_workers: 2

  high_memory_system:
    max_memory_usage: "8GB"
    chunk_size: "200MB"
    parallel_processing: true
    max_workers: 4

  very_high_memory_system:
    max_memory_usage: "16GB"
    chunk_size: "500MB"
    parallel_processing: true
    max_workers: 8
```

### Monitoring and Alerting

```python
# Set up monitoring for large file processing
def setup_large_file_monitoring():
    import logging
    import psutil

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('large_file_processing.log'),
            logging.StreamHandler()
        ]
    )

    # Set up memory monitoring
    def memory_warning_threshold():
        memory = psutil.virtual_memory()
        if memory.percent > 85:
            logging.warning(f"High memory usage: {memory.percent}%")
        if memory.available < 512 * 1024 * 1024:  # Less than 512MB available
            logging.critical(f"Low memory available: {memory.available / 1024 / 1024:.2f}MB")

    # Set up disk space monitoring
    def disk_space_warning():
        disk = psutil.disk_usage('/')
        if disk.percent > 85:
            logging.warning(f"High disk usage: {disk.percent}%")
        if disk.free < 1024 * 1024 * 1024:  # Less than 1GB free
            logging.critical(f"Low disk space: {disk.free / 1024 / 1024 / 1024:.2f}GB")

    return memory_warning_threshold, disk_space_warning
```

Remember: Large file processing requires patience and proper resource management. Always test with smaller subsets first, monitor system resources continuously, and implement proper error handling and recovery mechanisms.
