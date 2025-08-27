# 4. Configure Converters

This section allows users to apply PyRIT converters to transform their datasets for enhanced AI red-teaming scenarios. Converters modify prompts in various ways including encoding, translation, jailbreak techniques, and adversarial transformations. The enhanced interface provides comprehensive dataset management with both overwrite and copy options for safe experimentation.

## Enhanced Features:
- **Dual-source dataset loading** from session state and PyRIT memory
- **Two-column responsive layout** for better space utilization
- **Smart converter parameter handling** with type validation and UI forms
- **Preview and confirmation workflow** with sample transformations
- **Multiple application modes**: Overwrite original or create named copies
- **Integrated testing functionality** with compact result display
- **PyRIT memory integration** for persistent dataset storage

## Prerequisites:
- **Generators configured** from Step 2 (at least one functional generator required)
- **Datasets available** from Step 3 or PyRIT memory collections
- **PyRIT memory initialized** for dataset persistence and testing

## 4.1 Select Generator and Dataset

### Display Layout:
- **Two-column layout**:
  - **Left Column**: Generator and dataset selection with information display
  - **Right Column**: System status and configuration summary

### Generator & Dataset Selection (Left Column):
- **Generator Selection**: Dropdown of configured generators from Step 2
- **Dataset Selection**: Dropdown of available datasets from:
  - Session state datasets (configured in Step 3)
  - PyRIT memory datasets (persistent collections)
- **Information Display**:
  - Generator type and status
  - Dataset prompt count and source

### System Status (Right Column):
- **PyRIT Memory Status**: Connection and initialization status
- **Generator Summary**: Count of configured generators
- **Dataset Summary**: Total datasets with breakdown by source:
  - Session datasets (temporary)
  - Memory datasets (persistent)

### Backend Processing:
- **Dataset Discovery**: Automatic loading from both session state and PyRIT memory
- **Generator Validation**: Ensure generator instances are functional
- **Session State Management**: Store selections for workflow continuity
- **Memory Integration**: Query PyRIT memory for saved dataset collections

## 4.2 Select Converter Class

### Display Layout:
- **Two-column responsive design**:
  - **Left Column**: Converter category and class selection
  - **Right Column**: Parameter configuration with dynamic forms

### Converter Selection (Left Column):
- **Converter Category Dropdown**: Organized by transformation type:
  - String Manipulation
  - Encoding/Decoding
  - Language Translation
  - Adversarial Techniques
  - LLM-based Transformations
- **Converter Class Dropdown**: Available converters within selected category
- **Target Requirement Indicator**:
  - 🎯 "This converter requires a target" (for LLM-based converters)
  - ⚙️ "Standalone converter" (for rule-based converters)

### Backend Logic:
- **Dynamic Category Loading**: Retrieve available converter categories from configuration
- **Target Validation**: Check if converter requires `PromptTarget` or `PromptChatTarget`
- **Parameter Discovery**: Load converter-specific parameter definitions
- **Session State Storage**: Store selected converter class for workflow

## 4.3 Configure Converter Parameters (Right Column)

### Enhanced Parameter Forms:
- **Dynamic Form Generation**: Forms adapt to converter requirements
- **Type-Aware Widgets**: Appropriate input widgets based on parameter types:
  - **Selectbox**: For Literal types and predefined choices
  - **Checkbox**: For boolean parameters with contextual help text
  - **Number Input**: For integers and floats with proper formatting
  - **Text Area**: For list types (one item per line)
  - **Text Input**: For strings and tuples (comma-separated)
- **Smart Default Handling**: Pre-populate with default values
- **Parameter Persistence**: Maintain configured values across form refreshes

### Parameter Types and Widgets:
```python
# Examples of parameter handling:
bool -> st.checkbox()           # append_description, verbose flags
int -> st.number_input(step=1)  # max_tokens, retry_count
float -> st.number_input()      # temperature, threshold values
list -> st.text_area()          # word_lists, replacement_sets
str -> st.text_input()          # templates, custom_strings
Literal -> st.selectbox()       # predefined choices like encrypt_type
```

