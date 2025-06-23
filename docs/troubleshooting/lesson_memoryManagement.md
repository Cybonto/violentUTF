# Lesson on Memory Management

This document provides guidance on memory management strategies in ViolentUTF, with enhanced coverage of the new persistent dataset collections, PyRIT memory integration, and optimization techniques for large-scale red-teaming operations.

## Enhanced Memory Features in ViolentUTF

### New Persistent Dataset Collections
ViolentUTF now provides persistent dataset storage across sessions using named collections in PyRIT memory:

- **Named Dataset Collections**: Datasets are saved with specific names for easy retrieval
- **Cross-session Persistence**: Datasets remain available across application restarts
- **Automatic Deduplication**: SHA256-based duplicate prevention at the PyRIT level
- **Dual Storage Options**: Session state (temporary) + PyRIT memory (persistent)

### Memory Integration Architecture
```
Dataset Creation → Finalization → Storage Options →
├── Session Storage (Temporary, cleared on restart)
└── PyRIT Memory (Persistent, named collections) → Cross-session Access
```

### Deduplication Strategy
PyRIT's built-in deduplication mechanism uses SHA256 hashing to prevent duplicate prompt storage:
- Prompts with identical content are automatically deduplicated
- Memory storage remains efficient even with repeated dataset saves
- No manual intervention required for duplicate management

### Identified Memory Issues

1.  **Loading Entire Datasets into Memory:**
    * **Issue:** The functions used to load datasets, both PyRIT's native `Workspace_*` functions (e.g., `Workspace_harmbench_dataset`[cite: 8868], `Workspace_decoding_trust_stereotypes_dataset` [cite: 8858]) and custom loaders for local files (`parse_local_dataset_file` in `util_datasets/data_loaders.py`), appear to load the entire dataset content into memory at once, often as `SeedPromptDataset` objects or Pandas DataFrames. Large datasets can lead to excessive memory consumption.
    * **Evidence:** Dataset loading functions in `util_datasets/data_loaders.py` are called in `pages/3_ConfigureDatasets.py`[cite: 8631]. PyRIT fetch functions are designed to return full datasets[cite: 9019, 9024, 9028].
2.  **Unbounded Storage of Interactions:**
    * **Issue:** PyRIT's memory (`DuckDBMemory` or `AzureSQLMemory`) stores all prompts, responses, and scores (`PromptRequestPiece` objects) generated during red teaming sessions[cite: 8757, 8760, 9294, 9295, 9296]. Over long sessions or with many users, the database can grow significantly. If embeddings are enabled[cite: 8760, 9175], this further increases storage needs. Querying large histories or using the "InMemory" option [cite: 9512] could overwhelm available memory.
    * **Evidence:** The `MemoryInterface` provides methods like `add_request_response_to_memory` [cite: 8760, 9181, 10480] and `add_scores_to_memory`[cite: 8760, 9181, 10480]. `PromptMemoryEntry` stores extensive data per piece.
3.  **Reporting Module Memory Usage:**
    * **Issue:** The `ReportingManager` (described in `desc_reporting`) extracts all prompt requests and scores using `get_all()` methods and then loads them into Pandas DataFrames for processing[cite: 10098]. For extensive testing histories, this approach can consume a large amount of memory before the report is even generated.
    * **Evidence:** The `extract_data` method in the reporting manager description fetches all prompt pieces and scores[cite: 10098].
4.  **Potential Resource Leaks (Database Connections):**
    * **Issue:** Persistent memory backends like DuckDB [cite: 8764, 9223] and Azure SQL [cite: 8765, 9168] require proper disposal of database connections/engines using `dispose_engine()`[cite: 9175, 10478]. While `MemoryManager` might handle this[cite: 10080], if not called consistently (e.g., on application shutdown or when switching configurations), it could lead to resource leaks over time.
    * **Evidence:** `dispose_engine()` method exists in `MemoryInterface`[cite: 9181, 10478]. Code examples sometimes omit cleanup[cite: 9305], although some include it[cite: 9293].
5.  **Storing Large Objects in UI Session State:**
    * **Issue:** Streamlit's `st.session_state` is used to hold configuration across pages (e.g., `st.session_state["memory_type"]` [cite: 9509]). Storing large objects like complete datasets, detailed configurations, or extensive results directly in the session state can increase the memory footprint for each active user session.
    * **Evidence:** The blueprint describes storing user selections and configurations in `st.session_state`[cite: 9509, 9557, 9558].
    * **Enhancement:** ViolentUTF now implements dual storage strategy with persistent PyRIT memory for datasets, reducing session state memory pressure.

## Enhanced Memory Management Strategies

### Implemented Enhancements in ViolentUTF

#### 1. Persistent Dataset Collections
**Implementation:** ViolentUTF now supports saving datasets directly to PyRIT memory as named collections:
- **Named Storage**: `memory.add_seed_prompts_to_memory_async()` with specific dataset names
- **Retrieval**: `memory.get_seed_prompts()` filtered by dataset name for cross-session access
- **Deduplication**: Automatic SHA256-based duplicate prevention at PyRIT level
- **Memory Efficiency**: Reduces need to reload large datasets in each session

#### 2. Dual Storage Architecture
**Session State (Temporary)**:
- Stores active dataset for current workflow
- Cleared on application restart
- Fast access for immediate processing

**PyRIT Memory (Persistent)**:
- Named dataset collections for cross-session access
- Persistent storage across application restarts
- Efficient querying and retrieval mechanisms

#### 3. Enhanced Memory Statistics
**Real-time Monitoring**:
- Live dataset count displays in UI
- Memory usage statistics and summaries
- Saved dataset collection management

