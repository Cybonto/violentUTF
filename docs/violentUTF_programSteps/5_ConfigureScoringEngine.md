# 5. Configure Scoring Engine

This section provides a comprehensive interface for configuring PyRIT scorers that evaluate AI model outputs for safety, security, and policy compliance. The enhanced interface features category-first selection, smart parameter handling, integrated testing capabilities, and a management dashboard for scorer administration.

## Enhanced Features:
- **Category-first scorer selection** based on use case and evaluation needs
- **Six comprehensive scorer categories** from Pattern Matching to Cloud-Based Professional
- **Two-column responsive layout** with configuration and management sections
- **Smart parameter handling** with type-aware widgets and validation
- **Integrated testing system** with category-specific test cases
- **AI Gateway access control** for LLM-based scorers
- **Scorer management dashboard** with test, clone, and delete operations

## 5a. Page Header and Context

### Display:
- **Page Title**: "5. Configure Scoring Engine" with target emoji (🎯)
- **Pipeline Context Banner**: "PyRIT Pipeline: Configure Scorers that evaluate AI responses for safety, bias, and policy compliance"
- **Quick Start Guide**: Expandable section with links to comprehensive Guide_scorers.md
- **System Status**: Current scorer count and generator availability summary

### Context Information:
- **Purpose Explanation**: Help users understand scorer evaluation capabilities
- **Reference Documentation**: Link to detailed Guide_scorers.md for comprehensive information
- **Quick Setup Tips**: Step-by-step overview of the configuration process

### Backend:
- **Authentication Validation**: Ensure user is logged in before proceeding
- **PyRIT Memory Check**: Verify memory initialization for scorer testing
- **Generator Loading**: Load available generators for chat_target parameters
- **Session State Initialization**: Set up scorer management variables

## 5b. Main Content Layout

### System Status Display:
- **Current Status Indicators**:
  - ✅ "Current Status: X scorer(s) configured" (when scorers exist)
  - ⚠️ "Current Status: No scorers configured yet" (when none exist)
- **Generator Availability**:
  - 🎯 "Available Generators: X generator(s) available for chat targets" (with AI access)
  - 🔒 "Limited Generator Access: X generator(s) configured but AI Gateway access is disabled"
- **AI Gateway Access Control**:
  - ❌ "AI Gateway Access Required: SelfAsk scorers need AI Gateway access to function properly"
  - 💡 "Solution: Contact your administrator to enable the 'ai-api-access' role for your account"
  - ℹ️ "Alternative: You can still use non-AI scorers like Pattern Matching, Cloud-Based, and Utility scorers"

### Two-Column Layout:
- **Left Column**: 🎯 Configure New Scorer
- **Right Column**: 📊 Scorer Management

## 5c. Configure New Scorer (Left Column)

### Step 1: Category-First Selection

**Display:**
- **Step 1: Select Scorer Category** with dropdown selection
- **Six Main Categories** based on use case and evaluation approach:

#### 1. Pattern Matching Scorers
- **Description**: Fast, reliable detection of specific content patterns using simple matching techniques
- **Strengths**: Lightning fast (no LLM calls), 100% reliable, Resource efficient, Perfect for keywords
- **Limitations**: Limited context understanding, High false positives, Narrow scope
- **Best Scenarios**: Quick pre-filtering, Policy violations, Technical content detection, High-volume scanning
- **Available Scorers**: SubStringScorer

#### 2. Self-Ask Scorer Family
- **Description**: Versatile LLM-based evaluation using custom questions for flexible, context-aware scoring
- **Strengths**: Highly customizable, Context aware, Natural language criteria, Flexible output formats
- **Limitations**: Requires LLM calls, Variable results, Quality dependent on LLM, Needs prompt engineering
- **Best Scenarios**: Subjective evaluation, Custom policies, Domain-specific criteria, Research experiments
- **Available Scorers**: SelfAskTrueFalseScorer, SelfAskLikertScorer, SelfAskCategoryScorer, SelfAskScaleScorer, SelfAskRefusalScorer

#### 3. Security and Attack Detection
- **Description**: Specialized detection of adversarial attacks, jailbreaks, and security threats against AI systems
- **Strengths**: Attack specialized, Professional grade, Real-time detection, Threat intelligence
- **Limitations**: Narrow focus, External dependencies, Cost considerations, False positives
- **Best Scenarios**: Production AI systems, Red-teaming, Security research, Customer-facing applications
- **Available Scorers**: PromptShieldScorer

