"""
Model loading utilities for phishing detection pipeline.

This module provides utilities for:
- Loading trained artifacts from disk
- Loading TF-IDF vectorizers
- Validating model files
- File I/O operations with proper error handling
"""

import os
import pickle
import joblib
from pathlib import Path
from typing import Tuple, Optional


class ModelLoader:
    """
    Utility class for loading artifacts and pipeline components from disk.

    This class provides safe, validated loading of:
    - Trained ML artifacts (pickle files)
    - TF-IDF vectorizers (joblib files)
    - Model metadata (JSON files)

    All methods include proper error handling and file validation.

    Usage:
        loader = ModelLoader(verbose=True)

        # Load model
        model = loader.load_model('./artifacts/v1_2/production/phishing_detector_mlp_classifier.pkl')

        # Load vectorizers
        subject_vec, body_vec = loader.load_vectorizers(
            subject_path='./artifacts/pipeline_components/subject_vectorizer.pkl',
            body_path='./artifacts/pipeline_components/body_vectorizer.pkl'
        )

        # Validate files before loading
        is_valid = loader.validate_file_path('./artifacts/model.pkl')
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize ModelLoader.

        Args:
            verbose: If True, print detailed loading logs
        """
        self.verbose = verbose

        if self.verbose:
            print("[ModelLoader] Initialized")

    def validate_file_path(self, file_path: str, file_type: str = "file") -> bool:
        """
        Validate that a file path exists and is accessible.

        Args:
            file_path: Path to file
            file_type: Description of file type for error messages

        Returns:
            True if file exists and is readable

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file isn't readable
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"{file_type} not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"File not readable: {file_path}")

        if self.verbose:
            size_kb = path.stat().st_size / 1024
            print(f"[ModelLoader] {file_type} validated: {file_path} ({size_kb:.1f} KB)")

        return True

    def load_model(self, model_path: str, validate_partial_fit: bool = False):
        """
        Load a trained model from pickle file.

        Args:
            model_path: Path to model pickle file
            validate_partial_fit: If True, verify model supports partial_fit

        Returns:
            Loaded model object

        Raises:
            FileNotFoundError: If model file doesn't exist
            ValueError: If model is invalid or doesn't support partial_fit
            Exception: If pickle loading fails

        Example:
            loader = ModelLoader()
            model = loader.load_model('./artifacts/v1_2/production/phishing_detector_mlp_classifier.pkl')
        """
        # Validate file exists
        self.validate_file_path(model_path, "Model file")

        if self.verbose:
            print(f"[ModelLoader] Loading model from: {model_path}")

        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
        except Exception as e:
            raise Exception(f"Failed to load model from {model_path}: {str(e)}")

        # Get model info
        model_name = type(model).__name__

        if self.verbose:
            print(f"[ModelLoader] Model loaded successfully: {model_name}")

        # Validate partial_fit support if requested
        if validate_partial_fit:
            if not hasattr(model, 'partial_fit'):
                raise ValueError(
                    f"Model {model_name} does not support partial_fit. "
                    f"Only MLPClassifier and SGDClassifier support online learning."
                )

            if self.verbose:
                print(f"[ModelLoader] Model supports partial_fit: ✓")

        return model

    def load_vectorizer(self, vectorizer_path: str, vectorizer_type: str = "vectorizer"):
        """
        Load a TF-IDF vectorizer from joblib file.

        Args:
            vectorizer_path: Path to vectorizer pickle/joblib file
            vectorizer_type: Description for error messages (e.g., "subject vectorizer")

        Returns:
            Loaded TfidfVectorizer object

        Raises:
            FileNotFoundError: If vectorizer file doesn't exist
            Exception: If loading fails

        Example:
            loader = ModelLoader()
            vectorizer = loader.load_vectorizer(
                './artifacts/pipeline_components/subject_vectorizer.pkl',
                vectorizer_type="subject vectorizer"
            )
        """
        # Validate file exists
        self.validate_file_path(vectorizer_path, vectorizer_type)

        if self.verbose:
            print(f"[ModelLoader] Loading {vectorizer_type} from: {vectorizer_path}")

        try:
            vectorizer = joblib.load(vectorizer_path)
        except Exception as e:
            raise Exception(f"Failed to load {vectorizer_type} from {vectorizer_path}: {str(e)}")

        if self.verbose:
            vocab_size = len(vectorizer.get_feature_names_out()) if hasattr(vectorizer, 'get_feature_names_out') else 0
            print(f"[ModelLoader] {vectorizer_type.capitalize()} loaded successfully (vocab size: {vocab_size})")

        return vectorizer

    def load_vectorizers(self,
                         subject_path: str,
                         body_path: str) -> Tuple:
        """
        Load both subject and body TF-IDF vectorizers.

        Args:
            subject_path: Path to subject vectorizer file
            body_path: Path to body vectorizer file

        Returns:
            Tuple of (subject_vectorizer, body_vectorizer)

        Raises:
            FileNotFoundError: If either vectorizer file doesn't exist
            Exception: If loading fails

        Example:
            loader = ModelLoader()
            subject_vec, body_vec = loader.load_vectorizers(
                subject_path='./artifacts/pipeline_components/subject_vectorizer.pkl',
                body_path='./artifacts/pipeline_components/body_vectorizer.pkl'
            )
        """
        if self.verbose:
            print("[ModelLoader] Loading vectorizers...")

        # Load subject vectorizer
        subject_vectorizer = self.load_vectorizer(subject_path, "subject vectorizer")

        # Load body vectorizer
        body_vectorizer = self.load_vectorizer(body_path, "body vectorizer")

        if self.verbose:
            print("[ModelLoader] Both vectorizers loaded successfully")

        return subject_vectorizer, body_vectorizer

    def load_pipeline_components(self,
                                 model_path: str,
                                 subject_vectorizer_path: str,
                                 body_vectorizer_path: str,
                                 validate_partial_fit: bool = False) -> Tuple:
        """
        Load all pipeline components at once.

        Args:
            model_path: Path to model file
            subject_vectorizer_path: Path to subject vectorizer
            body_vectorizer_path: Path to body vectorizer
            validate_partial_fit: If True, verify model supports partial_fit

        Returns:
            Tuple of (model, subject_vectorizer, body_vectorizer)

        Raises:
            FileNotFoundError: If any file doesn't exist
            Exception: If loading fails

        Example:
            loader = ModelLoader()
            model, subject_vec, body_vec = loader.load_pipeline_components(
                model_path='./artifacts/v1_2/production/phishing_detector_mlp_classifier.pkl',
                subject_vectorizer_path='./artifacts/pipeline_components/subject_vectorizer.pkl',
                body_vectorizer_path='./artifacts/pipeline_components/body_vectorizer.pkl'
            )
        """
        if self.verbose:
            print("[ModelLoader] Loading all pipeline components...")

        # Load model
        model = self.load_model(model_path, validate_partial_fit=validate_partial_fit)

        # Load vectorizers
        subject_vectorizer, body_vectorizer = self.load_vectorizers(
            subject_path=subject_vectorizer_path,
            body_path=body_vectorizer_path
        )

        if self.verbose:
            print("[ModelLoader] All pipeline components loaded successfully")

        return model, subject_vectorizer, body_vectorizer

    def validate_model_compatibility(self, model) -> dict:
        """
        Validate model compatibility and get capability info.

        Args:
            model: Loaded model object

        Returns:
            Dictionary with model capabilities:
            - model_name: Model class name
            - supports_partial_fit: Whether model supports online learning
            - has_predict_proba: Whether model can output probabilities
            - has_decision_function: Whether model has decision function

        Example:
            loader = ModelLoader()
            model = loader.load_model('model.pkl')
            info = loader.validate_model_compatibility(model)

            if not info['supports_partial_fit']:
                print("Warning: Model doesn't support online learning")
        """
        info = {
            'model_name': type(model).__name__,
            'supports_partial_fit': hasattr(model, 'partial_fit'),
            'has_predict_proba': hasattr(model, 'predict_proba'),
            'has_decision_function': hasattr(model, 'decision_function'),
        }

        if self.verbose:
            print("[ModelLoader] Model compatibility check:")
            print(f"  Model: {info['model_name']}")
            print(f"  Supports partial_fit: {'✓' if info['supports_partial_fit'] else '✗'}")
            print(f"  Has predict_proba: {'✓' if info['has_predict_proba'] else '✗'}")
            print(f"  Has decision_function: {'✓' if info['has_decision_function'] else '✗'}")

        return info

    def get_file_info(self, file_path: str) -> dict:
        """
        Get information about a file.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file information:
            - path: Absolute file path
            - exists: Whether file exists
            - size_bytes: File size in bytes
            - size_kb: File size in KB
            - size_mb: File size in MB

        Example:
            loader = ModelLoader()
            info = loader.get_file_info('./artifacts/model.pkl')
            print(f"Model size: {info['size_mb']:.2f} MB")
        """
        path = Path(file_path)

        if not path.exists():
            return {
                'path': str(path.absolute()),
                'exists': False,
                'size_bytes': 0,
                'size_kb': 0.0,
                'size_mb': 0.0
            }

        size_bytes = path.stat().st_size

        return {
            'path': str(path.absolute()),
            'exists': True,
            'size_bytes': size_bytes,
            'size_kb': size_bytes / 1024,
            'size_mb': size_bytes / (1024 * 1024)
        }


# =============================================================================
# STANDALONE HELPER FUNCTIONS
# =============================================================================

def load_model(model_path: str, verbose: bool = False):
    """
    Quick helper to load a model without creating ModelLoader instance.

    Args:
        model_path: Path to model pickle file
        verbose: If True, print loading info

    Returns:
        Loaded model object

    Example:
        from artifacts.loader import load_model
        model = load_model('./artifacts/v1_2/production/phishing_detector_mlp_classifier.pkl')
    """
    loader = ModelLoader(verbose=verbose)
    return loader.load_model(model_path)


def load_vectorizers(subject_path: str, body_path: str, verbose: bool = False) -> Tuple:
    """
    Quick helper to load vectorizers without creating ModelLoader instance.

    Args:
        subject_path: Path to subject vectorizer
        body_path: Path to body vectorizer
        verbose: If True, print loading info

    Returns:
        Tuple of (subject_vectorizer, body_vectorizer)

    Example:
        from artifacts.loader import load_vectorizers
        subject_vec, body_vec = load_vectorizers(
            subject_path='./artifacts/pipeline_components/subject_vectorizer.pkl',
            body_path='./artifacts/pipeline_components/body_vectorizer.pkl'
        )
    """
    loader = ModelLoader(verbose=verbose)
    return loader.load_vectorizers(subject_path, body_path)


def validate_file(file_path: str) -> bool:
    """
    Quick helper to validate a file exists and is readable.

    Args:
        file_path: Path to file

    Returns:
        True if file is valid

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file isn't readable

    Example:
        from artifacts.loader import validate_file

        try:
            validate_file('./artifacts/model.pkl')
            print("File is valid")
        except FileNotFoundError:
            print("File not found")
    """
    loader = ModelLoader(verbose=False)
    return loader.validate_file_path(file_path)