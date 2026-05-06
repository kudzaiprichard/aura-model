"""Shared helpers for the AURA inference dashboard.

Centralises registry/model loading, upload parsing, in-memory templates,
benchmark persistence, and small UI utilities. Heavy loaders are wrapped in
`st.cache_resource` / `st.cache_data` so a detector is loaded once per session.

The dashboard ships five production capabilities:

    Predict · Batch Predict · Model Management · Online Learning · Benchmarks

The dashboard never auto-loads datasets from disk — the only built-in data is
the small set of in-memory sample emails (:data:`SAMPLE_EMAILS` /
:data:`SAMPLE_BATCHES`). For everything else the user imports their own CSV /
JSON files; downloadable templates are generated in-memory from the samples.
"""

from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

# Make `inference` importable when Streamlit launches us from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from inference import (  # noqa: E402
    ModelRegistry,
    PhishingDetector,
)
from inference.registry import default_models_root  # noqa: E402


REPO_ROOT = _REPO_ROOT
DASHBOARD_DATA_DIR = REPO_ROOT / 'dashboard_data'
BENCHMARKS_DIR = DASHBOARD_DATA_DIR / 'benchmarks'

# Sentinel used by model selectboxes to mean "fall back to the active model".
ACTIVE_CHOICE = 'Active model (default)'


# ──────────────────────────────────────────────────────────────────────────
# Registry & model loaders
# ──────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_models_root() -> Path:
    """Locate the models directory.

    Prefers ``default_models_root()`` (``AURA_MODELS_DIR`` env or ``cwd/models``)
    and falls back to ``<repo>/models`` so the dashboard works no matter which
    directory Streamlit was launched from.
    """
    try:
        return default_models_root()
    except FileNotFoundError:
        candidate = REPO_ROOT / 'models'
        if candidate.exists():
            return candidate.resolve()
        raise


@st.cache_resource(show_spinner=False)
def get_registry() -> ModelRegistry:
    return ModelRegistry(get_models_root())


def clear_registry_caches() -> None:
    """Drop cached registry + detectors after a mutation (activate / delete / train)."""
    get_registry.clear()
    load_detector.clear()


@st.cache_resource(show_spinner='Loading model…')
def load_detector(
    version: str | None,
    review_low: float | None = None,
    review_high: float | None = None,
    use_calibrator: bool = False,
) -> PhishingDetector:
    """Load a specific version (or active if ``None``) with optional thresholds.

    The cache key includes all four args so different threshold / calibrator
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


def resolve_version(choice: str | None) -> str:
    """Map a selectbox choice to a concrete version.

    ``None`` or :data:`ACTIVE_CHOICE` resolve to the active version (or the
    latest on disk when nothing is active). Anything else is returned as-is.
    """
    registry = get_registry()
    if choice is None or choice == ACTIVE_CHOICE:
        resolved = registry.active_version() or registry.latest_version()
        if resolved is None:
            raise FileNotFoundError('No model versions found in registry.')
        return resolved
    return choice


def version_metrics(version: str) -> dict:
    """Return the recorded holdout metrics for a version (or empty dict)."""
    meta = get_registry()._read_registry_metadata()
    return (meta.get('versions', {}).get(version, {}) or {}).get('metrics', {}) or {}


def sidebar_status() -> None:
    """Consistent brand + live registry status rail shown on every page."""
    registry = get_registry()
    active = registry.active_version()
    versions = registry.list_versions()
    with st.sidebar:
        st.markdown('### 🛡️ AURA')
        st.caption('Adaptive User Risk Analyzer')
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric('Active model', active or '—')
        c2.metric('Versions', len(versions))
        if active is None:
            st.caption('⚠️ No active model — predictions use the latest version.')
        st.divider()


def model_version_selector(
    label: str = 'Model',
    *,
    key: str | None = None,
    help: str | None = 'Leave on "Active model (default)" to use the live model.',
) -> str:
    """Render a model selectbox that defaults to the active model.

    Returns a concrete version string (already resolved through
    :func:`resolve_version`).
    """
    registry = get_registry()
    versions = registry.list_versions()
    active = registry.active_version()
    options = [ACTIVE_CHOICE] + versions
    choice = st.selectbox(
        label,
        options,
        index=0,
        format_func=lambda v: (
            f'{ACTIVE_CHOICE}  →  {active}' if v == ACTIVE_CHOICE and active
            else ('Active model (none set — uses latest)' if v == ACTIVE_CHOICE
                  else (f'{v}  ·  active' if v == active else v))
        ),
        key=key,
        help=help,
    )
    return resolve_version(choice)


@st.cache_resource(show_spinner=False)
def get_pipeline_vectorisers() -> tuple:
    """Load the shared subject/body vectorisers from ``pipeline_components/``.

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

    Validates that it exposes ``predict_proba`` and that ``n_features_in_``
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


