# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
MCP Command Handler for Phase 3 UI Implementation
=================================================

This module provides command execution and management for the
Smart Commands & Natural Language Interface in Simple Chat.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

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
    """Manages command history with persistence"""

    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self._history: List[Dict[str, Any]] = []

    def add(self, command: str, result: Any, success: bool = True):
        """Add command to history"""
        entry = {"command": command, "result": result, "success": success, "timestamp": datetime.now().isoformat()}
        self._history.append(entry)

        # Maintain max history size
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history :]

    def get_recent(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent command history"""
        return self._history[-count:]

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search command history"""
        results = []
        query_lower = query.lower()
        for entry in self._history:
            if query_lower in entry["command"].lower():
                results.append(entry)
        return results

    def clear(self):
        """Clear command history"""
        self._history = []


class MCPCommandHandler:
    """Handles MCP command execution and management"""

    def __init__(self, mcp_client: MCPClientSync):
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

    def execute_command(self, command_text: str) -> Tuple[bool, Any]:
        """Execute an MCP command and return result"""
        try:
            # Parse command
            command = self.parser.parse(command_text)

            if command.type == MCPCommandType.UNKNOWN:
                return False, "Unknown command. Type '/mcp help' for available commands."

            # Execute command
            executor = self._executors.get(command.type)
            if not executor:
                return False, f"No executor for command type: {command.type.value}"

            # Execute and track history
            success, result = executor(command)
            self.history.add(command_text, result, success)

            return success, result

        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return False, f"Error executing command: {str(e)}"

    def get_command_suggestions(self, partial_text: str) -> List[str]:
        """Get command suggestions for autocomplete"""
        suggestions = self.parser.suggest_command(partial_text)

        # Add history-based suggestions
        if len(suggestions) < 5:
            history_matches = self.history.search(partial_text)
            for entry in history_matches[:3]:
                if entry["command"] not in suggestions:
                    suggestions.append(entry["command"])

        return suggestions[:5]  # Return top 5 suggestions

    # Command Executors

    def _execute_help(self, command: MCPCommand) -> Tuple[bool, str]:
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

    def _execute_test(self, command: MCPCommand) -> Tuple[bool, Any]:
        """Execute test command"""
        test_type = command.arguments.get("test_type", "jailbreak")

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
                return False, f"Test execution failed: {result.get('error', 'Unknown error')}"

        except Exception as e:
            logger.error(f"Test execution error: {e}")
            return False, f"Failed to execute test: {str(e)}"

    def _execute_dataset(self, command: MCPCommand) -> Tuple[bool, Any]:
        """Execute dataset command"""
        dataset_name = command.arguments.get("dataset_name", "")

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
                "preview": dataset[:3] if isinstance(dataset, list) else str(dataset)[:200],
            }
        else:
            return False, f"Failed to load dataset: {dataset_name}"

    def _execute_enhance(self, command: MCPCommand) -> Tuple[bool, Any]:
        """Execute enhance command"""
        # Get current prompt
        current_prompt = st.session_state.get("current_user_input", "")
        if not current_prompt:
            return False, "No prompt to enhance. Please enter a prompt first."

        try:
            enhanced = self.mcp_client.get_prompt("prompt_enhancement", {"original_prompt": current_prompt})

            if enhanced:
                return True, {"type": "enhanced_prompt", "original": current_prompt, "enhanced": enhanced}
            else:
                return False, "Failed to enhance prompt"

        except Exception as e:
            logger.error(f"Enhancement error: {e}")
            return False, f"Enhancement failed: {str(e)}"

    def _execute_analyze(self, command: MCPCommand) -> Tuple[bool, Any]:
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
                "bias_detection", {"focus_area": "general", "category": "implicit", "test_prompt": current_prompt}
            )
            if bias_analysis:
                analyses["bias"] = bias_analysis

            return True, {"type": "analysis_results", "prompt": current_prompt, "analyses": analyses}

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return False, f"Analysis failed: {str(e)}"

    def _execute_resources(self, command: MCPCommand) -> Tuple[bool, Any]:
        """Execute resources command"""
        try:
            # Get available resources
            resources = self.mcp_client.list_resources()

            # Categorize resources
            categorized = {"datasets": [], "prompts": [], "config": [], "other": []}

            for resource in resources:
                if "datasets" in resource.uri:
                    categorized["datasets"].append(resource)
                elif "prompts" in resource.uri:
                    categorized["prompts"].append(resource)
                elif "config" in resource.uri:
                    categorized["config"].append(resource)
                else:
                    categorized["other"].append(resource)

            return True, {"type": "resource_list", "total": len(resources), "categories": categorized}

        except Exception as e:
            logger.error(f"Resource listing error: {e}")
            return False, f"Failed to list resources: {str(e)}"

    def _execute_prompt(self, command: MCPCommand) -> Tuple[bool, Any]:
        """Execute prompt command"""
        prompt_name = command.arguments.get("prompt_name", "")

        if not prompt_name:
            # List available prompts
            prompts = self.mcp_client.list_prompts()
            return True, {"type": "prompt_list", "prompts": prompts}

        # Try to get specific prompt
        try:
            # Get prompt with minimal required arguments
            prompt_args = self._get_default_prompt_args(prompt_name)
            rendered = self.mcp_client.get_prompt(prompt_name, prompt_args)

            if rendered:
                return True, {"type": "prompt_rendered", "name": prompt_name, "content": rendered}
            else:
                return False, f"Failed to get prompt: {prompt_name}"

        except Exception as e:
            logger.error(f"Prompt retrieval error: {e}")
            return False, f"Failed to get prompt: {str(e)}"

    def _get_default_prompt_args(self, prompt_name: str) -> Dict[str, Any]:
        """Get default arguments for a prompt"""
        # Define default arguments for known prompts
        defaults = {
            "jailbreak_test": {"scenario": "Test scenario", "target_query": "Test query", "persona": "security tester"},
            "bias_detection": {"focus_area": "general", "category": "implicit", "test_prompt": "Test prompt"},
            "capability_test": {
                "assessment_type": "reasoning",
                "domain": "general",
                "task_description": "Test task",
                "test_content": "Test content",
                "criteria": ["accuracy", "completeness"],
            },
        }

        return defaults.get(prompt_name, {})


