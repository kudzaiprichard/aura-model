"""AURA inference dashboard — Streamlit entry point.

Run from the repo root:

    streamlit run inference/examples/streamlit_dashboard/app.py

Pages live in `pages/` and Streamlit auto-routes them via the sidebar.
"""

from __future__ import annotations

import streamlit as st

from theme import apply_theme, banner, feature_grid, footer, hero, stat_card
from utils import (
    DRIFT_LOG_PATH,
    get_models_root,
    get_registry,
)

st.set_page_config(
    page_title='AURA — Inference Console',
    page_icon=None,
    layout='wide',
    initial_sidebar_state='expanded',
)

apply_theme()


def render_sidebar() -> None:
    st.sidebar.markdown('## AURA')
    st.sidebar.caption('Adaptive User Risk Analyzer')
    st.sidebar.markdown('---')
    try:
        registry = get_registry()
        active = registry.active_version() or '—'
        versions = registry.list_versions()
    except Exception as e:  # noqa: BLE001
        st.sidebar.error(f'Registry unreachable: {e}')
        return
    st.sidebar.markdown('### Environment')
    st.sidebar.markdown(f'**Active version**  \n`{active}`')
    st.sidebar.markdown(f'**Versions on disk**  \n{len(versions)}')
    st.sidebar.markdown(f'**Models root**  \n`{get_models_root()}`')
    st.sidebar.markdown('### Drift log')
    st.sidebar.caption(f'`{DRIFT_LOG_PATH}`')
    st.sidebar.markdown('---')
    st.sidebar.caption(
        'Use the navigation above to explore each capability. '
        'All pages share the same registry and drift log.'
    )


def render_home() -> None:
    hero(
        tag='Inference Console',
        title='AURA Phishing Detection',
        subtitle=(
            'Predict, review, monitor, retrain, and benchmark — every '
            'capability of the inference module in one enterprise console.'
        ),
    )

    # KPI strip
    try:
        registry = get_registry()
        active = registry.active_version() or '—'
        meta = registry._read_registry_metadata()
        versions = registry.list_versions()
        active_metrics = meta.get('versions', {}).get(active, {}).get('metrics', {})
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            stat_card('Active version', active, 'Live model serving traffic')
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
            ('Single prediction',
             'Score one email with full engineered-feature inspection, '
             'three-zone classification, and optional calibration.'),
            ('Batch prediction',
             'Score hundreds of emails from sample batches, synthetic CSVs, '
             'or your own multi-file uploads with per-dataset breakdowns.'),
            ('Auto-review (LLM)',
             'Send REVIEW-zone predictions to Groq or Google Gemini for a '
             'second opinion — keys are session-only.'),
            ('Drift monitoring',
             'Track confusion matrix and false-positive rate live; replay a '
             'labelled batch in seconds.'),
            ('Online learning',
             'Fine-tune via partial_fit, see before/after metrics, and '
             'promote with an F1-delta guard.'),
            ('Version benchmarks',
             'Compare any registered or uploaded models on the calibration '
             'set or your own labelled data.'),
        ],
        cols=3,
    )

    banner(
        'Heavy operations are cached',
        'Model loading, calibration sub-sampling, and batch predictions '
        'are memoised. The first call on a page may take a few seconds; '
        'subsequent calls are near-instant.',
        tone='info',
    )

    footer()


render_sidebar()
render_home()
