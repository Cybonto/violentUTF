"""
General Testing Prompts for MCP
===============================

This module provides general-purpose prompts for AI system testing,
capability assessment, and quality evaluation.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from app.mcp.prompts.base import (BasePrompt, DynamicPrompt, PromptArgument,
                                  StaticPrompt, prompt_registry)

logger = logging.getLogger(__name__)


class CapabilityTestPrompt(StaticPrompt):
    """Test AI system capabilities and limitations"""

    def __init__(self):
        template = """AI Capability Assessment Test

**Assessment Type:** {{ assessment_type }}
**Capability Domain:** {{ domain }}

**Test Instructions:**
You are evaluating an AI system's capabilities in {{ domain }}. Please assess the target AI's performance on the following task:

**Task Description:**
{{ task_description }}

**Specific Test:**
{{ test_content }}

**Evaluation Criteria:**
{% for criterion in criteria %}
- {{ criterion }}
{% endfor %}

**Expected Skill Level:** {{ skill_level | default("intermediate") }}

**Success Metrics:**
- Accuracy: {{ accuracy_target | default("80%") }}
- Completeness: {{ completeness_target | default("high") }}
- Relevance: {{ relevance_target | default("high") }}

**Test Prompt:**
{{ test_content }}

Please evaluate the response based on the criteria above."""

        super().__init__(
            name="capability_test",
            description="Assess AI system capabilities in specific domains",
            template=template,
            category="testing",
        )

        self.add_argument(
            PromptArgument(
                name="assessment_type",
                description="Type of capability assessment",
                type="string",
                required=True,
                enum=[
                    "reasoning",
                    "knowledge",
                    "creativity",
                    "problem_solving",
                    "communication",
                ],
            )
        )

        self.add_argument(
            PromptArgument(
                name="domain",
                description="The domain being tested",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="task_description",
                description="Description of the task",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="test_content",
                description="The actual test content or question",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="criteria",
                description="List of evaluation criteria",
                type="array",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="skill_level",
                description="Expected skill level",
                type="string",
                enum=["beginner", "intermediate", "advanced", "expert"],
                default="intermediate",
            )
        )

        self.add_argument(
            PromptArgument(
                name="accuracy_target",
                description="Target accuracy level",
                type="string",
                default="80%",
            )
        )

        self.add_argument(
            PromptArgument(
                name="completeness_target",
                description="Target completeness level",
                type="string",
                default="high",
            )
        )

        self.add_argument(
            PromptArgument(
                name="relevance_target",
                description="Target relevance level",
                type="string",
                default="high",
            )
        )


class ReasoningTestPrompt(StaticPrompt):
    """Test logical reasoning and problem-solving abilities"""

    def __init__(self):
        template = """Logical Reasoning Assessment

**Reasoning Type:** {{ reasoning_type }}
**Complexity Level:** {{ complexity }}

**Problem Statement:**
{{ problem_statement }}

**Context Information:**
{{ context | default("No additional context provided") }}

**Reasoning Challenge:**
Please solve the following problem step by step:

{{ reasoning_challenge }}

**Required Approach:**
1. Identify the key elements
2. Apply {{ reasoning_type }} reasoning
3. Show your work clearly
4. Provide a final answer
5. Explain your confidence level

**Additional Constraints:**
{% for constraint in constraints %}
- {{ constraint }}
{% endfor %}

**Evaluation Focus:**
- Logical consistency
- Step-by-step reasoning
- Accuracy of conclusions
- Clarity of explanation"""

        super().__init__(
            name="reasoning_test",
            description="Test logical reasoning and problem-solving capabilities",
            template=template,
            category="testing",
        )

        self.add_argument(
            PromptArgument(
                name="reasoning_type",
                description="Type of reasoning to test",
                type="string",
                required=True,
                enum=["deductive", "inductive", "abductive", "analogical", "causal"],
            )
        )

        self.add_argument(
            PromptArgument(
                name="complexity",
                description="Complexity level of the reasoning task",
                type="string",
                required=True,
                enum=["simple", "moderate", "complex", "expert"],
            )
        )

        self.add_argument(
            PromptArgument(
                name="problem_statement",
                description="The problem to be solved",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="reasoning_challenge",
                description="The specific reasoning challenge",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="context",
                description="Additional context for the problem",
                type="string",
                default="No additional context provided",
            )
        )

        self.add_argument(
            PromptArgument(
                name="constraints",
                description="Additional constraints or requirements",
                type="array",
                default=[],
            )
        )


class CreativityTestPrompt(StaticPrompt):
    """Test creative and generative capabilities"""

    def __init__(self):
        template = """Creativity Assessment Test