### Special Parameter Handling:
- **Target Injection**: Automatically inject generator instances for converters requiring targets
- **SeedPrompt Conversion**: Convert string templates to SeedPrompt objects
- **Complex Type Skipping**: Skip UI generation for complex objects (handled programmatically)
- **Validation and Type Conversion**: Real-time validation with error feedback

### Form Workflow:
1. **Parameter Discovery**: Load converter-specific parameter definitions
2. **Form Rendering**: Generate appropriate widgets based on parameter types
3. **Form Submission**: "Set Parameters" button triggers validation
4. **Type Conversion**: Convert raw widget values to proper Python types
5. **Validation**: Check required fields and type constraints
6. **Storage**: Store validated parameters in session state
7. **Success Feedback**: Confirm parameter configuration completion

## 4.4 Preview & Apply Converter

### Two-Column Preview Layout:

#### Left Column - Preview Sample:
- **Original Prompt Display**: Show first prompt from selected dataset
- **Converted Prompt Display**: Real-time transformation preview
- **Converter Creation**: Use centralized `create_converter_instance()` logic
- **Confirmation Workflow**:
  - ✅ **Confirm Button**: Enable converter application
  - ❌ **Cancel Button**: Reset confirmation state
- **Status Indicators**:
  - ⚠️ "Click 'Confirm' to enable dataset application options"
  - ✅ "Converter confirmed - Apply options available below!"

#### Right Column - Converter Details:
- **Converter Information**: Name and type display
- **Parameter Summary**: Expandable view of configured parameters
- **Application Status**: Confirmation and application state tracking
- **Dataset Reset Option**: 🔄 "Reset Dataset" for testing different configurations

### Preview Logic:
- **Sample Selection**: Use first prompt from dataset for preview
- **Real-time Conversion**: Apply converter to sample with error handling
- **Preview Validation**: Ensure converter works before full application
- **State Management**: Track confirmation status for workflow control

## 4.5 Apply to Dataset - Dual Application Modes

### Enhanced Application Options (Two-Column Layout):

#### Left Column - Overwrite Original:
- **"Apply to Entire Dataset" Button**: 🚀 Overwrite original dataset
- **Memory Integration**: Option to save changes to PyRIT memory
- **Warning Display**: ⚠️ "This overwrites the original dataset in memory"
- **Immediate Application**: Direct replacement of current dataset

#### Right Column - Create Copy:
- **New Dataset Name Input**: Pre-filled with `{original}_converted` pattern
- **"Apply to Copied Dataset" Button**: 📋 Create new dataset copy
- **PyRIT Memory Storage**: Automatically save new dataset to persistent memory
- **Original Preservation**: ✅ "Creates a new dataset, keeps original intact"
- **Session Integration**: Add new dataset to available datasets list

### Application Workflows:

#### Overwrite Mode:
1. **Converter Application**: Apply to entire original dataset
2. **Session State Update**: Replace current dataset in session
3. **Memory Sync**: Update combined datasets and PyRIT memory
4. **Verification**: Confirm transformation with first prompt preview

#### Copy Mode:
1. **Dataset Duplication**: Create copy with new name
2. **Converter Application**: Apply converter to copied dataset
3. **Memory Persistence**: Save to PyRIT memory with new name
4. **Session Integration**: Add to combined datasets for immediate access
5. **Success Tracking**: Store copy information for testing and feedback

### Success Feedback:
- **Persistent Messages**: Success/error messages survive page refreshes
- **Progress Indicators**: Spinners during conversion operations
- **Verification Displays**: Show converted prompt previews
- **Status Tracking**: Maintain application state for workflow continuity

## 4.6 Test Converted Dataset

### Integrated Testing Features:
- **Conditional Display**: Only appears after successful converter application
- **Smart Dataset Selection**: Automatically test most recently created dataset
- **Configurable Sample Size**: 1-10 prompts with default of 3
- **Compact Results Display**: Expandable sections for each test

