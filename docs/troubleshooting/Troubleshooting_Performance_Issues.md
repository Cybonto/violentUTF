# Troubleshooting: Performance Issues

## Overview

This guide addresses performance optimization and troubleshooting for ViolentUTF's dataset integration system. Performance issues can manifest as slow processing times, high resource usage, system unresponsiveness, or inefficient resource utilization. This guide provides systematic approaches to identify, diagnose, and resolve performance bottlenecks.

## Performance Baseline and Expectations

### Expected Performance Benchmarks

```yaml
Performance_Benchmarks:
  small_datasets:
    size_range: "< 10MB, < 5000 records"
    expected_processing_time: "< 30 seconds"
    memory_usage: "< 200MB"
    cpu_utilization: "< 50%"

  medium_datasets:
    size_range: "10-50MB, 5000-25000 records"
    expected_processing_time: "30 seconds - 5 minutes"
    memory_usage: "200MB - 1GB"
    cpu_utilization: "50-80%"

  large_datasets:
    size_range: "50-500MB, 25000-100000 records"
    expected_processing_time: "5-30 minutes"
    memory_usage: "1-4GB"
    cpu_utilization: "70-90%"

  very_large_datasets:
    size_range: "> 500MB, > 100000 records"
    expected_processing_time: "> 30 minutes"
    memory_usage: "> 4GB"
    cpu_utilization: "80-95%"
```

### System Requirements by Dataset Type

```yaml
Dataset_Performance_Requirements:
  OllaGen1:
    minimum_ram: "4GB"
    recommended_ram: "8GB"
    cpu_cores: "2+"
    storage_space: "2GB"

  Garak:
    minimum_ram: "8GB"
    recommended_ram: "16GB"
    cpu_cores: "4+"
    storage_space: "5GB"

  LegalBench:
    minimum_ram: "6GB"
    recommended_ram: "12GB"
    cpu_cores: "2+"
    storage_space: "3GB"

  DocMath:
    minimum_ram: "6GB"
    recommended_ram: "12GB"
    cpu_cores: "2+"
    storage_space: "4GB"

  GraphWalk:
    minimum_ram: "4GB"
    recommended_ram: "8GB"
    cpu_cores: "2+"
    storage_space: "2GB"

  ConfAIde:
    minimum_ram: "5GB"
    recommended_ram: "10GB"
    cpu_cores: "2+"
    storage_space: "3GB"

  JudgeBench:
    minimum_ram: "7GB"
    recommended_ram: "14GB"
    cpu_cores: "4+"
    storage_space: "4GB"
```

## Performance Monitoring and Diagnostics

### System Resource Monitoring

#### Real-Time Performance Monitoring

```bash
#!/bin/bash
# performance_monitor.sh - Real-time system monitoring

echo "Starting ViolentUTF Performance Monitor..."

# Function to monitor system resources
monitor_resources() {
    echo "=== System Resource Monitor ==="
    echo "Timestamp: $(date)"

    # CPU Usage
    echo "CPU Usage:"
    top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1

    # Memory Usage
    echo "Memory Usage:"
    free -h | awk 'NR==2{printf "Used: %s/%s (%.2f%%)\n", $3,$2,$3*100/$2 }'

    # Disk Usage
    echo "Disk Usage:"
    df -h | grep -vE '^Filesystem|tmpfs|cdrom'

    # Process-specific monitoring
    echo "ViolentUTF Processes:"
    ps aux | grep -E "(violentutf|streamlit|fastapi)" | grep -v grep

    echo "=====================================\n"
}

# Monitor continuously
while true; do
    monitor_resources
    sleep 30
done
```

#### Python Performance Profiling