#### 4. Async Memory Operations
**Non-blocking Processing**:
- `asyncio.run()` for memory operations
- Progress indicators during save/load operations
- Graceful error handling for memory access failures

### Proposed Fixes and Strategies

1.  **Optimize Dataset Handling:**
    * **Strategy:** Implement streaming or chunking for loading and processing datasets, especially large local files (CSV, JSON). Instead of loading everything into a DataFrame/`SeedPromptDataset` at once, process the file line-by-line or chunk-by-chunk.
    * **Example:** Modify `parse_local_dataset_file` to yield prompts iteratively rather than returning a full DataFrame. When using PyRIT datasets, explore if underlying functions offer ways to iterate or sample, or load only necessary subsets based on user criteria.
2.  **Manage Memory Growth:**
    * **Strategy:** Introduce a data retention strategy. For persistent backends (DuckDB, AzureSQL), add functionality to periodically archive or delete old conversation entries based on age or run ID.
    * **Strategy:** Use embeddings selectively. Only enable memory embeddings (`memory.enable_embedding()`) when necessary (e.g., for similarity searches via `ConversationAnalytics` [cite: 8737, 8742]). Keep it disabled by default.
    * **Strategy:** Refine data retrieval. Instead of using `get_all()`, use filtering capabilities in `get_prompt_request_pieces`[cite: 8761], `get_scores_by_*`[cite: 8762], etc., to fetch only the data relevant to the current task (e.g., filtering by `conversation_id`, `orchestrator_identifier`, or `labels` [cite: 8761, 9051, 10418]).
3.  **Optimize Reporting:**
    * **Strategy:** Modify the `ReportingManager` to query and process data in batches or streams rather than loading everything into memory. Filter data within the database query (using PyRIT memory methods with filters) before loading it into Pandas.
    * **Example:** Instead of `memory.prompt_request_pieces.get_all()`, use `memory.get_prompt_request_pieces(orchestrator_id=target_run_id)` to get data only for the specific run being reported. If transformations require large data, use chunking options in Pandas.
4.  **Ensure Resource Cleanup:**
    * **Strategy:** Centralize memory management, potentially within the `MemoryManager` class[cite: 10078]. Ensure `dispose_engine()` [cite: 10080] is reliably called when the application shuts down or when the memory configuration changes, especially for DuckDB and AzureSQL backends. Using context managers (`with`) for session management can also help ensure resources are released.
5.  **Efficient UI State Management:**
    * **Strategy:** Store only necessary identifiers (like dataset names, configuration keys) or minimal configuration details in `st.session_state`. Load the full data (e.g., dataset prompts, detailed results) from the memory backend only when actively needed for display or processing within a specific page or function. Avoid storing large DataFrames or lists directly in the session state.
    * **Implementation in ViolentUTF:** The enhanced dataset management now implements this strategy with dual storage options and efficient memory querying.

## Best Practices for Memory Management in ViolentUTF

### Dataset Management
1. **Use Persistent Collections**: Save finalized datasets to PyRIT memory for cross-session access
2. **Named Collections**: Use descriptive dataset names for easy identification and retrieval
3. **Selective Loading**: Load only required datasets into session state when needed
4. **Memory Cleanup**: Regularly review and clean up unused dataset collections

### PyRIT Memory Optimization
1. **Leverage Deduplication**: Trust PyRIT's built-in SHA256 deduplication for efficiency
2. **Filtered Queries**: Use specific dataset names when querying memory to reduce data transfer
3. **Async Operations**: Use async memory operations to prevent UI blocking
4. **Error Handling**: Implement graceful degradation when memory operations fail

### Session State Management
1. **Minimal Storage**: Store only essential data in session state
2. **Lazy Loading**: Load datasets from memory only when actively needed
3. **Progressive Updates**: Update memory statistics incrementally rather than full refreshes
4. **Resource Cleanup**: Clear session state appropriately when switching contexts

### Performance Monitoring
1. **Memory Statistics**: Monitor PyRIT memory usage through built-in statistics
2. **Dataset Summaries**: Display concise dataset information without loading full content
3. **Progress Indicators**: Provide user feedback during memory-intensive operations
4. **Error Logging**: Log memory operations for debugging and optimization

## Implementation Examples

### Saving Dataset to Memory
```python
# Create dataset-named prompts for persistent storage
for prompt in dataset.prompts:
    prompt_copy = SeedPrompt(
        value=prompt.value,
        dataset_name=dataset_name,  # Named collection identifier
        # ... other attributes preserved
    )

# Async save with deduplication
await memory.add_seed_prompts_to_memory_async(
    prompts=prompts_to_save,
    added_by=f"ConfigureDatasets Finalizer - {dataset_name}"
)
```

### Loading Dataset from Memory
```python
# Query by dataset name for efficient retrieval
saved_prompts = memory.get_seed_prompts(
    added_by=f"ConfigureDatasets Finalizer - {dataset_name}"
)

# Create dataset from memory prompts
loaded_dataset = SeedPromptDataset(prompts=saved_prompts)
```

### Memory Statistics Display
```python
# Efficient memory querying for statistics
memory_prompts = memory.get_seed_prompts()
dataset_groups = {}
for prompt in memory_prompts:
    if prompt.dataset_name:
        dataset_groups.setdefault(prompt.dataset_name, 0)
        dataset_groups[prompt.dataset_name] += 1

# Display summary without loading full datasets
for name, count in dataset_groups.items():
    st.write(f"📁 {name}: {count} prompts")
```
