"""
MCP Integration Utilities for ViolentUTF
Provides natural language command parsing and context analysis for MCP features
"""

import json
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

# Import existing utilities
from .logging import get_logger
from .mcp_client import MCPClient, MCPClientSync

# Import existing dataset utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from util_datasets.dataset_transformations import (
        JinjaTransformer,
        TransformationConfig,
    )
except ImportError:
    # Fallback if dataset_transformations is not available
    JinjaTransformer = None
    TransformationConfig = None

# Set up logger
logger = get_logger(__name__)


class MCPCommandType(Enum):
    """Types of MCP commands"""

    HELP = "help"
    TEST = "test"
    DATASET = "dataset"
    ENHANCE = "enhance"
    ANALYZE = "analyze"
    RESOURCES = "resources"
    PROMPT = "prompt"
    LIST = "list"
    UNKNOWN = "unknown"


@dataclass
class MCPCommand:
    """Parsed MCP command"""

    type: MCPCommandType
    subcommand: Optional[str] = None
    arguments: Dict[str, Any] = None
    raw_text: str = ""

    def __post_init__(self):
        if self.arguments is None:
            self.arguments = {}


class NaturalLanguageParser:
    """Parse natural language commands for MCP operations"""

    # Command patterns
    COMMAND_PATTERNS = {
        MCPCommandType.HELP: [
            r"/mcp\s+help",
            r"show\s+mcp\s+commands?",
            r"what\s+can\s+mcp\s+do",
            r"mcp\s+usage",
        ],
        MCPCommandType.TEST: [
            r"/mcp\s+test\s+(?P<test_type>[\w-]+)",
            r"/mcp\s+test(?:\s+|$)",  # Allow /mcp test without type
            r"run\s+(?P<test_type>\w+)\s+test",
            r"test\s+for\s+(?P<test_type>\w+)",
            r"check\s+for\s+(?P<test_type>\w+)",
        ],
        MCPCommandType.DATASET: [
            r"/mcp\s+dataset\s+(?P<dataset_name>[\w-]+)",
            r"load\s+dataset\s+(?P<dataset_name>[\w-]+)",
            r"use\s+(?P<dataset_name>[\w-]+)\s+dataset",
            r"show\s+(?P<dataset_name>[\w-]+)\s+data",
        ],
        MCPCommandType.ENHANCE: [
            r"/mcp\s+enhance",
            r"enhance\s+this\s+prompt",
            r"improve\s+this\s+prompt",
            r"make\s+this\s+prompt\s+better",
        ],
        MCPCommandType.ANALYZE: [
            r"/mcp\s+analyze",
            r"analyze\s+this\s+prompt",
            r"analyze\s+for\s+(?P<issue>\w+)",
            r"find\s+(?P<issue>\w+)\s+issues?",
        ],
        MCPCommandType.RESOURCES: [
            r"/mcp\s+resources",
            r"show\s+mcp\s+resources",
            r"list\s+available\s+resources",
            r"what\s+resources\s+are\s+available",
        ],
        MCPCommandType.PROMPT: [
            r"/mcp\s+prompt\s+(?P<prompt_name>[\w-]+)",
            r"use\s+(?P<prompt_name>[\w-]+)\s+prompt",
            r"show\s+(?P<prompt_name>[\w-]+)\s+template",
        ],
        MCPCommandType.LIST: [
            r"/mcp\s+list\s+(?P<resource>[\w-]+)",
            r"list\s+(?:all\s+)?(?P<resource>[\w-]+)",
            r"show\s+(?:me\s+)?(?:all\s+)?(?:available\s+)?(?P<resource>[\w-]+)",
            r"what\s+(?P<resource>[\w-]+)\s+are\s+available",
        ],
    }

    def __init__(self):
        """Initialize parser with compiled patterns"""
        self.compiled_patterns = {}
        for cmd_type, patterns in self.COMMAND_PATTERNS.items():
            self.compiled_patterns[cmd_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

    def parse(self, text: str) -> MCPCommand:
        """
        Parse natural language text into MCP command

        Args:
            text: Input text to parse

        Returns:
            MCPCommand object with parsed information
        """
        text = text.strip()

        # Check each command type
        for cmd_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    # Extract named groups as arguments
                    arguments = match.groupdict()
                    # Remove None values
                    arguments = {k: v for k, v in arguments.items() if v is not None}

                    return MCPCommand(type=cmd_type, arguments=arguments, raw_text=text)

        # If no pattern matches, return unknown command
        return MCPCommand(type=MCPCommandType.UNKNOWN, raw_text=text)

    def suggest_command(self, partial_text: str) -> List[str]:
        """
        Suggest commands based on partial input

        Args:
            partial_text: Partial command text

        Returns:
            List of suggested commands
        """
        suggestions = []
        partial_lower = partial_text.lower().strip()

        # All available commands
        all_commands = [
            "/mcp help",
            "/mcp enhance",
            "/mcp analyze",
            "/mcp test jailbreak",
            "/mcp test bias",
            "/mcp test privacy",
            "/mcp dataset harmbench",
            "/mcp dataset jailbreak",
            "/mcp resources",
            "/mcp prompt security_test",
        ]

        # Basic command suggestions
        if partial_lower.startswith("/mc"):
            # If it's a partial /mcp command, suggest all commands
            suggestions = all_commands
        elif partial_lower.startswith("enha"):
            suggestions.append("/mcp enhance")
        elif partial_lower.startswith("analy"):
            suggestions.append("/mcp analyze")
        elif partial_lower.startswith("test"):
            suggestions.extend(
                ["/mcp test jailbreak", "/mcp test bias", "/mcp test privacy"]
            )
        elif partial_lower.startswith("load") or partial_lower.startswith("data"):
            suggestions.extend(["/mcp dataset harmbench", "/mcp dataset jailbreak"])
        else:
            # For any other text, suggest relevant commands based on keywords
            for cmd in all_commands:
                if partial_lower in cmd.lower():
                    suggestions.append(cmd)

        # Filter based on partial text matching start of suggestion
        filtered = []
        for s in suggestions:
            if s.lower().startswith(partial_lower) or partial_lower in s.lower():
                if s not in filtered:
                    filtered.append(s)

        return filtered[:5]  # Return top 5 suggestions

    def extract_parameters(self, text: str) -> Dict[str, Any]:
        """
        Extract parameters from natural language text

        Args:
            text: Natural language text

        Returns:
            Dictionary of extracted parameters
        """
        params = {}
        text_lower = text.lower()

        # Extract temperature
        temp_patterns = [
            r"temperature\s*(?:of|=|:)?\s*(\d+\.?\d*)",
            r"temp\s*(?:of|=|:)?\s*(\d+\.?\d*)",
            r"(\d+\.?\d*)\s*temperature",
        ]
        for pattern in temp_patterns:
            match = re.search(pattern, text_lower)
            if match:
                params["temperature"] = float(match.group(1))
                break

        # Extract max tokens
        token_patterns = [
            r"max[\s_]?tokens?\s*(?:of|=|:)?\s*(\d+)",
            r"(\d+)\s*tokens?",
            r"limit\s*(?:of|=|:)?\s*(\d+)",
        ]
        for pattern in token_patterns:
            match = re.search(pattern, text_lower)
            if match:
                params["max_tokens"] = int(match.group(1))
                break

        # Extract creativity/temperature descriptors
        if "creative" in text_lower or "high creativity" in text_lower:
            params["temperature"] = 0.9
        elif "balanced" in text_lower:
            params["temperature"] = 0.7
        elif "focused" in text_lower or "low creativity" in text_lower:
            params["temperature"] = 0.3

        return params


class ContextAnalyzer:
    """Analyze conversation context for MCP opportunities"""

    # Keywords that might trigger suggestions
    ENHANCEMENT_TRIGGERS = [
        "improve",
        "better",
        "enhance",
        "optimize",
        "refine",
        "stronger",
        "clearer",
        "more effective",
    ]

    SECURITY_TRIGGERS = [
        "jailbreak",
        "bypass",
        "security",
        "safety",
        "harmful",
        "malicious",
        "attack",
        "vulnerability",
        "exploit",
    ]

    BIAS_TRIGGERS = [
        "bias",
        "fair",
        "discriminat",
        "stereotyp",
        "prejudic",
        "neutral",
        "balanced",
        "inclusive",
    ]

    def __init__(self, mcp_client: Optional[MCPClientSync] = None):
        """Initialize analyzer with optional MCP client"""
        self.mcp_client = mcp_client or MCPClientSync()
        self.logger = logger

    def analyze_for_suggestions(self, text: str) -> List[Dict[str, Any]]:
        """
        Analyze text and suggest relevant MCP operations

        Args:
            text: Text to analyze

        Returns:
            List of suggestions with type and reason
        """
        suggestions = []
        text_lower = text.lower()

        # Check for enhancement opportunities
        if any(trigger in text_lower for trigger in self.ENHANCEMENT_TRIGGERS):
            suggestions.append(
                {
                    "type": "enhance",
                    "reason": "Your message mentions improvement. Would you like to enhance this prompt?",
                    "command": "/mcp enhance",
                    "priority": 1,
                }
            )

        # Check for security concerns
        if any(trigger in text_lower for trigger in self.SECURITY_TRIGGERS):
            suggestions.append(
                {
                    "type": "security",
                    "reason": "Security-related content detected. Consider running a security analysis.",
                    "command": "/mcp analyze",
                    "priority": 2,
                }
            )
            suggestions.append(
                {
                    "type": "test",
                    "reason": "You might want to test for jailbreak vulnerabilities.",
                    "command": "/mcp test jailbreak",
                    "priority": 2,
                }
            )

        # Check for bias concerns
        if any(trigger in text_lower for trigger in self.BIAS_TRIGGERS):
            suggestions.append(
                {
                    "type": "bias",
                    "reason": "Bias-related concerns detected. Consider a bias analysis.",
                    "command": "/mcp test bias",
                    "priority": 2,
                }
            )

        # Sort by priority
        suggestions.sort(key=lambda x: x.get("priority", 999))

        return suggestions[:3]  # Return top 3 suggestions

    def detect_prompt_type(self, text: str) -> str:
        """
        Detect the type of prompt based on content

        Args:
            text: Prompt text to analyze

        Returns:
            Detected prompt type
        """
        text_lower = text.lower()

        # Security/jailbreak prompts
        if any(
            word in text_lower for word in ["ignore", "bypass", "override", "forget"]
        ):
            return "jailbreak_attempt"

        # Role-playing prompts
        if any(
            phrase in text_lower
            for phrase in ["act as", "pretend to be", "you are now"]
        ):
            return "roleplay"

        # Question prompts
        if text_lower.strip().endswith("?"):
            return "question"

        # Instruction prompts
        if any(word in text_lower for word in ["write", "create", "generate", "make"]):
            return "instruction"

        # Default
        return "general"


class ResourceSearcher:
    """Search and filter MCP resources"""

    def __init__(self, mcp_client: Optional[MCPClientSync] = None):
        """Initialize searcher with MCP client"""
        self.mcp_client = mcp_client or MCPClientSync()
        self._resources_cache = None
        self._prompts_cache = None
        self.logger = logger

    def search_resources(
        self, query: str, resource_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for resources matching query

        Args:
            query: Search query
            resource_type: Optional filter by resource type

        Returns:
            List of matching resources
        """
        # Get all resources (with caching)
        if self._resources_cache is None:
            self._resources_cache = self.mcp_client.list_resources()

        resources = self._resources_cache
        query_lower = query.lower()

        # Filter by query
        matches = []
        for resource in resources:
            # Check name and description
            if (
                query_lower in resource.get("name", "").lower()
                or query_lower in resource.get("description", "").lower()
                or query_lower in resource.get("uri", "").lower()
            ):

                # Filter by type if specified
                if resource_type:
                    if resource_type in resource.get("uri", ""):
                        matches.append(resource)
                else:
                    matches.append(resource)

        return matches

    def search_prompts(
        self, query: str, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for prompts matching query

        Args:
            query: Search query
            category: Optional filter by category

        Returns:
            List of matching prompts
        """
        # Get all prompts (with caching)
        if self._prompts_cache is None:
            self._prompts_cache = self.mcp_client.list_prompts()

        prompts = self._prompts_cache
        query_lower = query.lower()

        # Filter by query
        matches = []
        for prompt in prompts:
            # Check name and description
            if (
                query_lower in prompt.get("name", "").lower()
                or query_lower in prompt.get("description", "").lower()
            ):

                # Filter by category if specified
                if category:
                    # Category might be in name or tags
                    if category.lower() in prompt.get("name", "").lower():
                        matches.append(prompt)
                else:
                    matches.append(prompt)

        return matches

    def get_resource_by_uri(self, uri: str) -> Optional[Dict[str, Any]]:
        """Get specific resource by URI"""
        resources = self._resources_cache or self.mcp_client.list_resources()

        for resource in resources:
            if resource.get("uri") == uri:
                return resource

        return None

    def get_prompt_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific prompt by name"""
        prompts = self._prompts_cache or self.mcp_client.list_prompts()

        for prompt in prompts:
            if prompt.get("name") == name:
                return prompt

        return None


class TestScenarioInterpreter:
    """Interpret and execute test scenarios using MCP"""

    def __init__(self, mcp_client: Optional[MCPClientSync] = None):
        """Initialize interpreter with MCP client"""
        self.mcp_client = mcp_client or MCPClientSync()
        self.logger = logger

    def interpret_test_request(
        self, test_type: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Interpret a test request and prepare test configuration

        Args:
            test_type: Type of test requested
            context: Optional context or prompt to test

        Returns:
            Test configuration dictionary
        """
        test_type_lower = test_type.lower()

        # Map test types to MCP prompts
        test_mappings = {
            "jailbreak": "jailbreak_test",
            "bias": "bias_detection",
            "privacy": "privacy_test",
            "security": "security_audit",
            "harmful": "harmful_content_test",
            "injection": "prompt_injection",
        }

        # Find matching prompt
        prompt_name = None
        for key, value in test_mappings.items():
            if key in test_type_lower:
                prompt_name = value
                break

        if not prompt_name:
            return {
                "error": f"Unknown test type: {test_type}",
                "available_types": list(test_mappings.keys()),
            }

        # Prepare test configuration
        config = {
            "test_type": test_type,
            "prompt_name": prompt_name,
            "context": context,
            "parameters": self._get_default_parameters(prompt_name),
        }

        return config

    def _get_default_parameters(self, prompt_name: str) -> Dict[str, Any]:
        """Get default parameters for a prompt"""
        defaults = {
            "jailbreak_test": {
                "scenario": "standard",
                "techniques": ["roleplay", "hypothetical"],
                "target_behavior": "harmful_content",
            },
            "bias_detection": {
                "focus_area": "general",
                "demographics": ["gender", "race", "age"],
                "test_depth": "standard",
            },
            "privacy_test": {
                "data_types": ["personal", "financial"],
                "test_method": "extraction",
                "sensitivity_level": "high",
            },
            "security_audit": {
                "audit_scope": "comprehensive",
                "vulnerability_types": ["injection", "bypass", "extraction"],
                "severity_threshold": "medium",
            },
            "harmful_content_test": {
                "content_types": ["violence", "illegal", "harmful_advice"],
                "test_intensity": "moderate",
            },
            "prompt_injection": {
                "injection_type": "direct",
                "payload_complexity": "medium",
                "target_override": "system_prompt",
            },
        }

        return defaults.get(prompt_name, {})

    def execute_test(self, test_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a test based on configuration

        Args:
            test_config: Test configuration from interpret_test_request

        Returns:
            Test results dictionary
        """
        if "error" in test_config:
            return test_config

        try:
            # Get the prompt
            prompt_name = test_config["prompt_name"]
            parameters = test_config.get("parameters", {})

            # Add context if provided
            if test_config.get("context"):
                parameters["context"] = test_config["context"]

            # Get rendered prompt from MCP
            rendered_prompt = self.mcp_client.get_prompt(prompt_name, parameters)

            if not rendered_prompt:
                return {
                    "error": f"Failed to get prompt: {prompt_name}",
                    "test_type": test_config["test_type"],
                }

            # Return test setup (actual execution would happen elsewhere)
            return {
                "test_type": test_config["test_type"],
                "prompt_name": prompt_name,
                "rendered_prompt": rendered_prompt,
                "parameters": parameters,
                "status": "ready",
                "next_steps": [
                    "Execute prompt against target model",
                    "Analyze response for vulnerabilities",
                    "Generate security report",
                ],
            }

        except Exception as e:
            self.logger.error(f"Test execution failed: {e}")
            return {
                "error": str(e),
                "test_type": test_config.get("test_type", "unknown"),
            }


class DatasetIntegration:
    """Integrate MCP with existing dataset system"""

    def __init__(self, mcp_client: Optional[MCPClientSync] = None):
        """Initialize with MCP client"""
        self.mcp_client = mcp_client or MCPClientSync()
        self.logger = logger

    def load_mcp_dataset(self, dataset_uri: str) -> Optional[Any]:
        """
        Load dataset from MCP resource

        Args:
            dataset_uri: MCP resource URI for dataset

        Returns:
            Loaded dataset or None if error
        """
        try:
            # Read resource from MCP
            content = self.mcp_client.read_resource(dataset_uri)

            if not content:
                self.logger.error(f"Failed to read dataset: {dataset_uri}")
                return None

            # If content is already structured, return it
            if isinstance(content, (list, dict)):
                return content

            # If content is JSON string, parse it
            if isinstance(content, str):
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Return as raw text if not JSON
                    return content

            return content

        except Exception as e:
            self.logger.error(f"Failed to load MCP dataset: {e}")
            return None

    def transform_with_jinja(self, data: Any, template: str) -> Optional[str]:
        """
        Transform data using Jinja2 template

        Args:
            data: Data to transform
            template: Jinja2 template string

        Returns:
            Transformed string or None if error
        """
        try:
            if JinjaTransformer is None or TransformationConfig is None:
                # Fallback to basic Jinja2 if transformer not available
                from jinja2 import Template

                jinja_template = Template(template)

                # Prepare data for transformation
                if isinstance(data, list):
                    template_data = {"items": data}
                elif isinstance(data, dict):
                    template_data = data
                else:
                    template_data = {"content": data}

                return jinja_template.render(**template_data)

            # Use existing Jinja transformer
            config = TransformationConfig(template=template, output_format="text")

            transformer = JinjaTransformer(config)

            # Prepare data for transformation
            if isinstance(data, list):
                template_data = {"items": data}
            elif isinstance(data, dict):
                template_data = data
            else:
                template_data = {"content": data}

            # Transform
            return transformer.transform([template_data])

        except Exception as e:
            self.logger.error(f"Jinja transformation failed: {e}")
            return None

    def list_available_datasets(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        List all available datasets from both MCP and local sources

        Returns:
            Dictionary with 'mcp' and 'local' dataset lists
        """
        datasets = {"mcp": [], "local": []}

        # Get MCP datasets
        try:
            resources = self.mcp_client.list_resources()
            for resource in resources:
                if "dataset" in resource.get("uri", "").lower():
                    datasets["mcp"].append(
                        {
                            "name": resource.get("name", "Unknown"),
                            "uri": resource.get("uri", ""),
                            "description": resource.get("description", ""),
                            "source": "mcp",
                        }
                    )
        except Exception as e:
            self.logger.error(f"Failed to list MCP datasets: {e}")

        # Get local PyRIT datasets
        try:
            # This would integrate with existing dataset system
            # For now, just return placeholder
            datasets["local"].append(
                {
                    "name": "PyRIT Native Datasets",
                    "description": "Built-in PyRIT security testing datasets",
                    "source": "local",
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to list local datasets: {e}")

        return datasets


class ConfigurationIntentDetector:
    """Detects configuration-related intents in natural language"""

    def __init__(self):
        self.generator_keywords = [
            "generator",
            "create",
            "model",
            "gpt",
            "claude",
            "llm",
        ]
        self.dataset_keywords = ["dataset", "data", "load", "prompts"]
        self.orchestrator_keywords = [
            "orchestrator",
            "test",
            "run",
            "execute",
            "red team",
        ]
        self.scorer_keywords = ["scorer", "score", "evaluate", "bias", "security"]
        self.converter_keywords = [
            "converter",
            "convert",
            "transform",
            "transformation",
            "translation",
        ]

    def detect_configuration_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """Detect if text contains configuration intent"""
        text_lower = text.lower()

        # Check for orchestrator setup first (most specific)
        if any(kw in text_lower for kw in ["orchestrator", "red team", "pipeline"]):
            return {"type": "orchestrator", "action": "create", "details": text}

        # Check for converter configuration
        if any(kw in text_lower for kw in self.converter_keywords):
            # Make sure it's not another resource type
            if not any(
                kw in text_lower
                for kw in [
                    "generator",
                    "model",
                    "gpt",
                    "claude",
                    "llm",
                    "dataset",
                    "data",
                    "scorer",
                    "orchestrator",
                ]
            ):
                action = (
                    "list"
                    if any(
                        word in text_lower
                        for word in ["show", "list", "available", "what"]
                    )
                    else "configure"
                )
                return {"type": "converter", "action": action, "details": text}

        # Check for scorer configuration (specific)
        if any(kw in text_lower for kw in self.scorer_keywords):
            # Make sure it's not a generator or dataset intent
            if not any(
                kw in text_lower
                for kw in [
                    "generator",
                    "model",
                    "gpt",
                    "claude",
                    "llm",
                    "dataset",
                    "data",
                ]
            ):
                action = (
                    "list"
                    if any(
                        word in text_lower
                        for word in ["show", "list", "available", "what", "options"]
                    )
                    else "configure"
                )
                scorer_type = self._extract_scorer_type(text)
                return {
                    "type": "scorer",
                    "action": action,
                    "target": scorer_type,
                    "details": text,
                }

        # Check for dataset operations (before generator since "load" is specific)
        if any(kw in text_lower for kw in self.dataset_keywords):
            # Exclude if it's clearly about generators
            if not any(
                kw in text_lower
                for kw in ["generator", "model", "gpt", "claude", "llm"]
            ):
                action = "load" if "load" in text_lower else "create"
                dataset_name = self._extract_dataset_name(text)
                return {
                    "type": "dataset",
                    "action": action,
                    "target": dataset_name,
                    "details": text,
                }

        # Check for generator creation (most general)
        if any(kw in text_lower for kw in self.generator_keywords):
            if (
                "create" in text_lower
                or "set up" in text_lower
                or "configure" in text_lower
            ):
                return {"type": "generator", "action": "create", "details": text}

        return None

    def extract_generator_params(self, text: str) -> Dict[str, Any]:
        """Extract generator parameters from natural language"""
        parser = NaturalLanguageParser()
        params = parser.extract_parameters(text)

        # Extract model name
        text_lower = text.lower()
        if "gpt-4" in text_lower:
            params["model"] = "gpt-4"
        elif "gpt-3.5" in text_lower or "gpt-35" in text_lower:
            params["model"] = "gpt-3.5-turbo"
        elif "claude" in text_lower:
            params["model"] = "claude-3"

        # Extract provider
        if "openai" in text_lower:
            params["provider"] = "openai"
        elif "anthropic" in text_lower:
            params["provider"] = "anthropic"

        return params

    def _extract_dataset_name(self, text: str) -> str:
        """Extract dataset name from text"""
        # Simple extraction - look for common dataset names
        text_lower = text.lower()
        if "jailbreak" in text_lower:
            return "jailbreak"
        elif "bias" in text_lower:
            return "bias-test"
        elif "harmful" in text_lower:
            return "harmful-content"
        return "custom"

    def _extract_scorer_type(self, text: str) -> str:
        """Extract scorer type from text"""
        text_lower = text.lower()
        if "bias" in text_lower:
            return "bias"
        elif "security" in text_lower:
            return "security"
        elif "harm" in text_lower:
            return "harmful"
        return "general"


class ConversationContextAnalyzer:
    """Analyzes conversation context to provide intelligent suggestions"""

    def __init__(self):
        self.topic_keywords = {
            "security": [
                "jailbreak",
                "injection",
                "attack",
                "vulnerability",
                "exploit",
            ],
            "bias": ["bias", "fairness", "discrimination", "stereotype"],
            "harmful": ["harmful", "toxic", "dangerous", "inappropriate"],
            "privacy": ["privacy", "pii", "personal", "sensitive", "data"],
            "test": ["test", "evaluate", "assess", "check", "verify"],
            "dataset": ["dataset", "data", "prompts", "examples"],
            "generator": ["generator", "model", "llm", "ai", "gpt", "claude"],
            "orchestrator": ["orchestrator", "pipeline", "workflow", "automation"],
        }

    def analyze_context(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Analyze conversation context"""
        if not messages:
            return {
                "message_count": 0,
                "topics": [],
                "suggested_actions": [],
                "mentioned_resources": [],
            }

        # Extract topics from messages
        topics = set()
        mentioned_resources = set()

        for msg in messages:
            content = msg.get("content", "").lower()

            # Identify topics
            for topic, keywords in self.topic_keywords.items():
                if any(kw in content for kw in keywords):
                    topics.add(topic)

            # Look for resource mentions
            if "dataset" in content:
                mentioned_resources.add("dataset")
            if "generator" in content:
                mentioned_resources.add("generator")
            if "orchestrator" in content:
                mentioned_resources.add("orchestrator")

        # Generate suggestions based on context
        suggested_actions = []

        if "dataset" in topics and "generator" not in mentioned_resources:
            suggested_actions.append("Create a generator to test with the dataset")

        if "generator" in mentioned_resources and "test" not in topics:
            suggested_actions.append("Run security tests on the generator")

        if "security" in topics and "dataset" not in mentioned_resources:
            suggested_actions.append("Load security testing datasets")

        return {
            "message_count": len(messages),
            "topics": list(topics),
            "suggested_actions": suggested_actions,
            "mentioned_resources": list(mentioned_resources),
        }