#### 4. Human Evaluation
- **Description**: Human oversight and judgment for complex, subjective, or culturally sensitive evaluation cases
- **Strengths**: Human expertise, Complex understanding, Ground truth, Flexible criteria
- **Limitations**: Slow and expensive, Scalability issues, Consistency challenges, Subjective variability
- **Best Scenarios**: Training datasets, Cultural sensitivity, Quality assurance, Ground truth research
- **Available Scorers**: HumanInTheLoopScorer

#### 5. Utility and Meta-Scoring
- **Description**: Tools for combining, transforming, and orchestrating other scorers into sophisticated evaluation pipelines
- **Strengths**: Orchestration capabilities, Logical operations, Score transformation, Workflow integration
- **Limitations**: Added complexity, Dependencies on other scorers, Debugging difficulty, Performance impact
- **Best Scenarios**: Comprehensive evaluation, Complex policies, Research workflows, Multi-requirement systems
- **Available Scorers**: CompositeScorer, FloatScaleThresholdScorer, TrueFalseInverterScorer

#### 6. Cloud-Based Professional Scorers
- **Description**: Enterprise-grade cloud services for production-ready safety and content evaluation
- **Strengths**: Production ready, Professional support, Regular updates, High reliability, Compliance ready
- **Limitations**: Cost considerations, External dependencies, Limited customization, Data privacy concerns
- **Best Scenarios**: Production applications, Compliance requirements, High-volume moderation, Professional support needs
- **Available Scorers**: AzureContentFilterScorer

### Category Information Display:
- **Expandable "About {Category}" Section** showing:
  - **Purpose**: Detailed description of category capabilities
  - **Two-column layout**:
    - **Left**: ✅ Strengths (bulleted list of advantages)
    - **Right**: ⚠️ Limitations (bulleted list of constraints)
  - **Best Scenarios**: Comma-separated list of optimal use cases

### Step 2: Specific Scorer Selection

**Display:**
- **Step 2: Select Specific Scorer** dropdown
- **System Validation**: Filter available scorers to only those actually available in the system
- **Error Handling**: Warning if no scorers from selected category are available

**Backend:**
- **Dynamic Filtering**: Compare category scorers with system-available scorers
- **Availability Check**: Only show scorers that are actually instantiable
- **Error Recovery**: Graceful handling when category scorers are unavailable

### Step 3: Scorer Configuration

**Display:**
- **Step 3: Configure Scorer** section
- **Unique Scorer Name Input**: Required field with validation
- **Parameter Configuration**: Dynamic form based on scorer requirements

## 5d. Smart Parameter Configuration

### Parameter Discovery and Grouping:
- **Required Parameters**: Displayed prominently with asterisks
- **Optional Parameters**: Grouped in expandable section
- **Parameter Types**: Intelligent widget selection based on type

### Type-Aware Parameter Widgets:

#### Complex Type Handling:
- **chat_target Parameter**: Special handling for Self-Ask scorers requiring AI generators
  - **AI Gateway Access Check**: Verify user has 'ai-api-access' role
  - **Generator Selection**: Dropdown of configured generators from Step 2
  - **Access Control Messages**:
    - 🔒 "AI Gateway Access Required" (when access disabled)
    - ✅ "Using generator 'X' as chat target" (when properly configured)
    - ❌ "Generator 'X' doesn't have a valid target instance" (when invalid)
  - **Fallback Options**: Clear guidance for users without AI access

#### Standard Parameter Types:
- **Literal Choices**: `st.selectbox()` for predefined options
- **Boolean**: `st.checkbox()` with appropriate defaults
- **Integer/Float**: `st.number_input()` with proper step values
- **String**: `st.text_input()` with password type for sensitive fields
- **List**: `st.text_input()` with comma-separated format
- **Complex Objects**: Informational messages for auto-handled parameters

### Parameter Validation:
- **Required Field Checking**: Real-time validation with error messages
- **Type Conversion**: Automatic conversion to proper Python types
- **Success Indicators**: ✅ Green checkmarks for valid parameters
- **Error Messages**: ❌ Clear explanations for invalid inputs

### Save and Test Integration:
- **Conditional Button**: "💾 Save and Test Scorer" enabled only when valid
- **Validation Gates**: Name uniqueness and parameter completeness checks
- **User Guidance**: Clear instructions when requirements not met

## 5e. Scorer Management Dashboard (Right Column)

### Dashboard Overview:
- **Empty State**: "🔍 No scorers configured yet. Configure your first scorer on the left!"
- **Categorized Display**: Group scorers by their respective categories
- **Expandable Sections**: 📁 Category folders with scorer counts

### Scorer Display Format:
- **Scorer Information**:
  - **Scorer Name**: Bold heading with unique identifier
  - **Type Caption**: Scorer class type for reference
