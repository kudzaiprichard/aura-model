"""
Stateless prediction pipeline for phishing detection.

Key Features:
- No singleton pattern - each instance is independent
- Lazy loading - model loaded on first predict() call
- No cached state - can reload artifacts dynamically
- Thread-safe - separate instances per thread
- Multi-model support - test multiple versions simultaneously
"""

import warnings
import numpy as np
from pathlib import Path
from typing import Optional

from .base import (
    PredictionResult,
    get_timestamp,
    calculate_confidence,
    validate_threshold,
    DEFAULT_THRESHOLD
)


class PredictionPipeline:
    """
    Stateless prediction pipeline for phishing detection.

    This pipeline is designed to be:
    1. Stateless - no cached state between predictions
    2. Reusable - can create multiple instances with different artifacts
    3. Thread-safe - each instance operates independently
    4. Hot-swappable - load new artifacts without restart

    Usage:
        # Create pipeline with specific model
        pipeline = PredictionPipeline(
            model_path='./artifacts/v1_2/production/phishing_detector_mlp_classifier.pkl',
            cleaner=cleaner,
            feature_extractor=extractor,
            threshold=75.0,
            verbose=False
        )

        # Predict
        result = pipeline.predict(
            sender='sender@example.com',
            subject='Test email',
            body='Email content...'
        )

        # Test multiple artifacts simultaneously
        pipeline_v1 = PredictionPipeline(model_path='v1_0/...')
        pipeline_v2 = PredictionPipeline(model_path='v1_1/...')

        result_v1 = pipeline_v1.predict(...)
        result_v2 = pipeline_v2.predict(...)
    """

    def __init__(self,
                 model_path: str,
                 cleaner,
                 feature_extractor,
                 threshold: float = DEFAULT_THRESHOLD,
                 verbose: bool = False):
        """
        Initialize prediction pipeline.

        Args:
            model_path: Path to trained model pickle file
            cleaner: EmailCleaner instance (stateless)
            feature_extractor: EmailFeatureExtractor instance (stateless)
            threshold: Phishing probability threshold (0-100 or 0-1)
            verbose: If True, print detailed logs

        Raises:
            FileNotFoundError: If model file doesn't exist
            ValueError: If threshold is invalid
        """
        self.model_path = model_path
        self.cleaner = cleaner
        self.feature_extractor = feature_extractor
        self.verbose = verbose

        # Validate threshold
        self.threshold = validate_threshold(threshold)

        # Validate model path exists
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        # Lazy-loaded model (loaded on first predict call)
        self._model = None
        self._model_name = None

        if self.verbose:
            print(f"[PredictionPipeline] Initialized (model will be loaded on first prediction)")
            print(f"[PredictionPipeline] Model path: {model_path}")
            print(f"[PredictionPipeline] Threshold: {self.threshold * 100:.1f}%")

    def _load_model(self):
        """
        Lazy load model from disk.

        This method is called automatically on first predict() call.
        Model is loaded into memory and cached for subsequent predictions.

        Returns:
            Loaded model object
        """
        if self.verbose:
            print(f"[PredictionPipeline] Loading model from: {self.model_path}")

        import pickle

        with open(self.model_path, 'rb') as f:
            model = pickle.load(f)

        self._model_name = type(model).__name__

        if self.verbose:
            print(f"[PredictionPipeline] Model loaded: {self._model_name}")

        return model

    def reload_model(self):
        """
        Manually reload model from disk.

        Useful when you want to refresh the model without creating a new pipeline instance.

        Example:
            pipeline = PredictionPipeline(model_path='v1_0/...')
            result1 = pipeline.predict(...)  # Uses v1_0

            # Update model file on disk
            pipeline.model_path = 'v1_1/...'
            pipeline.reload_model()  # Reload from disk

            result2 = pipeline.predict(...)  # Uses v1_1
        """
        if self.verbose:
            print("[PredictionPipeline] Reloading model...")

        self._model = None
        self._model = self._load_model()

        if self.verbose:
            print("[PredictionPipeline] Model reloaded successfully")

    def predict(self,
                sender: str,
                subject: str,
                body: str,
                verbose: Optional[bool] = None) -> PredictionResult:
        """
        Predict if an email is phishing or legitimate.

        Pipeline execution:
        1. Clean email (remove HTML, preserve URLs/!/? for features)
        2. Extract 15 engineered features + 7000 TF-IDF features
        3. Predict with trained model (lazy-loaded on first call)
        4. Calculate confidence scores
        5. Apply threshold for alerting

        Args:
            sender: Raw sender field (e.g., "John Doe <john@example.com>")
            subject: Raw subject line
            body: Raw email body (can contain HTML)
            verbose: Override instance verbose setting for this prediction

        Returns:
            PredictionResult: DTO with prediction results

        Example:
            result = pipeline.predict(
                sender='suspicious@phish.xyz',
                subject='URGENT!!! Verify Account',
                body='Click here: http://fake-site.com'
            )

            print(f"Prediction: {result.predicted_label}")
            print(f"Confidence: {result.confidence_score * 100:.1f}%")
            print(f"Should Alert: {result.should_alert}")
        """
        # Use instance verbose if not overridden
        show_verbose = verbose if verbose is not None else self.verbose

        # Minimal logging when verbose=False
        if not show_verbose:
            print("[PredictionPipeline] Starting email prediction...")
        else:
            print("\n" + "=" * 80)
            print("[PredictionPipeline] ===== EMAIL PREDICTION PIPELINE =====")
            print("=" * 80)

        try:
            # Step 1: Lazy load model if not already loaded
            if self._model is None:
                self._model = self._load_model()

            # Step 2: Clean email
            if show_verbose:
                print("[PredictionPipeline] Step 1/3: Cleaning email")

            cleaned_email = self.cleaner.clean_email(
                sender=sender,
                subject=subject,
                body=body
            )

            if show_verbose:
                print(f"[PredictionPipeline] Email cleaned successfully")

            # Step 3: Extract features
            if show_verbose:
                print("[PredictionPipeline] Step 2/3: Extracting features")

            feature_vector = self.feature_extractor.process_email(
                cleaned_email,
                verbose=show_verbose
            )

            if show_verbose:
                print(f"[PredictionPipeline] Features extracted: {feature_vector.shape}")

            # Step 4: Predict
            if show_verbose:
                print("[PredictionPipeline] Step 3/3: Running model prediction")

            # Suppress sklearn warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                # Get prediction
                raw_prediction = self._model.predict(feature_vector)[0]

                # Get probability scores
                if hasattr(self._model, 'predict_proba'):
                    # For artifacts with predict_proba (MLPClassifier, SGD with log_loss)
                    probabilities = self._model.predict_proba(feature_vector)[0]
                    legitimate_prob = probabilities[0]
                    phishing_prob = probabilities[1]

                elif hasattr(self._model, 'decision_function'):
                    # For artifacts with decision_function (SGD with hinge, PAC)
                    decision = self._model.decision_function(feature_vector)[0]

                    # Convert to probability using sigmoid
                    phishing_prob = 1 / (1 + np.exp(-decision))
                    legitimate_prob = 1 - phishing_prob

                else:
                    # Fallback: binary prediction only
                    phishing_prob = float(raw_prediction)
                    legitimate_prob = 1 - phishing_prob

            # Calculate confidence
            confidence = calculate_confidence(phishing_prob)

            # Determine label
            predicted_label = 'PHISHING' if raw_prediction == 1 else 'LEGITIMATE'

            # Apply threshold for alerting
            should_alert = phishing_prob >= self.threshold

            # Build result DTO
            result = PredictionResult(
                predicted_label=predicted_label,
                confidence_score=float(confidence),
                phishing_probability=float(phishing_prob),
                legitimate_probability=float(legitimate_prob),
                threshold_used=float(self.threshold),
                should_alert=bool(should_alert),
                raw_prediction=int(raw_prediction)
            )

            if show_verbose:
                print("\n" + "=" * 80)
                print("[PredictionPipeline] ===== PREDICTION RESULT =====")
                print("=" * 80)
                print(f"Predicted Label: {result.predicted_label}")
                print(f"Confidence: {result.confidence_score * 100:.2f}%")
                print(f"Phishing Probability: {result.phishing_probability * 100:.2f}%")
                print(f"Should Alert: {'YES' if result.should_alert else 'NO'}")
                print("=" * 80 + "\n")
            else:
                print(f"[PredictionPipeline] Prediction complete: {result.predicted_label} "
                      f"(confidence: {result.confidence_score * 100:.1f}%)\n")

            return result

        except Exception as e:
            error_msg = f"Prediction failed: {str(e)}"

            if show_verbose:
                print(f"[PredictionPipeline] Error: {error_msg}")
            else:
                print(f"[PredictionPipeline] Prediction failed: {error_msg}\n")

            return PredictionResult(
                predicted_label='ERROR',
                confidence_score=0.0,
                phishing_probability=0.0,
                legitimate_probability=0.0,
                threshold_used=self.threshold,
                should_alert=False,
                raw_prediction=-1,
                error=error_msg
            )

    def predict_batch(self,
                      emails: list,
                      verbose: Optional[bool] = None) -> list:
        """
        Predict multiple emails in batch.

        Args:
            emails: List of email dicts with keys: 'sender', 'subject', 'body'
            verbose: Override instance verbose setting

        Returns:
            List of PredictionResult DTOs

        Example:
            emails = [
                {'sender': 'alice@example.com', 'subject': 'Hi', 'body': 'Hello'},
                {'sender': 'bob@phish.xyz', 'subject': 'URGENT!!!', 'body': 'Click here'}
            ]
            results = pipeline.predict_batch(emails)
        """
        show_verbose = verbose if verbose is not None else self.verbose

        if not show_verbose:
            print(f"[PredictionPipeline] Starting batch prediction for {len(emails)} emails...")
        else:
            print(f"\n{'=' * 80}")
            print(f"[PredictionPipeline] ===== BATCH PREDICTION =====")
            print(f"{'=' * 80}")
            print(f"Total emails: {len(emails)}")

        results = []

        for i, email in enumerate(emails, 1):
            if show_verbose:
                print(f"\n[PredictionPipeline] Processing email {i}/{len(emails)}")

            try:
                result = self.predict(
                    sender=email['sender'],
                    subject=email['subject'],
                    body=email['body'],
                    verbose=False  # Don't show verbose for each email
                )
                results.append(result)

                if show_verbose:
                    print(f"Email {i}: {result.predicted_label}")

            except Exception as e:
                if show_verbose:
                    print(f"Email {i}: Error - {str(e)}")

                results.append(PredictionResult(
                    predicted_label='ERROR',
                    confidence_score=0.0,
                    phishing_probability=0.0,
                    legitimate_probability=0.0,
                    threshold_used=self.threshold,
                    should_alert=False,
                    raw_prediction=-1,
                    error=str(e)
                ))

        # Summary
        successful = sum(1 for r in results if r.error is None)
        phishing = sum(1 for r in results if r.predicted_label == 'PHISHING')

        if show_verbose:
            print(f"\n{'=' * 80}")
            print("[PredictionPipeline] ===== BATCH SUMMARY =====")
            print(f"{'=' * 80}")
            print(f"Processed: {successful}/{len(emails)}")
            print(f"Phishing detected: {phishing}")
            print(f"{'=' * 80}\n")
        else:
            print(f"[PredictionPipeline] Batch complete: {successful}/{len(emails)} successful, "
                  f"{phishing} phishing detected\n")

        return results

    def get_model_info(self) -> dict:
        """
        Get information about the loaded model.

        Returns:
            dict: Model information including type, path, threshold
        """
        # Lazy load if needed
        if self._model is None:
            self._model = self._load_model()

        return {
            'model_name': self._model_name,
            'model_type': str(type(self._model)),
            'model_path': self.model_path,
            'threshold_percent': self.threshold * 100,
            'threshold_decimal': self.threshold,
            'has_predict_proba': hasattr(self._model, 'predict_proba'),
            'has_decision_function': hasattr(self._model, 'decision_function'),
            'model_params': self._model.get_params() if hasattr(self._model, 'get_params') else {}
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_prediction_pipeline(model_path: str,
                               cleaner,
                               feature_extractor,
                               threshold: float = DEFAULT_THRESHOLD,
                               verbose: bool = False) -> PredictionPipeline:
    """
    Factory function to create a new prediction pipeline instance.

    Args:
        model_path: Path to trained model
        cleaner: EmailCleaner instance
        feature_extractor: EmailFeatureExtractor instance
        threshold: Prediction threshold (0-100 or 0-1)
        verbose: Enable detailed logging

    Returns:
        New PredictionPipeline instance

    Example:
        pipeline = create_prediction_pipeline(
            model_path='./artifacts/v1_2/production/phishing_detector_mlp_classifier.pkl',
            cleaner=cleaner,
            feature_extractor=extractor,
            threshold=75
        )
    """
    return PredictionPipeline(
        model_path=model_path,
        cleaner=cleaner,
        feature_extractor=feature_extractor,
        threshold=threshold,
        verbose=verbose
    )