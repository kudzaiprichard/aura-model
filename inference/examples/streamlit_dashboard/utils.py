"""Shared helpers for the AURA Streamlit dashboard.

Centralises model/registry loading, drift-monitor lifecycle, sample data,
and small UI utilities. Loaders are wrapped in `st.cache_resource` so a
detector or registry is loaded once per Streamlit session.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st

# Make `inference` importable when Streamlit launches us from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from inference import (  # noqa: E402
    DriftMonitor,
    ModelRegistry,
    PhishingDetector,
)
from inference.registry import default_models_root  # noqa: E402


REPO_ROOT = _REPO_ROOT
DASHBOARD_DATA_DIR = REPO_ROOT / 'dashboard_data'
DRIFT_LOG_PATH = DASHBOARD_DATA_DIR / 'drift.jsonl'
SYNTHETIC_DIR = REPO_ROOT / '_datasets' / 'online_learning'
CALIBRATION_X = REPO_ROOT / '_datasets' / 'calibration' / 'X_val.npy'
CALIBRATION_Y = REPO_ROOT / '_datasets' / 'calibration' / 'y_val.npy'


# ──────────────────────────────────────────────────────────────────────────
# Cached loaders
# ──────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_models_root() -> Path:
    return default_models_root()


@st.cache_resource(show_spinner=False)
def get_registry() -> ModelRegistry:
    return ModelRegistry(get_models_root())


@st.cache_resource(show_spinner='Loading model…')
def load_detector(
    version: str | None,
    review_low: float | None = None,
    review_high: float | None = None,
    use_calibrator: bool = False,
) -> PhishingDetector:
    """Load a specific version (or active if None) with optional thresholds.

    The cache key includes all four args so different threshold/calibrator
    settings each get their own cached detector.
    """
    registry = get_registry()
    chosen = version or registry.active_version() or registry.latest_version()
    if chosen is None:
        raise FileNotFoundError('No model versions found in registry.')
    paths = registry.paths_for(chosen)
    model = joblib.load(paths['model'])
    subject_vec = joblib.load(paths['subject_vectorizer'])
    body_vec = joblib.load(paths['body_vectorizer'])
    calibrator = None
    if use_calibrator and paths.get('calibrator') is not None:
        calibrator = joblib.load(paths['calibrator'])
    return PhishingDetector(
        model,
        subject_vec,
        body_vec,
        version=chosen,
        calibrator=calibrator,
        review_low_threshold=review_low,
        review_high_threshold=review_high,
    )


@st.cache_resource(show_spinner=False)
def get_pipeline_vectorisers() -> tuple:
    """Load the shared subject/body vectorisers from `pipeline_components/`.

    These are version-agnostic: every registered model is trained against the
    same TF-IDF vocabularies, so we can re-use them to vectorise raw uploaded
    text for any version (or any uploaded model that respects the same dim).
    """
    root = get_models_root() / 'pipeline_components'
    subject_vec = joblib.load(root / 'subject_vectorizer.pkl')
    body_vec = joblib.load(root / 'body_vectorizer.pkl')
    return subject_vec, body_vec


def vectorise_emails(df: pd.DataFrame):
    """Vectorise a (sender, subject, body) DataFrame to a sparse feature matrix.

    Uses the registry's pipeline_components so the result is compatible with
    every registered model (and any uploaded model trained to the same dim).
    """
    from inference.preprocessing import build_feature_matrix
    subj, body = get_pipeline_vectorisers()
    records = df[['sender', 'subject', 'body']].to_dict(orient='records')
    return build_feature_matrix(records, subj, body)


def load_uploaded_model(file):
    """Load a joblib-serialised classifier from a Streamlit UploadedFile.

    Validates that it exposes `predict_proba` and that `n_features_in_`
    (when present) matches the registry's expected feature count.
    """
    from inference.schema import TOTAL_FEATURES
    raw = file.read() if hasattr(file, 'read') else file
    if not isinstance(raw, (bytes, bytearray)):
        raise ValueError('uploaded model is not a binary file')
    model = joblib.load(io.BytesIO(raw))
    if not hasattr(model, 'predict_proba'):
        raise ValueError(
            f'{type(model).__name__} has no predict_proba — must be a '
            'probabilistic classifier'
        )
    n_in = getattr(model, 'n_features_in_', None)
    if n_in is not None and n_in != TOTAL_FEATURES:
        raise ValueError(
            f'uploaded model expects {n_in} features but the registry '
            f'pipeline produces {TOTAL_FEATURES}. Mismatched vocabularies?'
        )
    return model


@st.cache_resource(show_spinner=False)
def get_drift_monitor(fpr_threshold: float = 0.10) -> DriftMonitor:
    DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DriftMonitor(DRIFT_LOG_PATH, fpr_threshold=fpr_threshold)


def reset_drift_monitor() -> None:
    """Clear cached monitor so a new one is built (e.g. after log reset)."""
    get_drift_monitor.clear()


# ──────────────────────────────────────────────────────────────────────────
# Sample emails & _datasets
# ──────────────────────────────────────────────────────────────────────────

SAMPLE_EMAILS: list[dict] = [
    {
        'name': 'Phishing — PayPal lookalike',
        'sender': '"PayPal Security" <service@paypa1-alerts.com>',
        'subject': 'URGENT: verify your account',
        'body': (
            'Dear customer, unusual activity was detected on your account. '
            'Click http://paypa1-alerts.com/verify within 24 hours to avoid '
            'permanent suspension. Failure to act will result in account closure.'
        ),
    },
    {
        'name': 'Legit — GitHub PR notification',
        'sender': '"GitHub" <noreply@github.com>',
        'subject': '[repo] Pull request #482 merged',
        'body': (
            'Your pull request "Add retry logic to ingest pipeline" has been '
            'merged into main by alice. You can view the commit on github.com.'
        ),
    },
    {
        'name': 'Borderline — internal favour ask',
        'sender': '"Matt Patel" <m.patel@company-team.co>',
        'subject': 'Favor — need this done today',
        'body': (
            'Hi Emma, I am tied up in meetings all day. Could you process the '
            'attached invoice and confirm payment? Let me know once done.'
        ),
    },
    {
        'name': 'Legit — Coursera digest',
        'sender': '"Coursera" <no-reply@t.mail.coursera.org>',
        'subject': 'New courses recommended for you this week',
        'body': (
            'Based on the courses you have completed, here are three new '
            'machine-learning specialisations starting next week. Enrol any time.'
        ),
    },
]


SAMPLE_BATCHES: dict[str, list[dict]] = {
    'Mixed showcase (4 emails)': [dict(e) for e in SAMPLE_EMAILS],
    'Phishing pair': [
        {
            'sender': '"PayPal Security" <service@paypa1-alerts.com>',
            'subject': 'URGENT: verify your account',
            'body': (
                'Click http://paypa1-alerts.com/verify within 24 hours to '
                'avoid permanent suspension.'
            ),
        },
        {
            'sender': '"Microsoft 365" <noreply@ms365-hub.co>',
            'subject': 'Pending item on your account',
            'body': (
                'Notification from Microsoft 365 — review the document at '
                'https://ms365-hub.co/review or your access will be revoked.'
            ),
        },
    ],
    'Legit pair': [
        {
            'sender': '"GitHub" <noreply@github.com>',
            'subject': '[repo] Pull request #482 merged',
            'body': (
                'Your pull request "Add retry logic to ingest pipeline" has '
                'been merged into main by alice.'
            ),
        },
        {
            'sender': '"Coursera" <no-reply@t.mail.coursera.org>',
            'subject': 'New courses recommended for you this week',
            'body': (
                'Based on your completed courses, three new ML '
                'specialisations start next week.'
            ),
        },
    ],
}


def list_synthetic_datasets() -> list[str]:
    if not SYNTHETIC_DIR.exists():
        return []
    return sorted(p.name for p in SYNTHETIC_DIR.glob('*.csv'))


@st.cache_data(show_spinner=False)
def load_synthetic_csv(name: str) -> pd.DataFrame:
    path = SYNTHETIC_DIR / name
    return pd.read_csv(path)


# ──────────────────────────────────────────────────────────────────────────
# Calibration matrix (for benchmarks)
# ──────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_calibration_subset(n: int = 800, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Return a deterministic subsample of the calibration matrix.

    The full file is ~800 MB so we mmap and slice rather than copy.
    """
    if not CALIBRATION_X.exists() or not CALIBRATION_Y.exists():
        raise FileNotFoundError(
            f'Calibration data not found at {CALIBRATION_X} / {CALIBRATION_Y}'
        )
    X = np.load(CALIBRATION_X, mmap_mode='r')
    y = np.load(CALIBRATION_Y)
    n = min(n, X.shape[0])
    rng = np.random.default_rng(seed)
    idx = rng.choice(X.shape[0], size=n, replace=False)
    idx.sort()
    return np.asarray(X[idx]), y[idx]


