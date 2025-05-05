
Garak is a Python framework designed to assess the security and behavior of language models (LLMs) by generating adversarial prompts and analyzing their responses. While it's commonly used via the command line, Garak can also be integrated into Python scripts or Jupyter notebooks, allowing for programmatic control and customization.

This guide will walk you through setting up and running a Garak pipeline in a Jupyter notebook, focusing on both REST and OpenAI endpoints. We'll cover the following:

1. **Dependencies and Setup**
2. **Understanding Garak's Core Components**
3. **Instantiating Generators for REST and OpenAI**
4. **Loading and Configuring Probes**
5. **Running Probes and Collecting Attempts**
6. **Applying Detectors to Analyze Responses**
7. **Evaluating and Reporting Results**

---

## 1. Dependencies and Setup

### Python Libraries

- **Python 3.7 or higher**: Garak requires Python 3.7+ for compatibility.
- **Garak**: Install via pip.
- **Additional Libraries** (as needed for specific generators or probes):
  - `requests`: For HTTP requests (used by REST generators).
  - `openai`: OpenAI's library if interacting with OpenAI endpoints.
  - **Environment Variables**: For API keys and tokens.

### Installation

Install Garak using pip:

```bash
pip install garak
```

Ensure you have the necessary API keys set up as environment variables:

- **OpenAI API Key**: Set `OPENAI_API_KEY`.
- **REST API Key** (if required by your REST endpoint): Customize as needed.

---

## 2. Understanding Garak's Core Components

Before diving into code, it's essential to understand Garak's main components:

