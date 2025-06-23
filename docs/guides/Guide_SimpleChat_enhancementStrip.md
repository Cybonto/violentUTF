# MCP Enhancement Strip User Guide

## Overview

The MCP Enhancement Strip is a powerful new feature in Simple Chat that provides intelligent assistance for prompt engineering, security testing, and conversation analysis. It integrates seamlessly with the ViolentUTF MCP (Model Context Protocol) server to offer real-time prompt enhancements, security analysis, and test generation capabilities.

## Features

### 1. Enhancement Strip Buttons

The enhancement strip appears below your prompt input area with four main controls:

- **✨ Enhance** - Improves your prompt quality using MCP-powered suggestions
- **🔍 Analyze** - Analyzes your prompt for security vulnerabilities and bias issues
- **🧪 Test** - Generates test variations of your prompt for security testing
- **Quick Actions** - Dropdown menu for specific testing scenarios

### 2. Real-time Enhancement

Click the **✨ Enhance** button to:
- Improve prompt clarity and effectiveness
- Add necessary context and constraints
- Optimize for better AI responses
- Leverage MCP server's prompt engineering capabilities

### 3. Security & Bias Analysis

Click the **🔍 Analyze** button to:
- Detect potential jailbreak attempts
- Identify bias in prompts
- Check for security vulnerabilities
- Get recommendations for safer prompts

### 4. Test Variation Generation

Click the **🧪 Test** button to:
- Generate multiple test variations
- Create jailbreak test scenarios
- Produce bias testing prompts
- Build security audit test cases

### 5. Quick Actions

The Quick Actions dropdown provides instant access to:
- **Test for jailbreak** - Generate jailbreak test variations
- **Check for bias** - Run bias detection analysis
- **Privacy analysis** - Check for PII and sensitive data exposure
- **Security audit** - Comprehensive security assessment

## How to Use

### Basic Workflow

1. **Enter your prompt** in the text area
2. **Click an enhancement button** to process your prompt
3. **Review the results** in the tabbed interface below
4. **Use enhanced prompts** by clicking "Use Enhanced Prompt"
5. **Generate response** with the improved prompt

### Enhancement Results

Results are displayed in tabs:

#### Enhanced Prompt Tab
- Shows original and enhanced versions side-by-side
- Click "Use Enhanced Prompt" to load it into the input
- Maintains enhancement history for reference

#### Analysis Results Tab
- Displays security and bias analysis findings
- Shows risk levels and specific issues detected
- Provides actionable recommendations

#### Test Variations Tab
- Lists all generated test variations
- Each variation includes its type and purpose
- Click "Use This Variation" to test specific scenarios

## Integration with Existing Features

### Prompt Variables
- Enhanced prompts can be saved as prompt variables
- Use the "Create Prompt Variable" buttons as before
- Variables work seamlessly with MCP enhancements

### AI Gateway Integration
- MCP features work with all AI Gateway providers
- Security plugins (Prompt Guard, Decorator) remain active
- Enhanced prompts respect existing security policies

## Best Practices

### For Prompt Enhancement
1. Start with a clear, basic prompt
2. Use enhancement to add structure and context
3. Review suggested improvements before using
4. Save effective enhancements as variables

### For Security Testing
1. Always analyze prompts before production use
2. Test variations against your target model
3. Address identified vulnerabilities
4. Use quick actions for rapid assessment

### For Bias Detection
1. Check all user-facing prompts for bias
2. Pay attention to demographic categories
3. Test with diverse scenarios
4. Iterate based on analysis results

## Troubleshooting

### MCP Server Connection Issues
- Ensure ViolentUTF API is running
- Check JWT authentication is valid
- Verify APISIX gateway is accessible
- Look for error messages in the UI

### No Enhancement Available
- Some prompts may not have MCP enhancements
- Fallback enhancements will be provided
- Check available MCP prompts in server logs

### Slow Response Times
- MCP operations may take a few seconds
- Loading spinners indicate processing
- Performance depends on server load
- Consider caching frequently used enhancements

## Advanced Features

### Natural Language Commands (Coming in Phase 3)
- Use `/mcp enhance` directly in prompts
- Natural language configuration requests
- Command autocomplete suggestions

### Context-Aware Assistance (Coming in Phase 4)
- Automatic enhancement suggestions
- Real-time security monitoring
- Conversation context analysis

### Visual Builders (Coming in Phase 5)
- Drag-and-drop prompt construction
- Template library integration
- A/B testing support

## Security Considerations

- All MCP operations require authentication
- Enhanced prompts are not automatically saved
- Analysis results are session-specific
- No sensitive data is sent to external services

## Feedback and Support

For issues or suggestions regarding the MCP Enhancement Strip:
1. Check the troubleshooting section above
2. Review MCP server logs for errors
3. Report issues at https://github.com/anthropics/claude-code/issues
4. Include specific error messages and steps to reproduce

---

*Last updated: Phase 2 Implementation*