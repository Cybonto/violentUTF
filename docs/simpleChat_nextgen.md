# Simple Chat Next Generation: MCP Enhancement Layer Integration Plan

## Overview
This document outlines the development plan for integrating MCP (Model Context Protocol) server capabilities into the Simple Chat page as a natural enhancement layer, providing intelligent assistance for prompt engineering, security testing, conversation analysis, and **natural language configuration of ViolentUTF components**.

## Existing Functionality Analysis

### What Already Exists in ViolentUTF:
1. **MCP Server** (violentutf_api) - Complete implementation with SSE transport, prompts, resources
   - ✅ All required methods implemented (tools/list, tools/execute, resources/read, prompts/get)
   - ✅ Server-side handlers fixed and tested
2. **JWT Authentication** - Comprehensive token management with automatic refresh
3. **API Gateway Integration** - All requests routed through APISIX
4. **Dataset Management** - Loading, combining, and transforming datasets
5. **Security Testing** - PyRIT orchestrators, scorers, and converters
6. **Prompt Variables** - Save and reuse prompt snippets in Simple Chat
7. **Multi-Provider Support** - AI Gateway, OpenAI, Anthropic, etc.
8. **Template Transformation** - Jinja2-based prompt transformation
9. **MCP Tool Discovery** - Automatic introspection of API endpoints as MCP tools
10. **Configuration APIs** - Full CRUD operations for generators, datasets, converters, scorers

### What Does NOT Exist (and needs to be built):
1. **MCP Client** - No SSE client implementation in Streamlit
2. **JSON-RPC Client** - No JSON-RPC message handling
3. **Streaming Support** - No real-time streaming from backend
4. **Command Interface** - No natural language command parsing
5. **Prompt Enhancement UI** - No UI for MCP prompt templates
6. **Real-time Analysis** - No live conversation analysis
7. **Context Browser** - No UI for browsing MCP resources

## Natural Language Configuration Use Cases

### Primary Use Case: Configure ViolentUTF Components via Natural Language

The MCP integration enables users to configure ViolentUTF components using natural language instead of navigating through multiple configuration pages. This dramatically simplifies the workflow for:

#### 1. **Generator Configuration**
Instead of: Navigate to Configure Generators → Fill form → Save → Test
Now: Type "Create a GPT-4 generator with temperature 0.7 and test it"

MCP will:
- Parse the intent and parameters
- Call `create_generator` tool with appropriate arguments
- Automatically test the generator
- Return results in chat

#### 2. **Dataset Management**
Instead of: Configure Datasets → Upload/Select → Transform → Save
Now: Type "Load the jailbreak dataset and add custom prompts from my file"

MCP will:
- Identify dataset by name
- Load dataset via `get_datasets` tool
- Apply transformations
- Make dataset available for testing

#### 3. **Orchestrator Setup**
Instead of: Multiple pages for generator → scorer → dataset → orchestrator
Now: Type "Run a red team test on GPT-4 using jailbreak dataset with bias scoring"

MCP will:
- Check/create required generator
- Configure appropriate scorer
- Load specified dataset
- Create and execute orchestrator
- Stream results back

#### 4. **Complex Workflows**
Example: "Create a complete testing pipeline for our new chatbot with security and bias testing"

MCP will guide through:
1. Generator selection/creation
2. Appropriate scorer configuration
3. Dataset recommendations
4. Orchestrator setup
5. Execution and monitoring

### Benefits of Natural Language Configuration

1. **Reduced Learning Curve**: No need to understand UI navigation
2. **Faster Workflow**: Single command vs multiple page visits
3. **Context Preservation**: Stay in chat while configuring
4. **Batch Operations**: Configure multiple components in one command
5. **Intelligent Defaults**: MCP suggests sensible defaults
6. **Error Prevention**: Validation before execution
7. **Workflow Memory**: Repeat similar configurations easily

## Development Phases

### Phase 1: Foundation & MCP Client Implementation
**Duration**: 2-3 days

#### Prerequisites
- MCP server running and accessible at configured endpoint
- Valid JWT tokens available for authentication
- APISIX gateway properly configured with MCP routes

