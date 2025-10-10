# Performance Optimization Guide

## Overview

This comprehensive guide provides systematic approaches to optimize performance across all components of ViolentUTF's dataset integration system. Performance optimization encompasses computational efficiency, memory management, I/O optimization, and system-level tuning to ensure optimal evaluation throughput and resource utilization.

## Performance Optimization Philosophy

### Optimization Hierarchy

```yaml
Optimization_Priority_Framework:
  tier_1_critical:
    focus: "Core system stability and functionality"
    priorities:
      - "Memory management and leak prevention"
      - "System stability and error recovery"
      - "Data integrity and consistency"
      - "Basic performance thresholds"

  tier_2_performance:
    focus: "Computational efficiency and throughput"
    priorities:
      - "Algorithm optimization and efficiency"
      - "Parallel processing and concurrency"
      - "Caching and data reuse strategies"
      - "Resource utilization optimization"

  tier_3_scalability:
    focus: "Large-scale processing and scalability"
    priorities:
      - "Distributed processing capabilities"
      - "Cloud integration and elastic scaling"
      - "Advanced caching and persistence"
      - "Performance monitoring and analytics"

  tier_4_advanced:
    focus: "Cutting-edge optimization techniques"
    priorities:
      - "Machine learning-based optimization"
      - "Predictive resource allocation"
      - "Advanced parallelization strategies"
      - "Hardware-specific optimizations"
```

### Performance Measurement Framework

```yaml
Performance_Metrics_Framework:
  throughput_metrics:
    dataset_processing_rate: "Records processed per second"
    evaluation_completion_time: "Total time for evaluation completion"
    concurrent_evaluation_capacity: "Number of simultaneous evaluations"
    scaling_efficiency: "Performance scaling with resource increase"

  resource_utilization_metrics:
    cpu_utilization: "Percentage of CPU capacity utilized"
    memory_efficiency: "Memory usage per unit of work"
    storage_optimization: "Storage space utilization and access patterns"
    network_efficiency: "Network bandwidth utilization for distributed processing"

  quality_metrics:
    accuracy_maintenance: "Performance optimization impact on result accuracy"
    reliability_preservation: "System reliability under optimized configurations"
    error_rate_monitoring: "Error rates under different performance configurations"
    user_experience_metrics: "Response times and system responsiveness"
```

## System-Level Optimization

### Operating System Tuning

#### Linux System Optimization

```bash
#!/bin/bash
# linux_performance_tuning.sh

echo "Configuring Linux system for ViolentUTF performance optimization..."

# 1. Memory management optimization
echo "Optimizing memory management..."

# Increase virtual memory limits
echo "vm.max_map_count=262144" >> /etc/sysctl.conf
echo "vm.overcommit_memory=1" >> /etc/sysctl.conf
echo "vm.overcommit_ratio=80" >> /etc/sysctl.conf

# Optimize swappiness for memory-intensive workloads
echo "vm.swappiness=10" >> /etc/sysctl.conf

# 2. File system optimization
echo "Optimizing file system performance..."

# Increase file descriptor limits
echo "fs.file-max=2097152" >> /etc/sysctl.conf
echo "* soft nofile 1048576" >> /etc/security/limits.conf
echo "* hard nofile 1048576" >> /etc/security/limits.conf

# 3. Network optimization for distributed processing
echo "Optimizing network configuration..."

# TCP optimization for high-throughput applications
echo "net.core.rmem_max=134217728" >> /etc/sysctl.conf
echo "net.core.wmem_max=134217728" >> /etc/sysctl.conf
echo "net.ipv4.tcp_rmem=4096 16384 134217728" >> /etc/sysctl.conf
echo "net.ipv4.tcp_wmem=4096 65536 134217728" >> /etc/sysctl.conf

# 4. CPU scheduling optimization
echo "Optimizing CPU scheduling..."

# Set CPU frequency governor to performance mode
echo performance > /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Apply settings
sysctl -p

echo "Linux system optimization complete."
```

#### macOS System Optimization