```python
# performance_profiler.py - Detailed performance profiling

import cProfile
import pstats
import io
import time
import psutil
import threading
from functools import wraps

class PerformanceProfiler:
    def __init__(self, output_file="performance_profile.txt"):
        self.output_file = output_file
        self.start_time = None
        self.monitoring = False

    def profile_function(self, func):
        """Decorator to profile individual functions"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            pr = cProfile.Profile()
            pr.enable()

            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()

            pr.disable()

            # Generate profile report
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s)
            ps.sort_stats('cumulative')
            ps.print_stats()

            # Save profile data
            with open(f"{func.__name__}_profile.txt", 'w') as f:
                f.write(f"Function: {func.__name__}\n")
                f.write(f"Execution time: {end_time - start_time:.4f} seconds\n")
                f.write(f"Memory usage: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB\n")
                f.write("\nProfile Data:\n")
                f.write(s.getvalue())

            return result
        return wrapper

    def start_monitoring(self):
        """Start continuous resource monitoring"""
        self.monitoring = True
        self.start_time = time.time()

        def monitor():
            with open(self.output_file, 'w') as f:
                f.write("Timestamp,CPU%,Memory_MB,Disk_Read_MB,Disk_Write_MB\n")

                while self.monitoring:
                    process = psutil.Process()
                    cpu_percent = process.cpu_percent()
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    io_counters = process.io_counters()
                    disk_read_mb = io_counters.read_bytes / 1024 / 1024
                    disk_write_mb = io_counters.write_bytes / 1024 / 1024

                    timestamp = time.time() - self.start_time
                    f.write(f"{timestamp:.2f},{cpu_percent},{memory_mb:.2f},{disk_read_mb:.2f},{disk_write_mb:.2f}\n")
                    f.flush()

                    time.sleep(1)

        self.monitor_thread = threading.Thread(target=monitor)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join()

# Usage example
profiler = PerformanceProfiler()

@profiler.profile_function
def process_dataset(dataset_path):
    # Your dataset processing code here
    pass
```

### Performance Bottleneck Identification

#### CPU Performance Issues

**Issue: High CPU Usage and Slow Processing**

**Symptoms:**
- CPU usage consistently above 90%
- System becomes unresponsive
- Processing takes much longer than expected
- High context switching and load average

**Diagnostic Steps:**
```bash
# Check CPU usage patterns
top -p $(pgrep -f violentutf) -n 1

# Monitor CPU usage over time
sar -u 1 60  # Monitor for 60 seconds

# Check for CPU-intensive processes
ps aux --sort=-%cpu | head -10

# Profile CPU usage by function
python -m cProfile -o cpu_profile.prof dataset_processor.py
python -c "import pstats; pstats.Stats('cpu_profile.prof').sort_stats('cumulative').print_stats(20)"
```

**Solutions:**

1. **Algorithm Optimization**
   ```python
   # Optimize expensive operations
   def optimized_data_processing(data):
       # Use vectorized operations where possible
       import numpy as np
       import pandas as pd

       # Convert to pandas for efficient operations
       df = pd.DataFrame(data)

       # Vectorized operations instead of loops
       result = df.apply(lambda x: process_row_vectorized(x), axis=1)

       return result.tolist()

   # Use caching for expensive computations
   from functools import lru_cache

   @lru_cache(maxsize=1000)
   def expensive_computation(input_data):
       # Cache results of expensive operations
       return complex_calculation(input_data)
   ```

2. **Parallel Processing Optimization**
   ```python
   # Implement multiprocessing for CPU-intensive tasks
   import multiprocessing as mp
   from concurrent.futures import ProcessPoolExecutor

   def parallel_dataset_processing(dataset, num_workers=None):
       if num_workers is None:
           num_workers = min(mp.cpu_count(), 4)  # Limit to 4 cores max

       # Split dataset into chunks
       chunk_size = len(dataset) // num_workers
       chunks = [dataset[i:i+chunk_size] for i in range(0, len(dataset), chunk_size)]

       # Process chunks in parallel
       with ProcessPoolExecutor(max_workers=num_workers) as executor:
           results = list(executor.map(process_chunk, chunks))

       # Combine results
       return [item for chunk_result in results for item in chunk_result]

   def process_chunk(chunk):
       return [process_item(item) for item in chunk]
   ```

3. **Processing Optimization**
   ```python
   # Optimize data structures and algorithms
   def optimized_processing():
       # Use generators instead of lists for memory efficiency
       def data_generator(source):
           for item in source:
               yield process_item(item)

       # Use appropriate data structures
       from collections import defaultdict, deque

       # Use sets for membership testing instead of lists
       seen_items = set()

       # Use deque for efficient append/pop operations
       processing_queue = deque()

       return data_generator, seen_items, processing_queue
   ```

#### Memory Performance Issues

**Issue: Excessive Memory Usage and Memory Leaks**

