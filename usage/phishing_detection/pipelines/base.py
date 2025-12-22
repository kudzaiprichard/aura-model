"""
Base components shared across all pipelines.

This module contains:
- Data Transfer Objects (DTOs)
- Enums
- Decorators
- Common helper functions
"""

from dataclasses import dataclass
from typing import Optional, Dict, Callable
from enum import Enum
from functools import wraps
from datetime import datetime


# =============================================================================
# ENUMS
# =============================================================================

class TrainingStep(Enum):
    """Training pipeline steps with auto-calculated progress ranges."""
    CALCULATING_VERSION = ("Calculating version number", 0, 10)
    LOADING_MODEL = ("Loading base model", 10, 20)
    PREPROCESSING = ("Preprocessing batch", 20, 40)
    VALIDATING_BEFORE = ("Validating performance before update", 40, 50)
    PARTIAL_FIT = ("Performing partial_fit", 50, 70)
    VALIDATING_AFTER = ("Validating performance after update", 70, 80)
    SAVING_MODEL = ("Saving new model version", 80, 100)

    def __init__(self, description: str, start_progress: int, end_progress: int):
        self.description = description
        self.start_progress = start_progress
        self.end_progress = end_progress
        self.mid_progress = (start_progress + end_progress) // 2


# =============================================================================
# DATA TRANSFER OBJECTS (DTOs)
# =============================================================================

@dataclass
class PredictionResult:
    """
    Data Transfer Object for prediction results.

    Attributes:
        predicted_label: 'PHISHING' or 'LEGITIMATE'
        confidence_score: 0.0 to 1.0 (distance from decision boundary)
        phishing_probability: 0.0 to 1.0 (probability of phishing)
        legitimate_probability: 0.0 to 1.0 (probability of legitimate)
        threshold_used: Threshold used for alerting (0.0 to 1.0)
        should_alert: True if phishing_probability >= threshold
        raw_prediction: 0 (legitimate) or 1 (phishing)
        error: Error message if prediction failed
    """
    predicted_label: str
    confidence_score: float
    phishing_probability: float
    legitimate_probability: float
    threshold_used: float
    should_alert: bool
    raw_prediction: int
    error: Optional[str] = None


@dataclass
class TrainingStatus:
    """
    DTO for training status tracking.

    Attributes:
        is_training: Whether training is in progress
        current_step: Description of current step
        progress_percent: 0-100 progress percentage
        started_at: ISO format timestamp when training started
        estimated_completion: ISO format timestamp for estimated completion
        version_number: Version being created (e.g., "v1_2")
        corrections_count: Number of correction emails in batch
        error: Error message if training failed
    """
    is_training: bool
    current_step: Optional[str]
    progress_percent: int
    started_at: Optional[str]
    estimated_completion: Optional[str]
    version_number: Optional[str]
    corrections_count: int
    error: Optional[str]


@dataclass
class OnlineLearningResult:
    """
    DTO for online learning results.

    Attributes:
        success: Whether training succeeded
        version_number: New version number created (e.g., "v1_2")
        emails_processed: Number of emails successfully processed
        performance_before: Metrics before update (accuracy, precision, etc.)
        performance_after: Metrics after update
        timestamp: ISO format timestamp
        model_files: Paths to saved model files
        error: Error message if training failed
    """
    success: bool
    version_number: Optional[str]
    emails_processed: int
    performance_before: Optional[dict]
    performance_after: Optional[dict]
    timestamp: str
    model_files: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class ModelInfo:
    """
    DTO for model information.

    Attributes:
        version_number: Version number (e.g., "v1_2")
        model_name: Model class name (e.g., "MLPClassifier")
        model_type: Full model type string
        threshold: Prediction threshold (0.0 to 1.0)
        is_active: Whether this is the active model
        trained_timestamp: When model was trained
        performance_metrics: Accuracy, precision, recall, F1
        training_info: Training details
    """
    version_number: str
    model_name: str
    model_type: str
    threshold: float
    is_active: bool
    trained_timestamp: str
    performance_metrics: dict
    training_info: dict


@dataclass
class FileValidationResult:
    """
    DTO for file validation results.

    Attributes:
        all_valid: Whether all files exist and are valid
        missing_files: List of missing file paths
        validated_files: Dict of validated files with metadata
    """
    all_valid: bool
    missing_files: list
    validated_files: dict


@dataclass
class CleanedEmail:
    """
    DTO for cleaned email data.

    Attributes:
        sender: Cleaned sender (e.g., "name <email@domain.com>")
        subject: Cleaned subject
        body: Cleaned body (HTML removed, URLs preserved)
        urls: True if URLs detected, False otherwise
    """
    sender: str
    subject: str
    body: str
    urls: bool


