# IronUTF Defense Module Guide

## Overview

IronUTF is ViolentUTF's defense module that provides custom protection for AI endpoints. It allows you to implement security measures and modify AI interactions in real-time, creating a robust defense layer for your AI infrastructure.

## What is IronUTF?

IronUTF leverages two powerful APISIX plugins to provide:

1. **AI Prompt Guard** - Security filtering to block harmful or inappropriate prompts
2. **AI Prompt Decorator** - Dynamic prompt modification and enhancement

These plugins work at the gateway level, providing consistent protection and customization across all your AI providers (OpenAI, Anthropic, Ollama, Open WebUI).

## Key Features

### 🛡️ AI Prompt Guard
- **Content Filtering**: Block prompts containing specific patterns or keywords
- **Whitelist Control**: Allow only prompts matching approved patterns
- **Custom Responses**: Configure personalized error messages for blocked requests
- **Case-Insensitive Matching**: Flexible pattern matching options

### 🎨 AI Prompt Decorator
- **System Context**: Add consistent system prompts across conversations
- **Pre/Post Processing**: Insert messages before or after user prompts
- **Role-Based Messages**: Support for system, user, and assistant roles
- **Provider Compatibility**: Automatically adapts to different AI provider requirements

## Getting Started

### Prerequisites

1. **Authentication**: Ensure you're logged in through Keycloak SSO or have environment credentials configured
2. **APISIX Setup**: Complete ViolentUTF setup with configured AI routes
3. **Admin Access**: IronUTF requires administrative privileges for route modification

### Accessing IronUTF

1. Navigate to the IronUTF page in your ViolentUTF interface
2. The system will automatically generate admin API tokens
3. Available AI routes will be loaded from your APISIX configuration

## Using AI Prompt Guard

### Basic Configuration

1. **Select Route**: Choose the AI endpoint you want to protect
2. **Configure Patterns**: Set up deny and allow patterns
3. **Test Configuration**: Verify your settings work as expected
4. **Apply Changes**: Deploy the protection to your endpoint

### Deny Patterns

Block prompts containing harmful content:

```
# Examples of deny patterns
hack.*system
jailbreak
ignore.*instructions
DAN.*mode
```

These patterns use regular expressions to match dangerous prompt injections.

### Allow Patterns

Restrict to only approved content (optional):

```
# Examples of allow patterns
.*business.*query
help.*with.*coding
explain.*concept
```

If allow patterns are specified, **only** prompts matching these patterns will be processed.

### Custom Messages

Configure user-friendly error messages:
- Default: "Your request has been blocked due to policy violations."
- Custom: "Please rephrase your request to comply with our usage guidelines."

### Case Sensitivity

- **Case Insensitive** (default): Matches patterns regardless of capitalization
- **Case Sensitive**: Exact case matching for more precise control

## Using AI Prompt Decorator

### Basic Configuration

1. **Prepend Messages**: Add context before user prompts
2. **Append Messages**: Add instructions after user prompts
3. **Role Selection**: Choose appropriate message roles
4. **Provider Compatibility**: System handles provider-specific limitations

### Prepend Examples

Add consistent system context:

**Role**: system
**Content**: "You are a helpful AI assistant specialized in cybersecurity. Always provide accurate, ethical guidance."

**Role**: user
**Content**: "Please consider security implications in your response."

### Append Examples

Add consistent instructions:

**Role**: system
**Content**: "Always include relevant security warnings if applicable."

**Role**: assistant
**Content**: "Is there anything specific about security you'd like me to clarify?"

### Provider-Specific Considerations

#### Anthropic Models
- **Limitation**: Only supports 'user' and 'assistant' roles
- **Recommendation**: Use 'user' role for system-like instructions
- **Example**: "As a user, I want you to act as a security expert..."

#### OpenAI Models
- **Full Support**: system, user, and assistant roles
- **Best Practice**: Use 'system' for context, 'user' for instructions

#### Local Models (Ollama/WebUI)
- **Variable Support**: Depends on model implementation
- **Testing**: Always test configurations with your specific models

## Advanced Configurations

### Combining Both Plugins

You can use both plugins simultaneously for comprehensive control:

1. **Guard**: Filter out harmful content
2. **Decorator**: Add security-focused context

Example workflow:
1. Prompt Guard blocks dangerous inputs
2. Prompt Decorator adds security context to safe prompts
3. AI model processes enhanced, safe prompts

### Testing Configurations

Always test your configurations before deployment:

1. **Click "Test Configuration"**
2. **Review Test Results**: Verify filtering and decoration work correctly
3. **Check Response**: Ensure the AI model receives and processes modified prompts
4. **Iterate**: Adjust patterns and messages as needed

### Provider Detection

IronUTF automatically detects your AI provider and adapts:
- **OpenAI**: Full role support
- **Anthropic**: Limited role support with warnings
- **Ollama**: Local model detection
- **WebUI**: Open WebUI integration

## Best Practices

### Security Patterns

#### Prompt Injection Prevention
```
# Deny patterns for common prompt injections
ignore.*previous.*instructions
act.*as.*[^a-zA-Z]*DAN
system.*prompt.*is
forget.*everything
new.*instructions
```

#### Content Safety
```
# Deny patterns for inappropriate content
.*explicit.*content
.*harmful.*instructions
.*illegal.*activities
```

