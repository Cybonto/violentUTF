# 2. Configure Generators

This section guides you through configuring the Generator (PyRIT Target). You'll select the generator technology, configure specific parameters using an enhanced two-column interface, and ensure the selected Generator is properly initialized and tested. The interface has been streamlined to focus on the three core generator types with AI Gateway as the default option.

## Notes:
- In PyRIT, the term **Target** is used internally, but ViolentUTF uses "Generator" for consistency.
- **AI Gateway** provides unified access to multiple AI providers through APISIX proxy.
- The interface uses dynamic model discovery for real-time provider integration.

## 2a. Manage Existing Generators

### Display:
- **Two-column layout** with generator management on the left and system info on the right
- A grid display (3 columns) of existing Generators showing:
  - Generator name and type
  - Instance status (✅ Ready / ⚠️ Failed)
- **Add New Generator** section below the existing generators
- **Delete Generators** expandable section with multi-select deletion

### Action:
- User can add (configure/set up) a new Generator
- User can delete one or more existing Generators via multi-select

### Backend:
- Retrieve and display the list of saved Generators from the generator configuration file
- Update `st.session_state` and `generators.yaml` when changes are made
- Handle generator instantiation and testing asynchronously

## 2b. Generator Technology Selection

### Display:
- **Streamlined selection** with only three core generator types:
  1. **AI Gateway** (Default) - Unified access to multiple AI providers
  2. **OpenAI_Completion** - Direct OpenAI API integration
  3. **HTTP REST** - Generic HTTP endpoint integration
- Two-column basic configuration layout
- **Generator Technology** selectbox with **AI Gateway as default selection**

### Action:
- User selects one of the three generator technologies
- Selection triggers form refresh for technology-specific parameters

### Backend:
- Store the selected generator type in session state
- Trigger form counter increment for dynamic UI updates
- Load technology-specific parameter definitions

## 2c. Enhanced Parameter Configuration

### 2c.1 AI Gateway Configuration (Default)

#### Display:
- **Provider Selection Outside Form**: Enables dynamic model loading
- **Two-column parameter layout**:
  - **Left Column (Configuration)**: Provider, Model, Rate Limiting
  - **Right Column (Model Parameters)**: Temperature, Tokens, Penalties
- **Dynamic Model Discovery**: Real-time model loading based on provider selection
- **Live Discovery Info**: Shows available model count for selected provider

#### Provider Selection Flow:
1. **Provider Selectbox** (Outside form with `on_change` callback):
   - Options: OpenAI, Anthropic, Ollama, WebUI
   - Default: OpenAI
   - Triggers model refresh when changed

2. **Dynamic Model Loading**:
   - Calls `get_apisix_models_for_provider()` for real-time model discovery
   - Updates model selectbox options automatically
   - Shows "📡 **Live Discovery**: Found X models for Y provider"

#### Parameters by Category:
**Configuration Parameters (Left Column):**
- `provider`: AI Provider selection (openai, anthropic, ollama, webui)
- `model`: Model Name (dynamically loaded from APISIX)
- `max_requests_per_minute`: Rate limiting (optional)

**Model Parameters (Right Column):**
- `temperature`: Temperature (0.0-2.0, default: 0.7)
- `max_tokens`: Max Tokens (default: 1000, required for Anthropic)
- `top_p`: Top P (0.0-1.0, default: 1.0)
- `frequency_penalty`: Frequency Penalty (-2.0 to 2.0, default: 0.0)
- `presence_penalty`: Presence Penalty (-2.0 to 2.0, default: 0.0)
- `seed`: Random seed for reproducibility (optional)

#### Backend Integration:
- **TokenManager Integration**: Uses `TokenManager.call_ai_endpoint()` for API calls
- **APISIX Endpoints**: Routes to `/ai/{provider}/{model}` endpoints
- **Authentication**: API key-based authentication with fallback tokens
- **Error Handling**: Proper PyRIT response format with `construct_response_from_request()`

### 2c.2 OpenAI_Completion Configuration

#### Display:
- Standard single-column parameter layout
- Model selection from predefined list loaded from `default_parameters.yaml`

#### Parameters:
- `api_key`: OpenAI API Key (password field)
- `model_name`: Chat Model selection (dropdown)
- `max_tokens`: Max completion length (default: 1000)
- `temperature`: Temperature (0.0-2.0, default: 0.7)
- `top_p`, `frequency_penalty`, `presence_penalty`: Advanced parameters
- `headers`: Additional request headers (JSON format)
- `verbose`: Enable verbose logging
- `max_requests_per_minute`: Rate limiting (optional)

### 2c.3 HTTP REST Configuration

#### Display:
- Standard parameter layout for generic HTTP endpoints