def format_command_result(result: Any) -> str:
    """Format command result for display"""
    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        result_type = result.get("type", "unknown")

        if result_type == "test_result":
            return f"""**Test Generated: {result['test_type']}**

{result['prompt'][:500]}...
"""

        elif result_type == "dataset_loaded":
            return f"""**Dataset Loaded: {result['name']}**

Size: {result['size']}
Preview: {result['preview']}
"""

        elif result_type == "enhanced_prompt":
            return f"""**Enhanced Prompt:**

{result['enhanced']}
"""

        elif result_type == "analysis_results":
            output = "**Analysis Results:**\n\n"
            for analysis_type, content in result.get("analyses", {}).items():
                output += f"**{analysis_type.title()}:**\n{content[:300]}...\n\n"
            return output

        elif result_type == "resource_list":
            output = f"**Available Resources ({result['total']} total):**\n\n"
            for category, resources in result.get("categories", {}).items():
                if resources:
                    output += f"**{category.title()} ({len(resources)}):**\n"
                    for resource in resources[:3]:
                        output += f"• {resource.name}\n"
                    if len(resources) > 3:
                        output += f"  ...and {len(resources) - 3} more\n"
                    output += "\n"
            return output

        elif result_type == "prompt_list":
            output = "**Available Prompts:**\n\n"
            for prompt in result.get("prompts", [])[:10]:
                name = prompt.name if hasattr(prompt, "name") else prompt.get("name", "Unknown")
                desc = (
                    prompt.description
                    if hasattr(prompt, "description")
                    else prompt.get("description", "No description")
                )
                output += f"• `{name}` - {desc}\n"
            return output

        elif result_type == "prompt_rendered":
            return f"""**Prompt: {result['name']}**

{result['content']}
"""

        elif result_type == "dataset_list":
            output = "**Available Datasets:**\n\n"
            datasets = result.get("datasets", {})
            for source, dataset_list in datasets.items():
                if dataset_list:
                    output += f"**{source.title()} Datasets:**\n"
                    for dataset in dataset_list[:5]:
                        name = dataset.get("name", "Unknown")
                        output += f"• {name}\n"
                    output += "\n"
            return output

    # Fallback to string representation
    return str(result)
