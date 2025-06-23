# Using Simple Chat for ViolentUTF Workflow Configuration

## Overview

Simple Chat's MCP (Model Context Protocol) integration enables you to configure and execute ViolentUTF workflows using natural language commands instead of navigating through multiple configuration pages. This guide demonstrates how to use Simple Chat to set up generators, datasets, converters, scorers, and run complete red-teaming evaluations.

## Prerequisites

- ViolentUTF fully set up with API running
- Access to Simple Chat with AI Gateway enabled
- JWT token with 'ai-api-access' role
- Basic understanding of ViolentUTF components

## Natural Language Command System

Simple Chat recognizes both explicit MCP commands and natural language requests:

### Explicit Commands
- `/mcp help` - Show available commands
- `/mcp list generators` - List configured generators
- `/mcp list datasets` - List loaded datasets
- `/mcp list converters` - List configured converters
- `/mcp list scorers` - List configured scorers
- `/mcp list orchestrators` - List configured orchestrators
- `/mcp dataset <name>` - Load a specific dataset
- `/mcp test jailbreak` - Run jailbreak tests
- `/mcp test bias` - Run bias tests

### Natural Language
- "Create a GPT-4 generator with temperature 0.7"
- "Load the jailbreak dataset"
- "Configure a bias scorer"
- "Show me available converters" - List converter types
- "What converters are configured" - List configured converters
- "Show available dataset options" - List dataset types
- "What datasets are loaded" - List loaded datasets
- "Run a red team test on GPT-4"

## Workflow 1: Configure a Generator

### Simple Configuration

**Natural Language Command:**
```
Create an OpenAI generator with GPT-4 and temperature 0.8
```

**What Happens:**
1. MCP parses your intent and extracts parameters
2. Creates generator via API with:
   - Name: `openai_gpt-4_20240617_123456`
   - Type: `AI Gateway`
   - Provider: `openai`
   - Model: `gpt-4`
   - Temperature: 0.8
3. Returns confirmation with generator ID

**Response Example:**
```
🔧 Detected configuration command: generator
🤖 Creating generator...
✅ Successfully created generator 'openai_gpt-4_20240617_123456'!
ID: `gen_123456`
```

### Advanced Configuration

**Natural Language Command:**
```
Create a Claude 3.5 Sonnet generator with temperature 0.7, max tokens 2000, and name it "production-claude"
```

**Alternative Explicit Approach:**
```
/mcp create generator --provider anthropic --model claude-3-5-sonnet-latest --temperature 0.7 --max_tokens 2000 --name production-claude
```

### List and Verify Generators

**Commands:**
- "List all my generators"
- "Show configured generators"
- "/mcp list generators"

**Expected Output:**
```
📋 Listing configured generators...
✅ Found 2 configured generator(s):

🤖 openai_gpt-4_20240617_123456
  Provider: AI Gateway
  Model: gpt-4
  ID: `gen_123456`
  Parameters:
  - temperature: 0.8
  Created: 2024-06-17 12:34:56

🤖 production-claude
  Provider: AI Gateway
  Model: claude-3-5-sonnet-20241022
  ID: `gen_789012`
  Created: 2024-06-17 12:45:00
```

## Workflow 2: Load and Configure Datasets

### Load Existing Dataset

**Natural Language Commands:**
```
Load the harmbench dataset
```
or
```
/mcp dataset harmbench
```

**Expected Response:**
```
🔧 Detected configuration command: dataset
📂 Loading dataset: harmbench
Creating built-in dataset: HarmBench Dataset
✅ Successfully loaded 'harmbench' dataset!
ID: `ds_345678`
Items: 245

Dataset Details:
  Name: harmbench
  Type: harmbench
  Source: native
  Items: 245
  Size: 1.23 MB
  Created: Just now
```

### List Available Dataset Types

**Natural Language Commands:**
```
Show available dataset options
```
or
```
What datasets can I use?
```

