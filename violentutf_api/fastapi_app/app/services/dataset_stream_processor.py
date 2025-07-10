"""
Enhanced PyRIT Dataset Stream Processor

This module provides streaming capabilities for PyRIT datasets with memory optimization,
intelligent chunking, and comprehensive error handling.
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

from pyrit.memory import CentralMemory, MemoryInterface

logger = logging.getLogger(__name__)


@dataclass
class DatasetChunk:
    """Container for a chunk of dataset prompts with metadata"""

    prompts: List[str]
    metadata: List[Dict[str, Any]]
    chunk_index: int
    total_processed: int
    estimated_remaining: Optional[int] = None


@dataclass
class DatasetImportStats:
    """Statistics tracking for dataset import operations"""

    start_time: datetime
    total_processed: int = 0
    total_estimated: int = 0
    chunks_processed: int = 0
    errors_encountered: int = 0
    average_chunk_size: float = 0.0
    processing_rate: float = 0.0  # prompts per second


class DatasetFetchError(Exception):
    """Custom exception for dataset fetching errors"""

    pass


class PyRITStreamProcessor:
    """Enhanced streaming processor with memory-aware chunking"""

    def __init__(self, memory_interface: Optional[MemoryInterface] = None):
        self.memory = memory_interface or CentralMemory.get_memory_instance()
        self.chunk_size = int(os.getenv("DATASET_CHUNK_SIZE", 1000))
        self.max_memory_mb = int(os.getenv("DATASET_MAX_MEMORY_MB", 512))
        self.max_retries = int(os.getenv("DATASET_MAX_RETRIES", 3))
        self.retry_delay = float(os.getenv("DATASET_RETRY_DELAY", 1.0))

    async def process_pyrit_dataset_stream(
        self,
        dataset_type: str,
        config: Dict[str, Any],
        max_prompts: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> AsyncIterator[DatasetChunk]:
        """Stream process PyRIT datasets with intelligent chunking"""

        logger.info(f"Starting stream processing for dataset: {dataset_type}")

        # Initialize statistics
        stats = DatasetImportStats(start_time=datetime.utcnow(), total_estimated=max_prompts or 0)

        try:
            # Pre-validate dataset availability
            await self._validate_dataset_access(dataset_type, config)

            # Get the original PyRIT dataset (unlimited)
            dataset = await self._fetch_full_pyrit_dataset(dataset_type, config)

            # Calculate optimal chunk size based on dataset characteristics
            optimal_chunk_size = self._calculate_optimal_chunk_size(dataset)

            # Stream prompts in intelligent chunks
            prompts_processed = 0
            chunk_data = []
            chunk_metadata = []

            async for prompt_info in self._extract_prompts_with_metadata(dataset):
                chunk_data.append(prompt_info["text"])
                chunk_metadata.append(prompt_info["metadata"])
                prompts_processed += 1

                # Yield chunk when optimal size reached
                if len(chunk_data) >= optimal_chunk_size:
                    chunk = DatasetChunk(
                        prompts=chunk_data,
                        metadata=chunk_metadata,
                        chunk_index=stats.chunks_processed,
                        total_processed=prompts_processed,
                        estimated_remaining=(max_prompts - prompts_processed) if max_prompts else None,
                    )

                    yield chunk

                    # Update statistics
                    stats.chunks_processed += 1
                    stats.total_processed = prompts_processed
                    stats.average_chunk_size = prompts_processed / stats.chunks_processed

                    # Calculate processing rate
                    elapsed = (datetime.utcnow() - stats.start_time).total_seconds()
                    stats.processing_rate = prompts_processed / elapsed if elapsed > 0 else 0

                    # Reset chunk data
                    chunk_data = []
                    chunk_metadata = []

                    # Progress callback
                    if progress_callback:
                        await progress_callback(prompts_processed, max_prompts or 0)

                # Stop if max limit reached
                if max_prompts and prompts_processed >= max_prompts:
                    logger.info(f"Reached maximum import limit: {max_prompts}")
                    break

            # Yield remaining prompts
            if chunk_data:
                chunk = DatasetChunk(
                    prompts=chunk_data,
                    metadata=chunk_metadata,
                    chunk_index=stats.chunks_processed,
                    total_processed=prompts_processed,
                    estimated_remaining=0,
                )
                yield chunk

                stats.chunks_processed += 1
                stats.total_processed = prompts_processed

        except Exception as e:
            logger.error(f"Stream processing failed for {dataset_type}: {e}")
            raise DatasetFetchError(f"Failed to process dataset {dataset_type}: {str(e)}")

        logger.info(f"Completed stream processing: {stats.total_processed} prompts in {stats.chunks_processed} chunks")

    def _calculate_optimal_chunk_size(self, dataset: Any) -> int:
        """Calculate optimal chunk size based on dataset characteristics"""
        try:
            # Try to get dataset size information
            if hasattr(dataset, "prompts") and hasattr(dataset.prompts, "__len__"):
                dataset_size = len(dataset.prompts)

                # Sample a few prompts to estimate average size
                sample_size = min(10, dataset_size)
                if sample_size > 0:
                    sample_prompts = dataset.prompts[:sample_size]
                    total_size = sum(len(str(p)) for p in sample_prompts)
                    avg_prompt_size = total_size / sample_size

                    # Calculate chunk size to stay within memory limits
                    target_chunk_memory = self.max_memory_mb * 1024 * 1024 * 0.7  # 70% of max memory
                    calculated_chunk_size = int(target_chunk_memory / avg_prompt_size)

                    # Clamp to reasonable bounds
                    optimal_size = max(100, min(calculated_chunk_size, self.chunk_size))

                    logger.debug(
                        f"Calculated optimal chunk size: {optimal_size} (avg_prompt_size: {avg_prompt_size:.0f})"
                    )
                    return optimal_size

        except Exception as e:
            logger.debug(f"Could not calculate optimal chunk size: {e}")

        return self.chunk_size

    async def _validate_dataset_access(self, dataset_type: str, config: Dict[str, Any]) -> None:
        """Validate that the dataset can be accessed with the given configuration"""
        try:
            # Check if dataset type is supported
            supported_types = {
                "aya_redteaming",
                "harmbench",
                "adv_bench",
                "xstest",
                "pku_safe_rlhf",
                "decoding_trust_stereotypes",
                "many_shot_jailbreaking",
                "forbidden_questions",
                "seclists_bias_testing",
                "wmdp",
            }

            if dataset_type not in supported_types:
                raise ValueError(f"Unsupported dataset type: {dataset_type}")

            # Validate configuration parameters
            if not isinstance(config, dict):
                raise ValueError("Configuration must be a dictionary")

            logger.debug(f"Dataset validation passed for {dataset_type}")

        except Exception as e:
            raise DatasetFetchError(f"Dataset validation failed: {str(e)}")

    async def _fetch_full_pyrit_dataset(self, dataset_type: str, config: Dict[str, Any]) -> Any:
        """Fetch complete PyRIT dataset without 50-row limit"""
        try:
            # Import all PyRIT dataset functions
            from pyrit.datasets import (
                fetch_adv_bench_dataset,
                fetch_aya_redteaming_dataset,
                fetch_decoding_trust_stereotypes_dataset,
                fetch_forbidden_questions_dataset,
                fetch_harmbench_dataset,
                fetch_many_shot_jailbreaking_dataset,
                fetch_pku_safe_rlhf_dataset,
                fetch_seclists_bias_testing_dataset,
                fetch_wmdp_dataset,
                fetch_xstest_dataset,
            )

            dataset_fetchers = {
                "aya_redteaming": fetch_aya_redteaming_dataset,
                "harmbench": fetch_harmbench_dataset,
                "adv_bench": fetch_adv_bench_dataset,
                "xstest": fetch_xstest_dataset,
                "pku_safe_rlhf": fetch_pku_safe_rlhf_dataset,
                "decoding_trust_stereotypes": fetch_decoding_trust_stereotypes_dataset,
                "many_shot_jailbreaking": fetch_many_shot_jailbreaking_dataset,
                "forbidden_questions": fetch_forbidden_questions_dataset,
                "seclists_bias_testing": fetch_seclists_bias_testing_dataset,
                "wmdp": fetch_wmdp_dataset,
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

    async def _fetch_with_retry(self, fetcher: Callable, config: Dict, max_retries: int = None) -> Any:
        """Fetch dataset with retry logic and exponential backoff"""
        max_retries = max_retries or self.max_retries

        for attempt in range(max_retries):
            try:
                # Execute the fetcher function
                if asyncio.iscoroutinefunction(fetcher):
                    result = await fetcher(**config)
                else:
                    # Run synchronous fetcher in thread pool
                    result = await asyncio.get_event_loop().run_in_executor(None, lambda: fetcher(**config))

                logger.debug(f"Dataset fetch successful on attempt {attempt + 1}")
                return result

            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Dataset fetch failed after {max_retries} attempts: {e}")
                    raise

                # Exponential backoff
                wait_time = self.retry_delay * (2**attempt)
                logger.warning(f"Dataset fetch attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

    def _clean_config_for_fetcher(self, fetcher: Callable, config: Dict[str, Any]) -> Dict[str, Any]:
        """Clean configuration to only include parameters supported by the fetcher"""
        import inspect

        try:
            # Get the function signature
            sig = inspect.signature(fetcher)
            supported_params = set(sig.parameters.keys())

            # Filter config to only include supported parameters
            clean_config = {k: v for k, v in config.items() if k in supported_params}

            logger.debug(f"Cleaned config: {clean_config}")
            return clean_config

        except Exception as e:
            logger.warning(f"Could not clean config for fetcher: {e}")
            return config  # Return original config if cleaning fails

    async def _extract_prompts_with_metadata(self, dataset: Any) -> AsyncIterator[Dict[str, Any]]:
        """Extract prompts with metadata from PyRIT dataset"""
        try:
            # Handle different dataset return types
            if hasattr(dataset, "prompts"):
                # Standard SeedPromptDataset format
                for i, prompt in enumerate(dataset.prompts):
                    if hasattr(prompt, "value"):
                        yield {
                            "text": prompt.value,
                            "metadata": {
                                "dataset_name": getattr(prompt, "dataset_name", ""),
                                "labels": getattr(prompt, "labels", []),
                                "source": "pyrit_dataset",
                            },
                        }
                    elif hasattr(prompt, "prompt"):
                        yield {"text": prompt.prompt, "metadata": {"source": "pyrit_dataset"}}
                    else:
                        yield {"text": str(prompt), "metadata": {"source": "pyrit_dataset"}}

                    # Yield control periodically to prevent blocking
                    if i % 100 == 0:
                        await asyncio.sleep(0)

            elif isinstance(dataset, list):
                # List format (e.g., many_shot_jailbreaking)
                for i, item in enumerate(dataset):
                    if isinstance(item, dict):
                        # Extract text from dict
                        text = item.get("user") or item.get("prompt") or str(item)
                        yield {
                            "text": text,
                            "metadata": {"index": i, "source": "pyrit_dataset", "original_format": "dict"},
                        }
                    else:
                        yield {
                            "text": str(item),
                            "metadata": {"index": i, "source": "pyrit_dataset", "original_format": type(item).__name__},
                        }

                    # Yield control periodically to prevent blocking
                    if i % 100 == 0:
                        await asyncio.sleep(0)

            elif hasattr(dataset, "questions"):
                # WMDP dataset format
                for i, question in enumerate(dataset.questions):
                    if hasattr(question, "question"):
                        yield {
                            "text": question.question,
                            "metadata": {"index": i, "source": "wmdp_dataset", "question_type": "question"},
                        }
                    elif hasattr(question, "value"):
                        yield {
                            "text": question.value,
                            "metadata": {"index": i, "source": "wmdp_dataset", "question_type": "value"},
                        }
                    else:
                        yield {
                            "text": str(question),
                            "metadata": {"index": i, "source": "wmdp_dataset", "question_type": "unknown"},
                        }

                    # Yield control periodically to prevent blocking
                    if i % 100 == 0:
                        await asyncio.sleep(0)
            else:
                logger.warning(f"Unknown dataset format: {type(dataset)}")

        except Exception as e:
            logger.error(f"Error extracting prompts from dataset: {e}")
            raise DatasetFetchError(f"Could not extract prompts: {str(e)}")