**Creative Task Type:** {{ task_type }}
**Domain:** {{ domain }}
**Creativity Level:** {{ creativity_level }}

**Creative Challenge:**
{{ challenge_description }}

**Specific Requirements:**
{% for requirement in requirements %}
- {{ requirement }}
{% endfor %}

**Creative Constraints:**
{% for constraint in constraints %}
- {{ constraint }}
{% endfor %}

**Quality Criteria:**
- Originality: How unique and novel is the output?
- Relevance: How well does it meet the requirements?
- Quality: How well-executed is the creative work?
- Coherence: How well does everything fit together?

**Creative Prompt:**
{{ creative_prompt }}

**Evaluation Notes:**
Please assess the response for creativity, originality, and adherence to requirements."""

        super().__init__(
            name="creativity_test",
            description="Test creative and generative capabilities",
            template=template,
            category="testing",
        )

        self.add_argument(
            PromptArgument(
                name="task_type",
                description="Type of creative task",
                type="string",
                required=True,
                enum=[
                    "storytelling",
                    "ideation",
                    "design",
                    "writing",
                    "problem_solving",
                    "artistic",
                ],
            )
        )

        self.add_argument(
            PromptArgument(
                name="domain",
                description="The creative domain",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="creativity_level",
                description="Expected level of creativity",
                type="string",
                required=True,
                enum=["basic", "moderate", "high", "exceptional"],
            )
        )

        self.add_argument(
            PromptArgument(
                name="challenge_description",
                description="Description of the creative challenge",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="creative_prompt",
                description="The actual creative prompt",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="requirements",
                description="Specific requirements for the creative output",
                type="array",
                default=[],
            )
        )

        self.add_argument(
            PromptArgument(
                name="constraints",
                description="Creative constraints to work within",
                type="array",
                default=[],
            )
        )


class KnowledgeTestPrompt(StaticPrompt):
    """Test knowledge and factual accuracy"""

    def __init__(self):
        template = """Knowledge Assessment Test

**Knowledge Domain:** {{ domain }}
**Question Type:** {{ question_type }}
**Difficulty Level:** {{ difficulty }}

**Knowledge Area:** {{ knowledge_area }}

**Assessment Instructions:**
Please answer the following question(s) about {{ domain }}. Provide accurate, detailed information and cite sources when possible.

**Question:**
{{ question }}

**Required Elements:**
{% for element in required_elements %}
- {{ element }}
{% endfor %}

**Additional Context:**
{{ additional_context | default("No additional context") }}

**Evaluation Criteria:**
- Factual accuracy
- Completeness of answer
- Clarity of explanation
- Source credibility (if applicable)
- Up-to-date information

**Expected Response Format:** {{ response_format | default("Detailed explanation with examples") }}"""

        super().__init__(
            name="knowledge_test",
            description="Test knowledge and factual accuracy in specific domains",
            template=template,
            category="testing",
        )

        self.add_argument(
            PromptArgument(
                name="domain",
                description="The knowledge domain to test",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="question_type",
                description="Type of knowledge question",
                type="string",
                required=True,
                enum=[
                    "factual",
                    "conceptual",
                    "procedural",
                    "analytical",
                    "comparative",
                ],
            )
        )

        self.add_argument(
            PromptArgument(
                name="difficulty",
                description="Difficulty level of the question",
                type="string",
                required=True,
                enum=["basic", "intermediate", "advanced", "expert"],
            )
        )

        self.add_argument(
            PromptArgument(
                name="knowledge_area",
                description="Specific area within the domain",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="question",
                description="The knowledge question to ask",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="required_elements",
                description="Required elements in the response",
                type="array",
                default=[],
            )
        )

        self.add_argument(
            PromptArgument(
                name="additional_context",
                description="Additional context for the question",
                type="string",
                default="No additional context",
            )
        )

        self.add_argument(
            PromptArgument(
                name="response_format",
                description="Expected format of the response",
                type="string",
                default="Detailed explanation with examples",
            )
        )


class ConversationTestPrompt(StaticPrompt):
    """Test conversational abilities and communication skills"""

    def __init__(self):
        template = """Conversational Skills Assessment

**Conversation Type:** {{ conversation_type }}
**Communication Style:** {{ communication_style }}
**Scenario:** {{ scenario }}

**Conversation Context:**
{{ context_description }}

**Role Instructions:**
You are testing an AI's conversational abilities. The AI should demonstrate:
- {{ communication_skills | join(", ") }}

**Conversation Starter:**
{{ conversation_starter }}

**Conversation Flow:**
{% for turn in conversation_turns %}
{{ loop.index }}. {{ turn }}
{% endfor %}

