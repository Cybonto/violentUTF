# Improved Dataset Import Plan - PyRIT & ViolentUTF Harmonious Integration

## Executive Summary

After comprehensive analysis of the PyRIT API documentation, ViolentUTF's dual storage architecture, and current implementation challenges, this improved plan provides a robust solution that addresses the 50-row import limitation while maintaining seamless integration with both PyRIT's memory system and ViolentUTF's configuration database.

## Architecture Understanding

### ViolentUTF's Dual Storage Architecture Rationale

ViolentUTF employs a **dual database architecture** by necessity, not design choice:

1. **PyRIT Memory System (DuckDB)**: 
   - **Purpose**: Framework-mandated execution data storage
   - **Content**: Conversation flows, prompt/response pairs, scoring results
   - **Lifecycle**: Ephemeral, execution-scoped, can be cleared after analysis
   - **Management**: PyRIT's `CentralMemory` and `DuckDBMemory` classes

2. **ViolentUTF Database (SQLite)**:
   - **Purpose**: Application configuration and API management
   - **Content**: User-defined generators, scorers, datasets, converters
   - **Lifecycle**: Persistent, survives across sessions
   - **Management**: ViolentUTF's own database managers

### Current 50-Row Limitation Analysis

The hardcoded limits exist in **three critical locations**:
- `datasets.py:675,688,701`: `return prompts[:50]` for each dataset type
- `dataset_integration_service.py:227`: `return prompts[:50]` for active memory
- `dataset_integration_service.py:272`: `LIMIT 50` in SQL query

## Improved Integration Architecture

### Phase 1: Enhanced Backend with Smart Memory Management

#### 1.1 PyRIT-Aware Streaming Processor with Memory Optimization
```python
class PyRITStreamProcessor:
    """Enhanced streaming processor with memory-aware chunking"""
    
    def __init__(self, memory_interface: Optional[MemoryInterface] = None):
        self.memory = memory_interface or CentralMemory.get_memory_instance()
        self.chunk_size = int(os.getenv("DATASET_CHUNK_SIZE", 1000))
        self.max_memory_mb = int(os.getenv("DATASET_MAX_MEMORY_MB", 512))
        self.stats = DatasetImportStats()
        
    async def process_pyrit_dataset_stream(
        self, 
        dataset_type: str,
        config: Dict[str, Any],
        import_config: DatasetImportConfig,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> AsyncIterator[DatasetChunk]:
        """Stream process PyRIT datasets with intelligent chunking"""
        
        # Pre-validate dataset availability
        await self._validate_dataset_access(dataset_type, config)
        
        # Get the original PyRIT dataset (unlimited)
        dataset = await self._fetch_full_pyrit_dataset(dataset_type, config)
        
        # Calculate optimal chunk size based on dataset characteristics
        optimal_chunk_size = self._calculate_optimal_chunk_size(dataset, import_config)
        
        # Stream prompts in intelligent chunks
        prompts_processed = 0
        chunk_data = []
        chunk_metadata = []
        
        async for prompt_info in self._extract_prompts_with_metadata(dataset):
            chunk_data.append(prompt_info.text)
            chunk_metadata.append(prompt_info.metadata)
            prompts_processed += 1
            
            # Yield chunk when optimal size reached
            if len(chunk_data) >= optimal_chunk_size:
                yield DatasetChunk(
                    prompts=chunk_data,
                    metadata=chunk_metadata,
                    chunk_index=prompts_processed // optimal_chunk_size,
                    total_processed=prompts_processed
                )
                chunk_data = []
                chunk_metadata = []
                
                # Progress callback
                if progress_callback:
                    await progress_callback(prompts_processed, self.stats.estimated_total)
                
            # Stop if max limit reached
            if import_config.max_import_size and prompts_processed >= import_config.max_import_size:
                break
                
        # Yield remaining prompts
        if chunk_data:
            yield DatasetChunk(
                prompts=chunk_data,
                metadata=chunk_metadata,
                chunk_index=(prompts_processed // optimal_chunk_size) + 1,
                total_processed=prompts_processed
            )
    
    def _calculate_optimal_chunk_size(self, dataset: Any, config: DatasetImportConfig) -> int:
        """Calculate optimal chunk size based on dataset characteristics"""
        if hasattr(dataset, 'prompts'):
            # Estimate average prompt size
            sample_size = min(10, len(dataset.prompts))
            avg_prompt_size = sum(len(str(p)) for p in dataset.prompts[:sample_size]) / sample_size
            
            # Calculate chunk size to stay within memory limits
            target_chunk_memory = self.max_memory_mb * 1024 * 1024 * 0.7  # 70% of max memory
            calculated_chunk_size = int(target_chunk_memory / avg_prompt_size)
            
            # Clamp to reasonable bounds
            return max(100, min(calculated_chunk_size, config.chunk_size))
        
        return config.chunk_size
    
    async def _fetch_full_pyrit_dataset(self, dataset_type: str, config: Dict) -> Any:
        """Fetch complete PyRIT dataset without 50-row limit"""
        try:
            # Import all PyRIT dataset functions
            from pyrit.datasets import (
                fetch_harmbench_dataset,
                fetch_many_shot_jailbreaking_dataset,
                fetch_decoding_trust_stereotypes_dataset,
                fetch_seclists_bias_testing_dataset,
                fetch_wmdp_dataset,
                fetch_adv_bench_dataset,
                fetch_aya_redteaming_dataset,
                fetch_forbidden_questions_dataset,
                fetch_pku_safe_rlhf_dataset,
                fetch_xstest_dataset,
            )
            
            dataset_fetchers = {
                "harmbench": fetch_harmbench_dataset,
                "many_shot_jailbreaking": fetch_many_shot_jailbreaking_dataset,
                "decoding_trust_stereotypes": fetch_decoding_trust_stereotypes_dataset,
                "seclists_bias_testing": fetch_seclists_bias_testing_dataset,
                "wmdp": fetch_wmdp_dataset,
                "adv_bench": fetch_adv_bench_dataset,
                "aya_redteaming": fetch_aya_redteaming_dataset,
                "forbidden_questions": fetch_forbidden_questions_dataset,
                "pku_safe_rlhf": fetch_pku_safe_rlhf_dataset,
                "xstest": fetch_xstest_dataset,
            }
            
            fetcher = dataset_fetchers.get(dataset_type)
            if not fetcher:
                raise ValueError(f"Unknown dataset type: {dataset_type}")
            
            # Filter config to only include supported parameters
            clean_config = self._clean_config_for_fetcher(fetcher, config)
            
            # Fetch dataset with retries and error handling
            return await self._fetch_with_retry(fetcher, clean_config)
            
        except Exception as e:
            logger.error(f"Failed to fetch PyRIT dataset {dataset_type}: {e}")
            raise DatasetFetchError(f"Could not fetch dataset {dataset_type}: {str(e)}")
    
    async def _fetch_with_retry(self, fetcher: Callable, config: Dict, max_retries: int = 3) -> Any:
        """Fetch dataset with retry logic and exponential backoff"""
        for attempt in range(max_retries):
            try:
                return fetcher(**config)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                
                # Exponential backoff
                wait_time = 2 ** attempt
                logger.warning(f"Dataset fetch attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
```

