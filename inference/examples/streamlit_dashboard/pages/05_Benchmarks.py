"""Benchmarks page — compare 2+ model versions on a labelled dataset.

Workflow:
  1. Choose two or more registered versions (and optionally upload extra .pkl
     models).
  2. Provide a labelled dataset shaped like ``benchmark_data.csv`` (columns:
     sender, subject, body, label) — upload or use the bundled demo.
  3. Run the benchmark. Results are shown side-by-side from the first (oldest)
     version to the last, with medals, per-metric winners, and trend deltas so
     it is obvious which model beats which. Every run is saved to JSON.
"""

from __future__ import annotations

import math
import sys
from datetime import datetime, timezone
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

from theme import (  # noqa: E402
    apply_theme, banner, footer, model_compare_card, page_header, winner_card,
)
from utils import (  # noqa: E402
    confusion_metrics,
    df_to_csv_bytes,
    get_registry,
    labelled_template_bytes,
    list_benchmark_runs,
    load_benchmark_run,
    load_uploaded_model,
    read_uploaded_table,
    save_benchmark_run,
    select_email_columns,
    sidebar_status,
    version_metrics,
    vectorise_emails,
)

st.set_page_config(page_title='Benchmarks — AURA', layout='wide', page_icon='🏁')
apply_theme()
sidebar_status()
page_header(
    eyebrow='Evaluation',
    title='Version benchmarks',
    subtitle='Compare two or more versions on a labelled dataset — ranked oldest → newest with medals.',
)

registry = get_registry()
versions = registry.list_versions()
active = registry.active_version()
METRIC_KEYS = ('accuracy', 'precision', 'recall', 'f1', 'roc_auc', 'avg_precision')
# Higher-is-better for every metric we rank on.

# ── Model selection ────────────────────────────────────────────────────────
st.subheader('1 · Choose models (pick two or more)')
default_sel = versions[-min(3, len(versions)):] if versions else []
chosen_versions = st.multiselect('Registered versions', versions, default=default_sel)
with st.expander('Add extra uploaded model .pkl files (optional)'):
    uploaded_models = st.file_uploader(
        'Model files', type=['pkl', 'joblib'], accept_multiple_files=True,
        help='joblib-pickled classifier with predict_proba and n_features_in_ == 7015.')

n_models = len(chosen_versions) + len(uploaded_models or [])

# Pre-run preview so the page is never empty: show the line-up + recorded metrics.
if chosen_versions:
    order = {v: i for i, v in enumerate(versions)}
    preview = pd.DataFrame([
        {'version': v, 'active': '✅' if v == active else '',
         **{k: version_metrics(v).get(k) for k in ('accuracy', 'precision', 'recall', 'f1')}}
        for v in sorted(chosen_versions, key=lambda v: order.get(v, 1_000))
    ])
    st.caption('Line-up (oldest → newest) with recorded holdout metrics:')
    st.dataframe(
        preview, hide_index=True, use_container_width=True,
        column_config={c: st.column_config.NumberColumn(format='%.3f')
                       for c in ('accuracy', 'precision', 'recall', 'f1')},
    )

# ── Data selection ─────────────────────────────────────────────────────────
st.subheader('2 · Labelled dataset')
st.download_button('⬇ Download labelled CSV template (sender, subject, body, label)',
                   data=labelled_template_bytes(),
                   file_name='benchmark_template.csv', mime='text/csv')
st.caption('Import a labelled file with columns **sender, subject, body, label**. '
           'Extra columns are dropped. For meaningful ROC-AUC / average precision, '
           'include **both** classes (1 = phishing, 0 = legitimate). CSV, JSON '
           'array, or JSONL all work.')
data_file = st.file_uploader('Labelled emails',
                             type=['csv', 'json', 'jsonl', 'ndjson'],
                             key='benchmark_data_uploader')

c1, c2, c3 = st.columns(3)
n_rows = c1.slider('Row cap', 100, 12000, 1000, 100,
                   help='Rows are vectorised on the fly — keep modest for speed.')
