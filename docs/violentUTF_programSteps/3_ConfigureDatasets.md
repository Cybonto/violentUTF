# 3. Configure Datasets

This section allows users to create, load, and manage datasets with enhanced PyRIT memory integration. Users can create datasets from multiple sources including natively supported datasets, custom datasets from local files or online resources, persistent PyRIT memory collections, or by combining and transforming existing datasets. The enhanced interface features a two-column layout, persistent dataset storage, and comprehensive memory integration for cross-session dataset management.

## Enhanced Features:
- **Two-column layout** with dataset configuration and memory status
- **PyRIT memory integration** for persistent dataset collections
- **Load from PyRIT Memory** for accessing saved datasets across sessions
- **Dual storage options** (session state + persistent memory)
- **Advanced memory statistics** and dataset management

## 3a. Choose Dataset Source

### Display:
- **Two-column layout**:
  - **Left Column**: Dataset source selection and memory status
  - **Right Column**: Dataset configuration flows (dynamic based on selection)
- **Dataset Source Options** (radio button selection):
  1. **Select Natively Supported Datasets** - PyRIT and platform-native datasets
  2. **Upload Local Dataset File** - CSV, TSV, JSON, YAML, TXT files
  3. **Fetch from Online Dataset** - Download datasets from URLs
  4. **Load from PyRIT Memory** - Access previously saved dataset collections
  5. **Combining Datasets** - Merge multiple existing datasets
  6. **Transforming Dataset** - Apply prompt templates to existing datasets

### Action:
- User selects one dataset source option
- Right column updates dynamically based on selection
- Memory status displays current PyRIT memory state

### Backend:
- Store the selected source type in `st.session_state["dataset_source"]`
- Map selections to internal values: `"native"`, `"local"`, `"online"`, `"memory"`, `"combination"`, `"transform"`
- Update parameter file with the dataset source selection
- Display real-time memory statistics and saved dataset summaries

## 3b. Conditional Flows

The flows below are displayed dynamically in the right column according to the selected Dataset Source value from step 3a.

### 3b.A Flow for "Select Natively Supported Datasets"

#### 3b.A.1 Display Natively Supported Datasets

**Display:**
- Dropdown list of PyRIT-supported datasets loaded via `data_loaders.get_pyrit_datasets()`
- Default "-- Select --" option to prevent premature loading

**Action:**
- User selects a dataset from the dropdown
- System loads dataset metadata and configuration options

**Backend:**
- Retrieve available PyRIT datasets dynamically
- Handle dataset loading errors gracefully
- Store selected dataset in session state

#### 3b.A.2 Configure Dataset Parameters

**Display:**
- Dataset-specific configuration options (e.g., language selection for `aya_redteaming`)
- Configuration appears only when a valid dataset is selected

**Action:**
- User configures dataset-specific parameters as needed
- Parameters vary by dataset type

**Backend:**
- Store configuration parameters in session state
- Validate parameter combinations
- Prepare for dataset loading

#### 3b.A.3 Load Dataset

**Display:**
- Loading spinner during dataset fetch
- Success/error messages for loading status
- Dataset statistics upon successful load

**Action:**
- User triggers dataset loading (automatic after configuration)
- System validates and loads the dataset into session state

**Backend:**
- Use `data_loaders.load_dataset()` with configuration parameters
- Create `SeedPromptDataset` object
- Store in `st.session_state['dataset']`
- Handle `DatasetLoadingError` exceptions gracefully

### 3b.B Flow for "Upload Local Dataset File"

#### 3b.B.1 Upload and Parse File

**Display:**
- File uploader accepting CSV, TSV, JSON, YAML, TXT formats
- File validation and security checking
- Parse progress indication

**Action:**
- User uploads a dataset file
- System performs security validation and parsing

**Backend:**
- Use `data_loaders.parse_local_dataset_file()` for file processing
- Perform malicious content detection
- Store raw dataset in `st.session_state['raw_dataset']`

#### 3b.B.2 Dataset Preview and Field Mapping

**Display:**
- Preview of uploaded data using `st.dataframe()`
- Field mapping interface for required SeedPrompt attributes
- Column selection dropdowns for mapping fields

**Action:**
- User maps dataset columns to required fields (minimally 'value' field)
- User reviews data preview before creating dataset

**Backend:**
- Provide column options from uploaded dataset
- Store field mappings for dataset creation
- Validate mapping completeness

#### 3b.B.3 Create Dataset

**Display:**
- "Create Dataset" button
- Dataset creation progress and results

**Action:**
- User clicks to create the final dataset
- System creates `SeedPromptDataset` from mappings

**Backend:**
- Use `data_loaders.map_dataset_fields()` and `data_loaders.create_seed_prompt_dataset()`
- Store final dataset in `st.session_state['dataset']`
- Handle creation errors with user feedback