```bash
#!/bin/bash
# macos_performance_tuning.sh

echo "Configuring macOS system for ViolentUTF performance optimization..."

# 1. Increase file descriptor limits
echo "Increasing file descriptor limits..."
echo "kern.maxfiles=2097152" | sudo tee -a /etc/sysctl.conf
echo "kern.maxfilesperproc=1048576" | sudo tee -a /etc/sysctl.conf

# Create launchd configuration for ulimits
sudo tee /Library/LaunchDaemons/limit.maxfiles.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
        "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>limit.maxfiles</string>
    <key>ProgramArguments</key>
    <array>
      <string>launchctl</string>
      <string>limit</string>
      <string>maxfiles</string>
      <string>1048576</string>
      <string>1048576</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>ServiceIPC</key>
    <false/>
  </dict>
</plist>
EOF

# 2. Optimize memory settings
echo "Configuring memory optimization..."

# Increase shared memory limits
echo "kern.sysv.shmmax=4294967296" | sudo tee -a /etc/sysctl.conf
echo "kern.sysv.shmall=1048576" | sudo tee -a /etc/sysctl.conf

# 3. Network optimization
echo "Optimizing network settings..."
echo "net.inet.tcp.recvspace=2097152" | sudo tee -a /etc/sysctl.conf
echo "net.inet.tcp.sendspace=2097152" | sudo tee -a /etc/sysctl.conf

echo "macOS system optimization complete. Reboot required for full effect."
```

### Container and Virtualization Optimization

#### Docker Performance Optimization

```yaml
# docker-compose.performance.yml
version: '3.8'

services:
  violentutf_api:
    image: violentutf/api:latest
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
    environment:
      - PYTHONOPTIMIZE=2
      - PYTHONDONTWRITEBYTECODE=1
      - MALLOC_ARENA_MAX=2
      - MALLOC_MMAP_THRESHOLD_=131072
      - MALLOC_TRIM_THRESHOLD_=131072
      - MALLOC_TOP_PAD_=131072
      - MALLOC_MMAP_MAX_=65536
    volumes:
      - type: tmpfs
        target: /tmp
        tmpfs:
          size: 2G
          mode: 1777
    ulimits:
      memlock: -1
      nofile: 1048576
      nproc: 65536
    sysctls:
      - net.core.somaxconn=65535
      - vm.overcommit_memory=1
```

#### Kubernetes Performance Configuration

```yaml
# kubernetes-performance-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: violentutf-performance-config
data:
  performance.yaml: |
    optimization:
      memory_management:
        max_heap_size: "6g"
        gc_optimization: true
        memory_mapping: true

      cpu_optimization:
        thread_pool_size: 16
        parallel_processing: true
        cpu_affinity: true

      io_optimization:
        async_io: true
        buffer_size: 1048576
        batch_processing: true

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: violentutf-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: violentutf-api
  template:
    metadata:
      labels:
        app: violentutf-api
    spec:
      nodeSelector:
        performance-tier: high
      containers:
      - name: violentutf-api
        image: violentutf/api:optimized
        resources:
          requests:
            memory: "4Gi"
            cpu: "2000m"
          limits:
            memory: "8Gi"
            cpu: "4000m"
        env:
        - name: PYTHONOPTIMIZE
          value: "2"
        - name: MALLOC_ARENA_MAX
          value: "2"
        volumeMounts:
        - name: performance-config
          mountPath: /config
        - name: tmp-volume
          mountPath: /tmp
      volumes:
      - name: performance-config
        configMap:
          name: violentutf-performance-config
      - name: tmp-volume
        emptyDir:
          medium: Memory
          sizeLimit: 2Gi
```

## Application-Level Optimization

### Python Performance Optimization

#### Memory Management Optimization

