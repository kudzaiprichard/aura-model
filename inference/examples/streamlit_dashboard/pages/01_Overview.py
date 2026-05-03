"""Overview page — registry snapshot and metric trend across versions."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Make sibling utils.py importable when Streamlit launches a page directly.
_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(_DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_ROOT))

from theme import apply_theme, footer, page_header, stat_card  # noqa: E402
from utils import get_models_root, get_registry  # noqa: E402

st.set_page_config(page_title='Overview — AURA', layout='wide')
apply_theme()
page_header(
    eyebrow='Console',
    title='Overview',
    subtitle='Registry snapshot, metric trends across registered versions, and quick navigation.',
)

registry = get_registry()
meta = registry._read_registry_metadata()
versions_meta: dict = meta.get('versions', {})
disk_versions = registry.list_versions()
active = registry.active_version() or '—'

c1, c2, c3, c4 = st.columns(4)
with c1:
    stat_card('Active version', active, 'Live model')
with c2:
    stat_card('Versions on disk', str(len(disk_versions)), 'Available artefacts')
with c3:
    stat_card('Tracked in metadata', str(len(versions_meta)), 'Registered entries')
with c4:
    stat_card('Models root', f'<code>{get_models_root().name}</code>',
              str(get_models_root().parent))

st.markdown('### Version metrics')

rows = []
for v in disk_versions:
    entry = versions_meta.get(v, {})
    metrics = entry.get('metrics', {}) or {}
    rows.append({
        'version': v,
        'active': v == active,
        'promoted': bool(entry.get('promoted', False)),
        'source': entry.get('source_version') or '',
        'accuracy': metrics.get('accuracy'),
        'precision': metrics.get('precision'),
        'recall': metrics.get('recall'),
        'f1': metrics.get('f1'),
        'sha256': (entry.get('sha256') or '')[:12],
    })
df = pd.DataFrame(rows)

if df.empty:
    st.info('No registered versions yet.')
    st.stop()

st.dataframe(df, hide_index=True, use_container_width=True)

st.markdown('### Metric trend')
metric_cols = ['accuracy', 'precision', 'recall', 'f1']
plot_df = df.melt(id_vars=['version'], value_vars=metric_cols,
                  var_name='metric', value_name='value').dropna()
if not plot_df.empty:
    fig = px.line(
        plot_df,
        x='version',
        y='value',
        color='metric',
        markers=True,
        title='Metrics across registered versions',
    )
    fig.update_yaxes(range=[0.0, 1.0])
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info('No metric data recorded yet for any version.')

st.markdown('### Quick actions')
ca, cb, cc = st.columns(3)
with ca:
    if st.button('Refresh registry', use_container_width=True):
        get_registry.clear()
        st.rerun()
with cb:
    if st.button('Open Predict page', use_container_width=True):
        st.switch_page('pages/02_Predict.py')
with cc:
    if st.button('Open Benchmarks', use_container_width=True):
        st.switch_page('pages/07_Benchmarks.py')

footer()
