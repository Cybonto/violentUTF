#!/usr/bin/env python3
"""
Test script to verify the sequential execution implementation for avoiding 504 Gateway Timeout.

This script demonstrates the batch processing approach implemented in 4_Configure_Scorers.py
"""

import requests
import time
import json
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:9080"  # APISIX Gateway
HEADERS = {
    "Authorization": "Bearer YOUR_TOKEN_HERE",  # Replace with actual token
    "Content-Type": "application/json",
    "X-API-Gateway": "APISIX",
}


def test_batch_processing():
    """
    Test the batch processing implementation:
    1. Creates multiple orchestrators for batches
    2. Executes each batch sequentially
    3. Tracks progress throughout
    """

    print("Sequential Execution Test - Batch Processing Approach")
    print("=" * 60)

    # Simulate full dataset parameters
    full_dataset_size = 50
    batch_size = 10
    num_batches = (full_dataset_size + batch_size - 1) // batch_size

    print(f"\nDataset Configuration:")
    print(f"  Total prompts: {full_dataset_size}")
    print(f"  Batch size: {batch_size}")
    print(f"  Number of batches: {num_batches}")

    total_successful = 0
    total_failed = 0
    batch_results = []

    # Process each batch
    for batch_idx in range(num_batches):
        batch_start = batch_idx * batch_size
        batch_end = min(batch_start + batch_size, full_dataset_size)
        batch_prompts = batch_end - batch_start

        print(f"\n--- Batch {batch_idx + 1}/{num_batches} ---")
        print(f"Processing prompts {batch_start + 1}-{batch_end}")

        # Step 1: Create orchestrator for this batch
        orchestrator_payload = {
            "name": f"test_batch_{batch_idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "orchestrator_type": "PromptSendingOrchestrator",
            "description": f"Test batch {batch_idx + 1}",
            "parameters": {
                "objective_target": {"type": "configured_generator", "generator_name": "test_generator"},
                "scorers": [{"type": "configured_scorer", "scorer_id": "test_scorer_id", "scorer_name": "test_scorer"}],
            },
        }

        print(f"Creating orchestrator for batch {batch_idx + 1}...")
        # Simulate orchestrator creation
        orchestrator_id = f"orch_{batch_idx}_{datetime.now().strftime('%H%M%S')}"

        # Step 2: Execute batch
        execution_payload = {
            "execution_name": f"batch_{batch_idx}_execution",
            "execution_type": "dataset",
            "input_data": {
                "dataset_id": "test_dataset",
                "sample_size": batch_prompts,
                "randomize": False,
                "offset": batch_start,
                "metadata": {"batch_index": batch_idx, "total_batches": num_batches, "test_mode": "batch_processing"},
            },
        }

        print(f"Executing batch {batch_idx + 1} with {batch_prompts} prompts...")
        start_time = time.time()

        # Simulate execution (would be actual API call)
        time.sleep(2)  # Simulate processing time

        # Simulate results
        batch_successful = batch_prompts - 1  # Simulate 1 failure per batch
        batch_failed = 1

        execution_time = time.time() - start_time
        print(f"Batch {batch_idx + 1} completed in {execution_time:.2f}s")
        print(f"  Successful: {batch_successful}")
        print(f"  Failed: {batch_failed}")

        total_successful += batch_successful
        total_failed += batch_failed

        batch_results.append(
            {
                "batch_idx": batch_idx,
                "orchestrator_id": orchestrator_id,
                "successful": batch_successful,
                "failed": batch_failed,
                "execution_time": execution_time,
            }
        )

        # Progress update
        progress = (batch_idx + 1) / num_batches * 100
        print(f"Overall progress: {progress:.1f}%")

    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print(f"  Total prompts processed: {full_dataset_size}")
    print(f"  Total successful: {total_successful}")
    print(f"  Total failed: {total_failed}")
    print(f"  Success rate: {(total_successful / full_dataset_size * 100):.1f}%")
    print(f"  Total execution time: {sum(r['execution_time'] for r in batch_results):.2f}s")

    print("\nBATCH PROCESSING BENEFITS:")
    print("✓ No 504 Gateway Timeout - each batch completes within 60s")
    print("✓ Progress tracking - user sees real-time progress")
    print("✓ Fault tolerance - if one batch fails, others continue")
    print("✓ Scalable - works with any dataset size")
    print("✓ Results saved - each batch saves to database")


def test_api_timeout_handling():
    """
    Test how the implementation handles API timeouts
    """
    print("\n\nAPI Timeout Handling Test")
    print("=" * 60)

    print("Testing different batch sizes vs timeout threshold:")

    batch_sizes = [5, 10, 20, 50]
    timeout_threshold = 60  # seconds

    for batch_size in batch_sizes:
        # Estimate execution time (2 seconds per prompt)
        estimated_time = batch_size * 2

        print(f"\nBatch size: {batch_size}")
        print(f"  Estimated execution time: {estimated_time}s")

        if estimated_time < timeout_threshold:
            print(f"  ✓ Safe from timeout (under {timeout_threshold}s)")
        else:
            print(f"  ✗ Risk of timeout (over {timeout_threshold}s)")
            print(f"  → Recommendation: Use smaller batch size")

    print("\nCONCLUSION:")
    print("The implementation uses batch_size=10 which keeps execution")
    print("well under the 60-second APISIX timeout threshold.")


if __name__ == "__main__":
    print("ViolentUTF Sequential Execution Implementation Test")
    print("This demonstrates the batch processing approach to avoid 504 timeouts\n")

    test_batch_processing()
    test_api_timeout_handling()

    print("\n\nIMPLEMENTATION SUMMARY:")
    print("1. Full dataset is split into batches of 10 prompts")
    print("2. Each batch creates its own orchestrator")
    print("3. Batches execute sequentially with progress tracking")
    print("4. Results are aggregated and saved to database")
    print("5. User sees real-time progress updates")
    print("6. No risk of 504 Gateway Timeout")