```python
# memory_optimization.py
import gc
import sys
import tracemalloc
from functools import wraps
from typing import Any, Callable, Generator, Optional

class MemoryOptimizer:
    """Advanced memory optimization for ViolentUTF operations"""

    def __init__(self, max_memory_mb: int = 2048):
        self.max_memory_mb = max_memory_mb
        self.memory_threshold = max_memory_mb * 0.8  # 80% threshold

    def memory_efficient_decorator(self, func: Callable) -> Callable:
        """Decorator for memory-efficient function execution"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Start memory tracking
            tracemalloc.start()

            try:
                # Execute function with memory monitoring
                result = self._execute_with_memory_management(func, *args, **kwargs)
                return result
            finally:
                # Stop memory tracking and cleanup
                tracemalloc.stop()
                gc.collect()

        return wrapper

    def _execute_with_memory_management(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with active memory management"""
        import psutil

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Execute function
        result = func(*args, **kwargs)

        # Check memory usage after execution
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_delta = final_memory - initial_memory

        if final_memory > self.memory_threshold:
            print(f"Memory usage high: {final_memory:.2f}MB (delta: +{memory_delta:.2f}MB)")
            self._aggressive_cleanup()

        return result

    def _aggressive_cleanup(self):
        """Perform aggressive memory cleanup"""
        # Force garbage collection multiple times
        for _ in range(3):
            gc.collect()

        # Clear Python's internal caches
        sys._clear_type_cache()

        # Additional cleanup for specific libraries
        try:
            import numpy as np
            # Clear NumPy memory pools if available
            if hasattr(np, '_NoValue'):
                np._NoValue._instances.clear()
        except ImportError:
            pass

# Memory-efficient data processing patterns
class EfficientDataProcessor:
    """Memory-efficient data processing implementations"""

    @staticmethod
    def chunked_processor(data: list, chunk_size: int = 1000) -> Generator[list, None, None]:
        """Process data in memory-efficient chunks"""
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            yield chunk

            # Clear chunk reference and force garbage collection
            del chunk
            gc.collect()

    @staticmethod
    def streaming_file_processor(file_path: str, buffer_size: int = 8192) -> Generator[str, None, None]:
        """Memory-efficient file processing using streaming"""
        with open(file_path, 'r', buffering=buffer_size) as file:
            for line in file:
                yield line.strip()

                # Periodic garbage collection for long files
                if file.tell() % (buffer_size * 1000) == 0:
                    gc.collect()

    @staticmethod
    def memory_mapped_processor(file_path: str) -> Generator[bytes, None, None]:
        """Use memory mapping for large file processing"""
        import mmap

        with open(file_path, 'rb') as file:
            with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                for line in iter(mmapped_file.readline, b""):
                    yield line

# Usage examples
memory_optimizer = MemoryOptimizer(max_memory_mb=4096)

@memory_optimizer.memory_efficient_decorator
def process_large_dataset(dataset):
    """Example of memory-efficient dataset processing"""
    processor = EfficientDataProcessor()

    results = []
    for chunk in processor.chunked_processor(dataset, chunk_size=1000):
        # Process chunk
        chunk_results = [process_item(item) for item in chunk]
        results.extend(chunk_results)

    return results

def process_item(item):
    """Process individual data item"""
    # Implement actual processing logic
    return item
```

#### CPU Performance Optimization