seed = c2.number_input('Random seed', value=0, step=1)
threshold = c3.slider('Decision threshold', 0.0, 1.0, 0.75, 0.01)

run_btn = st.button('🏁 Run benchmark', type='primary',
                    disabled=(n_models < 2), use_container_width=True)
if n_models < 2:
    st.info('Select at least **two** models (registered versions and/or uploads) to compare.')

# ── History ────────────────────────────────────────────────────────────────
past = list_benchmark_runs()
if past:
    with st.expander(f'📁 Saved benchmark runs ({len(past)})'):
        for p in past[:20]:
            st.markdown(f'- `{p.name}`')
        sel = st.selectbox('Inspect a saved run', [p.name for p in past])
        if sel:
            st.json(load_benchmark_run(next(p for p in past if p.name == sel)))

if not run_btn:
    st.stop()

# ── Build evaluation matrix (X, y) ─────────────────────────────────────────
if data_file is None:
    st.warning('Import a labelled file to continue.')
    st.stop()
try:
    with st.spinner('Reading + vectorising uploaded data…'):
        df = read_uploaded_table(data_file)
        df = select_email_columns(df, with_label=True)
        if len(df) > n_rows:
            df = df.sample(n=int(n_rows), random_state=int(seed))
        y = df['label'].to_numpy()
        X = vectorise_emails(df)
    data_label = f'upload:{getattr(data_file, "name", "file")}'
except Exception as e:  # noqa: BLE001
    st.error(f'Could not prepare uploaded data: {e}')
    st.stop()

n_pos, n_neg = int(np.sum(y == 1)), int(np.sum(y == 0))
st.caption(
    f'Evaluating on **{X.shape[0]} rows** × {X.shape[1]} features '
    f'({n_pos} phishing / {n_neg} legitimate) — {data_label}.'
)
single_class = (n_pos == 0 or n_neg == 0)
if single_class:
    banner(
        'Single-class dataset',
        'This dataset contains only one label, so ROC-AUC and average precision '
        'are undefined and shown as <code>n/a</code>. Upload a dataset with both '
        'phishing (1) and legitimate (0) rows for the full comparison.',
        tone='warning',
    )

# ── Resolve candidates in version order (oldest → newest), uploads last ─────
candidates: list[tuple[str, object]] = []
version_order = {v: i for i, v in enumerate(versions)}
for v in sorted(chosen_versions, key=lambda v: version_order.get(v, 1_000)):
    try:
        candidates.append((v, joblib.load(registry.paths_for(v)['model'])))
    except Exception as e:  # noqa: BLE001
        st.warning(f'Could not load {v}: {e}')
for f in uploaded_models or []:
    try:
        candidates.append((f'uploaded:{f.name}', load_uploaded_model(f)))
    except Exception as e:  # noqa: BLE001
        st.warning(f'Skipped uploaded `{f.name}`: {e}')

if len(candidates) < 2:
    st.error('Need at least two models that load successfully.')
    st.stop()