#### 1.2 Enhanced PyRIT Memory Integration with User Context
```python
class PyRITMemoryBridge:
    """Enhanced bridge between ViolentUTF and PyRIT memory systems"""
    
    def __init__(self):
        self.memory_cache = {}
        self.user_context_manager = UserContextManager()
        
    async def get_or_create_user_memory(self, user_id: str) -> DuckDBMemory:
        """Get or create user-specific PyRIT memory instance"""
        if user_id not in self.memory_cache:
            # Create user-specific memory path
            user_hash = self.user_context_manager.get_user_hash(user_id)
            memory_path = f"/app/app_data/violentutf/pyrit_memory_{user_hash}.db"
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(memory_path), exist_ok=True)
            
            # Create memory instance
            memory = DuckDBMemory(db_path=memory_path)
            self.memory_cache[user_id] = memory
            
        return self.memory_cache[user_id]
    
    async def store_prompts_to_pyrit_memory(
        self, 
        prompts: List[str], 
        metadata: List[Dict[str, Any]],
        dataset_id: str,
        user_id: str,
        batch_size: int = 100
    ) -> int:
        """Store prompts using PyRIT's async memory functions with user context"""
        from pyrit.models import SeedPrompt
        
        memory = await self.get_or_create_user_memory(user_id)
        
        # Convert to PyRIT SeedPrompt format with rich metadata
        seed_prompts = []
        for i, (prompt_text, prompt_metadata) in enumerate(zip(prompts, metadata)):
            # Merge dataset metadata with prompt metadata
            combined_metadata = {
                "dataset_id": dataset_id,
                "import_batch": str(i // batch_size),
                "import_timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                **prompt_metadata
            }
            
            seed_prompt = SeedPrompt(
                value=prompt_text,
                dataset_name=dataset_id,
                labels=[f"dataset:{dataset_id}", "imported", f"user:{user_id}"],
                metadata=combined_metadata
            )
            seed_prompts.append(seed_prompt)
            
        # Batch insert to PyRIT memory
        stored_count = 0
        for batch_start in range(0, len(seed_prompts), batch_size):
            batch = seed_prompts[batch_start:batch_start + batch_size]
            try:
                await memory.add_seed_prompts_to_memory_async(prompts=batch)
                stored_count += len(batch)
            except Exception as e:
                logger.error(f"Failed to store batch {batch_start}: {e}")
                raise
                
        return stored_count
    
    async def get_prompts_from_pyrit_memory(
        self,
        dataset_id: str,
        user_id: str,
        offset: int = 0,
        limit: int = 1000,
        include_metadata: bool = False
    ) -> Tuple[List[str], int]:
        """Retrieve prompts using PyRIT memory interface with pagination"""
        memory = await self.get_or_create_user_memory(user_id)
        
        try:
            # Use PyRIT's filtering capabilities
            pieces = memory.get_prompt_request_pieces(
                labels=[f"dataset:{dataset_id}", f"user:{user_id}"],
                offset=offset,
                limit=limit
            )
            
            prompts = []
            for piece in pieces:
                if piece.original_value:
                    if include_metadata:
                        prompts.append({
                            "text": piece.original_value,
                            "metadata": piece.metadata or {}
                        })
                    else:
                        prompts.append(piece.original_value)
            
            # Get total count
            total_count = len(memory.get_prompt_request_pieces(
                labels=[f"dataset:{dataset_id}", f"user:{user_id}"]
            ))
            
            return prompts, total_count
            
        except Exception as e:
            logger.error(f"Failed to retrieve prompts from PyRIT memory: {e}")
            return [], 0
```

