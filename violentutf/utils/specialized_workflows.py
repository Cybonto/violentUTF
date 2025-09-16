# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Specialized Workflows and User Guidance System for ViolentUTF

This module provides user guidance systems, contextual help, and specialized
workflows to enhance the user experience for dataset selection and configuration.
"""

import logging
from typing import Any, Dict, List, Optional

import streamlit as st

logger = logging.getLogger(__name__)


class UserGuidanceSystem:
    """Comprehensive user guidance and help system"""

    def __init__(self) -> None:
        """Initialize the user guidance system"""
        # Initialize session state for guidance
        if "user_guidance_state" not in st.session_state:
            st.session_state.user_guidance_state = {
                "current_step": "start",
                "completed_steps": [],
                "user_type": "new_user",
                "guidance_enabled": True,
            }

        # Workflow step definitions
        self.workflow_steps = {
            1: "Select Dataset Category",
            2: "Choose Specific Dataset",
            3: "Configure Dataset Parameters",
            4: "Preview Dataset Content",
            5: "Setup Evaluation Workflow",
            6: "Execute Evaluation",
            7: "Review Results",
        }

        # Help content library
        self.help_content = self._initialize_help_content()

    def _initialize_help_content(self) -> Dict[str, Dict[str, str]]:
        """Initialize help content library"""
        return {
            "dataset_selection": {
                "general": """
                ## Dataset Selection Guide

                Choose datasets that match your evaluation goals:

                **🧠 Cognitive & Behavioral**: For evaluating decision-making and risk assessment
                **🔴 Red-Teaming & Security**: For adversarial testing and security validation
                **⚖️ Legal Reasoning**: For legal and regulatory compliance evaluation
                **🔢 Mathematical**: For quantitative reasoning and problem-solving
                **🗺️ Spatial**: For navigation and graph reasoning tasks
                **🔒 Privacy**: For privacy-preserving AI evaluation
                **👨‍⚖️ Meta-Evaluation**: For evaluating evaluation systems themselves
                """,
                "cognitive_behavioral": """
                ## Cognitive & Behavioral Assessment

                This category focuses on evaluating AI systems' decision-making capabilities:

                **WCP (What, Context, Person)**: Situational awareness and context understanding
                **WHO (Who, How, Outcome)**: Stakeholder analysis and impact assessment
                **TeamRisk**: Team dynamics and collaborative decision-making
                **TargetFactor**: Target identification and prioritization

                **Best for**: Risk assessment, security decision-making, behavioral analysis
                **Dataset size**: 679K+ entries (use sampling for quick tests)
                """,
                "redteaming": """
                ## AI Red-Teaming & Security

                Evaluate your AI system's resistance to adversarial attacks:

                **Attack Types**: Jailbreaking, prompt injection, data extraction
                **Severity Levels**: Low, medium, high, critical
                **Target Models**: Language models, chat assistants, specialized systems

                **Best for**: Security testing, vulnerability assessment, robustness evaluation
                **Safety**: All attacks follow ethical guidelines and defensive purposes
                """,
            },
            "configuration": {
                "general": """
                ## Dataset Configuration

                Configure your selected dataset for optimal evaluation:

                **Sample Size**: Start with smaller samples (1K-10K) for initial testing
                **Difficulty Levels**: Choose appropriate complexity for your use case
                **Domain Focus**: Select specific areas relevant to your evaluation goals

                **💡 Tip**: Use default configurations for your first evaluation
                """,
                "cognitive": """
                ## Cognitive Dataset Configuration

                **Question Types**:
                - WCP: What-Context-Person scenarios
                - WHO: Who-How-Outcome analysis
                - TeamRisk: Team dynamics evaluation
                - TargetFactor: Target prioritization

                **Scenario Limits**:
                - 1K: Quick testing
                - 10K: Standard evaluation
                - 50K+: Comprehensive analysis

                **Focus Areas**: Choose based on your evaluation objectives
                """,
            },
            "evaluation_setup": {
                "general": """
                ## Evaluation Workflow Setup

                Choose the right evaluation approach:

                **Single Dataset**: Focus on one domain, good for beginners
                **Cross-Domain**: Compare performance across multiple domains
                **Progressive**: Gradually increase complexity
                **Comprehensive**: Full security and robustness evaluation

                **💡 Recommendation**: Start with Single Dataset evaluation
                """
            },
            "error_recovery": {
                "api_connection_failed": """
                ## Connection Error Recovery

                **Problem**: Cannot connect to ViolentUTF API

                **Solutions**:
                1. Check that all services are running: `./check_services.sh`
                2. Verify APISIX gateway is accessible: `curl http://localhost:9080/health`
                3. Restart services if needed: `./setup_macos_new.sh --cleanup && ./setup_macos_new.sh`
                4. Check your authentication token hasn't expired

                **Need Help?**: Check the troubleshooting guide in `/docs/troubleshooting/`
                """,
                "authentication_expired": """
                ## Authentication Recovery

                **Problem**: Your authentication session has expired

                **Solutions**:
                1. Refresh the page to trigger re-authentication
                2. Clear browser cache and log in again
                3. Check Keycloak service status
                4. Verify your credentials are still valid

                **Prevention**: Authentication automatically refreshes during active use
                """,
                "dataset_loading_error": """
                ## Dataset Loading Recovery

                **Problem**: Dataset failed to load or preview

                **Solutions**:
                1. Try a smaller sample size first
                2. Check dataset availability in the API
                3. Verify dataset configuration is valid
                4. Clear dataset cache and try again

                **Large Datasets**: Use progressive loading for datasets >100K entries
                """,
            },
        }

    def render_contextual_help(self, component_type: str, dataset_type: Optional[str] = None) -> None:
        """Render contextual help based on current interface component"""
        help_key = dataset_type if dataset_type else "general"
        help_content = self.help_content.get(component_type, {}).get(help_key, "")

        if not help_content:
            help_content = self.help_content.get(component_type, {}).get("general", "Help content not available.")

        with st.expander("❓ Help & Guidance", expanded=False):
            st.markdown(help_content)

            # Quick tips based on component type
            if component_type == "dataset_selection":
                st.info("💡 **Quick Tip**: Start with smaller datasets to familiarize yourself with the interface")
            elif component_type == "configuration":
                st.info("💡 **Quick Tip**: Use default configurations for your first evaluation")
            elif component_type == "evaluation_setup":
                st.info("💡 **Quick Tip**: Single dataset evaluation is recommended for beginners")

            # Show current step in workflow
            current_step = self._get_current_step_from_component(component_type)
            if current_step:
                st.caption(f"Current step: {current_step}")

    def render_workflow_guide(self, workflow_step: str) -> None:
        """Render step-by-step workflow guide"""
        # Get current step number
        current_step = self.get_current_workflow_step(workflow_step)

        st.markdown("### 📋 Workflow Progress")

        # Progress indicator
        cols = st.columns(len(self.workflow_steps))
        for idx, (step_num, step_name) in enumerate(self.workflow_steps.items()):
            with cols[idx]:
                if step_num == current_step:
                    st.markdown(f"**{step_num}. {step_name}** ✅")
                    st.markdown("← *Current*")
                elif step_num < current_step:
                    st.markdown(f"✅ {step_num}. {step_name}")
                else:
                    st.markdown(f"{step_num}. {step_name}")

        # Current step guidance
        self._render_step_guidance(current_step)

    def _render_step_guidance(self, step: int) -> None:
        """Render guidance for current step"""
        guidance_text = {
            1: "Select a dataset category that matches your evaluation goals for AI testing.",
            2: "Choose a specific dataset within your selected category based on size and complexity.",
            3: "Configure the dataset parameters. Start with default settings if you're unsure.",
            4: "Preview the dataset to understand its structure and content before proceeding.",
            5: "Set up your evaluation workflow. Single dataset evaluation is recommended for beginners.",
            6: "Execute the evaluation. This may take some time depending on dataset size and complexity.",
            7: "Review your results and consider next steps or additional evaluations.",
        }

        if step in guidance_text:
            st.info(f"**Current Step Guidance**: {guidance_text[step]}")

    def render_dataset_recommendations(self, user_context: str) -> None:
        """Render dataset recommendations based on user context"""
        recommendations = self.get_dataset_recommendations(user_context)

        st.subheader("💡 Recommended Datasets")
        st.markdown("Based on your profile, we recommend these datasets to get started:")

        for rec in recommendations:
            with st.container():
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"**{rec['name']}**")
                    st.markdown(rec["description"])
                    st.markdown(f"*Best for: {rec['use_case']}*")

                    # Show difficulty and size indicators
                    difficulty_color = {"Beginner": "🟢", "Intermediate": "🟡", "Advanced": "🔴"}
                    size_indicator = {"Small": "📄", "Medium": "📊", "Large": "📈"}

                    st.caption(
                        f"{difficulty_color.get(rec['difficulty'], '⚪')} {rec['difficulty']} • "
                        f"{size_indicator.get(rec['size_category'], '📄')} {rec['size_category']}"
                    )

                with col2:
                    if st.button("Select", key=f"rec_{rec['name']}"):
                        st.session_state.selected_dataset = rec["name"]
                        st.session_state.selected_dataset_category = rec["category"]
                        st.success(f"✅ Selected {rec['name']}")
                        st.rerun()

            st.divider()

    def get_dataset_recommendations(self, user_context: str) -> List[Dict[str, Any]]:
        """Get dataset recommendations based on user context"""
        base_recommendations = [
            {
                "name": "garak_redteaming",
                "description": "AI red-teaming dataset perfect for security testing beginners",
                "use_case": "Security testing, adversarial evaluation",
                "difficulty": "Beginner",
                "size_category": "Small",
                "category": "redteaming",
                "why": "Manageable size with clear attack categories",
            },
            {
                "name": "legalbench_professional",
                "description": "Professional legal reasoning dataset for compliance testing",
                "use_case": "Legal compliance, regulatory assessment",
                "difficulty": "Intermediate",
                "size_category": "Medium",
                "category": "legal_reasoning",
                "why": "Well-structured with professional validation",
            },
            {
                "name": "docmath_mathematical",
                "description": "Mathematical reasoning dataset for quantitative evaluation",
                "use_case": "Mathematical reasoning, problem-solving",
                "difficulty": "Intermediate",
                "size_category": "Medium",
                "category": "mathematical_reasoning",
                "why": "Good balance of complexity and interpretability",
            },
            {
                "name": "ollegen1_cognitive",
                "description": "Comprehensive cognitive assessment for advanced users",
                "use_case": "Behavioral analysis, decision-making evaluation",
                "difficulty": "Advanced",
                "size_category": "Large",
                "category": "cognitive_behavioral",
                "why": "Most comprehensive but requires experience with large datasets",
            },
        ]

        # Filter recommendations based on user context
        if user_context == "new_user":
            return [rec for rec in base_recommendations if rec["difficulty"] in ["Beginner", "Intermediate"]]
        elif user_context == "security_focused":
            return [rec for rec in base_recommendations if rec["category"] in ["redteaming", "privacy_evaluation"]]
        elif user_context == "compliance_focused":
            return [rec for rec in base_recommendations if rec["category"] in ["legal_reasoning", "privacy_evaluation"]]
        else:
            return base_recommendations

    def render_onboarding_tour(self) -> None:
        """Render interactive onboarding tour for new users"""
        if not st.session_state.user_guidance_state.get("onboarding_completed", False):
            st.info("👋 Welcome to ViolentUTF! Let's take a quick tour of the dataset selection interface.")

            tour_steps = [
                {
                    "title": "Dataset Categories",
                    "content": "Choose from 7 specialized categories designed for different AI evaluation needs.",
                    "action": "Browse the category tabs above",
                },
                {
                    "title": "Dataset Selection",
                    "content": "Each category contains carefully curated datasets for specific evaluation domains.",
                    "action": "Click on a dataset to see more details",
                },
                {
                    "title": "Configuration",
                    "content": "Configure datasets to match your specific evaluation requirements.",
                    "action": "Use the configuration options to customize your evaluation",
                },
                {
                    "title": "Preview",
                    "content": "Preview dataset content before running your evaluation.",
                    "action": "Use the preview feature to understand your data",
                },
            ]

            current_tour_step = st.session_state.user_guidance_state.get("tour_step", 0)

            if current_tour_step < len(tour_steps):
                step = tour_steps[current_tour_step]

                with st.container():
                    st.markdown(f"### 🎯 Step {current_tour_step + 1}: {step['title']}")
                    st.markdown(step["content"])
                    st.markdown(f"**Next**: {step['action']}")

                    col1, col2, col3 = st.columns([1, 1, 1])

                    with col1:
                        if st.button("⏭️ Skip Tour"):
                            st.session_state.user_guidance_state["onboarding_completed"] = True
                            st.rerun()

                    with col2:
                        if current_tour_step > 0:
                            if st.button("⬅️ Previous"):
                                st.session_state.user_guidance_state["tour_step"] = current_tour_step - 1
                                st.rerun()

                    with col3:
                        if st.button("Next ➡️"):
                            if current_tour_step < len(tour_steps) - 1:
                                st.session_state.user_guidance_state["tour_step"] = current_tour_step + 1
                            else:
                                st.session_state.user_guidance_state["onboarding_completed"] = True
                            st.rerun()

    def render_error_recovery_guidance(self, error_scenario: str) -> None:
        """Render error recovery guidance for specific scenarios"""
        error_content = self.help_content.get("error_recovery", {}).get(error_scenario, "")

        if error_content:
            with st.expander("🔧 Error Recovery Guide", expanded=True):
                st.markdown(error_content)

                # Offer to contact support
                st.markdown("---")
                st.markdown("**Still having issues?**")
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("📖 View Documentation"):
                        st.info("Opening documentation... (Link to /docs/troubleshooting/)")

                with col2:
                    if st.button("💬 Get Help"):
                        st.info("Opening help channel... (Link to support)")

    def get_current_workflow_step(self, workflow_step: str) -> int:
        """Get current workflow step number"""
        step_mapping = {
            "authenticate": 0,
            "browse_categories": 1,
            "select_dataset": 2,
            "configure_parameters": 3,
            "preview_data": 4,
            "setup_evaluation": 5,
            "confirm_settings": 6,
            "execute_evaluation": 6,
            "review_results": 7,
        }

        return step_mapping.get(workflow_step, 1)

    def _get_current_step_from_component(self, component_type: str) -> Optional[str]:
        """Get current step description from component type"""
        component_to_step = {
            "dataset_selection": "Step 1-2: Dataset Selection",
            "configuration": "Step 3: Configuration",
            "preview": "Step 4: Preview",
            "evaluation_setup": "Step 5: Evaluation Setup",
        }

        return component_to_step.get(component_type)

    def update_user_progress(self, step: str) -> None:
        """Update user progress through the workflow"""
        if step not in st.session_state.user_guidance_state["completed_steps"]:
            st.session_state.user_guidance_state["completed_steps"].append(step)
            logger.info("User completed step: %s", step)

    def get_user_experience_level(self) -> str:
        """Determine user experience level based on their actions"""
        completed_steps = len(st.session_state.user_guidance_state.get("completed_steps", []))

        if completed_steps == 0:
            return "new_user"
        elif completed_steps < 3:
            return "beginner"
        elif completed_steps < 6:
            return "intermediate"
        else:
            return "advanced"

    def render_quick_start_guide(self) -> None:
        """Render quick start guide for immediate productivity"""
        with st.expander("🚀 Quick Start Guide", expanded=True):
            st.markdown(
                """
            ### Get Started in 3 Steps:

            1. **🎯 Choose Your Goal**:
               - Security Testing → Red-Teaming datasets
               - Compliance → Legal Reasoning datasets
               - Decision Making → Cognitive datasets

            2. **📊 Start Small**:
               - Use sample sizes of 1K-10K for initial testing
               - Try default configurations first
               - Preview data before full evaluation

            3. **🚀 Run Evaluation**:
               - Select "Single Dataset Evaluation" for your first run
               - Monitor progress and results
               - Iterate and expand based on findings
            """
            )

            # Quick action buttons
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("🔴 Security Test"):
                    st.session_state.quick_start_selection = "redteaming"
                    st.info("Navigating to security testing datasets...")

            with col2:
                if st.button("⚖️ Compliance Check"):
                    st.session_state.quick_start_selection = "legal"
                    st.info("Navigating to legal compliance datasets...")

            with col3:
                if st.button("🧠 Behavior Analysis"):
                    st.session_state.quick_start_selection = "cognitive"
                    st.info("Navigating to cognitive assessment datasets...")

    def render_advanced_tips(self) -> None:
        """Render advanced tips for experienced users"""
        user_level = self.get_user_experience_level()

        if user_level in ["intermediate", "advanced"]:
            with st.expander("💡 Advanced Tips", expanded=False):
                if user_level == "intermediate":
                    st.markdown(
                        """
                    ### Intermediate Tips:
                    - **Cross-Domain Evaluation**: Compare performance across multiple domains
                    - **Progressive Assessment**: Gradually increase complexity to find breaking points
                    - **Batch Operations**: Configure multiple datasets simultaneously
                    - **Custom Workflows**: Create reusable evaluation templates
                    """
                    )
                else:  # advanced
                    st.markdown(
                        """
                    ### Advanced Techniques:
                    - **Meta-Evaluation**: Use JudgeBench to evaluate your evaluation methods
                    - **Transfer Learning**: Test domain adaptation capabilities
                    - **Adversarial Robustness**: Combine red-teaming with other domains
                    - **Statistical Analysis**: Enable significance testing for rigorous evaluation
                    - **Custom Orchestrators**: Configure specialized evaluation pipelines
                    """
                    )

    def toggle_guidance_mode(self) -> None:
        """Toggle guidance mode on/off"""
        current_state = st.session_state.user_guidance_state.get("guidance_enabled", True)
        st.session_state.user_guidance_state["guidance_enabled"] = not current_state

        mode = "enabled" if not current_state else "disabled"
        st.success(f"Guidance mode {mode}")
        logger.info("User toggled guidance mode: %s", mode)

    def render_guidance_toggle(self) -> None:
        """Render guidance mode toggle"""
        current_state = st.session_state.user_guidance_state.get("guidance_enabled", True)

        _, col2 = st.columns([4, 1])
        with col2:
            if st.button("❓" if not current_state else "❓ ON", help="Toggle guidance mode", key="guidance_toggle"):
                self.toggle_guidance_mode()
                st.rerun()
