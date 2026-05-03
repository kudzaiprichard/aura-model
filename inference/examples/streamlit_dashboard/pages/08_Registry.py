"""Registry page — inspect, set-active, and verify integrity."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(_DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_ROOT))

from theme import apply_theme, footer, page_header, stat_card  # noqa: E402
from utils import get_models_root, get_registry, load_detector  # noqa: E402

st.set_page_config(page_title='Registry — AURA', layout='wide')
apply_theme()
page_header(
    eyebrow='Governance',
    title='Model registry',
    subtitle='Inspect every registered version, set the active model, and verify integrity.',
)

registry = get_registry()
meta = registry._read_registry_metadata()
versions_meta: dict = meta.get('versions', {})
disk = registry.list_versions()
active = registry.active_version()

c1, c2, c3 = st.columns(3)
with c1:
    stat_card('Active version', active or '—', 'Live model')
with c2:
    stat_card('Versions on disk', str(len(disk)), 'Available artefacts')
with c3:
    stat_card('Tracked in metadata', str(len(versions_meta)),
              'Registered entries')

st.markdown('### Versions on disk')
rows = []
for v in disk:
    entry = versions_meta.get(v, {}) or {}
    metrics = entry.get('metrics', {}) or {}
    paths = registry.paths_for(v)
    rows.append({
        'version': v,
        'active': v == active,
        'promoted': bool(entry.get('promoted', False)),
        'source': entry.get('source_version') or '',
        'sha256': (entry.get('sha256') or '')[:12],
        'calibrator?': bool(paths.get('calibrator')),
        'accuracy': metrics.get('accuracy'),
        'precision': metrics.get('precision'),
        'recall': metrics.get('recall'),
        'f1': metrics.get('f1'),
    })
df = pd.DataFrame(rows)
st.dataframe(df, hide_index=True, use_container_width=True)

# ── Per-version actions ───────────────────────────────────────────────────
st.markdown('### Inspect / activate')
chosen = st.selectbox('Select version', disk,
                      index=disk.index(active) if active in disk else 0)

paths = registry.paths_for(chosen)
st.code(
    json.dumps({k: str(v) if v else None for k, v in paths.items()}, indent=2),
    language='json',
)

entry = versions_meta.get(chosen, {})
with st.expander('Registry-level metadata for this version'):
    st.json(entry)

a, b, c = st.columns(3)
with a:
    if st.button('Set as active', use_container_width=True,
                 disabled=(chosen == active)):
        try:
            registry.set_active(chosen, verify_integrity=True)
            get_registry.clear()
            load_detector.clear()
            st.success(f'Active version is now {chosen}')
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(f'Failed: {e}')

with b:
    if st.button('Verify integrity (sha256)', use_container_width=True):
        try:
            registry._verify_integrity(chosen)
            st.success('Integrity check passed.')
        except Exception as e:  # noqa: BLE001
            st.error(f'Integrity check failed: {e}')

with c:
    if st.button('Refresh registry view', use_container_width=True):
        get_registry.clear()
        st.rerun()

# ── Raw metadata file ─────────────────────────────────────────────────────
st.markdown('### Raw `model_metadata.json`')
meta_path = get_models_root() / 'model_metadata.json'
if meta_path.exists():
    st.code(meta_path.read_text(encoding='utf-8'), language='json')
else:
    st.info('Registry metadata file not present yet.')

footer()