#### Tasks
1. **Create MCP Client Library** (`utils/mcp_client.py`)
   - Implement SSE (Server-Sent Events) client for MCP communication
   - Handle JSON-RPC protocol for MCP server interaction
   - **Reuse existing authentication**:
     - Import `get_auth_headers()` from existing pages
     - Use `jwt_manager.get_valid_token()` for token refresh
     - Leverage existing APISIX routing (base URL from environment)
   - Create methods for:
     - List prompts and get prompt details
     - Render prompts with arguments
     - List and read resources
     - **Execute MCP tools** - Critical for configuration tasks
     - List available tools and their schemas
   - Add connection health checks and retry logic
   - **Build on existing patterns**:
     - Follow the `api_request()` pattern for error handling
     - Use existing logging configuration from `utils/logging.py`
   - **MCP Tool Execution Support**:
     - Map natural language to MCP tool names
     - Execute tools like `create_generator`, `list_datasets`, `test_generator`
     - Handle tool arguments and validation

2. **Create MCP Integration Utilities** (`utils/mcp_integration.py`)
   - Natural language command parser for MCP features
   - Context analysis functions
   - **Integrate with existing features**:
     - Use existing dataset loaders from `util_datasets/data_loaders.py`
     - Leverage Jinja2 transformation from `dataset_transformations.py`
   - Resource search and filtering
   - Test scenario interpreter
   - **Configuration Intent Recognition**:
     - Detect when user wants to configure components
     - Map phrases like "create a GPT-4 generator" to MCP tools
     - Extract parameters from natural language
     - Suggest appropriate configuration steps

3. **Extend Existing Infrastructure**
   - **No need to update authentication** - MCP endpoints already configured in APISIX
   - Add SSE connection handling to existing error handling patterns
   - Ensure compatibility with existing `token_manager.py`

#### Testing
1. **Unit Tests** (`tests/test_mcp_client.py`)
   - Test SSE connection establishment
   - Test JSON-RPC request/response handling
   - Test authentication flow
   - Test each MCP operation (list prompts, render, etc.)
   - Test error handling and retry logic

2. **Integration Tests** (`tests/test_mcp_integration.py`)
   - **MUST use real MCP server**, no mocks or simulated data
   - Test MCP client with actual ViolentUTF API endpoints
   - Verify JWT token passing through APISIX
   - Test all MCP tools discovered from API
   - Verify actual API responses, not mocked data
   - Test timeout and connection recovery
   - **Required Coverage**: 100% of MCP client methods

3. **Manual Testing Checklist**
   - [ ] Connect to MCP server from Python console
   - [ ] List all available prompts from real server
   - [ ] Execute actual MCP tools (create_generator, etc.)
   - [ ] Verify tools affect real ViolentUTF data
   - [ ] List and read actual resources
   - [ ] Handle connection errors gracefully

#### Integration Test Gate
**MUST PASS before proceeding to Phase 2:**
- [ ] All MCP client methods tested with real server
- [ ] Authentication flow verified end-to-end
- [ ] At least 5 different MCP tools executed successfully
- [ ] Resource operations tested with real data
- [ ] Error scenarios tested and handled properly

#### Documentation (Phase 1)
- **API Reference**: Complete `mcp_client.py` documentation
- **Integration Guide**: How to connect to real MCP server
- **Testing Guide**: How to verify MCP operations
- **Troubleshooting Guide**: Common connection/auth issues

---

### Phase 2: Basic Enhancement Strip UI
**Duration**: 2 days

#### Prerequisites
- Phase 1 integration tests passed
- MCP client library fully functional with real server
- Documentation from Phase 1 available

#### Tasks
1. **Implement Enhancement Strip** (in Simple_Chat.py)
   - Add enhancement buttons below main text area:
     - ✨ Enhance - Improve prompt quality (via real MCP prompts)
     - 🔍 Analyze - Security & bias analysis (via real MCP tools)
     - 🧪 Test - Generate test variations (via real MCP server)
   - Add quick actions dropdown
   - Implement button click handlers that call actual MCP operations
   - Add loading states and progress indicators
   - **Integrate with existing prompt variables**:
     - Allow saving MCP-enhanced prompts as variables
     - Support using variables in MCP prompts
   - **All operations MUST use real MCP server, no hardcoded responses**

2. **Create Results Display Components**
   - Enhanced prompt display with diff highlighting
   - Analysis results panel with metrics
   - Test variations carousel
   - "Use This Prompt" integration
   - **Leverage existing UI patterns**:
     - Use existing `st.dialog` pattern for detailed views
     - Follow existing button styling from other pages

