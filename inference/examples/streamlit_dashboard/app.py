"""AURA inference dashboard — Streamlit entry point.

A production console for the AURA phishing-detection inference module,
focused on five capabilities:

    Predict · Batch Predict · Model Management · Online Learning · Benchmarks

Run from the AURA_Model directory:

    streamlit run inference/examples/streamlit_dashboard/app.py

Pages live in ``pages/`` and Streamlit auto-routes them via the sidebar.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Ensure sibling modules import regardless of how Streamlit is launched.
_DASHBOARD_ROOT = Path(__file__).resolve().parent
if str(_DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_ROOT))

from theme import apply_theme, banner, feature_grid, footer, hero, stat_card  # noqa: E402
from utils import get_models_root, get_registry  # noqa: E402

st.set_page_config(
    page_title='AURA — Inference Console',
    page_icon='🛡️',
    layout='wide',
    initial_sidebar_state='expanded',
)

apply_theme()


def render_sidebar() -> None:
    st.sidebar.markdown('## 🛡️ AURA')
    st.sidebar.caption('Adaptive User Risk Analyzer')
    st.sidebar.markdown('---')
    try:
        registry = get_registry()
        active = registry.active_version() or '— none active —'
        versions = registry.list_versions()
    except Exception as e:  # noqa: BLE001
        st.sidebar.error(f'Registry unreachable: {e}')
        return
    st.sidebar.markdown('### Environment')
    st.sidebar.markdown(f'**Active model**  \n`{active}`')
    st.sidebar.markdown(f'**Versions on disk**  \n{len(versions)}')
    st.sidebar.markdown(f'**Models root**  \n`{get_models_root()}`')
    st.sidebar.markdown('---')
    st.sidebar.caption(
        'Predict · Batch Predict · Model Management · Online Learning · '
        'Benchmarks. All pages share one registry.'
    )


def render_home() -> None:
    hero(
        tag='Inference Console',
        title='AURA Phishing Detection',
        subtitle=(
            'Score emails, manage model versions, adapt online, and benchmark '
            'candidates side-by-side — a production console for the AURA '
            'inference module.'
        ),
    )

    try:
        registry = get_registry()
        active = registry.active_version() or '—'
        meta = registry._read_registry_metadata()
        versions = registry.list_versions()
        active_metrics = meta.get('versions', {}).get(active, {}).get('metrics', {})
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            stat_card('Active model', active, 'Serves prediction traffic by default')
        with c2:
            stat_card('Registered versions', str(len(versions)),
                      'Available for benchmarks & rollback')
        with c3:
            stat_card('F1 (active)',
                      f'{active_metrics.get("f1", 0):.3f}' if active_metrics else '—',
                      'Holdout performance')
        with c4:
            stat_card('Accuracy (active)',
                      f'{active_metrics.get("accuracy", 0):.3f}' if active_metrics else '—',
                      'Holdout performance')
    except Exception as e:  # noqa: BLE001
        st.error(f'Could not read registry: {e}')

    st.markdown('### Capabilities')
    feature_grid(
        [
            ('🔍 Predict',
             'Score a single email with the engineered-feature inspector and '
             'three-zone classification. Uses the active model unless you pick '
             'another version.'),
            ('📦 Batch Predict',
             'Score many emails from a CSV / JSON upload (sender, subject, body) '
             'or the built-in demo batches, with charts and CSV export.'),
            ('🗂️ Model Management',
             'Full CRUD over registered versions — inspect, register, edit '
             'notes, activate / deactivate, verify integrity, and delete.'),
            ('🧠 Online Learning',
             'Fine-tune via partial_fit from a labelled CSV, compare before / '
             'after metrics, and promote with an F1-delta guard.'),
            ('🏁 Benchmarks',
             'Compare two or more versions on a labelled dataset, ranked oldest '
             '→ newest with medals and per-metric winners. Saved to JSON.'),
        ],
        cols=3,
    )

    banner(
        'Defaults to the active model',
        'Predict and Batch Predict use the active model unless you explicitly '
        'choose another version. Manage which model is active on the '
        '<b>Model Management</b> page.',
        tone='info',
    )

    footer()


render_sidebar()
render_home()
