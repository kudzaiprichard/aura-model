"""
Input validation utilities for phishing detection pipeline.

This module provides validation functions for:
- Email fields (sender, subject, body)
- Training data (labels, batch size)
- File paths
- Model compatibility
- Threshold values
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple


# =============================================================================
# EMAIL VALIDATION
# =============================================================================

def validate_email_field(field_value: str,
                         field_name: str,
                         min_length: int = 1,
                         allow_empty: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Validate a single email field.

    Args:
        field_value: Field value to validate
        field_name: Name of field for error messages
        min_length: Minimum length after stripping
        allow_empty: If True, empty strings are valid

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Example:
        is_valid, error = validate_email_field(sender, "sender", min_length=3)
        if not is_valid:
            print(f"Validation failed: {error}")
    """
    # Check if None
    if field_value is None:
        return False, f"{field_name} cannot be None"

    # Convert to string
    field_str = str(field_value).strip()

    # Check if empty
    if len(field_str) == 0:
        if allow_empty:
            return True, None
        return False, f"{field_name} cannot be empty"

    # Check minimum length
    if len(field_str) < min_length:
        return False, f"{field_name} must be at least {min_length} characters long"

    return True, None


def validate_email_fields(sender: str,
                          subject: str,
                          body: str,
                          min_body_length: int = 10) -> Tuple[bool, Optional[str]]:
    """
    Validate all email fields for prediction.

    Args:
        sender: Email sender field
        subject: Email subject field
        body: Email body field
        min_body_length: Minimum body length

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_email_fields(sender, subject, body)
        if not is_valid:
            raise ValueError(error)
    """
    # Validate sender
    is_valid, error = validate_email_field(sender, "sender", min_length=3)
    if not is_valid:
        return False, error

    # Validate subject
    is_valid, error = validate_email_field(subject, "subject", min_length=1)
    if not is_valid:
        return False, error

    # Validate body
    is_valid, error = validate_email_field(body, "body", min_length=min_body_length)
    if not is_valid:
        return False, error

    return True, None


def validate_training_email(email: dict) -> Tuple[bool, Optional[str]]:
    """
    Validate a single email for training (must include label).

    Args:
        email: Email dictionary with keys: sender, subject, body, label

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        email = {'sender': '...', 'subject': '...', 'body': '...', 'label': 1}
        is_valid, error = validate_training_email(email)
    """
    # Check required fields exist
    required_fields = ['sender', 'subject', 'body', 'label']
    for field in required_fields:
        if field not in email:
            return False, f"Missing required field: {field}"

    # Validate email fields
    is_valid, error = validate_email_fields(
        email['sender'],
        email['subject'],
        email['body']
    )
    if not is_valid:
        return False, error

    # Validate label
    is_valid, error = validate_label(email['label'])
    if not is_valid:
        return False, error

    return True, None


def validate_training_batch(emails: list,
                            min_batch_size: int = 1,
                            max_batch_size: int = 10000) -> Tuple[bool, Optional[str]]:
    """
    Validate a batch of emails for training.

    Args:
        emails: List of email dictionaries
        min_batch_size: Minimum batch size
        max_batch_size: Maximum batch size

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        batch = [email1, email2, email3]
        is_valid, error = validate_training_batch(batch)
        if not is_valid:
            raise ValueError(error)
    """
    # Check if list
    if not isinstance(emails, list):
        return False, "Emails must be a list"

    # Check batch size
    if len(emails) < min_batch_size:
        return False, f"Batch size must be at least {min_batch_size}, got {len(emails)}"

    if len(emails) > max_batch_size:
        return False, f"Batch size must be at most {max_batch_size}, got {len(emails)}"

    # Validate each email
    for i, email in enumerate(emails):
        is_valid, error = validate_training_email(email)
        if not is_valid:
            return False, f"Email {i + 1}: {error}"

    return True, None


# =============================================================================
# LABEL VALIDATION
# =============================================================================

def validate_label(label) -> Tuple[bool, Optional[str]]:
    """
    Validate a label value.

    Args:
        label: Label value (should be 0 or 1)

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_label(1)
    """
    # Check if integer
    try:
        label_int = int(label)
    except (TypeError, ValueError):
        return False, f"Label must be integer, got {type(label).__name__}"

    # Check valid values
    if label_int not in [0, 1]:
        return False, f"Label must be 0 (legitimate) or 1 (phishing), got {label_int}"

    return True, None


def validate_labels(labels: list) -> Tuple[bool, Optional[str]]:
    """
    Validate a list of labels.

    Args:
        labels: List of label values

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        labels = [0, 1, 0, 1, 1]
        is_valid, error = validate_labels(labels)
    """
    for i, label in enumerate(labels):
        is_valid, error = validate_label(label)
        if not is_valid:
            return False, f"Label {i + 1}: {error}"

    return True, None