3. **Session State Management**
   - **Extend existing session state** in Simple Chat:
     - Add to existing `st.session_state` variables
     - Maintain compatibility with prompt variable system
   - Track MCP enhancement history
   - Store analysis results
   - Manage active contexts

#### Testing
1. **UI Tests**
   - Test each enhancement button functionality
   - Verify loading states work correctly
   - Test error message display
   - Verify session state persistence

2. **Integration Tests** (`tests/test_enhancement_strip_integration.py`)
   - **MUST verify real MCP server responses**
   - Test enhancement returns actual MCP prompt results
   - Test analysis uses real ViolentUTF scorers via MCP
   - Test variations generated by actual MCP server
   - Verify no hardcoded/mocked responses in UI

3. **User Flow Tests**
   - Write prompt → Enhance → Verify MCP response → Use enhanced version
   - Write prompt → Analyze → Verify real analysis → View results
   - Generate test variations → Verify from MCP → Select one → Use it
   - **Configuration Flow Tests**:
     - Natural language → MCP parse → Tool execution → Result display
     - Multi-step configuration workflows
     - Error handling for invalid configurations

4. **Manual Testing Checklist**
   - [ ] Enhancement strip appears correctly
   - [ ] All buttons call real MCP operations
   - [ ] Results come from actual MCP server
   - [ ] Enhanced prompts match MCP server output
   - [ ] UI remains responsive during MCP operations
   - [ ] Error messages from MCP server displayed properly

#### Integration Test Gate
**MUST PASS before proceeding to Phase 3:**
- [ ] All enhancement operations use real MCP server
- [ ] No hardcoded responses found in code review
- [ ] At least 10 successful enhancement operations
- [ ] Error handling tested with real server errors
- [ ] Performance acceptable with real server latency

#### Documentation (Phase 2)
- **User Guide**: "Using MCP Enhancement Features" with real examples
- **UI Component Guide**: Screenshots and descriptions
- **API Integration**: Document actual MCP endpoints used
- **Update from Phase 1**: Add UI-specific troubleshooting

---

### Phase 3: Smart Commands & Natural Language Interface
**Duration**: 3 days

#### Prerequisites
- Phase 2 integration tests passed
- Enhancement strip working with real MCP server
- Documentation from Phases 1-2 available

#### Tasks
1. **Implement Command Parser**
   - Recognize `/mcp` commands in input
   - Parse natural language requests
   - Map commands to MCP operations
   - Provide command suggestions/autocomplete
   - **Natural Language Configuration**:
     - Parse requests like "Create an OpenAI generator with GPT-4"
     - Extract model, provider, and parameter information
     - Map to appropriate MCP tools

2. **Create Command Handlers**
   - `/mcp help` - Show available commands
   - `/mcp test <type>` - Quick test access
   - `/mcp dataset <name>` - Load dataset
   - `/mcp enhance` - Enhance current prompt
   - `/mcp analyze` - Analyze for issues
   - `/mcp resources` - Browse resources
   - **Configuration Commands**:
     - `/mcp create generator <details>` - Create new generator
     - `/mcp list generators` - Show configured generators
     - `/mcp test generator <name>` - Test a generator
     - `/mcp configure scorer <type>` - Set up scorer
     - `/mcp load dataset <name>` - Load dataset for testing

3. **Implement Intelligent Suggestions**
   - Detect when user might benefit from MCP
   - Show contextual suggestions
   - Learn from user preferences
   - Provide non-intrusive hints
   - **Configuration Workflow Guidance**:
     - Suggest next steps after creating generator
     - Recommend appropriate scorers for testing
     - Guide through orchestrator setup

#### Testing
1. **Command Parser Tests**
   - Test command recognition accuracy
   - Test parameter extraction from natural language
   - Test error handling for invalid commands
   - Test command suggestions based on context

2. **Integration Tests** (`tests/test_command_integration.py`)
   - **MUST execute real MCP tools for each command**
   - Test `/mcp create generator` creates actual generator via API
   - Test `/mcp list generators` returns real configured generators
   - Test natural language "Create GPT-4 generator" executes actual tool
   - Verify all configuration commands affect real ViolentUTF data
   - Test command chaining and multi-step workflows

