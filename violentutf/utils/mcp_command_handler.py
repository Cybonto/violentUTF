# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""MCP command handling and processing utilities.

MCP Command Handler for Phase 3 UI Implementation.

=================================================

This module provides command execution and management for the
Smart Commands & Natural Language Interface in Simple Chat.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple, Union, cast

import streamlit as st

from .mcp_client import MCPClientSync
from .mcp_integration import (
    DatasetIntegration,
    MCPCommand,
    MCPCommandType,
    NaturalLanguageParser,
    ResourceSearcher,
    TestScenarioInterpreter,
)

logger = logging.getLogger(__name__)


class CommandHistory:
    """Manage command history with persistence"""

    def __init__(self: CommandHistory, max_history: int = 50) -> None:
        """Initialize command history with maximum size.

        Args:
            max_history: Maximum number of commands to keep in history

        """
        self.max_history = max_history
        self._history: List[Dict[str, Union[str, bool]]] = []

    def add(
        self: CommandHistory,
        command: str,
        result: Union[str, Dict[str, object], object],
        success: bool = True,
    ) -> None:
        """Add command to history"""
        entry: Dict[str, Union[str, bool]] = {
            "command": command,
            "result": str(result),
            "success": success,
            "timestamp": datetime.now().isoformat(),
        }
        self._history.append(entry)

        # Maintain max history size
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history :]

    def get_recent(self: CommandHistory, count: int = 10) -> List[Dict[str, Union[str, bool]]]:
        """Get recent command history"""
        return self._history[-count:]

    def search(self: CommandHistory, query: str) -> List[Dict[str, Union[str, bool]]]:
        """Search command history"""
        results = []

        query_lower = query.lower()
        for entry in self._history:
            command = entry.get("command", "")
            if isinstance(command, str) and query_lower in command.lower():
                results.append(entry)
        return results

    def clear(self: CommandHistory) -> None:
        """Clear command history"""
        self._history = []


