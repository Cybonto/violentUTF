# AI Analysis Integration Guide

## Overview

The AI Analysis block in ViolentUTF's Report Setup feature provides intelligent security insights by analyzing execution data from PyRIT and Garak scans. This guide explains how the AI Analysis integration works and how to configure it effectively.

## Architecture

### Data Flow

```
Orchestrator Execution Results
        ↓
    API Endpoint
        ↓
AI Analysis Block
        ↓
   Generator Service
        ↓
  AI Provider (OpenAI/Anthropic/etc)
        ↓
    Report Output
```

### Key Components

1. **Execution Data Fetching**: Retrieves real-time results from orchestrator executions
2. **Score Processing**: Analyzes vulnerability scores and patterns
3. **AI Generation**: Uses configured generators for intelligent analysis
4. **Risk Assessment**: Calculates overall risk scores and severity distributions

## Configuration

### AI Model Selection

The AI model dropdown dynamically loads available models from configured generators:

```python
# Models are fetched from the generator service
GET /api/v1/generators

# Returns list of configured AI models:
{
  "generators": [
    {
      "name": "gpt-4-security-tuned",
      "type": "openai",
      "description": "Fine-tuned GPT-4 for security analysis"
    },
    {
      "name": "claude-3-security",
      "type": "anthropic",
      "description": "Claude 3 configured for security assessments"
    }
  ]
}
```

### Configuration Options

#### Basic Settings
- **AI Provider**: Automatically determined from selected model
- **AI Model**: Dropdown populated from live generator data
- **Analysis Prompt**: Customizable prompt for AI analysis
- **Max Tokens**: Control output length (default: 2000)
- **Temperature**: Adjust creativity (0.0-1.0, default: 0.7)

#### Advanced Settings
- **Analysis Depth**:
  - `quick`: High-level summary only
  - `standard`: Balanced analysis
  - `detailed`: Comprehensive deep dive
- **Include Recommendations**: Toggle actionable suggestions
- **Severity Threshold**: Filter which findings to analyze

## Real-Time Data Integration

### Execution Data Fetching

The AI Analysis block fetches live data from orchestrator executions:

```python
# Fetch execution details
GET /api/v1/orchestrators/results/{execution_id}

# Returns detailed execution data including:
- Total prompts tested
- Vulnerability scores
- Attack success rates
- Score distributions
- Category breakdowns
```

### Score Processing

The system processes execution scores to identify:
- **Critical Findings**: Scores ≥ 0.9
- **High Risk Areas**: Scores ≥ 0.7
- **Pattern Detection**: Common vulnerability types
- **Trend Analysis**: Changes over time

### Risk Calculation

Overall risk score is calculated using:
```
risk_score = (critical_weight * critical_count +
              high_weight * high_count +
              medium_weight * medium_count) / total_tests
```

## Usage Best Practices

### 1. Model Selection
- Choose specialized security models when available
- Consider model context window for large datasets
- Use consistent models for comparative analysis

### 2. Prompt Engineering
Effective prompts include:
- Clear analysis objectives
- Specific security frameworks to consider
- Output format requirements
- Focus areas (e.g., OWASP Top 10)

Example prompt:
```
Analyze the security test results focusing on:
1. Critical vulnerabilities and their potential impact
2. Attack patterns and success rates
3. Compliance with OWASP guidelines
4. Prioritized remediation recommendations

Format the analysis with clear sections and actionable insights.
```

### 3. Analysis Depth
- **Quick**: For regular monitoring and dashboards
- **Standard**: For weekly security reviews
- **Detailed**: For compliance audits and incident response

### 4. Performance Optimization
- Cache analysis results for identical configurations
- Use appropriate token limits to balance detail vs cost
- Consider batch processing for multiple executions

## Integration with Other Blocks

The AI Analysis block works seamlessly with:

### Executive Summary Block
- Provides high-level insights
- Feeds risk scores and key findings
- Generates management-friendly summaries

### Security Metrics Block
- Complements quantitative metrics with qualitative analysis
- Provides context for score distributions
- Explains anomalies and outliers

### Recommendations Block
- AI-generated remediation suggestions
- Prioritized action items
- Implementation guidance

## Troubleshooting

### Common Issues

1. **Empty AI Model Dropdown**
   - Verify generator service is running
   - Check API connectivity to `/api/v1/generators`
   - Ensure generators are properly configured

2. **No Execution Data Available**
   - Confirm execution_id is valid
   - Check orchestrator service connectivity
   - Verify user has permissions to access execution data

3. **AI Analysis Timeout**
   - Reduce max_tokens setting
   - Check AI provider API limits
   - Consider using a faster model

4. **Inconsistent Analysis Results**
   - Use lower temperature (0.1-0.3) for consistency
   - Standardize prompts across reports
   - Ensure consistent data preprocessing

### Debug Mode

Enable debug logging to troubleshoot issues:
```python
# In your environment
VIOLENTUTF_DEBUG=true
VIOLENTUTF_LOG_LEVEL=DEBUG
```

## Security Considerations

1. **API Key Management**
   - AI provider keys are stored securely
   - Never expose keys in reports or logs
   - Rotate keys regularly

2. **Data Privacy**
   - Sensitive data can be redacted before AI analysis
   - Consider on-premise models for highly sensitive data
   - Review AI provider data retention policies

3. **Prompt Injection Prevention**
   - Sanitize execution data before analysis
   - Use system prompts to establish boundaries
   - Validate AI output before inclusion in reports

## Advanced Configuration

### Custom Analysis Functions

For specialized analysis needs:

```python
# Custom preprocessing function
def preprocess_execution_data(execution_data):
    # Filter and transform data
    return processed_data

# Custom postprocessing function
def postprocess_ai_output(ai_response):
    # Validate and format output
    return formatted_response
```

### Multi-Model Analysis

Combine insights from multiple models:
```python
models = ["gpt-4-security", "claude-security", "llama-security"]
analyses = []

for model in models:
    analysis = generate_analysis(data, model)
    analyses.append(analysis)

# Aggregate insights
final_analysis = aggregate_analyses(analyses)
```

## Future Enhancements

Planned improvements include:
- Automatic prompt optimization based on feedback
- Cross-execution trend analysis
- Integration with threat intelligence feeds
- Custom fine-tuned models for ViolentUTF
- Real-time streaming analysis for live tests

## Related Documentation

- [Report Setup Overview](./Guide_Report_Setup_Overview.md)
- [Report Configuration Guide](./Guide_Report_Configuration.md)
- [API Documentation](../api/API_Report_Setup_Endpoints.md)
- [Troubleshooting Guide](../troubleshooting/Troubleshooting_Report_Generation.md)