# ──────────────────────────────────────────────────────────────────────────
# Pre-loaded in-memory demo emails (no files required)
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
    'Mixed showcase (4 emails)': [
        {k: v for k, v in e.items() if k != 'name'} for e in SAMPLE_EMAILS
    ],
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


# ──────────────────────────────────────────────────────────────────────────
# In-memory CSV templates
#
# The dashboard never auto-loads datasets from disk — users import their own
# files. These helpers build small, correctly-shaped templates entirely from
# the in-memory sample emails so a user can download one, fill it in, and
# re-upload, without any dataset file needing to exist on disk.
# ──────────────────────────────────────────────────────────────────────────

def prediction_template_bytes() -> bytes:
    """A CSV template for Predict / Batch Predict (sender, subject, body)."""
    rows = [{k: e[k] for k in REQUIRED_FIELDS} for e in SAMPLE_EMAILS]
    return df_to_csv_bytes(pd.DataFrame(rows, columns=list(REQUIRED_FIELDS)))


def labelled_template_bytes() -> bytes:
    """A CSV template for Online Learning / Benchmarks (sender, subject, body, label).

    Phishing samples get label 1, the rest label 0 — purely illustrative so the
    column shape and value domain are obvious.
    """
    rows = []
    for e in SAMPLE_EMAILS:
        label = 1 if 'Phishing' in e['name'] else 0
        rows.append({**{k: e[k] for k in REQUIRED_FIELDS}, 'label': label})
    return df_to_csv_bytes(pd.DataFrame(rows, columns=list(TRAINING_FIELDS)))


# ──────────────────────────────────────────────────────────────────────────
# Upload parsing helpers
# ──────────────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = ('sender', 'subject', 'body')
TRAINING_FIELDS = ('sender', 'subject', 'body', 'label')


def read_uploaded_table(file) -> pd.DataFrame:
    """Read a Streamlit UploadedFile of CSV / JSON / JSONL into a DataFrame."""
    name = (getattr(file, 'name', '') or '').lower()
    raw = file.read() if hasattr(file, 'read') else file
    if isinstance(raw, bytes):
        text = raw.decode('utf-8', errors='replace')
    else:
        text = str(raw)
    if name.endswith('.csv'):
        return pd.read_csv(io.StringIO(text))
    if name.endswith(('.jsonl', '.ndjson', '.json')):
        return pd.DataFrame(parse_jsonl(text))
    # Fallback — try CSV, then JSON in any shape.
    try:
        return pd.read_csv(io.StringIO(text))
    except Exception:
        return pd.DataFrame(parse_jsonl(text))


def select_email_columns(df: pd.DataFrame, *, with_label: bool) -> pd.DataFrame:
    """Validate and project a DataFrame down to the fields the model needs.

    Drops every extra column (``category``, ``notes``, …) and keeps only
    sender / subject / body (and label when ``with_label`` is True). Raises
    ValueError if a required field is missing.
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
    """Accepts JSONL, a JSON array, or a JSON object whose values are arrays."""
    stripped = text.strip()
    if not stripped:
        return []
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
# Benchmark run persistence (saved as JSON)
# ──────────────────────────────────────────────────────────────────────────

def save_benchmark_run(payload: dict) -> Path:
    """Persist a benchmark run to ``dashboard_data/benchmarks/`` as JSON.

    Returns the path written. The filename is timestamped so runs never clash.
    """
    BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = BENCHMARKS_DIR / f'benchmark_{ts}.json'
    path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return path


def list_benchmark_runs() -> list[Path]:
    """Return saved benchmark JSON files, newest first."""
    if not BENCHMARKS_DIR.exists():
        return []
    return sorted(BENCHMARKS_DIR.glob('benchmark_*.json'), reverse=True)


def load_benchmark_run(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8'))


# ──────────────────────────────────────────────────────────────────────────
# Misc UI helpers
# ──────────────────────────────────────────────────────────────────────────

def label_word(label: int) -> str:
    return 'PHISHING' if label == 1 else 'LEGITIMATE'


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
