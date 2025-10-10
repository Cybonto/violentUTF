# SimpleChat Documentation Access Guide

This guide explains how to use SimpleChat's enhanced documentation access features to get information about ViolentUTF directly through natural language queries.

## Overview

ViolentUTF's SimpleChat application now includes integrated documentation access through the Model Context Protocol (MCP). This allows you to ask questions about ViolentUTF and receive relevant information from the extensive documentation library.

## Features

### Natural Language Documentation Queries

SimpleChat can now understand and respond to documentation-related questions using natural language patterns:

- **Setup Questions**: "How do I set up ViolentUTF?" or "What are the setup requirements?"
- **Troubleshooting**: "How to fix authentication errors?" or "Troubleshoot Docker issues"
- **Concepts**: "What is PyRIT?" or "Explain ViolentUTF architecture"
- **Configuration**: "How to configure AI providers?" or "Setup Keycloak authentication"
- **Usage**: "How to use the API?" or "Run security tests with Garak"

### Supported Query Patterns

The system recognizes several natural language patterns:

1. **How-to queries**: "how do I...", "how to...", "how can I..."
2. **What-is queries**: "what is...", "what are...", "explain..."
3. **Troubleshooting**: "troubleshoot...", "fix...", "resolve..."
4. **Configuration**: "configure...", "setup...", "install..."
5. **General search**: Any documentation-related keywords

## Using Documentation Features

### Basic Usage

1. **Open SimpleChat**: Navigate to http://localhost:8501 after ViolentUTF setup
2. **Login**: Use your ViolentUTF credentials (violentutf.web / [generated password])
3. **Ask Questions**: Type natural language questions about ViolentUTF

### Example Conversations

```
User: How do I set up ViolentUTF on macOS?

SimpleChat: Based on the ViolentUTF documentation, here's how to set up ViolentUTF on macOS:

1. Run the setup script: `./setup_macos_new.sh`
2. The script will automatically:
   - Configure Docker containers
   - Set up Keycloak authentication
   - Initialize APISIX gateway
   - Deploy all services

[Additional relevant documentation content...]

Sources: setup_macos_new.sh documentation, installation guides
```

```
User: What is PyRIT and how is it integrated with ViolentUTF?

SimpleChat: PyRIT (Python Risk Identification Toolkit) is Microsoft's framework for AI red-teaming...

[Detailed explanation with relevant documentation]

Sources: PyRIT integration documentation, architecture guides
```

### Advanced Features

#### Specific Documentation Searches

You can request specific types of documentation:

- "Show me troubleshooting guides"
- "Find setup documentation"
- "Search for API examples"
- "Get configuration guides"

#### Multi-Document Responses

The system can combine information from multiple documentation sources to provide comprehensive answers.

## Technical Details

### MCP Integration

The documentation access is powered by:

- **DocumentationResourceProvider**: Indexes and searches all markdown files in the `./docs/` directory
- **Full-text Search**: Searches content, headers, and metadata
- **Smart Ranking**: Relevance scoring based on query matching and document metadata
- **Citation Support**: Provides source references for all information

### Supported File Types

- **Markdown files** (`.md`): All documentation in the `./docs/` directory
- **Metadata extraction**: Automatically extracts titles, categories, and content structure
- **Cross-references**: Links between different documentation sections

### Search Capabilities

- **Content search**: Full-text search across document content
- **Header matching**: Prioritizes matches in document headers
- **Category filtering**: Organizes results by documentation category
- **Relevance scoring**: Ranks results by relevance to the query

## Configuration

### Environment Variables

The documentation system uses these environment variables (automatically set during setup):

```env
MCP_ENABLE_DOCUMENTATION=true
DOCUMENTATION_ROOT_PATH=./docs
```

### Documentation Structure

The system indexes documentation from:

```
./docs/
├── plans/          # Implementation plans and designs
├── troubleshooting/ # Troubleshooting guides
└── guides/         # User guides (including this one)
```

## Troubleshooting

### Common Issues

#### "No documentation found" Error

**Problem**: SimpleChat responds that no relevant documentation was found.

**Solutions**:
1. Check that the `./docs/` directory contains markdown files
2. Verify MCP server is running and accessible
3. Try rephrasing your question with different keywords

#### Authentication Issues

**Problem**: MCP requests fail with authentication errors.

**Solutions**:
1. Ensure you're logged into SimpleChat with valid credentials
2. Check that JWT tokens are working correctly
3. Verify APISIX gateway is routing MCP requests properly

#### Slow Response Times

**Problem**: Documentation queries take a long time to respond.

**Solutions**:
1. The system builds an index on first use - subsequent queries will be faster
2. Check system resources if indexing is slow
3. Verify network connectivity to the MCP server

### Debug Information

To enable debug logging for documentation queries:

1. Set verbosity to debug mode: `./setup_macos_new.sh --debug`
2. Check FastAPI logs for MCP documentation provider activity
3. Use browser developer tools to inspect SimpleChat MCP communications

## Best Practices

### Effective Query Techniques

1. **Be Specific**: "How to configure OpenAI API key" vs. "API configuration"
2. **Use Keywords**: Include relevant technical terms like "PyRIT", "Garak", "APISIX"
3. **Ask Follow-ups**: Build on previous questions for deeper understanding
4. **Request Examples**: Ask for specific examples or code snippets

### Query Examples

**Good Queries**:
- "How do I troubleshoot Keycloak authentication issues?"
- "What are the Docker requirements for ViolentUTF?"
- "Explain the difference between PyRIT and Garak integration"
- "Show me how to configure AI provider routes"

**Less Effective Queries**:
- "Help" (too general)
- "Error" (needs more context)
- "Setup" (too broad - be more specific)

## Integration with Other Features

### MCP Tools and Resources

The documentation system integrates with other MCP features:

- **Tool Discovery**: Find tools related to documentation topics
- **Resource Access**: Access configuration files and examples
- **Prompt Library**: Use documentation-aware prompts

### API Integration

Documentation queries can also be made via the REST API:

```bash
curl -X POST http://localhost:9080/mcp/sse/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "resources/read",
    "params": {
      "uri": "violentutf://docs/setup/macos_setup",
      "query": "Docker requirements"
    },
    "id": 1
  }'
```

## Support and Feedback

For issues with the documentation system:

1. Check the troubleshooting section above
2. Review MCP server logs in the FastAPI container
3. Verify documentation files are present and readable
4. Report issues via the ViolentUTF issue tracker

## Future Enhancements

Planned improvements to the documentation system:

- **Multi-language Support**: Support for documentation in multiple languages
- **Version Control**: Track changes to documentation over time
- **Interactive Examples**: Executable code examples within documentation
- **External Documentation**: Integration with external documentation sources
- **Advanced Search**: Semantic search using AI embeddings

---

*This guide is part of the ViolentUTF documentation system and can be accessed through SimpleChat by asking "How do I use documentation features?" or similar queries.*