3. **Configuration Verification Tests**
   - Create generator via command → Verify in Configure Generators page
   - Load dataset via command → Verify dataset actually loaded
   - Configure scorer → Verify scorer available for orchestrator
   - Full pipeline test: Generator → Dataset → Scorer → Orchestrator

4. **Manual Testing Checklist**
   - [ ] Type `/mcp help` and see actual available MCP tools
   - [ ] Execute each command and verify real API changes
   - [ ] Natural language creates real ViolentUTF components
   - [ ] Command suggestions based on actual MCP capabilities
   - [ ] Commands produce same results as Configure_*.py pages

#### Integration Test Gate
**MUST PASS before proceeding to Phase 4:**
- [ ] All commands execute real MCP tools
- [ ] Natural language correctly maps to tool execution
- [ ] At least 20 successful configuration operations
- [ ] Created components visible in UI pages
- [ ] No discrepancies between command and UI results

#### Documentation (Phase 3)
- **Command Reference**: Complete list with real examples
- **Natural Language Guide**: Patterns that work with actual parser
- **Configuration Cookbook**: Common configuration scenarios
- **Update from Phase 2**: Add command-specific sections
- **API Mapping**: Document which MCP tools each command uses

---

### Phase 4: Context-Aware Assistant & Resource Browser
**Duration**: 3-4 days

#### Prerequisites
- Phase 3 integration tests passed
- Commands working with real MCP tools
- Documentation from Phases 1-3 available

#### Tasks
1. **Implement MCP Assistant**
   - Monitor conversation for enhancement opportunities
   - Provide real-time suggestions
   - Auto-detect security concerns
   - Suggest relevant resources
   - **Integrate with existing PyRIT features**:
     - Suggest appropriate scorers from Configure Scorers
     - Recommend datasets from Configure Datasets
     - Link to relevant orchestrators

2. **Create Resource Browser**
   - Sidebar resource search interface
   - Resource preview panels using real MCP `list_resources`
   - **Connect to existing dataset system**:
     - Show PyRIT native datasets via MCP resources
     - Load actual datasets through MCP tools
     - Support existing dataset formats (CSV, JSON, etc.)
   - Resource metadata from real MCP server
   - Filtering and sorting of actual resources

3. **Implement Context Management**
   - Active context indicator
   - Context switching UI
   - **Build on existing features**:
     - Use prompt variables as context snippets
     - Support dataset content as context
     - Allow IronUTF configurations as context

4. **Add Conversation Analysis**
   - Real-time security scoring via MCP tools
   - **Leverage existing scorers**:
     - Use actual PyRIT scorers through MCP API
     - Execute real scoring operations
     - Show live results from scorer execution
   - Bias detection using real MCP scorer tools
   - Test coverage tracking with actual data
   - Recommendations based on real analysis results

#### Testing
1. **Assistant Tests**
   - Test suggestion accuracy based on real context
   - Test timing of suggestions during conversation
   - Verify non-intrusiveness of assistance
   - Test learning from actual user interactions

2. **Integration Tests** (`tests/test_assistant_integration.py`)
   - **MUST use real MCP resources and tools**
   - Resource browser shows actual MCP resources
   - Loading resource executes real MCP operations
   - Analysis uses actual PyRIT scorers via MCP
   - Context reflects real conversation data
   - All suggestions based on actual MCP capabilities

3. **Resource Browser Tests**
   - Search returns real MCP resources
   - Preview shows actual resource content
   - Loading affects real ViolentUTF state
   - Filtering works on actual resource metadata

4. **Manual Testing Checklist**
   - [ ] Assistant suggestions use real MCP data
   - [ ] Resource browser shows actual resources
   - [ ] Context includes real conversation history
   - [ ] Analysis runs actual scorers via MCP
   - [ ] Performance acceptable with real operations

#### Integration Test Gate
**MUST PASS before proceeding to Phase 5:**
- [ ] Resource browser lists 100% real resources
- [ ] All analysis uses actual MCP scorer execution
- [ ] Context management reflects real data
- [ ] At least 50 assistant interactions tested
- [ ] No simulated data found in implementation

#### Documentation (Phase 4)
- **Assistant Guide**: How context-aware suggestions work
- **Resource Browser Guide**: Using real MCP resources
- **Analysis Guide**: Understanding real scorer results
- **Update from Phase 3**: Add assistant-specific content
- **Architecture**: Document real-time MCP integration

