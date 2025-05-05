# ViolentUTF
A red teaming tool for Generative AI.

## Announcement
- 24APR: ViolentUTF now moves on to the final round of the [CyberWarrior 2025 - Applied LLM Challenge](https://www.svcsi.org/events-1/cyberwarrior-2025-applied-llm-challenge) so the codes will stay under embargo until the winners are announced in June 2025. The first release will immediately dropped immediately after the competition is over.
- 06MAR: I'm enrolling violentUTF to [CyberWarrior 2025 - Applied LLM Challenge](https://www.svcsi.org/events-1/cyberwarrior-2025-applied-llm-challenge) so the inition code push will not happen at least until the Demo Paper submission deadline is passed (27APR).
- A while ago: Please stand by for the initial nightly-build release (scheduled for early March). 

## Folder Structure
```
/
├── README.md
├── env.sample 
├── Guide_RedTeaming_GenAIsystems.md
├── LICENSE
├── .gitignore
├── Home.py            # The home page of the Streamlit application
├── vitutf.py          # Commandline application
├── setup_linux.sh     # Setup script for Linux
├── setup_macos.sh     # Setup script for Mac
├── setup_windows.bat  # Setup script for Windows
├── config.py          # Configuration settings
├── requirements.txt   # Requirement file
├── api/               # API package
│   ├── __init__.py
│   └── v1
│       ├── __init__.py
│       ├── api.py     # Include all routers
│       └── endpoints/ # Individual endpoints
│           ├── __init__.py
│           ├── hello.py                 # Hello World endpoint
│           ├── memory.py                # Memory configuration endpoints
│           ├── targets.py               # Target configuration endpoints
│           ├── datasets.py              # Dataset configuration endpoints
│           ├── converters.py            # Converter configuration endpoints
│           ├── scorers.py               # Scorer configuration endpoints
│           ├── orchestrators.py         # Orchestrator configuration endpoints
│           └── reports.py               # Report generation endpoints
├── app_data
|   ├── .gitignore
|   ├── simplechat     # A simple chat application's data
|   └── violentutf     # ViolentUTF's data
├── app_logs
|   ├── .gitignore
|   ├── simplechat     # A simple chat application's logs
|   └── violentutf     # ViolentUTF's logs
├── core/              # Core application modules
│   ├── __init__.py
│   ├── auth.py        # Authentication and authorization
│   ├── security.py    # Security-related utilities
│   ├── config.py      # Configuration loading
│   └── utils.py       # Utility functions
├── docs/              # Documentations
│   ├── pyrit_API.md
│   ├── SystemModel.sysml
│   ├── .gitignore
│   ├── PyRIT_snapshot/
│   └── ...
├── models/            # Pydantic models (schemas)
│   ├── __init__.py
│   ├── user_identity.py  # UserIdentity model
│   ├── error_response.py
│   ├── memory.py
│   ├── target.py
│   ├── dataset.py
│   ├── converter.py
│   ├── scorer.py
│   ├── orchestrator.py
│   ├── report.py
│   └── (other models)
├── pages/             # 
├── parameters/
│   └── default_parameters.yaml
├── tests/             # Test suite
|   ├── __init__.py
|   ├── test_main.py
|   ├── test_memory.py
|   └── (other tests)
└── (additional files)
```