**Expected Response:**
```
📋 Listing available dataset types...
**Built-in PyRIT Datasets:**
• **harmbench**: HarmBench - Comprehensive harmful behavior dataset
• **jailbreak**: Jailbreak Prompts - Collection of jailbreak attempts
• **promptinjection**: Prompt Injection - Injection attack patterns
• **bias**: Bias Testing - Prompts to test for biases
• **security**: Security Testing - Security-focused test prompts

**Custom Dataset Sources:**
• **CSV/Excel Upload**: Upload your own prompt datasets
• **Online URL**: Load datasets from web URLs
• **Manual Entry**: Create datasets manually
💡 Use commands like 'Load the harmbench dataset' to load a specific dataset
```

### Create Custom Dataset

**Natural Language Command:**
```
Create a dataset called "financial-risks" with prompts about financial fraud detection
```

**What Happens:**
1. MCP creates new dataset configuration
2. You can then add prompts through the Configure Datasets UI
3. Dataset becomes available for orchestrator use

### Combine Datasets

**Natural Language Command:**
```
Create a combined dataset from harmbench and promptinjection datasets
```

## Workflow 3: Configure Converters

### List Available Converters

**Natural Language Command:**
```
Show me available converters for prompt transformation
```

**Expected Response:**
```
🔧 Detected configuration command: converter
📋 Listing available converter types...
**Available PyRIT Converters:**
• **Base64Converter**: Encode prompts in Base64 format
• **CaesarConverter**: Apply Caesar cipher transformation
• **TranslationConverter**: Translate prompts to different languages
• **VariationConverter**: Generate prompt variations
• **ROT13Converter**: Apply ROT13 encoding
• **UnicodeConverter**: Convert to Unicode representations
• **ASCIIArtConverter**: Transform text to ASCII art
• **MorseConverter**: Convert to Morse code
• **EmojiConverter**: Replace words with emojis
• **PersuasionConverter**: Add persuasive elements
• **ToneConverter**: Change the tone of prompts
💡 Visit the 'Configure Converters' page to set up converters
```

### List Configured Converters

**Natural Language Command:**
```
What converters are configured?
```

**Expected Response:**
```
📋 Listing configured converters...
✅ Found 2 configured converter(s):

🔄 Base64 Encoder
  Type: Base64Converter
  ID: `conv_234567`
  Status: ready
  Created: 2024-06-17 13:00:00

🔄 Spanish Translator
  Type: TranslationConverter
  ID: `conv_345678`
  Status: ready
  Parameters:
  - target_language: spanish
  Created: 2024-06-17 13:15:00
```

### Configure Specific Converter

**Natural Language Commands:**
```
Configure a base64 converter for encoding prompts
```
or
```
Set up a translation converter for Spanish
```

**Expected Actions:**
- MCP identifies converter type from natural language
- For configuration: Shows guidance to use Configure Converters page
- For listing: Shows available converters or converter types

**Response:**
```
🔧 Detected configuration command: converter
💡 To configure converters, please visit the 'Configure Converters' page
Converters allow you to transform prompts using various techniques like translation, encoding, etc.
```

## Workflow 4: Configure Scorers

### Basic Scorer Setup

**Natural Language Commands:**
```
Configure a bias scorer for fairness evaluation
```
or
```
Set up a self-ask scorer using GPT-4
```

**Expected Response:**
```
🔧 Detected configuration command: scorer
📏 Configuring scorer...
✅ Successfully configured bias scorer!
ID: `scorer_456789`
Type: bias
```

### List Available Scorer Types

**Natural Language Commands:**
```
Show available scorer options
```
or
```
What scorer types are available?
```

**Expected Response:**
```
🔧 Detected configuration command: scorer
📋 Listing available scorer types...
**📏 Available PyRIT Scorer Types:**
• **bias**: Bias Scorer - Detects biased content in AI responses
• **security**: Security Scorer - Identifies security vulnerabilities  
• **harmful**: Harmful Content Scorer - Detects harmful or toxic content
• **self-ask**: Self-Ask Scorer - Uses LLM to evaluate responses
• **regex**: Regex Scorer - Pattern-based scoring
• **substring**: Substring Scorer - Checks for specific substrings
• **true-false**: True/False Scorer - Binary evaluation of responses
• **float-scale**: Float Scale Scorer - Numeric scoring from 0.0 to 1.0
💡 Use commands like 'Configure a bias scorer' to set up a specific scorer
```