# ──────────────────────────────────────────────────────────────────────────
# Parsing helpers (for batch upload)
# ──────────────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = ('sender', 'subject', 'body')
TRAINING_FIELDS = ('sender', 'subject', 'body', 'label')


def read_uploaded_table(file) -> pd.DataFrame:
    """Read a Streamlit UploadedFile of CSV / JSON / JSONL into a DataFrame.

    Pandas figures out the format from the extension, but we also auto-detect
    bare-JSON arrays vs JSONL lines so users can drop in either shape.
    """
    name = (getattr(file, 'name', '') or '').lower()
    raw = file.read() if hasattr(file, 'read') else file
    if isinstance(raw, bytes):
        text = raw.decode('utf-8', errors='replace')
    else:
        text = str(raw)
    if name.endswith('.csv'):
        return pd.read_csv(io.StringIO(text))
    if name.endswith('.jsonl') or name.endswith('.ndjson') or name.endswith('.json'):
        return pd.DataFrame(parse_jsonl(text))
    # Fallback — try CSV, then JSON in any shape
    try:
        return pd.read_csv(io.StringIO(text))
    except Exception:
        return pd.DataFrame(parse_jsonl(text))


def select_email_columns(df: pd.DataFrame, *, with_label: bool) -> pd.DataFrame:
    """Validate and project a DataFrame down to the fields the model needs.

    Drops every column except sender / subject / body (and label when
    `with_label` is True). Raises ValueError if a required field is missing.
    """
    fields = TRAINING_FIELDS if with_label else REQUIRED_FIELDS
    missing = [f for f in fields if f not in df.columns]
    if missing:
        raise ValueError(
            f'Uploaded data is missing required columns: {missing}. '
            f'Found columns: {list(df.columns)}'
        )
    out = df[list(fields)].copy()
    for f in REQUIRED_FIELDS:
        out[f] = out[f].astype(object).where(out[f].notna(), '').astype(str)
    if with_label:
        out = out[out['label'].notna()].copy()
        out['label'] = out['label'].astype(int)
        bad = out[~out['label'].isin([0, 1])]
        if not bad.empty:
            raise ValueError(
                f'`label` column must be 0 or 1; saw {bad["label"].unique().tolist()}'
            )
    return out


