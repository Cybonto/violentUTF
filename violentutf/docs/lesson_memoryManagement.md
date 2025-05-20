# Lesson on Memory Management

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
