# Advanced Dashboard - Report Setup Page

## Overview

The Report Setup page is a comprehensive interface for managing COB (Close of Business) report templates, generating reports, and configuring automated report schedules. This page will be positioned under the Advanced Dashboard section of the ViolentUTF Streamlit application.

## Main Features

### 1. Template Management Section

#### 1.1 Template Gallery - Red Teaming Focused

**Core Metadata Structure:**
- **Core Identifiers**: ID, name, description, version (e.g., 1.0.0)
- **Red Teaming Classification**: 
  - Testing category (Security/Safety/Reliability/Robustness/Compliance)
  - Target model types (LLM/Vision/Multimodal/Embedding/Custom)
  - Attack categories (Prompt Injection/Jailbreak/Data Leakage/Hallucination/Bias/Toxicity)
  - Compliance frameworks (OWASP LLM/NIST AI RMF/ISO 23053/EU AI Act)
  - Severity focus (Critical/High/Medium/Low/Informational)
- **Testing Configuration**:
  - Scanner compatibility (PyRIT scorers/orchestrators, Garak probes/detectors)
  - Test data requirements (dataset types, minimum samples)
  - Report sections (vulnerability assessment, attack success rates, defense recommendations)
- **Technical Metadata**:
  - AI analysis requirements (models, tokens, scan result processing)
  - Output formats (PDF/JSON/Markdown)
  - Estimated generation time
  - Template complexity level

**Search & Filter System:**
- **Text Search**: Across names, descriptions, attack categories, testing notes
- **Primary Filters**:
  - Testing categories and target models
  - Attack vectors with visual indicators
  - Scanner type (PyRIT/Garak/Both/Any)
  - Compliance framework with coverage display
- **Advanced Filters**:
  - Severity levels (default: Critical & High)
  - Report components selection
  - Complexity slider
- **Quick Scenarios**: Security Audit, Injection Tests, Safety Testing, Compliance, Full Assessment, Quick Scan
- **Sort Options**: Best Match, Severity Focus, Recently Updated, Name, Complexity

**Gallery Implementation:**
- **Card Layout**: Severity indicators, testing badges, scanner compatibility
- **Key Metrics Display**: Scanner type, complexity, report sections, generation time
- **Compliance Badges**: Framework coverage indicators
- **Action Buttons**: Use Template, Preview, Edit, Clone

#### 1.2 Template Editor - Streamlit-Compatible Implementation

**Visual Block Editor Architecture:**
- **Streamlit-Native Approach**: Uses expandable sections, button-based reordering, and session state management
- **Block Management**: Add/remove blocks, reorder with up/down buttons, inline configuration
- **Real-time Preview**: Side panel showing template structure and sample output

**Red Team Report Block Types:**

1. **Executive Summary Block**
   - Summary components: Overall Risk Score, Critical Vulnerabilities Count, Attack Success Rate, Top Attack Vectors, Compliance Status, Key Recommendations
   - Auto-summarize from AI analysis and security metrics blocks
   - Highlight threshold settings (Critical Only/High and Above/Medium and Above)

2. **AI Analysis Block - Scan Result Integration**
   - **Analysis Focus**: Vulnerability assessment, attack pattern analysis, defense recommendations, compliance gaps, risk prioritization
   - **Scan Result Sources**: PyRIT results, Garak results, custom scanner output, previous reports
   - **Prompt Variables**:
     - Scanner variables: {{scanner_type}}, {{target_model}}, {{scan_date}}, {{total_tests}}, {{successful_attacks}}
     - Result variables: {{scan_results}}, {{vulnerability_matrix}}, {{attack_chains}}, {{scorer_outputs}}, {{probe_results}}
   - **Result Processing**: Include raw results option, severity filtering, aggregation levels
   - **AI Providers**: OpenAI GPT-4, Anthropic Claude, GSAi, Local Model
   - **Output Format**: Structured Analysis, Narrative Report, Bullet Points

