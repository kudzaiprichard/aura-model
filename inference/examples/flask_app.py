"""Flask example.

Run:
    flask --app inference.examples.flask_app run

Environment variables (all optional):
    AURA_MODELS_DIR        Registry root (default ./models)
    AURA_CALIBRATOR_PATH   Override calibrator path
    AURA_REVIEW_LOW        Lower REVIEW-zone threshold  (must pair with _HIGH)
    AURA_REVIEW_HIGH       Upper REVIEW-zone threshold
    AURA_DRIFT_LOG         JSONL path; enables /drift
    AURA_REVIEW_PROVIDER   'groq' or 'google'; requires _API_KEY
    AURA_REVIEW_API_KEY    API key for the selected provider
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request

from inference import (
    AutoReviewer,
    ConfidenceZone,
    DriftMonitor,
    LLMProvider,
    ModelRegistry,
    PhishingDetector,
    ValidationError,
)
from inference.registry import default_models_root

app = Flask(__name__)

_detector: PhishingDetector | None = None
_drift_monitor: DriftMonitor | None = None
_auto_reviewer: AutoReviewer | None = None


def _float_env(name: str) -> float | None:
    v = os.environ.get(name)
    return float(v) if v not in (None, '') else None


def _initialise() -> None:
    global _detector, _drift_monitor, _auto_reviewer
    if _detector is not None:
        return

    root = Path(os.environ.get('AURA_MODELS_DIR') or default_models_root())
    registry = ModelRegistry(root)
    version = registry.active_version() or registry.latest_version()
    if version is None:
        raise RuntimeError(f'No versions found under {root}')
    paths = registry.paths_for(version)

    calibrator_path = (
        Path(os.environ['AURA_CALIBRATOR_PATH'])
        if os.environ.get('AURA_CALIBRATOR_PATH')
        else paths.get('calibrator')
    )

    drift_log = os.environ.get('AURA_DRIFT_LOG')
    if drift_log:
        _drift_monitor = DriftMonitor(Path(drift_log))

    review_low = _float_env('AURA_REVIEW_LOW')
    review_high = _float_env('AURA_REVIEW_HIGH')

    _detector = PhishingDetector.from_paths(
        model_path=paths['model'],
        subject_vectorizer_path=paths['subject_vectorizer'],
        body_vectorizer_path=paths['body_vectorizer'],
        calibrator_path=calibrator_path,
        review_low_threshold=review_low,
        review_high_threshold=review_high,
        drift_monitor=_drift_monitor,
    )
    _detector.version = version

    provider = os.environ.get('AURA_REVIEW_PROVIDER')
    api_key = os.environ.get('AURA_REVIEW_API_KEY')
    if provider and api_key:
        _auto_reviewer = AutoReviewer(LLMProvider(provider), api_key)


@app.post('/predict')
def predict():
    _initialise()
    assert _detector is not None
    data = request.get_json(force=True) or {}
    try:
        result = _detector.predict(
            data.get('sender', ''),
            data.get('subject', ''),
            data.get('body', ''),
            threshold=float(data.get('threshold', 0.75)),
        )
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    payload = result.to_dict()
    if _auto_reviewer is not None and result.confidence_zone == ConfidenceZone.REVIEW:
        review = _auto_reviewer.review_if_uncertain(
            result, data.get('sender', ''), data.get('subject', ''), data.get('body', ''),
        )
        if review is not None:
            payload['auto_review'] = review.to_dict()
    return jsonify(payload)


@app.post('/confirm')
def confirm():
    _initialise()
    if _drift_monitor is None:
        return jsonify({'error': 'drift monitoring disabled'}), 503
    data = request.get_json(force=True) or {}
    try:
        _drift_monitor.record_confirmation(
            prediction_id=data['prediction_id'],
            confirmed_label=int(data['confirmed_label']),
        )
    except (KeyError, TypeError) as e:
        return jsonify({'error': f'invalid payload: {e}'}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    return jsonify({'status': 'recorded'})


@app.get('/drift')
def drift():
    _initialise()
    if _drift_monitor is None:
        return jsonify({'error': 'drift monitoring disabled'}), 503
    return jsonify(_drift_monitor.drift_signal().to_dict())
