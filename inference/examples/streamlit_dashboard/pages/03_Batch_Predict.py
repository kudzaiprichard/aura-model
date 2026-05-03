"""Batch Predict page — score many emails at once with charts and export."""

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
    get_drift_monitor,
    get_registry,
    list_synthetic_datasets,
    load_detector,
    load_synthetic_csv,
    parse_jsonl,
    read_uploaded_table,
)

st.set_page_config(page_title='Batch Predict — AURA', layout='wide')
apply_theme()
page_header(
    eyebrow='Inference',
    title='Batch prediction',
    subtitle='Score many emails at once from sample batches, synthetic _datasets, or your own multi-file uploads.',
)

registry = get_registry()
versions = registry.list_versions()
if not versions:
    st.error('No model versions available.')
    st.stop()

with st.sidebar:
    st.header('Batch configuration')
    active = registry.active_version() or versions[-1]
    version = st.selectbox('Model version', versions, index=versions.index(active))
    threshold = st.slider('Decision threshold', 0.0, 1.0, 0.75, 0.01)
    use_zone = st.toggle('Three-zone classification', value=True)
    if use_zone:
        review_low, review_high = st.slider(
            'REVIEW zone', 0.0, 1.0, (0.30, 0.80), 0.01)
    else:
        review_low = review_high = None
    use_calibrator = st.toggle('Apply calibrator', value=False)
    record_drift = st.toggle('Record to drift monitor', value=False)

# ── Source ─────────────────────────────────────────────────────────────────
st.subheader('Choose a source')
source = st.radio(
    'Source',
    ['Sample batches', 'Synthetic dataset', 'Upload files', 'Paste JSON / JSONL'],
    horizontal=True, label_visibility='collapsed',
)

emails: list[dict] = []
if source == 'Sample batches':
    st.caption('Pre-loaded ready-to-score batches — same style as the Predict page.')
    chosen_batches = st.multiselect(
        'Pick one or more sample batches',
        options=list(SAMPLE_BATCHES.keys()),
        default=[next(iter(SAMPLE_BATCHES))],
    )
    if st.button('Load samples', type='primary', disabled=not chosen_batches):
        rows = []
        for b in chosen_batches:
            for e in SAMPLE_BATCHES[b]:
                rows.append({**e, '_dataset': b})
        df = pd.DataFrame(rows)
        st.session_state['batch_emails'] = emails_from_dataframe(df)
        st.session_state['batch_source_df'] = df
        st.success(f'Loaded {len(rows)} sample emails '
                   f'across {len(chosen_batches)} batches.')
elif source == 'Synthetic dataset':
    available = list_synthetic_datasets()
    if not available:
        st.warning('No CSVs found in `_datasets/online_learning/`.')
    else:
        chosen = st.multiselect(
            'Synthetic dataset(s) — pick one or more',
            available,
            default=[available[0]],
        )
        max_rows = st.slider('Rows per dataset to score', 10, 5000, 200, 10)
        if st.button('Load dataset(s)', type='primary', disabled=not chosen):
            frames: list[pd.DataFrame] = []
            for name in chosen:
                d = load_synthetic_csv(name).head(max_rows).copy()
                d['_dataset'] = name
                frames.append(d)
            df = pd.concat(frames, ignore_index=True)
            st.session_state['batch_emails'] = emails_from_dataframe(df)
            st.session_state['batch_source_df'] = df
            st.success(f'Loaded {len(df)} rows from {len(chosen)} dataset(s).')