**Symptoms:**
- Memory usage continuously increases
- System starts swapping to disk
- "MemoryError" exceptions
- Performance degrades over time

**Diagnostic Steps:**
```bash
# Monitor memory usage patterns
watch -n 5 'free -h'

# Check memory usage by process
ps aux --sort=-%mem | head -10

# Profile memory usage
python -m memory_profiler dataset_processor.py

# Check for memory leaks
valgrind --tool=memcheck --leak-check=full python dataset_processor.py
```

**Solutions:**

1. **Memory-Efficient Data Structures**
   ```python
   # Use memory-efficient data structures
   import array
   import sys

   # Use array instead of list for numeric data
   def create_efficient_numeric_array(data):
       # array uses less memory than list for numeric data
       return array.array('f', data)  # 'f' for float

   # Use __slots__ to reduce memory overhead in classes
   class EfficientDataRecord:
       __slots__ = ['id', 'value', 'timestamp']

       def __init__(self, id, value, timestamp):
           self.id = id
           self.value = value
           self.timestamp = timestamp

   # Use generators instead of lists
   def memory_efficient_processor(large_dataset):
       for item in large_dataset:
           # Process one item at a time
           yield process_item(item)
           # Memory is freed automatically
   ```

2. **Explicit Memory Management**
   ```python
   # Implement explicit memory cleanup
   import gc
   import weakref

   def process_with_memory_management(dataset):
       batch_size = 1000
       batch = []

       for i, item in enumerate(dataset):
           batch.append(process_item(item))

           # Process batch when full
           if len(batch) >= batch_size:
               yield from batch
               batch = []

               # Force garbage collection
               gc.collect()

       # Process remaining items
       if batch:
           yield from batch

   # Use weak references to avoid circular references
   class MemoryAwareCache:
       def __init__(self):
           self._cache = weakref.WeakValueDictionary()

       def get(self, key):
           return self._cache.get(key)

       def set(self, key, value):
           self._cache[key] = value
   ```

3. **Memory Monitoring and Limits**
   ```python
   # Implement memory monitoring and limits
   import psutil
   import resource

   def set_memory_limit(limit_mb):
       """Set memory limit for the process"""
       limit_bytes = limit_mb * 1024 * 1024
       resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))

   def check_memory_usage(threshold_mb=1000):
       """Check if memory usage exceeds threshold"""
       process = psutil.Process()
       memory_mb = process.memory_info().rss / 1024 / 1024

       if memory_mb > threshold_mb:
           print(f"Warning: Memory usage ({memory_mb:.2f}MB) exceeds threshold ({threshold_mb}MB)")
           return False
       return True

   def process_with_memory_monitoring(dataset):
       for i, item in enumerate(dataset):
           result = process_item(item)

           # Check memory every 1000 items
           if i % 1000 == 0:
               if not check_memory_usage():
                   gc.collect()  # Force garbage collection

           yield result
   ```

#### I/O Performance Issues

**Issue: Slow File I/O and Disk Operations**

**Symptoms:**
- Very slow file reading/writing
- High I/O wait times
- Disk operations block processing
- Inconsistent processing speeds

**Diagnostic Steps:**
```bash
# Monitor I/O performance
iostat -x 1 10

# Check disk usage and performance
iotop -o  # Show only processes with I/O activity

# Test disk read/write performance
hdparm -tT /dev/sda

# Monitor file system cache
cat /proc/meminfo | grep -E "Buffers|Cached"
```

**Solutions:**

1. **Optimized File I/O**
   ```python
   # Use buffered I/O for better performance
   def optimized_file_reading(file_path, buffer_size=8192*16):
       with open(file_path, 'r', buffering=buffer_size) as file:
           while True:
               chunk = file.read(buffer_size)
               if not chunk:
                   break
               yield chunk

   # Use memory-mapped files for large files
   import mmap

   def memory_mapped_file_processing(file_path):
       with open(file_path, 'rb') as file:
           with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
               # Process data without loading entire file
               for line in iter(mmapped_file.readline, b""):
                   yield line.decode('utf-8')

   # Asynchronous file I/O
   import aiofiles
   import asyncio

   async def async_file_processing(file_path):
       async with aiofiles.open(file_path, 'r') as file:
           async for line in file:
               yield await process_line_async(line)
   ```