### 3b.C Flow for "Fetch from Online Dataset"

#### 3b.C.1 Enter Dataset URL

**Display:**
- Text input for dataset URL
- Format instructions (CSV, TSV, JSON, YAML, TXT)
- "Fetch Dataset" button

**Action:**
- User enters valid dataset URL
- User triggers fetch operation

**Backend:**
- Store URL in session state
- Validate URL format

#### 3b.C.2 Fetch and Preview

**Display:**
- Download progress indication
- Dataset preview after successful fetch
- Error messages for fetch failures

**Action:**
- User reviews fetched data
- User proceeds to field mapping

**Backend:**
- Use `data_loaders.fetch_online_dataset()` for download and parsing
- Handle network errors and invalid formats
- Store raw dataset for processing

#### 3b.C.3 Field Mapping and Creation

**Process:**
- Follow same mapping process as local file upload (3b.B.2 and 3b.B.3)
- Create final `SeedPromptDataset` from online source

### 3b.D Flow for "Load from PyRIT Memory" (NEW)

#### 3b.D.1 Browse Saved Datasets

**Display:**
- **Loading spinner** while querying PyRIT memory
- **Available Saved Datasets** section showing:
  - Dataset names with prompt counts
  - Grouped by dataset name from memory
- **Dataset selection dropdown** with saved collections

**Action:**
- User selects a previously saved dataset from memory
- User reviews dataset information before loading

**Backend:**
- Query PyRIT memory using `memory.get_seed_prompts()`
- Group prompts by `dataset_name` attribute
- Generate dataset summary with prompt counts

#### 3b.D.2 Preview and Load

**Display:**
- **Dataset information**: Name and prompt count
- **Prompt preview**: First 5 prompts with expandable view
- **"Load Selected Dataset"** button

**Action:**
- User previews dataset contents
- User confirms loading of selected dataset

**Backend:**
- Retrieve all prompts for selected dataset name
- Create `SeedPromptDataset` from memory prompts
- Store in `st.session_state['dataset']`
- Handle memory access errors gracefully

### 3b.E Flow for "Combining Datasets"

#### 3b.E.1 Select Datasets to Combine

**Display:**
- Multi-select checkboxes for existing configured datasets
- "Combine Datasets" button
- Warning if no datasets available

**Action:**
- User selects multiple datasets from session state
- User triggers combination process

**Backend:**
- Check `st.session_state['datasets_list']` for available datasets
- Validate dataset selection (minimum 2 required)

#### 3b.E.2 Combine and Create

**Display:**
- Combination progress indication
- Statistics of combined dataset
- Success/error messages

**Action:**
- User reviews combined dataset statistics
- System creates combined dataset

**Backend:**
- Use `dataset_transformations.combine_datasets()` for merging
- Store combined dataset in session state
- Handle combination errors and conflicts

### 3b.F Flow for "Transforming Dataset"

#### 3b.F.1 Select Dataset and Method

**Display:**
- Dataset selection (requires existing dataset)
- Transformation method radio buttons:
  - "Transform with existing prompt template"
  - "Transform with new prompt template"

**Action:**
- User selects dataset to transform
- User chooses transformation method

**Backend:**
- Validate dataset availability
- Store transformation method selection

#### 3b.F.2 Template Selection/Creation

**For Existing Templates:**
- Template dropdown with preview functionality
- Template content display

**For New Templates:**
- Text area for custom template entry
- Template syntax validation
- Example templates and guidance

#### 3b.F.3 Apply Transformation

**Display:**
- "Preview Template" button for testing
- "Apply Template" button for final transformation
- Transformation progress and results

**Action:**
- User previews template application
- User applies template to create transformed dataset

**Backend:**
- Use `dataset_transformations.transform_dataset_with_template()`
- Handle `TemplateError` exceptions
- Store transformed dataset in session state

## 3c. Test Dataset

### Enhanced Testing Features:
- **Generator selection** from configured generators (Step 2)
- **Sample size selection** (1-10 prompts, defaulting to 3)
- **PyRIT memory integration** for test prompt storage
- **Real-time memory statistics** during testing
- **Comprehensive error handling** with improved debugging

### Display:
- **Dataset information**: Total prompt count and status
- **Generator selection**: Dropdown of configured generators with validation
- **Sample size slider**: Configurable test sample size
- **"Run Test" button**: Disabled until generator selected
- **Test results display**: Response snippets and error status

### Testing Process:

#### 3c.1 Pre-test Validation
- Verify dataset exists and contains prompts
- Validate generator selection and availability
- Ensure PyRIT memory is accessible

