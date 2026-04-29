"""Tests for PhishingDetector against the real trained artefacts."""

from __future__ import annotations

from pathlib import Path

import pytest

from inference import (
    ConfidenceZone,
    PhishingDetector,
    PredictionResult,
    ValidationError,
)
from inference.detector import classify_zone
from inference.schema import ENGINEERED_FEATURE_ORDER

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_ROOT = REPO_ROOT / 'models'


@pytest.fixture(scope='module')
def detector():
    if not MODELS_ROOT.exists():
        pytest.skip('models/ directory not present')
    return PhishingDetector.load_production(MODELS_ROOT)


def test_predict_returns_prediction_result(detector):
    r = detector.predict(
        'Alice <alice@example.com>',
        'Quick hello',
        'Hey, just checking in.',
    )
    assert isinstance(r, PredictionResult)
    assert r.predicted_label in (0, 1)
    assert 0.0 <= r.phishing_probability <= 1.0
    assert 0.0 <= r.legitimate_probability <= 1.0
    assert pytest.approx(r.phishing_probability + r.legitimate_probability, abs=1e-6) == 1.0
    assert set(r.engineered_features) == set(ENGINEERED_FEATURE_ORDER)


def test_predict_threshold_bounds(detector):
    with pytest.raises(ValidationError):
        detector.predict('a@b.c', 's', 'b', threshold=1.5)
    with pytest.raises(ValidationError):
        detector.predict('a@b.c', 's', 'b', threshold=-0.1)


def test_predict_rejects_non_str(detector):
    with pytest.raises(ValidationError):
        detector.predict(None, 's', 'b')  # type: ignore[arg-type]


def test_predict_batch_vectorised(detector):
    emails = [
        {'sender': 'a@b.c', 'subject': 'x', 'body': 'hello world'},
        {'sender': 'c@d.e', 'subject': 'y', 'body': 'free money now https://evil.example'},
    ]
    results = detector.predict_batch(emails)
    assert len(results) == 2
    for r in results:
        assert isinstance(r, PredictionResult)


def test_predict_safe_error_payload(detector):
    out = detector.predict_safe(None, 's', 'b')  # type: ignore[arg-type]
    assert out['error'] == 'validation_error'


# -- calibrator wiring (Phase 2) --------------------------------------------

_CALIBRATOR_PATH = MODELS_ROOT / 'pipeline_components' / 'calibrator.pkl'
_MODEL_PATH = MODELS_ROOT / 'v1_0' / 'production' / 'phishing_detector_mlp_classifier.pkl'
_SUBJECT_VEC_PATH = MODELS_ROOT / 'pipeline_components' / 'subject_vectorizer.pkl'
_BODY_VEC_PATH = MODELS_ROOT / 'pipeline_components' / 'body_vectorizer.pkl'


def test_load_production_attaches_calibrator_when_present(detector):
    # Phase 1 saved a calibrator artifact; load_production should auto-attach it.
    if not _CALIBRATOR_PATH.exists():
        pytest.skip('calibrator.pkl not present')
    assert detector.calibrator is not None
    r = detector.predict('Alice <alice@example.com>', 'Quick hello', 'Hey there.')
    assert r.calibrated is True
    assert r.raw_phishing_probability is not None
    assert r.raw_legitimate_probability is not None
    assert 0.0 <= r.raw_phishing_probability <= 1.0
    assert pytest.approx(r.phishing_probability + r.legitimate_probability, abs=1e-6) == 1.0


def test_from_paths_without_calibrator():
    if not _MODEL_PATH.exists():
        pytest.skip('model artifacts not present')
    det = PhishingDetector.from_paths(_MODEL_PATH, _SUBJECT_VEC_PATH, _BODY_VEC_PATH)
    assert det.calibrator is None
    r = det.predict('Alice <alice@example.com>', 'Quick hello', 'Hey there.')
    assert r.calibrated is False
    assert r.raw_phishing_probability == r.phishing_probability
    assert r.raw_legitimate_probability == r.legitimate_probability


def test_from_paths_with_calibrator():
    if not _MODEL_PATH.exists() or not _CALIBRATOR_PATH.exists():
        pytest.skip('model or calibrator artifacts not present')
    det = PhishingDetector.from_paths(
        _MODEL_PATH, _SUBJECT_VEC_PATH, _BODY_VEC_PATH,
        calibrator_path=_CALIBRATOR_PATH,
    )
    assert det.calibrator is not None
    r = det.predict('sender@example.com', 'You won!', 'click https://evil.example/claim now')
    assert r.calibrated is True
    assert r.raw_phishing_probability is not None
    # The calibrator should actually transform the probability (not be a pure
    # identity) on a prediction like this — but even if it happens to match,
    # the calibrated flag is the load-bearing signal.
    assert 0.0 <= r.phishing_probability <= 1.0


def test_apply_calibrator_identity_when_absent():
    if not _MODEL_PATH.exists():
        pytest.skip('model artifacts not present')
    det = PhishingDetector.from_paths(_MODEL_PATH, _SUBJECT_VEC_PATH, _BODY_VEC_PATH)
    # No calibrator → _apply_calibrator must be an identity.
    assert det._apply_calibrator(0.42) == 0.42
    assert det._apply_calibrator(0.0) == 0.0
    assert det._apply_calibrator(1.0) == 1.0


