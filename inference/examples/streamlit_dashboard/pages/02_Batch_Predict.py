"""Batch Predict page — score many emails at once.

Sources:
  1. Choose a model (defaults to the active model).
  2. Upload a CSV or JSON file shaped like ``demo_10_emails_a.csv`` /
     ``demo_10_emails_a.json`` (columns: sender, subject, body — label optional).
  3. Or use the built-in demo batches / reference demo files (no upload).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(_DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_ROOT))

from theme import apply_theme, footer, page_header  # noqa: E402
from utils import (  # noqa: E402
    SAMPLE_BATCHES,
    df_to_csv_bytes,
    emails_from_dataframe,
    get_registry,
    load_detector,
    model_version_selector,
    prediction_template_bytes,
    read_uploaded_table,
    sidebar_status,
)

st.set_page_config(page_title='Batch Predict — AURA', layout='wide', page_icon='📦')
apply_theme()
sidebar_status()
page_header(
    eyebrow='Inference',
    title='Batch prediction',
    subtitle='Score many emails from an imported CSV/JSON file or the built-in in-memory demo batches.',
)

registry = get_registry()
if not registry.list_versions():
    st.error('No model versions available. Register one on the Model Management page.')
    st.stop()

with st.sidebar:
    st.header('Configuration')
    version = model_version_selector('Model version', key='batch_model')
    st.caption(f'Scoring with **{version}**.')
    threshold = st.slider('Decision threshold', 0.0, 1.0, 0.75, 0.01)
    use_zone = st.toggle('Three-zone classification', value=True)
    if use_zone:
        review_low, review_high = st.slider(
            'REVIEW zone', 0.0, 1.0, (0.30, 0.80), 0.01)
    else:
        review_low = review_high = None
    use_calibrator = st.toggle('Apply calibrator', value=False)

# ── Source ─────────────────────────────────────────────────────────────────
st.subheader('Choose a source')
st.download_button('⬇ Download CSV template (sender, subject, body)',
                   data=prediction_template_bytes(),
                   file_name='predict_template.csv', mime='text/csv')
source = st.radio(
    'Source',
    ['Upload file (CSV / JSON)', 'Demo batches (in-memory)'],
    horizontal=True, label_visibility='collapsed',
)

if source == 'Upload file (CSV / JSON)':
    st.caption(
        'Import one or more CSV / JSON / JSONL files with columns '
        '**sender, subject, body** (a `label` column is optional and enables '
        'accuracy metrics). Rows are tagged with their source filename.'
    )
    uploaded = st.file_uploader(
        'Email files', type=['csv', 'json', 'jsonl', 'ndjson'],
        accept_multiple_files=True,
    )
    if uploaded and st.button('Load uploaded file(s)', type='primary'):
        frames: list[pd.DataFrame] = []
        errors: list[str] = []
        for f in uploaded:
            try:
                d = read_uploaded_table(f)
                d['_dataset'] = f.name
                frames.append(d)
            except Exception as e:  # noqa: BLE001
                errors.append(f'{f.name}: {e}')
        if frames:
            df = pd.concat(frames, ignore_index=True)
            try:
                st.session_state['batch_emails'] = emails_from_dataframe(df)
                st.session_state['batch_source_df'] = df
                st.success(f'Loaded {len(df)} rows from {len(frames)} file(s).')
            except Exception as e:  # noqa: BLE001
                st.error(f'Combined frame is missing required columns: {e}')
        for msg in errors:
            st.warning(msg)

else:  # Demo batches (in-memory)
    st.caption('Pre-loaded in-memory batches — no files required.')
    chosen_batches = st.multiselect(
        'Pick one or more demo batches',
        options=list(SAMPLE_BATCHES.keys()),
        default=[next(iter(SAMPLE_BATCHES))],
    )
    if st.button('Load demo batches', type='primary', disabled=not chosen_batches):
        rows = []
        for b in chosen_batches:
            for e in SAMPLE_BATCHES[b]:
                rows.append({**e, '_dataset': b})
        df = pd.DataFrame(rows)
        st.session_state['batch_emails'] = emails_from_dataframe(df)
        st.session_state['batch_source_df'] = df
        st.success(f'Loaded {len(rows)} demo emails across {len(chosen_batches)} batches.')

emails = st.session_state.get('batch_emails', [])
if not emails:
    st.info('Load a source above to enable scoring.')
    st.stop()

st.caption(f'**{len(emails)}** emails ready to score with `{version}`.')
if not st.button('Run batch predict', type='primary', use_container_width=True):
    st.stop()

# ── Run batch ──────────────────────────────────────────────────────────────
detector = load_detector(version, review_low, review_high, use_calibrator)
with st.spinner(f'Scoring {len(emails)} emails…'):
    results = detector.predict_batch(emails, threshold=threshold)

source_df = st.session_state.get('batch_source_df')
dataset_tags = (
    source_df['_dataset'].astype(str).tolist()
    if source_df is not None and '_dataset' in source_df.columns
    else [None] * len(emails)
)

rows = []
for src, r, ds in zip(emails, results, dataset_tags):
    rows.append({
        'dataset': ds,
        'sender': src.get('sender', '')[:60],
        'subject': src.get('subject', '')[:60],
        'true_label': src.get('label'),
        'predicted_label': r.predicted_label,
        'verdict': 'PHISHING' if r.predicted_label == 1 else 'LEGITIMATE',
        'phish_prob': r.phishing_probability,
        'legit_prob': r.legitimate_probability,
        'zone': r.confidence_zone.value if r.confidence_zone else None,
        'calibrated': r.calibrated,
        'prediction_id': r.prediction_id,
    })
out = pd.DataFrame(rows)
multi_dataset = out['dataset'].notna().any() and out['dataset'].nunique() > 1

# ── Summary ────────────────────────────────────────────────────────────────
st.markdown('### Summary')
c1, c2, c3, c4 = st.columns(4)
c1.metric('Total scored', len(out))
c2.metric('Predicted phishing', int((out['predicted_label'] == 1).sum()))
c3.metric('Predicted legitimate', int((out['predicted_label'] == 0).sum()))
if 'true_label' in out.columns and out['true_label'].notna().any():
    accurate = (out['predicted_label'] == out['true_label']).sum()
    n_labelled = out['true_label'].notna().sum()
    c4.metric('Accuracy (labelled)', f'{accurate / n_labelled:.3f}')
else:
    c4.metric('Accuracy', '—', help='Add a `label` column to compute accuracy.')

# ── Charts ─────────────────────────────────────────────────────────────────
left, right = st.columns(2)
with left:
    fig = px.histogram(out, x='phish_prob', nbins=40,
                       title='Phishing-probability distribution')
    fig.add_vline(x=threshold, line_dash='dash', line_color='red',
                  annotation_text=f'threshold {threshold:.2f}')
    if use_zone:
        fig.add_vline(x=review_low, line_dash='dot', line_color='orange')
        fig.add_vline(x=review_high, line_dash='dot', line_color='orange')
    st.plotly_chart(fig, use_container_width=True)

with right:
    if out['zone'].notna().any():
        zone_counts = out['zone'].value_counts().reset_index()
        zone_counts.columns = ['zone', 'count']
        fig = px.bar(zone_counts, x='zone', y='count', color='zone',
                     color_discrete_map={'SPAM': '#F87171', 'NOT_SPAM': '#34D399',
                                         'REVIEW': '#FBBF24'},
                     title='Zone distribution')
        st.plotly_chart(fig, use_container_width=True)
    else:
        label_counts = out['verdict'].value_counts().reset_index()
        label_counts.columns = ['verdict', 'count']
        fig = px.bar(label_counts, x='verdict', y='count', color='verdict',
                     color_discrete_map={'PHISHING': '#F87171', 'LEGITIMATE': '#34D399'},
                     title='Verdict distribution')
        st.plotly_chart(fig, use_container_width=True)

# ── Per-dataset breakdown when multiple sources are mixed in ───────────────
if multi_dataset:
    st.markdown('### Per-dataset breakdown')
    per_ds = (
        out
        .assign(predicted_phish=lambda d: (d['predicted_label'] == 1).astype(int))
        .groupby('dataset')
        .agg(rows=('predicted_label', 'size'),
             phish_rate=('predicted_phish', 'mean'),
             mean_phish_prob=('phish_prob', 'mean'))
        .reset_index()
    )
    st.dataframe(per_ds, hide_index=True, use_container_width=True)

# ── Confusion matrix when labels available ─────────────────────────────────
if 'true_label' in out.columns and out['true_label'].notna().any():
    st.markdown('### Confusion matrix (labelled rows)')
    labelled = out[out['true_label'].notna()].copy()
    labelled['true_label'] = labelled['true_label'].astype(int)
    cm = pd.crosstab(
        labelled['true_label'], labelled['predicted_label'],
        rownames=['true'], colnames=['predicted'], dropna=False,
    ).reindex(index=[0, 1], columns=[0, 1], fill_value=0)
    fig = px.imshow(cm.values, text_auto=True,
                    x=['pred 0', 'pred 1'], y=['true 0', 'true 1'],
                    color_continuous_scale='Blues',
                    title=f'{len(labelled)} labelled emails')
    st.plotly_chart(fig, use_container_width=True)

# ── Table + download ───────────────────────────────────────────────────────
st.markdown('### Per-email results')
st.dataframe(out, hide_index=True, use_container_width=True, height=420)
st.download_button(
    'Download results CSV', data=df_to_csv_bytes(out),
    file_name='aura_batch_predictions.csv', mime='text/csv',
)

footer()
