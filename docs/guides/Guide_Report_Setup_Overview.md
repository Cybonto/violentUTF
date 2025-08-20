# Report Setup Overview Guide

## Introduction

The Report Setup feature in ViolentUTF provides a comprehensive interface for creating customized security assessment reports from PyRIT and Garak scan data. This guide covers the key features and workflow of the Report Setup system.

## Recent Updates (December 2024)

### Major Changes
1. **COB (Close of Business) Reports Retirement**: The legacy COB Reports tab has been removed from the Dashboard. All report functionality is now consolidated under the Report Setup feature.
2. **API Consolidation**: All report-related endpoints have been consolidated under `/api/v1/reports/` for consistency.
3. **Dynamic AI Model Selection**: AI models are now dynamically loaded from configured generators instead of using hardcoded options.
4. **Real-time Data Integration**: All features now use live data from API endpoints - no mock data is used.

## System Architecture

### API Structure
The Report Setup system uses a unified API structure:
- **Base URL**: `/api/v1/reports/`
- **Key Endpoints**:
  - `/api/v1/reports/templates` - Template management
  - `/api/v1/reports/blocks/registry` - Block type registry
  - `/api/v1/reports/data/browse` - Scan data browsing
  - `/api/v1/reports/config` - Configuration management

### Authentication
All endpoints require JWT authentication through the APISIX gateway. The system automatically handles token refresh and validation.

## Tab-Based Interface

The Report Setup page is organized into five main tabs:

### 1. Data Selection Tab
- Browse and select scan data from PyRIT and Garak executions
- Filter by scanner type, date range, severity level, and model
- Preview scan results before selection
- Multi-select capability for combining data from multiple scans

### 2. Template Selection Tab
- Choose from predefined report templates or custom templates
- Templates are categorized by type (executive, technical, compliance, security)
- Smart template recommendations based on selected data
- Template compatibility checking ensures selected templates work with your data

### 3. Configuration Tab
The Configuration tab is divided into five sections:

#### Basic Configuration
- Set report title, description, and reporting period
- Configure timezone settings
- Manage report metadata

#### Block Configuration
- Enable/disable individual report blocks
- Customize block-specific settings
- Reorder blocks to match your preferences
- Configure data presentation options

#### AI Analysis Settings
- **Dynamic Model Selection**: AI models are loaded from configured generators
- Configure analysis prompts and parameters
- Set analysis depth (quick, standard, detailed)
- Customize scoring thresholds

#### Output Settings
- Select output formats (PDF, JSON, Markdown)
- Configure PDF styling options
- Set data export preferences
- Manage file naming conventions

#### Notification & Schedule
- Configure email notifications
- Set up automated report generation schedules
- Manage distribution lists
- Configure webhook integrations

### 4. Preview Tab (Coming Soon)
- Live preview of report with actual data
- Format-specific previews
- Variable resolution display
- Block-by-block preview options

### 5. Generate Tab (Coming Soon)
- Execute report generation
- Real-time progress tracking
- Multi-format output generation
- Download and distribution options

## Key Features

### Dynamic Data Loading
All dropdowns and selections use live data:
- AI models are loaded from the generator service
- Templates are fetched from the database
- Scan data is queried in real-time
- No hardcoded or mock data is used

### Block System
Reports are composed of configurable blocks:
- **Executive Summary**: High-level overview
- **Methodology**: Testing approach details
- **Findings Summary**: Aggregated security findings
- **AI Analysis**: AI-powered insights from execution data
- **Recommendations**: Actionable security recommendations
- **Detailed Results**: Comprehensive test results
- **Evidence**: Supporting evidence and artifacts
- **Appendix**: Additional technical details

### AI Analysis Integration
The AI Analysis block provides intelligent insights by:
- Fetching real execution data from orchestrator results
- Processing vulnerability scores and patterns
- Generating context-aware recommendations
- Using configured AI models for analysis

## Configuration Schema

Each block supports JSON Schema-based configuration:
```json
{
  "type": "object",
  "properties": {
    "enabled": {
      "type": "boolean",
      "default": true
    },
    "settings": {
      "type": "object",
      "properties": {
        // Block-specific settings
      }
    }
  }
}
```

## Best Practices

1. **Data Selection**: Select relevant scan data that matches your reporting needs
2. **Template Choice**: Choose templates that align with your audience (executive vs technical)
3. **Configuration**: Customize blocks to highlight the most important findings
4. **AI Settings**: Select appropriate AI models based on your analysis requirements
5. **Review**: Always preview reports before final generation

## Troubleshooting

### Common Issues

1. **"Resource not found" errors**: Ensure APISIX routes are properly configured
2. **Empty dropdowns**: Check that services are running and accessible
3. **Template compatibility**: Verify selected data matches template requirements
4. **AI model not available**: Ensure generators are properly configured

### API Health Checks
Use the following endpoints to verify system health:
- `/api/v1/health` - Overall API health
- `/api/v1/generators` - Available AI models
- `/api/v1/reports/blocks/registry` - Available report blocks

## Migration Notes

### From COB Reports
If you were using the legacy COB (Close of Business) Reports:
1. The functionality has been replaced by the Report Setup feature
2. Use the scheduling feature in Configuration tab for automated reports
3. Templates provide more flexibility than the fixed COB format

### API Endpoint Changes
- Old: `/api/v1/cob/*` endpoints
- New: `/api/v1/reports/*` endpoints
- All functionality has been preserved and enhanced

## Next Steps

1. Start with the Data Selection tab to choose your scan data
2. Select an appropriate template in the Template Selection tab
3. Customize your report in the Configuration tab
4. Generate your report when ready

For detailed information on specific features, see the related guides in this documentation folder.