#### 3c.2 Memory Integration
- **Add seed prompts to memory**: `memory.add_seed_prompts_to_memory_async()`
- **Built-in deduplication**: PyRIT prevents duplicate prompt storage
- **Memory statistics update**: Real-time prompt count display

#### 3c.3 Async Test Execution
- **PromptSendingOrchestrator**: Configure with selected generator
- **Async prompt sending**: `send_prompts_async()` with test prompt texts
- **Proper response handling**: Compatible with enhanced error handling

#### 3c.4 Results Display
- **Response table**: Snippet and error status for each test
- **Error handling**: Timeout, network, and API error management
- **Memory verification**: Confirm prompts added to persistent storage

### Backend Processing:
- **Memory Management**: Integration with PyRIT CentralMemory
- **Async Operations**: Non-blocking test execution
- **Error Recovery**: Graceful handling of API failures
- **Result Formatting**: User-friendly response presentation

## 3d. Enhanced Finalize Dataset Configuration

### New Features:
- **Two-column layout** for better organization
- **Dual storage options**: Session state and PyRIT memory
- **Named dataset collections** for persistent storage
- **Dataset management summary** with real-time statistics

### Display Layout:

#### Left Column - Save Configuration:
- **Dataset name input**: Required for saving
- **Storage option checkboxes**:
  - ☑️ **Save to current session (temporary)**: Available during session only
  - ☑️ **Save to PyRIT memory (persistent)**: Stored permanently across sessions
- **Save processing**: Progress indicators and success/error messages

#### Right Column - Saved Datasets Summary:
- **📁 Session Datasets**: Currently loaded temporary datasets
- **💾 PyRIT Memory Datasets**: Persistent collections with prompt counts
- **Real-time updates**: Automatic refresh of dataset lists

### Enhanced Save Process:

#### 3d.1 Session State Storage
- Store complete `SeedPromptDataset` object in `st.session_state['datasets_list']`
- Immediate availability for current session operations
- Temporary storage cleared on session end

#### 3d.2 PyRIT Memory Storage
**Process:**
1. **Prompt Preparation**: Create copies with specific dataset name
2. **Async Memory Storage**: Use `memory.add_seed_prompts_to_memory_async()`
3. **Deduplication Handling**: PyRIT's built-in SHA256-based deduplication
4. **Progress Indication**: Real-time save progress with spinner
5. **Verification**: Confirm successful storage

**Backend Implementation:**
```python
# Create dataset-named prompts for memory storage
for prompt in dataset.prompts:
    prompt_copy = SeedPrompt(
        value=prompt.value,
        dataset_name=dataset_name,  # Named collection
        # ... other attributes
    )

# Async save to memory with deduplication
await memory.add_seed_prompts_to_memory_async(
    prompts=prompts_to_save,
    added_by=f"ConfigureDatasets Finalizer - {dataset_name}"
)
```

### 3d.3 Success Confirmation
- **Multi-location success**: Confirmation for both storage types
- **Error handling**: Separate error reporting for each storage method
- **User feedback**: Clear indication of save success/failure

### 3d.4 Continue Workflow
- **"Proceed to Next Step"** button with primary styling
- **Validation**: Ensure dataset properly configured before proceeding
- **Navigation**: Transition to `4_ConfigureConverters.py`

## 3e. Memory Integration Architecture

### PyRIT Memory Features:
- **Named Dataset Collections**: Organized storage by dataset name
- **Cross-session Persistence**: Datasets available across all future sessions
- **Automatic Deduplication**: SHA256-based duplicate prevention
- **Metadata Preservation**: Complete prompt attributes and provenance tracking

### Memory Management:
- **Real-time Statistics**: Live prompt counts and dataset summaries
- **Error Recovery**: Graceful handling of memory access failures
- **Performance Optimization**: Efficient querying and storage operations
- **Resource Management**: Proper memory instance handling and cleanup

### Data Flow:
```
Configure Dataset → Finalize → Save Options → 
├── Session Storage (Temporary)
└── PyRIT Memory (Persistent) → Named Collections → Cross-session Access
```

## 3f. Implementation Notes

### Enhanced Error Handling:
- **Comprehensive validation** for all dataset operations
- **User-friendly error messages** with actionable guidance
- **Graceful degradation** when optional services fail
- **Detailed logging** for debugging and monitoring

### Performance Considerations:
- **Async operations** for non-blocking UI interactions
- **Memory-efficient** dataset loading and processing
- **Optimized queries** for large dataset collections
- **Progressive loading** for improved user experience

### Security Features:
- **File validation** for uploaded datasets
- **Content sanitization** for malicious data prevention
- **Access control** through PyRIT memory permissions
- **Secure storage** of dataset collections

This enhanced dataset configuration provides a comprehensive, persistent, and user-friendly interface for managing datasets across the entire red-teaming workflow with seamless PyRIT memory integration.