### Advanced Scorer Configuration

**Natural Language Command:**
```
Create a custom scorer that checks for financial advice compliance using Claude with a threshold of 0.8
```

**What MCP Does:**
1. Identifies scorer type (custom/self-ask)
2. Sets model to Claude
3. Configures threshold parameter
4. Creates scorer configuration

### List Configured Scorers

**Commands:**
- "Show all scorers"
- "List my configured scorers"
- "/mcp list scorers"

**Expected Response:**
```
📋 Listing configured scorers...
✅ Found 2 configured scorer(s):

📏 Bias Fairness Scorer
  Type: bias
  ID: `scorer_456789`
  Created: 2024-06-17 14:00:00

📏 Security Self-Ask Scorer
  Type: self-ask
  ID: `scorer_567890`
  Parameters:
  - model: gpt-4
  - threshold: 0.8
  Created: 2024-06-17 14:15:00
```

## Workflow 5: Complete Red Team Evaluation

### Step-by-Step Workflow

**Step 1: Create Generator**
```
Create a GPT-4 generator for testing with temperature 0.7
```

**Step 2: Load Dataset**
```
Load the jailbreak dataset for security testing
```

**Step 3: Configure Scorer**
```
Set up a security scorer to detect harmful outputs
```

**Step 4: Run Evaluation**
```
Run a red team test on GPT-4
```

**Expected Response:**
```
🔧 Detected configuration command: orchestrator
🎭 Setting up orchestrator...
✅ Successfully set up red_team orchestrator!
ID: `orch_678901`
💡 You can now execute this orchestrator to run tests.
```

### One-Command Workflow

**Advanced Natural Language Command:**
```
Set up a complete red team test on GPT-4 using jailbreak prompts with bias and security scoring
```

**What MCP Orchestrates:**
1. Creates or uses existing GPT-4 generator
2. Loads jailbreak dataset
3. Configures both bias and security scorers
4. Sets up orchestrator with all components
5. Initiates evaluation run

## Workflow 6: Multi-Stage Testing Pipeline

### Complex Workflow Example

**Natural Language Sequence:**

1. **Initialize Components:**
   ```
   Create generators for GPT-4, Claude, and Llama-3
   ```

2. **Prepare Test Data:**
   ```
   Load harmbench and combine with custom financial prompts
   ```

3. **Configure Converters:**
   ```
   Set up base64 and translation converters for robustness testing
   ```

4. **Configure Scoring:**
   ```
   Configure bias, security, and hallucination scorers
   ```

5. **Run Comparative Evaluation:**
   ```
   Run comparative red team test across all three models with all scorers
   ```

## Command Patterns and Tips

### Parameter Extraction

MCP intelligently extracts parameters from natural language:

| Natural Language | Extracted Parameters |
|-----------------|---------------------|
| "temperature 0.8" | `temperature: 0.8` |
| "max tokens 1500" | `max_tokens: 1500` |
| "GPT-4" | `provider: openai, model: gpt-4` |
| "Claude" | `provider: anthropic, model: claude-*` |
| "bias scorer" | `scorer_type: bias` |

### Provider Mapping

| Mention | Provider | Models |
|---------|----------|--------|
| "GPT", "OpenAI" | openai | gpt-4, gpt-3.5-turbo |
| "Claude", "Anthropic" | anthropic | claude-3-5-sonnet, claude-3-opus |
| "Llama", "Local" | ollama | llama3, mistral, etc. |

### Action Keywords

| Keyword | MCP Action |
|---------|------------|
| "create", "make", "set up" | Create new configuration |
| "list", "show", "display" | List existing items |
| "load", "get", "use" | Load/activate resource |
| "run", "execute", "start" | Execute evaluation |
| "test", "evaluate" | Run testing workflow |

## Error Handling and Troubleshooting

### Common Issues