- **Generators**: Interfaces to LLMs or dialogue systems (e.g., OpenAI's GPT-3, REST APIs). They take prompts and return generated text.
- **Probes**: Define adversarial prompts designed to elicit specific behaviors or vulnerabilities from the model.
- **Attempts**: Represent a single interaction between a probe and a generator, including the prompt and the model's response.
- **Detectors**: Analyze the responses in attempts to identify specific failure modes or unwanted content.
- **Evaluators**: Assess the outcomes based on detectors and produce pass/fail results.

---

## 3. Instantiating Generators for REST and OpenAI

### OpenAI Generator

The `OpenAIGenerator` class interacts with OpenAI's API.

```python
from garak.generators.openai import OpenAIGenerator

# Initialize the OpenAI generator
openai_generator = OpenAIGenerator(
    name='gpt-3.5-turbo',  # Model name
)
```

**Dependencies**:

- **Environment Variable**: `OPENAI_API_KEY` must be set.
- **openai** Python package (installed automatically with Garak).

**Class Description**:

- **`OpenAIGenerator`**: A generator for OpenAI's GPT models. It handles authentication, sending prompts, and receiving responses.

### REST Generator

The `RestGenerator` class interfaces with custom REST endpoints.

```python
from garak.generators.rest import RestGenerator

# Configuration for the REST endpoint
rest_generator_config = {
    'uri': 'https://your-api-endpoint.com/generate',
    'method': 'post',  # HTTP method
    'headers': {
        'Authorization': 'Bearer YOUR_REST_API_KEY',
        'Content-Type': 'application/json',
    },
    'req_template_json_object': {
        'prompt': '$INPUT',  # Placeholder for the prompt
    },
    'response_json': True,
    'response_json_field': 'generated_text',
}

# Initialize the REST generator
rest_generator = RestGenerator(
    uri=rest_generator_config['uri'],
    name='Custom REST Generator',
)
# Update the generator's configuration
for key, value in rest_generator_config.items():
    setattr(rest_generator, key, value)
```

**Dependencies**:

- **requests** library.
- REST API specifications (e.g., authentication method, request/response format).

**Class Description**:

- **`RestGenerator`**: A flexible generator for REST-based LLM APIs. It allows customization of HTTP methods, headers, request/response templates, and handling of API keys.

---

## 4. Loading and Configuring Probes

Probes are designed to test specific behaviors or vulnerabilities in the model. The example below uses Dan_6_2

```python
from garak.probes.dan import Dan_6_2

# Initialize the probe
probe = Dan_6_2()

# Optionally, configure probe parameters
probe.generations = 1  # Number of responses to generate per prompt
```

**Dependencies**:

- Probes may have specific dependencies (e.g., data files, language support).
- Ensure any required data or configurations are accessible.

**Class Description**:

- **`Dan_6_2`**: A probe containing a "Do Anything Now" (DAN) prompt designed to bypass system prompts and elicit unrestricted responses.

---

## 5. Running Probes and Collecting Attempts

An attempt represents a single interaction between the probe and the generator.

```python
# Run the probe against the OpenAI generator
openai_attempts = probe.probe(openai_generator)

# Alternatively, run the probe against the REST generator
rest_attempts = probe.probe(rest_generator)
```

**Dependencies**:

- Network connectivity to the endpoints.
- Properly configured generators and probes.

**Function Description**:

- **`probe.probe(generator)`**: Executes the probe using the specified generator, returning a list of `Attempt` objects containing prompts and responses.

---

## 6. Applying Detectors to Analyze Responses

Detectors analyze attempts to identify failures or unwanted content.

```python
from garak.detectors.mitigation import MitigationBypass

# Initialize the detector
detector = MitigationBypass()

# Analyze attempts
for attempt in openai_attempts:
    detector.detect(attempt)

for attempt in rest_attempts:
    detector.detect(attempt)
```

**Dependencies**:

- Detectors may require additional libraries or models for analysis.
  - For example, detectors using machine learning models might require Hugging Face transformers.
- Ensure any required resources are available.

**Class Description**:

- **`MitigationBypass`**: A detector that checks if the model bypassed safety mitigations or system prompts.

---

## 7. Evaluating and Reporting Results

After running detectors, you can evaluate the results.

```python
from garak.evaluators import Evaluator

# Initialize an evaluator
evaluator = Evaluator()

# Evaluate OpenAI attempts
openai_results = evaluator.evaluate(openai_attempts, [detector])

# Evaluate REST attempts
rest_results = evaluator.evaluate(rest_attempts, [detector])

# Display results
print("OpenAI Results:")
for result in openai_results:
    print(result)

print("\nREST Results:")
for result in rest_results:
    print(result)
```

**Dependencies**:

- None beyond Garak's core.

**Class Description**:

- **`Evaluator`**: Processes attempts and detectors' findings to produce pass/fail outcomes for each probe.

---

## 8. Example: Putting It All Together

```python
# Import necessary components
from garak.generators.openai import OpenAIGenerator
from garak.generators.rest import RestGenerator
from garak.probes.dan import Dan_6_2
from garak.detectors.mitigation import MitigationBypass
from garak.evaluators import Evaluator

# Set up the OpenAI generator
openai_generator = OpenAIGenerator(name='gpt-3.5-turbo')

# Configure the REST generator
rest_generator_config = {
    'uri': 'https://your-api-endpoint.com/generate',
    'method': 'post',
    'headers': {
        'Authorization': 'Bearer YOUR_REST_API_KEY',
        'Content-Type': 'application/json',
    },
    'req_template_json_object': {
        'prompt': '$INPUT',
    },
    'response_json': True,
    'response_json_field': 'generated_text',
}
rest_generator = RestGenerator(
    uri=rest_generator_config['uri'],
    name='Custom REST Generator',
)
for key, value in rest_generator_config.items():
    setattr(rest_generator, key, value)

# Instantiate the probe
probe = Dan_6_2()

# Run the probe with both generators
openai_attempts = probe.probe(openai_generator)
rest_attempts = probe.probe(rest_generator)

# Initialize the detector
detector = MitigationBypass()

# Analyze the attempts
for attempt in openai_attempts:
    detector.detect(attempt)

for attempt in rest_attempts:
    detector.detect(attempt)

# Evaluate and display results
evaluator = Evaluator()

openai_results = evaluator.evaluate(openai_attempts, [detector])
rest_results = evaluator.evaluate(rest_attempts, [detector])

print("OpenAI Results:")
for result in openai_results:
    print(result)

print("\nREST Results:")
for result in rest_results:
    print(result)
```

---

## 9. Additional Considerations

- **Custom Probes and Detectors**: You can create your own probes and detectors by subclassing `Probe` and `Detector` respectively.
- **Parallelization**: For large numbers of attempts, consider configuring Garak to run probes in parallel.
- **Logging and Reporting**: Garak provides mechanisms to log detailed information about attempts and results, which can be customized or extended.



## Note
- Follow established procedures for Red Teaming
- Always ensure compliance with the terms of service of any APIs or services you interact with, especially when using OpenAI's API or any external endpoints.
- Be cautious when running probes that may generate or interact with potentially harmful or prohibited content.