```python
# cpu_optimization.py
import multiprocessing as mp
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import lru_cache, partial
import asyncio
import time
from typing import List, Callable, Any, Optional

class CPUOptimizer:
    """CPU performance optimization for computational tasks"""

    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(mp.cpu_count(), 8)
        self.cpu_count = mp.cpu_count()

    def parallel_map(self, func: Callable, iterable: List[Any],
                    use_processes: bool = True) -> List[Any]:
        """Parallel execution using either processes or threads"""

        if use_processes and len(iterable) > 100:
            # Use processes for CPU-intensive tasks
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                return list(executor.map(func, iterable))
        else:
            # Use threads for I/O-bound tasks or small datasets
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                return list(executor.map(func, iterable))

    def batch_parallel_processing(self, func: Callable, data: List[Any],
                                 batch_size: Optional[int] = None) -> List[Any]:
        """Process data in batches using parallel execution"""

        if batch_size is None:
            batch_size = max(len(data) // (self.max_workers * 4), 1)

        # Create batches
        batches = [data[i:i + batch_size] for i in range(0, len(data), batch_size)]

        # Process batches in parallel
        batch_processor = partial(self._process_batch, func)

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            batch_results = list(executor.map(batch_processor, batches))

        # Flatten results
        return [item for batch_result in batch_results for item in batch_result]

    @staticmethod
    def _process_batch(func: Callable, batch: List[Any]) -> List[Any]:
        """Process a single batch of data"""
        return [func(item) for item in batch]

    async def async_parallel_processing(self, async_func: Callable,
                                       data: List[Any],
                                       semaphore_limit: int = 100) -> List[Any]:
        """Asynchronous parallel processing with concurrency control"""

        semaphore = asyncio.Semaphore(semaphore_limit)

        async def controlled_execution(item):
            async with semaphore:
                return await async_func(item)

        # Execute all tasks concurrently
        tasks = [controlled_execution(item) for item in data]
        return await asyncio.gather(*tasks)

# Caching optimization
class SmartCache:
    """Intelligent caching for performance optimization"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = {}
        self._access_times = {}

    def cached_function(self, func: Callable) -> Callable:
        """Decorator for intelligent function caching"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = self._create_cache_key(func.__name__, args, kwargs)

            # Check cache
            if self._is_cache_valid(cache_key):
                self._access_times[cache_key] = time.time()
                return self._cache[cache_key]

            # Execute function and cache result
            result = func(*args, **kwargs)
            self._store_in_cache(cache_key, result)

            return result

        return wrapper

    def _create_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Create a unique cache key"""
        import hashlib

        key_data = f"{func_name}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid"""
        if cache_key not in self._cache:
            return False

        # Check TTL
        access_time = self._access_times.get(cache_key, 0)
        if time.time() - access_time > self.ttl_seconds:
            self._remove_from_cache(cache_key)
            return False

        return True

    def _store_in_cache(self, cache_key: str, result: Any):
        """Store result in cache with size management"""
        # Remove oldest entries if cache is full
        if len(self._cache) >= self.max_size:
            self._cleanup_old_entries()

        self._cache[cache_key] = result
        self._access_times[cache_key] = time.time()

    def _cleanup_old_entries(self):
        """Remove oldest cache entries"""
        # Sort by access time and remove oldest 20%
        sorted_keys = sorted(self._access_times.keys(),
                           key=lambda k: self._access_times[k])

        keys_to_remove = sorted_keys[:len(sorted_keys) // 5]

        for key in keys_to_remove:
            self._remove_from_cache(key)

    def _remove_from_cache(self, cache_key: str):
        """Remove entry from cache"""
        self._cache.pop(cache_key, None)
        self._access_times.pop(cache_key, None)

# Algorithm optimization
class AlgorithmOptimizer:
    """Optimized algorithms for common ViolentUTF operations"""

    @staticmethod
    @lru_cache(maxsize=1000)
    def fast_similarity_calculation(text1: str, text2: str) -> float:
        """Optimized text similarity calculation with caching"""
        if text1 == text2:
            return 1.0

        # Use efficient similarity algorithm
        return AlgorithmOptimizer._jaccard_similarity(text1, text2)

    @staticmethod
    def _jaccard_similarity(text1: str, text2: str) -> float:
        """Fast Jaccard similarity implementation"""
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0

    @staticmethod
    def vectorized_processing(data: List[dict]) -> List[dict]:
        """Vectorized data processing using NumPy"""
        try:
            import numpy as np
            import pandas as pd

            # Convert to DataFrame for vectorized operations
            df = pd.DataFrame(data)

            # Perform vectorized operations
            if 'score' in df.columns:
                df['normalized_score'] = (df['score'] - df['score'].min()) / (df['score'].max() - df['score'].min())

            return df.to_dict('records')

        except ImportError:
            # Fallback to regular processing if NumPy/Pandas not available
            return AlgorithmOptimizer._fallback_processing(data)

    @staticmethod
    def _fallback_processing(data: List[dict]) -> List[dict]:
        """Fallback processing without NumPy/Pandas"""
        if not data or 'score' not in data[0]:
            return data

        scores = [item['score'] for item in data]
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score

        for item in data:
            if score_range > 0:
                item['normalized_score'] = (item['score'] - min_score) / score_range
            else:
                item['normalized_score'] = 0.0

        return data

# Usage examples
cpu_optimizer = CPUOptimizer(max_workers=8)
smart_cache = SmartCache(max_size=2000, ttl_seconds=1800)
algorithm_optimizer = AlgorithmOptimizer()

# Example optimized function
@smart_cache.cached_function
def expensive_computation(input_data):
    """Example of expensive computation with caching"""
    # Simulate expensive operation
    time.sleep(0.1)
    return sum(ord(c) for c in str(input_data))

# Parallel processing example
def process_dataset_optimized(dataset):
    """Optimized dataset processing using all techniques"""

    # Use vectorized processing for numerical operations
    if isinstance(dataset[0], dict):
        dataset = algorithm_optimizer.vectorized_processing(dataset)

    # Use parallel processing for independent operations
    results = cpu_optimizer.batch_parallel_processing(
        expensive_computation,
        dataset,
        batch_size=100
    )

    return results
```