#### 1.3 Enhanced Configuration System with Adaptive Limits
```python
@dataclass
class DatasetImportConfig:
    """Enhanced configuration with adaptive and context-aware settings"""
    
    # Basic limits
    preview_limit: int = 10
    chunk_size: int = 1000  
    max_import_size: int = 0  # 0 = unlimited
    
    # PyRIT integration
    use_pyrit_memory: bool = True
    pyrit_batch_size: int = 100
    preserve_metadata: bool = True
    
    # Performance optimization
    enable_streaming: bool = True
    enable_progress_tracking: bool = True
    adaptive_chunk_size: bool = True
    max_memory_mb: int = 512
    
    # Error handling
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_partial_import: bool = True
    
    # User context
    enable_user_isolation: bool = True
    cleanup_on_failure: bool = True
    
    # Advanced features
    enable_duplicate_detection: bool = False
    enable_content_validation: bool = True
    enable_statistics_tracking: bool = True
    
    @classmethod
    def from_env(cls) -> "DatasetImportConfig":
        """Load configuration from environment variables"""
        return cls(
            preview_limit=int(os.getenv("DATASET_PREVIEW_LIMIT", 10)),
            chunk_size=int(os.getenv("DATASET_CHUNK_SIZE", 1000)),
            max_import_size=int(os.getenv("DATASET_MAX_IMPORT_SIZE", 0)),
            use_pyrit_memory=os.getenv("DATASET_USE_PYRIT_MEMORY", "true").lower() == "true",
            pyrit_batch_size=int(os.getenv("DATASET_PYRIT_BATCH_SIZE", 100)),
            preserve_metadata=os.getenv("DATASET_PRESERVE_METADATA", "true").lower() == "true",
            enable_streaming=os.getenv("DATASET_ENABLE_STREAMING", "true").lower() == "true",
            enable_progress_tracking=os.getenv("DATASET_ENABLE_PROGRESS", "true").lower() == "true",
            adaptive_chunk_size=os.getenv("DATASET_ADAPTIVE_CHUNK_SIZE", "true").lower() == "true",
            max_memory_mb=int(os.getenv("DATASET_MAX_MEMORY_MB", 512)),
            max_retries=int(os.getenv("DATASET_MAX_RETRIES", 3)),
            retry_delay=float(os.getenv("DATASET_RETRY_DELAY", 1.0)),
            enable_partial_import=os.getenv("DATASET_ENABLE_PARTIAL_IMPORT", "true").lower() == "true",
            enable_user_isolation=os.getenv("DATASET_ENABLE_USER_ISOLATION", "true").lower() == "true",
            cleanup_on_failure=os.getenv("DATASET_CLEANUP_ON_FAILURE", "true").lower() == "true",
            enable_duplicate_detection=os.getenv("DATASET_ENABLE_DUPLICATE_DETECTION", "false").lower() == "true",
            enable_content_validation=os.getenv("DATASET_ENABLE_CONTENT_VALIDATION", "true").lower() == "true",
            enable_statistics_tracking=os.getenv("DATASET_ENABLE_STATISTICS_TRACKING", "true").lower() == "true",
        )
    
    def get_effective_chunk_size(self, dataset_size: int, avg_prompt_size: int) -> int:
        """Calculate effective chunk size based on dataset characteristics"""
        if not self.adaptive_chunk_size:
            return self.chunk_size
            
        # Calculate optimal chunk size based on memory constraints
        memory_per_chunk = self.max_memory_mb * 1024 * 1024 * 0.7  # 70% of max memory
        calculated_size = int(memory_per_chunk / avg_prompt_size)
        
        # Clamp to reasonable bounds
        return max(100, min(calculated_size, self.chunk_size))
```

### Phase 2: Enhanced API Endpoints with Comprehensive Error Handling