# ── Score each model ───────────────────────────────────────────────────────
def _score(model, X, y, thr: float) -> dict:
    probs = model.predict_proba(X)[:, 1]
    preds = (probs >= thr).astype(int)
    tp = int(((preds == 1) & (y == 1)).sum())
    tn = int(((preds == 0) & (y == 0)).sum())
    fp = int(((preds == 1) & (y == 0)).sum())
    fn = int(((preds == 0) & (y == 1)).sum())
    cm = confusion_metrics(tp, tn, fp, fn)
    # ROC-AUC / average precision are undefined when y has a single class.
    try:
        roc = float(roc_auc_score(y, probs))
    except ValueError:
        roc = float('nan')
    try:
        ap = float(average_precision_score(y, probs))
    except ValueError:
        ap = float('nan')
    return {
        'probs': probs, 'preds': preds, 'y': y,
        'accuracy': float(accuracy_score(y, preds)),
        'precision': float(precision_score(y, preds, zero_division=0)),
        'recall': float(recall_score(y, preds, zero_division=0)),
        'f1': float(f1_score(y, preds, zero_division=0)),
        'roc_auc': roc,
        'avg_precision': ap,
        'false_positive_rate': cm['false_positive_rate'],
        'false_negative_rate': cm['false_negative_rate'],
        'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
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
    prog.progress((i + 1) / len(candidates), text=f'Scored {name} ({i + 1}/{len(candidates)})')
prog.empty()

if len(results) < 2:
    st.error('Fewer than two models scored successfully.')
    st.stop()

# Results stay in candidate order = version order (oldest → newest).
def _best(metric: str):
    valid = [r for r in results if not math.isnan(r[metric])]
    if not valid:
        return None, float('nan')
    top = max(valid, key=lambda r: r[metric])
    return top['name'], top[metric]


best_for: dict[str, str | None] = {}
best_value: dict[str, float] = {}
for k in METRIC_KEYS:
    best_for[k], best_value[k] = _best(k)

# ── Leaderboard (ranked by F1) ─────────────────────────────────────────────
st.markdown('### 🏆 Leaderboard (by F1)')
ranked = sorted(results, key=lambda r: r['f1'], reverse=True)
rank_of = {r['name']: i for i, r in enumerate(ranked)}
champion = ranked[0]['name']
runner = ranked[1]['name']
f1_gap = ranked[0]['f1'] - ranked[1]['f1']
banner(
    f'Winner: {champion}',
    f'Beats runner-up <b>{runner}</b> by <b>{f1_gap:+.3f} F1</b> '
    f'on {X.shape[0]} rows at threshold {threshold:.2f}.',
    tone='success',
)

# ── Per-metric winners ─────────────────────────────────────────────────────
st.markdown('### Per-metric winners')
wcols = st.columns(len(METRIC_KEYS))
for col, k in zip(wcols, METRIC_KEYS):
    with col:
        if best_for[k] is None or math.isnan(best_value[k]):
            winner_card(k, 'n/a', float('nan'))
        else:
            winner_card(k, best_for[k], best_value[k])

# ── Side-by-side cards, oldest → newest, with trend vs previous version ────
st.markdown('### Side-by-side (oldest → newest)')
st.caption('Cards are ordered from the first selected version to the last. The '
           'small ▲/▼ shows the change vs the previous card; ⭐ marks a '
           'metric this model wins outright.')
card_cols = st.columns(len(results))
prev_metrics: dict[str, float] | None = None
for col, r in zip(card_cols, results):
    metrics = {k: r[k] for k in METRIC_KEYS}
    deltas = (None if prev_metrics is None
              else {k: metrics[k] - prev_metrics[k] for k in METRIC_KEYS})
    best_flags = {k: (best_for[k] == r['name']) for k in METRIC_KEYS}
    with col:
        model_compare_card(
            r['name'], metrics, rank=rank_of[r['name']],
            is_active=(r['name'] == active), deltas=deltas, best_flags=best_flags)
    prev_metrics = metrics

# ── Highlighted comparison table ───────────────────────────────────────────
st.markdown('### Metric comparison table')
metric_df = pd.DataFrame([{'model': r['name'], **{k: r[k] for k in METRIC_KEYS},
                           'FPR': r['false_positive_rate'],
                           'FNR': r['false_negative_rate']} for r in results])
st.dataframe(
    metric_df.style
    .background_gradient(subset=list(METRIC_KEYS), cmap='Greens')
    .background_gradient(subset=['FPR', 'FNR'], cmap='Reds')
    .format({c: '{:.3f}' for c in list(METRIC_KEYS) + ['FPR', 'FNR']}, na_rep='—'),
    hide_index=True, use_container_width=True,
)

plot_df = metric_df.melt(id_vars='model', value_vars=list(METRIC_KEYS),
                         var_name='metric', value_name='value')
fig = px.bar(plot_df, x='metric', y='value', color='model', barmode='group',
             title='Metrics across selected models', range_y=[0, 1],
             category_orders={'model': [r['name'] for r in results]})
st.plotly_chart(fig, use_container_width=True)

# ── ROC + PR curves ────────────────────────────────────────────────────────
cc1, cc2 = st.columns(2)
with cc1:
    st.markdown('#### ROC curve')
    roc_fig = go.Figure()
    for r in results:
        fpr, tpr, _ = roc_curve(r['y'], r['probs'])
        roc_fig.add_trace(go.Scatter(x=fpr, y=tpr, mode='lines',
                                     name=f'{r["name"]} (AUC={r["roc_auc"]:.3f})'))
    roc_fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode='lines', name='chance',
                                 line={'dash': 'dash', 'color': '#7f8c8d'}))
    roc_fig.update_layout(xaxis_title='false-positive rate', yaxis_title='true-positive rate')
    st.plotly_chart(roc_fig, use_container_width=True)