### Database Performance Optimization

```python
# database_optimization.py
import sqlite3
import threading
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import time

class DatabaseOptimizer:
    """Database performance optimization for ViolentUTF"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection_pool = []
        self.pool_lock = threading.Lock()
        self.max_connections = 10

        # Initialize connection pool
        self._initialize_connection_pool()

    def _initialize_connection_pool(self):
        """Initialize database connection pool"""
        for _ in range(self.max_connections):
            conn = self._create_optimized_connection()
            self.connection_pool.append(conn)

    def _create_optimized_connection(self) -> sqlite3.Connection:
        """Create optimized database connection"""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0
        )

        # Apply SQLite optimizations
        optimizations = [
            "PRAGMA synchronous = NORMAL",
            "PRAGMA cache_size = 20000",
            "PRAGMA temp_store = MEMORY",
            "PRAGMA journal_mode = WAL",
            "PRAGMA mmap_size = 268435456",  # 256MB
            "PRAGMA page_size = 4096",
            "PRAGMA auto_vacuum = INCREMENTAL"
        ]

        cursor = conn.cursor()
        for optimization in optimizations:
            cursor.execute(optimization)

        conn.commit()
        return conn

    @contextmanager
    def get_connection(self):
        """Get connection from pool"""
        with self.pool_lock:
            if self.connection_pool:
                conn = self.connection_pool.pop()
            else:
                conn = self._create_optimized_connection()

        try:
            yield conn
        finally:
            with self.pool_lock:
                if len(self.connection_pool) < self.max_connections:
                    self.connection_pool.append(conn)
                else:
                    conn.close()

    def optimized_batch_insert(self, table: str, data: List[Dict[str, Any]],
                              batch_size: int = 1000) -> int:
        """Optimized batch insert with transaction management"""

        if not data:
            return 0

        total_inserted = 0

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Prepare insert statement
            columns = list(data[0].keys())
            placeholders = ','.join(['?' for _ in columns])
            insert_sql = f"INSERT OR IGNORE INTO {table} ({','.join(columns)}) VALUES ({placeholders})"

            # Process in batches
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]

                try:
                    cursor.execute("BEGIN IMMEDIATE TRANSACTION")

                    # Convert batch to tuple format
                    batch_tuples = [tuple(row[col] for col in columns) for row in batch]

                    cursor.executemany(insert_sql, batch_tuples)
                    cursor.execute("COMMIT")

                    total_inserted += len(batch)

                except Exception as e:
                    cursor.execute("ROLLBACK")
                    print(f"Batch insert error: {e}")
                    # Continue with next batch

        return total_inserted

    def optimized_bulk_select(self, query: str, parameters: Optional[tuple] = None,
                             fetch_size: int = 10000) -> List[Dict[str, Any]]:
        """Optimized bulk select with memory management"""

        results = []

        with self.get_connection() as conn:
            cursor = conn.cursor()

            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)

            # Get column names
            columns = [description[0] for description in cursor.description]

            # Fetch in chunks to manage memory
            while True:
                rows = cursor.fetchmany(fetch_size)
                if not rows:
                    break

                # Convert to dictionaries
                chunk_results = [dict(zip(columns, row)) for row in rows]
                results.extend(chunk_results)

        return results

    def create_performance_indexes(self, table_indexes: Dict[str, List[str]]):
        """Create performance indexes for common queries"""

        with self.get_connection() as conn:
            cursor = conn.cursor()

            for table, columns in table_indexes.items():
                for column in columns:
                    index_name = f"idx_{table}_{column}"

                    try:
                        cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column})")
                        print(f"Created index: {index_name}")
                    except Exception as e:
                        print(f"Error creating index {index_name}: {e}")

            conn.commit()

    def analyze_and_optimize(self):
        """Analyze database and apply optimizations"""

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Update table statistics
            cursor.execute("ANALYZE")

            # Optimize database
            cursor.execute("PRAGMA optimize")

            # Incremental vacuum if needed
            cursor.execute("PRAGMA incremental_vacuum")

            conn.commit()

            print("Database analysis and optimization complete.")

# Usage example
db_optimizer = DatabaseOptimizer("violentutf_optimized.db")

# Create performance indexes
performance_indexes = {
    "evaluations": ["dataset_type", "timestamp", "user_id"],
    "results": ["evaluation_id", "score", "created_at"],
    "datasets": ["type", "size", "status"]
}

db_optimizer.create_performance_indexes(performance_indexes)

# Optimized data insertion
def insert_evaluation_results(results_data):
    """Insert evaluation results with optimization"""
    return db_optimizer.optimized_batch_insert("results", results_data, batch_size=2000)

# Optimized data retrieval
def get_evaluation_history(dataset_type):
    """Retrieve evaluation history with optimization"""
    query = """
    SELECT e.id, e.dataset_type, e.timestamp, r.score, r.accuracy
    FROM evaluations e
    JOIN results r ON e.id = r.evaluation_id
    WHERE e.dataset_type = ?
    ORDER BY e.timestamp DESC
    """
    return db_optimizer.optimized_bulk_select(query, (dataset_type,))
```

