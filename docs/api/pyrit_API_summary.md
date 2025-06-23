## Pyrit API Summary

This document outlines the key components of PyRIT (Python Risk Identification Toolkit) for system engineering design, focusing on extensibility and core functionality.

**I. Core Modules and Classes**

The central modules for extending and using PyRIT are:

*   **`pyrit.memory`**:  Handles persistent storage of conversation data, prompts, scores, and embeddings.  Crucial for tracking interactions and enabling attacks that leverage conversation history.
    *   **`MemoryInterface` (Abstract Base Class)**: Defines the interface for all memory implementations.  Key methods:
        *   `add_request_pieces_to_memory()`: Stores prompt requests.
        *   `add_request_response_to_memory()`: Stores prompt responses and automatically handles embedding generation (if enabled).
        *   `add_scores_to_memory()`: Stores scores associated with prompts.
        *   `get_conversation()`: Retrieves a conversation by ID.
        *   `get_prompt_request_pieces()`: Retrieves prompts based on various filters (orchestrator ID, role, conversation ID, labels, etc.).
        *   `get_scores_by_*()`: Retrieves scores based on labels, orchestrator ID, or prompt IDs.
        *   `duplicate_conversation()`:  Essential for attacks that require branching conversations.
        *   `enable_embedding()` / `disable_embedding()`: Controls embedding generation.
        *    `export_conversations()`: Export the conversation data
    *   **Concrete Implementations**:
        *   `DuckDBMemory`: Uses DuckDB for local, file-based storage.  Good for development and single-machine deployments.
        *   `AzureSQLMemory`: Uses Azure SQL Server. Suitable for production and multi-user environments.
        *   `InMemoryMemory`: Not included, but implied. A basic in-memory store for quick testing.
    * **`CentralMemory`**: Provides singleton access to memory. This is called internally.
    *   **`EmbeddingDataEntry`**: SQLAlchemy model representing embedding data linked to conversation entries.
    *   **`PromptMemoryEntry`**: SQLAlchemy model for prompt data, including original/converted values, timestamps, labels, and metadata.
    * **`MemoryExporter`**: Handles data exporting, such as to JSON.

*   **`pyrit.prompt_target`**: Defines how PyRIT interacts with target models/systems.
    *   **`PromptTarget` (Abstract Base Class)**: The base class for all target interactions.  Key method:
        *   `send_prompt_async()`: Sends a prompt to the target and returns a `PromptRequestResponse`.
    *   **`PromptChatTarget` (Abstract Base Class)**: Extends `PromptTarget` for conversational (chat-based) targets. Includes:
        *   `set_system_prompt()`:  Sets the system prompt for the target.
        * `is_json_response_supported()`: Checks if the JSON mode is supported.
        * `is_response_format_json()`: Sets JSON as the response format if supported.
    *   **Concrete Implementations**:
        *   `OpenAIChatTarget`, `OpenAICompletionTarget`, `OpenAIDALLETarget`, `OpenAITTSTarget`: For interacting with OpenAI and Azure OpenAI APIs (chat, completion, image generation, text to speach).
        *   `HuggingFaceChatTarget`, `HuggingFaceEndpointTarget`: For local Hugging Face models and cloud-hosted endpoints.
        *   `AzureMLChatTarget`: For models deployed on Azure AI Machine Learning Studio endpoints.
        *   `OllamaChatTarget`: Supports sending prompts to Ollama.
        *   `HTTPTarget`:  A generic target for interacting with any HTTP endpoint (useful for custom APIs or web interfaces).
        *   `TextTarget`:  A simple target that writes prompts to an output stream (e.g., `stdout`). Useful for manual testing.
    *  **`limit_requests_per_minute`**: Decorator to enforce rate limiting.

*   **`pyrit.orchestrator`**:  Manages the overall attack process, coordinating prompt generation, sending, and scoring.
    *   **`Orchestrator` (Abstract Base Class)**:  Base class for orchestrators.
    *   **`PromptSendingOrchestrator`**: Sends prompts to a target, optionally applying converters and scorers.
    *   **`MultiTurnOrchestrator` (Abstract Base Class)**:  Handles multi-turn attacks, managing conversations between an adversarial chat model and the objective target.
    *   **Concrete Implementations**:
        *   `RedTeamingOrchestrator`:  A basic multi-turn orchestrator for red teaming.
        *   `CrescendoOrchestrator`: Implements the Crescendo attack (multi-turn, progressive guidance).
        *   `PAIROrchestrator`: Implements the Prompt Automatic Iterative Refinement (PAIR) algorithm.
        *   `TreeOfAttacksWithPruningOrchestrator`: Implements the Tree of Attacks with Pruning (TAP) algorithm.
        * `FuzzerOrchestrator`: Performs fuzzing.
        *   `XPIAOrchestrator`, `XPIATestOrchestrator`, `XPIAManualProcessingOrchestrator`: For cross-domain prompt injection attacks.
        * `SkeletonKeyOrchestrator`: Implements the Skeleton Key attack.
        * `ScoringOrchestrator`: For scoring prompts in memory.