#### 2.1 Streaming Dataset Import with Progress Tracking
```python
@router.post("/v1/datasets/{dataset_id}/import-pyrit")
async def import_pyrit_dataset_stream(
    dataset_id: str,
    request: PyRITDatasetImportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    config: DatasetImportConfig = Depends(DatasetImportConfig.from_env)
):
    """Import PyRIT dataset with streaming, progress tracking, and error handling"""
    
    # Validate dataset exists and user has access
    dataset = await get_dataset_by_id(dataset_id, current_user.id)
    if not dataset:
        raise HTTPException(404, f"Dataset {dataset_id} not found or access denied")
    
    # Validate dataset type and configuration
    try:
        await validate_pyrit_dataset_config(request.dataset_type, request.config)
    except ValueError as e:
        raise HTTPException(400, f"Invalid dataset configuration: {str(e)}")
    
    # Check for existing import jobs
    existing_job = await get_active_import_job(dataset_id, current_user.id)
    if existing_job:
        return {
            "job_id": existing_job.id,
            "status": existing_job.status,
            "message": "Import already in progress"
        }
    
    # Create import job with comprehensive metadata
    job = ImportJob(
        id=str(uuid.uuid4()),
        dataset_id=dataset_id,
        user_id=current_user.id,
        source_type="pyrit_native",
        dataset_type=request.dataset_type,
        config=request.config,
        import_config=config.__dict__,
        status="pending",
        created_at=datetime.utcnow(),
        estimated_total=await estimate_dataset_size(request.dataset_type, request.config),
        progress_percentage=0.0,
        processed_rows=0,
        error_details=None
    )
    await save_import_job(job)
    
    # Start background streaming import
    background_tasks.add_task(
        stream_import_pyrit_dataset,
        job.id,
        request.dataset_type,
        request.config,
        config,
        current_user.id
    )
    
    return {
        "job_id": job.id,
        "status": "processing",
        "estimated_total": job.estimated_total,
        "progress_url": f"/v1/datasets/import-jobs/{job.id}/progress"
    }

async def stream_import_pyrit_dataset(
    job_id: str,
    dataset_type: str, 
    pyrit_config: Dict,
    import_config: DatasetImportConfig,
    user_id: str
):
    """Background task for streaming PyRIT dataset import with comprehensive error handling"""
    job = None
    processor = None
    memory_bridge = None
    
    try:
        # Initialize components
        job = await get_import_job(job_id)
        processor = PyRITStreamProcessor()
        memory_bridge = PyRITMemoryBridge()
        
        # Update job status
        await update_job_status(job_id, "processing", "Starting dataset import...")
        
        # Initialize statistics
        stats = ImportStatistics(
            start_time=datetime.utcnow(),
            total_processed=0,
            total_stored_pyrit=0,
            total_stored_violentutf=0,
            chunks_processed=0,
            errors_encountered=0
        )
        
        # Progress callback function
        async def progress_callback(processed: int, total: int):
            progress = (processed / total * 100) if total > 0 else 0
            await update_job_progress(job_id, processed, total, progress)
            
            # Send real-time progress via WebSocket
            await send_progress_update(user_id, {
                "job_id": job_id,
                "processed": processed,
                "total": total,
                "progress": progress,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Stream process the dataset
        async for chunk in processor.process_pyrit_dataset_stream(
            dataset_type, 
            pyrit_config,
            import_config,
            progress_callback
        ):
            try:
                # Store in PyRIT memory (if enabled)
                if import_config.use_pyrit_memory:
                    stored_count = await memory_bridge.store_prompts_to_pyrit_memory(
                        chunk.prompts, 
                        chunk.metadata,
                        job_id,
                        user_id,
                        import_config.pyrit_batch_size
                    )
                    stats.total_stored_pyrit += stored_count
                
                # Store in ViolentUTF schema for API compatibility
                violentutf_count = await store_prompts_in_violentutf_db(
                    job_id, 
                    chunk.prompts, 
                    chunk.metadata,
                    user_id
                )
                stats.total_stored_violentutf += violentutf_count
                
                # Update statistics
                stats.total_processed += len(chunk.prompts)
                stats.chunks_processed += 1
                
                # Progress callback
                await progress_callback(stats.total_processed, job.estimated_total)
                
            except Exception as chunk_error:
                stats.errors_encountered += 1
                logger.error(f"Error processing chunk {chunk.chunk_index}: {chunk_error}")
                
                # Decide whether to continue or fail
                if not import_config.enable_partial_import:
                    raise
                
                # Log error and continue with next chunk
                await log_import_error(job_id, chunk.chunk_index, str(chunk_error))
        
        # Complete the job
        await complete_job(job_id, stats)
        
        # Send completion notification
        await send_completion_notification(user_id, {
            "job_id": job_id,
            "status": "completed",
            "stats": stats.__dict__,
            "message": f"Successfully imported {stats.total_processed} prompts"
        })
        
    except Exception as e:
        logger.error(f"Import job {job_id} failed: {e}")
        
        # Cleanup on failure (if enabled)
        if import_config.cleanup_on_failure and job:
            await cleanup_failed_import(job_id, user_id)
        
        # Update job status
        await fail_job(job_id, str(e))
        
        # Send error notification
        await send_error_notification(user_id, {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
            "message": "Import failed - check logs for details"
        })
```