### Testing Process:
1. **Dataset Selection Logic**:
   - Primary: Most recently copied dataset (tracked in session state)
   - Fallback: Current main dataset if no copy available
2. **Generator Integration**: Use selected generator from Step 4.1
3. **Async Orchestration**: `PromptSendingOrchestrator` for proper PyRIT testing
4. **Results Presentation**: Compact expandable format with prompt and response

### Test Results Display:
```
🧪 Testing 3 prompts from copied dataset 'jailbreak_prompts_converted'

Test 1 - Converted Prompt ▼
  Converted Prompt: [Transformed text with converter applied]
  Response: [AI model response to converted prompt]

Test 2 - Converted Prompt ▼
  [Additional test results...]
```

### Backend Processing:
- **Memory Management**: No need to add test prompts to PyRIT memory
- **Error Handling**: Comprehensive error catching with user feedback
- **Response Extraction**: Proper PyRIT response object handling
- **Performance Optimization**: Efficient async operations

## 4.7 Enhanced Data Management

### Dataset Source Integration:
- **Session State Datasets**: Temporary datasets from current workflow
- **PyRIT Memory Datasets**: Persistent collections from previous sessions
- **Combined Management**: Unified interface for both data sources
- **Real-time Updates**: Dynamic dataset list updates after conversions

### Memory Persistence:
- **Automatic Saving**: Converted datasets saved to PyRIT memory
- **Named Collections**: Organized storage with descriptive names
- **Metadata Preservation**: Maintain prompt attributes and provenance
- **Cross-session Access**: Datasets available in future sessions

### Error Recovery:
- **Graceful Degradation**: System remains functional when memory unavailable
- **Validation Checks**: Ensure datasets and generators exist before operations
- **User Communication**: Clear error messages with actionable guidance
- **State Cleanup**: Proper cleanup of failed operations

## 4.8 Technical Implementation

### Centralized Converter Creation:
```python
def create_converter_instance(converter_name, converter_params):
    # Handle special parameters (targets, templates)
    # Perform type conversions and validation
    # Return instantiated converter with proper error handling
```

### Parameter Type System:
- **Primary Type Detection**: Identify base Python types
- **Literal Choice Handling**: Support for enumerated options
- **Complex Type Skipping**: Programmatic handling of objects
- **Default Value Management**: Smart default application

### Async Operations:
- **Converter Application**: Sync operations for immediate feedback
- **Dataset Testing**: Async orchestrator operations
- **Memory Storage**: Async PyRIT memory operations
- **Error Propagation**: Proper async error handling

### Session State Architecture:
```python
# Key session state variables:
st.session_state['current_converter_class']      # Selected converter
st.session_state['current_converter_params']     # Configured parameters
st.session_state['converter_confirmed']          # Confirmation status
st.session_state['converter_applied']            # Application status
st.session_state['combined_datasets']            # All available datasets
st.session_state['last_copied_dataset_name']     # Most recent copy for testing
```

## 4.9 User Experience Enhancements

### Progressive Disclosure:
- **Step-by-step Workflow**: Clear progression through converter configuration
- **Conditional UI Elements**: Show options only when prerequisites met
- **Status Indicators**: Visual feedback for each workflow stage
- **Help Text**: Contextual guidance for complex parameters

### Responsive Design:
- **Two-column Layouts**: Optimal space utilization
- **Expandable Sections**: Detailed information without clutter
- **Button Grouping**: Logical action organization
- **Status Messages**: Persistent feedback across page refreshes

### Error Prevention:
- **Validation Gates**: Prevent progression without valid configuration
- **Preview System**: Test conversion before full application
- **Confirmation Steps**: Explicit user confirmation for destructive operations
- **Reset Options**: Allow users to restart configuration safely

This enhanced converter configuration provides a comprehensive, user-friendly interface for applying PyRIT converters to datasets with robust error handling, multiple application modes, and seamless integration with the broader red-teaming workflow.
