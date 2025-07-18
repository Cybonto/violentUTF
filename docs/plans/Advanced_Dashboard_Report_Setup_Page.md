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

### 2. Report Generation Section - Improved Data-First Approach

#### Initial Template Library (Toxicity/Safety Focus)

**Core Templates:**
1. **Basic Safety Assessment Report** - Comprehensive safety evaluation focusing on harmful content
2. **Toxicity Analysis Deep Dive** - Detailed analysis of model responses to toxic prompts
3. **Jailbreak Resilience Report** - Assessment of resistance to jailbreak attempts
4. **Bias and Fairness Evaluation** - Comprehensive bias testing across dimensions
5. **Safety Compliance Report** - Compliance-focused report for safety standards

#### 2.1 Manual Report Generation - Reordered Workflow

**New Step-Based Workflow:**
1. **Data Selection** → 2. **Template Recommendation** → 3. **Report Configuration** → 4. **Generation & Export**

**Step 1: Data Selection (NEW FIRST STEP)**
- **Data Source Tabs**: Recent Scans | Search by Model | Search by Date | Search by Type
- **Enhanced Scan Cards**:
  - Scanner type indicator (PyRIT/Garak)
  - Score category badges (☠️ toxicity, 🛡️ safety, ⚖️ bias, 🔓 jailbreak)
  - Key metrics display (tests run, avg toxicity score)
  - Dataset/Orchestrator information
  - Expandable score breakdown table
- **Quick Filters**: "All", "Safety/Toxicity", "Jailbreak", "Bias", "Compliance"
- **Scan Selection**: Checkbox with visual feedback for selected scans

**Step 2: Template Recommendation (Based on Selected Data)**
- **Data Analysis Summary**:
  - Number of scans selected
  - Score categories present
  - Models tested
  - Total tests run
- **Recommended Templates**:
  - Templates matched to scan data categories (>50% overlap)
  - Visual "RECOMMENDED" indicator
  - Automatic suggestion for safety assessment if toxicity data present
- **Template Cards**:
  - Template name and description
  - "Best for" categories
  - Template structure preview
  - Selection buttons (primary for recommended)

**Step 3: Report Configuration**
- **Multi-Format Default**:
  - Output formats default to ["PDF", "JSON"]
  - Format-specific options (PDF style, JSON structure)
- **Enhanced Configuration**:
  - Basic settings with smart defaults
  - Block configuration with available variables
  - AI settings with provider options
  - Advanced data processing options

**Step 4: Generation & Export**
- **Progress Tracking**:
  - 7-stage progress indicator
  - Real-time metrics and logs
- **Multi-Format Output**:
  - Simultaneous generation of selected formats
  - Individual download buttons per format
  - Preview options for each format

**Enhanced Variable System (ViolentUTF API):**
- **Orchestrator Variables**: execution_id, orchestrator_name/type, execution_summary
- **Scoring Variables**: score_value/type/category, score_rationale, scorer_class, avg_toxicity_score, safety_pass_rate
- **Dataset Variables**: dataset_name/category/size, dataset_description
- **Model Variables**: target_model, model_endpoint/version, deployment_name
- **Garak Variables**: vulnerabilities_found, probe_names, generator_used, success_rate
- **Compliance Variables**: owasp_coverage, nist_alignment, framework_gaps

#### 2.2 Extensible Block System

**Backend Architecture:**
```
BaseReportBlock (Abstract)
├── BlockDefinition (metadata, parameters, variables)
├── Validation (config validation)
├── Processing (data transformation)
└── Rendering (PDF/JSON/Markdown output)
```

**Block Registry System:**
- Dynamic block registration
- Category-based organization
- Frontend configuration generator
- Parameter type support (text, select, multiselect, number, boolean, code)

**Example New Block - Toxicity Heatmap:**
- Categories: hate, harassment, violence, sexual, self-harm
- Aggregation: mean, max, p95, count
- Color scales: red_yellow_green, blue_white_red, viridis
- Output: toxicity_matrix, category_summary

#### 2.3 Report Scheduling - Technology Stack

**Leveraging Existing Infrastructure:**
- **Scheduler**: APScheduler with SQLAlchemy persistence (existing DB)
- **Execution**: FastAPI Background Tasks with asyncio
- **Security**: JWT via APISIX, role-based authorization
- **Reliability**: Exponential backoff retry, checkpoint recovery

**Scheduling Features:**
- **Frequency Options**: Daily, Weekly, Monthly, Custom Cron
- **Timezone Support**: Full timezone selection
- **Data Selection Strategies**:
  - Latest scans matching criteria
  - All scans since last report
  - Fixed time window
  - Saved data selection
- **Reliability Options**:
  - Retry on failure (1-5 attempts)
  - Skip on persistent error
  - Checkpoint-based recovery
- **Notifications**:
  - Email, Webhook, In-App
  - Success/Failure notifications
  - Configurable recipients

**Security Implementation:**
- Encrypted auth tokens in job context
- Permission validation for scheduling
- Audit logging for all operations
- Secure execution isolation

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