## I/O Performance Optimization

### File I/O Optimization

```python
# io_optimization.py
import asyncio
import aiofiles
import mmap
import os
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator, Generator, List, Optional
import time

class IOOptimizer:
    """I/O performance optimization for file operations"""

    def __init__(self, buffer_size: int = 1024 * 1024):  # 1MB default
        self.buffer_size = buffer_size
        self.thread_pool = ThreadPoolExecutor(max_workers=4)

    def optimized_file_read(self, file_path: str,
                           chunk_size: Optional[int] = None) -> Generator[str, None, None]:
        """Optimized file reading with large buffers"""

        chunk_size = chunk_size or self.buffer_size

        with open(file_path, 'r', buffering=chunk_size) as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def memory_mapped_read(self, file_path: str) -> Generator[bytes, None, None]:
        """Memory-mapped file reading for large files"""

        with open(file_path, 'rb') as file:
            with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                for line in iter(mmapped_file.readline, b""):
                    yield line

    async def async_file_read(self, file_path: str,
                             chunk_size: Optional[int] = None) -> AsyncGenerator[str, None]:
        """Asynchronous file reading"""

        chunk_size = chunk_size or self.buffer_size

        async with aiofiles.open(file_path, 'r') as file:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def parallel_file_processing(self, file_paths: List[str],
                                processor_func) -> List:
        """Process multiple files in parallel"""

        with ThreadPoolExecutor(max_workers=len(file_paths)) as executor:
            futures = [executor.submit(processor_func, path) for path in file_paths]
            results = [future.result() for future in futures]

        return results

    def optimized_file_write(self, file_path: str, data: List[str],
                            sync_frequency: int = 1000):
        """Optimized file writing with controlled sync"""

        with open(file_path, 'w', buffering=self.buffer_size) as file:
            for i, line in enumerate(data):
                file.write(line)

                # Sync to disk periodically
                if i % sync_frequency == 0:
                    file.flush()
                    os.fsync(file.fileno())

# Network I/O optimization
class NetworkOptimizer:
    """Network I/O optimization for distributed processing"""

    def __init__(self, connection_pool_size: int = 10):
        self.connection_pool_size = connection_pool_size

    async def optimized_http_requests(self, urls: List[str],
                                     semaphore_limit: int = 50) -> List[str]:
        """Optimized HTTP requests with connection pooling"""

        import aiohttp

        semaphore = asyncio.Semaphore(semaphore_limit)

        async def fetch_url(session, url):
            async with semaphore:
                async with session.get(url) as response:
                    return await response.text()

        connector = aiohttp.TCPConnector(
            limit=self.connection_pool_size,
            limit_per_host=10,
            keepalive_timeout=300
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [fetch_url(session, url) for url in urls]
            return await asyncio.gather(*tasks)

# Usage examples
io_optimizer = IOOptimizer(buffer_size=2 * 1024 * 1024)  # 2MB buffer

def process_large_file_optimized(file_path):
    """Example of optimized large file processing"""

    results = []

    # Use memory mapping for very large files
    file_size = os.path.getsize(file_path)

    if file_size > 100 * 1024 * 1024:  # 100MB
        # Use memory mapping
        for line in io_optimizer.memory_mapped_read(file_path):
            processed_line = process_line(line.decode('utf-8'))
            results.append(processed_line)
    else:
        # Use optimized buffered reading
        for chunk in io_optimizer.optimized_file_read(file_path):
            for line in chunk.split('\n'):
                if line.strip():
                    processed_line = process_line(line)
                    results.append(processed_line)

    return results

def process_line(line):
    """Process individual line"""
    return line.strip().upper()
```

