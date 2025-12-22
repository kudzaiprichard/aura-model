"""
Performance metrics calculation utilities for phishing detection pipeline.

This module provides functions for:
- Classification metrics (accuracy, precision, recall, F1)
- Confidence score calculation
- Probability calibration
- Performance comparison
- Confusion matrix analysis
"""

import numpy as np
from typing import Dict, List, Tuple, Optional


# =============================================================================
# CLASSIFICATION METRICS
# =============================================================================

def calculate_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate accuracy score.

    Args:
        y_true: True labels
        y_pred: Predicted labels

    Returns:
        Accuracy (0.0 to 1.0)

    Example:
        y_true = np.array([0, 1, 1, 0, 1])
        y_pred = np.array([0, 1, 0, 0, 1])
        accuracy = calculate_accuracy(y_true, y_pred)  # 0.8
    """
    correct = np.sum(y_true == y_pred)
    total = len(y_true)
    return float(correct / total) if total > 0 else 0.0


def calculate_precision(y_true: np.ndarray,
                        y_pred: np.ndarray,
                        positive_label: int = 1,
                        zero_division: float = 0.0) -> float:
    """
    Calculate precision score.

    Precision = TP / (TP + FP)

    Args:
        y_true: True labels
        y_pred: Predicted labels
        positive_label: Label to consider as positive (default: 1)
        zero_division: Value to return if no positive predictions

    Returns:
        Precision (0.0 to 1.0)

    Example:
        precision = calculate_precision(y_true, y_pred)
    """
    # True positives
    tp = np.sum((y_true == positive_label) & (y_pred == positive_label))

    # False positives
    fp = np.sum((y_true != positive_label) & (y_pred == positive_label))

    # Calculate precision
    if (tp + fp) == 0:
        return zero_division

    return float(tp / (tp + fp))


def calculate_recall(y_true: np.ndarray,
                     y_pred: np.ndarray,
                     positive_label: int = 1,
                     zero_division: float = 0.0) -> float:
    """
    Calculate recall score (sensitivity, true positive rate).

    Recall = TP / (TP + FN)

    Args:
        y_true: True labels
        y_pred: Predicted labels
        positive_label: Label to consider as positive (default: 1)
        zero_division: Value to return if no actual positives

    Returns:
        Recall (0.0 to 1.0)

    Example:
        recall = calculate_recall(y_true, y_pred)
    """
    # True positives
    tp = np.sum((y_true == positive_label) & (y_pred == positive_label))

    # False negatives
    fn = np.sum((y_true == positive_label) & (y_pred != positive_label))

    # Calculate recall
    if (tp + fn) == 0:
        return zero_division

    return float(tp / (tp + fn))


def calculate_f1_score(y_true: np.ndarray,
                       y_pred: np.ndarray,
                       positive_label: int = 1,
                       zero_division: float = 0.0) -> float:
    """
    Calculate F1 score (harmonic mean of precision and recall).

    F1 = 2 * (precision * recall) / (precision + recall)

    Args:
        y_true: True labels
        y_pred: Predicted labels
        positive_label: Label to consider as positive (default: 1)
        zero_division: Value to return if precision + recall = 0

    Returns:
        F1 score (0.0 to 1.0)

    Example:
        f1 = calculate_f1_score(y_true, y_pred)
    """
    precision = calculate_precision(y_true, y_pred, positive_label, zero_division)
    recall = calculate_recall(y_true, y_pred, positive_label, zero_division)

    if (precision + recall) == 0:
        return zero_division

    return float(2 * (precision * recall) / (precision + recall))


def calculate_all_metrics(y_true: np.ndarray,
                          y_pred: np.ndarray,
                          positive_label: int = 1,
                          zero_division: float = 0.0) -> Dict[str, float]:
    """
    Calculate all classification metrics at once.

    Args:
        y_true: True labels
        y_pred: Predicted labels
        positive_label: Label to consider as positive (default: 1)
        zero_division: Value to return for undefined metrics

    Returns:
        Dictionary with all metrics:
        - accuracy: Overall accuracy
        - precision: Precision for positive class
        - recall: Recall for positive class
        - f1_score: F1 score for positive class

    Example:
        metrics = calculate_all_metrics(y_true, y_pred)
        print(f"Accuracy: {metrics['accuracy']:.3f}")
        print(f"Precision: {metrics['precision']:.3f}")
        print(f"Recall: {metrics['recall']:.3f}")
        print(f"F1: {metrics['f1_score']:.3f}")
    """
    return {
        'accuracy': calculate_accuracy(y_true, y_pred),
        'precision': calculate_precision(y_true, y_pred, positive_label, zero_division),
        'recall': calculate_recall(y_true, y_pred, positive_label, zero_division),
        'f1_score': calculate_f1_score(y_true, y_pred, positive_label, zero_division)
    }


# =============================================================================
# CONFUSION MATRIX
# =============================================================================

def calculate_confusion_matrix(y_true: np.ndarray,
                               y_pred: np.ndarray) -> Dict[str, int]:
    """
    Calculate confusion matrix components.

    Args:
        y_true: True labels (0 or 1)
        y_pred: Predicted labels (0 or 1)

    Returns:
        Dictionary with confusion matrix components:
        - true_positives (TP): Correctly predicted phishing
        - true_negatives (TN): Correctly predicted legitimate
        - false_positives (FP): Legitimate predicted as phishing
        - false_negatives (FN): Phishing predicted as legitimate

    Example:
        cm = calculate_confusion_matrix(y_true, y_pred)
        print(f"TP: {cm['true_positives']}")
        print(f"TN: {cm['true_negatives']}")
        print(f"FP: {cm['false_positives']}")
        print(f"FN: {cm['false_negatives']}")
    """
    # True positives: actual=1, predicted=1
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))

    # True negatives: actual=0, predicted=0
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))

    # False positives: actual=0, predicted=1
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))

    # False negatives: actual=1, predicted=0
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))

    return {
        'true_positives': tp,
        'true_negatives': tn,
        'false_positives': fp,
        'false_negatives': fn
    }


def calculate_specificity(y_true: np.ndarray,
                          y_pred: np.ndarray,
                          zero_division: float = 0.0) -> float:
    """
    Calculate specificity (true negative rate).

    Specificity = TN / (TN + FP)

    Args:
        y_true: True labels
        y_pred: Predicted labels
        zero_division: Value to return if TN + FP = 0

    Returns:
        Specificity (0.0 to 1.0)

    Example:
        specificity = calculate_specificity(y_true, y_pred)
    """
    cm = calculate_confusion_matrix(y_true, y_pred)

    tn = cm['true_negatives']
    fp = cm['false_positives']

    if (tn + fp) == 0:
        return zero_division

    return float(tn / (tn + fp))


# =============================================================================
# CONFIDENCE SCORES
# =============================================================================

def calculate_confidence_from_probability(probability: float) -> float:
    """
    Calculate confidence score from probability.

    Confidence is the distance from the decision boundary (0.5).
    Higher confidence means prediction is more certain.

    Args:
        probability: Probability value (0.0 to 1.0)

    Returns:
        Confidence score (0.0 to 1.0)

    Examples:
        >>> calculate_confidence_from_probability(0.5)  # At decision boundary
        0.0
        >>> calculate_confidence_from_probability(0.75)  # 25% away
        0.5
        >>> calculate_confidence_from_probability(1.0)  # Maximum confidence
        1.0
        >>> calculate_confidence_from_probability(0.1)  # High confidence for negative
        0.8
    """
    return abs(probability - 0.5) * 2


def calculate_confidence_from_probabilities(probabilities: np.ndarray) -> np.ndarray:
    """
    Calculate confidence scores for multiple probabilities.

    Args:
        probabilities: Array of probability values

    Returns:
        Array of confidence scores

    Example:
        probs = np.array([0.9, 0.6, 0.3, 0.8])
        confidences = calculate_confidence_from_probabilities(probs)
    """
    return np.abs(probabilities - 0.5) * 2


# =============================================================================
# THRESHOLD ANALYSIS
# =============================================================================

def apply_threshold(probabilities: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """
    Apply threshold to probabilities to get binary predictions.

    Args:
        probabilities: Array of probability values
        threshold: Decision threshold (0.0 to 1.0)

    Returns:
        Array of binary predictions (0 or 1)

    Example:
        probs = np.array([0.9, 0.6, 0.3, 0.8])
        predictions = apply_threshold(probs, threshold=0.7)
        # [1, 0, 0, 1]
    """
    return (probabilities >= threshold).astype(int)


def calculate_metrics_at_threshold(y_true: np.ndarray,
                                   probabilities: np.ndarray,
                                   threshold: float) -> Dict[str, float]:
    """
    Calculate metrics at a specific threshold.

    Args:
        y_true: True labels
        probabilities: Predicted probabilities
        threshold: Decision threshold

    Returns:
        Dictionary with metrics at the specified threshold

    Example:
        metrics = calculate_metrics_at_threshold(y_true, probs, threshold=0.75)
    """
    y_pred = apply_threshold(probabilities, threshold)
    return calculate_all_metrics(y_true, y_pred)


def find_optimal_threshold(y_true: np.ndarray,
                           probabilities: np.ndarray,
                           metric: str = 'f1_score',
                           thresholds: Optional[List[float]] = None) -> Tuple[float, float]:
    """
    Find optimal threshold that maximizes a given metric.

    Args:
        y_true: True labels
        probabilities: Predicted probabilities
        metric: Metric to optimize ('accuracy', 'precision', 'recall', 'f1_score')
        thresholds: List of thresholds to test (default: 0.0 to 1.0 in steps of 0.01)

    Returns:
        Tuple of (optimal_threshold, max_metric_value)

    Example:
        optimal_threshold, max_f1 = find_optimal_threshold(y_true, probs, metric='f1_score')
        print(f"Optimal threshold: {optimal_threshold:.2f}")
        print(f"Max F1 score: {max_f1:.3f}")
    """
    if thresholds is None:
        thresholds = np.arange(0.0, 1.01, 0.01)

    best_threshold = 0.5
    best_metric_value = 0.0

    for threshold in thresholds:
        metrics = calculate_metrics_at_threshold(y_true, probabilities, threshold)
        metric_value = metrics.get(metric, 0.0)

        if metric_value > best_metric_value:
            best_metric_value = metric_value
            best_threshold = threshold

    return float(best_threshold), float(best_metric_value)


# =============================================================================
# PERFORMANCE COMPARISON
# =============================================================================

def compare_metrics(metrics_before: Dict[str, float],
                    metrics_after: Dict[str, float]) -> Dict[str, Dict[str, float]]:
    """
    Compare metrics before and after model update.

    Args:
        metrics_before: Metrics before update
        metrics_after: Metrics after update

    Returns:
        Dictionary with comparison:
        - before: Original metrics
        - after: Updated metrics
        - change: Absolute change
        - change_percent: Percentage change

    Example:
        comparison = compare_metrics(metrics_before, metrics_after)
        print(f"Accuracy improved by: {comparison['accuracy']['change_percent']:.1f}%")
    """
    comparison = {}

    for metric_name in ['accuracy', 'precision', 'recall', 'f1_score']:
        before = metrics_before.get(metric_name, 0.0)
        after = metrics_after.get(metric_name, 0.0)

        change = after - before
        change_percent = (change / before * 100) if before > 0 else 0.0

        comparison[metric_name] = {
            'before': before,
            'after': after,
            'change': change,
            'change_percent': change_percent
        }

    return comparison


def format_metrics(metrics: Dict[str, float],
                   precision: int = 3,
                   as_percentage: bool = False) -> Dict[str, str]:
    """
    Format metrics for display.

    Args:
        metrics: Dictionary of metric values
        precision: Number of decimal places
        as_percentage: If True, format as percentages

    Returns:
        Dictionary with formatted metric strings

    Example:
        metrics = {'accuracy': 0.856, 'f1_score': 0.834}
        formatted = format_metrics(metrics, as_percentage=True)
        # {'accuracy': '85.6%', 'f1_score': '83.4%'}
    """
    formatted = {}

    for key, value in metrics.items():
        if as_percentage:
            formatted[key] = f"{value * 100:.{precision - 2}f}%"
        else:
            formatted[key] = f"{value:.{precision}f}"

    return formatted


# =============================================================================
# STATISTICAL MEASURES
# =============================================================================

def calculate_mean_confidence(probabilities: np.ndarray) -> float:
    """
    Calculate mean confidence score.

    Args:
        probabilities: Array of probability values

    Returns:
        Mean confidence score

    Example:
        probs = np.array([0.9, 0.6, 0.3, 0.8])
        mean_conf = calculate_mean_confidence(probs)
    """
    confidences = calculate_confidence_from_probabilities(probabilities)
    return float(np.mean(confidences))


def calculate_prediction_distribution(y_pred: np.ndarray) -> Dict[str, float]:
    """
    Calculate distribution of predictions.

    Args:
        y_pred: Predicted labels

    Returns:
        Dictionary with prediction distribution:
        - phishing_count: Number of phishing predictions
        - legitimate_count: Number of legitimate predictions
        - phishing_ratio: Ratio of phishing predictions
        - legitimate_ratio: Ratio of legitimate predictions

    Example:
        distribution = calculate_prediction_distribution(y_pred)
        print(f"Phishing: {distribution['phishing_ratio']:.1%}")
    """
    total = len(y_pred)
    phishing_count = int(np.sum(y_pred == 1))
    legitimate_count = int(np.sum(y_pred == 0))

    return {
        'phishing_count': phishing_count,
        'legitimate_count': legitimate_count,
        'phishing_ratio': phishing_count / total if total > 0 else 0.0,
        'legitimate_ratio': legitimate_count / total if total > 0 else 0.0
    }


# =============================================================================
# ERROR ANALYSIS
# =============================================================================

def identify_misclassifications(y_true: np.ndarray,
                                y_pred: np.ndarray,
                                probabilities: Optional[np.ndarray] = None) -> Dict[str, List[int]]:
    """
    Identify indices of misclassified samples.

    Args:
        y_true: True labels
        y_pred: Predicted labels
        probabilities: Optional probability values

    Returns:
        Dictionary with misclassification indices:
        - false_positives: Indices where legitimate was predicted as phishing
        - false_negatives: Indices where phishing was predicted as legitimate
        - high_confidence_errors: Misclassifications with confidence > 0.7

    Example:
        errors = identify_misclassifications(y_true, y_pred, probs)
        print(f"False positives: {len(errors['false_positives'])}")
        print(f"False negatives: {len(errors['false_negatives'])}")
    """
    # False positives: actual=0, predicted=1
    fp_indices = np.where((y_true == 0) & (y_pred == 1))[0].tolist()

    # False negatives: actual=1, predicted=0
    fn_indices = np.where((y_true == 1) & (y_pred == 0))[0].tolist()

    result = {
        'false_positives': fp_indices,
        'false_negatives': fn_indices
    }

    # High confidence errors (if probabilities provided)
    if probabilities is not None:
        confidences = calculate_confidence_from_probabilities(probabilities)
        misclassified = np.where(y_true != y_pred)[0]
        high_conf_errors = [int(idx) for idx in misclassified if confidences[idx] > 0.7]
        result['high_confidence_errors'] = high_conf_errors

    return result


# =============================================================================
# SUMMARY STATISTICS
# =============================================================================

def generate_performance_summary(y_true: np.ndarray,
                                 y_pred: np.ndarray,
                                 probabilities: Optional[np.ndarray] = None) -> Dict:
    """
    Generate comprehensive performance summary.

    Args:
        y_true: True labels
        y_pred: Predicted labels
        probabilities: Optional probability values

    Returns:
        Dictionary with comprehensive performance summary

    Example:
        summary = generate_performance_summary(y_true, y_pred, probs)
        print(f"Accuracy: {summary['metrics']['accuracy']:.3f}")
        print(f"False positives: {summary['confusion_matrix']['false_positives']}")
    """
    summary = {
        'metrics': calculate_all_metrics(y_true, y_pred),
        'confusion_matrix': calculate_confusion_matrix(y_true, y_pred),
        'distribution': calculate_prediction_distribution(y_pred),
        'sample_count': len(y_true)
    }

    if probabilities is not None:
        summary['mean_confidence'] = calculate_mean_confidence(probabilities)
        summary['misclassifications'] = identify_misclassifications(y_true, y_pred, probabilities)

    return summary