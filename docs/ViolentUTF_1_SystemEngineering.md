# Violent UTF ("vaye tuff" )
## A\. Problem Statement
tba
## B\. Main Requirements
The following sub-sections describe the main program requirements. The operational requirements will be implicitly or explicitly described in the "Program Steps" section.
### **1. System Architecture and Design**
- **Modular Architecture**: The system must be designed using a modular architecture to facilitate the addition of new modules and features without impacting existing functionality.
- **Scalable Infrastructure**: Design the system to scale horizontally and vertically to handle increasing workloads and data volumes.
- **Separation of Concerns**: Ensure clear separation between data processing, business logic, and presentation layers to enhance maintainability.
- **Loose Coupling**: Use asynchronous communication and message queues to decouple system components, enhancing resilience and scalability.
- **Event-Driven Design**: Adopt an event-driven architecture to support real-time processing and responsiveness.
### **2. Accessibility and Interfaces**
- **Python backend**: Core functionalities are implemented in Python and categorized into modules as needed.
- **Web Interface**: All modules must be accessible through an intuitive and user-friendly Streamlit web interface that supports all major browsers and devices. 
- **Command Line Interface**: All modules must be accessible through a python file that takes proper parameters and can be executed in command line interfaces of different operating systems.
### **3. User Interaction and Experience**
- **Intuitive UI/UX**: Provide an intuitive user interface that simplifies complex tasks, reduces the learning curve, and enhances productivity.
- **Documentation and Help**: Offer comprehensive documentation, tutorials, and tooltips within the user interface.
### **4. Logging, Monitoring, and Alerting**
- **Comprehensive Logging**: Implement detailed logging for all system components, capturing system events, errors, and user activities.
- **Alerting Mechanisms**: Set up automated alerts for critical events, failures, and security incidents.
- **Try/catch mechanisms**: The system shall implement robust try/catch mechanisms at all major steps (file upload, parameter reading, file conversion, content extraction, table processing, and JSON enrichment).  
- **Corrupted file or partial conversion handling**:
  - Log detailed error messages (including error type, file name, timestamp, and stack trace) to the logs/ folder.  
  - Display clear user-facing error messages with suggested recovery actions (e.g., “The file appears to be corrupted. Please upload another copy or try again later.”) via both the Streamlit interface and CLI console output.  
  - For table or text extraction failures, the system should attempt a limited number of retry attempts (configurable in the parameter file) before resorting to saving any partially extracted data along with error annotations.  
### **5. Development and Deployment Practices**
- **Automated Testing**: Include unit tests, integration tests, and end-to-end tests to ensure system reliability and prevent regressions.
- **Version Control**: Use a robust version control system (e.g., Git) for all code, configurations, and scripts.
- **Reporting and Alerts**:
  - Track performance metrics and, when thresholds are exceeded (e.g., processing delays or high CPU/memory usage), alert system administrators.
  - Provide comprehensive reports that address system responsiveness under different load conditions.
### **6. Maintainability and Support**
- **Code Quality Standards**: Adhere to coding standards and best practices to enhance readability and maintainability.
- **Documentation**: Produce extensive documentation for system architecture, APIs, modules, and operational procedures.
- **Automated Maintenance Tasks**: Schedule and automate routine maintenance tasks like database indexing, log rotation, and system updates.
### **7. Data Quality and Validation**
- **Data Validation**: Implement validation rules to ensure data integrity and correctness at all stages of processing.
- **Error Correction**: Provide mechanisms to detect and correct errors or inconsistencies in data.
- **Quality Metrics**: Monitor and report on data quality metrics, such as completeness, accuracy, and consistency.

## C\. Main folder structure
```
/
│
├── Home.py                       # The index of all Red Team Streamlit-based apps
├── app_data/
│   │
│   ├── violentutf/               # Violent UTF folder to store application data
│   └── ...
├── pages/
│   │
│   ├── ViolentUTF.py             # The Violent UTF app page
│   └── ...
├── violentutf/                   # The Violent UTF backend
|   │
|   ├── parameters/                 # The folder to store the parameter (.yaml) files
|   ├── requirements.txt            # Required packages
|   ├── README.md                   # Documentation
|   ├── logs/                       # Logs directory for error, event logs, and audit trails
|   ├── tests/                      # Unit and integration tests
|   ├── modules/                    # Core logic for each step of the pipeline
|   └── ...
└── ...
```
## D\. Key Definitions
#### PyRIT
Microsoft PyRIT (Python Red-Teaming for Intrusion Techniques) is a Python package designed to facilitate red teaming and security testing of Large Language Models (LLMs). It provides a framework and tools to systematically probe LLMs for vulnerabilities, biases, and other undesirable behaviors.  PyRIT helps security professionals and researchers understand the risks associated with LLMs and develop strategies to mitigate them. Here's a breakdown of PyRIT's key aspects:
- **Dataset Integration:** PyRIT integrates with various datasets relevant to LLM security, such as those focusing on jailbreaking, bias detection, and harmful content.  It provides functions to easily fetch and load these datasets as `SeedPromptDataset` objects, making it easier to reproduce research findings or build upon existing work.
- **Structured Prompt Management:** PyRIT provides classes like `SeedPrompt` and `SeedPromptDataset` to manage and organize collections of prompts. This allows for systematic testing with diverse prompt variations and facilitates the creation of prompt libraries for different attack scenarios.  It also supports Jinja2 templating for dynamic prompt generation.
- **Prompt Orchestration:** PyRIT includes tools for orchestrating the sending of prompts to target LLMs. The `PromptSendingOrchestrator` allows you to send prompts in bulk, manage asynchronous requests, and collect responses. This streamlines the process of testing many prompts and analyzing the LLM's behavior. {{improve this}}
- **Target Abstraction:** PyRIT is designed to work with various LLM targets.  The `PromptTarget` class provides an abstraction layer, allowing you to easily switch between different LLM APIs or services (e.g., local endpoint, Azure OpenAI, OpenAI).
- **Extensibility:** PyRIT is designed to be extensible.  You can easily add new prompt targets, dataset loaders, or attack techniques to the framework.  This allows the tool to evolve as LLM technology and attack vectors change.
- **Emphasis on Reproducibility:** By providing a structured framework and integration with public datasets, PyRIT promotes reproducible research in the field of LLM security.
- **Utilities and Helpers:**  PyRIT also includes various utility functions for tasks like data serialization (YAML, JSON, CSV), text processing, and file management.
#### PyRIT Seed Prompt Class
The `SeedPrompt` class represents a single, potentially parameterized prompt that can be used to elicit responses from a language model.  It encapsulates the prompt text itself along with metadata and attributes that provide context and facilitate organization, analysis, and manipulation of the prompt. Key aspects of the `SeedPrompt` class include:
- **Prompt Text (`value`):** The actual text of the prompt intended for the language model.  This can be a static string or a Jinja2 template that allows for dynamic parameterization.
- **Unique Identifier (`id`):** A UUID assigned to each prompt instance, ensuring uniqueness and facilitating tracking.
- **Data Type (`data_type`):** Specifies the type of data contained in the prompt, such as "text", "image", or "audio". This helps in selecting appropriate processing and rendering methods.
- **Metadata:**  Various metadata fields provide context for the prompt:
  - `name`: A human-readable name for the prompt.
  - `dataset_name`: The name of the dataset this prompt belongs to.
  - `harm_categories`: A list of categories representing potential harms associated with the prompt (e.g., "toxicity," "bias").
  - `description`: A more detailed explanation of the prompt's purpose or content.
  - `authors`:  A list of the individuals or entities who created the prompt.
  - `groups`:  A list of groups the prompt belongs to.
  - `source`:  The origin of the prompt.
  - `date_added`: The date and time the prompt was added.
  - `added_by`:  The user or process that added the prompt.
  - `metadata`: A dictionary for storing any additional, custom metadata.
- **Parameters (`parameters`):** A list of parameter names used in the prompt template.
- **Prompt Grouping:** Fields for organizing prompts into related sets:
  - `prompt_group_id`: A UUID that groups related prompts together.
  - `prompt_group_alias`: A human-readable alias for the prompt group.
  - `sequence`: An integer representing the order of the prompt within a group. This is crucial for multi-part prompts.
- **SHA256 Hash (`value_sha256`):**  A hash of the prompt's value, useful for identifying duplicate prompts and ensuring data integrity.  This is calculated asynchronously after the prompt value is finalized.
- **Template Rendering:** The `render_template_value` method allows for dynamic substitution of parameters within the prompt text using Jinja2 templating.
- **YAML Serialization:** The class inherits from `YamlLoadable`, enabling easy serialization and deserialization of `SeedPrompt` objects to and from YAML files.
#### PyRIT Seed Prompt Dataset
The `SeedPromptDataset` class serves as a container for managing and organizing collections of `SeedPrompt` objects. It's designed to streamline the process of loading, processing, and utilizing multiple prompts, especially in scenarios like red teaming or dataset creation.  Here's a breakdown of its key features and purpose:
- **Prompt Storage (`prompts`):** The core of the `SeedPromptDataset` is a list of `SeedPrompt` objects. This allows you to group and manage multiple prompts together.  The prompts can be provided directly during initialization or loaded from various sources.
- **Dataset-Level Metadata:**  `SeedPromptDataset` can store metadata that applies to the entire collection of prompts, such as:
  - `data_type`: The predominant data type of the prompts in the dataset.
  - `name`: A descriptive name for the dataset.
  - `dataset_name`:  A more specific name, potentially referencing the original source.
  - `harm_categories`: A list of potential harm categories relevant to the dataset as a whole.
  - `description`: A detailed description of the dataset.
  - `authors`: The creators of the dataset.
  - `groups`: Groups the dataset belongs to.
  - `source`: The origin of the dataset.
  - `date_added`: The date the dataset was created.
  - `added_by`: The user or process that created the dataset.
- **Data Loading and Merging (`from_dict`):** The `from_dict` class method provides a convenient way to load prompt data from a dictionary.  Critically, it handles the merging of dataset-level defaults with individual prompt properties.  This ensures that common attributes (like `harm_categories` or `authors`) can be easily applied to all prompts in the dataset while still allowing individual prompts to override these defaults. This is particularly useful when loading data from YAML or JSON files.
- **Prompt Grouping and Organization:** While the dataset itself doesn't inherently group prompts, it facilitates the creation of `SeedPromptGroup` objects. The `group_seed_prompts_by_prompt_group_id` static method takes a list of `SeedPrompt` objects (likely from a `SeedPromptDataset`) and creates `SeedPromptGroup` instances based on the `prompt_group_id` attribute of each prompt. This is essential for scenarios where multiple prompts need to be sent together as a single request.
- **Flexibility in Prompt Creation:**  `SeedPromptDataset` can be initialized with lists of `SeedPrompt` objects or with dictionaries, which are then converted to `SeedPrompt` objects. This provides flexibility in how you create and populate your datasets.
- **Use in Orchestration:** `SeedPromptDataset` objects are often used in conjunction with orchestrators like `PromptSendingOrchestrator`.  The dataset provides a structured way to load and manage the prompts that will be sent to a target language model.
#### Prompt Targets
- A Prompt Target represents an endpoint where prompts are sent.  This is typically an AI model or application (e.g., a GPT-4 endpoint, a Llama model, or even a custom API). The primary purpose of a Prompt Target is to receive prompts and generate responses.  It's the core component that interacts with the AI system you're testing or using.  Prompt Targets abstract away the specifics of interacting with different AI models, allowing you to easily swap between them.  They also provide a standardized interface (`send_prompt_async`) for sending prompts.
- **Relationships with Other Components:**
  - Orchestrators use Prompt Targets as destinations for the prompts they generate or modify.  An orchestrator might apply transformations (via converters) and then send the resulting prompt to a specified Prompt Target.  The orchestrator handles the logic of *how* and *when* to send prompts, while the target handles the *where*.
  - Scorers often rely on Prompt Targets to evaluate the quality or safety of responses.  A scorer might send a prompt to a target and then analyze the target's response based on predefined criteria.
  - Converters can also use Prompt Targets. A converter might transform a prompt using an LLM (acting as a Prompt Target) to rephrase it, translate it, or apply other modifications.
  - It is a subclass of PromptTarget. These often require a `PromptChatTarget`, which implies you can modify a conversation history.