## Monitoring and Analytics

### Performance Monitoring System

```python
# performance_monitoring.py
import time
import psutil
import threading
import json
from datetime import datetime
from typing import Dict, List, Optional, Callable
import sqlite3

class PerformanceMonitor:
    """Comprehensive performance monitoring system"""

    def __init__(self, db_path: str = "performance_metrics.db"):
        self.db_path = db_path
        self.monitoring_active = False
        self.monitor_thread = None
        self.metrics_cache = {}

        self._initialize_database()

    def _initialize_database(self):
        """Initialize performance metrics database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            metric_type TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            metadata TEXT
        )
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_performance_timestamp
        ON performance_metrics (timestamp)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_performance_type_name
        ON performance_metrics (metric_type, metric_name)
        """)

        conn.commit()
        conn.close()

    def start_monitoring(self, interval: float = 1.0):
        """Start continuous performance monitoring"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join()

    def _monitoring_loop(self, interval: float):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                self._collect_system_metrics()

                # Collect application metrics
                self._collect_application_metrics()

                # Store metrics in database
                self._store_metrics()

                time.sleep(interval)

            except Exception as e:
                print(f"Monitoring error: {e}")

    def _collect_system_metrics(self):
        """Collect system-level performance metrics"""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        self.metrics_cache['system_cpu_percent'] = cpu_percent

        # Memory metrics
        memory = psutil.virtual_memory()
        self.metrics_cache['system_memory_percent'] = memory.percent
        self.metrics_cache['system_memory_used_mb'] = memory.used / 1024 / 1024
        self.metrics_cache['system_memory_available_mb'] = memory.available / 1024 / 1024

        # Disk metrics
        disk = psutil.disk_usage('/')
        self.metrics_cache['system_disk_percent'] = (disk.used / disk.total) * 100

        # Network metrics
        network = psutil.net_io_counters()
        self.metrics_cache['system_network_bytes_sent'] = network.bytes_sent
        self.metrics_cache['system_network_bytes_recv'] = network.bytes_recv

    def _collect_application_metrics(self):
        """Collect application-specific metrics"""
        try:
            process = psutil.Process()

            # Process CPU and memory
            self.metrics_cache['app_cpu_percent'] = process.cpu_percent()
            self.metrics_cache['app_memory_mb'] = process.memory_info().rss / 1024 / 1024

            # Process I/O
            io_counters = process.io_counters()
            self.metrics_cache['app_io_read_bytes'] = io_counters.read_bytes
            self.metrics_cache['app_io_write_bytes'] = io_counters.write_bytes

            # Thread count
            self.metrics_cache['app_thread_count'] = process.num_threads()

        except psutil.NoSuchProcess:
            pass

    def _store_metrics(self):
        """Store collected metrics in database"""
        if not self.metrics_cache:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        timestamp = datetime.now()

        for metric_name, metric_value in self.metrics_cache.items():
            metric_type = metric_name.split('_')[0]  # system or app

            cursor.execute("""
            INSERT INTO performance_metrics
            (timestamp, metric_type, metric_name, metric_value)
            VALUES (?, ?, ?, ?)
            """, (timestamp, metric_type, metric_name, metric_value))

        conn.commit()
        conn.close()

        # Clear cache
        self.metrics_cache.clear()

    def performance_decorator(self, metric_name: str):
        """Decorator to measure function performance"""
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss

                try:
                    result = func(*args, **kwargs)
                    success = True
                except Exception as e:
                    result = e
                    success = False

                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss

                # Record metrics
                execution_time = end_time - start_time
                memory_delta = (end_memory - start_memory) / 1024 / 1024  # MB

                self._record_function_metrics(metric_name, execution_time, memory_delta, success)

                if not success:
                    raise result

                return result

            return wrapper
        return decorator

    def _record_function_metrics(self, metric_name: str, execution_time: float,
                                memory_delta: float, success: bool):
        """Record function-specific metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        timestamp = datetime.now()

        # Record execution time
        cursor.execute("""
        INSERT INTO performance_metrics
        (timestamp, metric_type, metric_name, metric_value, metadata)
        VALUES (?, ?, ?, ?, ?)
        """, (timestamp, 'function', f"{metric_name}_execution_time",
              execution_time, json.dumps({"success": success})))

        # Record memory delta
        cursor.execute("""
        INSERT INTO performance_metrics
        (timestamp, metric_type, metric_name, metric_value, metadata)
        VALUES (?, ?, ?, ?, ?)
        """, (timestamp, 'function', f"{metric_name}_memory_delta",
              memory_delta, json.dumps({"success": success})))

        conn.commit()
        conn.close()

    def get_performance_report(self, hours: int = 24) -> Dict:
        """Generate performance report for specified time period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Query metrics from last N hours
        cursor.execute("""
        SELECT metric_type, metric_name,
               AVG(metric_value) as avg_value,
               MIN(metric_value) as min_value,
               MAX(metric_value) as max_value,
               COUNT(*) as sample_count
        FROM performance_metrics
        WHERE timestamp > datetime('now', '-{} hours')
        GROUP BY metric_type, metric_name
        ORDER BY metric_type, metric_name
        """.format(hours))

        results = cursor.fetchall()
        conn.close()

        # Organize results by metric type
        report = {}
        for row in results:
            metric_type, metric_name, avg_val, min_val, max_val, count = row

            if metric_type not in report:
                report[metric_type] = {}

            report[metric_type][metric_name] = {
                'average': avg_val,
                'minimum': min_val,
                'maximum': max_val,
                'samples': count
            }

        return report

# Usage example
monitor = PerformanceMonitor()
monitor.start_monitoring(interval=5.0)  # Monitor every 5 seconds

@monitor.performance_decorator("dataset_processing")
def process_dataset_with_monitoring(dataset):
    """Example function with performance monitoring"""
    time.sleep(1)  # Simulate processing
    return len(dataset)

# Generate report
report = monitor.get_performance_report(hours=1)
print(json.dumps(report, indent=2))
```

This comprehensive performance optimization guide provides systematic approaches to optimize every aspect of ViolentUTF's dataset integration system, from system-level tuning to application-specific optimizations, ensuring maximum performance and efficiency across all evaluation workflows.
