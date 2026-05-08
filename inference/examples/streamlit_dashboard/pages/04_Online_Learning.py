"""Online Learning page — partial_fit from a labelled CSV.

Upload a CSV shaped exactly like ``train_buffer.csv`` (columns: sender,
subject, body, label — an extra ``category`` column is dropped automatically),
tweak the training knobs (iterations, row cap, OOV guard, holdout), run
``partial_fit_batch``, compare before/after metrics, and optionally promote.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(_DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_ROOT))

from theme import apply_theme, banner, footer, page_header, trend_html  # noqa: E402
from utils import (  # noqa: E402
    SAMPLE_EMAILS,
    clear_registry_caches,
    get_models_root,
    get_registry,
    labelled_template_bytes,
    read_uploaded_table,
    select_email_columns,
    sidebar_status,
)
from inference import OnlineLearner  # noqa: E402

st.set_page_config(page_title='Online Learning — AURA', layout='wide', page_icon='🧠')
apply_theme()
sidebar_status()
page_header(
    eyebrow='Adaptation',
    title='Online learning',
    subtitle='Fine-tune via partial_fit from a labelled CSV, compare before/after, and promote with a guard.',
)

banner(
    'This mutates the registry',
    'Each successful run writes a new <code>models/v*</code> directory and '
    'updates <code>model_metadata.json</code>. The new version is <b>not</b> '
    'activated until you promote it.',
    tone='warning',
)

registry = get_registry()
versions = registry.list_versions()
if not versions:
    st.error('No model versions available. Register one on the Model Management page.')
    st.stop()

j1, j2, j3 = st.columns(3)
j1.metric('Active model', registry.active_version() or '—')
j2.metric('Versions on disk', len(versions))
j3.metric('Default source', registry.active_version() or registry.latest_version() or '—',
          help='Parent version a new run fine-tunes from unless you change it below.')

# ── Training data ──────────────────────────────────────────────────────────
st.subheader('1 · Training batch')
st.download_button('⬇ Download labelled CSV template (sender, subject, body, label)',
                   data=labelled_template_bytes(),
                   file_name='train_template.csv', mime='text/csv')

mode = st.radio(
    'Source',
    ['Upload labelled CSV', 'Manual editor'],
    horizontal=True,
)

batch: list[dict] = []

if mode == 'Upload labelled CSV':
    st.caption('Import a file with columns **sender, subject, body, label** '
               '(extra columns such as `category` are dropped). CSV, JSON array, '
               'or JSONL all work.')
    uploaded = st.file_uploader('Labelled training file',
                                type=['csv', 'json', 'jsonl', 'ndjson'],
                                key='ol_uploaded')
    col1, col2 = st.columns(2)
    cap_n = col1.slider('Cap rows', 10, 5000, 300, 10)
    cap_seed = col2.number_input('Sampling seed', value=0, step=1, key='ol_seed')
    if uploaded is not None and st.button('Load uploaded batch', type='primary'):
        try:
            df = read_uploaded_table(uploaded)
            df = select_email_columns(df, with_label=True)
            if len(df) > cap_n:
                df = df.sample(n=int(cap_n), random_state=int(cap_seed))
            st.session_state['ol_batch'] = [
                {'sender': str(r['sender']), 'subject': str(r['subject']),
                 'body': str(r['body']), 'label': int(r['label'])}
                for _, r in df.iterrows()
            ]
            st.success(f'Loaded {len(df)} labelled examples from {uploaded.name}.')
        except Exception as e:  # noqa: BLE001
            st.error(f'Could not parse uploaded file: {e}')
    batch = st.session_state.get('ol_batch', [])

else:  # Manual editor
    default_df = pd.DataFrame([
        {'sender': SAMPLE_EMAILS[0]['sender'], 'subject': SAMPLE_EMAILS[0]['subject'],
         'body': SAMPLE_EMAILS[0]['body'], 'label': 1},
        {'sender': SAMPLE_EMAILS[1]['sender'], 'subject': SAMPLE_EMAILS[1]['subject'],
         'body': SAMPLE_EMAILS[1]['body'], 'label': 0},
    ])
    edited = st.data_editor(
        default_df, num_rows='dynamic', use_container_width=True,
        column_config={'label': st.column_config.NumberColumn(
            'label (0/1)', min_value=0, max_value=1, step=1)},
        key='ol_editor',
    )
    for _, row in edited.iterrows():
        if pd.isna(row['label']):
            continue
        batch.append({
            'sender': str(row.get('sender', '') or ''),
            'subject': str(row.get('subject', '') or ''),
            'body': str(row.get('body', '') or ''),
            'label': int(row['label']),
        })

if batch:
    n_phish = sum(1 for e in batch if e['label'] == 1)
    st.caption(f'Prepared **{len(batch)}** training examples '
               f'({n_phish} phishing · {len(batch) - n_phish} legitimate). '
               'partial_fit_batch requires at least one example per class.')

# ── Holdout ────────────────────────────────────────────────────────────────
st.markdown('---')
st.subheader('2 · Holdout for before/after metrics')
use_holdout = st.toggle('Measure before/after metrics on an uploaded holdout', value=False,
                        help='Import a labelled holdout set to score the model before and '
                             'after fine-tuning. When off, partial_fit still runs but no '
                             'before/after metrics are produced.')
holdout = None
if use_holdout:
    st.caption('Import a labelled holdout (sender, subject, body, label) with **both '
               'classes** so precision/recall/F1 are meaningful.')
    hc1, hc2 = st.columns(2)
    holdout_n = hc1.slider('Holdout rows', 50, 3000, 400, 50)
    holdout_seed = hc2.number_input('Holdout seed', value=0, step=1, key='ol_holdout_seed')
    h_up = st.file_uploader('Holdout file (CSV / JSON / JSONL)',
                            type=['csv', 'json', 'jsonl', 'ndjson'], key='ol_holdout_up')
    hdf = None
    if h_up is not None:
        try:
            hdf = select_email_columns(read_uploaded_table(h_up), with_label=True)
            if len(hdf) > holdout_n:
                hdf = hdf.sample(n=int(holdout_n), random_state=int(holdout_seed))
        except Exception as e:  # noqa: BLE001
            st.warning(f'Could not prepare holdout: {e}')
            hdf = None
    if hdf is not None and not hdf.empty:
        holdout = (hdf[['sender', 'subject', 'body']].reset_index(drop=True),
                   hdf['label'].to_numpy())
        n1 = int((hdf['label'] == 1).sum())
        st.caption(f'Holdout: {len(hdf)} rows ({n1} phishing / {len(hdf) - n1} legitimate).')

# ── Training knobs ─────────────────────────────────────────────────────────
st.markdown('---')
st.subheader('3 · Training configuration')
k1, k2, k3 = st.columns(3)
source_version = k1.selectbox(
    'Source version (parent of the new version)', versions,
    index=versions.index(registry.active_version() or versions[-1]))
max_iter = k2.slider('partial_fit iterations per call (max_iter)', 1, 50, 5,
                     help='Number of partial_fit passes over the batch.')
oov_threshold = k3.slider('OOV warning threshold', 0.0, 1.0, 0.30, 0.05,
                          help='Logs a warning when out-of-vocabulary token rate exceeds this.')

run_disabled = len(batch) == 0
if st.button('🚀 Run partial_fit_batch', type='primary', disabled=run_disabled,
             use_container_width=True):
    learner = OnlineLearner(
        registry=registry, models_root=get_models_root(),
        holdout_set=holdout, oov_warn_threshold=float(oov_threshold),
    )
    try:
        with st.spinner('Running partial_fit_batch…'):
            result = learner.partial_fit_batch(
                batch, source_version=source_version,
                max_iter_per_call=int(max_iter))
    except Exception as e:  # noqa: BLE001
        st.error(f'partial_fit failed: {e}')
        st.stop()
    st.session_state['ol_result'] = result
    clear_registry_caches()
    st.success(f'Created new version **{result.new_version}** '
               f'(source: {result.source_version}). Promote it below to go live.')

# ── Last result ────────────────────────────────────────────────────────────
result = st.session_state.get('ol_result')
if result is None:
    st.info('Run a batch above to see before/after metrics.')
    st.stop()

st.markdown('---')
st.markdown(f'### Result — `{result.new_version}` (source `{result.source_version}`)')
c1, c2, c3, c4 = st.columns(4)
c1.metric('Batch size', result.batch_size)
c2.metric('Iterations', result.iterations)
c3.metric('Subject OOV', f'{result.oov_rate_subject:.3f}')
c4.metric('Body OOV', f'{result.oov_rate_body:.3f}')

if result.performance_before and result.performance_after:
    rows = []
    for k in ('accuracy', 'precision', 'recall', 'f1'):
        before = result.performance_before.get(k, 0.0)
        after = result.performance_after.get(k, 0.0)
        rows.append({'metric': k, 'before': before, 'after': after,
                     'delta': after - before})
    perf_df = pd.DataFrame(rows)

    st.markdown('#### Before vs after (holdout)')
    for _, r in perf_df.iterrows():
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:4px 0;border-bottom:1px solid #1F2937;">'
            f'<span style="color:#94A3B8;text-transform:uppercase;">{r["metric"]}</span>'
            f'<span>{r["before"]:.3f} → <b>{r["after"]:.3f}</b>'
            f'&nbsp;&nbsp;{trend_html(r["delta"])}</span></div>',
            unsafe_allow_html=True,
        )

    fig = go.Figure()
    fig.add_trace(go.Bar(name='before', x=perf_df['metric'], y=perf_df['before'],
                         marker_color='#3B82F6'))
    fig.add_trace(go.Bar(name='after', x=perf_df['metric'], y=perf_df['after'],
                         marker_color='#34D399'))
    fig.update_layout(barmode='group', yaxis_range=[0, 1],
                      title='Holdout metrics: before vs after partial_fit_batch')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info('No holdout configured — partial_fit ran but produced no metrics.')

# ── Promotion ──────────────────────────────────────────────────────────────
st.markdown('### Promote new version')
st.caption('Promotion activates the new version. The guard refuses if F1 dropped '
           'more than the configured delta vs the source version.')
min_delta = st.slider('Minimum acceptable F1 delta vs source', -0.5, 0.5, -0.01, 0.01)
if st.button(f'Promote {result.new_version} to active', type='primary'):
    learner = OnlineLearner(registry=registry, models_root=get_models_root())
    try:
        learner.promote(result.new_version, min_delta_f1=min_delta)
        clear_registry_caches()
        st.success(f'Promoted {result.new_version} — it is now the active model.')
    except Exception as e:  # noqa: BLE001
        st.error(f'Promotion refused: {e}')

with st.expander('Raw OnlineLearningResult'):
    st.json(result.to_dict())

footer()