#### PyRIT Prompt Templating
PyRIT's prompt templating system, built on Jinja2, allows for the creation of dynamic and parameterized prompts.  This is a crucial feature for red teaming and systematic testing because it enables you to easily generate variations of a prompt without manually editing each one.  Here's a breakdown of how it works:
- **Variable Substitution:** You can define variables within your prompt template using double curly braces `{{ variable_name }}`.  When the template is rendered, these placeholders will be replaced with actual values that you provide.
- **Control Flow:** Jinja2 also supports control flow structures like `if` statements, `for` loops, and macros. This allows you to create more complex and conditional prompts.  For example, you could include certain text in a prompt only if a specific condition is met.
- **Template Rendering (`render_template_value`):** The `SeedPrompt` class provides the `render_template_value` method.  This method takes a dictionary of key-value pairs as input, where the keys correspond to the variable names in your template and the values are the data you want to substitute.  When you call `render_template_value`, Jinja2 processes the template and replaces the variables with the provided values, generating the final prompt text.
#### Converters
Converters in PyRIT are components that transform prompts *before* they are sent to a Prompt Target.  They act as pre-processors, modifying the prompt's content, format, or representation.
- **Purpose:**
  - **Encoding/Decoding:** Change the prompt's encoding (e.g., Base64, ROT13, Binary).
  - **Adding Context/Information:**  Inject additional data, prefixes, or instructions into the prompt.
  - **Perturbation:**  Introduce variations, noise, or adversarial modifications to test model robustness (e.g., character swaps, leetspeak, random capitalization).
  - **Format Conversion:** Transform the prompt into a different format (e.g., text to ASCII art, text to audio, text to PDF).
  - **Translation:** Translate the prompt to another language.
  - **Rephrasing/Variation:** Generate variations of the prompt using an LLM (e.g., for softer phrasing, tone changes).
  - **Multi-modal Conversion:** Handle inputs and outputs across different modalities, such as audio and images, besides text.
  - **Human in the Loop:** Insert a human review and editing opportunity.
- **Relationships with Other Components:**
  - **Orchestrators:** Converters are *typically* used within an Orchestrator. The orchestrator manages the overall flow, applying converters to prompts *before* sending them to the target.  Converters can be *chained* (stacked) within an orchestrator, allowing for complex transformations.
  - **Prompt Targets:** Converters are *independent* of specific Prompt Targets.  The same converter can be used with different targets.  The converter modifies the *input* to the target, not the target itself.
  - **Datasets (SeedPromptDataset):**  Converters operate on the `value` of `SeedPrompt` objects within a `SeedPromptDataset`.  They can also operate on string.
- **Encoding/Decoding Converters:**
  - `Base64Converter`: Encodes or decodes prompts using Base64.
  - `ROT13Converter`: Applies the ROT13 substitution cipher.
  - `BinaryConverter`: Converts text to its binary representation.
  - `AnsiAttackConverter`: Handles ANSI escape sequences, including unescaping, injecting control characters.
- **Text Perturbation Converters:**
  - `RandomCapitalLettersConverter`: Randomly capitalizes letters in the prompt.
  - `LeetspeakConverter`: Converts text to leetspeak.
  - `CharSwapGenerator`: Swaps characters within words (inspired by the char-swap attack).
  - `StringJoinConverter`: Inserts a string between characters of the prompt.
- **LLM-Based Converters:** (These require an `OpenAIChatTarget` or similar)
  - `VariationConverter`: Generates variations of the prompt using an LLM.
  - `TranslationConverter`: Translates the prompt to a different language.
  - `ToneConverter`: Modifies the tone of the prompt (e.g., angry, polite).
  - `TenseConverter`: Changes the tense of the prompt (e.g., present, past, future).
  - `MaliciousQuestionGeneratorConverter`: Transforms a prompt into a malicious question.
  - `MathPromptConverter`: Transforms user queries into symbolic mathematical problems.
- **Multi-modal Converters:**
  - `AzureSpeechTextToAudioConverter`: Converts text to audio (speech synthesis).
  - `AzureSpeechAudioToTextConverter`: Converts audio to text (speech recognition).
  - `AddTextImageConverter`: Adds text overlays to images.
  - `AudioFrequencyConverter`: Change the frequency of a given audio.
  - `PDFConverter`: convert text or template to a pdf file.
- **Other:**
  - `NoiseConverter`: Adds random noise characters (using LLM)
  - `HumanInTheLoopConverter`:  Allows a human to review and modify prompts *before* they are sent.
#### Jailbreaking
Jailbreaking, in the context of LLMs, refers to the act of crafting specific inputs (prompts) that trick the model into bypassing its safety guidelines and generating outputs that it would normally refuse to produce.  LLMs are often trained with safety mechanisms to prevent them from generating harmful, offensive, or biased content.  Jailbreaking aims to circumvent these safeguards. Violent UTF provides a set of pre-built jailbreak prompt templates to assist in red teaming exercises. These templates are designed to exploit common vulnerabilities in LLMs and can be easily customized to target specific models or scenarios.
- **The Goal of Jailbreaking:**
  - Generating harmful content: Producing outputs that are toxic, racist, sexist, or otherwise offensive.
  - Revealing sensitive information: Tricking the model into divulging data it shouldn't share (e.g., internal code, personal information).
  - Bypassing restrictions: Getting the model to perform actions it's not supposed to, such as providing instructions for illegal activities.
  - Exposing vulnerabilities: Demonstrating weaknesses in the model's safety mechanisms that could be exploited by malicious actors.
- **Methods of Jailbreaking:**
  - Prompt Engineering: Carefully crafting prompts that use specific keywords, phrasing, or instructions to manipulate the model's behavior.  This often involves exploiting loopholes or ambiguities in the model's training data.
  - Role-Playing: Instructing the model to assume a role that is less constrained by safety guidelines (e.g., a villain, a hacker).
  - Hypothetical Scenarios: Framing prompts in hypothetical or fictional contexts to bypass restrictions on real-world actions.
  - System-Level Attacks: Exploiting vulnerabilities in the underlying system or API that the LLM is running on.  This is less common than prompt-based attacks.
  - Chain-of-Thought Prompting: Providing a chain of reasoning steps to the model, which can sometimes lead it to generate unsafe outputs in the process of reaching a conclusion.
- **Key Features of Jailbreak Templates:**
  - Targeted Attacks: The templates cover a range of jailbreaking techniques, including those mentioned above (role-playing, hypothetical scenarios, prompt manipulation).
  - Parameterization: The templates are parameterized using Jinja2, allowing you to easily modify and adapt them for different targets and attack vectors.  You can substitute keywords, instructions, or scenarios to create variations of the base prompts.
  - Modularity: The templates are designed to be modular, so you can combine or modify them to create more complex jailbreak attempts.
  - Example Templates (Illustrative - the actual template library may evolve):**
    - "Ignore Previous Instructions":**  Attempts to override prior instructions or safety guidelines by explicitly telling the model to disregard them.
    - "Act as a...":**  Instructs the model to assume a role that is less constrained by safety rules.
    - "Hypothetical Scenario":**  Presents a fictional or hypothetical situation to bypass restrictions on real-world actions.
    - "Code Injection":**  Attempts to inject malicious code into the model's output.
- **Using Jailbreak Templates:**
  - You can use the `SeedPrompt` class in PyRIT to load and render these templates.  The `render_template_value` method allows you to substitute parameters and customize the prompts for your specific needs.  Then, you can use the `PromptSendingOrchestrator` to send these jailbreak prompts to your target LLM and analyze the responses.
- **Important Note:**  Jailbreaking LLMs is a complex and evolving field.  New techniques are constantly being developed, and LLM providers are working to improve their safety mechanisms.  The jailbreak templates provide a starting point for red teaming exercises, but they should not be considered an exhaustive or definitive set of attacks.  It's crucial to stay updated on the latest research and techniques in this area.
#### Scorer
The Scoring Engine is a component responsible for evaluating the responses generated by a Prompt Target.  Scorers assign a value (a "score") to a response based on predefined criteria.  This score can be a boolean (true/false), a float (representing a scale), or a category.
- **Purpose:**
  - **Detect Harmful Content:** Identify responses containing toxic language, hate speech, personally identifiable information (PII), or other undesirable content.
  - **Identify Jailbreaks/Prompt Injection:** Determine if a prompt successfully bypassed the target's intended safety mechanisms.
  - **Assess Response Quality:**  Evaluate aspects like truthfulness, helpfulness, or adherence to instructions (though this is less common than security-focused scoring).
  - **Automate Red Teaming:**  Provide feedback to Orchestrators, allowing them to iteratively refine prompts and improve attack success rates.
  - **Detect Refusal:** Classify if the response is a refusal
- **Relationships with Other Components:**
  - **Orchestrators:** Scorers are *most often* used within Orchestrators.  The orchestrator sends prompts to a target, receives responses, and then passes those responses to one or more scorers.  The scores can then influence the orchestrator's subsequent actions (e.g., stopping if a jailbreak is detected, or generating new prompts based on the score).  `PromptSendingOrchestrator` can automatically apply scorers.  `ScoringOrchestrator` is designed specifically for scoring existing prompts.
  - **Prompt Targets:** Scorers are generally *independent* of the specific Prompt Target.  The same scorer can be used to evaluate responses from different targets.  However, some scorers *may* themselves use a Prompt Target internally (e.g., `SelfAskLikertScorer` uses an LLM to perform the scoring).
  - **Prompt Converters:** Prompt Converters are used *before* a prompt is sent to a target.
- **True/False Scorers:**  Return a boolean value indicating whether a condition is met.
  - `SelfAskTrueFalseScorer`: Uses an LLM to answer a yes/no question about the response.  Highly flexible, as you define the question.
  - `LlamaGuardScorer`: Uses LlamaGuard to detect harmful prompts
  - `PromptShieldScorer`:  Uses the Azure Content Safety Prompt Shield feature to detect jailbreaks (specifically in the *prompt*, not the response). Returns `True` if a jailbreak is detected.
  - `SelfAskRefusalScorer`: Determine if a prompt has been refused, and also detect a blocked response
  - `HITLScorer` (Human-in-the-Loop):  Presents the response to a human for manual scoring (true/false).
- **Float Scale Scorers:**  Return a numerical score, usually normalized between 0.0 and 1.0.
  - `LlamaGuardFilterScorer`: Uses the LlamaGuard via an API to score text or images for various harm categories (Hate, Sexual, Violence, SelfHarm).  Returns a score for *each* category.
  - `AzureContentFilterScorer`: Uses the Azure Content Safety API to score text or images for various harm categories (Hate, Sexual, Violence, SelfHarm).  Returns a score for *each* category.
  - `SelfAskLikertScorer`: Uses an LLM to score the response on a Likert scale (e.g., 1-5) based on a user-defined question.
  - `InsecureCodeScorer`: Evaluates security vulnerabilities in a code snippet.
- **Classification Scorers:**  Return a category label.
  - `SelfAskCategoryScorer`: Uses an LLM to classify the response into one of several predefined categories (e.g., "harmful", "harmless").  This is essentially a specialized true/false scorer.