*   **`pyrit.prompt_converter`**:  Transforms prompts before sending them to the target.
    *   **`PromptConverter` (Abstract Base Class)**:  Defines the interface for converters. Key methods:
        *   `convert_async()`:  Transforms a single prompt.
        *   `convert_tokens_async()`: Transforms specific parts of a prompt, delimited by tokens.
        *   `input_supported()` / `output_supported()`: Checks for supported data types.
    *   **Concrete Implementations**:
        *   `AsciiArtConverter`, `Base64Converter`, `CaesarConverter`, `EmojiConverter`, `LeetspeakConverter`, `MorseConverter`, `ROT13Converter`, `UnicodeConfusableConverter`, `UrlConverter`, `CharacterSpaceConverter`, `StringJoinConverter`, `SuffixAppendConverter`:  Various text-based transformations.
        *   `AddImageTextConverter`, `QRCodeConverter`: Image-related converters.
        *   `AzureSpeechTextToAudioConverter`, `AzureSpeechAudioToTextConverter`, `AudioFrequencyConverter`: Audio converters.
        * `TranslationConverter`, `ToneConverter`, `TenseConverter`, `VariationConverter`, `NoiseConverter`, `MathPromptConverter`, `MaliciousQuestionGeneratorConverter`, `PersuasionConverter`, `LLMGenericTextConverter`: Converters that use LLMs to transform input text.
        * `HumanInTheLoopConverter`: Allows the user to review, modify or use a converter on prompts.

*   **`pyrit.score`**:  Evaluates the responses from the target.
    *   **`Scorer` (Abstract Base Class)**: Defines the scoring interface.  Key method:
        *   `score_async()`: Scores a `PromptRequestPiece` and returns a list of `Score` objects.
    *   **Concrete Implementations**:
        *   `AzureContentFilterScorer`: Uses Azure Content Safety API for scoring.
        *   `SelfAskLikertScorer`, `SelfAskCategoryScorer`, `SelfAskTrueFalseScorer`, `SelfAskScaleScorer`: Uses "self-ask" techniques to score prompts.
        *   `SubStringScorer`:  Checks for the presence of a substring.
        * `PromptShieldScorer`: Uses an endpoint running Prompt Shield to determine if an attack is present.
        *   `GandalfScorer`:  Scores based on Gandalf game levels.
        * `HumanInTheLoopScorer`: Enables scoring by a human in the loop.
        * `MarkdownInjectionScorer`: Checks for markdown injection.
        * `FloatScaleThresholdScorer`: Converts other scores to true/false.
        * `TrueFalseInverterScorer`: Inverts true/false scores.

* **`pyrit.chat_message_normalizer`**: Converts conversation messages to formats used by specific models.
    * **`ChatMessageNormalizer`** (Abstract Base Class): Base class.
    * **Concrete Implementations**:
        * `ChatMessageNop`: Returns the same list passed in.
        * `ChatMessageNormalizerChatML`: Converts to ChatML format.
        * `ChatMessageNormalizerTokenizerTemplate`: Applies chat template from a tokenizer.
        * `GenericSystemSquash`: Returns first system message combined with first user message.
*   **`pyrit.models`**:  Defines data models used throughout the framework.  Key models:
    *   `ChatMessage`: Represents a single message in a conversation (role, content).
    *   `PromptRequestPiece`:  Represents a single prompt or response, including original and converted values, metadata, and associated identifiers.
    *   `PromptRequestResponse`:  Groups `PromptRequestPiece` objects for a single request, often used to represent a turn in a conversation.
    *   `Score`: Represents a score assigned to a prompt or response (type, value, category, rationale).
    * `SeedPrompt`: Represents a seed prompt.
    * `SeedPromptDataset`: Manages lists of SeedPrompts.
    * `SeedPromptGroup`: Represents a group of prompts.
    *   `EmbeddingResponse`, `EmbeddingData`, `EmbeddingUsageInformation`:  Models for handling embedding data.