class MCPCommandHandler:
    """Handle MCP command execution and management"""

    def __init__(self: MCPCommandHandler, mcp_client: MCPClientSync) -> None:
        """Initialize MCP command handler with client and integrations.

        Args:
            mcp_client: The MCP client for communication

        """
        self.mcp_client = mcp_client
        self.parser = NaturalLanguageParser()
        self.searcher = ResourceSearcher(mcp_client)
        self.test_interpreter = TestScenarioInterpreter(mcp_client)
        self.dataset_integration = DatasetIntegration(mcp_client)
        self.history = CommandHistory()

        # Command executors mapping
        self._executors = {
            MCPCommandType.HELP: self._execute_help,
            MCPCommandType.TEST: self._execute_test,
            MCPCommandType.DATASET: self._execute_dataset,
            MCPCommandType.ENHANCE: self._execute_enhance,
            MCPCommandType.ANALYZE: self._execute_analyze,
            MCPCommandType.RESOURCES: self._execute_resources,
            MCPCommandType.PROMPT: self._execute_prompt,
        }

    def execute_command(self: MCPCommandHandler, command_text: str) -> Tuple[bool, Union[str, Dict[str, object]]]:
        """Execute an MCP command and return result"""
        try:

            # Parse command
            command = self.parser.parse(command_text)

            if command.type == MCPCommandType.UNKNOWN:
                return (
                    False,
                    "Unknown command. Type '/mcp help' for available commands.",
                )

            # Execute command
            executor = self._executors.get(command.type)
            if not executor:
                return False, f"No executor for command type: {command.type.value}"

            # Execute and track history
            success, result = executor(command)
            self.history.add(command_text, result, success)

            return success, result

        except (AttributeError, ValueError, KeyError, TypeError) as e:
            logger.error("Command execution error: %s", e)
            return False, f"Error executing command: {str(e)}"

    def get_command_suggestions(self: MCPCommandHandler, partial_text: str) -> List[str]:
        """Get command suggestions for autocomplete"""
        suggestions = self.parser.suggest_command(partial_text)

        # Add history-based suggestions
        if len(suggestions) < 5:
            history_matches = self.history.search(partial_text)
            for entry in history_matches[:3]:
                command = entry.get("command", "")
                if isinstance(command, str) and command not in suggestions:
                    suggestions.append(command)

        return suggestions[:5]  # Return top 5 suggestions

    # Command Executors

    def _execute_help(self: MCPCommandHandler, command: MCPCommand) -> Tuple[bool, str]:
        """Execute help command"""
        help_text = """
**Available MCP Commands:**

• `/mcp help` - Show this help message
• `/mcp enhance` - Enhance the current prompt
• `/mcp analyze` - Analyze prompt for issues
• `/mcp test <type>` - Generate test variations
  - Types: jailbreak, bias, privacy, security
• `/mcp dataset <name>` - Load a dataset
• `/mcp prompt <name>` - Use a specific prompt template
• `/mcp resources` - List available resources

**Examples:**
- `/mcp test jailbreak` - Generate jailbreak test
- `/mcp dataset harmbench` - Load HarmBench dataset
- `/mcp prompt security_audit` - Use security audit template

**Natural Language:**
You can also use natural language like:
- "enhance this prompt"
- "test for bias"
- "load advbench dataset"

"""
        return True, help_text

    def _execute_test(self: MCPCommandHandler, command: MCPCommand) -> Tuple[bool, Union[str, Dict[str, object]]]:
        """Execute test command"""
        test_type = (command.arguments or {}).get("test_type", "jailbreak")

        # Get current prompt from session state
        current_prompt = st.session_state.get("current_user_input", "")
        if not current_prompt:
            return False, "No prompt to test. Please enter a prompt first."

        try:
            # Interpret test request
            test_config = self.test_interpreter.interpret_test_request(test_type, current_prompt)

            # Execute test
            result = self.test_interpreter.execute_test(test_config)

            # Format result for display
            if result["status"] == "ready":
                return True, {
                    "type": "test_result",
                    "test_type": test_type,
                    "prompt": result["rendered_prompt"],
                    "config": test_config,
                }
            else:
                return (
                    False,
                    f"Test execution failed: {result.get('error', 'Unknown error')}",
                )

        except (AttributeError, ValueError, KeyError, TypeError, OSError) as e:
            logger.error("Test execution error: %s", e)
            return False, f"Failed to execute test: {str(e)}"

    def _execute_dataset(self: MCPCommandHandler, command: MCPCommand) -> Tuple[bool, Union[str, Dict[str, object]]]:
        """Execute dataset command"""
        dataset_name = (command.arguments or {}).get("dataset_name", "")

        if not dataset_name:
            # List available datasets
            datasets = self.dataset_integration.list_available_datasets()
            return True, {"type": "dataset_list", "datasets": datasets}

        # Try to load specific dataset
        dataset_uri = f"violentutf://datasets/{dataset_name}"
        dataset = self.dataset_integration.load_mcp_dataset(dataset_uri)

        if dataset:
            # Store in session state for use
            st.session_state["loaded_dataset"] = dataset
            st.session_state["loaded_dataset_name"] = dataset_name

            return True, {
                "type": "dataset_loaded",
                "name": dataset_name,
                "size": len(dataset) if isinstance(dataset, list) else "N/A",
                "preview": (dataset[:3] if isinstance(dataset, list) else str(dataset)[:200]),
            }
        else:
            return False, f"Failed to load dataset: {dataset_name}"

    def _execute_enhance(self: MCPCommandHandler, command: MCPCommand) -> Tuple[bool, Union[str, Dict[str, object]]]:
        """Execute enhance command"""
        # Get current prompt

        current_prompt = st.session_state.get("current_user_input", "")
        if not current_prompt:
            return False, "No prompt to enhance. Please enter a prompt first."

        try:
            enhanced = self.mcp_client.get_prompt("prompt_enhancement", {"original_prompt": current_prompt})

            if enhanced:
                return True, {
                    "type": "enhanced_prompt",
                    "original": current_prompt,
                    "enhanced": enhanced,
                }
            else:
                return False, "Failed to enhance prompt"

        except (AttributeError, ValueError, KeyError, TypeError, OSError) as e:
            logger.error("Enhancement error: %s", e)
            return False, f"Enhancement failed: {str(e)}"

    def _execute_analyze(self: MCPCommandHandler, command: MCPCommand) -> Tuple[bool, Union[str, Dict[str, object]]]:
        """Execute analyze command"""
        # Get current prompt

        current_prompt = st.session_state.get("current_user_input", "")
        if not current_prompt:
            return False, "No prompt to analyze. Please enter a prompt first."

        try:
            # Get analysis from multiple perspectives
            analyses = {}

            # Security analysis
            security_analysis = self.mcp_client.get_prompt("security_analysis", {"prompt": current_prompt})
            if security_analysis:
                analyses["security"] = security_analysis

            # Bias analysis
            bias_analysis = self.mcp_client.get_prompt(
                "bias_detection",
                {
                    "focus_area": "general",
                    "category": "implicit",
                    "test_prompt": current_prompt,
                },
            )
            if bias_analysis:
                analyses["bias"] = bias_analysis

            return True, {
                "type": "analysis_results",
                "prompt": current_prompt,
                "analyses": analyses,
            }

        except (AttributeError, ValueError, KeyError, TypeError, OSError) as e:
            logger.error("Analysis error: %s", e)
            return False, f"Analysis failed: {str(e)}"

    def _execute_resources(self: MCPCommandHandler, command: MCPCommand) -> Tuple[bool, Union[str, Dict[str, object]]]:
        """Execute resources command"""
        try:

            # Get available resources
            resources = self.mcp_client.list_resources()

            # Categorize resources
            categorized: dict[str, list] = {
                "datasets": [],
                "prompts": [],
                "config": [],
                "other": [],
            }

            for resource in resources:
                resource_dict = cast(Dict[str, Any], resource)
                resource_uri = str(resource_dict.get("uri", ""))
                if "datasets" in resource_uri:
                    categorized["datasets"].append(resource)
                elif "prompts" in resource_uri:
                    categorized["prompts"].append(resource)
                elif "config" in resource_uri:
                    categorized["config"].append(resource)
                else:
                    categorized["other"].append(resource)

            return True, {
                "type": "resource_list",
                "total": len(resources),
                "categories": categorized,
            }

        except (AttributeError, ValueError, KeyError, TypeError, OSError) as e:
            logger.error("Resource listing error: %s", e)
            return False, f"Failed to list resources: {str(e)}"

    def _execute_prompt(self: MCPCommandHandler, command: MCPCommand) -> Tuple[bool, Union[str, Dict[str, object]]]:
        """Execute prompt command"""
        prompt_name = (command.arguments or {}).get("prompt_name", "")

        if not prompt_name:
            # List available prompts
            prompts = self.mcp_client.list_prompts()
            return True, {"type": "prompt_list", "prompts": prompts}

        # Try to get specific prompt
        try:
            # Get prompt with minimal required arguments
            prompt_args = self._get_default_prompt_args(prompt_name)
            prompt_args_cast = cast(Dict[str, object], prompt_args)
            rendered = self.mcp_client.get_prompt(prompt_name, prompt_args_cast)

            if rendered:
                return True, {
                    "type": "prompt_rendered",
                    "name": prompt_name,
                    "content": rendered,
                }
            else:
                return False, f"Failed to get prompt: {prompt_name}"

        except (AttributeError, ValueError, KeyError, TypeError, OSError) as e:
            logger.error("Prompt retrieval error: %s", e)
            return False, f"Failed to get prompt: {str(e)}"

    def _get_default_prompt_args(self: MCPCommandHandler, prompt_name: str) -> Dict[str, Union[str, List[str]]]:
        """Get default arguments for a prompt"""
        # Define default arguments for known prompts

        defaults = {
            "jailbreak_test": {
                "scenario": "Test scenario",
                "target_query": "Test query",
                "persona": "security tester",
            },
            "bias_detection": {
                "focus_area": "general",
                "category": "implicit",
                "test_prompt": "Test prompt",
            },
            "capability_test": {
                "assessment_type": "reasoning",
                "domain": "general",
                "task_description": "Test task",
                "test_content": "Test content",
                "criteria": ["accuracy", "completeness"],
            },
        }

        result = defaults.get(prompt_name, {})
        if not isinstance(result, dict):
            return {}
        return result