2. **Caching Strategies**
   ```python
   # Implement intelligent caching
   import pickle
   import os
   import hashlib

   class FileCache:
       def __init__(self, cache_dir="./cache"):
           self.cache_dir = cache_dir
           os.makedirs(cache_dir, exist_ok=True)

       def get_cache_key(self, file_path):
           """Generate cache key based on file content hash"""
           with open(file_path, 'rb') as f:
               content = f.read(1024)  # Read first 1KB for hash
               return hashlib.md5(content).hexdigest()

       def get(self, file_path):
           cache_key = self.get_cache_key(file_path)
           cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")

           if os.path.exists(cache_file):
               with open(cache_file, 'rb') as f:
                   return pickle.load(f)
           return None

       def set(self, file_path, data):
           cache_key = self.get_cache_key(file_path)
           cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")

           with open(cache_file, 'wb') as f:
               pickle.dump(data, f)

   # Use cache for processed data
   cache = FileCache()

   def cached_file_processing(file_path):
       # Check cache first
       cached_result = cache.get(file_path)
       if cached_result is not None:
           return cached_result

       # Process file if not cached
       result = process_file(file_path)
       cache.set(file_path, result)
       return result
   ```

3. **Parallel I/O Operations**
   ```python
   # Implement parallel file processing
   import threading
   from queue import Queue
   from concurrent.futures import ThreadPoolExecutor

   def parallel_file_processing(file_paths, max_workers=4):
       def process_file_worker(file_path):
           return process_single_file(file_path)

       with ThreadPoolExecutor(max_workers=max_workers) as executor:
           # Submit all file processing tasks
           future_to_file = {
               executor.submit(process_file_worker, path): path
               for path in file_paths
           }

           # Collect results as they complete
           for future in concurrent.futures.as_completed(future_to_file):
               file_path = future_to_file[future]
               try:
                   result = future.result()
                   yield file_path, result
               except Exception as e:
                   print(f"Error processing {file_path}: {e}")
   ```

## Configuration Optimization

### Performance-Oriented Configuration

```yaml
# High-performance configuration template
performance_optimized_config:
  system_optimization:
    parallel_processing: true
    max_workers: 4  # Adjust based on CPU cores
    memory_management: true
    progressive_loading: true

  dataset_processing:
    batch_size: 1000
    chunk_size: "50MB"
    cache_enabled: true
    compression: false  # Disable for speed

  resource_limits:
    max_memory_usage: "4GB"
    timeout_per_operation: 300
    retry_attempts: 3

  i_o_optimization:
    buffer_size: 131072  # 128KB
    async_io: true
    memory_mapping: true

  monitoring:
    performance_logging: true
    resource_monitoring: true
    progress_reporting: true
```

### Environment-Specific Tuning

```yaml
# Configuration for different environments
environment_configurations:
  development:
    debug_mode: true
    small_dataset_limits: true
    verbose_logging: true
    performance_profiling: true

  testing:
    parallel_processing: false
    deterministic_processing: true
    resource_limits_strict: true

  production:
    parallel_processing: true
    max_performance: true
    minimal_logging: true
    resource_optimization: aggressive

  cloud:
    auto_scaling: true
    distributed_processing: true
    cloud_storage_optimization: true
    network_optimization: true
```

## Specific Performance Optimizations

### PyRIT Integration Optimization

```python
# Optimize PyRIT integration for performance
class OptimizedPyRITIntegration:
    def __init__(self):
        self.connection_pool = self._create_connection_pool()
        self.result_cache = {}

    def _create_connection_pool(self):
        """Create connection pool for better performance"""
        import concurrent.futures
        return concurrent.futures.ThreadPoolExecutor(max_workers=4)

    def optimized_orchestrator_execution(self, prompts, target):
        """Execute orchestrator with performance optimizations"""
        # Batch prompts for efficiency
        batch_size = 10
        results = []

        for i in range(0, len(prompts), batch_size):
            batch = prompts[i:i+batch_size]
            batch_results = self._execute_batch(batch, target)
            results.extend(batch_results)

        return results

    def _execute_batch(self, batch, target):
        """Execute batch of prompts"""
        # Use connection pool for parallel execution
        future_to_prompt = {}

        with self.connection_pool as executor:
            for prompt in batch:
                future = executor.submit(self._execute_single_prompt, prompt, target)
                future_to_prompt[future] = prompt

            results = []
            for future in concurrent.futures.as_completed(future_to_prompt):
                prompt = future_to_prompt[future]
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    print(f"Error executing prompt {prompt}: {e}")
                    results.append(None)

        return results

    def _execute_single_prompt(self, prompt, target):
        """Execute single prompt with caching"""
        # Check cache first
        cache_key = hash(str(prompt) + str(target))
        if cache_key in self.result_cache:
            return self.result_cache[cache_key]

        # Execute prompt
        result = target.send_prompt(prompt)

        # Cache result
        self.result_cache[cache_key] = result
        return result
```

