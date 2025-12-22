"""
Model version registry for phishing detection pipeline.

This module provides:
- Centralized model version management
- Active model designation
- Version metadata tracking
- Model discovery and listing
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime


class ModelRegistry:
    """
    Centralized registry for managing model versions.

    This class provides:
    - Track all model versions in centralized metadata
    - Set/get active model version
    - List all available versions
    - Get version information and file paths
    - Validate model directories

    The registry uses a JSON metadata file to track all versions:
    - Version numbers (v1_0, v1_1, etc.)
    - Performance metrics
    - Training information
    - File paths
    - Active status

    Usage:
        # Initialize registry
        registry = ModelRegistry(
            models_dir='./artifacts',
            metadata_path='./artifacts/model_metadata.json'
        )

        # Get active model
        active_version = registry.get_active_version()
        active_paths = registry.get_model_paths(active_version)

        # Set new active model
        registry.set_active_model('v1_2')

        # List all versions
        versions = registry.list_versions()

        # Get version info
        info = registry.get_version_info('v1_2')
    """

    def __init__(self,
                 models_dir: str = './artifacts',
                 metadata_path: Optional[str] = None,
                 verbose: bool = False):
        """
        Initialize ModelRegistry.

        Args:
            models_dir: Base directory containing model versions
            metadata_path: Path to metadata JSON file (default: models_dir/model_metadata.json)
            verbose: If True, print detailed logs
        """
        self.models_dir = Path(models_dir)
        self.metadata_path = metadata_path or str(self.models_dir / 'model_metadata.json')
        self.verbose = verbose

        # Create artifacts directory if it doesn't exist
        os.makedirs(self.models_dir, exist_ok=True)

        if self.verbose:
            print(f"[ModelRegistry] Initialized")
            print(f"[ModelRegistry] Models directory: {self.models_dir}")
            print(f"[ModelRegistry] Metadata file: {self.metadata_path}")

    def _load_metadata(self) -> dict:
        """
        Load metadata from JSON file.

        Returns:
            Metadata dictionary
        """
        if not os.path.exists(self.metadata_path):
            if self.verbose:
                print("[ModelRegistry] No metadata file found, returning empty metadata")

            return {
                'metadata_version': '1.0',
                'last_updated': None,
                'active_version': None,
                'latest_version': None,
                'total_versions': 0,
                'versions': []
            }

        try:
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)

            if self.verbose:
                print(f"[ModelRegistry] Loaded metadata: {len(metadata.get('versions', []))} versions")

            return metadata

        except Exception as e:
            raise Exception(f"Failed to load metadata from {self.metadata_path}: {str(e)}")

    def _save_metadata(self, metadata: dict):
        """
        Save metadata to JSON file.

        Args:
            metadata: Metadata dictionary to save
        """
        try:
            with open(self.metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            if self.verbose:
                print(f"[ModelRegistry] Metadata saved: {self.metadata_path}")

        except Exception as e:
            raise Exception(f"Failed to save metadata to {self.metadata_path}: {str(e)}")

    def get_active_version(self) -> Optional[str]:
        """
        Get the currently active model version.

        Returns:
            Active version number (e.g., "v1_2") or None if no active version

        Example:
            registry = ModelRegistry()
            active = registry.get_active_version()

            if active:
                print(f"Active model: {active}")
            else:
                print("No active model set")
        """
        metadata = self._load_metadata()
        active = metadata.get('active_version')

        if self.verbose:
            print(f"[ModelRegistry] Active version: {active if active else 'None'}")

        return active

    def set_active_model(self, version_number: str):
        """
        Set a version as the active model.

        Args:
            version_number: Version to set as active (e.g., "v1_2")

        Raises:
            ValueError: If version doesn't exist

        Example:
            registry = ModelRegistry()
            registry.set_active_model('v1_2')
        """
        metadata = self._load_metadata()

        # Validate version exists
        version_found = False
        for version in metadata['versions']:
            if version['version_number'] == version_number:
                version_found = True
                break

        if not version_found:
            raise ValueError(f"Version {version_number} not found in registry")

        # Set all versions to inactive
        for version in metadata['versions']:
            version['is_active'] = False

        # Set specified version to active
        for version in metadata['versions']:
            if version['version_number'] == version_number:
                version['is_active'] = True
                break

        # Update metadata
        metadata['active_version'] = version_number
        metadata['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._save_metadata(metadata)

        if self.verbose:
            print(f"[ModelRegistry] Set active model: {version_number}")

    def get_latest_version(self) -> Optional[str]:
        """
        Get the latest (most recent) model version.

        Returns:
            Latest version number or None if no versions exist

        Example:
            registry = ModelRegistry()
            latest = registry.get_latest_version()
            print(f"Latest version: {latest}")
        """
        metadata = self._load_metadata()
        latest = metadata.get('latest_version')

        if self.verbose:
            print(f"[ModelRegistry] Latest version: {latest if latest else 'None'}")

        return latest

    def list_versions(self, active_only: bool = False) -> List[str]:
        """
        List all model versions.

        Args:
            active_only: If True, return only active version

        Returns:
            List of version numbers

        Example:
            registry = ModelRegistry()

            # All versions
            all_versions = registry.list_versions()
            print(f"All versions: {all_versions}")

            # Active only
            active = registry.list_versions(active_only=True)
            print(f"Active: {active}")
        """
        metadata = self._load_metadata()

        if active_only:
            versions = [v['version_number'] for v in metadata['versions'] if v.get('is_active', False)]
        else:
            versions = [v['version_number'] for v in metadata['versions']]

        if self.verbose:
            print(f"[ModelRegistry] Found {len(versions)} version(s)")

        return versions

    def get_version_info(self, version_number: str) -> Optional[dict]:
        """
        Get detailed information about a specific version.

        Args:
            version_number: Version to get info for (e.g., "v1_2")

        Returns:
            Dictionary with version information or None if not found

        Example:
            registry = ModelRegistry()
            info = registry.get_version_info('v1_2')

            if info:
                print(f"Accuracy: {info['performance_metrics']['accuracy']}")
                print(f"Trained: {info['trained_timestamp']}")
        """
        metadata = self._load_metadata()

        for version in metadata['versions']:
            if version['version_number'] == version_number:
                if self.verbose:
                    print(f"[ModelRegistry] Found info for version: {version_number}")
                return version

        if self.verbose:
            print(f"[ModelRegistry] Version not found: {version_number}")

        return None

    def get_model_paths(self, version_number: str) -> Optional[dict]:
        """
        Get file paths for a specific model version.

        Args:
            version_number: Version to get paths for

        Returns:
            Dictionary with paths:
            - model: Path to model pickle file
            - subject_vectorizer: Path to subject vectorizer
            - body_vectorizer: Path to body vectorizer

            Returns None if version not found

        Example:
            registry = ModelRegistry()
            paths = registry.get_model_paths('v1_2')

            if paths:
                model_path = os.path.join(registry.models_dir, paths['model'])
                print(f"Model: {model_path}")
        """
        version_info = self.get_version_info(version_number)

        if version_info is None:
            return None

        file_paths = version_info.get('file_paths', {})

        if self.verbose:
            print(f"[ModelRegistry] Paths for {version_number}:")
            for key, path in file_paths.items():
                print(f"  {key}: {path}")

        return file_paths

    def get_active_model_paths(self) -> Optional[dict]:
        """
        Get file paths for the currently active model.

        Returns:
            Dictionary with paths or None if no active model

        Example:
            registry = ModelRegistry()
            paths = registry.get_active_model_paths()

            if paths:
                model_path = os.path.join(registry.models_dir, paths['model'])
        """
        active_version = self.get_active_version()

        if active_version is None:
            if self.verbose:
                print("[ModelRegistry] No active model set")
            return None

        return self.get_model_paths(active_version)

    def version_exists(self, version_number: str) -> bool:
        """
        Check if a version exists in the registry.

        Args:
            version_number: Version to check

        Returns:
            True if version exists

        Example:
            registry = ModelRegistry()
            if registry.version_exists('v1_2'):
                print("Version v1_2 exists")
        """
        return self.get_version_info(version_number) is not None

    def get_version_count(self) -> int:
        """
        Get total number of versions in registry.

        Returns:
            Number of versions

        Example:
            registry = ModelRegistry()
            count = registry.get_version_count()
            print(f"Total versions: {count}")
        """
        metadata = self._load_metadata()
        return metadata.get('total_versions', 0)

    def discover_versions(self) -> List[str]:
        """
        Discover model versions by scanning the artifacts directory.

        This scans for directories matching version pattern (v1_0, v1_1, etc.)
        and checks if they contain a production model file.

        Returns:
            List of discovered version numbers

        Example:
            registry = ModelRegistry()
            discovered = registry.discover_versions()
            print(f"Discovered versions: {discovered}")
        """
        discovered = []

        if not self.models_dir.exists():
            if self.verbose:
                print("[ModelRegistry] Models directory doesn't exist")
            return discovered

        # Scan for version directories (v1_0, v1_1, etc.)
        for item in self.models_dir.iterdir():
            if item.is_dir() and item.name.startswith('v'):
                # Check if production model exists
                production_dir = item / 'production'
                model_file = production_dir / 'phishing_detector_mlp_classifier.pkl'

                if model_file.exists():
                    discovered.append(item.name)

        # Sort versions
        discovered.sort()

        if self.verbose:
            print(f"[ModelRegistry] Discovered {len(discovered)} version(s): {discovered}")

        return discovered

    def get_performance_comparison(self) -> List[dict]:
        """
        Get performance metrics for all versions for comparison.

        Returns:
            List of dictionaries with version number and metrics

        Example:
            registry = ModelRegistry()
            comparison = registry.get_performance_comparison()

            for item in comparison:
                print(f"{item['version']}: Accuracy={item['accuracy']:.3f}")
        """
        metadata = self._load_metadata()

        comparison = []
        for version in metadata['versions']:
            metrics = version.get('performance_metrics', {})
            comparison.append({
                'version': version['version_number'],
                'is_active': version.get('is_active', False),
                'accuracy': metrics.get('accuracy', 0.0),
                'precision': metrics.get('precision', 0.0),
                'recall': metrics.get('recall', 0.0),
                'f1_score': metrics.get('f1_score', 0.0),
                'trained_timestamp': version.get('trained_timestamp', 'Unknown')
            })

        if self.verbose:
            print(f"[ModelRegistry] Generated comparison for {len(comparison)} versions")

        return comparison

    def get_registry_summary(self) -> dict:
        """
        Get a summary of the entire registry.

        Returns:
            Dictionary with registry summary:
            - total_versions: Number of versions
            - active_version: Currently active version
            - latest_version: Most recent version
            - last_updated: Last metadata update timestamp

        Example:
            registry = ModelRegistry()
            summary = registry.get_registry_summary()

            print(f"Total versions: {summary['total_versions']}")
            print(f"Active: {summary['active_version']}")
        """
        metadata = self._load_metadata()

        summary = {
            'total_versions': metadata.get('total_versions', 0),
            'active_version': metadata.get('active_version'),
            'latest_version': metadata.get('latest_version'),
            'last_updated': metadata.get('last_updated'),
            'versions': self.list_versions()
        }

        if self.verbose:
            print("[ModelRegistry] Registry summary:")
            print(f"  Total versions: {summary['total_versions']}")
            print(f"  Active: {summary['active_version']}")
            print(f"  Latest: {summary['latest_version']}")

        return summary


# =============================================================================
# STANDALONE HELPER FUNCTIONS
# =============================================================================

def get_active_model_version(models_dir: str = './artifacts') -> Optional[str]:
    """
    Quick helper to get active model version without creating registry instance.

    Args:
        models_dir: Path to artifacts directory

    Returns:
        Active version number or None

    Example:
        from artifacts.registry import get_active_model_version
        active = get_active_model_version()
        print(f"Active model: {active}")
    """
    registry = ModelRegistry(models_dir=models_dir, verbose=False)
    return registry.get_active_version()


def list_all_versions(models_dir: str = './artifacts') -> List[str]:
    """
    Quick helper to list all versions without creating registry instance.

    Args:
        models_dir: Path to artifacts directory

    Returns:
        List of version numbers

    Example:
        from artifacts.registry import list_all_versions
        versions = list_all_versions()
        print(f"Available versions: {versions}")
    """
    registry = ModelRegistry(models_dir=models_dir, verbose=False)
    return registry.list_versions()


def set_active_version(version_number: str, models_dir: str = './artifacts'):
    """
    Quick helper to set active version without creating registry instance.

    Args:
        version_number: Version to set as active
        models_dir: Path to artifacts directory

    Example:
        from artifacts.registry import set_active_version
        set_active_version('v1_2')
    """
    registry = ModelRegistry(models_dir=models_dir, verbose=False)
    registry.set_active_model(version_number)