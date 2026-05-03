"""Predict page — single-email prediction with full result inspector."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(_DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_ROOT))

from theme import apply_theme, banner, footer, label_pill, page_header, zone_pill  # noqa: E402
from utils import (  # noqa: E402
    SAMPLE_EMAILS,
    get_drift_monitor,
    get_registry,
    label_word,
    load_detector,
)
from inference import ValidationError  # noqa: E402

st.set_page_config(page_title='Predict — AURA', layout='wide')
apply_theme()
page_header(
    eyebrow='Inference',
    title='Single-email prediction',
    subtitle='Score one message and inspect the engineered features behind the verdict.',
)

registry = get_registry()
versions = registry.list_versions()
if not versions:
    st.error('No model versions available.')
    st.stop()

# ── Configuration sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.header('Predict configuration')
    active = registry.active_version() or versions[-1]
    version = st.selectbox(
        'Model version', versions, index=versions.index(active),
    )
    threshold = st.slider('Decision threshold (phishing)', 0.0, 1.0, 0.75, 0.01)
    use_zone = st.toggle('Three-zone classification', value=True)
    review_low: float | None = None
    review_high: float | None = None
    if use_zone:
        review_low, review_high = st.slider(
            'REVIEW zone (probability range)',
            0.0, 1.0, (0.30, 0.80), 0.01,
        )
        if review_low >= review_high:
            st.warning('low must be strictly less than high')
            review_low, review_high = 0.30, 0.80
    use_calibrator = st.toggle('Apply calibrator (if available)', value=False)
    record_drift = st.toggle('Record predictions to drift monitor', value=False)

# ── Email input ────────────────────────────────────────────────────────────
left, right = st.columns([3, 2])

with left:
    st.subheader('Input')
    sample_names = ['(custom)'] + [s['name'] for s in SAMPLE_EMAILS]
    sample_idx = st.selectbox('Pre-loaded samples', options=range(len(sample_names)),
                              format_func=lambda i: sample_names[i])
    if sample_idx > 0:
        prefill = SAMPLE_EMAILS[sample_idx - 1]
    else:
        prefill = {'sender': '', 'subject': '', 'body': ''}

    sender = st.text_input('Sender', value=prefill['sender'])
    subject = st.text_input('Subject', value=prefill['subject'])
    body = st.text_area('Body', value=prefill['body'], height=240)
    run = st.button('Run prediction', type='primary', use_container_width=True)

# ── Run prediction ─────────────────────────────────────────────────────────
with right:
    st.subheader('Result')
    if not run:
        st.info('Configure inputs on the left and click **Run prediction**.')
        st.stop()
    try:
        detector = load_detector(
            version,
            review_low if use_zone else None,
            review_high if use_zone else None,
            use_calibrator,
        )
        if record_drift:
            detector.drift_monitor = get_drift_monitor()
        result = detector.predict(sender, subject, body, threshold=threshold)
    except ValidationError as e:
        st.error(f'Validation error: {e}')
        st.stop()
    except Exception as e:  # noqa: BLE001
        st.exception(e)
        st.stop()

    label_w = label_word(result.predicted_label)
    tone = 'danger' if result.predicted_label == 1 else 'success'
    banner(
        title=label_w,
        body=(
            f'Phishing probability <b>{result.phishing_probability:.4f}</b> '
            f'(threshold {result.threshold:.2f}).'
        ),
        tone=tone,
    )
    if result.confidence_zone is not None:
        st.markdown(
            f'**Confidence zone:** {zone_pill(result.confidence_zone.value)}  '
            f'<span style="color:#64748B;">low {result.review_low_threshold:.2f} '
            f'· high {result.review_high_threshold:.2f}</span>',
            unsafe_allow_html=True,
        )

    cols = st.columns(3)
    cols[0].metric('Phish prob', f'{result.phishing_probability:.4f}')
    cols[1].metric('Legit prob', f'{result.legitimate_probability:.4f}')
    cols[2].metric('Calibrated', 'yes' if result.calibrated else 'no')

    if result.calibrated and result.raw_phishing_probability is not None:
        st.caption(
            f'Raw probability {result.raw_phishing_probability:.4f} → '
            f'calibrated {result.phishing_probability:.4f}'
        )

# ── Engineered features ────────────────────────────────────────────────────
st.markdown('---')
st.subheader('Engineered features')
feat_df = pd.DataFrame(
    [{'feature': k, 'value': v} for k, v in result.engineered_features.items()]
).sort_values('value', ascending=True)

fig = px.bar(
    feat_df, x='value', y='feature', orientation='h',
    title='15 engineered features for this email',
    height=520,
)
fig.update_layout(yaxis_title='', xaxis_title='value')
st.plotly_chart(fig, use_container_width=True)

with st.expander('Raw prediction payload (PredictionResult.to_dict)'):
    st.json(result.to_dict())

if record_drift:
    st.success(
        f'Recorded prediction `{result.prediction_id}` to the drift monitor. '
        f'Confirm it on the **Drift Monitor** page.'
    )
    st.caption('Tip: switch to Drift Monitor and look in the *Pending* table.')

footer()