# =============================================================================
# DECORATORS
# =============================================================================

def training_step(step: TrainingStep):
    """
    Decorator to automatically handle progress tracking and error handling for training steps.

    Usage:
        @training_step(TrainingStep.LOADING_MODEL)
        def _step_load_model(self):
            # Your logic here
            return model

    Args:
        step: TrainingStep enum defining the step name and progress range
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Update status at step start
            if hasattr(self, '_update_progress'):
                self._update_progress(step, 'start')

            try:
                # Execute the step
                result = func(self, *args, **kwargs)

                # Update status at step completion
                if hasattr(self, '_update_progress'):
                    self._update_progress(step, 'complete')

                return result

            except Exception as e:
                # Update status on error
                error_msg = f"{step.description} failed: {str(e)}"
                if hasattr(self, '_update_progress'):
                    self._update_progress(step, 'error', error=error_msg)

                # Re-raise to be caught by calling function
                raise

        return wrapper

    return decorator


# =============================================================================
# COMMON HELPER FUNCTIONS
# =============================================================================

def get_timestamp() -> str:
    """
    Get current timestamp in ISO format.

    Returns:
        ISO format timestamp string
    """
    return datetime.now().isoformat()


def format_percentage(value: float) -> str:
    """
    Format float as percentage string.

    Args:
        value: Float value (0.0 to 1.0)

    Returns:
        Formatted percentage (e.g., "85.3%")
    """
    return f"{value * 100:.1f}%"


def calculate_confidence(probability: float) -> float:
    """
    Calculate confidence score from probability.

    Confidence is the distance from the decision boundary (0.5).
    Higher confidence means prediction is more certain.

    Args:
        probability: Probability value (0.0 to 1.0)

    Returns:
        Confidence score (0.0 to 1.0)

    Examples:
        >>> calculate_confidence(0.5)  # At decision boundary
        0.0
        >>> calculate_confidence(0.75)  # 25% away from boundary
        0.5
        >>> calculate_confidence(1.0)  # Maximum confidence
        1.0
    """
    return abs(probability - 0.5) * 2


def validate_threshold(threshold: float) -> float:
    """
    Validate and normalize threshold value.

    Args:
        threshold: Threshold value (can be 0-100 or 0-1)

    Returns:
        Normalized threshold (0.0 to 1.0)

    Raises:
        ValueError: If threshold is invalid
    """
    if threshold < 0:
        raise ValueError(f"Threshold must be non-negative, got {threshold}")

    # Convert percentage to decimal if needed
    if threshold > 1.0:
        if threshold > 100:
            raise ValueError(f"Threshold must be <= 100, got {threshold}")
        threshold = threshold / 100.0

    return threshold


def print_progress_bar(current: int, total: int, prefix: str = '',
                       suffix: str = '', length: int = 50):
    """
    Print a progress bar to console.

    Args:
        current: Current progress value
        total: Total value for 100%
        prefix: Prefix text before bar
        suffix: Suffix text after bar
        length: Length of progress bar in characters

    Example:
        >>> print_progress_bar(50, 100, prefix='Progress:', suffix='Complete')
        Progress: |█████████████████████████                         | 50% Complete
    """
    percent = 100 * (current / float(total))
    filled_length = int(length * current // total)
    bar = '█' * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent:.1f}% {suffix}', end='', flush=True)

    # Print newline on completion
    if current == total:
        print()


# =============================================================================
# CONSTANTS
# =============================================================================

# Default paths (relative to project root)
DEFAULT_MODEL_DIR = './artifacts'
DEFAULT_METADATA_PATH = './artifacts/model_metadata.json'
DEFAULT_STATUS_PATH = './storage/training_status.json'
DEFAULT_COMPONENTS_DIR = './artifacts/pipeline_components'

# Model configuration
DEFAULT_THRESHOLD = 0.75  # 75% phishing probability triggers alert
FEATURE_COUNT = 7015  # 2000 subject + 5000 body + 15 engineered

# Training configuration
VALID_LABELS = [0, 1]  # 0 = legitimate, 1 = phishing
MIN_BATCH_SIZE = 1
MAX_BATCH_SIZE = 10000

# Validation
MIN_BODY_LENGTH = 10  # Minimum characters in cleaned body
REQUIRED_EMAIL_FIELDS = ['sender', 'subject', 'body']
REQUIRED_TRAINING_FIELDS = ['sender', 'subject', 'body', 'label']