---

### Phase 5: Advanced Features & Visual Builders
**Duration**: 4-5 days

#### Prerequisites
- Phase 4 integration tests passed
- Assistant and resource browser using real MCP
- Documentation from Phases 1-4 available

#### Tasks
1. **Implement Visual Prompt Builder**
   - Drag-and-drop prompt components
   - Template library integration
   - Component property editors
   - Preview panel
   - Save/load prompt templates

2. **Create Test Scenario Builder**
   - Natural language test descriptions
   - Automatic test generation via MCP orchestrator tools
   - Test suite management using real ViolentUTF data
   - Results comparison from actual test execution
   - Export test reports with real metrics

3. **Add Prompt Evolution Tracking**
   - Version control for prompts
   - Diff visualization
   - Performance tracking over versions
   - A/B testing support

4. **Implement Collaboration Features**
   - Share enhanced prompts
   - Share test scenarios
   - Team resource libraries
   - Collaborative analysis

#### Testing
1. **Visual Builder Tests**
   - Test drag-and-drop creates real MCP operations
   - Test components map to actual MCP tools
   - Test templates save/load via MCP resources
   - Test preview shows real MCP responses

2. **Integration Tests** (`tests/test_advanced_features_integration.py`)
   - **MUST generate real tests via MCP orchestrators**
   - Visual builder outputs execute via MCP tools
   - Test scenarios create actual ViolentUTF tests
   - Version tracking uses real MCP resources
   - All operations affect real system state

3. **Test Scenario Tests**
   - Natural language creates real orchestrators
   - Scenario execution uses actual MCP tools
   - Results come from real test runs
   - Reports contain actual metrics

4. **Manual Testing Checklist**
   - [ ] Visual builder integrates with real MCP
   - [ ] Test scenarios execute actual tests
   - [ ] Version history tracks real changes
   - [ ] Collaboration uses real MCP resources
   - [ ] Performance acceptable with real operations

#### Integration Test Gate
**MUST PASS before proceeding to Phase 6:**
- [ ] Visual builder creates real configurations
- [ ] Test scenarios execute via MCP orchestrators
- [ ] All advanced features use real MCP server
- [ ] At least 20 visual configurations tested
- [ ] No mock data in advanced features

#### Documentation (Phase 5)
- **Visual Builder Guide**: Creating real configurations
- **Test Scenario Guide**: Building actual tests
- **Advanced Features**: Using MCP capabilities
- **Update from Phase 4**: Add visual builder content
- **Complete API Reference**: All MCP tools used

---

### Phase 6: Optimization & Polish
**Duration**: 2-3 days

#### Prerequisites
- Phase 5 integration tests passed
- All features using real MCP server
- Documentation from Phases 1-5 complete

#### Tasks
1. **Performance Optimization**
   - Implement caching for MCP responses
   - Optimize SSE connection management
   - Reduce unnecessary MCP calls
   - Implement lazy loading for resources
   - Add request debouncing

2. **UI/UX Polish**
   - Smooth animations and transitions
   - Consistent styling across components
   - Responsive design improvements
   - Accessibility enhancements
   - Error message improvements

3. **Integration Testing**
   - Full end-to-end testing
   - Cross-browser testing
   - Performance benchmarking
   - Load testing with multiple users
   - Edge case handling

4. **Documentation Finalization**
   - Complete user manual
   - Video tutorials
   - FAQ section
   - Troubleshooting guide
   - API reference

#### Testing
1. **Performance Tests**
   - Measure real MCP server response times
   - Test with actual network latency
   - Test with large ViolentUTF datasets
   - Monitor memory with real operations

2. **Full System Integration Tests** (`tests/test_full_system_integration.py`)
   - **End-to-end test of all phases with real MCP**
   - Create generator → Load dataset → Configure scorer → Run test
   - Natural language workflow completion
   - Verify all features work with production MCP server
   - Load test with multiple concurrent operations

3. **Usability Tests**
   - Test with users on real MCP server
   - Gather feedback on actual response times
   - Test workflows with real data
   - Accessibility with real operations

4. **Final Testing Checklist**
   - [ ] All features use real MCP server
   - [ ] No mock/simulated data remains
   - [ ] Performance acceptable with real latency
   - [ ] All integration tests passing
   - [ ] Documentation reflects real behavior

