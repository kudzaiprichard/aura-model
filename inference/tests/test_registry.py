"""Unit tests for ModelRegistry."""

from __future__ import annotations

import joblib
import pytest

from inference.registry import ModelRegistry


class _FakeModel:
    def __init__(self, tag='a'):
        self.tag = tag


def _make_layout(root, versions):
    (root / 'pipeline_components').mkdir(parents=True, exist_ok=True)
    joblib.dump({}, root / 'pipeline_components' / 'subject_vectorizer.pkl')
    joblib.dump({}, root / 'pipeline_components' / 'body_vectorizer.pkl')
    for v in versions:
        prod = root / v / 'production'
        prod.mkdir(parents=True, exist_ok=True)
        joblib.dump(_FakeModel(v), prod / 'phishing_detector_mlp_classifier.pkl')


def test_numeric_sort(tmp_path):
    _make_layout(tmp_path, ['v1_0', 'v1_1', 'v1_2', 'v1_10', 'v1_11'])
    reg = ModelRegistry(tmp_path)
    assert reg.list_versions() == ['v1_0', 'v1_1', 'v1_2', 'v1_10', 'v1_11']
    assert reg.latest_version() == 'v1_11'


def test_paths_for(tmp_path):
    _make_layout(tmp_path, ['v1_0'])
    reg = ModelRegistry(tmp_path)
    paths = reg.paths_for('v1_0')
    for key in ('model', 'subject_vectorizer', 'body_vectorizer'):
        assert paths[key].is_absolute()
        assert paths[key].exists()


def test_paths_for_without_calibrator(tmp_path):
    _make_layout(tmp_path, ['v1_0'])
    reg = ModelRegistry(tmp_path)
    paths = reg.paths_for('v1_0')
    assert paths['calibrator'] is None


def test_paths_for_with_calibrator(tmp_path):
    _make_layout(tmp_path, ['v1_0'])
    joblib.dump({'sentinel': 'calibrator'}, tmp_path / 'pipeline_components' / 'calibrator.pkl')
    reg = ModelRegistry(tmp_path)
    paths = reg.paths_for('v1_0')
    assert paths['calibrator'] is not None
    assert paths['calibrator'].is_absolute()
    assert paths['calibrator'].exists()


def test_invalid_version_rejected(tmp_path):
    _make_layout(tmp_path, ['v1_0'])
    reg = ModelRegistry(tmp_path)
    with pytest.raises(ValueError):
        reg.paths_for('vNOT_A_VERSION')


def test_set_active_and_active_version(tmp_path):
    _make_layout(tmp_path, ['v1_0', 'v1_1'])
    reg = ModelRegistry(tmp_path)
    assert reg.active_version() is None
    reg.set_active('v1_1', verify_integrity=False)
    assert reg.active_version() == 'v1_1'


def test_register_new_version_increments_minor(tmp_path):
    _make_layout(tmp_path, ['v1_0', 'v1_2'])
    reg = ModelRegistry(tmp_path)
    new = reg.register_new_version(_FakeModel('new'), source_version='v1_0')
    # next minor after max existing (v1_2) is v1_3
    assert new == 'v1_3'
    assert (tmp_path / 'v1_3' / 'production' / 'phishing_detector_mlp_classifier.pkl').exists()
    assert new in reg.list_versions()


def test_atomic_write_survives_existing_metadata(tmp_path):
    _make_layout(tmp_path, ['v1_0'])
    reg = ModelRegistry(tmp_path)
    reg.set_active('v1_0', verify_integrity=False)
    meta_path = tmp_path / 'model_metadata.json'
    mtime = meta_path.stat().st_mtime
    assert meta_path.exists()
    reg.set_active('v1_0', verify_integrity=False)
    assert meta_path.stat().st_mtime >= mtime
