# ViolentUTF
A red teaming tool for Generative AI.

## Announcement
- 06MAR: I'm enrolling violentUTF to [CyberWarrior 2025 - Applied LLM Challenge](https://www.svcsi.org/events-1/cyberwarrior-2025-applied-llm-challenge) so the inition code push will not happen at least until the Demo Paper submission deadline is passed (27APR).
- A while ago: Please stand by for the initial nightly-build release (scheduled for early March). 

## Folder Structure
violentutf/
├── app/
│   ├── __init__.py
│   ├── main.py            # Entry point of the application
│   ├── config.py          # Configuration settings
│   ├── api/               # API package
│   │   ├── __init__.py
│   │   ├── deps.py        # Dependencies
│   │   ├── v1/            # API version 1
│   │   │   ├── __init__.py
│   │   │   ├── api.py     # Include all routers
│   │   │   └── endpoints/ # Individual endpoints
│   │   │       ├── __init__.py
│   │   │       ├── memory.py                # Memory configuration endpoints
│   │   │       ├── targets.py               # Target configuration endpoints
│   │   │       ├── datasets.py              # Dataset configuration endpoints
│   │   │       ├── converters.py            # Converter configuration endpoints
│   │   │       ├── scorers.py               # Scorer configuration endpoints
│   │   │       ├── orchestrators.py         # Orchestrator configuration endpoints
│   │   │       └── reports.py               # Report generation endpoints
│   ├── core/              # Core application modules
│   │   ├── __init__.py
│   │   ├── auth.py        # Authentication and authorization
│   │   ├── security.py    # Security-related utilities
│   │   ├── config.py      # Configuration loading
│   │   └── utils.py       # Utility functions
│   ├── models/            # Pydantic models (schemas)
│   │   ├── __init__.py
│   │   ├── user_identity.py
│   │   ├── error_response.py
│   │   ├── memory.py
│   │   ├── target.py
│   │   ├── dataset.py
│   │   ├── converter.py
│   │   ├── scorer.py
│   │   ├── orchestrator.py
│   │   ├── report.py
│   │   └── (other models)
│   ├── services/          # Business logic
│   │   ├── __init__.py
│   │   ├── memory_service.py
│   │   ├── target_service.py
│   │   ├── dataset_service.py
│   │   ├── converter_service.py
│   │   ├── scorer_service.py
│   │   ├── orchestrator_service.py
│   │   ├── report_service.py
│   │   └── (other services)
│   └── tests/             # Test suite
│       ├── __init__.py
│       ├── test_main.py
│       ├── test_memory.py
│       └── (other tests)
├── requirements.txt       # Project dependencies
├── setup.py               # Installation script
├── README.md              # Project documentation
├── .gitignore             # Git ignore file
└── (additional files)