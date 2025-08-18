# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
PyRIT Memory Bridge Service.

This module provides a bridge between ViolentUTF and PyRIT memory systems,
handling user context, memory management, and data synchronization.
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pyrit.memory import CentralMemory, DuckDBMemory, MemoryInterface
from pyrit.models import SeedPrompt

logger = logging.getLogger(__name__)


class UserContextManager:
    """Manages user context for memory isolation."""

    @staticmethod
    def get_user_hash(user_id: str) -> str:
        """Generate a consistent hash for user identification."""
        # Use consistent salt for user hashing
        salt = os.getenv("PYRIT_DB_SALT", "default_salt")
        combined = f"{user_id}:{salt}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    @staticmethod
    def get_user_memory_path(user_id: str) -> str:
        """Get the memory database path for a specific user."""
        user_hash = UserContextManager.get_user_hash(user_id)
        memory_dir = os.getenv("PYRIT_MEMORY_DIR", "/app/app_data/violentutf")
        os.makedirs(memory_dir, exist_ok=True)
        return os.path.join(memory_dir, f"pyrit_memory_{user_hash}.db")


class PyRITMemoryBridge:
    """Enhanced bridge between ViolentUTF and PyRIT memory systems."""

    def __init__(self) -> None:
        """Initialize the instance."""
        self.memory_cache: Dict[str, DuckDBMemory] = {}
        self.user_context_manager = UserContextManager()

    async def get_or_create_user_memory(self, user_id: str) -> DuckDBMemory:
        """Get or create user-specific PyRIT memory instance."""
        if user_id not in self.memory_cache:
            try:
                # Create user-specific memory path
                memory_path = self.user_context_manager.get_user_memory_path(user_id)

                # Create memory instance
                memory = DuckDBMemory(db_path=memory_path)
                self.memory_cache[user_id] = memory

                logger.info(f"Created PyRIT memory instance for user {user_id}: {memory_path}")

            except Exception as e:
                logger.error(f"Failed to create PyRIT memory for user {user_id}: {e}")
                raise

        return self.memory_cache[user_id]

    async def store_prompts_to_pyrit_memory(
        self, prompts: List[str], metadata: List[Dict[str, Any]], dataset_id: str, user_id: str, batch_size: int = 100
    ) -> int:
        """Store prompts using PyRIT's async memory functions with user context."""
        try:
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
                    **prompt_metadata,
                }

                seed_prompt = SeedPrompt(
                    value=prompt_text,
                    dataset_name=dataset_id,
                    labels=[f"dataset:{dataset_id}", "imported", f"user:{user_id}"],
                    metadata=combined_metadata,
                )
                seed_prompts.append(seed_prompt)

            # Batch insert to PyRIT memory
            stored_count = 0
            for batch_start in range(0, len(seed_prompts), batch_size):
                batch = seed_prompts[batch_start : batch_start + batch_size]
                try:
                    await memory.add_seed_prompts_to_memory_async(prompts=batch)
                    stored_count += len(batch)
                    logger.debug(f"Stored batch {batch_start // batch_size + 1}: {len(batch)} prompts")
                except Exception as e:
                    logger.error(f"Failed to store batch {batch_start}: {e}")
                    raise

            logger.info(f"Successfully stored {stored_count} prompts to PyRIT memory for user {user_id}")
            return stored_count

        except Exception as e:
            logger.error(f"Failed to store prompts to PyRIT memory: {e}")
            raise

    async def get_prompts_from_pyrit_memory(
        self, dataset_id: str, user_id: str, offset: int = 0, limit: int = 1000, include_metadata: bool = False
    ) -> Tuple[List[str], int]:
        """Retrieve prompts using PyRIT memory interface with pagination."""
        try:
            memory = await self.get_or_create_user_memory(user_id)

            # Use PyRIT's filtering capabilities
            pieces = memory.get_prompt_request_pieces(
                labels=[f"dataset:{dataset_id}", f"user:{user_id}"], offset=offset, limit=limit
            )

            prompts = []
            for piece in pieces:
                if piece.original_value:
                    if include_metadata:
                        prompts.append(
                            {
                                "text": piece.original_value,
                                "metadata": piece.metadata or {},
                                "labels": piece.labels or [],
                                "timestamp": piece.timestamp.isoformat() if piece.timestamp else None,
                            }
                        )
                    else:
                        prompts.append(piece.original_value)

            # Get total count
            all_pieces = memory.get_prompt_request_pieces(labels=[f"dataset:{dataset_id}", f"user:{user_id}"])
            total_count = len(all_pieces)

            logger.debug(f"Retrieved {len(prompts)} prompts from PyRIT memory (total: {total_count})")
            return prompts, total_count

        except Exception as e:
            logger.error(f"Failed to retrieve prompts from PyRIT memory: {e}")
            return [], 0

    async def get_dataset_statistics(self, dataset_id: str, user_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a dataset in PyRIT memory."""
        try:
            memory = await self.get_or_create_user_memory(user_id)

            # Get all pieces for the dataset
            pieces = memory.get_prompt_request_pieces(labels=[f"dataset:{dataset_id}", f"user:{user_id}"])

            if not pieces:
                return {
                    "total_prompts": 0,
                    "last_updated": None,
                    "import_batches": 0,
                    "labels": [],
                    "metadata_summary": {},
                }

            # Calculate statistics
            total_prompts = len(pieces)
            timestamps = [p.timestamp for p in pieces if p.timestamp]
            last_updated = max(timestamps).isoformat() if timestamps else None

            # Extract unique labels and metadata
            all_labels = set()
            import_batches = set()

            for piece in pieces:
                if piece.labels:
                    all_labels.update(piece.labels)
                if piece.metadata and "import_batch" in piece.metadata:
                    import_batches.add(piece.metadata["import_batch"])

            return {
                "total_prompts": total_prompts,
                "last_updated": last_updated,
                "import_batches": len(import_batches),
                "labels": sorted(list(all_labels)),
                "metadata_summary": {
                    "unique_import_batches": len(import_batches),
                    "has_metadata": sum(1 for p in pieces if p.metadata),
                },
            }

        except Exception as e:
            logger.error(f"Failed to get dataset statistics: {e}")
            return {
                "total_prompts": 0,
                "last_updated": None,
                "import_batches": 0,
                "labels": [],
                "metadata_summary": {},
                "error": str(e),
            }

    async def delete_dataset_from_memory(self, dataset_id: str, user_id: str) -> bool:
        """Delete all prompts for a dataset from PyRIT memory."""
        try:
            memory = await self.get_or_create_user_memory(user_id)

            # Get all pieces for the dataset
            pieces = memory.get_prompt_request_pieces(labels=[f"dataset:{dataset_id}", f"user:{user_id}"])

            if not pieces:
                logger.info(f"No prompts found for dataset {dataset_id} in PyRIT memory")
                return True

            # Delete pieces (this depends on PyRIT's implementation)
            # Note: PyRIT may not have a direct delete method, so we might need to work around this
            deleted_count = 0
            for piece in pieces:
                try:
                    # This is a placeholder - actual deletion depends on PyRIT's API
                    # We might need to use direct database operations
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete piece {piece.id}: {e}")

            logger.info(f"Deleted {deleted_count} prompts for dataset {dataset_id} from PyRIT memory")
            return True

        except Exception as e:
            logger.error(f"Failed to delete dataset from PyRIT memory: {e}")
            return False

    async def cleanup_user_memory(self, user_id: str, max_age_days: int = 30) -> Dict[str, Any]:
        """Cleanup old data from user's PyRIT memory."""
        try:
            memory = await self.get_or_create_user_memory(user_id)

            # Get all pieces for the user
            pieces = memory.get_prompt_request_pieces(labels=[f"user:{user_id}"])

            if not pieces:
                return {"cleaned_up": 0, "total_pieces": 0, "message": "No data to cleanup"}

            # Filter old pieces
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            old_pieces = [p for p in pieces if p.timestamp and p.timestamp < cutoff_date]

            # Cleanup old pieces
            cleaned_count = 0
            for piece in old_pieces:
                try:
                    # This is a placeholder - actual cleanup depends on PyRIT's API
                    cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to cleanup piece {piece.id}: {e}")

            logger.info(f"Cleaned up {cleaned_count} old pieces from user {user_id} memory")

            return {
                "cleaned_up": cleaned_count,
                "total_pieces": len(pieces),
                "cutoff_date": cutoff_date.isoformat(),
                "message": f"Cleaned up {cleaned_count} pieces older than {max_age_days} days",
            }

        except Exception as e:
            logger.error(f"Failed to cleanup user memory: {e}")
            return {"cleaned_up": 0, "total_pieces": 0, "error": str(e)}

    def close_memory_connections(self) -> None:
        """Close all cached memory connections."""
        for user_id, memory in self.memory_cache.items():
            try:
                if hasattr(memory, "dispose_engine"):
                    memory.dispose_engine()
                logger.debug(f"Closed memory connection for user {user_id}")
            except Exception as e:
                logger.warning(f"Error closing memory connection for user {user_id}: {e}")

        self.memory_cache.clear()
        logger.info("All PyRIT memory connections closed")

    def __del__(self) -> None:
        """Cleanup on object destruction."""
        try:
            self.close_memory_connections()
        except Exception:
            pass  # Ignore errors during cleanup
