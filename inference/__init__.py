"""AURA inference package — public API."""

from inference.auto_reviewer import AutoReviewer
from inference.detector import PhishingDetector
from inference.drift_monitor import DriftMonitor, DriftSignal, DriftStatus
from inference.online_learner import OnlineLearner
from inference.registry import ModelRegistry
from inference.schema import (
    AutoReviewFailure,
    AutoReviewResponse,
    AutoReviewSuccess,
    ConfidenceZone,
    LLMProvider,
    OnlineLearningResult,
    PredictionResult,
    ReviewLabel,
    ValidationError,
)

__all__ = [
    'PhishingDetector',
    'OnlineLearner',
    'ModelRegistry',
    'PredictionResult',
    'OnlineLearningResult',
    'ValidationError',
    'ConfidenceZone',
    'DriftMonitor',
    'DriftSignal',
    'DriftStatus',
    'AutoReviewer',
    'AutoReviewSuccess',
    'AutoReviewFailure',
    'AutoReviewResponse',
    'LLMProvider',
    'ReviewLabel',
]