**Issue: "No generators configured yet"**
- Solution: Create a generator first using natural language
- Example: "Create a GPT-4 generator with temperature 0.8"

**Issue: "Dataset not found"**
- Solution: Check available datasets with "show available dataset options"
- Solution: Use exact dataset name: harmbench, jailbreak, bias, security, promptinjection

**Issue: "Failed to create generator"**
- Solution: Ensure JWT token is valid and has ai-api-access role
- Solution: Check API connectivity through APISIX gateway

**Issue: "API Error: 422"**
- Solution: Check field names match API expectations
- Common fixes:
  - Generators need "name" and "type" fields
  - Datasets need "name" and "source_type: native" for built-in datasets
  - Models should match exact names (e.g., "gpt-4" not "GPT-4")

**Issue: "Unhandled command type: list"**
- Solution: Specify the resource type: "list generators", "list datasets", etc.
- Updated in latest version to support all resource types

### Validation Commands

Check configurations before running:
```
List all generators
Show configured scorers
What datasets are loaded
List orchestrators
Show available converter options
What dataset types are available
```

### Distinguishing Between Types and Instances

**Available Types/Options:**
- "Show available dataset options" → Lists dataset types you can load
- "Show me available converters" → Lists converter types you can configure
- "What dataset types are available" → Shows built-in and custom options

**Configured/Loaded Instances:**
- "What datasets are loaded" → Lists actually loaded datasets
- "What converters are configured" → Lists configured converter instances
- "List generators" → Shows created generator instances

## Best Practices

### 1. Incremental Configuration
- Configure and test each component separately
- Verify each step before proceeding
- Use list commands to confirm configurations

### 2. Naming Conventions
- Use descriptive names for generators: "production-gpt4"
- Name datasets by purpose: "security-test-prompts"
- Label scorers clearly: "financial-compliance-scorer"

### 3. Workflow Documentation
- Save successful command sequences
- Document parameter choices
- Note effective scorer thresholds

### 4. Testing Strategy
- Start with small datasets
- Test individual components first
- Scale up to full evaluations

## Advanced Features

### Batch Operations

**Natural Language Command:**
```
Create generators for all available OpenAI models with temperature 0.7
```

### Conditional Workflows

**Natural Language Command:**
```
If the security score is below 0.5, run additional jailbreak tests
```

### Export and Reporting

**Natural Language Commands:**
```
Export evaluation results to CSV
Generate security report for the last test run
```

## Integration with UI Pages

After configuring via Simple Chat:
- View generators in "Configure Generators" page
- Check datasets in "Configure Datasets" page
- Monitor scorers in "Configure Scorers" page
- See results in "Dashboard" page

## Implementation Status

### Phase 3 Complete ✅
- Natural language command parsing fully integrated
- All commands execute real API calls
- Proper error handling and user feedback
- Support for listing both types and instances

### Available Commands
1. **Generators**: Create and list
2. **Datasets**: Load, list types, list loaded
3. **Converters**: List types, list configured
4. **Scorers**: Configure, list types, list configured
5. **Orchestrators**: Setup and list

### API Integration
- All commands go through APISIX Gateway
- JWT authentication required
- Proper field mapping for API compatibility
- Response unwrapping for nested data

## Example: Complete Security Evaluation

Here's a full example workflow for security testing:

```
User: Show available dataset options
Assistant: [Lists harmbench, jailbreak, bias, security, promptinjection datasets]

User: Create a GPT-4 generator with temperature 0.8
Assistant: ✅ Successfully created generator 'openai_gpt-4_20240617_123456'!

User: Load the harmbench dataset
Assistant: ✅ Successfully loaded 'harmbench' dataset! (245 items)

User: Show available scorer options
Assistant: [Lists bias, security, harmful, self-ask, regex, substring, true-false, float-scale scorer types]

User: Configure a bias scorer
Assistant: ✅ Successfully configured bias scorer!

User: Run a red team test on GPT-4
Assistant: ✅ Successfully set up red_team orchestrator!

User: List all my configurations
Assistant: [Shows all generators, datasets, scorers, and orchestrators]
```