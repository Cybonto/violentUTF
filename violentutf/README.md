# ViolentUTF

The rapid integration of Generative AI (GenAI) into various applications necessitates robust risk management strategies which includes Red Teaming (RT) - an evaluation method for simulating adversarial attacks. Unfortunately, RT for GenAI is often hindered by technical complexity, lack of user-friendly interfaces, and inadequate reporting features. This paper introduces Violent UTF - an accessible, modular, and scalable platform for GenAI red teaming. Through intuitive interfaces (Web GUI, CLI, API, MCP) powered by LLMs and for LLMs, Violent UTF aims to empower non-technical domain experts and students alongside technical experts, facilitate comprehensive security evaluation by unifying capabilities from RT frameworks like Microsoft PyRIT, Nvidia Garak and its own specialized evaluators. ViolentUTF is being used for evaluating the robustness of a flagship LLM-based product in a large US Government department. It also demonstrates effectiveness in evaluating LLMs' cross-domain reasoning capability between cybersecurity and behavioral psychology.

Developer: Tam (aka Tom) Nguyen

## Setup Steps
### 1. Setting up KeyCloak with Docker
* ViolentUTF is protected by KeyCloak by default. Please follow [ViolentUTF KeyCloak Setup Guide](https://github.com/Cybonto/ViolentUTF_nightly/tree/main/keycloak). The main idea is to have KeyCloak running first. Then, if the ViolentUTF realm is not there in KeyCloak, you can import an exported realm file (included) and you should be good to go with KeyCloak.
* Make sure to get the information from KeyCloak and fill out the [env.sample file](https://github.com/Cybonto/ViolentUTF_nightly/blob/main/env.sample) and then rename it to `.env`.
### 2. Run ViolentUTF setup script
Once your KeyCloak is up, you just need to run the ViolentUTF script per your OS. I tested the Mac OS script and it works. The script will automatically launch ViolentUTF at the end, in your default browser.
### 3. Login and play with ViolentUTF
You can get to your KeyCloak admin panel and check the username and password for the existing user under the ViolentUTF realm. You can also add more users in case you want to share this web tool with more users.
Check [the demo](https://youtu.be/c-UCYXq0rfY) for how a basic run should be.


## Logging

This application uses Python's standard `logging` module configured via `utils/logging.py`.

**Configuration:**

* Logging is set up once per Streamlit session when `Home.py` is first loaded.
* Log messages are written to a file located at: `app_logs/app.log`
* Logs are also output to the console (stdout).
* The default log level for the file is `DEBUG`, and for the console is `INFO`.
* Log messages from verbose libraries like `httpx` and `httpcore` are suppressed unless they are `WARNING` level or higher.

**Log Format:**

Logs follow this format:

```

YYYY-MM-DD HH:MM:SS,ms [LEVEL   ] [module\_name:function\_name:line\_number] - Log Message

```

Example:

```

2025-04-26 09:00:00,123 [INFO    ] [pages.2\_ConfigureGenerators:main:50] - User '[email address removed]' logged in.
2025-04-26 09:00:05,456 [DEBUG   ] [generators.generator\_config:add\_generator:150] - Adding generator 'MyGPT4' of type 'AzureOpenAI'.
2025-04-26 09:00:10,789 [ERROR   ] [generators.generator\_config:save\_and\_test\_generator:310] - Validation Error saving/testing 'MyGPT4': API key is required.

````

**How to Use Logging in Development:**

1.  **Import:** In any Python module (`.py` file) where you need logging, import the `get_logger` function:
    ```python
    from utils.logging import get_logger
    ```
2.  **Instantiate:** Get a logger instance specific to your module (this helps trace log origins):
    ```python
    logger = get_logger(__name__)
    ```
    *(Note: `__name__` automatically uses the module's path, e.g., `pages.2_ConfigureGenerators`)*
3.  **Log Messages:** Use the logger methods:
    * `logger.debug("Detailed information for diagnosing problems.")`
    * `logger.info("Confirmation that things are working as expected.")`
    * `logger.warning("An indication that something unexpected happened, or indicative of some problem in the near future (e.g. ‘disk space low’). The software is still working as expected.")`
    * `logger.error("Due to a more serious problem, the software has not been able to perform some function.")`
    * `logger.exception("Similar to error, but includes the exception traceback. Use within an except block.")`
    ```python
    try:
        # Risky operation
        result = 10 / 0
    except ZeroDivisionError as e:
        logger.exception(f"Failed to perform division: {e}")
    ```

Check the `app_logs/app.log` file for detailed runtime information and troubleshooting.

## Additional resources
* [Project structure](https://github.com/Cybonto/ViolentUTF_nightly/blob/main/docs/structure.md)
* [Detailed descriptions of the main program steps](https://github.com/Cybonto/ViolentUTF_nightly/tree/main/docs/programSteps)
* [Demo of Basic Use](https://youtu.be/c-UCYXq0rfY)
* [Results of a sample run - customized dataset permutation and evaluator](https://github.com/Cybonto/ViolentUTF_nightly/tree/main/sample_run)
* [My guide to Red Teaming of AI Systems](https://github.com/Cybonto/ViolentUTF_nightly/blob/main/docs/Guide_RedTeaming_GenAIsystems.md)