### Prompt Enhancement

#### Consistent Context
```
# Prepend system message
Role: system
Content: "You are a professional AI assistant. Always maintain ethical standards and provide accurate information."
```

#### Security Awareness
```
# Append reminder
Role: system
Content: "Remember to consider security implications and never provide information that could be misused."
```

### Testing Strategy

1. **Positive Tests**: Verify legitimate prompts pass through
2. **Negative Tests**: Confirm malicious prompts are blocked
3. **Edge Cases**: Test borderline content
4. **Provider Compatibility**: Test across different AI models

## Troubleshooting

### Common Issues

#### Authentication Errors
- **Problem**: "Failed to generate API token"
- **Solution**: Verify JWT_SECRET_KEY environment variable is set
- **Check**: Keycloak SSO or environment credentials are configured

#### Route Configuration Errors
- **Problem**: "Failed to update route configuration"
- **Solution**: Check APISIX admin API connectivity
- **Verify**: Admin privileges and network access

#### Plugin Conflicts
- **Problem**: Unexpected behavior with multiple plugins
- **Solution**: Test plugins individually, then in combination
- **Order**: Plugin execution order may affect results

#### Provider Compatibility
- **Problem**: "System role not supported"
- **Solution**: Use appropriate roles for your AI provider
- **Reference**: Check provider-specific warnings in the interface

### Debugging Tips

1. **Check Logs**: Review browser console and application logs
2. **Test Incrementally**: Start with simple configurations
3. **Use Debug Information**: Expand error details when configuration fails
4. **Provider Documentation**: Consult AI provider API documentation

## API Integration

### Direct API Access

IronUTF configurations can also be managed programmatically through the ViolentUTF API:

```bash
# Get route configuration
curl -H "Authorization: Bearer <token>" \
     -H "X-API-Gateway: APISIX" \
     http://localhost:9080/api/v1/apisix-admin/routes/<route_id>

# Update plugins
curl -X PUT \
     -H "Authorization: Bearer <token>" \
     -H "X-API-Gateway: APISIX" \
     -H "Content-Type: application/json" \
     -d '{"plugins": {...}}' \
     http://localhost:9080/api/v1/apisix-admin/routes/<route_id>/plugins
```

### Configuration Schema

#### AI Prompt Guard
```json
{
  "ai-prompt-guard": {
    "deny_patterns": ["pattern1", "pattern2"],
    "allow_patterns": ["pattern1", "pattern2"],
    "deny_message": "Custom error message",
    "case_insensitive": true
  }
}
```

#### AI Prompt Decorator
```json
{
  "ai-prompt-decorator": {
    "prepend": [
      {
        "role": "system",
        "content": "System context message"
      }
    ],
    "append": [
      {
        "role": "user",
        "content": "Additional instructions"
      }
    ]
  }
}
```

## Security Considerations

### Defense in Depth

IronUTF provides one layer of defense. Consider implementing:

1. **Input Validation**: Additional validation at application level
2. **Rate Limiting**: Prevent abuse through request limiting
3. **Monitoring**: Log and analyze prompt patterns
4. **Model Alignment**: Use well-aligned AI models

### Pattern Maintenance

Regularly update your patterns based on:

1. **Threat Intelligence**: New attack patterns
2. **False Positives**: Legitimate requests being blocked
3. **Business Requirements**: Changing use cases
4. **Model Updates**: AI provider capability changes

### Audit Trail

IronUTF changes are logged for audit purposes:
- Configuration changes
- Blocked requests
- Pattern matches
- Administrative actions

## Integration Examples

### E-commerce Platform
```json
{
  "ai-prompt-guard": {
    "allow_patterns": [
      ".*product.*recommendation",
      ".*shopping.*help",
      ".*customer.*support"
    ],
    "deny_patterns": [
      ".*competitor.*information",
      ".*pricing.*strategy",
      ".*internal.*data"
    ],
    "deny_message": "I can only help with product and shopping questions."
  },
  "ai-prompt-decorator": {
    "prepend": [{
      "role": "system",
      "content": "You are a helpful e-commerce assistant. Focus on helping customers find products and providing shopping guidance."
    }]
  }
}
```

### Educational Platform
```json
{
  "ai-prompt-guard": {
    "allow_patterns": [
      ".*explain.*concept",
      ".*homework.*help",
      ".*study.*guide"
    ],
    "deny_patterns": [
      ".*complete.*assignment",
      ".*write.*essay.*for.*me",
      ".*exam.*answers"
    ],
    "deny_message": "I can help explain concepts but cannot complete assignments for you."
  },
  "ai-prompt-decorator": {
    "prepend": [{
      "role": "system",
      "content": "You are an educational assistant. Help students learn by explaining concepts and guiding their thinking, but do not complete their work for them."
    }]
  }
}
```

## Conclusion

IronUTF provides powerful, flexible defense capabilities for AI endpoints. By combining prompt filtering and decoration, you can create secure, customized AI experiences that meet your specific requirements while protecting against common threats.

Remember to:
- Test configurations thoroughly
- Monitor for false positives
- Update patterns regularly
- Consider provider-specific limitations
- Maintain defense in depth

For additional support, refer to the official APISIX documentation or contact your ViolentUTF administrator.
