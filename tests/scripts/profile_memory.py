from typing import Any

#!/usr/bin/env python3
# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Memory profiling script for ViolentUTF components."""

import time
import tracemalloc


def profile_sample_operation() -> Any:
    """Sample operation to profile memory usage."""
    # Start tracing.
    tracemalloc.start()

    # Sample operation - create some data
    data = []
    for i in range(1000):
        data.append({"id": i, "value": f"item_{i}" * 10})

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory usage: {current / 1024 / 1024:.2f} MB")
    print(f"Peak memory usage: {peak / 1024 / 1024:.2f} MB")

    tracemalloc.stop()
    return data


if __name__ == "__main__":
    print("ViolentUTF Memory Profiling")
    print("-" * 30)
    print("Running sample memory profiling...")
    profile_sample_operation()
    print("\nNote: Implement actual component profiling as needed")