#### Parameters:
- `http_request`: HTTP request string with {PROMPT} placeholder
- `prompt_regex_string`: Prompt placeholder regex (default: {PROMPT})
- `use_tls`: Use HTTPS (default: True)
- `max_requests_per_minute`: Rate limiting (optional)

## 2d. Save and Test Generator

### Display:
- **"Save and Test Generator"** button (full width, disabled until parameters are configured)
- **Real-time validation** preventing submission with missing required fields

### Action:
- **Save Generator**: Validates parameters and saves configuration
- **Test Generator**: Performs async test call to verify connectivity and functionality

### Backend Processing:

#### Parameter Validation:
- **Required Field Validation**: Ensures all required parameters are provided
- **Type Validation**: Converts and validates parameter types (int, float, bool, dict)
- **Azure-Specific Logic**: Handles Azure OpenAI endpoint detection and parameter filtering
- **Default Value Handling**: Excludes optional parameters that match default values

#### Save Process:
1. Create `Generator` wrapper object with validated parameters
2. Instantiate the underlying PyRIT target class
3. Save configuration to `generators.yaml`
4. Update in-memory cache

#### Test Process:
1. **Async Test Execution**: Uses `test_generator_async()` for validation
2. **PyRIT Integration**: Creates proper `PromptRequestResponse` objects
3. **Response Validation**: Checks for successful assistant responses
4. **Error Handling**: Comprehensive error reporting with status updates

#### APISIX-Specific Features:
- **Anthropic Compatibility**: Ensures `max_tokens` is provided for Anthropic models
- **Role Consistency**: Uses `construct_response_from_request()` for proper PyRIT response format
- **Provider Verification**: Validates provider/model availability through APISIX endpoints

## 2e. Advanced Features

### Dynamic Model Discovery
- **Real-time Updates**: Model lists refresh when providers change
- **APISIX Integration**: Direct query to APISIX gateway for available models
- **Fallback Handling**: Graceful degradation when APISIX is unavailable
- **Provider-Specific Models**: Each provider shows only compatible models

### Error Handling and Validation
- **Comprehensive Validation**: Parameter type checking, required field validation
- **User-Friendly Messages**: Clear error messages for configuration issues
- **Async Error Handling**: Proper handling of network timeouts and API errors
- **Recovery Mechanisms**: Automatic retry logic and fallback options

### Memory Integration
- **Generator Persistence**: All configurations saved to persistent storage
- **Instance Management**: Proper cleanup and resource management
- **Session State**: Temporary storage for UI workflow management

## 2f. Delete Generators

### Display:
- **Expandable section** "Delete Generators"
- **Multi-select** interface for selecting generators to delete
- **Confirmation required** via "Delete Selected" button

### Action:
- User selects one or more generators from the list
- Confirms deletion via button click
- System provides feedback for each deletion attempt

### Backend:
- **Safe Deletion**: Removes from both cache and persistent storage
- **Error Handling**: Graceful handling of missing or corrupted generators
- **UI Updates**: Automatic refresh to reflect changes
- **Logging**: Comprehensive logging of deletion operations

## 2g. Proceed to Next Step

### Display:
- **"Next: Configure Datasets"** button (primary styling)
- **Disabled state** until at least one working generator exists

### Action:
- User clicks to proceed to dataset configuration
- **Validation**: Ensures at least one generator with successful instance exists

### Backend:
- **Generator Validation**: Checks for at least one generator with working instance
- **Navigation**: Switches to `3_ConfigureDatasets.py`
- **State Persistence**: Maintains generator configurations across page transitions

## 2h. Technical Implementation Notes

### PyRIT Integration
- **Target Classes**: Proper instantiation of PyRIT target classes
- **Memory Management**: Integration with CentralMemory for conversation tracking
- **Error Response Format**: Uses PyRIT's `construct_response_from_request()` helper
- **Async Operations**: All API calls use async/await patterns

### APISIX Gateway Features
- **Multi-Provider Support**: OpenAI, Anthropic, Ollama, WebUI through single interface
- **Dynamic Discovery**: Real-time model availability checking
- **Authentication**: Secure API key management through TokenManager
- **Rate Limiting**: Built-in rate limiting support across all providers

### UI/UX Improvements
- **Two-Column Layouts**: Better space utilization and logical parameter grouping
- **Dynamic Forms**: Form refresh triggers for real-time updates
- **Progress Indicators**: Spinner and status messages for long operations
- **Responsive Design**: Consistent layout across different screen sizes

### Error Handling Best Practices
- **Graceful Degradation**: System remains functional when optional services fail
- **User Communication**: Clear, actionable error messages
- **Logging**: Comprehensive logging for debugging and monitoring
- **Recovery**: Automatic retry mechanisms where appropriate

This enhanced generator configuration provides a streamlined, powerful interface for setting up AI targets with comprehensive provider support, dynamic discovery, and robust error handling.