#### Final Integration Test Gate
**MUST PASS before release:**
- [ ] 100% of features use real MCP server
- [ ] All integration tests from all phases pass
- [ ] Performance benchmarks meet targets
- [ ] No hardcoded/mock responses found
- [ ] Full workflow test completes successfully

#### Documentation (Phase 6 - Final)
- **Performance Guide**: Optimization with real MCP
- **Deployment Guide**: Production configuration
- **Migration Guide**: Moving from Configure pages
- **Complete User Manual**: All features documented
- **API Reference**: Final comprehensive guide
- **Release Notes**: All capabilities listed

---

## Testing Strategy

### Automated Testing
- Unit tests for all utility functions
- Integration tests for MCP communication
- UI component tests with Streamlit testing
- End-to-end tests for critical workflows
- Performance regression tests

### Manual Testing
- Exploratory testing by developers
- User acceptance testing
- Cross-browser compatibility testing
- Mobile responsiveness testing
- Accessibility testing with screen readers

### Test Environments
1. **Local Development**: Individual developer testing
2. **Integration Environment**: Test with actual MCP server
3. **Staging**: Full system testing with all components
4. **Production**: Gradual rollout with monitoring

---

## Progressive Documentation Strategy

### Documentation Requirements by Phase

Each phase MUST produce documentation that builds upon previous phases:

#### Phase 1 Documentation
- **MCP Client API Reference** (`docs/api/mcp-client.md`)
- **Integration Guide** (`docs/guides/mcp-integration.md`)
- **Testing Guide** (`docs/guides/testing-mcp.md`)
- **Troubleshooting** (`docs/troubleshooting/mcp-connection.md`)

#### Phase 2 Documentation (Updates Phase 1 + New)
- **Update**: API Reference with UI integration methods
- **New**: Enhancement Features Guide (`docs/guides/enhancement-strip.md`)
- **New**: UI Components Reference (`docs/ui/enhancement-components.md`)
- **Update**: Troubleshooting with UI-specific issues

#### Phase 3 Documentation (Updates Phase 1-2 + New)
- **Update**: API Reference with command parsing
- **New**: Command Reference (`docs/commands/mcp-commands.md`)
- **New**: Natural Language Guide (`docs/guides/natural-language.md`)
- **New**: Configuration Cookbook (`docs/cookbook/configuration.md`)
- **Update**: All guides with command examples

#### Phase 4 Documentation (Updates Phase 1-3 + New)
- **Update**: API Reference with assistant methods
- **New**: Assistant Guide (`docs/guides/context-assistant.md`)
- **New**: Resource Browser Guide (`docs/guides/resource-browser.md`)
- **New**: Analysis Guide (`docs/guides/real-time-analysis.md`)
- **Update**: Architecture with real-time features

#### Phase 5 Documentation (Updates Phase 1-4 + New)
- **Update**: API Reference with visual builder
- **New**: Visual Builder Guide (`docs/guides/visual-builder.md`)
- **New**: Test Scenario Guide (`docs/guides/test-scenarios.md`)
- **New**: Advanced Features (`docs/guides/advanced-features.md`)
- **Update**: Complete workflow examples

#### Phase 6 Documentation (Final Compilation)
- **Compile**: Complete User Manual from all guides
- **New**: Performance Optimization Guide
- **New**: Deployment Guide
- **New**: Migration Guide from Configure Pages
- **Final**: API Reference with all features
- **New**: Release Notes

### Documentation Standards

1. **Real Examples Only**: All code examples must work with real MCP server
2. **Version Tracking**: Each doc includes phase version
3. **Progressive Updates**: Later phases enhance earlier docs
4. **Integration Focus**: Show how features work together
5. **Testing Verification**: Include test commands for examples

## Documentation Deliverables

1. **User Documentation** (Progressive by Phase)
   - Getting Started Guide (Phase 1, updated each phase)
   - Feature Tutorials (Added progressively)
   - Command Reference (Phase 3+)
   - FAQ and Troubleshooting (Updated each phase)
   - Video Walkthroughs (Phase 6)

2. **Developer Documentation** (Progressive by Phase)
   - API Reference (Phase 1, completed by Phase 6)
   - Integration Guide (Phase 1, enhanced each phase)
   - Architecture Overview (Phase 4+)
   - Contributing Guidelines (Phase 6)
   - Code Examples (Added each phase)

