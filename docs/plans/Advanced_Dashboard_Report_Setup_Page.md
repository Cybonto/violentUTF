# Advanced Dashboard - Report Setup Page

## Overview

The Report Setup page is a comprehensive interface for managing COB (Close of Business) report templates, generating reports, and configuring automated report schedules. This page will be positioned under the Advanced Dashboard section of the ViolentUTF Streamlit application.

## Main Features

### 1. Template Management Section

#### 1.1 Template Gallery - Enhanced with Advanced Metadata

**Extended Metadata Structure:**
- **Core Identifiers**: ID, name, description, semantic version (e.g., 1.2.0)
- **Classification**: Category (Security/Compliance/Operations/Executive), tags, industry, compliance frameworks (SOC2/ISO27001/HIPAA/GDPR/PCI-DSS/NIST), report type, complexity level
- **Usage Analytics**: Total uses, last used, average generation time, success rate, user ratings, favorite count
- **Lifecycle Tracking**: Created/modified by, approval status, expiry date, deprecation status
- **Technical Requirements**: AI providers needed, minimum models, token estimates, data sources, dependencies, supported output formats
- **Content Summary**: Block counts by type, estimated page count, supported languages
- **Access Control**: Visibility levels, role-based access, sharing permissions

**Advanced Search & Filter System:**
- **Full-text Search**: Across names, descriptions, tags, block content, and AI prompts
- **Faceted Filtering**: 
  - Multi-select categories, frameworks, and report types
  - Complexity slider
  - Rating filters (minimum stars)
  - Date range selection
  - Usage frequency ranges
  - Performance metrics (generation time)
- **Smart Filters**: My templates, team favorites, recently used, trending, new arrivals, expiring soon, high-performance templates
- **Sort Options**: Relevance, name, date created/modified, usage count, rating, generation time

**Gallery Implementation:**
- **Responsive Grid Layout**: Card-based view with rich metadata display
- **Performance Metrics**: Visual indicators for success rate, generation time, usage trends
- **Quick Actions**: Use, preview, edit, clone buttons per template
- **Bulk Operations**: Select multiple templates for export, archival, or comparison

#### 1.2 Template Editor - Streamlit-Compatible Implementation

**Visual Block Editor Architecture:**
- **Hybrid Approach**: Given Streamlit limitations, uses ordered lists with move up/down buttons, expandable configuration sections, and real-time preview
- **Block Management**: Add/remove blocks, reorder with buttons or streamlit-sortables component, inline configuration
- **Session State Management**: Maintains editor state across interactions, tracks unsaved changes

**Comprehensive Block Types:**

1. **Executive Summary Block**
   - Auto-summarization from other blocks
   - Configurable summary length (100-500 words)
   - Metric inclusion selector
   - Tone adjustment (Professional/Technical/Executive/Simplified)
   - Visual highlighting for critical findings

2. **AI Analysis Block - Advanced Features**
   - **Analysis Types**: Threat assessment, vulnerability analysis, compliance check, risk evaluation, trend analysis, custom
   - **AI Provider Configuration**: 
     - Primary and fallback providers
     - Model selection with capability display
     - Cost estimation
   - **Prompt Engineering**:
     - System prompt definition
     - Template library with categories
     - Variable support ({{report_date}}, {{metrics}}, {{context}})
     - Prompt enhancement tools
     - Test with sample data
   - **Context Management**:
     - Multiple context sources (previous blocks, historical reports, real-time metrics, external intelligence)
     - Token allocation and prioritization
     - Relevance filtering with embeddings
   - **Generation Parameters**: Temperature, max tokens, top_p, frequency/presence penalties
   - **Output Configuration**:
     - Format selection (narrative, bullets, structured, Q&A)
     - Quality controls (fact verification, confidence scoring, source attribution)
     - Post-processing pipeline

3. **Data Table Block**
   - Data source selection (PyRIT, Garak, custom query, API, CSV)
   - Column configuration with custom columns
   - Advanced filtering and sorting
   - Aggregation functions
   - Conditional formatting rules
   - Export capabilities

4. **Security Metrics Block**
   - Pre-built metric templates
   - Multiple visualization types
   - Time range selection
   - Comparison modes
   - Threshold configuration
   - Real-time data integration

5. **Custom Content Block**
   - Support for Markdown, HTML, plain text
   - Variable mapping from other sources
   - Template syntax with dynamic content

**Block Configuration UI:**
- **Field Types**: Text inputs, selectboxes, multi-selects, sliders, checkboxes, code editors (via streamlit-ace)
- **Conditional Visibility**: Fields shown/hidden based on other selections
- **Validation**: Real-time validation with helpful error messages
- **Preview**: Live preview of block output

#### 1.3 Template Versioning System

**Semantic Versioning (SemVer):**
- **Version Format**: MAJOR.MINOR.PATCH (e.g., 2.1.0)
- **Pre-release Support**: Beta, RC tags (e.g., v2.1.0-beta.1)
- **Version Types**: Major (breaking changes), Minor (new features), Patch (bug fixes)

**Version Control Features:**
- **Complete History**: Every version stored with full template snapshot
- **Changelog Tracking**: 
  - Categorized changes (Added/Changed/Deprecated/Removed/Fixed/Security)
  - Impact levels and affected blocks
  - Migration requirements
- **Version Comparison**:
  - Side-by-side diff view
  - Block additions/removals/modifications
  - Visual structure comparison
  - Migration assistant
- **Branching & Merging**:
  - Create branches for parallel development
  - Three-way merge with conflict resolution
  - Branch visualization

**Version Lifecycle Management:**
- **States**: Draft → Pending Review → Approved → Published → Deprecated → Archived
- **Approval Workflow**: Required approvers, approval notes, rejection handling
- **Auto-transitions**: Configurable rules (e.g., auto-archive after 90 days deprecated)
- **Access Control**: Role-based permissions for state transitions

**Migration System:**
- **Migration Analysis**: Identify breaking changes, suggest replacements
- **Migration Scripts**: Auto-generated or custom migration code
- **Compatibility Checking**: Validate template compatibility with API versions
- **Batch Migration**: Migrate multiple reports/schedules to new template version

**Version UI Components:**
- **Timeline Visualization**: Interactive timeline of version history
- **Version Comparison Tool**: Detailed diff with multiple view modes
- **Migration Assistant**: Step-by-step migration guidance
- **Lifecycle Controls**: State transition interface with validation

### 2. Report Generation Section

#### 2.1 Manual Report Generation
- **Template Selection**: Dropdown to select from active templates
- **Report Parameters**: Dynamic form based on template requirements
- **Generation Options**:
  - Report name customization
  - Date range selection
  - AI provider selection (OpenAI, Anthropic, GSAi, REST API)
  - Analysis depth settings
- **Real-time Progress**: Progress bar showing report generation status
- **Preview Before Export**: Quick preview of generated report

#### 2.2 Batch Report Generation
- **Multiple Template Selection**: Generate reports from multiple templates
- **Bulk Parameters**: Apply common parameters to all reports
- **Queue Management**: View and manage report generation queue
- **Parallel Processing**: Generate multiple reports simultaneously

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