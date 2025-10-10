# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Specialized Dataset Configuration Interfaces for ViolentUTF

This module provides domain-specific configuration interfaces for different
types of native datasets, ensuring optimal setup for each evaluation domain.
"""

import logging
from typing import Any, Dict, Optional

import streamlit as st

logger = logging.getLogger(__name__)


class SpecializedConfigurationInterface:
    """Specialized configuration interfaces for different dataset domains"""

    def __init__(self) -> None:
        """Initialize the configuration interface"""
        # Initialize session state for configurations
        if "dataset_configurations" not in st.session_state:
            st.session_state.dataset_configurations = {}

    def render_configuration_interface(self, dataset_name: str, dataset_type: str) -> Dict[str, Any]:
        """Render specialized configuration based on dataset type"""
        logger.info("Rendering configuration for %s (type: %s)", dataset_name, dataset_type)

        if dataset_type == "cognitive_behavioral":
            return self.render_cognitive_configuration(dataset_name)
        elif dataset_type == "redteaming":
            return self.render_redteaming_configuration(dataset_name)
        elif dataset_type == "legal_reasoning":
            return self.render_legal_configuration(dataset_name)
        elif dataset_type == "mathematical_reasoning":
            return self.render_mathematical_configuration(dataset_name)
        elif dataset_type == "spatial_reasoning":
            return self.render_spatial_configuration(dataset_name)
        elif dataset_type == "privacy_evaluation":
            return self.render_privacy_configuration(dataset_name)
        elif dataset_type == "meta_evaluation":
            return self.render_meta_evaluation_configuration(dataset_name)
        else:
            return self.render_generic_configuration(dataset_name)

    def render_cognitive_configuration(self, dataset_name: str) -> Dict[str, Any]:
        """Render cognitive behavioral assessment configuration"""
        st.subheader("🧠 Cognitive Assessment Configuration")

        col1, col2 = st.columns(2)

        with col1:
            # Question type selection
            question_types = st.multiselect(
                "Question Types",
                ["WCP", "WHO", "TeamRisk", "TargetFactor"],
                default=["WCP", "WHO"],
                help="Select which question types to include in evaluation",
                key=f"cog_question_types_{dataset_name}",
            )

            # Scenario limit
            scenario_limit = st.selectbox(
                "Scenario Limit",
                [1000, 10000, 50000, "All scenarios"],
                index=1,
                help="Number of scenarios to include (679,996 total available)",
                key=f"cog_scenario_limit_{dataset_name}",
            )

        with col2:
            # Cognitive focus areas
            focus_areas = st.multiselect(
                "Cognitive Focus Areas",
                ["Risk Assessment", "Behavioral Analysis", "Compliance Evaluation", "Team Dynamics"],
                default=["Risk Assessment", "Compliance Evaluation"],
                help="Specific cognitive areas to emphasize",
                key=f"cog_focus_areas_{dataset_name}",
            )

            # Difficulty level filtering
            difficulty_levels = st.multiselect(
                "Difficulty Levels",
                ["basic", "medium", "high", "expert"],
                default=["medium", "high"],
                help="Select difficulty levels to include",
                key=f"cog_difficulty_{dataset_name}",
            )

        # Advanced options
        with st.expander("🔧 Advanced Cognitive Options"):
            include_metadata = st.checkbox(
                "Include Question Metadata",
                value=True,
                help="Include metadata like complexity scores and validation status",
                key=f"cog_metadata_{dataset_name}",
            )

            randomize_order = st.checkbox(
                "Randomize Question Order",
                value=True,
                help="Randomize the order of questions for evaluation",
                key=f"cog_randomize_{dataset_name}",
            )

            cognitive_bias_analysis = st.checkbox(
                "Enable Cognitive Bias Analysis",
                value=False,
                help="Include analysis of cognitive biases in responses",
                key=f"cog_bias_analysis_{dataset_name}",
            )

        return {
            "question_types": question_types,
            "scenario_limit": scenario_limit,
            "focus_areas": focus_areas,
            "difficulty_levels": difficulty_levels,
            "include_metadata": include_metadata,
            "randomize_order": randomize_order,
            "cognitive_bias_analysis": cognitive_bias_analysis,
        }

    def render_redteaming_configuration(self, dataset_name: str) -> Dict[str, Any]:
        """Render red-teaming dataset configuration"""
        st.subheader("🔴 Red-Teaming Configuration")

        col1, col2 = st.columns(2)

        with col1:
            # Attack type selection
            attack_types = st.multiselect(
                "Attack Types",
                ["jailbreak", "prompt_injection", "data_extraction", "bias_amplification", "manipulation"],
                default=["jailbreak", "prompt_injection"],
                help="Select types of attacks to include",
                key=f"red_attack_types_{dataset_name}",
            )

            # Severity filtering
            min_severity = st.selectbox(
                "Minimum Severity Level",
                ["low", "medium", "high", "critical"],
                index=1,
                help="Filter attacks by minimum severity level",
                key=f"red_min_severity_{dataset_name}",
            )

        with col2:
            # Target model types
            target_models = st.multiselect(
                "Target Model Types",
                ["language_model", "chat_assistant", "code_assistant", "multimodal", "specialized"],
                default=["language_model", "chat_assistant"],
                help="Select types of models to target",
                key=f"red_target_models_{dataset_name}",
            )

            # Evaluation mode
            evaluation_mode = st.selectbox(
                "Evaluation Mode",
                ["Automated", "Human-in-the-loop", "Hybrid"],
                index=0,
                help="Mode for evaluating attack success",
                key=f"red_eval_mode_{dataset_name}",
            )

        # Advanced red-teaming options
        with st.expander("🔧 Advanced Red-Teaming Options"):
            success_rate_threshold = st.slider(
                "Success Rate Threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.1,
                step=0.05,
                help="Minimum success rate for including attacks",
                key=f"red_success_threshold_{dataset_name}",
            )

            include_defenses = st.checkbox(
                "Include Defense Analysis",
                value=True,
                help="Include analysis of potential defenses",
                key=f"red_defenses_{dataset_name}",
            )

            ethical_constraints = st.checkbox(
                "Apply Ethical Constraints",
                value=True,
                help="Apply ethical guidelines to attack selection",
                key=f"red_ethics_{dataset_name}",
            )

        return {
            "attack_types": attack_types,
            "min_severity": min_severity,
            "target_models": target_models,
            "evaluation_mode": evaluation_mode,
            "success_rate_threshold": success_rate_threshold,
            "include_defenses": include_defenses,
            "ethical_constraints": ethical_constraints,
        }

    def render_legal_configuration(self, dataset_name: str) -> Dict[str, Any]:
        """Render legal reasoning configuration"""
        st.subheader("⚖️ Legal Reasoning Configuration")

        col1, col2 = st.columns(2)

        with col1:
            # Legal domain selection
            legal_domains = st.multiselect(
                "Legal Domains",
                ["contract", "constitutional", "criminal", "tort", "administrative", "international"],
                default=["contract", "constitutional"],
                help="Select legal domains to include",
                key=f"legal_domains_{dataset_name}",
            )

            # Complexity level
            complexity_levels = st.multiselect(
                "Complexity Levels",
                ["basic", "intermediate", "advanced", "expert"],
                default=["intermediate", "advanced"],
                help="Select complexity levels for legal reasoning",
                key=f"legal_complexity_{dataset_name}",
            )

        with col2:
            # Jurisdiction focus
            jurisdiction = st.selectbox(
                "Primary Jurisdiction",
                ["US Federal", "US State", "EU", "UK", "International", "Mixed"],
                index=0,
                help="Primary legal jurisdiction focus",
                key=f"legal_jurisdiction_{dataset_name}",
            )

            # Analysis type
            analysis_type = st.selectbox(
                "Analysis Type",
                ["Case Analysis", "Statutory Interpretation", "Precedent Application", "Policy Analysis"],
                index=0,
                help="Type of legal analysis to focus on",
                key=f"legal_analysis_{dataset_name}",
            )

        # Advanced legal options
        with st.expander("🔧 Advanced Legal Options"):
            include_citations = st.checkbox(
                "Include Legal Citations",
                value=True,
                help="Include legal citations and references",
                key=f"legal_citations_{dataset_name}",
            )

            ethical_considerations = st.checkbox(
                "Include Ethical Considerations",
                value=True,
                help="Include professional ethics considerations",
                key=f"legal_ethics_{dataset_name}",
            )

            bias_detection = st.checkbox(
                "Enable Bias Detection",
                value=False,
                help="Detect potential biases in legal reasoning",
                key=f"legal_bias_{dataset_name}",
            )

        return {
            "legal_domains": legal_domains,
            "complexity_levels": complexity_levels,
            "jurisdiction": jurisdiction,
            "analysis_type": analysis_type,
            "include_citations": include_citations,
            "ethical_considerations": ethical_considerations,
            "bias_detection": bias_detection,
        }

    def render_mathematical_configuration(self, dataset_name: str) -> Dict[str, Any]:
        """Render mathematical reasoning configuration"""
        st.subheader("🔢 Mathematical Reasoning Configuration")

        col1, col2 = st.columns(2)

        with col1:
            # Math domain selection
            math_domains = st.multiselect(
                "Mathematical Domains",
                ["algebra", "geometry", "calculus", "statistics", "probability", "logic", "cryptography"],
                default=["algebra", "statistics", "probability"],
                help="Select mathematical domains to include",
                key=f"math_domains_{dataset_name}",
            )

            # Problem complexity
            problem_complexity = st.multiselect(
                "Problem Complexity",
                ["elementary", "intermediate", "advanced", "research"],
                default=["intermediate", "advanced"],
                help="Select complexity levels for mathematical problems",
                key=f"math_complexity_{dataset_name}",
            )

        with col2:
            # Application context
            application_context = st.selectbox(
                "Application Context",
                ["Pure Mathematics", "Applied Mathematics", "Computer Science", "Engineering", "Finance"],
                index=1,
                help="Context for mathematical applications",
                key=f"math_context_{dataset_name}",
            )

            # Solution format
            solution_format = st.selectbox(
                "Solution Format",
                ["Step-by-step", "Final Answer Only", "Proof Format", "Mixed"],
                index=0,
                help="Expected format for mathematical solutions",
                key=f"math_format_{dataset_name}",
            )

        # Advanced mathematical options
        with st.expander("🔧 Advanced Mathematical Options"):
            include_visualizations = st.checkbox(
                "Include Visualizations",
                value=False,
                help="Include mathematical visualizations when possible",
                key=f"math_viz_{dataset_name}",
            )

            symbolic_computation = st.checkbox(
                "Enable Symbolic Computation",
                value=True,
                help="Enable symbolic mathematical computation",
                key=f"math_symbolic_{dataset_name}",
            )

            numerical_precision = st.slider(
                "Numerical Precision",
                min_value=2,
                max_value=16,
                value=6,
                help="Decimal places for numerical answers",
                key=f"math_precision_{dataset_name}",
            )

        return {
            "math_domains": math_domains,
            "problem_complexity": problem_complexity,
            "application_context": application_context,
            "solution_format": solution_format,
            "include_visualizations": include_visualizations,
            "symbolic_computation": symbolic_computation,
            "numerical_precision": numerical_precision,
        }

    def render_spatial_configuration(self, dataset_name: str) -> Dict[str, Any]:
        """Render spatial reasoning configuration"""
        st.subheader("🗺️ Spatial Reasoning Configuration")

        col1, col2 = st.columns(2)

        with col1:
            # Spatial task types
            spatial_tasks = st.multiselect(
                "Spatial Task Types",
                ["navigation", "object_rotation", "spatial_memory", "graph_traversal", "pattern_recognition"],
                default=["navigation", "graph_traversal"],
                help="Select types of spatial reasoning tasks",
                key=f"spatial_tasks_{dataset_name}",
            )

            # Dimensionality
            dimensionality = st.selectbox(
                "Spatial Dimensionality",
                ["2D", "3D", "Mixed"],
                index=2,
                help="Dimensionality of spatial problems",
                key=f"spatial_dim_{dataset_name}",
            )

        with col2:
            # Complexity level
            spatial_complexity = st.selectbox(
                "Spatial Complexity",
                ["Simple", "Moderate", "Complex", "Expert"],
                index=1,
                help="Complexity level for spatial reasoning",
                key=f"spatial_complexity_{dataset_name}",
            )

            # Graph properties
            graph_properties = st.multiselect(
                "Graph Properties",
                ["directed", "undirected", "weighted", "cyclic", "hierarchical"],
                default=["directed", "weighted"],
                help="Properties of graph structures",
                key=f"spatial_graph_{dataset_name}",
            )

        return {
            "spatial_tasks": spatial_tasks,
            "dimensionality": dimensionality,
            "spatial_complexity": spatial_complexity,
            "graph_properties": graph_properties,
        }

    def render_privacy_configuration(self, dataset_name: str) -> Dict[str, Any]:
        """Render privacy evaluation configuration"""
        st.subheader("🔒 Privacy Evaluation Configuration")

        col1, col2 = st.columns(2)

        with col1:
            # Privacy tier selection
            privacy_tiers = st.multiselect(
                "Privacy Complexity Tiers",
                [1, 2, 3, 4],
                default=[1, 2],
                format_func=lambda x: f"Tier {x}: {self.get_tier_description(x)}",
                help="Select privacy complexity tiers for evaluation",
                key=f"privacy_tiers_{dataset_name}",
            )

            # Contextual Integrity focus
            ci_focus = st.selectbox(
                "Contextual Integrity Focus",
                ["General", "Healthcare", "Financial", "Educational", "Workplace"],
                help="Specific contextual domain focus",
                key=f"privacy_ci_{dataset_name}",
            )

        with col2:
            # Privacy evaluation mode
            evaluation_mode = st.selectbox(
                "Evaluation Mode",
                ["Sensitivity Classification", "Contextual Appropriateness", "Norm Compliance"],
                help="Primary privacy evaluation approach",
                key=f"privacy_mode_{dataset_name}",
            )

            # Privacy framework
            privacy_framework = st.selectbox(
                "Privacy Framework",
                ["Contextual Integrity", "GDPR", "CCPA", "HIPAA", "Mixed"],
                index=0,
                help="Privacy framework for evaluation",
                key=f"privacy_framework_{dataset_name}",
            )

        # Advanced privacy options
        with st.expander("🔧 Advanced Privacy Options"):
            include_edge_cases = st.checkbox(
                "Include Edge Cases",
                value=True,
                help="Include privacy edge cases and corner scenarios",
                key=f"privacy_edge_{dataset_name}",
            )

            cultural_sensitivity = st.checkbox(
                "Cultural Sensitivity Analysis",
                value=False,
                help="Include cultural context in privacy analysis",
                key=f"privacy_cultural_{dataset_name}",
            )

        return {
            "privacy_tiers": privacy_tiers,
            "contextual_integrity_focus": ci_focus,
            "evaluation_mode": evaluation_mode,
            "privacy_framework": privacy_framework,
            "include_edge_cases": include_edge_cases,
            "cultural_sensitivity": cultural_sensitivity,
        }

    def render_meta_evaluation_configuration(self, dataset_name: str) -> Dict[str, Any]:
        """Render meta-evaluation configuration"""
        st.subheader("👨‍⚖️ Meta-Evaluation Configuration")

        col1, col2 = st.columns(2)

        with col1:
            # Judge evaluation aspects
            judge_aspects = st.multiselect(
                "Judge Evaluation Aspects",
                ["accuracy", "consistency", "bias_detection", "reasoning_quality", "fairness"],
                default=["accuracy", "consistency", "bias_detection"],
                help="Aspects to evaluate in judge performance",
                key=f"meta_aspects_{dataset_name}",
            )

            # Evaluation methodology
            eval_methodology = st.selectbox(
                "Evaluation Methodology",
                ["Comparative", "Absolute", "Hybrid"],
                index=0,
                help="Methodology for meta-evaluation",
                key=f"meta_methodology_{dataset_name}",
            )

        with col2:
            # Judge types to evaluate
            judge_types = st.multiselect(
                "Judge Types",
                ["human_expert", "ai_model", "rule_based", "hybrid"],
                default=["human_expert", "ai_model"],
                help="Types of judges to evaluate",
                key=f"meta_judge_types_{dataset_name}",
            )

            # Benchmark standards
            benchmark_standard = st.selectbox(
                "Benchmark Standard",
                ["Gold Standard", "Expert Consensus", "Cross-Validation", "Custom"],
                index=0,
                help="Standard for benchmarking judge performance",
                key=f"meta_benchmark_{dataset_name}",
            )

        return {
            "judge_aspects": judge_aspects,
            "eval_methodology": eval_methodology,
            "judge_types": judge_types,
            "benchmark_standard": benchmark_standard,
        }

    def render_generic_configuration(self, dataset_name: str) -> Dict[str, Any]:
        """Render generic configuration for unknown dataset types"""
        st.subheader("⚙️ Generic Dataset Configuration")

        # Basic configuration options
        sample_size = st.slider(
            "Sample Size",
            min_value=100,
            max_value=10000,
            value=1000,
            step=100,
            help="Number of samples to include in evaluation",
            key=f"generic_sample_{dataset_name}",
        )

        randomize = st.checkbox(
            "Randomize Sample Order",
            value=True,
            help="Randomize the order of samples",
            key=f"generic_randomize_{dataset_name}",
        )

        return {"sample_size": sample_size, "randomize": randomize}

    def get_tier_description(self, tier: int) -> str:
        """Get description for privacy complexity tier"""
        descriptions = {
            1: "Basic privacy concepts",
            2: "Intermediate privacy scenarios",
            3: "Complex privacy contexts",
            4: "Advanced privacy analysis",
        }
        return descriptions.get(tier, "Unknown tier")

    def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration parameters"""
        validation_result: Dict[str, Any] = {"valid": True, "errors": [], "warnings": []}

        # Check for empty selections
        for key, value in config.items():
            if isinstance(value, list) and len(value) == 0:
                validation_result["errors"].append(f"{key} cannot be empty")
                validation_result["valid"] = False
            elif isinstance(value, (int, float)) and value < 0:
                validation_result["errors"].append(f"{key} must be non-negative")
                validation_result["valid"] = False

        # Domain-specific validation
        if "scenario_limit" in config and isinstance(config["scenario_limit"], int):
            if config["scenario_limit"] > 679996:
                validation_result["warnings"].append("Scenario limit exceeds available data")

        return validation_result

    def save_configuration(self, dataset_name: str, config: Dict[str, Any]) -> bool:
        """Save configuration for a dataset"""
        try:
            st.session_state.dataset_configurations[dataset_name] = config
            logger.info("Saved configuration for %s: %s", dataset_name, config)
            return True
        except Exception as e:
            logger.error("Failed to save configuration for %s: %s", dataset_name, e)
            return False

    def get_configuration(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """Get saved configuration for a dataset"""
        return st.session_state.dataset_configurations.get(dataset_name)