#### 2.2 Enhanced Hybrid Retrieval System
```python
@router.get("/v1/datasets/{dataset_id}/prompts")
async def get_dataset_prompts_hybrid(
    dataset_id: str,
    offset: int = 0,
    limit: int = Query(100, le=1000),
    source: Literal["pyrit", "violentutf", "auto"] = "auto",
    include_metadata: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Get prompts with enhanced hybrid PyRIT/ViolentUTF retrieval"""
    
    # Validate access
    dataset = await get_dataset_by_id(dataset_id, current_user.id)
    if not dataset:
        raise HTTPException(404, "Dataset not found or access denied")
    
    retrieval_stats = {
        "source_attempted": [],
        "source_successful": None,
        "retrieval_time_ms": 0,
        "total_available": 0
    }
    
    start_time = time.time()
    
    # Try PyRIT memory first (if enabled)
    if source in ["pyrit", "auto"]:
        try:
            retrieval_stats["source_attempted"].append("pyrit")
            
            memory_bridge = PyRITMemoryBridge()
            prompts, total_count = await memory_bridge.get_prompts_from_pyrit_memory(
                dataset_id, 
                current_user.id,
                offset, 
                limit,
                include_metadata
            )
            
            if prompts:
                retrieval_stats["source_successful"] = "pyrit"
                retrieval_stats["total_available"] = total_count
                retrieval_stats["retrieval_time_ms"] = int((time.time() - start_time) * 1000)
                
                return {
                    "prompts": prompts,
                    "source": "pyrit_memory",
                    "pagination": {
                        "offset": offset,
                        "limit": limit,
                        "total": total_count,
                        "has_more": offset + limit < total_count
                    },
                    "metadata": {
                        "include_metadata": include_metadata,
                        "retrieval_stats": retrieval_stats
                    }
                }
                
        except Exception as e:
            logger.warning(f"PyRIT memory access failed for dataset {dataset_id}: {e}")
            retrieval_stats["pyrit_error"] = str(e)
    
    # Fallback to ViolentUTF database
    if source in ["violentutf", "auto"]:
        try:
            retrieval_stats["source_attempted"].append("violentutf")
            
            prompts, total_count = await get_violentutf_prompts(
                dataset_id, 
                current_user.id,
                offset, 
                limit,
                include_metadata
            )
            
            retrieval_stats["source_successful"] = "violentutf"
            retrieval_stats["total_available"] = total_count
            retrieval_stats["retrieval_time_ms"] = int((time.time() - start_time) * 1000)
            
            return {
                "prompts": prompts,
                "source": "violentutf_db", 
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "total": total_count,
                    "has_more": offset + limit < total_count
                },
                "metadata": {
                    "include_metadata": include_metadata,
                    "retrieval_stats": retrieval_stats
                }
            }
            
        except Exception as e:
            logger.error(f"ViolentUTF database access failed for dataset {dataset_id}: {e}")
            retrieval_stats["violentutf_error"] = str(e)
    
    # If all sources failed
    retrieval_stats["retrieval_time_ms"] = int((time.time() - start_time) * 1000)
    raise HTTPException(
        status_code=500,
        detail={
            "message": "Failed to retrieve prompts from all available sources",
            "retrieval_stats": retrieval_stats
        }
    )

@router.get("/v1/datasets/{dataset_id}/statistics")
async def get_dataset_statistics(
    dataset_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive dataset statistics from both storage systems"""
    
    # Validate access
    dataset = await get_dataset_by_id(dataset_id, current_user.id)
    if not dataset:
        raise HTTPException(404, "Dataset not found or access denied")
    
    stats = {
        "dataset_id": dataset_id,
        "sources": {},
        "summary": {
            "total_prompts": 0,
            "storage_systems": [],
            "last_updated": None,
            "import_history": []
        }
    }
    
    # Get PyRIT memory statistics
    try:
        memory_bridge = PyRITMemoryBridge()
        pyrit_prompts, pyrit_total = await memory_bridge.get_prompts_from_pyrit_memory(
            dataset_id, current_user.id, 0, 1  # Just get count
        )
        
        stats["sources"]["pyrit"] = {
            "available": True,
            "total_prompts": pyrit_total,
            "source_type": "pyrit_memory",
            "last_accessed": datetime.utcnow().isoformat()
        }
        
        stats["summary"]["total_prompts"] += pyrit_total
        stats["summary"]["storage_systems"].append("pyrit")
        
    except Exception as e:
        stats["sources"]["pyrit"] = {
            "available": False,
            "error": str(e),
            "source_type": "pyrit_memory"
        }
    
    # Get ViolentUTF database statistics
    try:
        violentutf_prompts, violentutf_total = await get_violentutf_prompts(
            dataset_id, current_user.id, 0, 1  # Just get count
        )
        
        stats["sources"]["violentutf"] = {
            "available": True,
            "total_prompts": violentutf_total,
            "source_type": "violentutf_db",
            "last_accessed": datetime.utcnow().isoformat()
        }
        
        stats["summary"]["total_prompts"] += violentutf_total
        stats["summary"]["storage_systems"].append("violentutf")
        
    except Exception as e:
        stats["sources"]["violentutf"] = {
            "available": False,
            "error": str(e),
            "source_type": "violentutf_db"
        }
    
    # Get import history
    try:
        import_jobs = await get_import_jobs_for_dataset(dataset_id, current_user.id)
        stats["summary"]["import_history"] = [
            {
                "job_id": job.id,
                "status": job.status,
                "processed_rows": job.processed_rows,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
            for job in import_jobs
        ]
        
        if import_jobs:
            stats["summary"]["last_updated"] = max(
                job.completed_at or job.created_at for job in import_jobs
            ).isoformat()
            
    except Exception as e:
        logger.warning(f"Could not retrieve import history: {e}")
    
    return stats
```