#### Orchestrator
An Orchestrator is the central component that coordinates the entire red teaming process or other prompt-sending tasks. It acts as the "conductor," managing the interaction between the Prompt Target, Datasets (prompts), Converters, and Scorers, effectively implementing a specific strategy or workflow.
- **Purpose:**
  - **Implement Attack Strategies:** Orchestrators encapsulate the logic for various attack techniques, including:
      - Single-turn prompt injections.
      - Multi-turn conversational attacks (e.g., PAIR, Crescendo).
      - Specialized attacks like Cross-domain Prompt Injection Attacks (XPIA) and Flip Attacks.
      - Simple prompt sending (for testing or data collection).
      - Scoring of existing prompts.
  - **Manage Prompt Flow:** Control how prompts are:
      - Selected from Datasets.
      - Modified by Converters.
      - Sent to the Prompt Target.
  - **Incorporate Scoring:** Utilize Scorers to:
      - Evaluate responses.
      - Guide the attack strategy (e.g., iterative refinement, stopping conditions).
  - **Handle Conversation History:**  For multi-turn attacks, orchestrators manage the conversation state, including:
      - Prepending system prompts.
      - Adding previous turns to the context.
  - **Coordinate Complex Attack:** Orchestrators can be used to set up complex red-teaming attacks.
- **Relationships with Other Components:**
  - **Prompt Targets:** Orchestrators *require* a Prompt Target. They use the target's `send_prompt_async` method to send prompts and receive responses. The orchestrator is the *primary user* of the target.
  - **Datasets (`SeedPromptDataset`):**  Orchestrators often retrieve their initial prompts (or objectives) from a `SeedPromptDataset`.
  - **Converters:** Orchestrators can use a *list* of Converters.  Converters are applied *in order* to each prompt *before* it's sent to the target.
  - **Scorers:** Orchestrators can use Scorers to evaluate responses. The scores can be used for:
      - Determining attack success.
      - Guiding iterative prompt refinement.
      - Filtering or selecting prompts.
- **Single-Turn Orchestrators:** (Process each prompt independently)
  - `PromptSendingOrchestrator`:
      - **Description:** The most fundamental orchestrator. Sends a list of prompts to a target (optionally applying converters) and collects the responses.  No conversation history is maintained.
      - **Use Cases:**  Testing a fixed set of prompts, encoding/decoding prompts, collecting baseline responses.
      - **Required Parameters:**
          - `objective_target`: The `PromptTarget` to send prompts to.
      - **Optional Parameters:**
          - `prompt_converters`:  A list of `PromptConverter` instances to apply.
          - `scorers`: For automatically scoring.
          - `batch_size`: Number of prompts sending together.
  - `RolePlayOrchestrator`:
      - **Description:** Prepends a role-playing scenario prompt (defined in a YAML file) before each user prompt. Can utilize an adversarial LLM to generate initial conversation turns.
      - **Use Cases:** Simulating specific conversational scenarios, testing how a model responds to different roles or personas.
      - **Required Parameters:**
           - `objective_target`: Target model
           - `adversarial_chat`: Adversarial LLM model
           - `role_play_definition_path`: Path to YAML.
      - **Optional Parameters:**
          - `scorers`
  - `FlipAttackOrchestrator`:
      - **Description:** Implements the Flip Attack, which involves sending a system prompt instructing the target to "unflip" the (flipped) malicious prompt.
      - **Use Cases:** Testing a model's vulnerability to the Flip Attack.
      - **Required Parameters:**
           - `objective_target`
      -  **Optional Parameters:**
          - `system_prompt`: The prompt to instruct target to "unflip" the attack.
  - `AdvBenchPromptSendingOrchestrator`:
      - **Description:** Send prompts from AdvBench dataset
      - **Required Parameters:**
           - `objective_target`
      -  **Optional Parameters:**
          - `prompt_converters`: prompt converters
          - `scorers`
- **Multi-Turn Orchestrators:** (Maintain and utilize conversation history)
  - `PAIROrchestrator`:
      - **Description:** Implements the Prompt Automatic Iterative Refinement (PAIR) attack.  Uses *two* LLMs: an "attacker" LLM to generate prompts and a "target" LLM to respond.  Iteratively refines prompts to elicit a desired response (defined by a prefix).
      - **Use Cases:**  Automated jailbreaking, finding vulnerabilities in conversational models.
      - **Required Parameters:**
          - `objective_target`: The target model being attacked.
          - `adversarial_chat`: The attacker LLM.
          - `scoring_target`: An LLM used for scoring (often the same as `adversarial_chat`).
          - `desired_response_prefix`: The string that indicates a successful jailbreak.
      - **Optional Parameters:**
          - `max_turns`:  Limit on the number of conversation turns.
          - Number of parallel conversation
  - `CrescendoOrchestrator`:
      - **Description:** Gradually increases the "harmfulness" of prompts over multiple turns, using an adversarial LLM to generate prompts.  Backtracks if the target refuses to respond.
      - **Use Cases:** Testing a model's ability to resist escalating harmful requests.
      - **Required Parameters:**
          - `objective_target`: The target model.
          - `adversarial_chat`:  An LLM used to generate increasingly harmful prompts.
          - `scoring_target`: An LLM used for scoring.
      - **Optional Parameters:**
          - `max_turns`:  Maximum number of conversation turns.
          - `max_backtracks`:  Maximum number of times to backtrack.
          - `prompt_converters`:
