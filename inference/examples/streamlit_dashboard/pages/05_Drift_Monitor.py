"""Drift Monitor page — live confusion matrix & FPR alerting."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(_DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_ROOT))

from theme import apply_theme, banner, footer, page_header  # noqa: E402
from utils import (  # noqa: E402
    DRIFT_LOG_PATH,
    confusion_metrics,
    get_drift_monitor,
    get_registry,
    list_synthetic_datasets,
    load_detector,
    load_synthetic_csv,
    reset_drift_monitor,
)

st.set_page_config(page_title='Drift Monitor — AURA', layout='wide')
apply_theme()
page_header(
    eyebrow='Observability',
    title='Drift Monitor',
    subtitle='Live confusion matrix and false-positive-rate alerting on confirmed predictions.',
)

# ── Sidebar: monitor settings ──────────────────────────────────────────────
with st.sidebar:
    st.header('Monitor settings')
    fpr_threshold = st.slider('FPR alert threshold', 0.0, 1.0, 0.10, 0.01)
    if st.button('Apply threshold'):
        # Threshold is set at construction; rebuild.
        reset_drift_monitor()
        st.session_state.pop('drift_log_cache', None)
        st.rerun()
    st.markdown('---')
    st.caption(f'Log path: `{DRIFT_LOG_PATH}`')
    if DRIFT_LOG_PATH.exists():
        size_kb = DRIFT_LOG_PATH.stat().st_size / 1024
        st.caption(f'Size: {size_kb:.1f} KB')
    if st.button('Reset drift log (delete file)'):
        DRIFT_LOG_PATH.unlink(missing_ok=True)
        reset_drift_monitor()
        st.success('Drift log deleted.')
        st.rerun()

monitor = get_drift_monitor(fpr_threshold)
signal = monitor.drift_signal()
cm = monitor.confusion_matrix()

# ── Top-line status ────────────────────────────────────────────────────────
banner(
    title=f'Status: {signal.status.value}',
    body=signal.message,
    tone='success' if signal.status.value == 'OK' else 'danger',
)

c1, c2, c3, c4 = st.columns(4)
c1.metric('Total predictions', signal.total_predictions)
c2.metric('Confirmed', signal.confirmed_predictions)
c3.metric('False positive rate', f'{signal.false_positive_rate:.4f}')
c4.metric('Threshold', f'{signal.threshold:.4f}')

# ── Confusion matrix + derived metrics ─────────────────────────────────────
st.markdown('### Live confusion matrix')
left, right = st.columns([2, 3])
with left:
    matrix = [
        [cm['tn'], cm['fp']],
        [cm['fn'], cm['tp']],
    ]
    fig = px.imshow(
        matrix, text_auto=True,
        x=['pred 0', 'pred 1'], y=['true 0', 'true 1'],
        color_continuous_scale='Blues',
        title='predicted vs confirmed',
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    metrics = confusion_metrics(cm['tp'], cm['tn'], cm['fp'], cm['fn'])
    st.metric('Accuracy', f'{metrics["accuracy"]:.4f}')
    st.metric('Precision', f'{metrics["precision"]:.4f}')
    st.metric('Recall', f'{metrics["recall"]:.4f}')
    st.metric('F1', f'{metrics["f1"]:.4f}')
    st.caption(f'FPR {metrics["false_positive_rate"]:.4f}  ·  '
               f'FNR {metrics["false_negative_rate"]:.4f}')

# ── Tabs: confirm / record / replay batch ─────────────────────────────────
st.markdown('---')
tab_pending, tab_record, tab_replay, tab_log = st.tabs(
    ['Confirm pending', 'Record manually', 'Replay batch', 'Raw log'],
)

# Snapshot pending predictions from in-memory monitor.
pending_snapshot = list(monitor._pending.items())  # (pid, predicted_label)

with tab_pending:
    if not pending_snapshot:
        st.info('No pending predictions. Run a prediction with '
                '"Record to drift monitor" enabled on the Predict page first.')
    else:
        st.caption(f'{len(pending_snapshot)} predictions awaiting confirmation.')
        df = pd.DataFrame([
            {'prediction_id': pid, 'predicted_label': lab}
            for pid, lab in pending_snapshot
        ])
        st.dataframe(df, hide_index=True, use_container_width=True, height=240)
        chosen_pid = st.selectbox('Choose prediction to confirm',
                                  options=[pid for pid, _ in pending_snapshot])
        confirmed_label = st.radio('Confirmed label',
                                   options=[0, 1],
                                   format_func=lambda v: 'LEGITIMATE (0)' if v == 0 else 'PHISHING (1)',
                                   horizontal=True)
        if st.button('Record confirmation', type='primary'):
            try:
                monitor.record_confirmation(chosen_pid, int(confirmed_label))
                st.success(f'Confirmed `{chosen_pid}` as label {confirmed_label}')
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f'Failed: {e}')

with tab_record:
    st.caption(
        'Record a prediction + confirmation pair manually. Useful for '
        'demoing the FPR alert without running an actual model call.'
    )
    pid_input = st.text_input('prediction_id (unique)',
                              value=f'manual-{datetime.now(timezone.utc).isoformat()}')
    pred_label = st.radio('Predicted label', [0, 1], horizontal=True, key='pred_l')
    pred_prob = st.slider('Predicted phishing probability', 0.0, 1.0, 0.5, 0.01)
    confirm_now = st.toggle('Also record confirmation now', value=True)
    confirmed_label_m = st.radio('Confirmed label', [0, 1], horizontal=True,
                                 key='conf_l') if confirm_now else None
    if st.button('Record'):
        try:
            registry = get_registry()
            monitor.record_prediction(
                prediction_id=pid_input,
                predicted_label=int(pred_label),
                predicted_probability=float(pred_prob),
                model_version=registry.active_version() or '',
            )
            if confirm_now:
                monitor.record_confirmation(pid_input, int(confirmed_label_m))
            st.success('Recorded.')
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(f'Failed: {e}')

with tab_replay:
    st.caption(
        'Take a synthetic dataset, predict each row with the active model, '
        'record predictions to this monitor, and confirm against the '
        'ground-truth `label` column. This is the fastest way to populate '
        'the confusion matrix.'
    )
    available = list_synthetic_datasets()
    if not available:
        st.warning('No CSVs found in `_datasets/online_learning/`.')
    else:
        chosen_csv = st.selectbox('Dataset', available, key='replay_csv')
        n_rows = st.slider('Rows to replay', 10, 2000, 100, 10)
        if st.button('Run replay', type='primary'):
            df = load_synthetic_csv(chosen_csv).head(n_rows)
            if 'label' not in df.columns:
                st.error('Dataset has no `label` column — cannot confirm.')
            else:
                emails = [
                    {'sender': str(r.get('sender', '')),
                     'subject': str(r.get('subject', '')),
                     'body': str(r.get('body', ''))}
                    for _, r in df.iterrows()
                ]
                detector = load_detector(version=None, review_low=None,
                                         review_high=None, use_calibrator=False)
                detector.drift_monitor = monitor
                with st.spinner(f'Predicting & confirming {n_rows} rows…'):
                    results = detector.predict_batch(emails)
                    for r, true_label in zip(results, df['label'].astype(int).tolist()):
                        monitor.record_confirmation(r.prediction_id, true_label)
                st.success(f'Replayed {n_rows} rows. Refresh chart above.')
                st.rerun()

with tab_log:
    if not DRIFT_LOG_PATH.exists():
        st.info('Drift log file does not exist yet.')
    else:
        records = []
        with DRIFT_LOG_PATH.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        if not records:
            st.info('Drift log is empty.')
        else:
            df_log = pd.DataFrame(records)
            st.caption(f'{len(df_log)} records')
            st.dataframe(df_log.tail(500), hide_index=True,
                         use_container_width=True, height=420)

            # FPR over time: walk through records, recompute FPR after each
            # confirmation, plot the trace.
            tp = tn = fp = fn = 0
            pending: dict[str, int] = {}
            history: list[dict] = []
            for rec in records:
                if rec.get('type') == 'prediction':
                    pending[rec['prediction_id']] = int(rec['predicted_label'])
                elif rec.get('type') == 'confirmation':
                    pid = rec['prediction_id']
                    pred = pending.pop(pid, None)
                    if pred is None:
                        continue
                    conf = int(rec['confirmed_label'])
                    if pred == 1 and conf == 1: tp += 1
                    elif pred == 0 and conf == 0: tn += 1
                    elif pred == 1 and conf == 0: fp += 1
                    elif pred == 0 and conf == 1: fn += 1
                    fpr = fp / (fp + tn) if (fp + tn) else 0.0
                    history.append({
                        'timestamp': rec.get('timestamp'),
                        'fpr': fpr,
                        'confirmations': tp + tn + fp + fn,
                    })
            if history:
                hist_df = pd.DataFrame(history)
                fig = px.line(
                    hist_df, x='confirmations', y='fpr',
                    title='Cumulative false-positive rate over confirmations',
                    markers=False,
                )
                fig.add_hline(y=fpr_threshold, line_dash='dash', line_color='red',
                              annotation_text=f'threshold {fpr_threshold:.2f}')
                st.plotly_chart(fig, use_container_width=True)

footer()