def parse_jsonl(text: str) -> list[dict]:
    """Accepts JSONL, a JSON array, or a JSON object whose values are arrays.

    A single bare JSON array `[ {...}, {...} ]` is returned as that list.
    A `{ "name_a": [...], "name_b": [...] }` shape (multiple _datasets in one
    JSON file) is flattened, with each row tagged via a `_dataset` key.
    Falls back to line-by-line JSONL when the document is not valid JSON.
    """
    stripped = text.strip()
    if not stripped:
        return []
    # Skip comment-only / blank lines so the JSONL placeholder copy/paste works.
    cleaned = '\n'.join(
        ln for ln in text.splitlines()
        if ln.strip() and not ln.lstrip().startswith('#')
    ).strip()
    if not cleaned:
        return []
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        out: list[dict] = []
        for i, line in enumerate(cleaned.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f'Line {i}: invalid JSON ({e})')
        return out
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict):
        if data and all(isinstance(v, list) for v in data.values()):
            combined: list[dict] = []
            for name, rows in data.items():
                for r in rows:
                    if isinstance(r, dict):
                        combined.append({**r, '_dataset': name})
            return combined
        return [data]
    raise ValueError(f'Top-level JSON value of type {type(data).__name__} '
                     'is not list or object')


def emails_from_dataframe(df: pd.DataFrame) -> list[dict]:
    missing = [f for f in REQUIRED_FIELDS if f not in df.columns]
    if missing:
        raise ValueError(f'Missing required columns: {missing}')
    records: list[dict] = []
    for _, row in df.iterrows():
        rec = {f: ('' if pd.isna(row[f]) else str(row[f])) for f in REQUIRED_FIELDS}
        if 'label' in df.columns and not pd.isna(row['label']):
            try:
                rec['label'] = int(row['label'])
            except (TypeError, ValueError):
                pass
        records.append(rec)
    return records


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode('utf-8')


# ──────────────────────────────────────────────────────────────────────────
# Misc UI helpers
# ──────────────────────────────────────────────────────────────────────────

def zone_color(zone: str | None) -> str:
    if zone == 'SPAM':
        return '#e74c3c'
    if zone == 'NOT_SPAM':
        return '#2ecc71'
    if zone == 'REVIEW':
        return '#f39c12'
    return '#7f8c8d'


def label_color(label: int) -> str:
    return '#e74c3c' if label == 1 else '#2ecc71'


def label_word(label: int) -> str:
    return 'PHISHING' if label == 1 else 'LEGITIMATE'


def section_header(title: str, subtitle: str | None = None) -> None:
    st.markdown(f'### {title}')
    if subtitle:
        st.caption(subtitle)


def confusion_metrics(tp: int, tn: int, fp: int, fn: int) -> dict[str, float]:
    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    fnr = fn / (fn + tp) if (fn + tp) else 0.0
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'false_positive_rate': fpr,
        'false_negative_rate': fnr,
    }