elif source == 'Upload files':
    st.caption(
        'Upload one or more CSV / JSON / JSONL files. Each file is read with '
        'the same parser; rows are tagged with their source filename so '
        'multi-dataset uploads stay distinguishable.'
    )
    uploaded = st.file_uploader(
        'Email files',
        type=['csv', 'jsonl', 'json', 'ndjson'],
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
else:
    placeholder = (
        '# JSONL (one object per line):\n'
        '{"sender":"a@b.com","subject":"hi","body":"hello"}\n'
        '{"sender":"c@d.com","subject":"meet","body":"can we meet?"}\n'
        '\n'
        '# OR JSON array:\n'
        '[{"sender":"a@b.com","subject":"hi","body":"hello"}]\n'
        '\n'
        '# OR a JSON object grouping multiple _datasets:\n'
        '{"phishing":[{...}], "legit":[{...}]}'
    )
    text = st.text_area('JSON / JSONL', height=220, placeholder=placeholder)
    if st.button('Parse', type='primary'):
        try:
            records = parse_jsonl(text)
            df = pd.DataFrame(records)
            st.session_state['batch_emails'] = emails_from_dataframe(df)
            st.session_state['batch_source_df'] = df
            datasets_seen = (
                df['_dataset'].nunique() if '_dataset' in df.columns else 1
            )
            st.success(
                f'Parsed {len(records)} emails '
                f'(across {datasets_seen} dataset section'
                f'{"s" if datasets_seen != 1 else ""}).'
            )
        except Exception as e:  # noqa: BLE001
            st.error(f'Could not parse: {e}')

emails = st.session_state.get('batch_emails', [])
if not emails:
    st.info('Load a source above to enable scoring.')
    st.stop()

st.caption(f'{len(emails)} emails ready to score.')
if not st.button('Run batch predict', type='primary', use_container_width=True):
    st.stop()

# ── Run batch ──────────────────────────────────────────────────────────────
detector = load_detector(version, review_low, review_high, use_calibrator)
if record_drift:
    detector.drift_monitor = get_drift_monitor()

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
    c4.metric('Accuracy', '—')

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
                     color_discrete_map={
                         'SPAM': '#e74c3c',
                         'NOT_SPAM': '#2ecc71',
                         'REVIEW': '#f39c12',
                     },
                     title='Zone distribution')
        st.plotly_chart(fig, use_container_width=True)
    else:
        label_counts = out['predicted_label'].value_counts().reset_index()
        label_counts.columns = ['label', 'count']
        label_counts['label'] = label_counts['label'].map(
            {0: 'LEGITIMATE', 1: 'PHISHING'})
        fig = px.bar(label_counts, x='label', y='count', color='label',
                     color_discrete_map={
                         'PHISHING': '#e74c3c', 'LEGITIMATE': '#2ecc71'},
                     title='Label distribution')
        st.plotly_chart(fig, use_container_width=True)

# ── Per-dataset breakdown when multiple sources are mixed in ──────────────
if multi_dataset:
    st.markdown('### Per-dataset breakdown')
    per_ds = (
        out
        .assign(predicted_phish=lambda d: (d['predicted_label'] == 1).astype(int))
        .groupby('dataset')
        .agg(
            rows=('predicted_label', 'size'),
            phish_rate=('predicted_phish', 'mean'),
            mean_phish_prob=('phish_prob', 'mean'),
        )
        .reset_index()
    )
    st.dataframe(per_ds, hide_index=True, use_container_width=True)
    fig = px.histogram(
        out, x='phish_prob', color='dataset', barmode='overlay',
        opacity=0.55, nbins=40,
        title='Phishing-probability distribution per dataset',
    )
    fig.add_vline(x=threshold, line_dash='dash', line_color='red')
    st.plotly_chart(fig, use_container_width=True)

# ── Confusion matrix when labels available ─────────────────────────────────
if 'true_label' in out.columns and out['true_label'].notna().any():
    st.markdown('### Confusion matrix (labelled rows)')
    labelled = out[out['true_label'].notna()].copy()
    labelled['true_label'] = labelled['true_label'].astype(int)
    cm = pd.crosstab(
        labelled['true_label'], labelled['predicted_label'],
        rownames=['true'], colnames=['predicted'], dropna=False,
    ).reindex(index=[0, 1], columns=[0, 1], fill_value=0)
    fig = px.imshow(
        cm.values, text_auto=True,
        x=['pred 0', 'pred 1'], y=['true 0', 'true 1'],
        color_continuous_scale='Blues',
        title=f'{len(labelled)} labelled emails',
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Table + download ──────────────────────────────────────────────────────
st.markdown('### Per-email results')
st.dataframe(out, hide_index=True, use_container_width=True, height=420)
st.download_button(
    'Download results CSV',
    data=df_to_csv_bytes(out),
    file_name='aura_batch_predictions.csv',
    mime='text/csv',
)

footer()
