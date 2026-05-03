"""Benchmarks page — compare registered + uploaded models on any dataset."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import (
    accuracy_score, average_precision_score, f1_score,
    precision_recall_curve, precision_score, recall_score, roc_auc_score, roc_curve,
)

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(_DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_ROOT))

from theme import apply_theme, footer, page_header  # noqa: E402
from utils import (  # noqa: E402
    confusion_metrics,
    get_registry,
    load_calibration_subset,
    load_uploaded_model,
    read_uploaded_table,
    select_email_columns,
    vectorise_emails,
)

st.set_page_config(page_title='Benchmarks — AURA', layout='wide')
apply_theme()
page_header(
    eyebrow='Evaluation',
    title='Version benchmarks',
    subtitle='Compare registered + uploaded models on the calibration set or any labelled dataset you upload.',
)

registry = get_registry()
versions = registry.list_versions()

# ── Sidebar: model + data sources ─────────────────────────────────────────
with st.sidebar:
    st.header('Models')
    chosen_versions = st.multiselect(
        'Registered versions',
        versions,
        default=versions[-min(3, len(versions)):] if versions else [],
    )
    uploaded_models = st.file_uploader(
        'Upload extra model .pkl files',
        type=['pkl', 'joblib'],
        accept_multiple_files=True,
        help=(
            'Each file must be a joblib-pickled scikit-learn classifier with '
            f'predict_proba and n_features_in_ matching the registry pipeline.'
        ),
    )
    st.markdown('---')
    st.header('Data')
    data_source = st.radio(
        'Source',
        ['Calibration subsample (pre-vectorised)', 'Upload labelled file'],
        index=0,
    )
    n_rows = st.slider('Sample / row cap', 100, 5000, 800, 100)
    seed = st.number_input('Random seed', value=0, step=1)
    threshold = st.slider('Decision threshold', 0.0, 1.0, 0.75, 0.01)

# ── Upload widget for custom data (sidebar would be too narrow) ───────────
data_file = None
if data_source.startswith('Upload'):
    st.subheader('Upload labelled dataset')
    st.caption(
        'Required columns: `sender`, `subject`, `body`, `label`. Extra '
        'columns are dropped. CSV, JSON array, or JSONL all work.'
    )
    data_file = st.file_uploader(
        'Labelled emails',
        type=['csv', 'json', 'jsonl', 'ndjson'],
        accept_multiple_files=False,
        key='benchmark_data_uploader',
    )

run_btn = st.button(
    'Run benchmark',
    type='primary',
    disabled=not (chosen_versions or uploaded_models),
    use_container_width=True,
)

if not run_btn:
    st.info('Pick at least one registered version or upload a model, '
            'then click **Run benchmark**.')
    st.stop()

# ── Build evaluation matrix (X, y) ────────────────────────────────────────
sample_label = ''
if data_source.startswith('Calibration'):
    try:
        with st.spinner('Loading calibration subsample…'):
            X, y = load_calibration_subset(int(n_rows), int(seed))
        sample_label = f'calibration ({X.shape[0]} rows)'
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()
else:
    if data_file is None:
        st.warning('Upload a labelled file to continue.')
        st.stop()
    try:
        with st.spinner('Reading + vectorising uploaded data…'):
            df = read_uploaded_table(data_file)
            df = select_email_columns(df, with_label=True)
            if len(df) > n_rows:
                df = df.sample(n=int(n_rows), random_state=int(seed))
            y = df['label'].to_numpy()
            X = vectorise_emails(df)
        sample_label = f'uploaded ({X.shape[0]} rows)'
    except Exception as e:  # noqa: BLE001
        st.error(f'Could not prepare uploaded data: {e}')
        st.stop()

st.caption(
    f'Evaluating on {X.shape[0]} rows × {X.shape[1]} features — {sample_label} '
    f'({int(np.sum(y == 1))} phish / {int(np.sum(y == 0))} legit).'
)

# ── Resolve all candidate models (registered + uploaded) ──────────────────
candidates: list[tuple[str, object]] = []
for v in chosen_versions:
    try:
        model = joblib.load(registry.paths_for(v)['model'])
        candidates.append((v, model))
    except Exception as e:  # noqa: BLE001
        st.warning(f'Could not load {v}: {e}')
for f in uploaded_models or []:
    try:
        model = load_uploaded_model(f)
        candidates.append((f'uploaded:{f.name}', model))
    except Exception as e:  # noqa: BLE001
        st.warning(f'Skipped uploaded `{f.name}`: {e}')

if not candidates:
    st.error('No models to score.')
    st.stop()

# ── Score each model ──────────────────────────────────────────────────────
def _score(model, X, y, threshold: float) -> dict:
    probs = model.predict_proba(X)[:, 1]
    preds = (probs >= threshold).astype(int)
    return {
        'probs': probs,
        'preds': preds,
        'y': y,
        'accuracy': float(accuracy_score(y, preds)),
        'precision': float(precision_score(y, preds, zero_division=0)),
        'recall': float(recall_score(y, preds, zero_division=0)),
        'f1': float(f1_score(y, preds, zero_division=0)),
        'roc_auc': float(roc_auc_score(y, probs)),
        'avg_precision': float(average_precision_score(y, probs)),
    }


results: list[dict] = []
prog = st.progress(0.0, text='Scoring models…')
for i, (name, model) in enumerate(candidates):
    try:
        res = _score(model, X, y, float(threshold))
        res['name'] = name
        results.append(res)
    except Exception as e:  # noqa: BLE001
        st.warning(f'Skipped {name}: {e}')
    prog.progress((i + 1) / len(candidates),
                  text=f'Scored {name} ({i + 1}/{len(candidates)})')
prog.empty()

if not results:
    st.error('No models scored successfully.')
    st.stop()

# ── Metric table ──────────────────────────────────────────────────────────
st.markdown('### Metric comparison')
metric_df = pd.DataFrame([
    {
        'model': r['name'],
        'accuracy': r['accuracy'],
        'precision': r['precision'],
        'recall': r['recall'],
        'f1': r['f1'],
        'roc_auc': r['roc_auc'],
        'avg_precision': r['avg_precision'],
    }
    for r in results
])
st.dataframe(
    metric_df.style.background_gradient(
        subset=['accuracy', 'precision', 'recall', 'f1', 'roc_auc', 'avg_precision'],
        cmap='Greens',
    ),
    hide_index=True,
    use_container_width=True,
)

plot_df = metric_df.melt(id_vars='model', var_name='metric', value_name='value')
fig = px.bar(
    plot_df, x='metric', y='value', color='model', barmode='group',
    title='Metrics across selected models', range_y=[0, 1],
)
st.plotly_chart(fig, use_container_width=True)

# ── ROC ───────────────────────────────────────────────────────────────────
st.markdown('### ROC curve')
roc_fig = go.Figure()
for r in results:
    fpr, tpr, _ = roc_curve(r['y'], r['probs'])
    roc_fig.add_trace(go.Scatter(
        x=fpr, y=tpr, mode='lines',
        name=f'{r["name"]} (AUC={r["roc_auc"]:.3f})',
    ))
roc_fig.add_trace(go.Scatter(
    x=[0, 1], y=[0, 1], mode='lines',
    name='chance', line={'dash': 'dash', 'color': '#7f8c8d'},
))
roc_fig.update_layout(xaxis_title='false-positive rate',
                      yaxis_title='true-positive rate')
st.plotly_chart(roc_fig, use_container_width=True)

# ── Precision-recall ──────────────────────────────────────────────────────
st.markdown('### Precision-recall curve')
pr_fig = go.Figure()
for r in results:
    precision, recall, _ = precision_recall_curve(r['y'], r['probs'])
    pr_fig.add_trace(go.Scatter(
        x=recall, y=precision, mode='lines',
        name=f'{r["name"]} (AP={r["avg_precision"]:.3f})',
    ))
pr_fig.update_layout(xaxis_title='recall', yaxis_title='precision')
st.plotly_chart(pr_fig, use_container_width=True)

# ── Per-model confusion matrices ──────────────────────────────────────────
st.markdown('### Confusion matrices (at chosen threshold)')
cols = st.columns(min(3, len(results)))
for i, r in enumerate(results):
    col = cols[i % len(cols)]
    tp = int(((r['preds'] == 1) & (r['y'] == 1)).sum())
    tn = int(((r['preds'] == 0) & (r['y'] == 0)).sum())
    fp = int(((r['preds'] == 1) & (r['y'] == 0)).sum())
    fn = int(((r['preds'] == 0) & (r['y'] == 1)).sum())
    matrix = [[tn, fp], [fn, tp]]
    cm_metrics = confusion_metrics(tp, tn, fp, fn)
    fig = px.imshow(
        matrix, text_auto=True,
        x=['pred 0', 'pred 1'], y=['true 0', 'true 1'],
        color_continuous_scale='Blues',
        title=f'{r["name"]}',
    )
    col.plotly_chart(fig, use_container_width=True)
    col.caption(
        f'FPR {cm_metrics["false_positive_rate"]:.3f}  ·  '
        f'FNR {cm_metrics["false_negative_rate"]:.3f}'
    )

# ── Probability distribution per model ───────────────────────────────────
st.markdown('### Predicted-probability distribution per model')
prob_rows = []
for r in results:
    for p, label in zip(r['probs'], r['y']):
        prob_rows.append({'model': r['name'], 'prob': float(p),
                          'true_label': int(label)})
prob_df = pd.DataFrame(prob_rows)
fig = px.histogram(
    prob_df, x='prob', color='model', barmode='overlay',
    nbins=40, opacity=0.55,
    title='How tightly each model separates the two classes',
)
fig.add_vline(x=threshold, line_dash='dash', line_color='red',
              annotation_text=f'threshold {threshold:.2f}')
st.plotly_chart(fig, use_container_width=True)

# ── Export combined results ──────────────────────────────────────────────
buf = io.StringIO()
metric_df.to_csv(buf, index=False)
st.download_button(
    'Download metric comparison CSV',
    data=buf.getvalue().encode('utf-8'),
    file_name='aura_benchmark_metrics.csv',
    mime='text/csv',
)

footer()
