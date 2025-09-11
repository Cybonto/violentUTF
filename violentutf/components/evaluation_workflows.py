# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Evaluation Workflow Interfaces for ViolentUTF

This module provides specialized interfaces for setting up and managing
evaluation workflows across different dataset domains and use cases.
"""

import logging
from typing import Any, Dict, List, Optional

import streamlit as st

logger = logging.getLogger(__name__)


class EvaluationWorkflowInterface:
    """Interface for creating and managing evaluation workflows"""

    def __init__(self) -> None:
        """Initialize the evaluation workflow interface"""
        # Initialize session state for workflows
        if "evaluation_workflows" not in st.session_state:
            st.session_state.evaluation_workflows = {}
        if "current_workflow" not in st.session_state:
            st.session_state.current_workflow = None

    def render_evaluation_workflow_setup(self, selected_datasets: List[str]) -> Dict[str, Any]:
        """Render guided evaluation workflow setup"""
        st.title("🚀 Evaluation Workflow Setup")
        st.markdown("Create a comprehensive evaluation workflow for your selected datasets")

        if not selected_datasets:
            st.warning("⚠️ No datasets selected. Please select datasets first.")
            return {}

        # Display selected datasets
        with st.expander("📊 Selected Datasets", expanded=True):
            for dataset in selected_datasets:
                st.markdown(f"• **{dataset}**")

        # Workflow type selection
        workflow_type = st.selectbox(
            "Evaluation Workflow Type",
            [
                "Single Dataset Evaluation",
                "Cross-Domain Comparison",
                "Progressive Complexity Assessment",
                "Comprehensive Security Evaluation",
            ],
            help="Choose the type of evaluation workflow",
            key="workflow_type_select",
        )

        # Render workflow-specific configuration
        if workflow_type == "Cross-Domain Comparison":
            return self.render_cross_domain_setup(selected_datasets)
        elif workflow_type == "Progressive Complexity Assessment":
            return self.render_progressive_assessment_setup(selected_datasets)
        elif workflow_type == "Comprehensive Security Evaluation":
            return self.render_comprehensive_evaluation_setup(selected_datasets)
        else:
            return self.render_single_dataset_setup(selected_datasets)

    def render_single_dataset_setup(self, datasets: List[str]) -> Dict[str, Any]:
        """Render single dataset evaluation setup"""
        st.subheader("📊 Single Dataset Evaluation Setup")

        col1, col2 = st.columns(2)

        with col1:
            # Primary dataset selection
            primary_dataset = st.selectbox(
                "Primary Dataset", datasets, help="Select the main dataset for evaluation", key="single_primary_dataset"
            )

            # Evaluation metrics
            evaluation_metrics = st.multiselect(
                "Evaluation Metrics",
                ["Accuracy", "Precision", "Recall", "F1-Score", "Robustness", "Bias Detection"],
                default=["Accuracy", "Robustness"],
                help="Select metrics for evaluation",
                key="single_eval_metrics",
            )

        with col2:
            # Sample size configuration
            sample_size = st.slider(
                "Sample Size",
                min_value=100,
                max_value=10000,
                value=1000,
                step=100,
                help="Number of samples to evaluate",
                key="single_sample_size",
            )

            # Evaluation mode
            eval_mode = st.selectbox(
                "Evaluation Mode",
                ["Standard", "Detailed Analysis", "Quick Assessment"],
                index=0,
                help="Level of detail for evaluation",
                key="single_eval_mode",
            )

        # Advanced options
        with st.expander("🔧 Advanced Single Dataset Options"):
            include_baseline = st.checkbox(
                "Include Baseline Comparison", value=True, help="Compare against baseline models", key="single_baseline"
            )

            statistical_significance = st.checkbox(
                "Statistical Significance Testing",
                value=False,
                help="Perform statistical significance tests",
                key="single_stats",
            )

        return {
            "workflow_type": "single_dataset",
            "primary_dataset": primary_dataset,
            "evaluation_metrics": evaluation_metrics,
            "sample_size": sample_size,
            "eval_mode": eval_mode,
            "include_baseline": include_baseline,
            "statistical_significance": statistical_significance,
        }

    def render_cross_domain_setup(self, datasets: List[str]) -> Dict[str, Any]:
        """Render cross-domain evaluation setup"""
        st.subheader("🔄 Cross-Domain Evaluation Setup")

        # Get domains from datasets
        available_domains = self.get_dataset_domains(datasets)

        col1, col2 = st.columns(2)

        with col1:
            # Domain combination selection
            selected_domains = st.multiselect(
                "Evaluation Domains",
                available_domains,
                default=available_domains[:2] if len(available_domains) >= 2 else available_domains,
                help="Select domains for cross-domain comparison",
                key="cross_domains",
            )

            # Comparison methodology
            comparison_method = st.selectbox(
                "Comparison Methodology",
                ["Pairwise Comparison", "All-vs-All", "Hierarchical"],
                index=0,
                help="Method for comparing across domains",
                key="cross_method",
            )

        with col2:
            # Comparison metrics
            comparison_metrics = st.multiselect(
                "Comparison Metrics",
                ["Accuracy", "Consistency", "Domain Specificity", "Bias Detection", "Transfer Learning"],
                default=["Accuracy", "Consistency"],
                help="Metrics for cross-domain evaluation comparison",
                key="cross_metrics",
            )

            # Normalization method
            normalization = st.selectbox(
                "Score Normalization",
                ["Z-Score", "Min-Max", "Percentile", "None"],
                index=0,
                help="Method for normalizing scores across domains",
                key="cross_normalization",
            )

        # Advanced cross-domain options
        with st.expander("🔧 Advanced Cross-Domain Options"):
            domain_adaptation = st.checkbox(
                "Domain Adaptation Analysis",
                value=False,
                help="Analyze domain adaptation capabilities",
                key="cross_adaptation",
            )

            transfer_learning = st.checkbox(
                "Transfer Learning Evaluation",
                value=False,
                help="Evaluate transfer learning between domains",
                key="cross_transfer",
            )

            fairness_analysis = st.checkbox(
                "Cross-Domain Fairness Analysis",
                value=True,
                help="Analyze fairness across different domains",
                key="cross_fairness",
            )

        # Orchestrator configuration
        orchestrator_config = self.render_orchestrator_configuration(selected_domains)

        return {
            "workflow_type": "cross_domain",
            "domains": selected_domains,
            "comparison_method": comparison_method,
            "comparison_metrics": comparison_metrics,
            "normalization": normalization,
            "domain_adaptation": domain_adaptation,
            "transfer_learning": transfer_learning,
            "fairness_analysis": fairness_analysis,
            "orchestrator_config": orchestrator_config,
        }

    def render_progressive_assessment_setup(self, datasets: List[str]) -> Dict[str, Any]:
        """Render progressive complexity assessment setup"""
        st.subheader("📈 Progressive Complexity Assessment Setup")

        col1, col2 = st.columns(2)

        with col1:
            # Complexity progression
            complexity_levels = st.multiselect(
                "Complexity Progression",
                ["Basic", "Intermediate", "Advanced", "Expert"],
                default=["Basic", "Intermediate", "Advanced"],
                help="Select complexity levels for progressive assessment",
                key="prog_complexity",
            )

            # Assessment methodology
            assessment_method = st.selectbox(
                "Assessment Methodology",
                ["Incremental", "Adaptive", "Threshold-based"],
                index=0,
                help="Method for progressive assessment",
                key="prog_method",
            )

        with col2:
            # Failure analysis
            failure_analysis = st.checkbox(
                "Detailed Failure Analysis",
                value=True,
                help="Analyze failure patterns across complexity levels",
                key="prog_failure",
            )

            # Performance tracking
            track_performance = st.checkbox(
                "Track Performance Degradation",
                value=True,
                help="Track how performance changes with complexity",
                key="prog_tracking",
            )

        # Threshold configuration
        with st.expander("🎯 Performance Thresholds"):
            success_threshold = st.slider(
                "Success Threshold (%)",
                min_value=0,
                max_value=100,
                value=70,
                help="Minimum performance to proceed to next level",
                key="prog_threshold",
            )

            early_stopping = st.checkbox(
                "Early Stopping", value=True, help="Stop assessment when threshold not met", key="prog_early_stop"
            )

        return {
            "workflow_type": "progressive",
            "complexity_levels": complexity_levels,
            "assessment_method": assessment_method,
            "failure_analysis": failure_analysis,
            "track_performance": track_performance,
            "success_threshold": success_threshold,
            "early_stopping": early_stopping,
        }

    def render_comprehensive_evaluation_setup(self, datasets: List[str]) -> Dict[str, Any]:
        """Render comprehensive security evaluation setup"""
        st.subheader("🛡️ Comprehensive Security Evaluation Setup")

        # Security evaluation dimensions
        col1, col2 = st.columns(2)

        with col1:
            # Security dimensions
            security_dimensions = st.multiselect(
                "Security Evaluation Dimensions",
                ["Robustness", "Privacy", "Fairness", "Explainability", "Adversarial Resistance"],
                default=["Robustness", "Privacy", "Fairness"],
                help="Select security dimensions to evaluate",
                key="comp_dimensions",
            )

            # Threat model
            threat_model = st.selectbox(
                "Threat Model",
                ["Standard", "Advanced Persistent Threat", "Insider Threat", "Custom"],
                index=0,
                help="Threat model for security evaluation",
                key="comp_threat",
            )

        with col2:
            # Evaluation depth
            eval_depth = st.selectbox(
                "Evaluation Depth",
                ["Surface Level", "Intermediate", "Deep Analysis", "Comprehensive"],
                index=2,
                help="Depth of security evaluation",
                key="comp_depth",
            )

            # Risk assessment
            risk_assessment = st.checkbox(
                "Include Risk Assessment", value=True, help="Include comprehensive risk assessment", key="comp_risk"
            )

        # Security testing configuration
        with st.expander("🔒 Security Testing Configuration"):
            penetration_testing = st.checkbox(
                "Automated Penetration Testing",
                value=False,
                help="Include automated penetration testing",
                key="comp_pentest",
            )

            vulnerability_scanning = st.checkbox(
                "Vulnerability Scanning", value=True, help="Perform vulnerability scanning", key="comp_vulnscan"
            )

            compliance_checking = st.checkbox(
                "Compliance Checking",
                value=True,
                help="Check compliance with security standards",
                key="comp_compliance",
            )

        return {
            "workflow_type": "comprehensive",
            "security_dimensions": security_dimensions,
            "threat_model": threat_model,
            "eval_depth": eval_depth,
            "risk_assessment": risk_assessment,
            "penetration_testing": penetration_testing,
            "vulnerability_scanning": vulnerability_scanning,
            "compliance_checking": compliance_checking,
        }

    def render_orchestrator_configuration(self, domains: List[str]) -> Dict[str, Any]:
        """Render orchestrator configuration for evaluation workflows"""
        st.markdown("### 🎼 Orchestrator Configuration")

        col1, col2 = st.columns(2)

        with col1:
            # Orchestrator type
            orchestrator_type = st.selectbox(
                "Orchestrator Type",
                ["PromptSendingOrchestrator", "ScoringOrchestrator", "TreeOfAttacksOrchestrator"],
                index=0,
                help="Type of orchestrator for evaluation",
                key="orch_type",
            )

            # Batch configuration
            batch_size = st.number_input(
                "Batch Size",
                min_value=1,
                max_value=100,
                value=10,
                help="Number of prompts to process in each batch",
                key="orch_batch",
            )

        with col2:
            # Parallel processing
            parallel_processing = st.checkbox(
                "Enable Parallel Processing",
                value=True,
                help="Process multiple batches in parallel",
                key="orch_parallel",
            )

            # Retry configuration
            max_retries = st.number_input(
                "Max Retries",
                min_value=0,
                max_value=10,
                value=3,
                help="Maximum number of retries for failed requests",
                key="orch_retries",
            )

        # Advanced orchestrator options
        with st.expander("🔧 Advanced Orchestrator Options"):
            memory_optimization = st.checkbox(
                "Memory Optimization", value=True, help="Optimize memory usage for large datasets", key="orch_memory"
            )

            checkpoint_frequency = st.number_input(
                "Checkpoint Frequency",
                min_value=0,
                max_value=1000,
                value=100,
                help="Save progress every N operations (0 to disable)",
                key="orch_checkpoint",
            )

            logging_level = st.selectbox(
                "Logging Level",
                ["DEBUG", "INFO", "WARNING", "ERROR"],
                index=1,
                help="Level of detail for orchestrator logging",
                key="orch_logging",
            )

        return {
            "orchestrator_type": orchestrator_type,
            "batch_size": batch_size,
            "parallel_processing": parallel_processing,
            "max_retries": max_retries,
            "memory_optimization": memory_optimization,
            "checkpoint_frequency": checkpoint_frequency,
            "logging_level": logging_level,
        }

    def get_dataset_domains(self, datasets: List[str]) -> List[str]:
        """Extract domains from dataset names"""
        domain_mapping = {
            "ollegen1_cognitive": "cognitive",
            "garak_redteaming": "security",
            "legalbench_professional": "legal",
            "docmath_mathematical": "mathematical",
            "acpbench_planning": "planning",
            "graphwalk_spatial": "spatial",
            "confaide_privacy": "privacy",
            "judgebench_meta": "meta_evaluation",
        }

        domains = []
        for dataset in datasets:
            domain = domain_mapping.get(dataset, "general")
            if domain not in domains:
                domains.append(domain)

        return domains

    def create_workflow_template(self, workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a reusable workflow template"""
        template = {
            "template_id": f"template_{len(st.session_state.evaluation_workflows)}",
            "name": f"{workflow_config['workflow_type']}_template",
            "description": f"Template for {workflow_config['workflow_type']} evaluation",
            "config": workflow_config,
            "created_at": st.session_state.get("current_timestamp", "unknown"),
        }

        return template

    def save_workflow(self, workflow_name: str, workflow_config: Dict[str, Any]) -> bool:
        """Save evaluation workflow configuration"""
        try:
            st.session_state.evaluation_workflows[workflow_name] = workflow_config
            st.session_state.current_workflow = workflow_name
            logger.info("Saved evaluation workflow: %s", workflow_name)
            return True
        except Exception as e:
            logger.error("Failed to save workflow %s: %s", workflow_name, e)
            return False

    def load_workflow(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Load saved evaluation workflow"""
        return st.session_state.evaluation_workflows.get(workflow_name)

    def get_workflow_summary(self, workflow_config: Dict[str, Any]) -> str:
        """Generate a summary of the workflow configuration"""
        workflow_type = workflow_config.get("workflow_type", "unknown")

        if workflow_type == "single_dataset":
            dataset = workflow_config.get("primary_dataset", "unknown")
            metrics_count = len(workflow_config.get("evaluation_metrics", []))
            return f"Single dataset evaluation of {dataset} with {metrics_count} metrics"
        elif workflow_type == "cross_domain":
            domains = workflow_config.get("domains", [])
            return f"Cross-domain evaluation across {len(domains)} domains: {', '.join(domains)}"
        elif workflow_type == "progressive":
            levels = workflow_config.get("complexity_levels", [])
            return f"Progressive assessment across {len(levels)} complexity levels"
        elif workflow_type == "comprehensive":
            dimensions = workflow_config.get("security_dimensions", [])
            return f"Comprehensive security evaluation covering {len(dimensions)} dimensions"
        else:
            return f"Custom {workflow_type} evaluation workflow"
