"""Model Management page — full CRUD over registered model versions.

Create   : register an uploaded classifier as a new version.
Read     : inspect every version, its metrics, paths, and raw metadata.
Update   : edit notes / metrics; activate or deactivate.
Delete   : remove a version's artefacts (with a confirmation guard).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(_DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_ROOT))

from theme import apply_theme, banner, footer, page_header, stat_card  # noqa: E402
from utils import (  # noqa: E402
    clear_registry_caches,
    get_models_root,
    get_registry,
    load_uploaded_model,
    sidebar_status,
)

st.set_page_config(page_title='Model Management — AURA', layout='wide', page_icon='🗂️')
apply_theme()
sidebar_status()
page_header(
    eyebrow='Governance',
    title='Model management',
    subtitle='Register, inspect, edit, activate / deactivate, verify, and delete model versions.',
)

registry = get_registry()
meta = registry._read_registry_metadata()
versions_meta: dict = meta.get('versions', {})
disk = registry.list_versions()
active = registry.active_version()

if not disk:
    st.warning('No model versions on disk. Use the **Create** tab to register one.')

# ── KPI strip ──────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
with c1:
    stat_card('Active model', active or '— none —', 'Serves traffic by default')
with c2:
    stat_card('Versions on disk', str(len(disk)), 'Available artefacts')
with c3:
    stat_card('Tracked in metadata', str(len(versions_meta)), 'Registered entries')

if active is None and disk:
    banner(
        'No active model',
        'Prediction pages fall back to the latest version on disk '
        f'(<code>{registry.latest_version()}</code>). Activate a version below '
        'to pin it.',
        tone='warning',
    )

# ── Registry table ─────────────────────────────────────────────────────────
st.markdown('### Registered versions')
rows = []
for v in disk:
    entry = versions_meta.get(v, {}) or {}
    metrics = entry.get('metrics', {}) or {}
    paths = registry.paths_for(v)
    rows.append({
        'version': v,
        'active': '✅' if v == active else '',
        'promoted': '✔' if entry.get('promoted') else '',
        'source': entry.get('source_version') or '',
        'accuracy': metrics.get('accuracy'),
        'precision': metrics.get('precision'),
        'recall': metrics.get('recall'),
        'f1': metrics.get('f1'),
        'calibrator': '✔' if paths.get('calibrator') else '',
        'sha256': (entry.get('sha256') or '')[:12],
        'notes': entry.get('notes', ''),
    })
table = pd.DataFrame(rows)
if not table.empty:
    st.dataframe(table, hide_index=True, use_container_width=True)

# ── Metric trend across versions + active-model spotlight ──────────────────
trend_rows = []
for v in disk:
    metrics = (versions_meta.get(v, {}) or {}).get('metrics', {}) or {}
    for k in ('accuracy', 'precision', 'recall', 'f1'):
        if metrics.get(k) is not None:
            trend_rows.append({'version': v, 'metric': k, 'value': metrics[k]})

left, right = st.columns([3, 2], gap='large')
with left:
    st.markdown('##### Metrics across versions')
    if trend_rows:
        tdf = pd.DataFrame(trend_rows)
        fig = px.line(tdf, x='version', y='value', color='metric', markers=True,
                      category_orders={'version': disk}, range_y=[0, 1.02])
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
                          legend_title_text='')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('No recorded metrics yet. Metrics are written by Online Learning '
                'runs and can be edited on the **Edit metadata** tab.')
with right:
    st.markdown('##### Active model spotlight')
    if active:
        sp = versions_meta.get(active, {}) or {}
        spm = sp.get('metrics', {}) or {}
        ap = registry.paths_for(active)
        st.markdown(
            f'<div class="aura-card">'
            f'<h4>🟢 {active}</h4>'
            f'<p>source <code>{sp.get("source_version") or "—"}</code> · '
            f'calibrator {"yes" if ap.get("calibrator") else "no"}</p></div>',
            unsafe_allow_html=True,
        )
        s1, s2 = st.columns(2)
        s1.metric('F1', f'{spm["f1"]:.3f}' if spm.get('f1') is not None else '—')
        s2.metric('Accuracy', f'{spm["accuracy"]:.3f}' if spm.get('accuracy') is not None else '—')
        s3, s4 = st.columns(2)
        s3.metric('Precision', f'{spm["precision"]:.3f}' if spm.get('precision') is not None else '—')
        s4.metric('Recall', f'{spm["recall"]:.3f}' if spm.get('recall') is not None else '—')
    else:
        st.warning('No active model set. Activate one below to pin a model for '
                   'prediction traffic.')

# ── CRUD tabs ──────────────────────────────────────────────────────────────
tab_rud, tab_edit, tab_create, tab_delete = st.tabs(
    ['🔌 Activate / Inspect', '✏️ Edit metadata', '➕ Register (create)', '🗑️ Delete']
)

# ---- Activate / Inspect / Verify -----------------------------------------
with tab_rud:
    if not disk:
        st.info('No versions to inspect.')
    else:
        chosen = st.selectbox('Version', disk,
                              index=disk.index(active) if active in disk else 0)
        paths = registry.paths_for(chosen)
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            if st.button('Set as active', use_container_width=True,
                         type='primary', disabled=(chosen == active)):
                try:
                    registry.set_active(chosen, verify_integrity=True)
                    clear_registry_caches()
                    st.success(f'Active model is now {chosen}.')
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(f'Failed: {e}')
        with col_b:
            if st.button('Deactivate (clear active)', use_container_width=True,
                         disabled=(active is None)):
                try:
                    registry.deactivate()
                    clear_registry_caches()
                    st.success('Active pointer cleared — pages fall back to latest.')
                    st.rerun()
                except Exception as e:  # noqa: BLE001
                    st.error(f'Failed: {e}')
        with col_c:
            if st.button('Verify integrity (sha256)', use_container_width=True):
                try:
                    registry._verify_integrity(chosen)
                    st.success('Integrity check passed.')
                except Exception as e:  # noqa: BLE001
                    st.error(f'Integrity check failed: {e}')
        with col_d:
            if st.button('Refresh', use_container_width=True):
                clear_registry_caches()
                st.rerun()

        st.markdown('#### Artefact paths')
        st.code(json.dumps({k: (str(v) if v else None) for k, v in paths.items()},
                           indent=2), language='json')
        with st.expander('Registry-level metadata for this version'):
            st.json(versions_meta.get(chosen, {}))

# ---- Update metadata ------------------------------------------------------
with tab_edit:
    if not disk:
        st.info('No versions to edit.')
    else:
        ev = st.selectbox('Version to edit', disk, key='edit_version')
        entry = versions_meta.get(ev, {}) or {}
        cur_metrics = entry.get('metrics', {}) or {}
        st.caption('Edit the free-text note and/or the recorded holdout metrics. '
                   'Leave a metric blank to keep it unchanged.')
        notes = st.text_area('Notes', value=entry.get('notes', ''), height=100)
        m1, m2, m3, m4 = st.columns(4)
        acc = m1.text_input('accuracy', value=str(cur_metrics.get('accuracy', '')))
        prec = m2.text_input('precision', value=str(cur_metrics.get('precision', '')))
        rec = m3.text_input('recall', value=str(cur_metrics.get('recall', '')))
        f1 = m4.text_input('f1', value=str(cur_metrics.get('f1', '')))
        if st.button('Save metadata', type='primary'):
            new_metrics = dict(cur_metrics)
            for key, raw in (('accuracy', acc), ('precision', prec),
                             ('recall', rec), ('f1', f1)):
                raw = (raw or '').strip()
                if raw:
                    try:
                        new_metrics[key] = float(raw)
                    except ValueError:
                        st.error(f'{key} is not a number: {raw!r}')
                        st.stop()
            try:
                registry.update_version_metadata(
                    ev, metrics=new_metrics or None, notes=notes)
                clear_registry_caches()
                st.success(f'Updated metadata for {ev}.')
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f'Failed: {e}')

# ---- Create / register ----------------------------------------------------
with tab_create:
    st.caption(
        'Register a joblib-pickled scikit-learn classifier as a new version. '
        'It must expose `predict_proba` and `n_features_in_ == 7015` (the '
        'registry pipeline dimension). The new version derives its number from '
        'the chosen source version.'
    )
    if not disk:
        st.info('Need at least one existing version to derive a source from. '
                'Bootstrap the registry outside the dashboard first.')
    else:
        src = st.selectbox('Source version (parent)', disk,
                           index=disk.index(active) if active in disk else 0)
        model_file = st.file_uploader('Model .pkl / .joblib',
                                      type=['pkl', 'joblib'], key='create_model')
        activate_after = st.checkbox('Activate the new version after registering')
        if model_file is not None and st.button('Register new version', type='primary'):
            try:
                model = load_uploaded_model(model_file)
                # register_new_version expects a model object + source version.
                new_version = registry.register_new_version(
                    model, source_version=src, metrics={})
                if activate_after:
                    registry.set_active(new_version, verify_integrity=True)
                clear_registry_caches()
                st.success(
                    f'Registered **{new_version}** from source {src}'
                    + (' and activated it.' if activate_after else '.'))
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f'Registration failed: {e}')

# ---- Delete ---------------------------------------------------------------
with tab_delete:
    if not disk:
        st.info('No versions to delete.')
    else:
        dv = st.selectbox('Version to delete', disk, key='delete_version')
        if dv == active:
            st.warning('This is the **active** model — deleting it clears the '
                       'active pointer.')
        st.caption('Shared `pipeline_components/` (vectorisers, calibrator) are '
                   'never touched. This permanently removes the version directory.')
        confirm = st.checkbox(f'I understand — permanently delete `{dv}`.')
        if st.button('Delete version', type='primary', disabled=not confirm):
            try:
                registry.delete_version(dv)
                clear_registry_caches()
                st.success(f'Deleted {dv}.')
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f'Delete failed: {e}')

st.markdown('### Raw `model_metadata.json`')
meta_path = get_models_root() / 'model_metadata.json'
if meta_path.exists():
    with st.expander('Show registry metadata file'):
        st.code(meta_path.read_text(encoding='utf-8'), language='json')

footer()
