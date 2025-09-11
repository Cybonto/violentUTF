# Advanced Evaluation Methodologies

## Overview

This document provides comprehensive guidance on advanced methodologies for evaluating AI systems using the ViolentUTF platform. These methodologies extend beyond basic assessment techniques to incorporate sophisticated analytical approaches, statistical validation, and multi-dimensional evaluation frameworks.

## Table of Contents

1. [Multi-Dimensional Evaluation Framework](#multi-dimensional-evaluation-framework)
2. [Statistical Validation Methodologies](#statistical-validation-methodologies)
3. [Cross-Domain Assessment Techniques](#cross-domain-assessment-techniques)
4. [Longitudinal Evaluation Strategies](#longitudinal-evaluation-strategies)
5. [Ensemble Evaluation Methods](#ensemble-evaluation-methods)
6. [Advanced Scoring Algorithms](#advanced-scoring-algorithms)
7. [Bias Detection and Mitigation](#bias-detection-and-mitigation)
8. [Meta-Learning Evaluation](#meta-learning-evaluation)
9. [Real-World Performance Correlation](#real-world-performance-correlation)
10. [Evaluation Quality Assurance](#evaluation-quality-assurance)

## Multi-Dimensional Evaluation Framework

### Conceptual Foundation

Advanced evaluation requires assessment across multiple dimensions simultaneously to capture the full complexity of AI system behavior.

#### Core Dimensions

**1. Cognitive Dimensions**
- Reasoning ability (deductive, inductive, abductive)
- Memory utilization and retention
- Learning transfer capabilities
- Problem decomposition skills

**2. Behavioral Dimensions**
- Response consistency across contexts
- Adaptation to changing requirements
- Error recovery mechanisms
- Performance under uncertainty

**3. Ethical Dimensions**
- Fairness across demographic groups
- Transparency in decision-making
- Accountability mechanisms
- Privacy preservation

**4. Technical Dimensions**
- Computational efficiency
- Scalability characteristics
- Robustness to input variations
- Integration compatibility

### Implementation Strategy

```python
# Example multi-dimensional evaluation framework
class MultiDimensionalEvaluator:
    def __init__(self, dimensions: List[str]):
        self.dimensions = dimensions
        self.scorers = {}
        self.weights = {}

    def evaluate_across_dimensions(self, responses: List[str]) -> Dict[str, float]:
        results = {}
        for dimension in self.dimensions:
            scorer = self.scorers[dimension]
            weight = self.weights.get(dimension, 1.0)
            score = scorer.score_responses(responses)
            results[dimension] = score * weight
        return results

    def compute_composite_score(self, dimension_scores: Dict[str, float]) -> float:
        total_weight = sum(self.weights.values())
        weighted_sum = sum(dimension_scores.values())
        return weighted_sum / total_weight if total_weight > 0 else 0.0
```

### Configuration Guidelines

**Dimension Selection**
- Identify primary evaluation objectives
- Select 3-7 core dimensions to avoid cognitive overload
- Ensure dimensions are orthogonal (non-overlapping)
- Weight dimensions based on use case priorities

**Scoring Integration**
- Use normalized scores (0-1 scale) for consistency
- Apply appropriate aggregation functions (weighted average, geometric mean)
- Consider non-linear relationships between dimensions
- Implement uncertainty quantification

## Statistical Validation Methodologies

### Hypothesis Testing Framework

#### Null Hypothesis Formulation

**Performance Comparison**
- H0: Model A performance ≤ Model B performance
- H1: Model A performance > Model B performance
- Significance level: α = 0.05 (adjustable)

**Bias Detection**
- H0: No significant bias across demographic groups
- H1: Significant bias exists across groups
- Effect size threshold: Cohen's d ≥ 0.3

#### Statistical Tests Selection

**Parametric Tests**
- t-tests for mean comparisons (normal distributions)
- ANOVA for multiple group comparisons
- Regression analysis for relationship modeling

**Non-Parametric Tests**
- Mann-Whitney U for non-normal distributions
- Kruskal-Wallis for multiple non-normal groups
- Permutation tests for complex scenarios

**Multiple Comparisons Correction**
- Bonferroni correction for conservative control
- False Discovery Rate (FDR) for exploratory analysis
- Bayesian approaches for complex hierarchies

### Effect Size Quantification

**Cohen's d for Mean Differences**
```python
import numpy as np
from scipy import stats

def cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
    """Calculate Cohen's d effect size"""
    pooled_std = np.sqrt(((len(group1) - 1) * np.var(group1, ddof=1) +
                         (len(group2) - 1) * np.var(group2, ddof=1)) /
                        (len(group1) + len(group2) - 2))
    return (np.mean(group1) - np.mean(group2)) / pooled_std

# Interpretation:
# |d| < 0.2: negligible effect
# 0.2 ≤ |d| < 0.5: small effect
# 0.5 ≤ |d| < 0.8: medium effect
# |d| ≥ 0.8: large effect
```

**R-squared for Explained Variance**
- Model performance explanation power
- Feature importance quantification
- Prediction accuracy assessment

### Confidence Intervals

**Bootstrap Confidence Intervals**
```python
def bootstrap_ci(data: np.ndarray, statistic: callable,
                confidence_level: float = 0.95, n_bootstrap: int = 10000) -> tuple:
    """Calculate bootstrap confidence interval"""
    bootstrap_stats = []
    for _ in range(n_bootstrap):
        sample = np.random.choice(data, size=len(data), replace=True)
        bootstrap_stats.append(statistic(sample))

    alpha = 1 - confidence_level
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100

    return np.percentile(bootstrap_stats, [lower_percentile, upper_percentile])
```

## Cross-Domain Assessment Techniques

### Domain Transfer Evaluation

#### Methodology Overview

Cross-domain assessment evaluates how well AI systems transfer knowledge and capabilities across different problem domains, datasets, and contexts.

**Transfer Types**
1. **Positive Transfer**: Improved performance on target domain
2. **Negative Transfer**: Degraded performance due to interference
3. **Zero Transfer**: No performance change
4. **Catastrophic Forgetting**: Loss of source domain performance

#### Evaluation Protocol

**1. Baseline Establishment**
- Train and evaluate on source domain only
- Train and evaluate on target domain only
- Record performance metrics for both scenarios

**2. Transfer Learning Assessment**
- Pre-train on source domain
- Fine-tune on target domain
- Evaluate on both domains post-transfer

**3. Transfer Metrics Calculation**
```python
def calculate_transfer_metrics(source_only: float, target_only: float,
                             source_after_transfer: float,
                             target_after_transfer: float) -> Dict[str, float]:
    """Calculate comprehensive transfer learning metrics"""

    # Forward transfer: improvement on target due to source training
    forward_transfer = target_after_transfer - target_only

    # Backward transfer: change in source performance after target training
    backward_transfer = source_after_transfer - source_only

    # Transfer efficiency: relative improvement over target-only training
    transfer_efficiency = forward_transfer / target_only if target_only > 0 else 0

    # Forgetting: loss of source performance
    forgetting = max(0, source_only - source_after_transfer)

    return {
        'forward_transfer': forward_transfer,
        'backward_transfer': backward_transfer,
        'transfer_efficiency': transfer_efficiency,
        'forgetting': forgetting
    }
```

### Multi-Domain Consistency Analysis

**Consistency Metrics**
- Cross-domain correlation coefficients
- Rank-order consistency across domains
- Performance stability measures

**Implementation Example**
```python
import pandas as pd
from scipy.stats import spearmanr, pearsonr

def analyze_cross_domain_consistency(results_df: pd.DataFrame) -> Dict[str, float]:
    """Analyze consistency of model performance across domains"""
    domains = results_df['domain'].unique()
    models = results_df['model'].unique()

    # Create domain-model performance matrix
    performance_matrix = results_df.pivot(index='model', columns='domain',
                                        values='performance')

    # Calculate pairwise correlations between domains
    correlations = {}
    for i, domain1 in enumerate(domains):
        for domain2 in domains[i+1:]:
            corr, p_value = pearsonr(performance_matrix[domain1],
                                   performance_matrix[domain2])
            correlations[f"{domain1}_vs_{domain2}"] = {
                'correlation': corr,
                'p_value': p_value
            }

    return correlations
```

## Longitudinal Evaluation Strategies

### Temporal Performance Analysis

#### Time-Series Evaluation Framework

**Components**
1. **Performance Tracking**: Monitor key metrics over time
2. **Trend Analysis**: Identify patterns and trajectories
3. **Changepoint Detection**: Identify significant performance shifts
4. **Stability Assessment**: Measure consistency over time

**Implementation Approach**
```python
import matplotlib.pyplot as plt
from changepoint import pelt
from scipy import stats

class LongitudinalEvaluator:
    def __init__(self, metrics: List[str]):
        self.metrics = metrics
        self.performance_history = {}

    def record_performance(self, timestamp: str, scores: Dict[str, float]):
        """Record performance scores at specific timestamp"""
        if timestamp not in self.performance_history:
            self.performance_history[timestamp] = {}
        self.performance_history[timestamp].update(scores)

    def detect_changepoints(self, metric: str, penalty: float = 10.0) -> List[int]:
        """Detect significant changes in performance over time"""
        scores = [self.performance_history[ts].get(metric, 0)
                 for ts in sorted(self.performance_history.keys())]

        # Apply PELT algorithm for changepoint detection
        model = "rbf"  # radial basis function model
        algo = pelt(model=model, jump=1, minseglen=3)
        result = algo.fit(scores).predict(pen=penalty)

        return result[:-1]  # Remove final changepoint (end of series)

    def calculate_stability_metrics(self, metric: str) -> Dict[str, float]:
        """Calculate stability metrics for a specific performance metric"""
        scores = [self.performance_history[ts].get(metric, 0)
                 for ts in sorted(self.performance_history.keys())]

        return {
            'coefficient_of_variation': np.std(scores) / np.mean(scores),
            'trend_slope': stats.linregress(range(len(scores)), scores).slope,
            'autocorrelation_lag1': np.corrcoef(scores[:-1], scores[1:])[0, 1]
        }
```

### Learning Curve Analysis

**Progressive Evaluation**
- Track performance vs. training data size
- Identify learning plateaus and saturation points
- Assess data efficiency and sample complexity

**Curve Fitting Models**
```python
from scipy.optimize import curve_fit

def power_law(x, a, b, c):
    """Power law learning curve model"""
    return a * np.power(x, b) + c

def exponential_decay(x, a, b, c):
    """Exponential learning curve model"""
    return a * (1 - np.exp(-b * x)) + c

def fit_learning_curve(data_sizes: np.ndarray,
                      performances: np.ndarray) -> Dict[str, float]:
    """Fit multiple learning curve models and compare"""
    models = {
        'power_law': power_law,
        'exponential': exponential_decay
    }

    results = {}
    for name, model in models.items():
        try:
            popt, pcov = curve_fit(model, data_sizes, performances)
            # Calculate R-squared
            y_pred = model(data_sizes, *popt)
            ss_res = np.sum((performances - y_pred) ** 2)
            ss_tot = np.sum((performances - np.mean(performances)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)

            results[name] = {
                'parameters': popt,
                'r_squared': r_squared,
                'covariance': pcov
            }
        except Exception as e:
            results[name] = {'error': str(e)}

    return results
```

## Ensemble Evaluation Methods

### Multi-Model Assessment

#### Ensemble Types
1. **Homogeneous Ensembles**: Same algorithm, different training data
2. **Heterogeneous Ensembles**: Different algorithms, same training data
3. **Stacked Ensembles**: Multi-level model combinations
4. **Dynamic Ensembles**: Context-dependent model selection

#### Evaluation Metrics

**Individual Model Metrics**
- Accuracy, precision, recall, F1-score
- Area under ROC curve (AUC-ROC)
- Calibration error (reliability)

**Ensemble-Specific Metrics**
```python
def calculate_ensemble_metrics(individual_predictions: List[np.ndarray],
                             ensemble_prediction: np.ndarray,
                             ground_truth: np.ndarray) -> Dict[str, float]:
    """Calculate ensemble-specific evaluation metrics"""

    # Diversity metrics
    disagreement = 0
    for i, pred1 in enumerate(individual_predictions):
        for pred2 in individual_predictions[i+1:]:
            disagreement += np.mean(pred1 != pred2)

    n_models = len(individual_predictions)
    avg_disagreement = disagreement / (n_models * (n_models - 1) / 2)

    # Ensemble improvement
    individual_accuracies = [np.mean(pred == ground_truth)
                           for pred in individual_predictions]
    ensemble_accuracy = np.mean(ensemble_prediction == ground_truth)
    improvement = ensemble_accuracy - np.mean(individual_accuracies)

    return {
        'diversity_score': avg_disagreement,
        'ensemble_improvement': improvement,
        'best_individual_accuracy': max(individual_accuracies),
        'ensemble_accuracy': ensemble_accuracy
    }
```

### Consensus Analysis

**Voting Mechanisms**
- Majority voting for classification
- Average voting for regression
- Weighted voting based on confidence
- Rank-based voting for ordinal outcomes

**Confidence Estimation**
```python
def estimate_ensemble_confidence(predictions: List[np.ndarray],
                               method: str = 'variance') -> np.ndarray:
    """Estimate confidence of ensemble predictions"""
    predictions_array = np.array(predictions)

    if method == 'variance':
        # Lower variance indicates higher confidence
        variances = np.var(predictions_array, axis=0)
        confidences = 1 / (1 + variances)  # Transform to [0, 1] range

    elif method == 'agreement':
        # Higher agreement indicates higher confidence
        mode_counts = []
        for i in range(predictions_array.shape[1]):
            values, counts = np.unique(predictions_array[:, i], return_counts=True)
            max_count = np.max(counts)
            mode_counts.append(max_count / len(predictions))
        confidences = np.array(mode_counts)

    elif method == 'entropy':
        # Lower entropy indicates higher confidence
        entropies = []
        for i in range(predictions_array.shape[1]):
            values, counts = np.unique(predictions_array[:, i], return_counts=True)
            probabilities = counts / len(predictions)
            entropy = -np.sum(probabilities * np.log2(probabilities + 1e-8))
            entropies.append(entropy)
        max_entropy = np.log2(len(predictions))
        confidences = 1 - (np.array(entropies) / max_entropy)

    return confidences
```

## Advanced Scoring Algorithms

### Adaptive Scoring Systems

#### Context-Aware Scoring

**Dynamic Weight Adjustment**
```python
class AdaptiveScorer:
    def __init__(self, base_criteria: Dict[str, float]):
        self.base_criteria = base_criteria
        self.context_modifiers = {}

    def add_context_modifier(self, context: str, modifiers: Dict[str, float]):
        """Add context-specific scoring modifiers"""
        self.context_modifiers[context] = modifiers

    def score_with_context(self, response: str, context: str) -> Dict[str, float]:
        """Score response considering specific context"""
        base_scores = self._calculate_base_scores(response)

        if context in self.context_modifiers:
            modifiers = self.context_modifiers[context]
            adjusted_scores = {}
            for criterion, base_score in base_scores.items():
                modifier = modifiers.get(criterion, 1.0)
                adjusted_scores[criterion] = base_score * modifier
            return adjusted_scores

        return base_scores

    def _calculate_base_scores(self, response: str) -> Dict[str, float]:
        """Calculate base scores using standard criteria"""
        # Implementation depends on specific scoring requirements
        return {}
```

#### Uncertainty-Aware Scoring

**Bayesian Scoring Framework**
```python
import numpy as np
from scipy import stats

class BayesianScorer:
    def __init__(self, prior_params: Dict[str, tuple]):
        """Initialize with prior parameters for each criterion"""
        self.priors = prior_params  # e.g., {'accuracy': (alpha, beta) for Beta distribution}
        self.posteriors = {}

    def update_posterior(self, criterion: str, observed_scores: List[float]):
        """Update posterior distribution based on observed scores"""
        if criterion not in self.priors:
            raise ValueError(f"No prior defined for criterion: {criterion}")

        alpha_prior, beta_prior = self.priors[criterion]

        # For Beta-Binomial conjugate pair
        n_successes = sum(observed_scores)
        n_trials = len(observed_scores)

        alpha_posterior = alpha_prior + n_successes
        beta_posterior = beta_prior + n_trials - n_successes

        self.posteriors[criterion] = (alpha_posterior, beta_posterior)

    def get_credible_interval(self, criterion: str, confidence: float = 0.95) -> tuple:
        """Get credible interval for criterion score"""
        if criterion not in self.posteriors:
            alpha, beta = self.priors[criterion]
        else:
            alpha, beta = self.posteriors[criterion]

        alpha_level = (1 - confidence) / 2
        lower = stats.beta.ppf(alpha_level, alpha, beta)
        upper = stats.beta.ppf(1 - alpha_level, alpha, beta)

        return lower, upper

    def get_expected_score(self, criterion: str) -> float:
        """Get expected score (posterior mean)"""
        if criterion not in self.posteriors:
            alpha, beta = self.priors[criterion]
        else:
            alpha, beta = self.posteriors[criterion]

        return alpha / (alpha + beta)
```

### Multi-Objective Optimization

**Pareto Frontier Analysis**
```python
def find_pareto_frontier(scores: np.ndarray) -> np.ndarray:
    """Find Pareto-optimal solutions in multi-objective space"""
    pareto_front = []

    for i, candidate in enumerate(scores):
        is_dominated = False
        for j, other in enumerate(scores):
            if i != j and dominates(other, candidate):
                is_dominated = True
                break

        if not is_dominated:
            pareto_front.append(i)

    return np.array(pareto_front)

def dominates(solution1: np.ndarray, solution2: np.ndarray) -> bool:
    """Check if solution1 dominates solution2 (assuming maximization)"""
    return np.all(solution1 >= solution2) and np.any(solution1 > solution2)

class MultiObjectiveEvaluator:
    def __init__(self, objectives: List[str], weights: List[float] = None):
        self.objectives = objectives
        self.weights = weights or [1.0] * len(objectives)

    def evaluate_solutions(self, solutions: List[Dict[str, float]]) -> Dict[str, any]:
        """Evaluate multiple solutions across objectives"""
        scores_matrix = np.array([[sol[obj] for obj in self.objectives]
                                for sol in solutions])

        pareto_indices = find_pareto_frontier(scores_matrix)

        # Calculate weighted sum for ranking
        weighted_scores = np.dot(scores_matrix, self.weights)

        return {
            'pareto_optimal_indices': pareto_indices,
            'weighted_rankings': np.argsort(weighted_scores)[::-1],
            'pareto_solutions': scores_matrix[pareto_indices],
            'all_scores': scores_matrix
        }
```

## Bias Detection and Mitigation

### Algorithmic Fairness Metrics

#### Individual Fairness
**Lipschitz Condition Verification**
```python
def check_individual_fairness(model_predictions: callable,
                            data_points: np.ndarray,
                            similarity_metric: callable,
                            lipschitz_constant: float = 1.0) -> float:
    """Check if model satisfies individual fairness (Lipschitz condition)"""
    violations = 0
    total_pairs = 0

    for i in range(len(data_points)):
        for j in range(i + 1, len(data_points)):
            point1, point2 = data_points[i], data_points[j]

            # Calculate similarity and prediction difference
            similarity = similarity_metric(point1, point2)
            pred_diff = abs(model_predictions(point1) - model_predictions(point2))

            # Check Lipschitz condition
            if pred_diff > lipschitz_constant * (1 - similarity):
                violations += 1

            total_pairs += 1

    return violations / total_pairs if total_pairs > 0 else 0
```

#### Group Fairness Metrics
```python
def calculate_fairness_metrics(y_true: np.ndarray,
                             y_pred: np.ndarray,
                             sensitive_attributes: np.ndarray) -> Dict[str, float]:
    """Calculate comprehensive fairness metrics"""
    groups = np.unique(sensitive_attributes)
    metrics = {}

    # Demographic Parity
    acceptance_rates = {}
    for group in groups:
        group_mask = sensitive_attributes == group
        acceptance_rates[group] = np.mean(y_pred[group_mask])

    dp_diff = max(acceptance_rates.values()) - min(acceptance_rates.values())
    metrics['demographic_parity_difference'] = dp_diff

    # Equalized Odds
    tpr_by_group = {}
    fpr_by_group = {}

    for group in groups:
        group_mask = sensitive_attributes == group
        group_y_true = y_true[group_mask]
        group_y_pred = y_pred[group_mask]

        # True Positive Rate
        tp = np.sum((group_y_true == 1) & (group_y_pred == 1))
        fn = np.sum((group_y_true == 1) & (group_y_pred == 0))
        tpr_by_group[group] = tp / (tp + fn) if (tp + fn) > 0 else 0

        # False Positive Rate
        fp = np.sum((group_y_true == 0) & (group_y_pred == 1))
        tn = np.sum((group_y_true == 0) & (group_y_pred == 0))
        fpr_by_group[group] = fp / (fp + tn) if (fp + tn) > 0 else 0

    tpr_diff = max(tpr_by_group.values()) - min(tpr_by_group.values())
    fpr_diff = max(fpr_by_group.values()) - min(fpr_by_group.values())

    metrics['equalized_odds_tpr_diff'] = tpr_diff
    metrics['equalized_odds_fpr_diff'] = fpr_diff
    metrics['equalized_odds_max_diff'] = max(tpr_diff, fpr_diff)

    return metrics
```

### Bias Mitigation Strategies

#### Pre-processing Techniques
**Data Resampling and Augmentation**
```python
from sklearn.utils import resample

def balance_dataset_by_group(X: np.ndarray, y: np.ndarray,
                           sensitive_attr: np.ndarray,
                           strategy: str = 'oversample') -> tuple:
    """Balance dataset to ensure fair representation"""
    balanced_X, balanced_y, balanced_attr = [], [], []

    # Get group-outcome combinations
    groups = np.unique(sensitive_attr)
    outcomes = np.unique(y)

    # Find target size for balancing
    group_outcome_counts = {}
    for group in groups:
        for outcome in outcomes:
            mask = (sensitive_attr == group) & (y == outcome)
            group_outcome_counts[(group, outcome)] = np.sum(mask)

    if strategy == 'oversample':
        target_size = max(group_outcome_counts.values())
    elif strategy == 'undersample':
        target_size = min(group_outcome_counts.values())
    else:
        target_size = int(np.mean(list(group_outcome_counts.values())))

    # Resample each group-outcome combination
    for group in groups:
        for outcome in outcomes:
            mask = (sensitive_attr == group) & (y == outcome)
            group_X = X[mask]
            group_y = y[mask]
            group_attr = sensitive_attr[mask]

            if len(group_X) > 0:
                if len(group_X) < target_size:
                    # Oversample
                    resampled_X, resampled_y, resampled_attr = resample(
                        group_X, group_y, group_attr,
                        n_samples=target_size,
                        replace=True,
                        random_state=42
                    )
                else:
                    # Undersample
                    resampled_X, resampled_y, resampled_attr = resample(
                        group_X, group_y, group_attr,
                        n_samples=target_size,
                        replace=False,
                        random_state=42
                    )

                balanced_X.append(resampled_X)
                balanced_y.append(resampled_y)
                balanced_attr.append(resampled_attr)

    return (np.vstack(balanced_X),
            np.hstack(balanced_y),
            np.hstack(balanced_attr))
```

## Meta-Learning Evaluation

### Learning-to-Learn Assessment

#### Few-Shot Learning Evaluation
```python
class FewShotEvaluator:
    def __init__(self, n_way: int = 5, k_shot: int = 1, n_query: int = 15):
        self.n_way = n_way  # Number of classes per episode
        self.k_shot = k_shot  # Number of examples per class in support set
        self.n_query = n_query  # Number of examples per class in query set

    def create_episode(self, dataset: Dict[str, List],
                      classes: List[str] = None) -> Dict[str, np.ndarray]:
        """Create a few-shot learning episode"""
        if classes is None:
            classes = np.random.choice(list(dataset.keys()),
                                     size=self.n_way, replace=False)

        support_set = {'data': [], 'labels': []}
        query_set = {'data': [], 'labels': []}

        for label_idx, class_name in enumerate(classes):
            class_data = dataset[class_name]
            selected_indices = np.random.choice(
                len(class_data),
                size=self.k_shot + self.n_query,
                replace=False
            )

            # Split into support and query
            support_indices = selected_indices[:self.k_shot]
            query_indices = selected_indices[self.k_shot:]

            # Add to sets
            for idx in support_indices:
                support_set['data'].append(class_data[idx])
                support_set['labels'].append(label_idx)

            for idx in query_indices:
                query_set['data'].append(class_data[idx])
                query_set['labels'].append(label_idx)

        return {
            'support': support_set,
            'query': query_set,
            'classes': classes
        }

    def evaluate_few_shot_performance(self, model: callable,
                                    episodes: List[Dict],
                                    adaptation_steps: int = 5) -> Dict[str, float]:
        """Evaluate model on few-shot learning episodes"""
        episode_accuracies = []
        adaptation_curves = []

        for episode in episodes:
            support_data = episode['support']['data']
            support_labels = episode['support']['labels']
            query_data = episode['query']['data']
            query_labels = episode['query']['labels']

            # Adapt model on support set
            adapted_model = model.clone()  # Assume model has clone method
            step_accuracies = []

            for step in range(adaptation_steps):
                adapted_model.fit_step(support_data, support_labels)

                # Evaluate on query set
                predictions = adapted_model.predict(query_data)
                accuracy = np.mean(predictions == query_labels)
                step_accuracies.append(accuracy)

            episode_accuracies.append(step_accuracies[-1])  # Final accuracy
            adaptation_curves.append(step_accuracies)

        return {
            'mean_accuracy': np.mean(episode_accuracies),
            'std_accuracy': np.std(episode_accuracies),
            'adaptation_curve': np.mean(adaptation_curves, axis=0),
            'episode_accuracies': episode_accuracies
        }
```

#### Meta-Learning Metrics
```python
def calculate_meta_learning_metrics(pre_adaptation_accuracies: List[float],
                                  post_adaptation_accuracies: List[float],
                                  adaptation_steps: List[int]) -> Dict[str, float]:
    """Calculate meta-learning specific metrics"""

    # Learning efficiency: improvement per adaptation step
    improvements = np.array(post_adaptation_accuracies) - np.array(pre_adaptation_accuracies)
    steps = np.array(adaptation_steps)
    learning_efficiency = np.mean(improvements / steps)

    # Adaptation speed: steps needed to reach threshold performance
    threshold = 0.8  # 80% accuracy threshold
    adaptation_speeds = []
    for i, (pre_acc, post_acc, steps) in enumerate(zip(
        pre_adaptation_accuracies, post_adaptation_accuracies, adaptation_steps
    )):
        if post_acc >= threshold:
            # Estimate steps needed (linear interpolation)
            estimated_steps = steps * (threshold - pre_acc) / (post_acc - pre_acc)
            adaptation_speeds.append(max(1, estimated_steps))

    return {
        'learning_efficiency': learning_efficiency,
        'mean_adaptation_speed': np.mean(adaptation_speeds) if adaptation_speeds else float('inf'),
        'adaptation_success_rate': len(adaptation_speeds) / len(pre_adaptation_accuracies),
        'final_performance_mean': np.mean(post_adaptation_accuracies),
        'final_performance_std': np.std(post_adaptation_accuracies)
    }
```

## Real-World Performance Correlation

### Ecological Validity Assessment

#### Simulation-to-Reality Gap Analysis
```python
class EcologicalValidityAnalyzer:
    def __init__(self):
        self.simulation_results = {}
        self.real_world_results = {}
        self.correlation_cache = {}

    def add_simulation_result(self, task_id: str, metric: str, value: float):
        """Record simulation performance"""
        if task_id not in self.simulation_results:
            self.simulation_results[task_id] = {}
        self.simulation_results[task_id][metric] = value

    def add_real_world_result(self, task_id: str, metric: str, value: float):
        """Record real-world performance"""
        if task_id not in self.real_world_results:
            self.real_world_results[task_id] = {}
        self.real_world_results[task_id][metric] = value

    def calculate_sim2real_correlation(self, metric: str) -> Dict[str, float]:
        """Calculate correlation between simulation and real-world performance"""
        if metric in self.correlation_cache:
            return self.correlation_cache[metric]

        # Get common task IDs
        common_tasks = set(self.simulation_results.keys()) & set(self.real_world_results.keys())

        if len(common_tasks) < 3:
            return {'error': 'Insufficient data for correlation analysis'}

        sim_scores = []
        real_scores = []

        for task_id in common_tasks:
            if (metric in self.simulation_results[task_id] and
                metric in self.real_world_results[task_id]):
                sim_scores.append(self.simulation_results[task_id][metric])
                real_scores.append(self.real_world_results[task_id][metric])

        if len(sim_scores) < 3:
            return {'error': f'Insufficient {metric} data for correlation'}

        # Calculate correlations
        pearson_r, pearson_p = pearsonr(sim_scores, real_scores)
        spearman_r, spearman_p = spearmanr(sim_scores, real_scores)

        # Calculate predictive validity (R-squared)
        slope, intercept, r_value, p_value, std_err = stats.linregress(sim_scores, real_scores)
        r_squared = r_value ** 2

        result = {
            'pearson_correlation': pearson_r,
            'pearson_p_value': pearson_p,
            'spearman_correlation': spearman_r,
            'spearman_p_value': spearman_p,
            'r_squared': r_squared,
            'regression_slope': slope,
            'regression_intercept': intercept,
            'standard_error': std_err,
            'sample_size': len(sim_scores)
        }

        self.correlation_cache[metric] = result
        return result

    def assess_transfer_validity(self) -> Dict[str, any]:
        """Assess how well evaluation transfers to real-world scenarios"""
        results = {}

        # Calculate correlations for all available metrics
        all_metrics = set()
        for task_results in self.simulation_results.values():
            all_metrics.update(task_results.keys())
        for task_results in self.real_world_results.values():
            all_metrics.update(task_results.keys())

        for metric in all_metrics:
            correlation_result = self.calculate_sim2real_correlation(metric)
            if 'error' not in correlation_result:
                results[metric] = correlation_result

        # Overall validity score (average of significant correlations)
        significant_correlations = []
        for metric, correlation_data in results.items():
            if correlation_data.get('pearson_p_value', 1.0) < 0.05:
                significant_correlations.append(abs(correlation_data['pearson_correlation']))

        overall_validity = np.mean(significant_correlations) if significant_correlations else 0.0

        return {
            'metric_correlations': results,
            'overall_validity_score': overall_validity,
            'significant_metrics': len(significant_correlations),
            'total_metrics': len(results)
        }
```

### User Study Integration

#### Human Evaluation Framework
```python
class HumanEvaluationIntegrator:
    def __init__(self):
        self.human_ratings = {}
        self.automated_scores = {}
        self.inter_rater_reliability = {}

    def collect_human_rating(self, evaluator_id: str, item_id: str,
                           criterion: str, rating: float):
        """Collect human evaluation rating"""
        if item_id not in self.human_ratings:
            self.human_ratings[item_id] = {}
        if criterion not in self.human_ratings[item_id]:
            self.human_ratings[item_id][criterion] = {}

        self.human_ratings[item_id][criterion][evaluator_id] = rating

    def calculate_inter_rater_reliability(self, criterion: str) -> Dict[str, float]:
        """Calculate inter-rater reliability using multiple methods"""
        ratings_by_item = {}

        # Collect all ratings for this criterion
        for item_id, item_data in self.human_ratings.items():
            if criterion in item_data:
                ratings_by_item[item_id] = list(item_data[criterion].values())

        if not ratings_by_item:
            return {'error': f'No ratings found for criterion: {criterion}'}

        # Calculate Cronbach's alpha
        ratings_matrix = []
        for item_id in sorted(ratings_by_item.keys()):
            ratings = ratings_by_item[item_id]
            if len(ratings) >= 2:  # Need at least 2 raters
                ratings_matrix.append(ratings)

        if len(ratings_matrix) < 2:
            return {'error': 'Insufficient data for reliability analysis'}

        ratings_array = np.array(ratings_matrix)
        cronbach_alpha = self._calculate_cronbach_alpha(ratings_array)

        # Calculate average pairwise correlation
        all_correlations = []
        for i in range(ratings_array.shape[1]):
            for j in range(i + 1, ratings_array.shape[1]):
                rater1_scores = ratings_array[:, i]
                rater2_scores = ratings_array[:, j]
                if len(set(rater1_scores)) > 1 and len(set(rater2_scores)) > 1:
                    corr, _ = pearsonr(rater1_scores, rater2_scores)
                    if not np.isnan(corr):
                        all_correlations.append(corr)

        avg_correlation = np.mean(all_correlations) if all_correlations else 0.0

        result = {
            'cronbach_alpha': cronbach_alpha,
            'average_correlation': avg_correlation,
            'num_raters': ratings_array.shape[1],
            'num_items': ratings_array.shape[0],
            'pairwise_correlations': all_correlations
        }

        self.inter_rater_reliability[criterion] = result
        return result

    def _calculate_cronbach_alpha(self, ratings: np.ndarray) -> float:
        """Calculate Cronbach's alpha for internal consistency"""
        n_items = ratings.shape[0]
        n_raters = ratings.shape[1]

        # Calculate item variances and total variance
        item_variances = np.var(ratings, axis=1, ddof=1)
        total_scores = np.sum(ratings, axis=1)
        total_variance = np.var(total_scores, ddof=1)

        # Cronbach's alpha formula
        alpha = (n_raters / (n_raters - 1)) * (1 - np.sum(item_variances) / total_variance)
        return alpha

    def correlate_human_automated(self, criterion: str) -> Dict[str, float]:
        """Correlate human ratings with automated scores"""
        human_scores = []
        auto_scores = []

        for item_id in self.human_ratings:
            if (criterion in self.human_ratings[item_id] and
                item_id in self.automated_scores and
                criterion in self.automated_scores[item_id]):

                # Average human ratings for this item
                human_ratings = list(self.human_ratings[item_id][criterion].values())
                avg_human = np.mean(human_ratings)

                auto_score = self.automated_scores[item_id][criterion]

                human_scores.append(avg_human)
                auto_scores.append(auto_score)

        if len(human_scores) < 3:
            return {'error': 'Insufficient data for correlation analysis'}

        correlation, p_value = pearsonr(human_scores, auto_scores)

        return {
            'correlation': correlation,
            'p_value': p_value,
            'sample_size': len(human_scores),
            'human_scores': human_scores,
            'automated_scores': auto_scores
        }
```

## Evaluation Quality Assurance

### Systematic Quality Control

#### Evaluation Audit Framework
```python
class EvaluationAuditor:
    def __init__(self):
        self.quality_checks = {
            'data_quality': self._check_data_quality,
            'methodology_validity': self._check_methodology,
            'statistical_power': self._check_statistical_power,
            'bias_assessment': self._check_bias_indicators,
            'reproducibility': self._check_reproducibility
        }
        self.audit_results = {}

    def run_comprehensive_audit(self, evaluation_data: Dict) -> Dict[str, any]:
        """Run comprehensive quality audit on evaluation"""
        audit_results = {}

        for check_name, check_function in self.quality_checks.items():
            try:
                result = check_function(evaluation_data)
                audit_results[check_name] = result
            except Exception as e:
                audit_results[check_name] = {'error': str(e)}

        # Calculate overall quality score
        quality_scores = []
        for check_name, result in audit_results.items():
            if 'quality_score' in result:
                quality_scores.append(result['quality_score'])

        overall_quality = np.mean(quality_scores) if quality_scores else 0.0

        audit_results['overall_quality_score'] = overall_quality
        audit_results['audit_timestamp'] = pd.Timestamp.now().isoformat()

        self.audit_results = audit_results
        return audit_results

    def _check_data_quality(self, data: Dict) -> Dict[str, any]:
        """Check quality of evaluation data"""
        issues = []
        quality_indicators = {}

        # Check for missing values
        if 'scores' in data:
            scores = np.array(data['scores'])
            missing_ratio = np.sum(np.isnan(scores)) / len(scores)
            quality_indicators['missing_data_ratio'] = missing_ratio

            if missing_ratio > 0.1:
                issues.append(f"High missing data ratio: {missing_ratio:.2%}")

        # Check for outliers
        if 'scores' in data:
            q1, q3 = np.percentile(scores[~np.isnan(scores)], [25, 75])
            iqr = q3 - q1
            outlier_bounds = (q1 - 1.5 * iqr, q3 + 1.5 * iqr)
            outliers = scores[(scores < outlier_bounds[0]) | (scores > outlier_bounds[1])]
            outlier_ratio = len(outliers) / len(scores)
            quality_indicators['outlier_ratio'] = outlier_ratio

            if outlier_ratio > 0.05:
                issues.append(f"High outlier ratio: {outlier_ratio:.2%}")

        # Check data distribution
        if 'scores' in data:
            from scipy.stats import normaltest
            _, p_value = normaltest(scores[~np.isnan(scores)])
            quality_indicators['normality_p_value'] = p_value

            if p_value < 0.05:
                issues.append("Data significantly deviates from normal distribution")

        # Calculate quality score
        quality_score = 1.0 - (missing_ratio + outlier_ratio) / 2
        quality_score = max(0.0, min(1.0, quality_score))

        return {
            'quality_score': quality_score,
            'issues': issues,
            'indicators': quality_indicators
        }

    def _check_methodology(self, data: Dict) -> Dict[str, any]:
        """Check validity of evaluation methodology"""
        issues = []
        indicators = {}

        # Check sample size adequacy
        if 'scores' in data:
            sample_size = len(data['scores'])
            indicators['sample_size'] = sample_size

            # Rule of thumb: n >= 30 for basic statistics
            if sample_size < 30:
                issues.append(f"Small sample size: {sample_size}")

        # Check for multiple testing correction
        if 'multiple_tests' in data and data['multiple_tests']:
            if 'correction_method' not in data:
                issues.append("Multiple testing without correction method")

        # Check evaluation metrics appropriateness
        required_metrics = ['accuracy', 'precision', 'recall']
        if 'metrics' in data:
            missing_metrics = [m for m in required_metrics if m not in data['metrics']]
            if missing_metrics:
                issues.append(f"Missing standard metrics: {missing_metrics}")

        # Calculate methodology quality score
        methodology_score = 1.0
        if issues:
            methodology_score -= len(issues) * 0.2
        methodology_score = max(0.0, methodology_score)

        return {
            'quality_score': methodology_score,
            'issues': issues,
            'indicators': indicators
        }

    def _check_statistical_power(self, data: Dict) -> Dict[str, any]:
        """Check statistical power of evaluation"""
        if 'effect_size' not in data or 'sample_size' not in data:
            return {'error': 'Insufficient data for power analysis'}

        effect_size = data['effect_size']
        sample_size = data['sample_size']
        alpha = data.get('alpha', 0.05)

        # Calculate power using approximation for t-test
        from scipy.stats import norm

        critical_t = norm.ppf(1 - alpha / 2)
        delta = effect_size * np.sqrt(sample_size / 2)
        power = 1 - norm.cdf(critical_t - delta) + norm.cdf(-critical_t - delta)

        issues = []
        if power < 0.8:
            issues.append(f"Low statistical power: {power:.3f}")

        return {
            'quality_score': min(power, 1.0),
            'statistical_power': power,
            'issues': issues,
            'indicators': {
                'effect_size': effect_size,
                'sample_size': sample_size,
                'alpha': alpha
            }
        }

    def _check_bias_indicators(self, data: Dict) -> Dict[str, any]:
        """Check for potential sources of bias"""
        issues = []
        indicators = {}

        # Check for selection bias indicators
        if 'demographics' in data:
            demographics = data['demographics']
            # Calculate diversity metrics
            unique_groups = len(set(demographics))
            total_samples = len(demographics)
            diversity_ratio = unique_groups / total_samples
            indicators['demographic_diversity'] = diversity_ratio

            if diversity_ratio < 0.1:
                issues.append("Low demographic diversity")

        # Check for confirmation bias indicators
        if 'hypothesis_direction' in data and 'results_direction' in data:
            if data['hypothesis_direction'] == data['results_direction']:
                issues.append("Results align perfectly with hypothesis (potential confirmation bias)")

        # Check for publication bias indicators
        if 'effect_sizes' in data:
            effect_sizes = np.array(data['effect_sizes'])
            # Funnel plot asymmetry test (simplified)
            if len(effect_sizes) > 10:
                # Check for asymmetry in effect size distribution
                skewness = stats.skew(effect_sizes)
                indicators['effect_size_skewness'] = skewness

                if abs(skewness) > 1:
                    issues.append(f"High effect size skewness: {skewness:.3f}")

        bias_score = 1.0 - min(len(issues) * 0.3, 1.0)

        return {
            'quality_score': bias_score,
            'issues': issues,
            'indicators': indicators
        }

    def _check_reproducibility(self, data: Dict) -> Dict[str, any]:
        """Check reproducibility aspects of evaluation"""
        issues = []
        indicators = {}

        required_info = [
            'random_seed',
            'software_versions',
            'data_preprocessing_steps',
            'model_hyperparameters'
        ]

        missing_info = [item for item in required_info if item not in data]
        if missing_info:
            issues.append(f"Missing reproducibility information: {missing_info}")

        # Check for code availability
        if 'code_available' in data:
            indicators['code_available'] = data['code_available']
            if not data['code_available']:
                issues.append("Evaluation code not available")

        # Check for data availability
        if 'data_available' in data:
            indicators['data_available'] = data['data_available']
            if not data['data_available']:
                issues.append("Evaluation data not available")

        reproducibility_score = 1.0 - (len(missing_info) + len(issues)) * 0.15
        reproducibility_score = max(0.0, reproducibility_score)

        return {
            'quality_score': reproducibility_score,
            'issues': issues,
            'indicators': indicators,
            'missing_information': missing_info
        }

    def generate_audit_report(self) -> str:
        """Generate comprehensive audit report"""
        if not self.audit_results:
            return "No audit results available. Run audit first."

        report = ["# Evaluation Quality Audit Report\n"]

        # Overall summary
        overall_score = self.audit_results.get('overall_quality_score', 0)
        report.append(f"## Overall Quality Score: {overall_score:.3f}\n")

        # Quality level determination
        if overall_score >= 0.8:
            quality_level = "High"
        elif overall_score >= 0.6:
            quality_level = "Medium"
        else:
            quality_level = "Low"

        report.append(f"**Quality Level: {quality_level}**\n")

        # Detailed results
        for check_name, results in self.audit_results.items():
            if check_name not in ['overall_quality_score', 'audit_timestamp']:
                report.append(f"### {check_name.replace('_', ' ').title()}\n")

                if 'error' in results:
                    report.append(f"**Error:** {results['error']}\n")
                    continue

                score = results.get('quality_score', 'N/A')
                report.append(f"**Score:** {score:.3f}\n")

                if 'issues' in results and results['issues']:
                    report.append("**Issues:**\n")
                    for issue in results['issues']:
                        report.append(f"- {issue}\n")

                if 'indicators' in results:
                    report.append("**Indicators:**\n")
                    for key, value in results['indicators'].items():
                        report.append(f"- {key}: {value}\n")

                report.append("\n")

        # Recommendations
        report.append("## Recommendations\n")

        if overall_score < 0.6:
            report.append("- **Critical:** Significant quality issues identified. Recommend revision before publication.\n")
        elif overall_score < 0.8:
            report.append("- **Moderate:** Some quality concerns. Address issues before finalization.\n")
        else:
            report.append("- **Good:** Evaluation meets quality standards. Minor improvements possible.\n")

        return "".join(report)
```

## Conclusion

Advanced evaluation methodologies provide the comprehensive framework necessary for rigorous AI system assessment in the ViolentUTF platform. These methodologies ensure:

1. **Scientific Rigor**: Statistical validation and hypothesis testing
2. **Comprehensive Coverage**: Multi-dimensional and cross-domain assessment
3. **Bias Mitigation**: Systematic identification and correction of evaluation biases
4. **Quality Assurance**: Systematic auditing and validation procedures
5. **Real-World Relevance**: Correlation with practical performance outcomes

### Implementation Priorities

1. **Start with Multi-Dimensional Framework**: Implement comprehensive evaluation across cognitive, behavioral, ethical, and technical dimensions
2. **Establish Statistical Validation**: Implement hypothesis testing and effect size quantification
3. **Deploy Bias Detection**: Systematic fairness assessment across demographic groups
4. **Implement Quality Controls**: Automated auditing and quality assurance procedures
5. **Enable Meta-Learning**: Few-shot learning and adaptation assessment capabilities

### Success Metrics

- **Evaluation Reliability**: Cronbach's α > 0.8 across evaluation dimensions
- **Statistical Power**: Power > 0.8 for detecting meaningful effects
- **Bias Mitigation**: Demographic parity difference < 0.1
- **Quality Assurance**: Overall quality score > 0.8
- **Real-World Correlation**: Simulation-to-reality correlation > 0.7

This advanced methodology framework ensures that AI system evaluation in ViolentUTF meets the highest standards of scientific rigor while providing actionable insights for system improvement and real-world deployment decisions.