- **Specialized Orchestrators:**
  - `XPIATestOrchestrator`:
      - **Description:**  Specifically for Cross-domain Prompt Injection Attacks (XPIA).  Involves uploading content to a storage target (e.g., Azure Blob Storage) and then prompting a processing target to summarize or interact with that content.
      - **Use Cases:** Testing scenarios where an attacker can inject malicious instructions via uploaded files or other external data sources.
      - **Required Parameters:**
          - `attack_content`:  The malicious content to be injected (e.g., a jailbreak prompt).
          - `processing_prompt`:  The prompt template used by the *processing* target (e.g., "Summarize the following file: {{...}}").  This template often includes a placeholder for the injected content.
          - `processing_target`:  The target that processes the uploaded content (e.g., an LLM with a summarization plugin).
          - `attack_setup_target`: The target used for the initial setup (e.g., an `AzureBlobStorageTarget`).
          - `scorer`: Evaluate the attack
      - **Optional Parameters:**
           - `verbose`
  - `ScoringOrchestrator`:
      - **Description:**  Designed solely for *scoring* existing prompts and their responses (already stored in PyRIT's memory).  Does *not* send new prompts to a target.
      - **Use Cases:**  Evaluating the results of previous runs, comparing different scorers, analyzing a specific set of prompts/responses.
      - **Required Parameters:**
          - `scorer`
  - `QuestionAnsweringBenchmarkOrchestrator`:
      - **Description:** Evaluates a chat model against a question-answering dataset and a scorer.
      - **Use Cases:** Benchmarking a model's ability to answer questions correctly.
      -  **Required Parameters:**
          - `chat_model_under_evaluation`: The target model.
          - `scorer`: The scorer used, typically a `QuestionAnswerScorer`.
      - **Optional Parameters:**
          - `verbose`
#### Memory
Memory is a persistent storage mechanism for data generated during red teaming activities.  It's essentially a database that tracks interactions, results, and configurations.
- **Purpose:**
  - **Track Conversations:** Store the history of prompts sent to targets and the corresponding responses. This includes both original and converted (modified) prompts.
  - **Store Scores:**  Record the scores assigned to responses by scorers, along with any metadata (e.g., the scorer used, rationale, timestamps).
  - **Persist Data:**  Save data to disk (or a remote database) so that it's not lost when the PyRIT process ends.  This enables resuming sessions, analyzing results later, and sharing data between users.
  - **Manage Seed Prompts:** Store and retrieve datasets of seed prompts and prompt templates, along with associated metadata (harm categories, authors, etc.).
  - **Store Embeddings:** (Less central to the basic flow, but important) Store text embeddings generated by embedding models.
    * **Enable Complex Orchestrator:** Store conversation history for multi-turn orchestrator to use.
- **Relationships with Other Components:**
  - **Orchestrators:** Orchestrators *write* to memory after sending prompts and receiving responses.  They also *read* from memory (e.g., to retrieve conversation history for multi-turn attacks, or to access prompts from a `SeedPromptDataset`).
  - **Prompt Targets:** Targets automatically write prompt requests and responses to memory.
  - **Scorers:** Scorers *write* their scores to memory, linking them to the corresponding prompt and response.
  - **Converters:** Converter information is stored as part of prompt request in memory.
  - **Datasets:** Datasets are loaded *into* memory as `SeedPromptDataset` objects, and new datasets created by the user are stored *in* memory.
- **`IN_MEMORY` (In-Memory DuckDB):**
  - **Description:** Uses an *in-memory* DuckDB database.  Data is stored only in RAM and is *lost* when the Python process terminates.
  - **Pros:** Fastest option; no external dependencies.
  - **Cons:**  Not persistent.  Not suitable for sharing data or long-running operations.
    * **Use Case:** Suitable for quick, one-time use or initial set up, not suitable for persistent use.
- **`DUCK_DB` (Persistent DuckDB):**
  - **Description:** Uses a DuckDB database stored in a *local file*.  Data is persisted to disk.
  - **Pros:**  Simple to set up (no external database server required); reasonably fast; data persists between sessions.
  - **Cons:**  Not designed for concurrent access by multiple users (unless you manually manage file sharing and locking – *not recommended*).
    * **Use Case:** Suitable for single-user operations.
- **`AZURE_SQL` (Azure SQL Database):**
  - **Description:** Uses a remote Azure SQL Database instance.  Requires an Azure subscription and a configured database.
  - **Pros:**  Supports multiple concurrent users; highly scalable and reliable; suitable for team collaboration.
  - **Cons:**  Requires more setup; incurs Azure costs.
  - **Use Cases:** Suitable for collaborative team red-teaming, and large scale testings.

## E\. Program steps
- GUI: Program steps are displayed on the sidebar. User actions are saved to a YAML parameter file.
- CLI: Parameters are loaded from a pre-existing YAML parameter file.
- GUI: Each step has its own page.
- GUI: Some steps require prior steps to be completed.
- Consistent numbering (1, 2, 3...) for steps.
- Clear separation of GUI (display) and Backend (logic).
- Use st.session_state to store intermediate values.
- In each step where the user makes selections or inputs parameters, after updating st.session_state, also update the parameter file with the user's selections. This involves writing the updated configurations back to the YAML parameter file or keeping a representation in st.session_state that can be saved at the end.
### 1. The Welcome Page
- **Display in GUI:**
  - A heading: "Welcome to Violent UTF"
  - Brief Introduction: Provide a concise description of what Violent UTF is and its purpose.
  - Links to Documentation and Tutorials: Include hyperlinks to the relevant resources for users to learn more.
  - Load Previously Saved Parameter File:
    - If parameter files exist in the "parameters" folder, display a dropdown (st.selectbox) labeled "Load a Parameter File" with the list of available .yaml files.
    - Alternatively, provide a st.file_uploader for users to upload a parameter file from their local machine.
  "Start" Button: A button to proceed to the next step.
- **In CLI:**
  - The user will use the parameter --param or -p to be followed by the path to the parameter file. The file must already exist.
  - At program startup, mandatory parameters (e.g., –target / -t for file path) are validated immediately. If missing, the system will prompt the user (GUI) or exit with an intelligible error message (CLI).  
  - In CLI mode, in the absence of a specified parameter file (--param / -p), the system should either use a default template (provided in the parameters folder) or gracefully exit with a message instructing the user to supply one.  
- **Action:**
  - If a Parameter File is Selected or Uploaded:
      - Load the parameters into st.session_state using a YAML parser, e.g., yaml.safe_load().
      - Update st.session_state with the loaded parameters.
      - Handle errors if the file is not a valid YAML or has invalid content.
  - If No Parameter File is Provided:
      - Initialize st.session_state with default values or an empty dictionary.
  - Clicking the "Start" button proceeds to the next step - Configure Memory.
- **Backend:**
  - Parameter File Loading:
  ```python
  import yaml

  if 'parameter_file' in st.session_state:
      with open(st.session_state['parameter_file'], 'r') as f:
          params = yaml.safe_load(f)
          st.session_state.update(params)
  ```
- **Error Handling & Tests:**
  - Use try...except blocks to catch and display errors related to file loading or parsing.
  - Include parameter validation testing as part of automated tests to ensure that missing or partial parameters are handled gracefully.
### 2. Configure Memory
Unless a user has memory configuration saved in a parameter file, the user must reconfigure memory in each application load.
#### 2a. Initial Display
- **Display:**
    - A heading: "Configure Memory"
    - Help text: Explain the different memory options, highlighting the trade-offs (persistence, sharing, setup complexity). *Emphasize that IN_MEMORY data is not saved.*
    - `st.radio` (or `st.selectbox`) labeled "Memory Type":
        - Options: "In-Memory (DuckDB)", "Local File (DuckDB)", "Azure SQL Database"
- **Action:** User selects a memory type.
- **Backend:** Store the selected memory type in `st.session_state["memory_type"]`.
#### 2b. Configure Memory Parameters (Dynamic)
- **Display:** Dynamically show input fields based on `st.session_state["memory_type"]`.
    - **`IN_MEMORY`:** *No additional parameters needed*.  Clearly indicate that data will not be saved.
    - **`DUCK_DB`:**
        - `Database File Path` (text input, *optional*): Allow the user to specify the path to the DuckDB file.  Provide a sensible default (e.g., in a `duckdb` subdirectory in app_data/violentutf).  *Include a file browser button if possible.*
    - **`AZURE_SQL`:**
        - `Connection String` (text input, `type="password"`, *required*):  The full SQLAlchemy connection string for the Azure SQL Database.  *Provide a link to documentation on how to obtain this.*
        - `Storage Container URL` (text input, *required*):  The URL of the Azure Blob Storage container used for storing associated files.
          * `Use AAD auth` (checkbox): choose between AAD auth and key based auth.
          * `Storage Key`: required if key-based auth is used.
- **Action:** User fills in the parameters (if any).
- **Backend:** Store the parameters in `st.session_state`, e.g., `st.session_state["duckdb_path"]`, `st.session_state["azure_sql_connection_string"]`.
#### 2c. Initialize Memory
- **Display:** A "Initialize Memory" button.
- **Action:** User clicks the button.
- **Backend:**
  - Sample backend codes
      ```python
      from pyrit.common import initialize_pyrit, IN_MEMORY, DUCK_DB, AZURE_SQL

      memory_type = st.session_state["memory_type"]

      if memory_type == "In-Memory (DuckDB)":
          initialize_pyrit(memory_db_type=IN_MEMORY)
      elif memory_type == "Local File (DuckDB)":
          db_path = st.session_state.get("duckdb_path", "pyrit_data/pyrit.db") # Use default if not provided
          initialize_pyrit(memory_db_type=DUCK_DB, memory_instance_kwargs={"db_path": db_path})
      elif memory_type == "Azure SQL Database":
          # Get the user input data
          connection_string = st.session_state["azure_sql_connection_string"]
          container_url = st.session_state["azure_storage_container_url"]

          if st.session_state["use_aad_auth"] :
              initialize_pyrit(memory_db_type=AZURE_SQL, memory_instance_kwargs={"db_connection_string": connection_string, "blob_container_url": container_url})
          else:
              storage_key = st.session_state["azure_storage_key"]
              initialize_pyrit(memory_db_type=AZURE_SQL,
              memory_instance_kwargs={"db_connection_string": connection_string, "blob_container_url": container_url, "blob_container_sas_token": storage_key })
      st.success(f"Memory initialized with type: {memory_type}")
      ```
  - **Error Handling:** Use `try...except` blocks around the `initialize_pyrit` call.  Display user-friendly error messages with `st.error()` if initialization fails (e.g., invalid connection string).
#### 2d. Display Schema and Next Step
- Display a button "Display Schema" to show the database schema
- Display a "Next step" button to proceed to the next step - Set Prompt Target.
#### 2e. Implementation Notes
- **`initialize_pyrit`:**  This function is *essential*.  It sets up the global `CentralMemory` instance that all other PyRIT components will use.
- **Defaults:** Provide sensible default values for parameters where possible (e.g., the DuckDB file path).
* **UX:** Provide option to use environment variables, and provide instructions for it.
#### 2f. UX Considerations
- **Clear Explanations:**  Explain the different memory types and their implications clearly.
- **Error Handling:**  Provide informative error messages if initialization fails.
- **Confirmation:**  Display a success message after successful initialization.
### 3. Set Prompt Targets
#### 3a. Select Target Interaction Type (Fundamental Choice)
- **Display:** Two radio buttons (or a clear, mutually exclusive selection method):
  - **Single Prompt Target (`PromptTarget`)**: For sending individual, independent prompts. *Include help text:* "Suitable for scenarios without conversational context.  Works with most orchestrators."
  - **Conversational Chat Target (`PromptChatTarget`)**: For multi-turn dialogues where conversation history matters. *Include help text:* "Required for orchestrators like PAIR, TAP, and those involving conversation modification.  Manages system prompts and turn-taking."
- **Action:** User selects one of the two options.
- **Backend:**
  - Store the selected interaction type (`PromptTarget` or `PromptChatTarget`) in `st.session_state`.
  - Update the parameter file with user's selections
#### 3b. Select Target Provider/Technology
- **Display:** A dropdown/selectbox appears, dynamically populated based on the choice in Step 1a.
  - *If `PromptTarget` was selected:*
    - HTTP Target
    - Azure Blob Storage
    - Prompt Shield Target
    - Custom Target
    - Realtime Target (Audio)
  - *If `PromptChatTarget` was selected:*
    - OpenAI (Chat)
    - Azure OpenAI (Chat)
    - Hugging Face (Chat)
    - Groq (Chat)
    - Azure ML (Chat)
    - Playwright Target
    - Custom Target
- **Action:** User selects a provider/technology.
- **Backend:**
  - Store the selected provider/technology in `st.session_state`.
  - Update the parameter file with user's selections
#### 3c. Select Specific Model/Endpoint (Contextual Step)
- **Display:** This step is *conditional*, appearing only for certain providers:
  - OpenAI (Chat):  Dropdown with model choices (e.g., "gpt-4o", "gpt-4", "gpt-3.5-turbo").
  - Azure OpenAI (Chat): *Ideally*, a dropdown populated with pre-configured Azure ML endpoint names (requires backend integration or a config file).  Alternatively, a text input for the "Deployment Name".
  - Hugging Face (Chat):  Text input for the Hugging Face Model ID (e.g., "HuggingFaceTB/SmolLM-360M-Instruct").  Include a link to the Hugging Face Model Hub.
  - Azure ML (Chat): Potentially a list of deployment names
  - Groq (Chat): Text input for model name.
  - Other Targets: This step is *skipped*.  (HTTP, Azure Blob, Prompt Shield, Custom, Realtime, Playwright).
- **Action:** User selects a model or enters an endpoint/model ID.
- **Backend:**
  - Store the selected model/endpoint in `st.session_state`.
  - Update the parameter file with user's selections
#### 3d. Configure Target Parameters (Dynamic Form)
- **Display:** A form with input fields, *dynamically generated* based on the selections in Steps 2 and 3.
  - **Common Fields (Always Present):**
    - `Target Name` (text input):  A user-friendly name for this target.
    - `Description` (text area, optional):  For notes.
  - **Target-Specific Fields:**
    - **OpenAI (Chat):**
      - `API Key` (text input, `type="password"`)
      - `Model Name` (text input) - could default to gpt-3.5-turbo
      - `Max Tokens` (number input) - Default to a reasonable value, e.g., 2048.
      - `Temperature` (number input)
    - **Azure OpenAI (Chat):**
      - `API Key` (text input, `type="password"`)
      - `Endpoint` (text input):  The full endpoint URL.
      - `Deployment Name` (text input):  The deployment name.
      - `Use AAD Authentication` (checkbox).
      - `API Version` (text input, optional).  Provide a default.
      - `Max Tokens` (number input)
      - `Temperature` (number input)
    - **Hugging Face (Chat):**
      - `Model ID` (text input, pre-filled if entered in Step 3).
      - `Use CUDA` (checkbox).
          - `Max New Tokens` (number input):
          - `Tensor Format` (text input)
    - **Groq (Chat):**
      - `API Key` (text input, `type="password"`).
      -  `Model Name` (Text Input)
    - **Azure ML (Chat):**
      - `Endpoint URI` (text input).
      - `API Key` (text input, `type="password"`).
          - `Temperature`
          - Other parameters
    - **HTTP Target:**
      - `HTTP Request` (text area):  The *full* HTTP request, including headers and body, with a placeholder like `{PROMPT}`.  Provide a *clear example*.
      - `Prompt Regex` (text input, *optional*, clearly labeled "Advanced: For extracting the response").
      - `Callback Function` (code editor, *optional*, clearly labeled "Advanced: For custom response parsing").
    - **Azure Blob Storage:**
      - `Container URL` (text input).
    - **Prompt Shield Target**
      - `Endpoint` (text input).
      - `API Key` (text input, `type="password"`).
      - **Playwright Target:**
          - `URL` (text input)
      - `Interaction Function` (code editor): The *primary* input. Provide an example from the documentation.
    - **Custom Target:**
      - Link to documentation (`2_custom_targets.ipynb`).
      - "Pre-built Custom Target" selectbox, options for Gandalf and Crucible
      - Optionally, a basic code editor for a simple Python class definition.
    - **Realtime Target (Audio):**
      - *No configuration parameters needed*.  The UI should clearly indicate this.
- **Action:** User fills in the required parameters.
- **Backend:**
  - Store all parameters in `st.session_state`, associated with the target name.
  - Update the parameter file with user's selections
#### 3e. Save and Test:**
- **Display:**
  - "Save Configuration" button.
  - "Test Connection" button.
- **Action:**
  - "Save": Serializes the configuration (from `st.session_state`) to JSON and stores it using PyRIT `MemoryFactory`.
  - "Test Connection":  Uses PyRIT's `send_prompt_async` with a simple test prompt to verify the target is reachable.
* **Backend**
    - Use `pyrit.memory.memory_factory.MemoryFactory` to save configurations.
    - Update the parameter file with user's selections
#### 3f. Manage Existing Targets
- List existing targets
- Allow select and edit existing targe
#### 3g. Next step button
- Display a "Next step" button to proceed to "Configure Datasets".
### 4. Configure Datasets
This section of the application allows users to create or load `SeedPromptDataset` objects, which are the primary way PyRIT manages input prompts for red teaming. The user can create datasets from three sources: pre-built standard datasets, local files, or online resources. The process involves selecting a source, potentially configuring parameters or mapping data fields, and optionally applying a prompt template. The user experience is driven by a primary choice of dataset source, which then dictates the subsequent steps.
#### 4a. Initial Screen: Choose Dataset Source
- **Display:** Three mutually exclusive options (buttons or radio group are recommended for best UX):
  - Option 1: Use Standard Prompt Dataset (Emphasis on built-in, ready-to-use datasets)
  - Option 2: Upload Local Dataset File (For users with their own data files)
  - Option 3: Fetch from Online Dataset (For datasets hosted at a URL)
- **Action:** User selects *one* of these options.
- **Backend:**
  - Store the selected source type (e.g., `"standard"`, `"local"`, `"online"`) in `st.session_state["dataset_source"]`.  This key is crucial for controlling the subsequent UI flow.
  - Update the parameter file with the dataset_source value
#### 4b. Conditional Flows (Based on Source):**
- **4b.A Flow for "Use Standard Prompt Dataset"**
  - **4b.A.1 Select Standard Dataset:**
    - **Display:**
      - `st.selectbox` labeled "Select Standard Dataset".
      - Options (with concise descriptions):
        - "Seclist (Bias)"
        - "XStest (Exaggerated Safety)"
        - "Harm Bench"
        - "DecodingTrust Stereotypes"
        - "AdvBench"
        - "PKU-SafeRLHF"
        - "LAT Harmful"
        - "Forbidden Questions"
        -  "LibrAI do-not-answer"
        - "WMDP QA Cyber, Bio, and Chem"
      - *UX Consideration:*  Consider grouping these options (e.g., by harm category) or providing a search/filter if the list becomes very long.
    - **Action:** User selects a dataset.
    - **Backend:**
      - Store the selected dataset name (e.g., `"AdvBench"`) in `st.session_state["standard_dataset_name"]`.
      - Update the parameter file with the standard_dataset_name value
  - **4b.A.2 (Conditional) Dataset-Specific Parameters:**
    - **Display:** *Dynamically show input fields based on `st.session_state["standard_dataset_name"]`. Use `if` statements extensively.*
      - **Seclist (Bias):**
        - `st.selectbox` for "Country".
        - `st.selectbox` for "Region".
        - `st.selectbox` for "Nationality" (ideally, this would be linked to the "Country" selection).
        - `st.selectbox` for "Gender" ("male", "female", "non-binary").
        - `st.selectbox` for "Skin Color" ("white", "black", "brown", "yellow").
        - "Confirm Seclist Bias Parameter Selection" button.
      - **DecodingTrust Stereotypes:**
        - `st.multiselect` for "Stereotype Topics".
        - `st.multiselect` for "Target Groups".
        - `st.selectbox` for "Prompt Type" ("benign", "untargeted", "targeted").
        -  "Confirm DecodingTrust Parameter Selection" button
      - **PKU-SafeRLHF:**
        - `st.selectbox` for "Safe or Unsafe prompts" (options: "safe", "unsafe")
      - **Other Datasets:** If a dataset has *no* parameters, skip this sub-step.  *Document which datasets have parameters.*
    - **Action:** User provides parameter values (if any).
    - **Backend:**
      - Store parameters in `st.session_state`, e.g., `st.session_state["seclist_country"] = "USA"`.

    - **4b.A.3 Fetch and Display (Confirmation):**
      - **Display:**
        - A "Fetch Dataset" button.  This is the main action button for this flow.
        - *After Fetching (triggered by button click):*
          - Success message:  "Dataset loaded successfully! (X prompts)"
          - *Optional Preview:*  `st.dataframe(data, height=200)` to show the *first 5-10* prompts.  *Do not* show the entire dataset if it's large. Use `.head()` on the underlying data.
      - **Action:** User clicks "Fetch Dataset".
      - **Backend:**
        - Call the appropriate `fetch_..._dataset()` function from PyRIT (e.g., `fetch_adv_bench_dataset()`).
        - Pass any parameters from `st.session_state` to the fetch function.
        - Store the resulting `SeedPromptDataset` in `st.session_state["seed_prompt_dataset"]`.
        - Error Handling: Use `try...except` blocks around the fetch calls.  Display user-friendly error messages with `st.error()` if fetching fails.

  - **4b.B Flow for "Upload Local Dataset File"**

    - **4b.B.1 Upload File:**
      - **Display:**
        - `st.file_uploader` labeled "Upload Dataset File".
        - `accept_multiple_files=False`
        - `type=["csv", "tsv", "json", "yaml", "txt"]` (explicitly list supported types)
      - **Action:** User uploads a file.
      - **Backend:**
        - Store the uploaded file object in `st.session_state["uploaded_file"]`.
        - *Immediately* attempt to parse the file:
                    ```python
                    import pandas as pd
                    import json
                    import yaml

                    uploaded_file = st.session_state["uploaded_file"]
                    if uploaded_file:
                        try:
                            if uploaded_file.name.endswith(".csv"):
                                df = pd.read_csv(uploaded_file)
                            elif uploaded_file.name.endswith(".tsv"):
                                df = pd.read_csv(uploaded_file, sep='\t')
                            elif uploaded_file.name.endswith(".json"):
                                data = json.load(uploaded_file)
                                # Handle JSON appropriately (list of dicts, single dict, etc.)
                                df = pd.DataFrame(data)  # Simplest case, might need adjustment
                            elif uploaded_file.name.endswith((".yaml", ".yml")):
                                data = yaml.safe_load(uploaded_file)
                                # Handle YAML, often similar to JSON
                                df = pd.DataFrame(data)
                            elif uploaded_file.name.endswith(".txt"):
                                # Assume each line is a prompt
                                lines = uploaded_file.read().decode("utf-8").splitlines()
                                df = pd.DataFrame({"prompt": lines}) # Create single column
                            else:
                                st.error("Unsupported file type.")
                                df = None

                            if df is not None:
                                st.session_state["raw_dataset"] = df
                        except Exception as e:
                            st.error(f"Error parsing file: {e}")
                            st.session_state["raw_dataset"] = None

                    ```
        - Store the *parsed* data (e.g., as a Pandas DataFrame) in `st.session_state["raw_dataset"]`.

    - **4b.B.2 Dataset Preview and Mapping:**
      - **Display:**
        - *If parsing was successful:* `st.dataframe(st.session_state["raw_dataset"].head())`  (Show a preview).
        - Input fields (all clearly labeled):
          - `Dataset Name` (text input, *required*).
          - `Field for Prompt Content` (selectbox, *required*):  Populate options with column names from `st.session_state["raw_dataset"].columns`.
          - `Field for Harm Categories` (selectbox, *optional*): Same options as above.
          - `Field for Prompt Name` (selectbox, *optional*):  Same options, plus an extra option:  "Same as dataset name".
                  - `Field for Groups` (selectbox, *optional*)
          - `Author(s)` (text input, optional).
          - `Added by` (text input, *required*).
          - `Dataset Description` (text area, optional).
      - **Action:** User fills in the mapping fields.
      - **Backend:** Store the mappings in `st.session_state`, e.g., `st.session_state["prompt_content_field"] = "text"`.

    - **4b.B.3. Create and Save SeedPromptDataset**
          - Display: "Create and Save SeedPromptDataset" button.
          - Action: User click the button.
          - Backend:
              - Create SeedPromptDataset based on the mapping, and store it in PyRIT memory.
              - Example codes (assuming `df` is available from parsing):
                   ```python
                    from pyrit.models import SeedPrompt, SeedPromptDataset
                    prompts = []

                    for idx, row in st.session_state["raw_dataset"].iterrows():
                        prompt_value = row[st.session_state["prompt_content_field"]]
                        harm_categories = []
                        if st.session_state.get("harm_categories_field"): #check if it exists in session
                           harm_categories = row[st.session_state["harm_categories_field"]]
                           if isinstance(harm_categories, str): # handle comma seprated string
                              harm_categories = [s.strip() for s in harm_categories.split(",")]

                        prompt_name = st.session_state["dataset_name"]
                        if st.session_state.get("prompt_name_field") and st.session_state["prompt_name_field"] != "Same as dataset name":
                           prompt_name = row[st.session_state["prompt_name_field"]]

                        groups = []
                        if st.session_state.get("groups_field"):
                            groups = row[st.session_state["groups_field"]]
                            if isinstance(groups, str):
                                groups = [s.strip() for s in groups.split(",")]

                        prompts.append(SeedPrompt(
                            value=prompt_value,
                            data_type="text",  # Adjust as needed
                            harm_categories=harm_categories,
                            dataset_name=st.session_state["dataset_name"],
                            name=prompt_name,
                            description=st.session_state.get("dataset_description"), #use get() in case it is not provided
                            authors=st.session_state.get("authors", "").split(","),  # Split into list
                            groups=groups,
                            added_by=st.session_state["added_by"],
                        ))

                    dataset = SeedPromptDataset(prompts=prompts)
                    #save to PyRIT memory
                    memory.prompt_datasets.add_dataset(dataset=dataset)
                    st.session_state["seed_prompt_dataset"] = dataset
                    st.success("SeedPromptDataset created successfully!")

                   ```

  - **4b.C Flow for "Fetch from Online Dataset"**

    - **4b.C.1 Enter URL:**
      - **Display:**
        - `st.text_input` labeled "Dataset URL".
        - Instructions: "Enter the URL of a CSV, TSV, JSON, YAML, or TXT file."
      - **Action:** User enters the URL.
      - **Backend:** Store the URL in `st.session_state["dataset_url"]`.

    - **4b.C.2 Fetch and Preview:**
      - **Display:**
        - "Fetch Dataset" button.
        - *After Fetching:*
          - Success/error message (`st.success` or `st.error`).
          - Preview of the *raw* data (as in 2.2.B.2).
      - **Action:** User clicks "Fetch Dataset".
      - **Backend:**
                ```python
                import requests
                import pandas as pd
                import io
                import json
                import yaml

                try:
                    url = st.session_state["dataset_url"]
                    response = requests.get(url)
                    response.raise_for_status()  # Raise an exception for bad status codes

                    if url.endswith(".csv"):
                        df = pd.read_csv(io.StringIO(response.text))
                    elif url.endswith(".tsv"):
                        df = pd.read_csv(io.StringIO(response.text), sep='\t')
                    elif url.endswith(".json"):
                        data = json.loads(response.text)
                        df = pd.DataFrame(data)  # Adjust as needed
                    elif url.endswith((".yaml", ".yml")):
                        data = yaml.safe_load(io.StringIO(response.text))
                        df = pd.DataFrame(data)  # Adjust
                    elif url.endswith(".txt"):
                        lines = response.text.splitlines()
                        df = pd.DataFrame({"prompt": lines})
                    else:
                        st.error("Unsupported file type at URL.")
                        df = None

                    if df is not None:
                        st.session_state["raw_dataset"] = df

                except Exception as e:
                    st.error(f"Error fetching or parsing data: {e}")
                    st.session_state["raw_dataset"] = None

                ```

    - **4b.C.3 Dataset Mapping:** (Identical to 4b.B.2 - *extract this into a reusable function*)
    -  **4b.C.4. Create and Save SeedPromptDataset** (Identical to 4b.B.3)

- **4b.D (Optional) Prompt Templating (Applies to *all* sources):**

  - **Display:**  *After* a `SeedPromptDataset` has been created (from *any* of the above flows), show these buttons *in a single row*:
    - Button 1: "Select Existing Template"
    - Button 2: "Add New Template"
    - Button 3: "Skip Templating"

  - **Action:**  User clicks one of the buttons.

  - **Backend:**
    - Store the choice in `st.session_state["template_choice"]`. Possible values: `"existing"`, `"new"`, `"skip"`.

  - **"Select Existing Template" Flow:**
    - **Display:**
      - Two `st.expander` sections: "Regular Prompt Templates" and "Jailbreak Prompt Templates".
      - Inside each expander:
        - Note: "Please click on a template name to view and select it."
        - List template names (filenames without extensions, with "_" replaced by spaces).  This requires reading the contents of the `templates` and `templates/jailbreaks` directories.  *Do this reading once at the start of the app and store in `st.session_state`.*
        - Example (inside expander):
                    ```python
                    import os
                    import streamlit as st

                    def list_templates(directory):
                        template_files = [f for f in os.listdir(directory) if f.endswith(".yaml")]
                        template_names = [f.replace("_", " ").replace(".yaml", "") for f in template_files]
                        return template_names

                    # Do this ONCE at the top of your app, NOT inside the expander
                    if "template_names" not in st.session_state:
                        st.session_state["template_names"] = list_templates("/app_data/violentutf/templates") #or use DATASETS_PATH
                    if "jailbreak_names" not in st.session_state:
                        st.session_state["jailbreak_names"] = list_templates("/app_data/violentutf/templates/jailbreaks") #or use DATASETS_PATH

                    with st.expander("Regular Prompt Templates"):
                        st.write("Please click on a template name to view and select it.")
                        cols = st.columns(3) #create columns
                        for i, name in enumerate(st.session_state["template_names"]):
                            with cols[i % 3]: # cycle through columns
                               if st.button(name, key=f"template_{name}"):
                                    with open(os.path.join("/app_data/violentutf/templates", name.replace(" ", "_") + ".yaml")) as f:
                                       template_content = f.read()

                                    with st.dialog("Template Content"):
                                        st.code(template_content, language="yaml")
                                        if (st.button("Select this template")):
                                           st.session_state["selected_template_path"] = os.path.join("/app_data/violentutf/templates", name.replace(" ", "_") + ".yaml")
                                           st
                    ```
### 5. Configure Converters
#### 5a. Initial Display
- **Display:**
    - A heading: "Configure Converters (Optional)"
    - Help text explaining the purpose of converters and their role in the pipeline.  Mention chaining/stacking.
    - A "Add Converter" button.
- **Action:** User clicks "Add Converter".
- **Backend:**
  - If "selected_converters" not in st.session_state: st.session_state["selected_converters"] = [] Initialize the list only if it doesn't exist. This prevents overwriting existing converters.
  - st.session_state["current_converter_class"] = None Initialize to None
  - st.session_state["current_converter_params"] = {} Initialize to empty dict
#### 5b.  Add Converter Flow
This is a repeating flow, triggered by the "Add Converter" button
- **Select Converter Type:**
  - **Display:**
      - `st.selectbox` labeled "Select Converter Type".
      - Options:  Populate this *dynamically* from the available converter classes (see Implementation Notes below).  The options should be user-friendly names (e.g., "Base64 Encoder/Decoder", "Random Capitalization", "Text to Speech (Azure)", etc.).
  - **Action:** User selects a converter type.
  - **Backend:**
    - Store the selected converter *class* (not an instance) in `st.session_state["current_converter_class"]`.
    - Add target_labels dictionary
- **Configure Converter Parameters (Dynamic):**
  - **Display:** *Dynamically* show input fields based on `st.session_state["current_converter_class"]`.  Use extensive `if` statements.
    - **Base64Converter:**
        - Dropdown for "Mode" (Encode/Decode).
    - **RandomCapitalLettersConverter:**
        - `st.number_input` for "Percentage" (0-100).
    - **AzureSpeechTextToAudioConverter:**
        - `st.selectbox` for "Output Format" (e.g., "wav", "mp3").
        - Potentially options for voice selection (if the API supports it).
    - **AzureSpeechAudioToTextConverter:**
        - *No specific parameters*.
    - **AddTextImageConverter:**
        - `st.text_area` for "Text to Add".
        - other necessary parameters
    - **LLM-Based Converters (Variation, Translation, Tone, etc.):**
        - *Crucially*: A way to select an *already configured* `PromptTarget` to use as the "converter target".  This should be a dropdown listing the names of targets configured in Step 1.
        - Any converter-specific parameters (e.g., "Target Language" for `TranslationConverter`, "Tone" for `ToneConverter`).
    - **HumanInTheLoopConverter:**
          - A way to select *other* converters to be made available within the human review step. This could be a multi-select list of the *names* of previously added converters.
    - **AnsiAttackConverter:**
        - Checkboxes for `include_raw`, `include_escaped`, `include_tasks`, `include_repeats`, `include_unescape` and `incorporate_user_prompt`
    - **CharSwapGenerator:**
        - `max_iterations`
        - `word_swap_ratio`
    - **PDFConverter:**
        - `font_type`
        - `font_size`
        - `page_width`
        - `page_height`
        - other optional fields
  - **Action:** User fills in the converter's parameters.
  - **Backend:** Store the parameters in a dictionary: `st.session_state["current_converter_params"] = {...}`.
#### 5c. Add to Pipeline
  - **Display:**  An "Add Converter" button at the end of each add converter flow.
  - **Action:** User clicks "Add Converter".
  - **Backend:**
      - Instantiate the selected converter class using the parameters from `st.session_state["current_converter_params"]`.
      - Append the *converter instance* to `st.session_state["selected_converters"]`.
      - Clear `st.session_state["current_converter_class"]` and `st.session_state["current_converter_params"]`.
      - Update the parameter file with added converter object and its parameters.
#### 5d. Display Converter Pipeline
   - Show the converter names
   - Allow removing converters
   - Allow reordering the converters
   - Update the parameter file as need
#### 5e. Test Converters (optional)
  - **Display:** A "Test Converters" button.
  - **Action:** User clicks the button.
  - **Backend:**
      - Prompt the user for a sample input string.
      - Apply the converters in `st.session_state["selected_converters"]` *sequentially* to the input string.
      - Display the intermediate and final results.  This helps the user verify that the converters are working as expected.
      - Update the parameter "tested_converter" parameter in the converter object in the parameter file. The default value is None
#### 5f. Implementation Notes and Code Snippets
- **Dynamic Converter List:**
    ```python
    from pyrit.prompt_converter import (
        Base64Converter,
        ROT13Converter,
        RandomCapitalLettersConverter,
        # ... import ALL converter classes ...
    )
    import inspect

    # Create dictionary to map Class Name to Class
    converter_classes = {}
    for name, obj in inspect.getmembers(pyrit.prompt_converter):
        if inspect.isclass(obj) and issubclass(obj, pyrit.prompt_converter.PromptConverter) and obj != pyrit.prompt_converter.PromptConverter:
            converter_classes[obj.__name__]= obj

    #in the UI
    converter_type = st.selectbox("Select Converter Type", list(converter_classes.keys()))
    st.session_state["current_converter_class"] = converter_classes[converter_type]

    ```
- **Instantiating Converters:**
    ```python
    # Inside the "Add Converter" button's callback:
    converter_class = st.session_state["current_converter_class"]
    params = st.session_state["current_converter_params"]

    # Handle LLM-based converters requiring a target
    if issubclass(converter_class, pyrit.prompt_converter.prompt_converter_llm_base.PromptConverterLLMBase):
      # Get Available targets from memory
      targets = memory.prompt_targets.list_targets()
      target_labels = [f"{target.target_type}: {target.prompt_target_id}" for target in targets]
      selected_target_label = st.selectbox("Select Target", options=target_labels)

      # Get the selected target id
      target_id = selected_target_label.split(":")[-1].strip()
      converter_target = memory.prompt_targets.get_prompt_target_by_id(prompt_target_id=target_id)

      params["converter_target"] = converter_target # Pass target to construct

    converter_instance = converter_class(**params)
    st.session_state["selected_converters"].append(converter_instance)

    ```
* **Storing Configuration:** After a complete pipeline has been configured (prompt target, datasets, converters), the configuration will be stored in PyRIT memory using MemoryFactory.
- **Converter Ordering:**  If you implement drag-and-drop reordering, update `st.session_state["selected_converters"]` accordingly.
- **Error Handling:** Use try...except for converter instantiations, and sending prompts.
#### 5g. UX Considerations
- **Clear Labels and Help Text:**  Make sure all input fields are clearly labeled and have helpful descriptions.  Explain what each converter does.
- **Visual Feedback:**  Provide immediate feedback to the user (e.g., success messages, error messages, previews).
- **Progress Indication:** For long-running operations (like fetching datasets or applying LLM-based converters), use `st.spinner` or `st.progress` to show progress.
- **Modular Design:** Break down the UI into logical sections using expanders or tabs.
### 6. Configure the Scoring Engine
#### 6a. Initial Display
- **Display:**
    - A heading: "Configure Scoring Engine (Optional)"
    - Help text explaining the purpose of scorers, emphasizing their role in evaluating responses.
    - An "Add Scorer" button.
- **Action:** User clicks "Add Scorer".
- **Backend:** Initialize an empty list in `st.session_state`: `st.session_state["selected_scorers"] = []`.

#### 6.2 Add Scorer Flow
This is a repeating flow
- **Select Scorer Type:**
  - **Display:**
      - `st.selectbox` labeled "Select Scorer Type".
      - Options: Populate this *dynamically* from the available scorer classes (see Implementation Notes).  Use user-friendly names:
          - "Azure Content Safety (Text/Image)"
          - "Self-Ask (True/False)"
          - "Self-Ask (Likert Scale)"
          - "Self-Ask (Category)"
          - "Prompt Shield (Jailbreak Detection)"
          - "Human-in-the-Loop"
          - "Refusal Scorer"
          - "Insecure Code Scorer"
          - ... (add others as needed) {{improve this}}
  - **Action:** User selects a scorer type.
  - **Backend:** Store the selected scorer *class* in `st.session_state["current_scorer_class"]`.
-**Configure Scorer Parameters (Dynamic):**
  - **Display:** *Dynamically* show input fields based on `st.session_state["current_scorer_class"]`.
      - **AzureContentFilterScorer:**
          - `API Key` (text input, `type="password"`)
          - `Endpoint` (text input)
          - `Use AAD auth` (checkbox)
      - **SelfAskTrueFalseScorer:**
          - `True/False Question` (text area):  The question to ask the LLM.
          - `Chat Target` (selectbox):  Select from the *previously configured* Prompt Targets (from Step 1).  This is *crucial*.
      - **SelfAskLikertScorer:**
          - `Likert Scale Question` (text area).
          - `Chat Target` (selectbox): Select from configured Prompt Targets.
      - **SelfAskCategoryScorer:**
          - `Content Classifier`
          - `Chat Target` (selectbox)
      - **PromptShieldScorer:**
          - `Endpoint` (text input)
          - `API Key` (text input)
      - **HITLScorer:**
            - `Instructions` (text area, *optional*): Instructions for the human reviewer.
      - **Refusal Scorer**
          - `Chat Target` (selectbox)
      - **InsecureCodeScorer:**
          - `Chat Target` (selectbox):
          - `Threshold` (number input)
  - **Action:** User fills in the parameters.
  - **Backend:** Store parameters in a dictionary: `st.session_state["current_scorer_params"] = {...}`.
#### 6.3 Add to Pipeline:**
  - **Display:** An "Add Scorer" button at the end of each add scorer flow.
  - **Action:** User clicks "Add Scorer".
  - **Backend:**
      - Instantiate the selected scorer class using the parameters from `st.session_state["current_scorer_params"]`.
      - Append the *scorer instance* to `st.session_state["selected_scorers"]`.
      - Clear `st.session_state["current_scorer_class"]` and `st.session_state["current_scorer_params"]`.
      - Add a scorer object in the parameter file with the object parameter values.
      - *Optionally:* Display a visual representation of the added scorers (list, etc.). {{improve this}}
#### 6.4 Display Scorer Pipeline:**
   - Show the scorer names
   - Allow removing scorers
   - Allow reordering the scorers
#### 6.5 Implementation Notes and Code Snippets:**
- **Dynamic Scorer List:**
    ```python
    from pyrit.score import (
        AzureContentFilterScorer,
        SelfAskTrueFalseScorer,
        # ... import ALL scorer classes ...
    )
    import inspect

     # Create dictionary to map Class Name to Class
    scorer_classes = {}
    for name, obj in inspect.getmembers(pyrit.score):
        if inspect.isclass(obj) and issubclass(obj, pyrit.score.base_scorer.BaseScorer) and obj != pyrit.score.base_scorer.BaseScorer:
            scorer_classes[obj.__name__]= obj

    # In the UI
    scorer_type = st.selectbox("Select Scorer Type", list(scorer_classes.keys()))
    st.session_state["current_scorer_class"] = scorer_classes[scorer_type]
    ```
- **Instantiating Scorers:**
    ```python
    # Inside the "Add Scorer" button's callback:
    scorer_class = st.session_state["current_scorer_class"]
    params = st.session_state["current_scorer_params"]
    scorer_instance = scorer_class(**params)
    st.session_state["selected_scorers"].append(scorer_instance)
    ```
- **Storing Configuration:** After all scorers have been configured, you would retrieve them and include them when instantiating an `Orchestrator`. The list of configured scorers is available in `st.session_state["selected_scorers"]`.
- **Human-in-the-loop:** You can set up a button that allows user to manually enter the score of the response based on the current configuration.
#### 6.6 UX Considerations
- **Clear Explanations:** Provide clear descriptions for each scorer type and its parameters.  Links to the PyRIT documentation for each scorer would be *extremely* helpful.
- **Error Handling:**  Handle cases where required parameters are missing or invalid (e.g., invalid API key format).
- **Dependency:** If a scorer requires a target (e.g. SelfAskTrueFalseScorer), make sure it's clear to user.
### 7. Configure Orchestrators
#### 7a. Initial Display
- **Display:**
    - A heading: "Configure Orchestrator"
    - Help text:  "Select an orchestrator to define how PyRIT interacts with the target and other components.  Different orchestrators implement different attack strategies or workflows."
    - `st.selectbox` labeled "Select Orchestrator Type".  *Dynamically populate* the options (see Implementation Notes).  Use user-friendly names:
        - "Simple Prompt Sending" (`PromptSendingOrchestrator`)
        - "Role Playing" (`RolePlayOrchestrator`)
        - "Flip Attack" (`FlipAttackOrchestrator`)
        - "PAIR (Iterative Jailbreaking)" (`PAIROrchestrator`)
        - "Crescendo (Escalating Harm)" (`CrescendoOrchestrator`)
        - "Cross-domain Prompt Injection (XPIA)" (`XPIATestOrchestrator`)
        - "Scoring Existing Prompts" (`ScoringOrchestrator`)
        - "Question Answering Benchmark" (`QuestionAnsweringBenchmarkOrchestrator`)
        - "AdvBench Prompt Sending" (`AdvBenchPromptSendingOrchestrator`)
- **Action:** User selects an orchestrator type.
- **Backend:**
    - Store the selected orchestrator *class* in `st.session_state["current_orchestrator_class"]`.
    - Initialize an empty dictionary for parameter: `st.session_state["current_orchestrator_params"] = {}`
#### 7b. Configure Orchestrator Parameters (Dynamic Form)
- **Display:**  A form appears, with input fields *dynamically generated* based on `st.session_state["current_orchestrator_class"]`. Use extensive `if` statements and refer to the parameter lists in Section D Orchestrator.
  - **Always Display (for all orchestrators):**
    - `Orchestrator Name` (text input, required): A user-defined name for this configuration.
    - `Prompt Target` (selectbox, required):  Lists the *names* of targets configured in Step 1.  This is how the orchestrator knows *which* target to use.
    - `Prompt Converters` (multiselect, optional): Lists the *names* of converters configured in Step 3.
    - `Scorers` (multiselect, optional): Lists the *names* of scorers configured in Step 4.
  - **Conditional Display (Orchestrator-Specific):** Use nested `if` statements based on `st.session_state["current_orchestrator_class"]`.  Refer to Section 5.2 for the parameters of each orchestrator.  *Crucially*, use the correct Streamlit input widgets (`st.text_input`, `st.text_area`, `st.number_input`, `st.selectbox`, `st.multiselect`, etc.) for each parameter type.  Provide default values where appropriate.
- **Action:** User fills in the required and optional parameters.
- **Backend:** Store the parameter values in `st.session_state["current_orchestrator_params"]`.  *Important:* Store the *names* (or IDs) of the selected target, converters, and scorers, *not* the objects themselves.  We'll retrieve the objects later.
#### 7c. Create and Store Orchestrator
- **Display:** A "Create Orchestrator" button.
- **Action:** User clicks the button.
- **Backend:**
      ```python
      import pyrit.orchestrator
      from pyrit.orchestrator import (
          PromptSendingOrchestrator,
          PAIROrchestrator,
          CrescendoOrchestrator,
          XPIATestOrchestrator,
          ScoringOrchestrator,
          RolePlayOrchestrator,
          FlipAttackOrchestrator
          QuestionAnsweringBenchmarkOrchestrator
          AdvBenchPromptSendingOrchestrator
      )
      import inspect

      orchestrator_classes = {}
      for name, obj in inspect.getmembers(pyrit.orchestrator):
          if inspect.isclass(obj) and issubclass(obj, pyrit.orchestrator.base_orchestrator.BaseOrchestrator) and obj != pyrit.orchestrator.base_orchestrator.BaseOrchestrator:
              orchestrator_classes[obj.__name__]= obj


      # Inside the button's callback:
      orchestrator_class = st.session_state["current_orchestrator_class"]
      params = st.session_state["current_orchestrator_params"]

      --- Retrieve the *objects* from their names (or IDs) ---

      # 1. Target
      target_name = params.pop("Prompt Target") # Get and remove from dict
      target = None
      for t in memory.prompt_targets.list_targets():
          if t.prompt_target_id == target_name:  # Assuming you use names as identifiers
              target = t
              break
      if not target:
          st.error(f"Error: Target '{target_name}' not found.")
          return  # Stop execution

      params["objective_target"] = target


      # 2. Converters (if any)
      selected_converter_names = params.pop("Prompt Converters", [])  # Get and remove, default to empty list
      converters = []
      for conv_instance in st.session_state["selected_converters"]:
          if conv_instance.__class__.__name__ in selected_converter_names: # compare by class name
              converters.append(conv_instance)
      params["prompt_converters"] = converters

      # 3. Scorers (if any)
      selected_scorer_names = params.pop("Scorers", [])
      scorers = []
      for scorer_instance in st.session_state["selected_scorers"]:
          if scorer_instance.__class__.__name__ in selected_scorer_names: #compare by class name
              scorers.append(scorer_instance)
      params["scorers"] = scorers

      --- Special Handling for specific orchestrators
      if orchestrator_class == PAIROrchestrator:
          # Need to retrieve the adversarial_chat and scoring_target
          adv_chat_name = params.pop("Adversarial Chat Target")
          adv_chat_target = None
          for t in memory.prompt_targets.list_targets():
              if t.prompt_target_id == adv_chat_name:
                  adv_chat_target = t
                  break
          if not adv_chat_target:
              st.error("Adversarial Chat Target Not Found")
              return
          params["adversarial_chat"] = adv_chat_target

          scoring_target_name = params.pop("Scoring Target")
          scoring_target = None
          for t in memory.prompt_targets.list_targets():
            if t.prompt_target_id == scoring_target_name:
              scoring_target = t
              break
          if not scoring_target:
            st.error("Scoring Target Not Found")
            return
          params["scoring_target"] = scoring_target

      elif orchestrator_class == CrescendoOrchestrator:
            # Need to retrieve the adversarial_chat
          adv_chat_name = params.pop("Adversarial Chat Target")
          adv_chat_target = None
          for t in memory.prompt_targets.list_targets():
            if t.prompt_target_id == adv_chat_name:
              adv_chat_target = t
              break
          if not adv_chat_target:
              st.error("Adversarial Chat Target Not Found")
              return
          params["adversarial_chat"] = adv_chat_target

          scoring_target_name = params.pop("Scoring Target")
          scoring_target = None
          for t in memory.prompt_targets.list_targets():
            if t.prompt_target_id == scoring_target_name:
              scoring_target = t
              break
          if not scoring_target:
            st.error("Scoring Target Not Found")
            return
          params["scoring_target"] = scoring_target
      elif orchestrator_class == XPIATestOrchestrator:
          attack_setup_target_name = params.pop("Attack Setup Target")
          attack_setup_target = None
          for t in memory.prompt_targets.list_targets():
              if t.prompt_target_id == attack_setup_target_name:
                  attack_setup_target = t
                  break

          if not attack_setup_target:
              st.error("Attack Setup Target Not Found")
              return
          params["attack_setup_target"] = attack_setup_target

          process_target
      ```

### 8. Reporting
**I. Recommended Tools and Technologies**

Given the need for professionalism, interactivity, analysis, and exportability, I recommend the following toolchain:

1.  **Data Extraction and Transformation (Python with Pandas):**

      * PyRIT's `CentralMemory` (or your configured memory type) will be the source of your data.  You'll use Python and the `pyrit.memory` API to extract the relevant data: prompts, responses, scores, metadata, conversation IDs, etc.
      * Pandas DataFrames will be your primary data structure for manipulation and analysis.  Pandas is excellent for:
          * Filtering data (e.g., selecting only prompts with a specific label).
          * Grouping data (e.g., calculating average scores per harm category).
          * Joining data (e.g., combining prompt text with scores).
          * Transforming data (e.g., converting score strings to floats, extracting data from JSON metadata).
          * Preparing data for visualization.

2.  **Interactive Visualization (Plotly, potentially with Streamlit):**

      * **Plotly:**  Plotly is an excellent choice for creating interactive charts and dashboards.  It supports a wide range of chart types (bar, line, scatter, histograms, heatmaps, etc.), and the interactivity (zooming, panning, hovering for details) is crucial for exploring red teaming results.  Plotly figures can be easily embedded in HTML reports.

      * **Streamlit (Optional, but Recommended):**  Since your primary application is already in Streamlit, you *could* integrate the report generation directly into the same app. This offers several advantages:

          * **Unified Experience:**  Users don't have to switch tools.
          * **Direct Data Access:**  You can directly access the `st.session_state` and PyRIT memory, simplifying data retrieval.
          * **Interactive Filtering:**  You can easily add interactive filters (dropdowns, sliders, etc.) to the report *within* Streamlit, allowing users to dynamically explore the data.
          * **No need to re-run**: Report can be generated from previous steps.

      * If you choose *not* to use Streamlit for the final report (e.g., if you need more advanced layout control), you can still use Plotly to generate the individual charts and save them as HTML snippets or images.

3.  **Report Generation (Jinja2, Markdown, and potentially WeasyPrint/wkhtmltopdf):**

      * **Jinja2:**  Use Jinja2 templating to create a structured HTML report.  This allows you to:
          * Define a reusable report template.
          * Dynamically insert text, tables (from Pandas), and charts (from Plotly) into the template.
          * Control the report's layout and styling.
      * **Markdown:**  You could generate a Markdown report, which is easy to read and can be converted to other formats.  However, embedding interactive Plotly charts directly into Markdown is less straightforward (you'd likely need to save them as separate HTML files and link to them).  HTML is a better choice for full interactivity.
      * **WeasyPrint or wkhtmltopdf (for PDF Export):** If you need PDF output, WeasyPrint (Python library) and wkhtmltopdf (command-line tool) are good options for converting HTML to PDF.  WeasyPrint is generally easier to integrate directly into a Python workflow.  These tools preserve the visual layout of the HTML report.
          * **Install WeasyPrint**: `pip install weasyprint`
          * **Install wkhtmltopdf**: follow instruction at [https://wkhtmltopdf.org/downloads.html](https://www.google.com/url?sa=E&source=gmail&q=https://wkhtmltopdf.org/downloads.html)
      * **Microsoft Word (Optional):** Exporting directly to a fully formatted Word document is more challenging.  The best approach is usually to:
        1.  Generate a well-structured HTML report.
        2.  Open the HTML report in Word.
        3.  Save as .docx, manually adjusting formatting as needed.

**II. Report Structure and Content (with a Red/Blue Team Focus)**

A well-structured report is essential for conveying the findings effectively. Here's a recommended structure, with specific content suggestions for each section:

1.  **Executive Summary:**

      * **Purpose:**  Provide a high-level overview of the red teaming exercise, its objectives, and key findings.  This section should be understandable by non-technical stakeholders.
      * **Content:**
          * Brief description of the target system (LLM, application).
          * Red teaming objectives (e.g., "Identify vulnerabilities to prompt injection," "Assess the model's adherence to safety guidelines").
          * Summary of key findings (e.g., "The model was successfully jailbroken in X% of attempts," "The model exhibited bias towards Y," "The Z safety mechanism was bypassed using technique A").
          * High-level recommendations (e.g., "Improve prompt filtering," "Retrain the model with a more diverse dataset").
      * **Visualization:** A few key summary statistics (e.g., overall success rate of attacks) as simple bar charts or numbers.

2.  **Methodology:**

      * **Purpose:** Describe the approach taken, the tools used, and the configuration.  This ensures reproducibility.
      * **Content:**
          * **PyRIT Version:** Specify the version of PyRIT used.
          * **Target System Details:**  Full details of the target (model name, version, API endpoint, any relevant configuration settings).
          * **Orchestrator Configuration:** Which orchestrator was used, and its parameters (e.g., `max_turns` for `CrescendoOrchestrator`).
          * **Dataset Description:**  Name and source of the dataset(s) used.  If a standard dataset was used, include the selection criteria (e.g., "AdvBench, harmful behaviors").  If a custom dataset was used, describe its creation and content.
          * **Converter Configuration:**  List any converters used and their settings.
          * **Scorer Configuration:** List the scorers used and their parameters (e.g., the `true_false_question` for `SelfAskTrueFalseScorer`, the API endpoint for `AzureContentFilterScorer`).
          * **Memory Configuration:** Specify the memory type used (In-Memory, DuckDB, Azure SQL) and any relevant connection details.
          * **Reproducibility:** State that the parameter file used is included in the attachment.

3.  **Detailed Results:**

      * **Purpose:** Present the full results of the red teaming exercise, organized in a clear and informative way.
      * **Content:** This section should be heavily driven by visualizations and tables.  Organize results by:
          * **Harm Category:** (If applicable)  Show results for each harm category tested (e.g., "Toxicity," "Hate Speech," "PII Disclosure").
          * **Attack Technique:** (If applicable)  Group results by the type of attack used (e.g., "Prompt Injection," "Role Playing," "Code Injection").
          * **Orchestrator:** If multiple orchestrators were used, separate the results.
          * **Prompt Converter:** if multiple prompt converters were used.
      * **Visualizations (use Plotly for interactivity):**
          * **Success Rate Bar Chart:**  Show the percentage of successful attacks (however you define "success") for each category/technique.
          * **Score Distribution Histograms:** For float-scale scorers, show the distribution of scores.  This helps understand the *severity* of the issues, not just the success rate.
          * **Scatter Plots:**  If you have multiple scores (e.g., from different scorers), a scatter plot can reveal correlations.  For example, plot "Toxicity Score" vs. "PII Disclosure Score."
          * **Tables:**  Include tables showing:
              * Prompt text (or a representative sample if there are many).
              * Response text (with potentially harmful content highlighted – *be very careful with this*).
              * Scores from each scorer.
              * Conversation ID (for multi-turn interactions).
              * Any relevant metadata (e.g., template parameters used).
          * **Interactive Filtering:** If using Streamlit, allow users to filter the results by harm category, attack technique, score range, etc.

4.  **Analysis and Discussion:**

      * **Purpose:** Interpret the results, draw conclusions, and identify patterns. This is where you move beyond just presenting data.
      * **Content:**
          * **Vulnerability Analysis:**  Discuss the specific vulnerabilities discovered.  For example:
              * "The model was consistently vulnerable to prompt injection attacks using the 'DAN' jailbreak technique."
              * "The model exhibited a bias towards generating toxic content when prompted with stereotypes about group X."
              * "The model failed to detect and filter PII in Y% of cases."
          * **Root Cause Analysis (as far as possible):**  Speculate on *why* the vulnerabilities exist.  This might involve discussing the model's training data, architecture, or safety mechanisms.
          * **Comparison to Baselines (if available):**  Compare the results to any available baselines (e.g., previous red teaming results, performance of other models).
          * **Limitations:** Acknowledge any limitations of the red teaming exercise (e.g., limited dataset size, specific attack techniques used).

5.  **Recommendations (Actionable Intelligence):**

      * **Purpose:**  Provide concrete, actionable recommendations for mitigating the identified vulnerabilities.  This is the most important part for the "blue team."
      * **Content:**
          * **Prioritize Recommendations:**  Rank recommendations based on the severity and likelihood of the vulnerabilities.
          * **Specific Mitigation Strategies:**  Suggest specific changes to the model, training data, prompt engineering, or deployment environment. Examples:
              * "Improve prompt filtering to detect and block common jailbreak phrases."
              * "Fine-tune the model on a dataset that includes counter-examples to the observed biases."
              * "Implement a PII detection and redaction system."
              * "Add a 'refusal' classifier to identify cases where the model should refuse to respond."
              * "Increase the temperature setting to reduce the likelihood of deterministic responses."
              * "Implement a system prompt to clearly define the persona and guardrails"
          * **Technical Feasibility:**  Consider the technical feasibility of implementing each recommendation.
          * **Trade-offs:**  Acknowledge any potential trade-offs between security and other factors (e.g., performance, usability).

6.  **Appendix (Optional):**

      * **Full Prompt List:** Include a complete list of all prompts used (if it's not too large).
      * **Raw Data:**  Provide a link to the raw data (e.g., the exported PyRIT memory database) for further analysis.
      * **Configuration Files:** Include the PyRIT configuration files (YAML) used for the red teaming exercise.

**III. Implementation Strategy (Step-by-Step)**

1.  **Data Extraction (Python/Pandas):**

      * Use `memory.get_prompt_request_pieces()` and `memory.get_scores()` to retrieve the data.  You can filter by conversation ID, labels, timestamps, etc.

      * Convert the data into Pandas DataFrames.  This will likely involve some data wrangling, especially for extracting data from the `prompt_metadata` and `score_metadata` fields (which are often JSON strings).

      * Example:

        ```python
        import pandas as pd
        from pyrit.memory import CentralMemory
        import json

        memory = CentralMemory.get_memory_instance()

        # Get all prompt request pieces and their associated scores
        prompt_pieces = memory.get_all_prompt_request_pieces()
        scores = memory.get_all_scores()

        # Convert to DataFrames
        prompts_df = pd.DataFrame([p.__dict__ for p in prompt_pieces])
        scores_df = pd.DataFrame([s.__dict__ for s in scores])

        # Merge the dataframes
        df = pd.merge(prompts_df, scores_df, left_on='id', right_on='prompt_request_response_id', how='left')
        # Clean up the dataframe, e.g. convert string to json
        df.score_metadata = df.score_metadata.apply(lambda x: json.loads(x) if isinstance(x, str) else x)
        df.prompt_metadata = df.prompt_metadata.apply(lambda x: json.loads(x) if isinstance(x, str) else x)

        # Example of data wrangling and filtering
        df["score_value"] = pd.to_numeric(df["score_value"], errors="coerce")  # Convert to numeric, handle errors

        # Filter for a specific scorer:
        df_filtered = df[df["scorer_class_identifier"] == "AzureContentFilterScorer"]

        # Extract nested data (example)
        # df["hate_score"] = df["score_metadata"].apply(lambda x: x.get("azure_severity") if isinstance(x, dict) else None)

        # Now df_filtered contains the data you need for your report.
        ```

2.  **Visualization (Plotly):**

      * Create Plotly figures (charts) based on the processed DataFrame.

      * Example (bar chart of success rates):

        ```python
        import plotly.express as px

        # Assuming you have a 'success' column (boolean) after scoring
        success_rates = df.groupby("harm_category")["success"].mean().reset_index()
        fig = px.bar(success_rates, x="harm_category", y="success", title="Attack Success Rate by Harm Category")
        fig.update_yaxes(range=[0, 1])  # Set y-axis to 0-1 (percentage)
        # fig.show() # if you want to display it here
        # you can save it as html
        fig.write_html("success_rate_chart.html")
        ```

      * Save each figure as an HTML file (using `fig.write_html()`).

3.  **Report Template (Jinja2):**

      * Create an HTML template (`report_template.html`) with placeholders for the content.  Example:

        ```html
        <!DOCTYPE html>
        <html>
        <head>
            <title>PyRIT Red Teaming Report</title>
            <style>
                /* Add your CSS styling here */
                body { font-family: sans-serif; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid black; padding: 8px; text-align: left; }
            </style>
        </head>
        <body>
            <h1>Red Teaming Report</h1>

            <h2>Executive Summary</h2>
            <p>{{ executive_summary }}</p>

            <h2>Methodology</h2>
            <p>{{ methodology }}</p>

            <h2>Detailed Results</h2>
            <h3>Success Rate by Harm Category</h3>
            <div>
              {{ success_rate_chart | safe }}
            </div>

            <h3>Example Prompts and Responses</h3>
             <div>
                {{ table_html | safe }}
            </div>

            <h2>Analysis</h2>
            <p>{{ analysis }}</p>

            <h2>Recommendations</h2>
            <p>{{ recommendations }}</p>

        </body>
        </html>

        ```

4.  **Report Generation (Python):**

      * Load the Jinja2 template.
      * Render the template, passing in the extracted data and Plotly HTML snippets.
      * Save the rendered HTML to a file.
      * *(Optional)* Convert the HTML to PDF using WeasyPrint.

    <!-- end list -->

    ```python
    import jinja2
    from weasyprint import HTML

    # --- (Previous steps: Data Extraction, Visualization) ---

    # --- Report Generation ---

    template_loader = jinja2.FileSystemLoader(searchpath="./")  # Assuming template is in the current directory
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("report_template.html")


    # Prepare data for the template
    report_data = {
        "executive_summary": "The LLM was vulnerable to prompt injection...",  # Fill in
        "methodology": "We used PyRIT with the following configuration...",      # Fill in
        "success_rate_chart": open("success_rate_chart.html").read(),        # Embed Plotly chart
        "table_html": df_filtered.to_html(),       # Example,  you need to use the dataframe you need
        "analysis": "Analysis of the results...",                            # Fill in
        "recommendations": "Recommendations for mitigation...",              # Fill in
    }

    # Render the template
    html_out = template.render(report_data)

    # Save the HTML report
    with open("red_teaming_report.html", "w", encoding="utf-8") as f:
        f.write(html_out)

    # (Optional) Convert to PDF using WeasyPrint
    HTML("red_teaming_report.html").write_pdf("red_teaming_report.pdf")

    print("Report generated: red_teaming_report.html (and optionally red_teaming_report.pdf)")

    ```

5.  **Report Generation (Streamlit)**

      * Alternatively, you can define a Streamlit page to display the report.
        ```python
           # Configure the page as wide layout
           st.set_page_config(layout="wide")

           st.title("Red Teaming Report")

           st.header("Executive Summary")

           st.header("Methodology")

           st.header("Detailed Results")

           st.plotly_chart(success_rate_fig) #success rate plot

           st.dataframe(
        ```