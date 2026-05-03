"""Online Learning page — partial_fit_batch with before/after comparison."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(_DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_ROOT))

from theme import apply_theme, banner, footer, page_header  # noqa: E402
from utils import (  # noqa: E402
    SAMPLE_EMAILS,
    get_models_root,
    get_registry,
    list_synthetic_datasets,
    load_detector,
    load_synthetic_csv,
    read_uploaded_table,
    select_email_columns,
)
from inference import OnlineLearner  # noqa: E402

st.set_page_config(page_title='Online Learning — AURA', layout='wide')
apply_theme()
page_header(
    eyebrow='Adaptation',
    title='Online Learning',
    subtitle='Fine-tune via partial_fit, compare metrics before and after, and promote with an F1-delta guard.',
)

banner(
    title='Heads-up — this mutates the registry',
    body=(
        'Each successful run writes a new <code>models/v*</code> directory and '
        'updates <code>model_metadata.json</code>. Start with small batches if '
        'you want to keep the registry tidy.'
    ),
    tone='warning',
)

registry = get_registry()
versions = registry.list_versions()
if not versions:
    st.error('No model versions available.')
    st.stop()

# ── Source ─────────────────────────────────────────────────────────────────
st.subheader('Training batch')
mode = st.radio(
    'Source',
    ['Single email (manual)', 'Multi-row form', 'Synthetic dataset', 'Upload file'],
    horizontal=True,
)

batch: list[dict] = []
if mode == 'Single email (manual)':
    sample_idx = st.selectbox(
        'Pre-loaded sample',
        options=range(len(SAMPLE_EMAILS) + 1),
        format_func=lambda i: '(custom)' if i == 0 else SAMPLE_EMAILS[i - 1]['name'],
    )
    pre = SAMPLE_EMAILS[sample_idx - 1] if sample_idx > 0 else {
        'sender': '', 'subject': '', 'body': ''}
    sender = st.text_input('Sender', value=pre['sender'])
    subject = st.text_input('Subject', value=pre['subject'])
    body = st.text_area('Body', value=pre['body'], height=160)
    label = st.radio('Label', [0, 1], horizontal=True,
                     format_func=lambda v: 'LEGITIMATE (0)' if v == 0 else 'PHISHING (1)')
    st.caption(
        '`partial_fit_batch` requires at least one example per class, so we '
        'pad the batch with a single placeholder of the opposite class.'
    )
    if sender or subject or body:
        opposite_label = 1 - label
        # Use one of the SAMPLE_EMAILS opposite-leaning emails as the pad.
        pad = SAMPLE_EMAILS[0] if opposite_label == 1 else SAMPLE_EMAILS[1]
        batch = [
            {'sender': sender, 'subject': subject, 'body': body, 'label': int(label)},
            {'sender': pad['sender'], 'subject': pad['subject'],
             'body': pad['body'], 'label': int(opposite_label)},
        ]
elif mode == 'Multi-row form':
    default_df = pd.DataFrame([
        {'sender': SAMPLE_EMAILS[0]['sender'],
         'subject': SAMPLE_EMAILS[0]['subject'],
         'body': SAMPLE_EMAILS[0]['body'],
         'label': 1},
        {'sender': SAMPLE_EMAILS[1]['sender'],
         'subject': SAMPLE_EMAILS[1]['subject'],
         'body': SAMPLE_EMAILS[1]['body'],
         'label': 0},
    ])
    edited = st.data_editor(
        default_df,
        num_rows='dynamic',
        use_container_width=True,
        column_config={
            'label': st.column_config.NumberColumn(
                'label (0/1)', min_value=0, max_value=1, step=1)
        },
        key='multi_row_editor',
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
elif mode == 'Synthetic dataset':
    available = list_synthetic_datasets()
    if not available:
        st.warning('No CSVs in `_datasets/online_learning/`.')
    else:
        chosen = st.selectbox('Synthetic CSV', available)
        n_rows = st.slider('Rows', 10, 2000, 100, 10)
        seed = st.number_input('Random seed', value=0, step=1)
        if st.button('Load batch'):
            df = load_synthetic_csv(chosen)
            df = df.sample(min(n_rows, len(df)), random_state=int(seed))
            for _, row in df.iterrows():
                if pd.isna(row.get('label')):
                    continue
                batch.append({
                    'sender': str(row.get('sender', '') or ''),
                    'subject': str(row.get('subject', '') or ''),
                    'body': str(row.get('body', '') or ''),
                    'label': int(row['label']),
                })
            st.session_state['ol_batch'] = batch
        batch = st.session_state.get('ol_batch', [])
else:  # 'Upload file'
    st.caption(
        'Required columns: `sender`, `subject`, `body`, `label`. Any extra '
        'columns (e.g. `category`, `notes`) are dropped automatically. '
        'CSV, JSON array, or JSONL all work.'
    )
    uploaded = st.file_uploader(
        'Upload labelled training file',
        type=['csv', 'json', 'jsonl', 'ndjson'],
        key='ol_uploaded',
    )
    cap_n = st.slider('Cap rows', 10, 5000, 200, 10)
    cap_seed = st.number_input('Random seed (for cap sampling)', value=0, step=1,
                               key='ol_seed')
    if uploaded is not None and st.button('Load uploaded batch'):
        try:
            df = read_uploaded_table(uploaded)
            df = select_email_columns(df, with_label=True)
            if len(df) > cap_n:
                df = df.sample(n=int(cap_n), random_state=int(cap_seed))
            loaded = []
            for _, row in df.iterrows():
                loaded.append({
                    'sender': str(row['sender']),
                    'subject': str(row['subject']),
                    'body': str(row['body']),
                    'label': int(row['label']),
                })
            st.session_state['ol_batch'] = loaded
            st.success(f'Loaded {len(loaded)} labelled examples from {uploaded.name}')
        except Exception as e:  # noqa: BLE001
            st.error(f'Could not parse uploaded file: {e}')
    batch = st.session_state.get('ol_batch', [])

if batch:
    st.caption(f'Prepared {len(batch)} training examples '
               f'({sum(1 for e in batch if e["label"] == 1)} phish, '
               f'{sum(1 for e in batch if e["label"] == 0)} legit).')

# ── Holdout configuration ─────────────────────────────────────────────────
st.markdown('---')
st.subheader('Holdout for before/after metrics')
use_holdout = st.toggle(
    'Use calibration subsample as a synthetic holdout',
    value=True,
    help='When off, before/after metrics will be empty; partial_fit still runs.',
)
holdout_n = st.slider('Holdout rows', 50, 2000, 300, 50, disabled=not use_holdout)

# ── Run ───────────────────────────────────────────────────────────────────
st.markdown('---')
source_version = st.selectbox(
    'Source version (parent of the new version)',
    versions,
    index=versions.index(registry.active_version() or versions[-1]),
)
max_iter = st.slider('partial_fit iterations per call', 1, 20, 5)

run_disabled = len(batch) == 0
if st.button('Run partial_fit_batch', type='primary', disabled=run_disabled,
             use_container_width=True):
    # Holdout: build (df, y) from a synthetic dataset so OnlineLearner can
    # measure metrics. We can't reuse calibration X_val.npy because it's
    # vectorised and OnlineLearner re-builds the matrix from raw text.
    holdout = None
    if use_holdout:
        available = list_synthetic_datasets()
        if available:
            df_h = load_synthetic_csv(available[0])
            df_h = df_h.dropna(subset=['label']).head(holdout_n).copy()
            df_h['label'] = df_h['label'].astype(int)
            y = df_h['label'].to_numpy()
            holdout = (df_h[['sender', 'subject', 'body']].fillna(''), y)

    learner = OnlineLearner(
        registry=registry,
        models_root=get_models_root(),
        holdout_set=holdout,
    )
    try:
        with st.spinner('Running partial_fit_batch…'):
            result = learner.partial_fit_batch(
                batch,
                source_version=source_version,
                max_iter_per_call=int(max_iter),
            )
    except Exception as e:  # noqa: BLE001
        st.error(f'partial_fit failed: {e}')
        st.stop()

    st.session_state['ol_result'] = result
    # Refresh registry caches so the new version shows up everywhere.
    get_registry.clear()
    load_detector.clear()
    st.success(f'Created new version: **{result.new_version}** (source: {result.source_version})')

# ── Display last result ───────────────────────────────────────────────────
result = st.session_state.get('ol_result')
if result is None:
    st.info('Run a batch above to see before/after metrics.')
    st.stop()

st.markdown(f'### Last run — `{result.new_version}` (source: `{result.source_version}`)')

c1, c2, c3, c4 = st.columns(4)
c1.metric('Batch size', result.batch_size)
c2.metric('Iterations', result.iterations)
c3.metric('Subject OOV', f'{result.oov_rate_subject:.3f}')
c4.metric('Body OOV', f'{result.oov_rate_body:.3f}')

if result.performance_before and result.performance_after:
    rows = []
    for k in ('accuracy', 'precision', 'recall', 'f1'):
        rows.append({
            'metric': k,
            'before': result.performance_before.get(k, 0.0),
            'after': result.performance_after.get(k, 0.0),
        })
    perf_df = pd.DataFrame(rows)
    perf_df['delta'] = perf_df['after'] - perf_df['before']
    st.dataframe(perf_df, hide_index=True, use_container_width=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(name='before', x=perf_df['metric'], y=perf_df['before'],
                         marker_color='#3498db'))
    fig.add_trace(go.Bar(name='after', x=perf_df['metric'], y=perf_df['after'],
                         marker_color='#27ae60'))
    fig.update_layout(barmode='group', yaxis_range=[0, 1],
                      title='Holdout metrics: before vs after partial_fit_batch')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(
        'No holdout configured — `partial_fit_batch` ran but did not '
        'produce before/after metrics.'
    )

# ── Promotion ─────────────────────────────────────────────────────────────
st.markdown('### Promote new version')
st.caption(
    'Promotion sets the new version as the active version. The default '
    'promotion guard refuses if F1 dropped more than 0.01 vs source.'
)
min_delta = st.slider('Minimum acceptable F1 delta vs source', -0.5, 0.5, -0.01, 0.01)
if st.button(f'Promote {result.new_version} to active'):
    learner = OnlineLearner(registry=registry, models_root=get_models_root())
    try:
        learner.promote(result.new_version, min_delta_f1=min_delta)
        get_registry.clear()
        load_detector.clear()
        st.success(f'Promoted {result.new_version} — it is now the active version.')
    except Exception as e:  # noqa: BLE001
        st.error(f'Promotion refused: {e}')

with st.expander('Raw OnlineLearningResult'):
    st.json(result.to_dict())

footer()