# =============================================================================
# FILE PATH VALIDATION
# =============================================================================

def validate_file_exists(file_path: str,
                         file_description: str = "File") -> Tuple[bool, Optional[str]]:
    """
    Validate that a file exists.

    Args:
        file_path: Path to file
        file_description: Description for error message

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_file_exists('./artifacts/model.pkl', "Model file")
        if not is_valid:
            raise FileNotFoundError(error)
    """
    path = Path(file_path)

    if not path.exists():
        return False, f"{file_description} not found: {file_path}"

    if not path.is_file():
        return False, f"Path is not a file: {file_path}"

    if not os.access(file_path, os.R_OK):
        return False, f"File not readable: {file_path}"

    return True, None


def validate_directory_exists(dir_path: str,
                              dir_description: str = "Directory") -> Tuple[bool, Optional[str]]:
    """
    Validate that a directory exists.

    Args:
        dir_path: Path to directory
        dir_description: Description for error message

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_directory_exists('./artifacts', "Models directory")
    """
    path = Path(dir_path)

    if not path.exists():
        return False, f"{dir_description} not found: {dir_path}"

    if not path.is_dir():
        return False, f"Path is not a directory: {dir_path}"

    return True, None


def validate_model_files(model_path: str,
                         subject_vectorizer_path: str,
                         body_vectorizer_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that all model files exist.

    Args:
        model_path: Path to model file
        subject_vectorizer_path: Path to subject vectorizer
        body_vectorizer_path: Path to body vectorizer

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_model_files(
            model_path='./artifacts/v1_2/production/phishing_detector_mlp_classifier.pkl',
            subject_vectorizer_path='./artifacts/pipeline_components/subject_vectorizer.pkl',
            body_vectorizer_path='./artifacts/pipeline_components/body_vectorizer.pkl'
        )
    """
    # Validate model file
    is_valid, error = validate_file_exists(model_path, "Model file")
    if not is_valid:
        return False, error

    # Validate subject vectorizer
    is_valid, error = validate_file_exists(subject_vectorizer_path, "Subject vectorizer")
    if not is_valid:
        return False, error

    # Validate body vectorizer
    is_valid, error = validate_file_exists(body_vectorizer_path, "Body vectorizer")
    if not is_valid:
        return False, error

    return True, None


# =============================================================================
# MODEL COMPATIBILITY VALIDATION
# =============================================================================

def validate_model_has_partial_fit(model) -> Tuple[bool, Optional[str]]:
    """
    Validate that a model supports partial_fit for online learning.

    Args:
        model: Loaded model object

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        model = load_model('model.pkl')
        is_valid, error = validate_model_has_partial_fit(model)
        if not is_valid:
            raise ValueError(error)
    """
    if not hasattr(model, 'partial_fit'):
        model_name = type(model).__name__
        return False, (
            f"Model {model_name} does not support partial_fit. "
            f"Only MLPClassifier and SGDClassifier support online learning."
        )

    return True, None


def validate_model_has_predict_proba(model) -> Tuple[bool, Optional[str]]:
    """
    Validate that a model supports predict_proba for probability outputs.

    Args:
        model: Loaded model object

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_model_has_predict_proba(model)
    """
    if not hasattr(model, 'predict_proba'):
        model_name = type(model).__name__
        return False, f"Model {model_name} does not support predict_proba"

    return True, None


# =============================================================================
# THRESHOLD VALIDATION
# =============================================================================

def validate_threshold(threshold: float) -> Tuple[bool, Optional[str]]:
    """
    Validate a threshold value.

    Args:
        threshold: Threshold value (0-1 or 0-100)

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_threshold(0.75)
        if not is_valid:
            raise ValueError(error)
    """
    # Check if numeric
    try:
        threshold_float = float(threshold)
    except (TypeError, ValueError):
        return False, f"Threshold must be numeric, got {type(threshold).__name__}"

    # Check range
    if threshold_float < 0:
        return False, f"Threshold must be non-negative, got {threshold_float}"

    if threshold_float > 100:
        return False, f"Threshold must be <= 100, got {threshold_float}"

    return True, None


def normalize_threshold(threshold: float) -> float:
    """
    Normalize threshold to 0-1 range.

    Args:
        threshold: Threshold value (0-1 or 0-100)

    Returns:
        Normalized threshold (0.0 to 1.0)

    Example:
        # Convert percentage to decimal
        normalized = normalize_threshold(75)  # Returns 0.75

        # Already in decimal form
        normalized = normalize_threshold(0.75)  # Returns 0.75
    """
    # Validate first
    is_valid, error = validate_threshold(threshold)
    if not is_valid:
        raise ValueError(error)

    # Convert percentage to decimal if needed
    if threshold > 1.0:
        return threshold / 100.0

    return float(threshold)


# =============================================================================
# FEATURE VECTOR VALIDATION
# =============================================================================

def validate_feature_vector(features, expected_shape: Tuple[int, int]) -> Tuple[bool, Optional[str]]:
    """
    Validate feature vector shape.

    Args:
        features: Feature array/matrix
        expected_shape: Expected shape (e.g., (1, 7015))

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_feature_vector(features, expected_shape=(1, 7015))
    """
    # Check if array-like
    if not hasattr(features, 'shape'):
        return False, "Features must be array-like with shape attribute"

    # Check shape
    if features.shape != expected_shape:
        return False, (
            f"Feature vector has incorrect shape. "
            f"Expected {expected_shape}, got {features.shape}"
        )

    return True, None


# =============================================================================
# VERSION VALIDATION
# =============================================================================

def validate_version_number(version: str) -> Tuple[bool, Optional[str]]:
    """
    Validate version number format.

    Args:
        version: Version string (e.g., "v1_2")

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_version_number("v1_2")
    """
    # Check if string
    if not isinstance(version, str):
        return False, f"Version must be string, got {type(version).__name__}"

    # Check format (v{major}_{minor})
    if not version.startswith('v'):
        return False, f"Version must start with 'v', got: {version}"

    parts = version[1:].split('_')

    if len(parts) != 2:
        return False, f"Version must be in format 'v{'{major}'}_{'{minor}'}', got: {version}"

    # Check major and minor are integers
    try:
        major = int(parts[0])
        minor = int(parts[1])
    except ValueError:
        return False, f"Version parts must be integers, got: {version}"

    # Check non-negative
    if major < 0 or minor < 0:
        return False, f"Version parts must be non-negative, got: {version}"

    return True, None


# =============================================================================
# BATCH VALIDATION
# =============================================================================

def validate_batch_size(batch_size: int,
                        min_size: int = 1,
                        max_size: int = 10000) -> Tuple[bool, Optional[str]]:
    """
    Validate batch size.

    Args:
        batch_size: Number of items in batch
        min_size: Minimum allowed size
        max_size: Maximum allowed size

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_batch_size(50, min_size=1, max_size=100)
    """
    # Check if integer
    try:
        size = int(batch_size)
    except (TypeError, ValueError):
        return False, f"Batch size must be integer, got {type(batch_size).__name__}"

    # Check range
    if size < min_size:
        return False, f"Batch size must be at least {min_size}, got {size}"

    if size > max_size:
        return False, f"Batch size must be at most {max_size}, got {size}"

    return True, None


# =============================================================================
# COMPREHENSIVE VALIDATION
# =============================================================================

def validate_prediction_inputs(sender: str,
                               subject: str,
                               body: str,
                               model_path: str,
                               threshold: float = 0.75) -> Tuple[bool, Optional[str]]:
    """
    Comprehensive validation for prediction pipeline inputs.

    Args:
        sender: Email sender
        subject: Email subject
        body: Email body
        model_path: Path to model file
        threshold: Prediction threshold

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_prediction_inputs(
            sender='test@example.com',
            subject='Test',
            body='Test email body...',
            model_path='./artifacts/model.pkl',
            threshold=0.75
        )
    """
    # Validate email fields
    is_valid, error = validate_email_fields(sender, subject, body)
    if not is_valid:
        return False, error

    # Validate model file
    is_valid, error = validate_file_exists(model_path, "Model file")
    if not is_valid:
        return False, error

    # Validate threshold
    is_valid, error = validate_threshold(threshold)
    if not is_valid:
        return False, error

    return True, None


def validate_training_inputs(emails: list,
                             base_model_path: str,
                             output_dir: str,
                             min_batch_size: int = 1,
                             max_batch_size: int = 10000) -> Tuple[bool, Optional[str]]:
    """
    Comprehensive validation for training pipeline inputs.

    Args:
        emails: List of training emails
        base_model_path: Path to base model
        output_dir: Output directory for new version
        min_batch_size: Minimum batch size
        max_batch_size: Maximum batch size

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        is_valid, error = validate_training_inputs(
            emails=training_batch,
            base_model_path='./artifacts/v1_0/production/phishing_detector_mlp_classifier.pkl',
            output_dir='./artifacts'
        )
    """
    # Validate training batch
    is_valid, error = validate_training_batch(emails, min_batch_size, max_batch_size)
    if not is_valid:
        return False, error

    # Validate base model exists
    is_valid, error = validate_file_exists(base_model_path, "Base model")
    if not is_valid:
        return False, error

    # Validate output directory exists
    is_valid, error = validate_directory_exists(output_dir, "Output directory")
    if not is_valid:
        return False, error

    return True, None