### Database Performance Optimization

```python
# Optimize database operations for performance
class DatabaseOptimizer:
    def __init__(self, db_path):
        self.db_path = db_path
        self._optimize_database()

    def _optimize_database(self):
        """Apply database performance optimizations"""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Apply SQLite optimizations
        optimizations = [
            "PRAGMA synchronous = NORMAL",
            "PRAGMA cache_size = 10000",
            "PRAGMA temp_store = MEMORY",
            "PRAGMA journal_mode = WAL",
            "PRAGMA optimize"
        ]

        for optimization in optimizations:
            cursor.execute(optimization)

        conn.commit()
        conn.close()

    def batch_insert(self, table, data, batch_size=1000):
        """Optimized batch insert"""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Begin transaction
            cursor.execute("BEGIN TRANSACTION")

            # Insert in batches
            for i in range(0, len(data), batch_size):
                batch = data[i:i+batch_size]
                cursor.executemany(f"INSERT INTO {table} VALUES ({','.join(['?'] * len(batch[0]))})", batch)

            # Commit transaction
            cursor.execute("COMMIT")

        except Exception as e:
            cursor.execute("ROLLBACK")
            raise e
        finally:
            conn.close()
```

## Performance Testing and Benchmarking

### Automated Performance Testing

```python
# Automated performance testing suite
class PerformanceTester:
    def __init__(self):
        self.test_results = []

    def run_performance_suite(self, dataset_types, dataset_sizes):
        """Run comprehensive performance tests"""
        for dataset_type in dataset_types:
            for size in dataset_sizes:
                result = self._run_single_test(dataset_type, size)
                self.test_results.append(result)

        return self._generate_report()

    def _run_single_test(self, dataset_type, size):
        """Run single performance test"""
        import time
        import psutil

        # Generate test dataset
        test_dataset = self._generate_test_dataset(dataset_type, size)

        # Record start metrics
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss

        # Execute test
        try:
            result = self._execute_test(test_dataset)
            success = True
        except Exception as e:
            result = str(e)
            success = False

        # Record end metrics
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss

        return {
            'dataset_type': dataset_type,
            'dataset_size': size,
            'execution_time': end_time - start_time,
            'memory_usage': (end_memory - start_memory) / 1024 / 1024,  # MB
            'success': success,
            'result': result
        }

    def _generate_report(self):
        """Generate performance report"""
        report = {
            'summary': {
                'total_tests': len(self.test_results),
                'successful_tests': sum(1 for r in self.test_results if r['success']),
                'average_execution_time': sum(r['execution_time'] for r in self.test_results) / len(self.test_results),
                'average_memory_usage': sum(r['memory_usage'] for r in self.test_results) / len(self.test_results)
            },
            'detailed_results': self.test_results
        }

        return report

# Usage
tester = PerformanceTester()
dataset_types = ['OllaGen1', 'Garak', 'LegalBench']
dataset_sizes = [1000, 5000, 10000]
report = tester.run_performance_suite(dataset_types, dataset_sizes)
```

### Performance Regression Detection