* **`pyrit.datasets`**: Provides functions to automatically fetch and load commonly used datasets.
    *   `fetch_adv_bench_dataset`, `fetch_harmbench_dataset`, `fetch_xstest_dataset`, `fetch_decoding_trust_stereotypes_dataset`, `fetch_seclists_bias_testing_dataset`, `fetch_pku_safe_rlhf_dataset`, `fetch_wmdp_dataset`, `fetch_forbidden_questions_dataset`,`fetch_tdc23_redteaming_dataset`, `fetch_aya_redteaming_dataset`:  Functions to fetch specific datasets.
    *   `fetch_many_shot_jailbreaking_dataset`:  Fetches a jailbreaking dataset.
    *   `fetch_examples`:  A generic function to fetch examples from various sources.

* **`pyrit.auth`**: Handles authentication, particularly for Azure services.
  * `Authenticator`: Abstract base class
  * `AzureAuth`: Authenticator using Azure credentials

*   **`pyrit.common`**:  Utility functions and classes.
    *   `initialize_pyrit()`:  Initializes PyRIT, setting up memory and loading environment variables.
    *   `get_required_value()`, `get_non_required_value()`:  Helpers for retrieving environment variables.
    * `Singleton`: Ensures singleton.
    * `YamlLoadable`: Abstract base class for objects that can be loaded from YAML files.

* **`pyrit.exceptions`**: Defines custom exception classes.
    * `PyritException`: Base exception class.
    * `BadRequestException`, `RateLimitException`, `EmptyResponseException`, `InvalidJsonException`, `MissingPromptPlaceholderException`: Specific exception types.
    * `pyrit_json_retry`, `pyrit_target_retry`, `pyrit_placeholder_retry`: Decorators to retry functions on failure.
    * `remove_markdown_json`: Removes markdown formatting from a string.

**II. System Engineering Design Considerations**

1.  **Extensibility**:  PyRIT is designed for extensibility. New targets, converters, scorers, and orchestrators can be added by subclassing the abstract base classes and implementing the required methods.

2.  **Modularity**:  The framework is divided into distinct modules, each with a specific responsibility (memory, targets, orchestrators, etc.). This promotes code organization and maintainability.

3.  **Data Flow**:  The typical data flow is:
    *   `Orchestrator` selects prompts (potentially using a `SeedPromptDataset`).
    *   `PromptConverter` (optionally) transforms the prompts.
    *   `PromptTarget` sends the prompts to the target system.
    *   `PromptTarget` receives the response and returns a `PromptRequestResponse`.
    *   `Scorer` (optionally) evaluates the response.
    *   `MemoryInterface` stores the prompt, response, and scores.

4.  **Asynchronous Operations**:  PyRIT heavily utilizes asynchronous operations (`async`/`await`) to handle interactions with external systems (LLMs, APIs) efficiently.  This is crucial for performance, especially when dealing with multiple targets or large datasets.

5.  **Configuration**:  Configuration is primarily managed through environment variables (e.g., API keys, endpoints) and YAML files (e.g., for defining system prompts, scorer parameters).  The `get_required_value()` and `get_non_required_value()` functions provide a consistent way to access configuration.

6.  **Memory Management**: The `MemoryInterface` and its implementations provide a flexible way to store conversation data.  The choice of memory backend (DuckDB, Azure SQL, in-memory) depends on the deployment scenario.

7.  **Error Handling**: Custom exception classes (`PyritException` and subclasses) provide a structured way to handle errors.  Retry decorators (`pyrit_target_retry`, etc.) are used to handle transient errors.

8. **Datasets**: The `pyrit.datasets` module allows loading in common datasets to simplify red-teaming.

9. **Authentication:** The `pyrit.auth` module and `Authenticator` classes allow for multiple authentication methods.

**III. Example Workflow (Simplified)**

```python
from pyrit.prompt_target import OpenAIChatTarget
from pyrit.orchestrator import PromptSendingOrchestrator
from pyrit.common import initialize_pyrit

# 1. Initialize PyRIT (sets up memory, loads config)
initialize_pyrit(memory_db_type="InMemory")

# 2. Create a PromptTarget (e.g., OpenAI Chat)
target = OpenAIChatTarget(deployment_name="your_deployment", endpoint="your_endpoint", api_key="your_key")

# 3. Create an Orchestrator (e.g., PromptSendingOrchestrator)
orchestrator = PromptSendingOrchestrator(objective_target=target)

# 4. Define prompts
prompts = ["Tell me a harmful joke.", "Write a malicious script."]

# 5. Send prompts and get responses
responses = await orchestrator.send_prompts_async(prompt_list=prompts)

# 6. (Optional) Use a Scorer to evaluate responses
# scorer = YourCustomScorer(...)
# scores = await scorer.score_responses_async(responses)

# 7. (Optional) Access conversation history through memory
# memory = orchestrator.get_memory()
# conversations = memory.get_conversation(conversation_id=...)

#Clean Up resources
orchestrator.dispose_db_engine()