- **Action Buttons** (three-column layout):
  - **🧪 Test**: Quick testing with sample inputs
  - **📋 Clone**: Create copy with different name
  - **🗑️ Delete**: Remove scorer with confirmation

### Interactive Operations:
- **Test Operations**: Full-featured testing interface outside main column layout
- **Clone Operations**: Automatic unique name generation with incremental counters
- **Delete Operations**: Confirmation workflow with cancel option

## 5f. Integrated Testing System

### Testing Interface Design:
- **Modal-Style Testing**: Appears below management section when activated
- **Tab-Based Input Selection**:
  - **🚀 Quick Test**: Pre-defined category-specific test cases
  - **✏️ Custom Input**: User-provided test content

### Category-Specific Test Cases:

#### Pattern Matching Scorers:
- Admin credentials and sensitive information
- Normal messages without sensitive content
- URLs and technical content

#### Self-Ask Scorer Family:
- Biased statements for evaluation
- Medical advice scenarios
- Quality assessment examples

#### Security and Attack Detection:
- Jailbreak attempts and prompt injections
- Role-playing attacks
- Normal AI capability discussions

#### Human Evaluation:
- Cultural and emotional content
- Complex ethical dilemmas
- Nuanced interpretation scenarios

#### Utility and Meta-Scoring:
- Multi-criteria evaluation content
- Score combination scenarios
- Threshold-based decision examples

#### Cloud-Based Professional Scorers:
- Hate speech and discrimination
- Violence and harm instructions
- Professional content evaluation

### Test Execution and Results:
- **Async Testing**: Non-blocking test execution with spinners
- **Result Formatting**: Structured display of score values, categories, and rationales
- **Error Handling**: Comprehensive error catching with user-friendly messages
- **Performance Tracking**: Response time and success rate monitoring

## 5g. Save and Test Workflow

### Scorer Saving Process:
1. **Validation Checks**: Name uniqueness and parameter completeness
2. **Debug Logging**: Comprehensive parameter logging for troubleshooting
3. **Scorer Instantiation**: Test instantiation before saving
4. **Configuration Storage**: Save to persistent configuration files
5. **Session State Update**: Add to current session for immediate use

### Automatic Testing:
- **Category-Specific Samples**: Use first test case from category examples
- **Test Execution**: Run immediate validation test
- **Result Display**: Show test results in expandable section
- **Success Confirmation**: Clear feedback on save and test success

### Error Recovery:
- **Save Failures**: Clear error messages with troubleshooting guidance
- **Test Failures**: Separate handling for save success but test failure
- **Session Management**: Proper cleanup on errors

## 5h. AI Gateway Access Control

### Access Level Detection:
- **Role Verification**: Check for 'ai-api-access' role in user permissions
- **Generator Validation**: Verify generators have valid target instances
- **Access Status Display**: Clear indicators of current access level

### Restricted Access Handling:
- **Error Messages**: 🔒 "AI Gateway Access Required" for Self-Ask scorers
- **Administrative Guidance**: Contact information for role enablement
- **Alternative Options**: Suggest non-AI scorer categories as alternatives
- **Generator Status**: Show configured generators with access status

### Fallback Options:
- **Non-AI Scorers**: Highlight Pattern Matching, Cloud-Based, and Utility scorers
- **Graceful Degradation**: System remains functional without AI access
- **Clear Communication**: Explain what's available vs. what requires access

## 5i. Next Steps and Workflow Completion

### Configuration Summary:
- **Two-Column Layout**:
  - **Left**: ✅ "Ready to proceed!" with scorer count and category breakdown
  - **Right**: 💡 "Recommended Combinations" with best practice suggestions

### Recommended Combinations:
- **For comprehensive protection**: Pattern Matching + Self-Ask Family (fast + flexible)
- **Security focused**: Security Detection + Cloud Services (attack + content safety)
- **Quality assurance**: Human Evaluation for subjective assessment
- **Quick Templates**:
  - **Basic Safety**: Azure + SubString scorers
  - **Research Setup**: Self-Ask + Human-in-loop
  - **Production**: Multi-layer with all categories

### Completion Validation:
- **Readiness Check**: Ensure at least one scorer is configured
- **Navigation Control**: Enable "Next: Configure Orchestrators" only when ready
- **Session State Management**: Set completion flags for workflow tracking
- **Error Handling**: Graceful navigation error handling

This enhanced scorer configuration provides a comprehensive, category-driven interface for configuring PyRIT scorers with intelligent access control, robust testing capabilities, and seamless workflow integration for AI red-teaming scenarios.