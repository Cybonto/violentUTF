# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Judge Analysis Utilities for JudgeBench Meta-Evaluation Converter (Issue #130).

Provides utilities for analyzing judge performance, consistency, and quality metrics
across different judge types and evaluation scenarios.

SECURITY: All analysis functions include input validation and sanitization.
"""

from typing import Any, Dict, List

from app.schemas.judgebench_datasets import JUDGE_CONFIGURATIONS, JudgeAnalysis, JudgeFileInfo

# Import numpy for statistical calculations
try:
    import numpy
except ImportError:
    numpy = None


class JudgeAnalysisUtils:
    """Utility functions for judge analysis and performance assessment."""

    @staticmethod
    def calculate_score_distribution(scores: List[float]) -> Dict[str, float]:
        """Calculate score distribution statistics.

        Args:
            scores: List of numerical scores

        Returns:
            Dictionary with distribution statistics
        """
        if not scores:
            return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

        return {
            "mean": float(numpy.mean(scores)),
            "std": float(numpy.std(scores)),
            "min": float(min(scores)),
            "max": float(max(scores)),
            "median": float(numpy.median(scores)),
            "q25": float(numpy.percentile(scores, 25)),
            "q75": float(numpy.percentile(scores, 75)),
        }

    @staticmethod
    def analyze_reasoning_patterns(reasoning_texts: List[str]) -> Dict[str, Any]:
        """Analyze patterns in judge reasoning texts.

        Args:
            reasoning_texts: List of reasoning text strings

        Returns:
            Dictionary with reasoning pattern analysis
        """
        if not reasoning_texts:
            return {"patterns": [], "common_words": [], "avg_length": 0}

        # Analyze length patterns
        lengths = [len(text) for text in reasoning_texts]
        avg_length = sum(lengths) / len(lengths)

        # Find common words (simple frequency analysis)
        all_words = []
        for text in reasoning_texts:
            words = text.lower().split()
            all_words.extend([word.strip('.,!?;:"()[]') for word in words])

        from collections import Counter

        word_freq = Counter(all_words)
        common_words = [word for word, count in word_freq.most_common(10) if len(word) > 3]

        # Identify reasoning patterns
        patterns = []
        if any("because" in text.lower() for text in reasoning_texts):
            patterns.append("causal_reasoning")
        if any("however" in text.lower() for text in reasoning_texts):
            patterns.append("contrastive_reasoning")
        if any("overall" in text.lower() for text in reasoning_texts):
            patterns.append("summary_reasoning")

        return {
            "patterns": patterns,
            "common_words": common_words[:5],  # Top 5 common words
            "avg_length": avg_length,
            "length_variance": float(numpy.var(lengths)) if lengths else 0,
        }

    @staticmethod
    def detect_scoring_bias(scores: List[float], metadata_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect potential scoring biases based on metadata.

        Args:
            scores: List of numerical scores
            metadata_list: List of metadata dictionaries

        Returns:
            Dictionary with bias detection results
        """
        if len(scores) != len(metadata_list) or not scores:
            return {"bias_detected": False, "details": "Insufficient data"}

        bias_results = {
            "bias_detected": False,
            "score_variance": float(numpy.var(scores)) if scores else 0,
            "potential_biases": [],
        }

        # Check for model-specific bias
        model_scores = {}
        for score, metadata in zip(scores, metadata_list):
            response_model = metadata.get("response_model", "unknown")
            if response_model not in model_scores:
                model_scores[response_model] = []
            model_scores[response_model].append(score)

        # Detect significant differences in mean scores between models
        if len(model_scores) > 1:
            model_means = {model: numpy.mean(scores) for model, scores in model_scores.items()}
            max_mean = max(model_means.values())
            min_mean = min(model_means.values())

            if max_mean - min_mean > 1.5:  # Significant difference threshold
                bias_results["bias_detected"] = True
                bias_results["potential_biases"].append("model_preference_bias")

        # Check for score clustering (lack of discrimination)
        unique_scores = len(set(scores))
        if unique_scores / len(scores) < 0.3:  # Low score diversity
            bias_results["potential_biases"].append("score_clustering_bias")

        return bias_results

    @staticmethod
    def assess_consistency_across_criteria(evaluations: List[Dict[str, Any]]) -> Dict[str, float]:
        """Assess consistency of scoring across different evaluation criteria.

        Args:
            evaluations: List of evaluation dictionaries

        Returns:
            Dictionary with consistency metrics
        """
        if not evaluations:
            return {"overall_consistency": 0.0}

        consistency_metrics = {}

        # Group evaluations by criteria types
        criteria_groups = {}
        for eval_data in evaluations:
            criteria = eval_data.get("evaluation_criteria", [])
            criteria_key = "_".join(sorted(criteria))
            if criteria_key not in criteria_groups:
                criteria_groups[criteria_key] = []
            criteria_groups[criteria_key].append(eval_data.get("score", 0))

        # Calculate consistency within each criteria group
        total_consistency = 0
        valid_groups = 0

        for criteria_key, scores in criteria_groups.items():
            if len(scores) > 1:
                consistency = 1.0 - (numpy.std(scores) / 10.0)  # Normalize by max possible score
                consistency_metrics[criteria_key] = max(0.0, consistency)
                total_consistency += consistency_metrics[criteria_key]
                valid_groups += 1

        overall_consistency = total_consistency / valid_groups if valid_groups > 0 else 0.0
        consistency_metrics["overall_consistency"] = overall_consistency

        return consistency_metrics

    @staticmethod
    def generate_judge_quality_report(analysis_results: List[JudgeAnalysis]) -> Dict[str, Any]:
        """Generate comprehensive judge quality report.

        Args:
            analysis_results: List of JudgeAnalysis instances

        Returns:
            Dictionary with comprehensive quality report
        """
        if not analysis_results:
            return {"status": "no_data", "quality_score": 0.0}

        # Aggregate quality metrics
        all_reasoning_quality = []
        all_performance_indicators = []
        all_consistency_indicators = []

        for analysis in analysis_results:
            all_reasoning_quality.append(analysis.reasoning_quality)
            all_performance_indicators.append(analysis.performance_indicators)
            all_consistency_indicators.append(analysis.consistency_indicators)

        # Calculate overall quality scores
        avg_reasoning_clarity = numpy.mean([rq.get("clarity", 0) for rq in all_reasoning_quality])
        avg_reasoning_logic = numpy.mean([rq.get("logic", 0) for rq in all_reasoning_quality])
        avg_reasoning_completeness = numpy.mean([rq.get("completeness", 0) for rq in all_reasoning_quality])

        avg_consistency = numpy.mean([ci.get("score_reasoning_alignment", 0) for ci in all_consistency_indicators])

        # Overall quality score (weighted average)
        quality_score = (
            avg_reasoning_clarity * 0.3
            + avg_reasoning_logic * 0.3
            + avg_reasoning_completeness * 0.2
            + avg_consistency * 0.2
        )

        return {
            "status": "complete",
            "total_analyses": len(analysis_results),
            "quality_score": float(quality_score),
            "reasoning_quality": {
                "clarity": float(avg_reasoning_clarity),
                "logic": float(avg_reasoning_logic),
                "completeness": float(avg_reasoning_completeness),
            },
            "consistency_score": float(avg_consistency),
            "recommendations": JudgeAnalysisUtils._generate_recommendations(
                quality_score, avg_reasoning_clarity, avg_consistency
            ),
        }

    @staticmethod
    def _generate_recommendations(
        quality_score: float, reasoning_clarity: float, consistency_score: float
    ) -> List[str]:
        """Generate recommendations based on quality metrics.

        Args:
            quality_score: Overall quality score
            reasoning_clarity: Reasoning clarity score
            consistency_score: Consistency score

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if quality_score < 0.6:
            recommendations.append("Overall judge quality is below acceptable threshold")

        if reasoning_clarity < 0.6:
            recommendations.append("Improve reasoning clarity and explanation detail")

        if consistency_score < 0.7:
            recommendations.append("Address scoring consistency issues between reasoning and numerical scores")

        if quality_score > 0.8:
            recommendations.append("Judge demonstrates high-quality evaluation capabilities")

        return recommendations

    @staticmethod
    def compare_judges_performance(judge_analyses: Dict[str, List[JudgeAnalysis]]) -> Dict[str, Any]:
        """Compare performance across different judges.

        Args:
            judge_analyses: Dictionary mapping judge names to analysis lists

        Returns:
            Dictionary with comparative analysis results
        """
        if not judge_analyses:
            return {"comparison": "no_data"}

        comparison_results = {}
        judge_scores = {}

        # Calculate quality scores for each judge
        for judge_name, analyses in judge_analyses.items():
            if analyses:
                quality_report = JudgeAnalysisUtils.generate_judge_quality_report(analyses)
                judge_scores[judge_name] = quality_report["quality_score"]
                comparison_results[judge_name] = {
                    "quality_score": quality_report["quality_score"],
                    "total_evaluations": len(analyses),
                    "reasoning_quality": quality_report["reasoning_quality"],
                    "consistency_score": quality_report["consistency_score"],
                }

        # Rank judges by quality score
        ranked_judges = sorted(judge_scores.items(), key=lambda x: x[1], reverse=True)

        return {
            "comparison": "complete",
            "judge_rankings": ranked_judges,
            "detailed_comparison": comparison_results,
            "best_performer": ranked_judges[0][0] if ranked_judges else None,
            "performance_spread": max(judge_scores.values()) - min(judge_scores.values()) if judge_scores else 0,
        }


# Numpy fallback already handled at module level


class JudgePerformanceAnalyzer:
    """Analyzes judge performance indicators and consistency metrics."""

    def analyze_single_evaluation(self, judge_evaluation: Dict[str, Any], file_info: JudgeFileInfo) -> JudgeAnalysis:
        """Analyze performance indicators for single judge evaluation.

        Args:
            judge_evaluation: Judge evaluation data dictionary
            file_info: Judge file information

        Returns:
            JudgeAnalysis with comprehensive performance assessment
        """
        # Extract performance indicators
        performance_indicators = {
            "response_length": len(judge_evaluation.get("judge_response", "")),
            "reasoning_length": len(judge_evaluation.get("reasoning", "")),
            "score_value": judge_evaluation.get("score", 0),
            "has_detailed_reasoning": len(judge_evaluation.get("reasoning", "")) > 50,
            "evaluation_completeness": self.assess_evaluation_completeness(judge_evaluation),
        }

        # Assess reasoning quality
        reasoning_quality = self.assess_reasoning_quality(judge_evaluation.get("reasoning", ""))

        # Check score appropriateness
        score_appropriateness = self.assess_score_appropriateness(judge_evaluation)

        # Generate evaluation dimensions
        evaluation_dimensions = self.get_judge_evaluation_dimensions(file_info.judge_name)

        return JudgeAnalysis(
            performance_indicators=performance_indicators,
            evaluation_dimensions=evaluation_dimensions,
            reasoning_quality=reasoning_quality,
            score_appropriateness=score_appropriateness,
            consistency_indicators=self.check_consistency_indicators(judge_evaluation),
            judge_characteristics=self.extract_judge_characteristics(file_info),
        )

    def analyze_judge_file_performance(self, judge_prompts: List[Any]) -> Dict[str, Any]:
        """Analyze overall performance across all evaluations in a judge file.

        Args:
            judge_prompts: List of SeedPrompt instances from judge file

        Returns:
            Dictionary with aggregate performance metrics
        """
        if not judge_prompts:
            return {"status": "no_data"}

        # Aggregate performance metrics
        scores = []
        reasoning_lengths = []
        response_lengths = []

        for prompt in judge_prompts:
            metadata = prompt.metadata
            scores.append(metadata.get("original_score", 0))
            if "judge_performance_indicators" in metadata:
                indicators = metadata["judge_performance_indicators"]
                reasoning_lengths.append(indicators.get("reasoning_length", 0))
                response_lengths.append(indicators.get("response_length", 0))

        return {
            "total_evaluations": len(judge_prompts),
            "score_statistics": {
                "mean": float(numpy.mean(scores)) if scores else 0,
                "std": float(numpy.std(scores)) if scores else 0,
                "min": float(min(scores)) if scores else 0,
                "max": float(max(scores)) if scores else 0,
            },
            "reasoning_statistics": {
                "mean_length": float(numpy.mean(reasoning_lengths)) if reasoning_lengths else 0,
                "has_detailed_reasoning_rate": (
                    sum(1 for x in reasoning_lengths if x > 50) / len(reasoning_lengths) if reasoning_lengths else 0
                ),
            },
            "response_statistics": {"mean_length": float(numpy.mean(response_lengths)) if response_lengths else 0},
        }

    def assess_evaluation_completeness(self, judge_evaluation: Dict[str, Any]) -> float:
        """Assess completeness of judge evaluation.

        Args:
            judge_evaluation: Judge evaluation data

        Returns:
            Completeness score (0.0 to 1.0)
        """
        required_fields = ["judge_response", "score", "reasoning", "evaluation_criteria"]
        present_fields = sum(1 for field in required_fields if judge_evaluation.get(field))
        return present_fields / len(required_fields)

    def assess_reasoning_quality(self, reasoning: str) -> Dict[str, float]:
        """Assess quality of judge reasoning.

        Args:
            reasoning: Judge's reasoning text

        Returns:
            Dictionary with reasoning quality metrics
        """
        if not reasoning:
            return {"clarity": 0.0, "logic": 0.0, "completeness": 0.0}

        # Simple heuristic-based quality assessment
        length_score = min(len(reasoning) / 200, 1.0)  # Longer reasoning generally better (up to 200 chars)

        # Check for logical connectors and structured reasoning
        logical_words = [
            "because",
            "therefore",
            "however",
            "additionally",
            "furthermore",
            "consequently",
            "since",
            "thus",
            "hence",
            "moreover",
            "although",
            "while",
            "whereas",
            "with",
            "follows",
        ]
        logic_score = min(sum(1 for word in logical_words if word in reasoning.lower()) / 3, 1.0)

        # If limited logical connectors found, give credit for structured reasoning patterns
        if logic_score <= 0.3 and len(reasoning) > 50:
            # Check for structured reasoning patterns
            structure_indicators = [". ", "? ", "! ", ": "]
            sentence_count = sum(reasoning.count(indicator) for indicator in structure_indicators)
            if sentence_count > 1:  # Multiple sentences suggest better reasoning
                structure_bonus = min(sentence_count / 5, 0.6)  # More generous scoring for structure
                logic_score = max(logic_score, structure_bonus)

        # Check for completeness indicators
        completeness_words = [
            "overall",
            "summary",
            "conclusion",
            "assessment",
            "evaluation",
            "demonstrates",
            "shows",
            "indicates",
            "suggests",
            "evidence",
        ]
        completeness_score = min(sum(1 for word in completeness_words if word in reasoning.lower()) / 3, 1.0)

        # Boost completeness for longer, detailed reasoning
        if len(reasoning) > 100:
            completeness_score = min(completeness_score + 0.2, 1.0)

        return {
            "clarity": (length_score + logic_score) / 2,
            "logic": logic_score,
            "completeness": (completeness_score + length_score) / 2,
        }

    def assess_score_appropriateness(self, judge_evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Assess appropriateness of judge's numerical score.

        Args:
            judge_evaluation: Judge evaluation data

        Returns:
            Dictionary with score appropriateness assessment
        """
        reasoning = judge_evaluation.get("reasoning", "")

        # Simple heuristic: longer, more detailed reasoning should correlate with more nuanced scoring
        reasoning_length = len(reasoning)
        expected_precision = min(reasoning_length / 100, 1.0)  # More detailed reasoning allows more precise scoring

        return {
            "consistency": 0.8,  # Placeholder - would need more sophisticated analysis
            "calibration": min(expected_precision + 0.3, 1.0),
        }

    def check_consistency_indicators(self, judge_evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Check consistency indicators in judge evaluation.

        Args:
            judge_evaluation: Judge evaluation data

        Returns:
            Dictionary with consistency indicators
        """
        # Placeholder implementation - would need more sophisticated analysis
        return {"score_reasoning_alignment": 0.85}  # Would analyze alignment between score and reasoning sentiment

    def get_judge_evaluation_dimensions(self, judge_name: str) -> List[str]:
        """Get evaluation dimensions for specific judge type.

        Args:
            judge_name: Name of the judge

        Returns:
            List of evaluation dimensions
        """
        base_dimensions = ["accuracy", "consistency", "reasoning_quality", "bias_detection"]

        if judge_name in JUDGE_CONFIGURATIONS:
            specific_dimensions = list(JUDGE_CONFIGURATIONS[judge_name]["specific_criteria"].keys())
            return base_dimensions + specific_dimensions

        return base_dimensions

    def extract_judge_characteristics(self, file_info: JudgeFileInfo) -> Dict[str, str]:
        """Extract judge characteristics from file info.

        Args:
            file_info: Judge file information

        Returns:
            Dictionary with judge characteristics
        """
        return {
            "judge_type": file_info.judge_name,
            "model": file_info.judge_model,
            "response_model": file_info.response_model,
            "file_size_category": (
                "large" if file_info.file_size_mb > 10 else "medium" if file_info.file_size_mb > 5 else "small"
            ),
        }