3. **Security Metrics Block - Compatibility Matrix Integration**
   - **Metric Sources**: Compatibility Matrix Results, PyRIT Scan Metrics, Garak Test Metrics, Combined
   - **Compatibility Matrix Metrics**:
     - Overall Compatibility Score
     - Framework Coverage (OWASP/NIST/ISO)
     - Attack Success Rates by Category
     - Vulnerability Distribution
     - Risk Score Breakdown
     - Compliance Percentage
     - Defense Effectiveness
   - **Visualizations**: Metric Cards, Risk Heatmap, Attack Success Chart, Vulnerability Timeline, Compliance Radar
   - **Severity Thresholds**: Critical (≥9.0), High (≥7.0), Medium (≥4.0), Low (≥0.0)

4. **Attack Results Table**
   - **Data Sources**: PyRIT Attack Results, Garak Probe Results, Combined Results
   - **Display Columns**: Attack Type, Target Component, Success Status, Severity Score, Response Analysis
   - **Filters**: Severity Level, Attack Success, Attack Category, Time Range
   - **Highlighting Rules**: Critical severity (red), Successful attacks (bold), New vulnerabilities (yellow)

5. **Custom Content Block - Simplified**
   - **Markdown-only** content editor
   - **Available Variables**:
     - Scan Results: {{total_tests}}, {{successful_attacks}}, {{failure_rate}}
     - Vulnerabilities: {{total_vulnerabilities}}, {{critical_count}}, {{high_count}}
     - Model Info: {{target_model}}, {{model_version}}, {{deployment_date}}
     - Test Info: {{test_date}}, {{scanner_type}}, {{test_duration}}
     - Metrics: {{risk_score}}, {{compliance_score}}, {{defense_rating}}

**Scan Result Variable System:**
- **Variable Registry**: PyRIT variables, Garak variables, Compatibility Matrix variables, Common variables
- **Variable Helper UI**: Grouped by source, click-to-insert functionality, usage examples
- **Conditional Display**: Support for if-statements based on variable values

#### 1.3 Simplified Template Versioning

**Basic Version Control:**
- **Version Format**: Simple MAJOR.MINOR.PATCH (e.g., 1.2.0)
- **Version Types**: 
  - Patch: Bug fixes, minor updates
  - Minor: New features, backwards compatible
  - Major: Breaking changes
- **Version Storage**: Each version saves a complete template snapshot with timestamp and change notes

**Version Management UI:**
- **Current Version Display**: Shows active version with creation info
- **Create New Version**: 
  - Select change type (patch/minor/major)
  - Add change notes (required)
  - Preview new version number
  - One-click creation
- **Version History**: 
  - Simple list of last 10 versions
  - Shows version number, change notes, author, date
  - Restore button to revert to any previous version

**Streamlined Features:**
- No complex branching or merging
- No approval workflows (can be added later if needed)
- Simple restore functionality instead of migration tools
- Basic change notes instead of detailed changelogs

### 2. Report Generation Section

#### 2.1 Manual Report Generation - Single Report Focus

**Step-Based Workflow:**
1. **Template Selection** → 2. **Scan Result Selection** → 3. **Report Configuration** → 4. **Generation Progress**

**Step 1: Template Selection**
- **Search and Filter**: Quick search with category filtering
- **Template Cards**: Display severity indicators, scanner compatibility, complexity level
- **Template Preview**: Expandable details showing blocks and features
- **Visual Selection**: Clear indication of selected template

**Step 2: Scan Result Selection (Dashboard Filter Style)**
- **Search Bar**: Search by model name, date, scanner type
- **Quick Filters**: "All Scans", "Last 7 Days", "Critical Only", "PyRIT Only", "Garak Only"
- **Advanced Filters** (Expandable):
  - Time Range: Date range picker for scan dates
  - Scanner Type: Multi-select (PyRIT, Garak, Custom)
  - Target Models: Multi-select from scanned models
  - Scan Status: Completed, Failed, Partial
  - Severity Levels: Multi-select with Critical/High default
  - Attack Categories: Prompt Injection, Jailbreak, etc.
  - Results Thresholds: Min vulnerabilities, success rate