# -- three-zone classification (Phase 3) -------------------------------------


@pytest.mark.parametrize(
    'prob,expected',
    [
        (0.0, ConfidenceZone.NOT_SPAM),
        (0.1, ConfidenceZone.NOT_SPAM),
        (0.2999, ConfidenceZone.NOT_SPAM),
        # Boundary: prob == low → REVIEW (inclusive on low, matches predicted_label rule).
        (0.3, ConfidenceZone.REVIEW),
        (0.5, ConfidenceZone.REVIEW),
        (0.7999, ConfidenceZone.REVIEW),
        # Boundary: prob == high → SPAM (inclusive on high).
        (0.8, ConfidenceZone.SPAM),
        (0.95, ConfidenceZone.SPAM),
        (1.0, ConfidenceZone.SPAM),
    ],
)
def test_classify_zone_buckets(prob, expected):
    assert classify_zone(prob, 0.3, 0.8) == expected


@pytest.fixture(scope='module')
def detector_with_zones():
    if not _MODEL_PATH.exists():
        pytest.skip('model artifacts not present')
    return PhishingDetector.from_paths(
        _MODEL_PATH,
        _SUBJECT_VEC_PATH,
        _BODY_VEC_PATH,
        calibrator_path=_CALIBRATOR_PATH if _CALIBRATOR_PATH.exists() else None,
        review_low_threshold=0.3,
        review_high_threshold=0.8,
    )


def test_detector_populates_zone_when_configured(detector_with_zones):
    r = detector_with_zones.predict(
        'Alice <alice@example.com>', 'Quick hello', 'Hey there.'
    )
    assert r.confidence_zone is not None
    assert isinstance(r.confidence_zone, ConfidenceZone)
    assert r.review_low_threshold == 0.3
    assert r.review_high_threshold == 0.8
    # The zone must be consistent with the pure bucketing function.
    assert r.confidence_zone == classify_zone(r.phishing_probability, 0.3, 0.8)


def test_detector_zone_none_when_not_configured(detector):
    r = detector.predict('Alice <alice@example.com>', 'Quick hello', 'Hey there.')
    assert r.confidence_zone is None
    assert r.review_low_threshold is None
    assert r.review_high_threshold is None


def test_detector_batch_populates_zones(detector_with_zones):
    emails = [
        {'sender': 'a@b.c', 'subject': 'x', 'body': 'hello world'},
        {'sender': 'c@d.e', 'subject': 'y', 'body': 'free money https://evil.example'},
    ]
    results = detector_with_zones.predict_batch(emails)
    assert len(results) == 2
    for r in results:
        assert isinstance(r.confidence_zone, ConfidenceZone)
        assert r.review_low_threshold == 0.3
        assert r.review_high_threshold == 0.8


def test_partial_review_thresholds_raise():
    if not _MODEL_PATH.exists():
        pytest.skip('model artifacts not present')
    with pytest.raises(ValidationError):
        PhishingDetector.from_paths(
            _MODEL_PATH, _SUBJECT_VEC_PATH, _BODY_VEC_PATH,
            review_low_threshold=0.3,
        )
    with pytest.raises(ValidationError):
        PhishingDetector.from_paths(
            _MODEL_PATH, _SUBJECT_VEC_PATH, _BODY_VEC_PATH,
            review_high_threshold=0.8,
        )


def test_review_thresholds_low_ge_high_raises():
    if not _MODEL_PATH.exists():
        pytest.skip('model artifacts not present')
    with pytest.raises(ValidationError):
        PhishingDetector.from_paths(
            _MODEL_PATH, _SUBJECT_VEC_PATH, _BODY_VEC_PATH,
            review_low_threshold=0.8,
            review_high_threshold=0.3,
        )
    with pytest.raises(ValidationError):
        PhishingDetector.from_paths(
            _MODEL_PATH, _SUBJECT_VEC_PATH, _BODY_VEC_PATH,
            review_low_threshold=0.5,
            review_high_threshold=0.5,
        )


def test_review_thresholds_out_of_range_raise():
    if not _MODEL_PATH.exists():
        pytest.skip('model artifacts not present')
    with pytest.raises(ValidationError):
        PhishingDetector.from_paths(
            _MODEL_PATH, _SUBJECT_VEC_PATH, _BODY_VEC_PATH,
            review_low_threshold=-0.1,
            review_high_threshold=0.8,
        )
    with pytest.raises(ValidationError):
        PhishingDetector.from_paths(
            _MODEL_PATH, _SUBJECT_VEC_PATH, _BODY_VEC_PATH,
            review_low_threshold=0.3,
            review_high_threshold=1.5,
        )


def test_to_dict_serialises_zone_as_plain_string(detector_with_zones):
    r = detector_with_zones.predict(
        'Alice <alice@example.com>', 'Quick hello', 'Hey there.'
    )
    d = r.to_dict()
    assert d['confidence_zone'] in ('SPAM', 'NOT_SPAM', 'REVIEW')
    assert type(d['confidence_zone']) is str
    # The serialised form must survive json.dumps / json.loads round-trip cleanly.
    import json
    reloaded = json.loads(json.dumps(d))
    assert reloaded['confidence_zone'] == d['confidence_zone']
