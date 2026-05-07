"""Predict page — single-email risk analysis with a full result inspector.

Defaults to the active model; the user may override with any registered
version. Pre-loaded in-memory sample emails make the page demo-ready with no
files required.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(_DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_ROOT))

from theme import (  # noqa: E402
    PALETTE, apply_theme, banner, footer, label_pill, page_header, status_pill, zone_pill,
)
from utils import (  # noqa: E402
    SAMPLE_EMAILS,
    get_registry,
    label_word,
    load_detector,
    model_version_selector,
    sidebar_status,
    version_metrics,
)
from inference import ValidationError  # noqa: E402

st.set_page_config(page_title='Predict — AURA', layout='wide', page_icon='🔍')
apply_theme()
sidebar_status()
page_header(
    eyebrow='Inference',
    title='Single-email risk analysis',
    subtitle='Score one message and inspect the engineered features behind the verdict.',
)

registry = get_registry()
if not registry.list_versions():
    st.error('No model versions available. Register one on the Model Management page.')
    st.stop()

# ── Configuration ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header('Configuration')
    version = model_version_selector('Model version', key='predict_model')
    threshold = st.slider('Decision threshold (phishing)', 0.0, 1.0, 0.75, 0.01)
    use_zone = st.toggle('Three-zone classification', value=True)
    review_low: float | None = None
    review_high: float | None = None
    if use_zone:
        review_low, review_high = st.slider(
            'REVIEW zone (probability range)', 0.0, 1.0, (0.30, 0.80), 0.01)
        if review_low >= review_high:
            st.warning('low must be strictly less than high')
            review_low, review_high = 0.30, 0.80
    use_calibrator = st.toggle('Apply calibrator (if available)', value=False)

# ── Always-visible model context strip ─────────────────────────────────────
m = version_metrics(version)
k1, k2, k3, k4 = st.columns(4)
k1.metric('Scoring model', version,
          help='Defaults to the active model; change it in the sidebar.')
k2.metric('Model F1', f'{m["f1"]:.3f}' if m.get('f1') is not None else '—',
          help='Recorded holdout F1 for this version.')
k3.metric('Decision threshold', f'{threshold:.2f}',
          help='Phishing if probability ≥ threshold.')
k4.metric('REVIEW band', f'{review_low:.2f} – {review_high:.2f}' if use_zone else 'off',
          help='Probabilities in this range are routed to manual review.')

st.markdown('')

# ── Email input ────────────────────────────────────────────────────────────
left, right = st.columns([3, 2], gap='large')

with left:
    with st.container(border=True):
        st.subheader('Message')
        sample_names = ['(custom)'] + [s['name'] for s in SAMPLE_EMAILS]
        sample_idx = st.selectbox(
            'Pre-loaded demo emails', options=range(len(sample_names)),
            format_func=lambda i: sample_names[i],
            help='In-memory samples — no upload required.',
        )
        prefill = (
            SAMPLE_EMAILS[sample_idx - 1] if sample_idx > 0
            else {'sender': '', 'subject': '', 'body': ''}
        )
        sender = st.text_input('Sender', value=prefill['sender'])
        subject = st.text_input('Subject', value=prefill['subject'])
        body = st.text_area('Body', value=prefill['body'], height=240)
        run = st.button('Run risk analysis', type='primary', use_container_width=True)

with right:
    st.subheader('Verdict')
    if not run:
        with st.container(border=True):
            st.info('Configure the message on the left and click **Run risk analysis**.')
            st.caption(
                'The detector combines TF-IDF over the subject and body with 15 '
                'engineered signals (URL density, domain entropy, sender/name '
                'consistency, …) and returns a calibrated phishing probability.'
            )
        st.stop()
    try:
        detector = load_detector(
            version,
            review_low if use_zone else None,
            review_high if use_zone else None,
            use_calibrator,
        )
        result = detector.predict(sender, subject, body, threshold=threshold)
    except ValidationError as e:
        st.error(f'Validation error: {e}')
        st.stop()
    except Exception as e:  # noqa: BLE001
        st.exception(e)
        st.stop()

    prob = result.phishing_probability
    label_w = label_word(result.predicted_label)
    tone = 'danger' if result.predicted_label == 1 else 'success'

    # Probability gauge — instantly readable risk meter.
    gauge = go.Figure(go.Indicator(
        mode='gauge+number',
        value=prob * 100,
        number={'suffix': '%', 'font': {'size': 30}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': PALETTE['danger'] if result.predicted_label == 1 else PALETTE['success']},
            'steps': [
                {'range': [0, (review_low if use_zone else threshold) * 100],
                 'color': 'rgba(52,211,153,0.18)'},
                {'range': [(review_low if use_zone else threshold) * 100,
                           (review_high if use_zone else threshold) * 100],
                 'color': 'rgba(251,191,36,0.18)'},
                {'range': [(review_high if use_zone else threshold) * 100, 100],
                 'color': 'rgba(248,113,113,0.18)'},
            ],
            'threshold': {'line': {'color': PALETTE['primary'], 'width': 3},
                          'thickness': 0.85, 'value': threshold * 100},
        },
    ))
    gauge.update_layout(height=210, margin=dict(l=20, r=20, t=10, b=0))
    st.plotly_chart(gauge, use_container_width=True)

    banner(
        title=f'{label_w}',
        body=(f'Phishing probability <b>{prob:.4f}</b> at threshold '
              f'{result.threshold:.2f} · model <code>{version}</code>.'),
        tone=tone,
    )
    pills = [label_pill(result.predicted_label)]
    if result.confidence_zone is not None:
        pills.append(zone_pill(result.confidence_zone.value))
    if result.calibrated:
        pills.append(status_pill('calibrated', 'primary'))
    st.markdown(' '.join(pills), unsafe_allow_html=True)

    cols = st.columns(2)
    cols[0].metric('Phishing', f'{prob:.4f}')
    cols[1].metric('Legitimate', f'{result.legitimate_probability:.4f}')
    if result.calibrated and result.raw_phishing_probability is not None:
        st.caption(f'Raw {result.raw_phishing_probability:.4f} → calibrated {prob:.4f}')

# ── Engineered features ────────────────────────────────────────────────────
st.divider()
st.subheader('Engineered feature signals')
st.caption('The 15 hand-engineered features feeding the classifier for this message.')

feat_df = pd.DataFrame(
    [{'feature': k, 'value': v} for k, v in result.engineered_features.items()]
)
fc1, fc2 = st.columns([3, 2], gap='large')
with fc1:
    plot_df = feat_df.sort_values('value', ascending=True)
    fig = px.bar(plot_df, x='value', y='feature', orientation='h', height=460)
    fig.update_layout(yaxis_title='', xaxis_title='value', margin=dict(l=0, r=0, t=10, b=0))
    fig.update_traces(marker_color=PALETTE['primary'])
    st.plotly_chart(fig, use_container_width=True)
with fc2:
    st.caption('Top signals by magnitude')
    top = feat_df.reindex(feat_df['value'].abs().sort_values(ascending=False).index).head(6)
    st.dataframe(top, hide_index=True, use_container_width=True,
                 column_config={'value': st.column_config.NumberColumn(format='%.3f')})

with st.expander('Raw prediction payload (PredictionResult.to_dict)'):
    st.json(result.to_dict())

footer()