```python
# Performance regression detection
class RegressionDetector:
    def __init__(self, baseline_file="performance_baseline.json"):
        self.baseline_file = baseline_file
        self.baseline_data = self._load_baseline()

    def _load_baseline(self):
        """Load baseline performance data"""
        import json
        import os

        if os.path.exists(self.baseline_file):
            with open(self.baseline_file, 'r') as f:
                return json.load(f)
        return {}

    def check_regression(self, current_results, threshold=0.2):
        """Check for performance regression"""
        regressions = []

        for test_case, current_time in current_results.items():
            if test_case in self.baseline_data:
                baseline_time = self.baseline_data[test_case]
                regression_ratio = (current_time - baseline_time) / baseline_time

                if regression_ratio > threshold:
                    regressions.append({
                        'test_case': test_case,
                        'baseline_time': baseline_time,
                        'current_time': current_time,
                        'regression_percent': regression_ratio * 100
                    })

        return regressions

    def update_baseline(self, new_results):
        """Update baseline with new results"""
        import json

        self.baseline_data.update(new_results)

        with open(self.baseline_file, 'w') as f:
            json.dump(self.baseline_data, f, indent=2)
```

## Emergency Performance Recovery

### Performance Emergency Response

```bash
#!/bin/bash
# performance_emergency_response.sh

echo "ViolentUTF Performance Emergency Response"
echo "========================================="

# 1. Check system resources
echo "1. Checking system resources..."
echo "Memory usage:"
free -h
echo ""
echo "CPU usage:"
top -bn1 | head -5
echo ""
echo "Disk usage:"
df -h
echo ""

# 2. Kill high-resource processes if necessary
echo "2. Checking for runaway processes..."
HIGH_CPU_PROCESSES=$(ps aux --sort=-%cpu | awk 'NR>1 && $3>80 {print $2}')
HIGH_MEM_PROCESSES=$(ps aux --sort=-%mem | awk 'NR>1 && $4>20 {print $2}')

if [ ! -z "$HIGH_CPU_PROCESSES" ] || [ ! -z "$HIGH_MEM_PROCESSES" ]; then
    echo "Found high-resource processes. Consider terminating:"
    ps aux --sort=-%cpu | head -5
    ps aux --sort=-%mem | head -5
fi

# 3. Clear caches
echo "3. Clearing caches..."
rm -rf app_data/violentutf/cache/*
rm -rf /tmp/violentutf_*

# 4. Restart services with optimized configuration
echo "4. Restarting services with performance optimization..."
docker-compose down
sleep 5

# Set performance environment variables
export VIOLENTUTF_PERFORMANCE_MODE=true
export VIOLENTUTF_MAX_WORKERS=2
export VIOLENTUTF_MEMORY_LIMIT=2048

docker-compose up -d

echo "Emergency response complete. Monitor system performance."
```

### Resource Cleanup Procedures

```python
# Resource cleanup for performance recovery
def emergency_resource_cleanup():
    """Emergency cleanup to free resources"""
    import gc
    import os
    import shutil
    import tempfile

    print("Starting emergency resource cleanup...")

    # 1. Force garbage collection
    print("1. Forcing garbage collection...")
    for i in range(3):
        gc.collect()

    # 2. Clear temporary files
    print("2. Clearing temporary files...")
    temp_dirs = [tempfile.gettempdir(), "/tmp", "./temp"]
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            for item in os.listdir(temp_dir):
                if item.startswith("violentutf_"):
                    item_path = os.path.join(temp_dir, item)
                    try:
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        else:
                            os.remove(item_path)
                        print(f"Removed: {item_path}")
                    except Exception as e:
                        print(f"Failed to remove {item_path}: {e}")

    # 3. Clear application caches
    print("3. Clearing application caches...")
    cache_dirs = ["./app_data/violentutf/cache", "./cache", "./.cache"]
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            try:
                shutil.rmtree(cache_dir)
                os.makedirs(cache_dir, exist_ok=True)
                print(f"Cleared cache: {cache_dir}")
            except Exception as e:
                print(f"Failed to clear cache {cache_dir}: {e}")

    # 4. Reset memory limits
    print("4. Resetting memory limits...")
    import resource
    try:
        # Set conservative memory limit (2GB)
        memory_limit = 2 * 1024 * 1024 * 1024  # 2GB in bytes
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit, resource.RLIM_INFINITY))
        print("Memory limit set to 2GB")
    except Exception as e:
        print(f"Failed to set memory limit: {e}")

    print("Emergency cleanup complete.")

# Usage
if __name__ == "__main__":
    emergency_resource_cleanup()
```

Remember: Performance optimization is an iterative process. Always profile before optimizing, measure the impact of changes, and maintain a balance between performance and system stability. When in doubt, start with conservative optimizations and gradually increase performance tuning based on observed results.