- **Scan Result Cards**:
  - Scanner icon and model name
  - Vulnerability summary (Critical/High/Medium counts)
  - Success rate metrics
  - Attack category badges
  - Selection checkbox with visual feedback
  - Expandable details (configuration, key findings)
- **Bulk Selection**: "Select All" and "Clear Selection" buttons

**Step 3: Report Configuration**
- **Configuration Tabs**:
  1. **Basic Settings**:
     - Report name with smart defaults
     - Report period (use scan dates or custom)
     - Output formats (PDF, JSON, Markdown)
     - Report focus (Comprehensive, Executive, Technical, Compliance)
  
  2. **Block Configuration**:
     - Available variables display from selected scans
     - Per-block settings based on block type:
       - Executive Summary: Component selection, highlight threshold
       - AI Analysis: Focus selection, data inclusion, custom prompts
       - Security Metrics: Metric selection, visualization types
       - Attack Results: Severity filter, column selection, row limits
       - Custom Content: Markdown editor with variable insertion
  
  3. **AI Settings**:
     - Global provider selection (OpenAI, Anthropic, GSAi, Local)
     - Model parameters (temperature, etc.)
     - Processing options (parallel, confidence scores, retry)
     - Per-block overrides for multiple AI blocks
  
  4. **Advanced Options**:
     - Performance settings (timeout, memory)
     - Data processing (deduplication, aggregation)
     - Export settings (PDF style, ToC, appendix)

**Step 4: Generation Progress**
- **Real-time Updates**:
  - Overall progress bar with percentage
  - Stage indicators (7 stages from init to export)
  - Current operation details
  - Live metrics (time, scans processed, blocks completed)
  - Generation log (expandable)
- **Completion Actions**:
  - Download buttons for each format
  - Preview options (PDF/Markdown/JSON)
  - Email report option
  - Schedule this report
  - Generate another

**Variable System Integration:**
- **Scan Result Variables** (from Section 1):
  - PyRIT: {{total_tests}}, {{successful_attacks}}, {{vulnerability_matrix}}, etc.
  - Garak: {{probe_results}}, {{detector_findings}}, {{model_behavior}}
  - Metrics: {{overall_risk_score}}, {{critical_count}}, {{compliance_scores}}
- **Variable Mapping**: Automatic mapping of scan data to template variables
- **Block Data Flow**: Each block receives appropriate processed data

#### 2.2 Batch Report Generation (Lower Priority)

**Batch Strategies:**
- Same Template, Multiple Scan Sets
- Multiple Templates, Same Scans
- Custom Mapping

**Batch Configuration:**
- Parallel execution limits (1-10 reports)
- Batch timeout settings
- Common output formats
- Report name patterns with variables

**Batch Execution:**
- Configuration validation
- Batch preview (first 5 reports)
- Progress monitoring for all reports
- Bulk download when complete

### 3. Report Scheduling Section

#### 3.1 Schedule Configuration
- **Schedule Creator**: User-friendly interface for creating schedules
  - Template selection
  - Frequency options (Daily, Weekly, Monthly, Custom)
  - Time selection with timezone support
  - Advanced cron expression support
- **Schedule Calendar View**: Visual calendar showing scheduled reports
- **Schedule Testing**: Test run schedules before activation

#### 3.2 Schedule Management
- **Active Schedules Dashboard**: List of all active schedules
- **Schedule History**: View past executions and their status
- **Schedule Monitoring**: Real-time status of running schedules
- **Failure Alerts**: Configure notifications for failed schedules
- **Schedule Analytics**: Success rate, execution time trends

### 4. Report Export & Distribution