with cc2:
    st.markdown('#### Precision-recall curve')
    pr_fig = go.Figure()
    for r in results:
        precision, recall, _ = precision_recall_curve(r['y'], r['probs'])
        pr_fig.add_trace(go.Scatter(x=recall, y=precision, mode='lines',
                                    name=f'{r["name"]} (AP={r["avg_precision"]:.3f})'))
    pr_fig.update_layout(xaxis_title='recall', yaxis_title='precision')
    st.plotly_chart(pr_fig, use_container_width=True)

# ── Confusion matrices ─────────────────────────────────────────────────────
st.markdown('### Confusion matrices (at chosen threshold)')
cm_cols = st.columns(min(3, len(results)))
for i, r in enumerate(results):
    col = cm_cols[i % len(cm_cols)]
    matrix = [[r['tn'], r['fp']], [r['fn'], r['tp']]]
    fig = px.imshow(matrix, text_auto=True, x=['pred 0', 'pred 1'],
                    y=['true 0', 'true 1'], color_continuous_scale='Blues',
                    title=r['name'])
    col.plotly_chart(fig, use_container_width=True)
    col.caption(f'FPR {r["false_positive_rate"]:.3f} · FNR {r["false_negative_rate"]:.3f}')

# ── Persist the run to JSON ────────────────────────────────────────────────
def _clean(v):
    return None if isinstance(v, float) and math.isnan(v) else v


payload = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'dataset': {'source': data_label, 'rows': int(X.shape[0]),
                'features': int(X.shape[1]),
                'phishing': int(np.sum(y == 1)), 'legitimate': int(np.sum(y == 0)),
                'seed': int(seed)},
    'threshold': float(threshold),
    'active_model': active,
    'model_order_oldest_to_newest': [r['name'] for r in results],
    'leaderboard_by_f1': [r['name'] for r in ranked],
    'winner': champion,
    'per_metric_winner': best_for,
    'models': [
        {'name': r['name'], 'rank_by_f1': rank_of[r['name']],
         **{k: _clean(r[k]) for k in METRIC_KEYS},
         'false_positive_rate': r['false_positive_rate'],
         'false_negative_rate': r['false_negative_rate'],
         'confusion': {'tp': r['tp'], 'tn': r['tn'], 'fp': r['fp'], 'fn': r['fn']}}
        for r in results
    ],
}
saved_path = save_benchmark_run(payload)
st.success(f'Benchmark saved to `{saved_path}`.')
dl1, dl2 = st.columns(2)
dl1.download_button('⬇ Download results JSON',
                    data=Path(saved_path).read_text(encoding='utf-8'),
                    file_name=saved_path.name, mime='application/json')
dl2.download_button('⬇ Download metric table CSV', data=df_to_csv_bytes(metric_df),
                    file_name='aura_benchmark_metrics.csv', mime='text/csv')

footer()
