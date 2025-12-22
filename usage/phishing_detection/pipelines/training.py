"""
Stateless online learning pipeline for phishing detection.

Key Features:
- No singleton pattern - each instance is independent
- Stateless - no cached training history
- Creates new model versions (doesn't overwrite)
- Supports incremental learning with partial_fit
- Thread-safe training operations
"""

import os
import json
import pickle
import warnings
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

from .base import (
    OnlineLearningResult,
    TrainingStatus,
    TrainingStep,
    training_step,
    get_timestamp,
    DEFAULT_MODEL_DIR,
    DEFAULT_METADATA_PATH,
    DEFAULT_STATUS_PATH,
    MIN_BATCH_SIZE,
    MAX_BATCH_SIZE
)


class OnlineLearningPipeline:
    """
    Stateless online learning pipeline for incremental model updates.

    This pipeline is designed to be:
    1. Stateless - no cached training history or state
    2. Version-safe - creates new versions instead of overwriting
    3. Independent - multiple instances can train simultaneously
    4. Thread-safe - separate instances per training job

    Pipeline Flow:
    1. Calculate next version number
    2. Load base model from disk
    3. Clean and preprocess batch
    4. Validate performance before update
    5. Perform partial_fit on new data
    6. Validate performance after update
    7. Save as new version with metadata

    Usage:
        # Create pipeline
        pipeline = OnlineLearningPipeline(
            base_model_path='./artifacts/v1_0/production/phishing_detector_mlp_classifier.pkl',
            cleaner=cleaner,
            feature_extractor=extractor,
            output_dir='./artifacts',
            verbose=False
        )

        # Train on new corrections
        corrections = [
            {'sender': '...', 'subject': '...', 'body': '...', 'label': 0},
            {'sender': '...', 'subject': '...', 'body': '...', 'label': 1},
        ]

        result = pipeline.partial_fit_batch(
            emails=corrections,
            parent_version='v1_0',
            validate=True
        )

        # Multiple training sessions (independent)
        pipeline1 = OnlineLearningPipeline(base_model_path='v1_0/...')
        pipeline2 = OnlineLearningPipeline(base_model_path='v1_1/...')

        result1 = pipeline1.partial_fit_batch(batch1)  # Creates v1_1
        result2 = pipeline2.partial_fit_batch(batch2)  # Creates v1_2
    """

    def __init__(self,
                 base_model_path: str,
                 cleaner,
                 feature_extractor,
                 output_dir: str = DEFAULT_MODEL_DIR,
                 metadata_path: Optional[str] = None,
                 verbose: bool = False):
        """
        Initialize online learning pipeline.

        Args:
            base_model_path: Path to base model for incremental training
            cleaner: EmailCleaner instance (stateless)
            feature_extractor: EmailFeatureExtractor instance (stateless)
            output_dir: Directory for saving new model versions
            metadata_path: Path to model metadata JSON file
            verbose: If True, print detailed logs

        Raises:
            FileNotFoundError: If base model doesn't exist
            ValueError: If model doesn't support partial_fit
        """
        self.base_model_path = base_model_path
        self.cleaner = cleaner
        self.feature_extractor = feature_extractor
        self.output_dir = output_dir
        self.metadata_path = metadata_path or os.path.join(output_dir, 'model_metadata.json')
        self.verbose = verbose

        # Create directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs('storage', exist_ok=True)

        # Validate base model exists
        if not Path(base_model_path).exists():
            raise FileNotFoundError(f"Base model not found: {base_model_path}")

        # Initialize training status (per instance, not shared)
        self._status = TrainingStatus(
            is_training=False,
            current_step=None,
            progress_percent=0,
            started_at=None,
            estimated_completion=None,
            version_number=None,
            corrections_count=0,
            error=None
        )

        if self.verbose:
            print("[OnlineLearningPipeline] Initialized")
            print(f"[OnlineLearningPipeline] Base model: {base_model_path}")
            print(f"[OnlineLearningPipeline] Output directory: {output_dir}")
        else:
            print("[OnlineLearningPipeline] Initialization complete\n")

    def _update_progress(self, step: TrainingStep, stage: str, error: str = None):
        """
        Update progress for a training step.

        Args:
            step: TrainingStep enum
            stage: 'start', 'complete', or 'error'
            error: Error message if stage is 'error'
        """
        if stage == 'start':
            progress = step.start_progress
            status = step.description
        elif stage == 'complete':
            progress = step.end_progress
            status = f"{step.description} completed"
        elif stage == 'error':
            progress = step.start_progress
            status = error
        else:
            progress = step.mid_progress
            status = step.description

        self._status.current_step = status
        self._status.progress_percent = progress

        if error:
            self._status.error = error
            self._status.is_training = False

        # Calculate estimated completion
        if self._status.is_training and self._status.started_at:
            elapsed = (datetime.now() - datetime.fromisoformat(self._status.started_at)).total_seconds()
            if progress > 0:
                total_estimated = (elapsed / progress) * 100
                remaining = total_estimated - elapsed
                estimated_completion = datetime.now().timestamp() + remaining
                self._status.estimated_completion = datetime.fromtimestamp(estimated_completion).isoformat()

        # Write to file (for external monitoring)
        try:
            status_dict = {
                'is_training': self._status.is_training,
                'current_step': self._status.current_step,
                'progress_percent': self._status.progress_percent,
                'started_at': self._status.started_at,
                'estimated_completion': self._status.estimated_completion,
                'version_number': self._status.version_number,
                'corrections_count': self._status.corrections_count,
                'error': self._status.error
            }
            with open(DEFAULT_STATUS_PATH, 'w') as f:
                json.dump(status_dict, f, indent=2)
        except Exception as e:
            if self.verbose:
                print(f"[OnlineLearningPipeline] Warning: Could not write status: {str(e)}")

        if self.verbose:
            print(f"[OnlineLearningPipeline] [{progress}%] {status}")

    def get_status(self) -> TrainingStatus:
        """
        Get current training status.

        Returns:
            TrainingStatus DTO with current progress
        """
        return self._status

    def _get_next_version_number(self) -> str:
        """
        Calculate next version number from metadata.

        Returns:
            Next version number (e.g., "v1_3")
        """
        if not os.path.exists(self.metadata_path):
            return "v1_0"

        with open(self.metadata_path, 'r') as f:
            metadata = json.load(f)

        latest_version = metadata.get('latest_version', 'v1_0')

        # Parse version (e.g., "v1_2" -> major=1, minor=2)
        parts = latest_version.replace('v', '').split('_')
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0

        # Increment minor version
        next_version = f"v{major}_{minor + 1}"

        return next_version

    def _update_metadata(self,
                         version_number: str,
                         parent_version: str,
                         performance_metrics: Dict,
                         training_info: Dict,
                         file_paths: Dict,
                         is_active: bool = False):
        """
        Update centralized model_metadata.json with new version.

        Args:
            version_number: New version number
            parent_version: Parent version
            performance_metrics: Performance metrics
            training_info: Training information
            file_paths: File paths for model components
            is_active: Whether this version is active
        """
        # Load existing metadata or create new
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {
                'metadata_version': '1.0',
                'last_updated': None,
                'active_version': None,
                'latest_version': None,
                'total_versions': 0,
                'versions': []
            }

        # Create new version entry
        new_version = {
            'version_number': version_number,
            'parent_version': parent_version,
            'is_active': is_active,
            'trained_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'training_method': 'partial_fit',
            'model_info': {
                'model_name': 'MLP_Classifier',
                'model_type': 'Multi-Layer Perceptron Neural Network',
                'threshold': performance_metrics.get('threshold', 0.75)
            },
            'performance_metrics': performance_metrics,
            'training_info': training_info,
            'file_paths': file_paths,
            'notes': f'Incremental training with {training_info["corrections_used"]} user corrections'
        }

        # Add to versions list
        metadata['versions'].append(new_version)
        metadata['latest_version'] = version_number
        metadata['total_versions'] = len(metadata['versions'])
        metadata['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Update active version if specified
        if is_active:
            for v in metadata['versions']:
                v['is_active'] = False
            new_version['is_active'] = True
            metadata['active_version'] = version_number

        # Save metadata
        with open(self.metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        if self.verbose:
            print(f"[OnlineLearningPipeline] Updated metadata: {self.metadata_path}")

    def _save_model_version(self,
                            model,
                            version_number: str,
                            parent_version: str,
                            performance_before: Dict,
                            performance_after: Dict,
                            training_info: Dict) -> Dict[str, str]:
        """
        Save model as new version with metadata.

        Args:
            model: Trained model
            version_number: New version number
            parent_version: Parent version number
            performance_before: Performance before update
            performance_after: Performance after update
            training_info: Training information

        Returns:
            Dictionary with file paths
        """
        # Create version directory
        version_dir = os.path.join(self.output_dir, version_number)
        production_dir = os.path.join(version_dir, 'production')
        os.makedirs(production_dir, exist_ok=True)

        # Save model
        model_path = os.path.join(production_dir, 'phishing_detector_mlp_classifier.pkl')
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        if self.verbose:
            print(f"[OnlineLearningPipeline] Saved model: {model_path}")

        # Build file paths
        file_paths = {
            'model': f"{version_number}/production/phishing_detector_mlp_classifier.pkl",
            'subject_vectorizer': 'pipeline_components/subject_vectorizer.pkl',
            'body_vectorizer': 'pipeline_components/body_vectorizer.pkl'
        }

        # Update metadata
        self._update_metadata(
            version_number=version_number,
            parent_version=parent_version,
            performance_metrics={
                'accuracy': performance_after['accuracy'],
                'precision': performance_after['precision'],
                'recall': performance_after['recall'],
                'f1_score': performance_after['f1_score'],
                'threshold': 0.75
            },
            training_info=training_info,
            file_paths=file_paths,
            is_active=False
        )

        return {
            'model_file_path': model_path,
            'metadata_path': self.metadata_path
        }

    def _preprocess_batch(self, emails: list) -> tuple:
        """
        Clean and extract features from batch of emails.

        Args:
            emails: List of email dicts with keys: sender, subject, body, label

        Returns:
            tuple: (X_features, y_labels, successful_count)
        """
        if self.verbose:
            print(f"[OnlineLearningPipeline] Preprocessing {len(emails)} emails")

        X_features = []
        y_labels = []
        failed = 0

        for i, email in enumerate(emails):
            try:
                # Validate required fields
                if not all(k in email for k in ['sender', 'subject', 'body', 'label']):
                    raise ValueError("Email missing required fields")

                # Clean email
                cleaned = self.cleaner.clean_email(
                    sender=email['sender'],
                    subject=email['subject'],
                    body=email['body']
                )

                # Extract features
                features = self.feature_extractor.process_email(cleaned, verbose=False)

                X_features.append(features[0])
                y_labels.append(email['label'])

            except Exception as e:
                failed += 1
                if self.verbose:
                    print(f"[OnlineLearningPipeline] Email {i + 1} failed: {str(e)[:50]}")

        if len(X_features) == 0:
            raise ValueError("No emails could be processed successfully")

        if self.verbose:
            print(f"[OnlineLearningPipeline] Processed: {len(X_features)}/{len(emails)}")

        X = np.vstack(X_features)
        y = np.array(y_labels)

        return X, y, len(X_features)

    @training_step(TrainingStep.CALCULATING_VERSION)
    def _step_calculate_version(self) -> str:
        """Step 1: Calculate next version number."""
        new_version = self._get_next_version_number()
        self._status.version_number = new_version
        if self.verbose:
            print(f"[OnlineLearningPipeline] New version: {new_version}")
        return new_version

    @training_step(TrainingStep.LOADING_MODEL)
    def _step_load_model(self):
        """Step 2: Load base model."""
        with open(self.base_model_path, 'rb') as f:
            model = pickle.load(f)

        if not hasattr(model, 'partial_fit'):
            raise ValueError(f"{type(model).__name__} does not support partial_fit")

        if self.verbose:
            print(f"[OnlineLearningPipeline] Model loaded: {type(model).__name__}")

        return model

    @training_step(TrainingStep.PREPROCESSING)
    def _step_preprocess(self, emails: list) -> tuple:
        """Step 3: Preprocess batch."""
        return self._preprocess_batch(emails)

    @training_step(TrainingStep.VALIDATING_BEFORE)
    def _step_validate_before(self, model, X, y) -> dict:
        """Step 4: Validate before update."""
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            y_pred = model.predict(X)

        metrics = {
            'accuracy': float(accuracy_score(y, y_pred)),
            'precision': float(precision_score(y, y_pred, zero_division=0)),
            'recall': float(recall_score(y, y_pred, zero_division=0)),
            'f1_score': float(f1_score(y, y_pred, zero_division=0))
        }

        if self.verbose:
            print(
                f"[OnlineLearningPipeline] Before: Accuracy={metrics['accuracy'] * 100:.1f}%, F1={metrics['f1_score']:.3f}")

        return metrics

    @training_step(TrainingStep.PARTIAL_FIT)
    def _step_partial_fit(self, model, X, y):
        """Step 5: Perform partial_fit."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            if hasattr(model, 'early_stopping'):
                model.early_stopping = False

            model.partial_fit(X, y, classes=[0, 1])

        if self.verbose:
            print("[OnlineLearningPipeline] Partial fit completed")

        return model

    @training_step(TrainingStep.VALIDATING_AFTER)
    def _step_validate_after(self, model, X, y, before: dict = None) -> dict:
        """Step 6: Validate after update."""
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            y_pred = model.predict(X)

        metrics = {
            'accuracy': float(accuracy_score(y, y_pred)),
            'precision': float(precision_score(y, y_pred, zero_division=0)),
            'recall': float(recall_score(y, y_pred, zero_division=0)),
            'f1_score': float(f1_score(y, y_pred, zero_division=0))
        }

        if self.verbose:
            print(
                f"[OnlineLearningPipeline] After: Accuracy={metrics['accuracy'] * 100:.1f}%, F1={metrics['f1_score']:.3f}")

            if before:
                acc_change = (metrics['accuracy'] - before['accuracy']) * 100
                f1_change = metrics['f1_score'] - before['f1_score']
                print(f"[OnlineLearningPipeline] Change: Accuracy={acc_change:+.1f}%, F1={f1_change:+.3f}")

        return metrics

    @training_step(TrainingStep.SAVING_MODEL)
    def _step_save_model(self, model, version: str, parent: str,
                         before: dict, after: dict, info: dict) -> dict:
        """Step 7: Save new model version."""
        return self._save_model_version(model, version, parent, before, after, info)

    def partial_fit_batch(self,
                          emails: list,
                          parent_version: Optional[str] = None,
                          validate: bool = True) -> OnlineLearningResult:
        """
        Perform online learning on a batch of labeled emails.

        Args:
            emails: List of email dicts with keys: sender, subject, body, label
            parent_version: Parent version number (e.g., "v1_0")
            validate: If True, validate performance before/after

        Returns:
            OnlineLearningResult DTO with training results

        Example:
            corrections = [
                {'sender': 'alice@company.com', 'subject': 'Meeting',
                 'body': 'Hi team...', 'label': 0},
                {'sender': 'scam@phish.xyz', 'subject': 'URGENT!!!',
                 'body': 'Click here...', 'label': 1}
            ]

            result = pipeline.partial_fit_batch(corrections, parent_version="v1_0")
        """
        # Initialize status
        self._status = TrainingStatus(
            is_training=True,
            current_step=None,
            progress_percent=0,
            started_at=get_timestamp(),
            estimated_completion=None,
            version_number=None,
            corrections_count=len(emails),
            error=None
        )

        if not self.verbose:
            print(f"[OnlineLearningPipeline] Starting training on {len(emails)} emails...")
        else:
            print("\n" + "=" * 80)
            print("[OnlineLearningPipeline] ===== ONLINE LEARNING PIPELINE =====")
            print("=" * 80)
            print(f"Batch size: {len(emails)}")

        try:
            # Execute training steps
            version = self._step_calculate_version()
            model = self._step_load_model()
            X, y, count = self._step_preprocess(emails)

            before = self._step_validate_before(model, X, y) if validate else {}
            model = self._step_partial_fit(model, X, y)
            after = self._step_validate_after(model, X, y, before) if validate else {}

            # Determine parent version
            if parent_version is None:
                if os.path.exists(self.metadata_path):
                    with open(self.metadata_path, 'r') as f:
                        metadata = json.load(f)
                    parent_version = metadata.get('latest_version', 'v1_0')
                else:
                    parent_version = 'v1_0'

            # Training info
            info = {
                'corrections_used': len(emails),
                'phishing_samples': int((y == 1).sum()),
                'legitimate_samples': int((y == 0).sum()),
                'training_samples': count,
                'training_time_seconds': 0.0
            }

            files = self._step_save_model(model, version, parent_version, before, after, info)

            # Mark complete
            self._status.is_training = False

            result = OnlineLearningResult(
                success=True,
                version_number=version,
                emails_processed=count,
                performance_before=before,
                performance_after=after,
                timestamp=get_timestamp(),
                model_files=files
            )

            if self.verbose:
                print("\n" + "=" * 80)
                print("[OnlineLearningPipeline] ===== TRAINING COMPLETE =====")
                print("=" * 80 + "\n")
            else:
                print(f"[OnlineLearningPipeline] Training complete: Version {version} created\n")

            return result

        except Exception as e:
            error_msg = str(e)

            if self.verbose:
                print(f"[OnlineLearningPipeline] Training failed: {error_msg}\n")
            else:
                print(f"[OnlineLearningPipeline] Training failed: {error_msg}\n")

            return OnlineLearningResult(
                success=False,
                version_number=self._status.version_number,
                emails_processed=0,
                performance_before=None,
                performance_after=None,
                timestamp=get_timestamp(),
                error=error_msg
            )


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_online_learning_pipeline(base_model_path: str,
                                    cleaner,
                                    feature_extractor,
                                    output_dir: str = DEFAULT_MODEL_DIR,
                                    verbose: bool = False) -> OnlineLearningPipeline:
    """
    Factory function to create a new online learning pipeline instance.

    Args:
        base_model_path: Path to base model
        cleaner: EmailCleaner instance
        feature_extractor: EmailFeatureExtractor instance
        output_dir: Output directory for new versions
        verbose: Enable detailed logging

    Returns:
        New OnlineLearningPipeline instance
    """
    return OnlineLearningPipeline(
        base_model_path=base_model_path,
        cleaner=cleaner,
        feature_extractor=feature_extractor,
        output_dir=output_dir,
        verbose=verbose
    )