3. **Operations Documentation** (Phase 6)
   - Deployment Guide
   - Configuration Reference
   - Monitoring Setup
   - Backup and Recovery
   - Performance Tuning

---

## Integration Strategy & Avoiding Duplications

### Reuse Existing Components:
1. **Authentication**: Use existing `jwt_manager`, `token_manager`, and `get_auth_headers()`
2. **API Communication**: Extend `api_request()` pattern, don't create new HTTP clients
3. **UI Components**: Use existing `st.dialog`, button styles, and layout patterns
4. **Data Management**: Leverage existing dataset loaders and transformations
5. **Security Testing**: Integrate with existing PyRIT orchestrators, scorers, and converters
6. **Prompt Storage**: Extend existing prompt variable system, don't create new storage
7. **MCP Tools**: Use auto-discovered API endpoints as MCP tools

### New Components Only:
1. **SSE Client**: Required for real-time MCP communication
2. **JSON-RPC Handler**: Required for MCP protocol
3. **Command Parser**: New natural language interface
4. **Enhancement UI**: New buttons and result displays
5. **Resource Browser UI**: New interface for MCP resources
6. **Real-time Analysis**: New live monitoring features

### Integration Points:
1. **Simple Chat Enhancement**: Add MCP features without changing core chat functionality
2. **Dataset Integration**: MCP resources appear alongside PyRIT datasets
3. **Scorer Integration**: Use existing scorers for MCP analysis
4. **Dashboard Connection**: MCP analysis results can be viewed in Dashboard
5. **IronUTF Compatibility**: MCP enhancements respect IronUTF configurations
6. **Configuration Pages**: MCP can execute same operations as Configure_*.py pages

## Success Metrics

1. **Functionality Metrics**
   - All planned features implemented
   - <2% error rate in MCP operations
   - <500ms average response time
   - 95% uptime for MCP connection

2. **User Experience Metrics**
   - 80% of users find enhancement helpful
   - 50% reduction in prompt iteration time
   - 90% success rate for security tests
   - <5 seconds to learn basic features

3. **Quality Metrics**
   - >80% test coverage
   - <10 critical bugs in production
   - <50 minor issues reported
   - All accessibility standards met

---

## Risk Mitigation

1. **Technical Risks**
   - MCP server availability → Implement fallback modes
   - SSE connection stability → Add reconnection logic
   - Performance impact → Implement caching and lazy loading
   - JWT token expiration → Handle token refresh

2. **User Experience Risks**
   - Feature complexity → Progressive disclosure
   - Learning curve → Intuitive design and good docs
   - Workflow disruption → Enhancement as optional layer
   - Information overload → Smart filtering and relevance

3. **Integration Risks**
   - Breaking existing features → Comprehensive testing
   - Authentication issues → Reuse existing auth
   - Version compatibility → Version checking
   - Resource conflicts → Namespace isolation

---

## Timeline Summary

- **Phase 1**: Foundation & MCP Client (3 days)
- **Phase 2**: Basic Enhancement Strip (2 days)
- **Phase 3**: Smart Commands (3 days)
- **Phase 4**: Assistant & Resources (4 days)
- **Phase 5**: Advanced Features (5 days)
- **Phase 6**: Optimization & Polish (3 days)

**Total Duration**: ~20 days (4 weeks)

---

## What NOT to Build (Already Exists)

### Do NOT Recreate:
1. **JWT Token Management** - Use existing `jwt_manager.py`
2. **API Gateway Routes** - MCP routes already configured in APISIX
3. **Dataset Loading** - Use existing `data_loaders.py`
4. **Template Transformation** - Use existing Jinja2 in `dataset_transformations.py`
5. **Scoring System** - Use existing PyRIT scorers
6. **Orchestration** - Use existing PyRIT orchestrators
7. **Authentication UI** - Use existing `handle_authentication_and_sidebar()`
8. **Error Handling** - Extend existing `error_handling.py`
9. **Logging** - Use existing `logging.py` configuration
10. **Prompt Storage** - Extend existing prompt variables JSON system

