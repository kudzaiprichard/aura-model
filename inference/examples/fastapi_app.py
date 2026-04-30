"""FastAPI example.

Run:
    uvicorn inference.examples.fastapi_app:app --reload

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

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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

app = FastAPI(title='AURA Phishing Detector')

detector: PhishingDetector | None = None
drift_monitor: DriftMonitor | None = None
auto_reviewer: AutoReviewer | None = None


class EmailIn(BaseModel):
    sender: str
    subject: str
    body: str
    threshold: float = 0.75


class ConfirmIn(BaseModel):
    prediction_id: str
    confirmed_label: int


def _float_env(name: str) -> float | None:
    v = os.environ.get(name)
    return float(v) if v not in (None, '') else None


@app.on_event('startup')
def _load() -> None:
    global detector, drift_monitor, auto_reviewer

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
        drift_monitor = DriftMonitor(Path(drift_log))

    review_low = _float_env('AURA_REVIEW_LOW')
    review_high = _float_env('AURA_REVIEW_HIGH')

    detector = PhishingDetector.from_paths(
        model_path=paths['model'],
        subject_vectorizer_path=paths['subject_vectorizer'],
        body_vectorizer_path=paths['body_vectorizer'],
        calibrator_path=calibrator_path,
        review_low_threshold=review_low,
        review_high_threshold=review_high,
        drift_monitor=drift_monitor,
    )
    detector.version = version

    provider = os.environ.get('AURA_REVIEW_PROVIDER')
    api_key = os.environ.get('AURA_REVIEW_API_KEY')
    if provider and api_key:
        auto_reviewer = AutoReviewer(LLMProvider(provider), api_key)


@app.post('/predict')
def predict(email: EmailIn) -> dict:
    assert detector is not None
    try:
        result = detector.predict(
            email.sender, email.subject, email.body, threshold=email.threshold,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    payload = result.to_dict()
    if auto_reviewer is not None and result.confidence_zone == ConfidenceZone.REVIEW:
        review = auto_reviewer.review_if_uncertain(
            result, email.sender, email.subject, email.body,
        )
        if review is not None:
            payload['auto_review'] = review.to_dict()
    return payload


@app.post('/confirm')
def confirm(payload: ConfirmIn) -> dict:
    if drift_monitor is None:
        raise HTTPException(status_code=503, detail='drift monitoring disabled')
    try:
        drift_monitor.record_confirmation(
            prediction_id=payload.prediction_id,
            confirmed_label=payload.confirmed_label,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {'status': 'recorded'}


@app.get('/drift')
def drift() -> dict:
    if drift_monitor is None:
        raise HTTPException(status_code=503, detail='drift monitoring disabled')
    return drift_monitor.drift_signal().to_dict()