### Phase 3: Enhanced Backward Compatibility and Migration

#### 3.1 Smart Legacy API Support
```python
# Enhanced backward compatibility with gradual migration
async def _load_real_pyrit_dataset(
    dataset_type: str, 
    config: Dict[str, Any],
    limit: Optional[int] = None,
    user_id: Optional[str] = None
) -> List[str]:
    """Enhanced backward compatible PyRIT dataset loading"""
    
    # Check if new streaming system is enabled
    streaming_enabled = os.getenv("DATASET_ENABLE_STREAMING", "true").lower() == "true"
    
    # For preview/small loads or when streaming is disabled, use legacy logic
    if not streaming_enabled or (limit and limit <= 50):
        return await _load_real_pyrit_dataset_legacy(dataset_type, config, limit)
    
    # For larger loads, use streaming with legacy interface
    try:
        import_config = DatasetImportConfig.from_env()
        processor = PyRITStreamProcessor()
        all_prompts = []
        
        # Stream process but collect all results (for backward compatibility)
        async for chunk in processor.process_pyrit_dataset_stream(
            dataset_type, config, import_config
        ):
            all_prompts.extend(chunk.prompts)
            
            # Apply limit if specified
            if limit and len(all_prompts) >= limit:
                all_prompts = all_prompts[:limit]
                break
        
        return all_prompts
        
    except Exception as e:
        logger.warning(f"Streaming dataset loading failed, falling back to legacy: {e}")
        return await _load_real_pyrit_dataset_legacy(dataset_type, config, limit)

async def _load_real_pyrit_dataset_legacy(
    dataset_type: str, 
    config: Dict[str, Any],
    limit: Optional[int] = None
) -> List[str]:
    """Legacy PyRIT dataset loading with hardcoded limits (for compatibility)"""
    
    # This is the original implementation with 50-row limit
    # Keep for backward compatibility and gradual migration
    try:
        from pyrit.datasets import (
            fetch_harmbench_dataset,
            fetch_many_shot_jailbreaking_dataset,
            # ... other fetchers
        )
        
        dataset_fetchers = {
            "harmbench": fetch_harmbench_dataset,
            "many_shot_jailbreaking": fetch_many_shot_jailbreaking_dataset,
            # ... existing mapping
        }
        
        fetcher = dataset_fetchers.get(dataset_type)
        if not fetcher:
            raise ValueError(f"Unknown dataset type: {dataset_type}")
        
        # Call the PyRIT fetch function
        dataset = fetcher(**config)
        
        # Handle different return types (existing logic)
        prompts = []
        
        if dataset_type == "many_shot_jailbreaking":
            # Existing logic for many_shot_jailbreaking
            if isinstance(dataset, list):
                for item in dataset:
                    if isinstance(item, dict) and "user" in item:
                        prompts.append(item["user"])
                    else:
                        prompts.append(str(item))
                return prompts[:limit or 50]  # Apply limit
        
        elif dataset and hasattr(dataset, "prompts"):
            # Standard SeedPromptDataset format
            for seed_prompt in dataset.prompts:
                if hasattr(seed_prompt, "value"):
                    prompts.append(seed_prompt.value)
                elif hasattr(seed_prompt, "prompt"):
                    prompts.append(seed_prompt.prompt)
                else:
                    prompts.append(str(seed_prompt))
            
            return prompts[:limit or 50]  # Apply limit
        
        return []
        
    except Exception as e:
        logger.error(f"Legacy dataset loading failed: {e}")
        return []
```