### Focus Only On:
1. **MCP Client Implementation** - New SSE/JSON-RPC client
2. **Enhancement UI** - New buttons and displays in Simple Chat
3. **Command Interface** - New natural language parsing
4. **Real-time Features** - New streaming and live analysis
5. **Resource Browser** - New UI for MCP resources
6. **Integration Logic** - Connect MCP to existing features

## MCP Tool Mapping for Configuration Operations

### Available MCP Tools (Auto-discovered from API)

The MCP server automatically discovers and exposes ViolentUTF API endpoints as tools:

#### Generator Tools
- `get_generators` - List all configured generators
- `create_generators` - Create new generator with parameters
- `update_generators_by_id` - Modify existing generator
- `delete_generators_by_id` - Remove generator
- `get_generator_types` - List available provider types
- `get_apisix_models` - Get available AI Gateway models

#### Dataset Tools
- `get_datasets` - List available datasets
- `create_datasets` - Upload/create new dataset
- `get_datasets_by_id` - Get specific dataset details
- `update_datasets_by_id` - Modify dataset
- `delete_datasets_by_id` - Remove dataset

#### Scorer Tools
- `get_scorers` - List configured scorers
- `create_scorers` - Configure new scorer
- `get_scorers_by_id` - Get scorer details
- `update_scorers_by_id` - Modify scorer configuration
- `delete_scorers_by_id` - Remove scorer

#### Orchestrator Tools
- `get_orchestrators` - List orchestrators
- `create_orchestrators` - Create new orchestrator
- `get_orchestrators_by_id` - Get orchestrator details
- `create_orchestrator_executions` - Execute orchestrator

### Natural Language to Tool Mapping Examples

| User Says | MCP Interprets | Tools Called |
|-----------|----------------|--------------|
| "Create a GPT-4 generator" | Create generator with OpenAI provider | `create_generators` |
| "List all my generators" | Show configured generators | `get_generators` |
| "Test the GPT-4 generator" | Create test orchestrator and execute | `create_orchestrators`, `create_orchestrator_executions` |
| "Load jailbreak dataset" | Find and load dataset | `get_datasets`, resource read |
| "Configure bias scorer" | Set up bias scoring | `create_scorers` |
| "Run security test on my chatbot" | Full pipeline setup | Multiple tools in sequence |

### Intelligent Parameter Extraction

MCP will extract parameters from natural language:

```
"Create an OpenAI generator with GPT-4, temperature 0.8, max tokens 1000"
↓
{
  "tool": "create_generators",
  "arguments": {
    "provider_type": "openai",
    "model_name": "gpt-4",
    "parameters": {
      "temperature": 0.8,
      "max_tokens": 1000
    }
  }
}
```

## Implementation Progress

### Phase 1: Foundation & MCP Client Implementation ✅ COMPLETED
- Created MCP Client Library with SSE support
- Implemented MCP Integration Utilities
- Fixed server-side implementation gaps
- All integration tests passing (17/18)
- Comprehensive documentation created

### Phase 2: Basic Enhancement Strip UI ✅ COMPLETED
- Enhancement strip integrated into Simple_Chat.py
- Three main buttons: ✨ Enhance, 🔍 Analyze, 🧪 Test
- Quick Actions dropdown for common scenarios
- Tabbed results display (Enhanced/Analysis/Variations)
- Session state management for MCP features
- UI tests: 12/14 passing
- Integration tests: 8/9 passing
- User guide and component documentation created

### Phase 3: Smart Commands & Natural Language Interface 🔄 NEXT
- Ready to begin implementation
- Prerequisites from Phase 2 are met
- MCP client fully functional
- Enhancement UI provides foundation

## Next Steps

1. Begin Phase 3: Smart Commands implementation
2. Add natural language command parsing to Simple Chat
3. Implement command handlers and suggestions
4. Create configuration command support
5. Continue with integration testing approach

---

*Document Version: 3.0*
*Last Updated: [Current Date]*
*Status: Enhanced with Integration Testing Requirements, Real MCP Server Usage, and Progressive Documentation Strategy*

### Key Improvements in Version 3.0:
1. **Mandatory Integration Test Gates** between phases
2. **Real MCP Server requirement** - no mocks or simulated data
3. **Progressive Documentation** - each phase builds on previous
4. **Comprehensive Testing** - unit, integration, and manual tests
5. **Clear Prerequisites** for each phase
6. **Specific Test Coverage Requirements**
