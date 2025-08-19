# Report Configuration Guide

## Overview

The Configuration tab in Report Setup provides comprehensive control over report generation settings. This guide details each configuration section and how to use them effectively.

## Configuration Sections

### 1. Basic Configuration

This section manages fundamental report settings:

- **Report Title**: A descriptive title for your report
- **Report Description**: Additional context about the report's purpose
- **Report Period**: 
  - Start Date: Beginning of the reporting period
  - End Date: End of the reporting period
- **Timezone**: Select the timezone for timestamps in the report

### 2. Block Configuration

Control which report sections appear and their settings:

#### Available Blocks:
- **Executive Summary**: High-level overview for leadership
- **Methodology**: Details about testing approaches used
- **Findings Summary**: Aggregated security findings
- **AI Analysis**: AI-powered insights from scan data
- **Recommendations**: Actionable security improvements
- **Detailed Results**: Comprehensive test results
- **Evidence**: Supporting artifacts and proof
- **Appendix**: Additional technical information

#### Block Controls:
- **Enable/Disable**: Toggle blocks on/off using checkboxes
- **Block Settings**: Each block has specific configuration options
- **Reorder**: Drag and drop to change block order in the final report

### 3. AI Analysis Settings

Configure how AI analyzes your security data:

#### Key Settings:
- **AI Provider**: Select from available providers (OpenAI, Anthropic, etc.)
- **AI Model**: Dynamically loaded from configured generators
  - Models are fetched in real-time from the generator service
  - No hardcoded options - reflects your actual AI configuration
- **Analysis Prompt**: Customize the prompt used for AI analysis
- **Max Tokens**: Control the length of AI-generated content
- **Temperature**: Adjust creativity vs consistency (0.0-1.0)
- **Analysis Depth**:
  - Quick: Fast, high-level analysis
  - Standard: Balanced depth and speed
  - Detailed: Comprehensive analysis with more context

### 4. Output Settings

Control how reports are generated and formatted:

#### Format Options:
- **PDF**: Professional document format
  - Customizable styling
  - Embedded charts and graphs
  - Print-ready layout
- **JSON**: Machine-readable format
  - Complete data export
  - API integration ready
  - Structured data format
- **Markdown**: Version-control friendly
  - Easy to edit and review
  - GitHub/GitLab compatible
  - Convertible to other formats

#### Additional Settings:
- **Include Raw Data**: Attach source data to reports
- **Anonymize Data**: Remove sensitive information
- **Compress Output**: Reduce file sizes for large reports

### 5. Notification & Schedule

Automate report generation and distribution:

#### Notification Settings:
- **Enable Notifications**: Turn on/off email alerts
- **Notification Email**: Where to send alerts
- **Notification Events**:
  - Report Started: When generation begins
  - Report Completed: When report is ready
  - Report Failed: If errors occur

#### Schedule Configuration:
- **Enable Schedule**: Activate automated generation
- **Schedule Type**:
  - Daily: Run every day at specified time
  - Weekly: Run on selected days
  - Monthly: Run on specific date each month
  - Custom: Cron expression for complex schedules
- **Scheduled Time**: When to run (respects timezone setting)

## Dynamic Features

### Live Data Integration

All configuration options use real-time data:
1. **AI Models** are fetched from the generator service
2. **Block Types** are loaded from the block registry
3. **Templates** reflect actual database content
4. **No mock data** is used anywhere

### JSON Schema Validation

Each block's configuration is validated against its schema:
```python
# Example schema for AI Analysis block
{
  "type": "object",
  "properties": {
    "includeRecommendations": {
      "type": "boolean",
      "default": true
    },
    "severityThreshold": {
      "type": "string",
      "enum": ["critical", "high", "medium", "low"]
    }
  }
}
```

### Smart Defaults

The system provides intelligent defaults based on:
- Selected template type
- Data characteristics
- Previous configurations
- Best practices

## Best Practices

### For AI Analysis:
1. **Model Selection**: Choose models based on your security focus
2. **Prompt Engineering**: Customize prompts for your specific needs
3. **Token Limits**: Balance detail with cost considerations
4. **Temperature**: Use lower values (0.1-0.3) for consistent reports

### For Scheduling:
1. **Timing**: Schedule during low-activity periods
2. **Frequency**: Match your security review cycles
3. **Notifications**: Enable for critical reports
4. **Time Zones**: Ensure correct timezone selection

### For Output:
1. **Formats**: Generate multiple formats for different audiences
2. **Data Inclusion**: Include raw data for technical teams
3. **Anonymization**: Enable for external sharing
4. **Compression**: Use for reports with large datasets

## Troubleshooting

### Common Issues:

1. **AI Model Dropdown Empty**
   - Check generator service is running
   - Verify API connectivity
   - Ensure generators are configured

2. **Block Settings Not Saving**
   - Validate against JSON schema
   - Check for required fields
   - Verify data types match schema

3. **Schedule Not Running**
   - Confirm schedule is enabled
   - Check timezone settings
   - Verify cron expression syntax

4. **Notifications Not Received**
   - Check email configuration
   - Verify notification settings
   - Check spam folders

## Advanced Configuration

### Custom Block Settings

For advanced users, blocks support custom JSON configuration:
```json
{
  "ai_analysis": {
    "custom_prompts": {
      "vulnerability_analysis": "Focus on OWASP Top 10...",
      "remediation_suggestions": "Provide specific code fixes..."
    },
    "model_parameters": {
      "top_p": 0.9,
      "frequency_penalty": 0.5
    }
  }
}
```

### Integration with External Systems

Configure webhooks for integration:
```json
{
  "webhooks": {
    "on_complete": "https://your-system.com/report-ready",
    "on_failure": "https://your-system.com/report-failed"
  }
}
```

## Next Steps

After configuration:
1. Use the Preview tab to see a sample report
2. Adjust settings based on preview results
3. Save configuration as a preset for reuse
4. Generate your final report

For more details on specific features, refer to the related guides in this documentation.