#### 3.2 Configuration Migration and Environment Setup
```python
# Enhanced environment configuration
# Add to ai-tokens.env
DATASET_PREVIEW_LIMIT=10
DATASET_CHUNK_SIZE=1000
DATASET_MAX_IMPORT_SIZE=0  # 0 = unlimited
DATASET_USE_PYRIT_MEMORY=true
DATASET_PYRIT_BATCH_SIZE=100
DATASET_ENABLE_STREAMING=true
DATASET_PRESERVE_METADATA=true
DATASET_ADAPTIVE_CHUNK_SIZE=true
DATASET_MAX_MEMORY_MB=512
DATASET_MAX_RETRIES=3
DATASET_RETRY_DELAY=1.0
DATASET_ENABLE_PARTIAL_IMPORT=true
DATASET_ENABLE_USER_ISOLATION=true
DATASET_CLEANUP_ON_FAILURE=true
DATASET_ENABLE_DUPLICATE_DETECTION=false
DATASET_ENABLE_CONTENT_VALIDATION=true
DATASET_ENABLE_STATISTICS_TRACKING=true

# Migration flags
DATASET_ENABLE_LEGACY_MODE=false  # For gradual migration
DATASET_LEGACY_LIMIT=50  # For existing preview functionality
```

### Phase 4: Frontend Integration with Enhanced UX

#### 4.1 Enhanced Streamlit UI with Real-time Progress
```python
# Enhanced dataset import UI in 2_Configure_Datasets.py
def render_enhanced_dataset_import():
    """Enhanced dataset import UI with real-time progress tracking"""
    
    st.header("Enhanced Dataset Import")
    
    # Dataset type selection with improved info
    dataset_types = get_available_dataset_types()
    
    selected_type = st.selectbox(
        "Select Dataset Type",
        options=list(dataset_types.keys()),
        format_func=lambda x: f"{x} - {dataset_types[x]['description']}"
    )
    
    if selected_type:
        dataset_info = dataset_types[selected_type]
        
        # Show dataset information
        with st.expander("Dataset Information"):
            st.write(f"**Category:** {dataset_info['category']}")
            st.write(f"**Description:** {dataset_info['description']}")
            if dataset_info.get('estimated_size'):
                st.write(f"**Estimated Size:** {dataset_info['estimated_size']} prompts")
            if dataset_info.get('source_url'):
                st.write(f"**Source:** {dataset_info['source_url']}")
        
        # Configuration options
        config = {}
        if dataset_info.get('config_required'):
            st.subheader("Configuration")
            for param, options in dataset_info.get('available_configs', {}).items():
                if isinstance(options, list):
                    config[param] = st.selectbox(f"Select {param}", options)
                else:
                    config[param] = st.text_input(f"Enter {param}")
        
        # Advanced options
        with st.expander("Advanced Options"):
            col1, col2 = st.columns(2)
            
            with col1:
                max_prompts = st.number_input(
                    "Max Prompts to Import",
                    min_value=0,
                    value=0,
                    help="0 = Import all available prompts"
                )
                
                chunk_size = st.number_input(
                    "Chunk Size",
                    min_value=100,
                    max_value=10000,
                    value=1000,
                    help="Number of prompts to process in each batch"
                )
            
            with col2:
                use_pyrit_memory = st.checkbox(
                    "Store in PyRIT Memory",
                    value=True,
                    help="Store prompts in PyRIT's memory system for orchestrator use"
                )
                
                preserve_metadata = st.checkbox(
                    "Preserve Metadata",
                    value=True,
                    help="Preserve dataset metadata and labels"
                )
        
        # Import button
        if st.button("Start Import", type="primary"):
            # Validate configuration
            try:
                validate_import_config(selected_type, config)
            except ValueError as e:
                st.error(f"Configuration error: {e}")
                return
            
            # Start import process
            import_request = {
                "dataset_type": selected_type,
                "config": config,
                "max_prompts": max_prompts if max_prompts > 0 else None,
                "chunk_size": chunk_size,
                "use_pyrit_memory": use_pyrit_memory,
                "preserve_metadata": preserve_metadata
            }
            
            # Create progress containers
            progress_container = st.container()
            
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                stats_container = st.empty()
                
                # Start import and monitor progress
                success = monitor_dataset_import(
                    import_request,
                    progress_bar,
                    status_text,
                    stats_container
                )
                
                if success:
                    st.success("✅ Dataset import completed successfully!")
                    
                    # Show import statistics
                    show_import_statistics(selected_type)
                    
                    # Offer next steps
                    st.info("💡 Your dataset is now ready for use in orchestrators!")
                    if st.button("View Dataset"):
                        st.experimental_rerun()
                else:
                    st.error("❌ Dataset import failed. Check the logs for details.")

def monitor_dataset_import(
    import_request: Dict,
    progress_bar: st.progress,
    status_text: st.empty,
    stats_container: st.empty
) -> bool:
    """Monitor dataset import with real-time progress updates"""
    
    # Start import job
    api_client = ViolentUTFAPIClient()
    response = api_client.start_dataset_import(import_request)
    
    if not response.get("job_id"):
        st.error("Failed to start import job")
        return False
    
    job_id = response["job_id"]
    
    # Monitor progress with WebSocket
    try:
        with create_websocket_connection(job_id) as ws:
            while True:
                # Get progress update
                progress_data = ws.recv()
                
                if not progress_data:
                    break
                
                # Update UI
                progress = progress_data.get("progress", 0)
                processed = progress_data.get("processed", 0)
                total = progress_data.get("total", 0)
                status = progress_data.get("status", "processing")
                
                # Update progress bar
                progress_bar.progress(progress / 100)
                
                # Update status text
                status_text.text(
                    f"Status: {status} - Processed: {processed:,} / {total:,} prompts"
                )
                
                # Update statistics
                if progress_data.get("stats"):
                    stats = progress_data["stats"]
                    with stats_container.container():
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Processed", f"{processed:,}")
                        
                        with col2:
                            st.metric("Success Rate", f"{stats.get('success_rate', 0):.1f}%")
                        
                        with col3:
                            st.metric("Speed", f"{stats.get('prompts_per_second', 0):.1f} p/s")
                
                # Check for completion
                if status in ["completed", "failed"]:
                    return status == "completed"
                
                # Small delay to prevent UI flickering
                time.sleep(0.1)
                
    except Exception as e:
        st.error(f"Error monitoring import progress: {e}")
        return False
    
    return False
```

