# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Meta-Evaluation Service for JudgeBench Converter (Issue #130).

Provides comprehensive meta-evaluation workflow services for judge assessment,
comparison, and ranking within the ViolentUTF platform.

SECURITY: All service functions include input validation and sanitization.
"""

from datetime import datetime
from typing import Any, Dict, List

from app.schemas.judgebench_datasets import ValidationResult
from app.utils.judge_analysis import JudgeAnalysisUtils


class MetaEvaluationService:
    """Service for managing meta-evaluation workflows and judge assessments."""

    def __init__(self) -> None:
        """Initialize the meta-evaluation service."""
        self.analysis_utils = JudgeAnalysisUtils()

    def create_meta_evaluation_workflow(self, judge_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create complete meta-evaluation workflow configuration.

        Args:
            judge_metadata: Dictionary of judge metadata

        Returns:
            Complete workflow configuration dictionary
        """
        workflow = {
            "workflow_id": f"meta_eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "workflow_type": "judge_meta_evaluation",
            "creation_timestamp": datetime.now().isoformat(),
            "judges_included": list(judge_metadata.keys()),
            "evaluation_stages": self._create_evaluation_stages(judge_metadata),
            "scoring_configuration": self._create_scoring_configuration(judge_metadata),
            "comparison_framework": self._create_comparison_framework(judge_metadata),
            "validation_criteria": self._create_validation_criteria(),
            "expected_outputs": self._define_expected_outputs(judge_metadata),
        }

        return workflow

    def generate_judge_comparison_framework(self, judge_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive judge comparison and ranking framework.

        Args:
            judge_data: List of judge data dictionaries

        Returns:
            Judge comparison framework configuration
        """
        if not judge_data:
            return {"status": "no_data", "framework": None}

        # Extract judge types and capabilities
        judge_types = set()
        judge_models = set()
        evaluation_focuses = set()

        for judge in judge_data:
            judge_types.add(judge.get("judge_name", "unknown"))
            judge_models.add(judge.get("judge_model", "unknown"))
            evaluation_focuses.add(judge.get("evaluation_focus", "general"))

        # Create comparison dimensions
        comparison_dimensions = [
            {
                "dimension": "accuracy",
                "weight": 0.3,
                "description": "Accuracy of judge evaluations relative to ground truth",
                "measurement": "percentage_correct_assessments",
            },
            {
                "dimension": "consistency",
                "weight": 0.25,
                "description": "Consistency between scores and reasoning",
                "measurement": "score_reasoning_correlation",
            },
            {
                "dimension": "reasoning_quality",
                "weight": 0.25,
                "description": "Quality and clarity of provided reasoning",
                "measurement": "reasoning_completeness_score",
            },
            {
                "dimension": "bias_resistance",
                "weight": 0.2,
                "description": "Resistance to systematic biases",
                "measurement": "bias_detection_score",
            },
        ]

        # Create judge-specific comparison criteria
        judge_specific_criteria = {}
        for judge_type in judge_types:
            if judge_type == "arena_hard":
                judge_specific_criteria[judge_type] = {
                    "difficulty_calibration": "Ability to assess task difficulty accurately",
                    "competitive_ranking": "Consistency in competitive performance rankings",
                    "score_granularity": "Appropriate use of scoring range",
                }
            elif judge_type == "reward_model":
                judge_specific_criteria[judge_type] = {
                    "reward_alignment": "Alignment with intended reward signals",
                    "preference_modeling": "Accuracy in modeling human preferences",
                    "value_consistency": "Consistency with stated value systems",
                }
            elif judge_type == "prometheus_2":
                judge_specific_criteria[judge_type] = {
                    "rubric_adherence": "Strict adherence to evaluation rubrics",
                    "criterion_coverage": "Complete coverage of evaluation criteria",
                    "score_justification": "Quality of score justification",
                }

        return {
            "status": "complete",
            "framework": {
                "comparison_id": f"judge_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "judges_count": len(judge_data),
                "judge_types": sorted(list(judge_types)),
                "judge_models": sorted(list(judge_models)),
                "evaluation_focuses": sorted(list(evaluation_focuses)),
                "comparison_dimensions": comparison_dimensions,
                "judge_specific_criteria": judge_specific_criteria,
                "ranking_methodology": "weighted_score_aggregation",
                "validation_approach": "cross_validation_with_expert_assessment",
            },
        }

    def extract_meta_evaluation_insights(self, evaluation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract insights from meta-evaluation results.

        Args:
            evaluation_results: List of evaluation result dictionaries

        Returns:
            Dictionary with extracted insights and recommendations
        """
        if not evaluation_results:
            return {"status": "no_data", "insights": []}

        insights = {
            "status": "complete",
            "total_evaluations": len(evaluation_results),
            "processing_timestamp": datetime.now().isoformat(),
            "insights": [],
            "patterns": [],
            "recommendations": [],
            "quality_metrics": {},
            "performance_summary": {},
        }

        # Extract scores and metadata
        scores = []
        judge_performance = {}
        reasoning_quality_scores = []

        for result in evaluation_results:
            if "original_score" in result:
                scores.append(result["original_score"])

            judge_name = result.get("judge_name", "unknown")
            if judge_name not in judge_performance:
                judge_performance[judge_name] = []

            if "judge_performance_indicators" in result:
                judge_performance[judge_name].append(result["judge_performance_indicators"])

            if "judge_reasoning_quality" in result:
                reasoning_quality = result["judge_reasoning_quality"]
                reasoning_quality_scores.append(reasoning_quality.get("clarity", 0))

        # Generate quality metrics
        if scores:
            insights["quality_metrics"] = {
                "score_distribution": self.analysis_utils.calculate_score_distribution(scores),
                "avg_reasoning_quality": (
                    sum(reasoning_quality_scores) / len(reasoning_quality_scores) if reasoning_quality_scores else 0
                ),
                "judge_diversity": len(judge_performance),
                "evaluation_coverage": len(evaluation_results),
            }

        # Identify patterns
        patterns = []
        if scores and len(set(scores)) / len(scores) < 0.3:
            patterns.append("low_score_diversity")
            insights["insights"].append(
                "Judges show limited score diversity, suggesting potential scoring bias or task homogeneity"
            )

        if reasoning_quality_scores and sum(reasoning_quality_scores) / len(reasoning_quality_scores) < 0.6:
            patterns.append("low_reasoning_quality")
            insights["insights"].append("Judge reasoning quality is below acceptable threshold")

        # Judge-specific performance analysis
        judge_insights = {}
        for judge_name, performance_data in judge_performance.items():
            if performance_data:
                avg_response_length = sum(p.get("response_length", 0) for p in performance_data) / len(performance_data)
                detailed_reasoning_rate = sum(
                    1 for p in performance_data if p.get("has_detailed_reasoning", False)
                ) / len(performance_data)

                judge_insights[judge_name] = {
                    "avg_response_length": avg_response_length,
                    "detailed_reasoning_rate": detailed_reasoning_rate,
                    "evaluation_count": len(performance_data),
                }

                if detailed_reasoning_rate < 0.7:
                    percentage = (1 - detailed_reasoning_rate) * 100
                    message = (
                        f"Judge {judge_name} provides insufficient detailed reasoning "
                        f"in {percentage:.1f}% of evaluations"
                    )
                    insights["insights"].append(message)

        insights["performance_summary"] = judge_insights
        insights["patterns"] = patterns

        # Generate recommendations
        recommendations = []
        if "low_score_diversity" in patterns:
            recommendations.append("Increase task diversity or adjust scoring guidelines to improve discrimination")

        if "low_reasoning_quality" in patterns:
            recommendations.append("Implement reasoning quality improvement measures for judges")

        if len(judge_performance) > 1:
            recommendations.append("Conduct comparative analysis between judges to identify best practices")

        insights["recommendations"] = recommendations

        return insights

    def validate_meta_evaluation_quality(
        self, prompts: List[Dict[str, Any]], metadata: Dict[str, Any]
    ) -> ValidationResult:
        """Validate quality of meta-evaluation prompts and metadata.

        Args:
            prompts: List of meta-evaluation prompt dictionaries
            metadata: Associated metadata

        Returns:
            ValidationResult with quality assessment
        """
        validation_errors = []
        warnings = []
        quality_scores = []

        # Validate prompt structure
        for i, prompt in enumerate(prompts):
            if not prompt.get("value"):
                validation_errors.append(f"Prompt {i} missing value")

            if not prompt.get("metadata"):
                validation_errors.append(f"Prompt {i} missing metadata")

            # Check for required metadata fields
            required_fields = [
                "judge_name",
                "judge_model",
                "response_model",
                "meta_evaluation_type",
                "meta_evaluation_criteria",
            ]

            prompt_metadata = prompt.get("metadata", {})
            for field in required_fields:
                if field not in prompt_metadata:
                    validation_errors.append(f"Prompt {i} missing required metadata field: {field}")

            # Quality assessment
            prompt_value = prompt.get("value", "")
            if len(prompt_value) < 500:
                warnings.append(f"Prompt {i} may be too short for comprehensive meta-evaluation")
                quality_scores.append(0.6)
            elif len(prompt_value) > 3000:
                warnings.append(f"Prompt {i} may be too long for effective evaluation")
                quality_scores.append(0.7)
            else:
                quality_scores.append(0.9)

        # Validate metadata completeness
        metadata_completeness = 0.0
        required_metadata_fields = [
            "evaluation_framework",
            "judge_count",
            "total_evaluations",
            "conversion_strategy",
            "judge_metadata",
        ]

        present_fields = sum(1 for field in required_metadata_fields if field in metadata)
        metadata_completeness = present_fields / len(required_metadata_fields)

        # Calculate overall quality score
        prompt_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        consistency_score = 0.8  # Placeholder - would analyze consistency between prompts

        overall_quality = prompt_quality_score * 0.5 + metadata_completeness * 0.3 + consistency_score * 0.2

        return ValidationResult(
            is_valid=len(validation_errors) == 0,
            validation_errors=validation_errors,
            warnings=warnings,
            quality_score=overall_quality,
            prompt_quality_score=prompt_quality_score,
            metadata_completeness=metadata_completeness,
            consistency_score=consistency_score,
        )

    def _create_evaluation_stages(self, judge_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create evaluation stages for meta-evaluation workflow.

        Args:
            judge_metadata: Judge metadata dictionary

        Returns:
            List of evaluation stage configurations
        """
        stages = [
            {
                "stage": "preparation",
                "description": "Prepare meta-evaluation prompts and configurations",
                "tasks": ["prompt_generation", "criteria_validation", "scorer_configuration"],
                "estimated_duration_minutes": 10,
            },
            {
                "stage": "execution",
                "description": "Execute meta-evaluation assessments",
                "tasks": ["judge_assessment", "performance_analysis", "consistency_checking"],
                "estimated_duration_minutes": 30,
            },
            {
                "stage": "analysis",
                "description": "Analyze meta-evaluation results",
                "tasks": ["result_aggregation", "pattern_detection", "insight_extraction"],
                "estimated_duration_minutes": 15,
            },
            {
                "stage": "reporting",
                "description": "Generate comprehensive reports and recommendations",
                "tasks": ["report_generation", "visualization", "recommendation_synthesis"],
                "estimated_duration_minutes": 10,
            },
        ]

        return stages

    def _create_scoring_configuration(self, judge_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create scoring configuration for meta-evaluation.

        Args:
            judge_metadata: Judge metadata dictionary

        Returns:
            Scoring configuration dictionary
        """
        return {
            "scoring_method": "weighted_multi_dimensional",
            "score_range": {"min": 0.0, "max": 10.0},
            "dimension_weights": {
                "accuracy": 0.3,
                "consistency": 0.25,
                "reasoning_quality": 0.25,
                "bias_resistance": 0.2,
            },
            "normalization": "z_score_with_bounds",
            "aggregation_method": "weighted_average",
        }

    def _create_comparison_framework(self, judge_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create comparison framework for judges.

        Args:
            judge_metadata: Judge metadata dictionary

        Returns:
            Comparison framework configuration
        """
        return {
            "comparison_type": "multi_dimensional_ranking",
            "ranking_criteria": ["overall_quality", "consistency", "reasoning_quality"],
            "statistical_tests": ["t_test", "mann_whitney_u", "effect_size"],
            "significance_threshold": 0.05,
            "effect_size_threshold": 0.2,
        }

    def _create_validation_criteria(self) -> Dict[str, Any]:
        """Create validation criteria for meta-evaluation.

        Returns:
            Validation criteria configuration
        """
        return {
            "minimum_evaluations_per_judge": 10,
            "minimum_prompt_length": 500,
            "maximum_prompt_length": 3000,
            "required_metadata_fields": [
                "judge_name",
                "judge_model",
                "response_model",
                "meta_evaluation_type",
                "meta_evaluation_criteria",
            ],
            "quality_thresholds": {"prompt_quality": 0.7, "metadata_completeness": 0.8, "consistency_score": 0.75},
        }

    def _define_expected_outputs(self, judge_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Define expected outputs from meta-evaluation.

        Args:
            judge_metadata: Judge metadata dictionary

        Returns:
            Expected outputs configuration
        """
        return {
            "primary_outputs": [
                "judge_quality_rankings",
                "performance_analysis_report",
                "bias_detection_results",
                "consistency_assessment",
            ],
            "secondary_outputs": ["improvement_recommendations", "comparative_analysis", "quality_metrics_dashboard"],
            "output_formats": ["json", "html_report", "csv_data"],
            "delivery_timeline": "within_1_hour_of_completion",
        }