def format_command_result(result: Union[str, Dict[str, object], object]) -> str:
    """Format command result for display"""
    if isinstance(result, str):

        return result

    if isinstance(result, dict):
        result_type = result.get("type", "unknown")

        if result_type == "test_result":
            test_type = result.get("test_type", "unknown")
            prompt = str(result.get("prompt", ""))[:500]
            return f"""**Test Generated: {test_type}**



{prompt}...

"""
        elif result_type == "dataset_loaded":

            name = result.get("name", "Unknown")
            size = result.get("size", "N/A")
            preview = result.get("preview", "No preview")
            return f"""**Dataset Loaded: {name}**



Size: {size}
Preview: {preview}

"""
        elif result_type == "enhanced_prompt":

            enhanced = result.get("enhanced", "No enhanced prompt")
            return f"""**Enhanced Prompt:**



{enhanced}

"""
        elif result_type == "analysis_results":

            output = "**Analysis Results:**\n\n"
            analyses = result.get("analyses", {})
            if isinstance(analyses, dict):
                for analysis_type, content in analyses.items():
                    content_str = str(content)[:300]
                    output += f"**{str(analysis_type).title()}:**\n{content_str}...\n\n"
            return output

        elif result_type == "resource_list":
            total = result.get("total", 0)
            output = f"**Available Resources ({total} total):**\n\n"
            categories = result.get("categories", {})
            if isinstance(categories, dict):
                for category, resources in categories.items():
                    if resources and isinstance(resources, list):
                        output += f"**{str(category).title()} ({len(resources)}):**\n"
                        for resource in resources[:3]:
                            name = getattr(resource, "name", str(resource))
                            output += f"• {name}\n"
                        if len(resources) > 3:
                            output += f"  ...and {len(resources) - 3} more\n"
                        output += "\n"
            return output

        elif result_type == "prompt_list":
            output = "**Available Prompts:**\n\n"
            prompts = result.get("prompts", [])
            if isinstance(prompts, list):
                for prompt in prompts[:10]:
                    name = "Unknown"
                    desc = "No description"
                    if hasattr(prompt, "name"):
                        name = prompt.name
                    elif isinstance(prompt, dict):
                        name = prompt.get("name", "Unknown")

                    if hasattr(prompt, "description"):
                        desc = prompt.description
                    elif isinstance(prompt, dict):
                        desc = prompt.get("description", "No description")

                    output += f"• `{name}` - {desc}\n"
            return output

        elif result_type == "prompt_rendered":
            name = result.get("name", "Unknown")
            content = result.get("content", "No content")
            return f"""**Prompt: {name}**



{content}

"""
        elif result_type == "dataset_list":

            output = "**Available Datasets:**\n\n"
            datasets = result.get("datasets", {})
            if isinstance(datasets, dict):
                for source, dataset_list in datasets.items():
                    if dataset_list and isinstance(dataset_list, list):
                        output += f"**{str(source).title()} Datasets:**\n"
                        for dataset in dataset_list[:5]:
                            name = "Unknown"
                            if isinstance(dataset, dict):
                                name = dataset.get("name", "Unknown")
                            elif hasattr(dataset, "name"):
                                name = dataset.name
                            output += f"• {name}\n"
                        output += "\n"
            return output

    # Fallback to string representation
    return str(result)