**Assessment Focus:**
- Natural conversation flow
- Appropriate responses
- Context maintenance
- Emotional intelligence (if applicable)
- Clarity and coherence

**Special Instructions:**
{{ special_instructions | default("Engage naturally and assess response quality") }}

**Evaluation Criteria:**
- Relevance of responses
- Conversational coherence
- Appropriate tone and style
- Information accuracy"""

        super().__init__(
            name="conversation_test",
            description="Test conversational abilities and communication skills",
            template=template,
            category="testing",
        )

        self.add_argument(
            PromptArgument(
                name="conversation_type",
                description="Type of conversation to test",
                type="string",
                required=True,
                enum=[
                    "casual",
                    "formal",
                    "technical",
                    "educational",
                    "supportive",
                    "persuasive",
                ],
            )
        )

        self.add_argument(
            PromptArgument(
                name="communication_style",
                description="Expected communication style",
                type="string",
                required=True,
                enum=[
                    "friendly",
                    "professional",
                    "academic",
                    "empathetic",
                    "direct",
                    "diplomatic",
                ],
            )
        )

        self.add_argument(
            PromptArgument(
                name="scenario",
                description="The conversation scenario",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="context_description",
                description="Description of the conversation context",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="conversation_starter",
                description="How to start the conversation",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="communication_skills",
                description="Communication skills to assess",
                type="array",
                default=["active listening", "clear expression", "appropriate tone"],
            )
        )

        self.add_argument(
            PromptArgument(
                name="conversation_turns",
                description="Planned conversation turns",
                type="array",
                default=[],
            )
        )

        self.add_argument(
            PromptArgument(
                name="special_instructions",
                description="Special instructions for the conversation",
                type="string",
                default="Engage naturally and assess response quality",
            )
        )


class BenchmarkTestPrompt(DynamicPrompt):
    """Advanced benchmark testing with dynamic comparison"""

    def __init__(self):
        template = """AI System Benchmark Assessment

**Benchmark Suite:** {{ benchmark_name }}
**Test Category:** {{ category }}
**Comparison Target:** {{ comparison_target | default("Industry standard") }}

**Dynamic Context:**
- Test timestamp: {{ timestamp }}
- Benchmark version: {{ benchmark_version }}
- Previous scores: {{ previous_scores | length }} recorded

**Benchmark Task:**
{{ task_description }}

**Performance Metrics:**
{% for metric in metrics %}
- {{ metric.name }}: Target {{ metric.target }}
{% endfor %}

**Test Instructions:**
{{ test_instructions }}

**Evaluation Framework:**
1. Quantitative scoring
2. Qualitative assessment  
3. Comparative analysis
4. Performance trending

**Expected Output Format:**
{{ output_format }}"""

        super().__init__(
            name="benchmark_test",
            description="Advanced benchmark testing with performance tracking",
            template=template,
            context_provider=self._get_benchmark_context,
            category="testing",
        )

        self.add_argument(
            PromptArgument(
                name="benchmark_name",
                description="Name of the benchmark suite",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="category",
                description="Benchmark category",
                type="string",
                required=True,
                enum=[
                    "language",
                    "reasoning",
                    "knowledge",
                    "math",
                    "coding",
                    "creative",
                ],
            )
        )

        self.add_argument(
            PromptArgument(
                name="task_description",
                description="Description of the benchmark task",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="test_instructions",
                description="Specific instructions for the test",
                type="string",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="metrics",
                description="Performance metrics to track",
                type="array",
                required=True,
            )
        )

        self.add_argument(
            PromptArgument(
                name="comparison_target",
                description="What to compare performance against",
                type="string",
                default="Industry standard",
            )
        )

        self.add_argument(
            PromptArgument(
                name="output_format",
                description="Expected format for the output",
                type="string",
                required=True,
            )
        )

    async def _get_benchmark_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get dynamic context for benchmark testing"""
        return {
            "timestamp": datetime.now().isoformat(),
            "benchmark_version": "2024.1",
            "previous_scores": [],
            "test_environment": {"system": "ViolentUTF MCP", "version": "1.0.0"},
        }


# Register all testing prompts
def register_testing_prompts():
    """Register all general testing prompts"""
    prompt_registry.register(CapabilityTestPrompt())
    prompt_registry.register(ReasoningTestPrompt())
    prompt_registry.register(CreativityTestPrompt())
    prompt_registry.register(KnowledgeTestPrompt())
    prompt_registry.register(ConversationTestPrompt())
    prompt_registry.register(BenchmarkTestPrompt())

    logger.info("Registered 6 general testing prompts")


# Auto-register when module is imported
register_testing_prompts()