#### 4.1 Export Options
- **Multi-format Export**: 
  - PDF with professional styling
  - JSON for programmatic processing
  - Markdown for documentation
  - HTML for web viewing
- **Bulk Export**: Export multiple reports at once
- **Export Templates**: Save export preferences

#### 4.2 Distribution Settings
- **Email Distribution**: Configure email recipients for reports
- **Webhook Integration**: Send reports to external systems
- **Cloud Storage**: Auto-upload to S3, Azure Blob, GCS
- **API Integration**: Push reports to external APIs

### 5. Report Analytics & History

#### 5.1 Report Dashboard
- **Generation Metrics**: Reports generated over time
- **Template Usage**: Most/least used templates
- **Export Statistics**: Popular export formats
- **Performance Metrics**: Average generation time

#### 5.2 Report Archive
- **Historical Reports**: Browse all generated reports
- **Advanced Search**: Search by date, template, content
- **Report Comparison**: Compare reports side-by-side
- **Retention Management**: Configure report retention policies

### 6. AI Configuration Section

#### 6.1 AI Provider Settings
- **Provider Management**: Configure multiple AI providers
- **Model Selection**: Choose specific models per provider
- **API Key Management**: Secure storage of API credentials
- **Fallback Configuration**: Set backup providers

#### 6.2 Prompt Management
- **Prompt Library**: Save and reuse effective prompts
- **Prompt Testing**: Test prompts with sample data
- **Prompt Variables**: Use dynamic variables in prompts
- **Prompt Performance**: Track prompt effectiveness

### 7. Security & Access Control

#### 7.1 Permission Management
- **Template Permissions**: Control who can create/edit templates
- **Report Access**: Set viewing permissions for reports
- **Schedule Ownership**: Manage schedule ownership
- **Audit Trail**: Track all actions and changes

#### 7.2 Data Security
- **Sensitive Data Handling**: Configure data masking rules
- **Encryption Settings**: Report encryption options
- **Compliance Tools**: GDPR, HIPAA compliance features

## User Interface Design

### Layout Structure
```
┌─────────────────────────────────────────────────────────────┐
│                    Report Setup                              │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │  Templates  │ │   Generate  │ │  Schedule   │           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Main Content Area - Changes based on selected tab]        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                                                       │  │
│  │                 Dynamic Content                       │  │
│  │                                                       │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  [Action Buttons]  [Status Messages]                        │
└─────────────────────────────────────────────────────────────┘
```

### Key UI Components
- **Tabbed Navigation**: Easy switching between major sections
- **Sidebar Filters**: Context-aware filtering options
- **Action Toolbar**: Quick access to common actions
- **Status Bar**: Real-time status updates and notifications
- **Help System**: Contextual help and tooltips

## Technical Implementation Notes

### State Management
- Use Streamlit session state for form data persistence
- Implement proper state cleanup on navigation
- Cache template configurations for performance

### API Integration
- All operations through existing COB API endpoints
- Real-time updates using polling or SSE
- Proper error handling and user feedback

### Security Considerations
- JWT token validation for all operations
- Input sanitization for template configurations
- Secure handling of AI API credentials
- Audit logging for all actions

### Performance Optimization
- Lazy loading for template gallery
- Pagination for report history
- Background processing for report generation
- Caching strategies for frequently used data

## Future Enhancements

1. **Template Marketplace**: Share templates with the community
2. **AI-Powered Template Suggestions**: Recommend templates based on usage
3. **Natural Language Report Requests**: Generate reports using chat interface
4. **Report Insights**: AI-generated insights from report trends
5. **Mobile App**: Access reports and schedules on mobile devices
6. **Integration Hub**: Connect with more external services
7. **Custom Visualizations**: Add custom chart types and visualizations
8. **Collaborative Editing**: Multi-user template editing
9. **Report Automation Workflows**: Chain reports and actions
10. **Advanced Analytics**: Predictive analytics on security trends