## Implementation Timeline

### Week 1: Core Infrastructure
- [ ] Implement enhanced PyRITStreamProcessor with memory optimization
- [ ] Create PyRITMemoryBridge with user context support
- [ ] Update configuration system with adaptive settings
- [ ] Remove hardcoded 50-row limits from all existing functions
- [ ] Add comprehensive error handling and logging

### Week 2: API Enhancement
- [ ] Implement streaming import endpoints with progress tracking
- [ ] Add hybrid retrieval system with fallback support
- [ ] Create background job processing with real-time updates
- [ ] Add WebSocket support for progress notifications
- [ ] Implement dataset statistics and monitoring endpoints

### Week 3: Frontend & UX
- [ ] Update Streamlit UI with enhanced import interface
- [ ] Add real-time progress monitoring with WebSocket
- [ ] Implement dataset statistics dashboard
- [ ] Add import history and job management
- [ ] Create advanced configuration options

### Week 4: Testing & Optimization
- [ ] Comprehensive testing with all PyRIT dataset types
- [ ] Performance optimization and memory usage testing
- [ ] Load testing with large datasets (100k+ prompts)
- [ ] Integration testing with orchestrator workflows
- [ ] Documentation and migration guides

## Enhanced Success Metrics

### Functional Requirements
- [ ] Import 100k+ rows from PyRIT datasets without 50-row limitation
- [ ] Maintain 100% compatibility with existing PyRIT memory operations
- [ ] Preserve all PyRIT dataset metadata and relationships
- [ ] Support both streaming and legacy import modes
- [ ] Zero data loss during import process
- [ ] Support all PyRIT dataset types (harmbench, many_shot_jailbreaking, etc.)

### Performance Requirements
- [ ] Achieve <2s response time for paginated retrieval
- [ ] Process 1000+ prompts per second during import
- [ ] Memory usage stays below 512MB per import job
- [ ] Support concurrent imports by multiple users
- [ ] 99.9% uptime during import operations

### User Experience Requirements
- [ ] Real-time progress updates with <1s latency
- [ ] Graceful error handling with recovery options
- [ ] Intuitive UI with clear progress indicators
- [ ] Comprehensive dataset statistics and monitoring
- [ ] Easy migration from legacy system

### Security & Reliability Requirements
- [ ] User isolation between import jobs
- [ ] Secure handling of user credentials and data
- [ ] Audit logging for all import operations
- [ ] Automatic cleanup of failed imports
- [ ] Data validation and duplicate detection

## Risk Mitigation

### Technical Risks
- **PyRIT API Changes**: Implement adapter pattern for PyRIT interface
- **Memory Exhaustion**: Implement adaptive chunking and memory monitoring
- **Database Conflicts**: Use separate memory instances per user/job
- **Network Failures**: Implement retry logic with exponential backoff

### Operational Risks
- **Data Loss**: Implement transaction rollback and backup strategies
- **Performance Degradation**: Monitor system resources and implement circuit breakers
- **User Experience**: Provide clear error messages and recovery options
- **Migration Issues**: Maintain backward compatibility during transition

This improved plan provides a comprehensive, production-ready solution that addresses all aspects of the dataset import limitation while maintaining harmony with both PyRIT's memory system and ViolentUTF's architecture.