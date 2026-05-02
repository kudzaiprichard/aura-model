"""Shared theme + UI components for the AURA dashboard.

`apply_theme()` injects a single block of CSS that:
- imports the Inter font
- tightens typography and padding to feel like a modern SaaS console
- repaints the sidebar as a dark navigation rail (Linear / Vercel-style)
- adds reusable `.aura-*` classes used by `kpi_card`, `status_pill`,
  `section_card`, `page_header`, and `hero`.

Each page calls `apply_theme()` once near the top. The helpers are thin
markdown wrappers — they emit HTML that targets the injected classes.
"""

from __future__ import annotations

from typing import Iterable

import streamlit as st


# ──────────────────────────────────────────────────────────────────────────
# Tokens (kept here so charts can re-use the same palette)
# ──────────────────────────────────────────────────────────────────────────

PALETTE = {
    'primary': '#3B82F6',
    'primary_dark': '#1E40AF',
    'success': '#34D399',
    'success_soft': '#064E3B',
    'success_text': '#A7F3D0',
    'warning': '#FBBF24',
    'warning_soft': '#78350F',
    'warning_text': '#FDE68A',
    'danger': '#F87171',
    'danger_soft': '#7F1D1D',
    'danger_text': '#FECACA',
    'neutral_soft': '#1E293B',
    'neutral_text': '#CBD5E1',
    'bg': '#0B1120',
    'surface': '#111827',
    'surface_elev': '#1E293B',
    'border': '#1F2937',
    'text': '#F1F5F9',
    'text_muted': '#94A3B8',
}

ZONE_BADGE = {
    'SPAM': ('danger', 'High-risk phishing'),
    'NOT_SPAM': ('success', 'Legitimate'),
    'REVIEW': ('warning', 'Manual review'),
}


# ──────────────────────────────────────────────────────────────────────────
# CSS injection
# ──────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --aura-bg: #0B1120;
    --aura-surface: #111827;
    --aura-surface-elev: #1E293B;
    --aura-border: #1F2937;
    --aura-border-strong: #334155;
    --aura-text: #F1F5F9;
    --aura-text-muted: #94A3B8;
    --aura-primary: #3B82F6;
    --aura-primary-dim: #1E40AF;
}

html, body, .stApp, [class*="css"], [class*="st-"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
    background-color: var(--aura-bg);
    color: var(--aura-text);
}
code, pre, .stCode { font-family: 'JetBrains Mono', monospace !important; }

/* Main canvas */
.block-container {
    padding-top: 2.4rem;
    padding-bottom: 4rem;
    max-width: 1320px;
}

/* Headings */
h1 { font-weight: 700; letter-spacing: -0.025em; color: #F8FAFC; }
h2, h3, h4 { font-weight: 600; letter-spacing: -0.012em; color: #F8FAFC; }
h2 { font-size: 1.6rem; margin-top: 1.6rem; }
h3 { font-size: 1.2rem; margin-top: 1.2rem; }
p, li, label, .stMarkdown { color: var(--aura-text); }

/* Sidebar — even darker rail with a faint blue accent */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #060B17 0%, #0F172A 100%);
    border-right: 1px solid var(--aura-border);
}
section[data-testid="stSidebar"] * { color: #E2E8F0; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4 { color: #F8FAFC !important; }
section[data-testid="stSidebar"] a { color: #93C5FD !important; }
section[data-testid="stSidebar"] hr { border-color: #1F2937; }
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #CBD5E1;
}
section[data-testid="stSidebar"] [role="radiogroup"] label,
section[data-testid="stSidebar"] [data-baseweb="select"] > div {
    color: #F1F5F9 !important;
}

/* Buttons */
.stButton > button {
    font-weight: 600;
    border-radius: 8px;
    background: var(--aura-surface-elev);
    color: var(--aura-text);
    border: 1px solid var(--aura-border-strong);
    transition: all 120ms ease;
}
.stButton > button:hover {
    border-color: var(--aura-primary);
    background: #1F2937;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}
.stButton > button[kind="primary"] {
    background: var(--aura-primary); color: white; border-color: var(--aura-primary);
}
.stButton > button[kind="primary"]:hover {
    background: #2563EB;
    box-shadow: 0 4px 16px rgba(59, 130, 246, 0.35);
}
.stDownloadButton > button { background: var(--aura-surface-elev); color: var(--aura-text); }

/* Inputs, selectboxes, sliders, text-areas */
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
[data-baseweb="select"] > div {
    background: var(--aura-surface) !important;
    color: var(--aura-text) !important;
    border-radius: 8px;
}
[data-baseweb="input"], [data-baseweb="select"], [data-baseweb="textarea"] {
    border-radius: 8px;
}
[data-baseweb="input"] input:focus,
[data-baseweb="textarea"] textarea:focus {
    border-color: var(--aura-primary) !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

/* Sliders — colour the active track */
[data-baseweb="slider"] [data-testid="stTickBar"] { color: var(--aura-text-muted); }

/* Metric cards */
[data-testid="stMetric"] {
    background: var(--aura-surface);
    border: 1px solid var(--aura-border);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}
[data-testid="stMetricLabel"] { color: var(--aura-text-muted); font-weight: 500; }
[data-testid="stMetricValue"] { font-weight: 700; color: var(--aura-text); }

/* Tabs */
[data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid var(--aura-border);
}
[data-baseweb="tab"] {
    padding: 0.5rem 1rem;
    border-radius: 8px 8px 0 0;
    color: var(--aura-text-muted);
    background: transparent;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #93C5FD;
    background: rgba(59, 130, 246, 0.08);
    border-bottom: 2px solid var(--aura-primary);
}

/* DataFrame polish */
[data-testid="stDataFrame"] {
    border: 1px solid var(--aura-border);
    border-radius: 10px;
    overflow: hidden;
}

/* Expander chrome */
.streamlit-expanderHeader, [data-testid="stExpander"] details {
    background: var(--aura-surface) !important;
    border: 1px solid var(--aura-border) !important;
    border-radius: 10px !important;
}

/* Code blocks */
[data-testid="stCodeBlock"] pre, .stCode {
    background: #060B17 !important;
    border: 1px solid var(--aura-border);
    border-radius: 10px;
}

/* Alerts (success / warning / error / info) — softer corners */
[data-testid="stAlert"] {
    border-radius: 10px;
    border-left-width: 4px;
    background: var(--aura-surface) !important;
    color: var(--aura-text) !important;
}

/* File uploader dropzone */
[data-testid="stFileUploaderDropzone"] {
    background: var(--aura-surface) !important;
    border: 1px dashed var(--aura-border-strong) !important;
    color: var(--aura-text-muted);
}

/* ── Custom AURA components ───────────────────────────────────────── */

.aura-card {
    background: var(--aura-surface);
    border: 1px solid var(--aura-border);
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
    margin-bottom: 1rem;
    transition: border-color 140ms ease, transform 140ms ease;
}
.aura-card:hover {
    border-color: var(--aura-border-strong);
    transform: translateY(-1px);
}
.aura-card h4 {
    margin: 0 0 0.4rem 0;
    font-weight: 600;
    color: #F8FAFC;
    font-size: 1.05rem;
}
.aura-card p { color: #CBD5E1; margin: 0.2rem 0 0 0; }

.aura-hero {
    background:
        radial-gradient(ellipse 80% 60% at 0% 0%, rgba(59,130,246,0.35), transparent 60%),
        radial-gradient(ellipse 60% 80% at 100% 100%, rgba(167,139,250,0.25), transparent 60%),
        linear-gradient(135deg, #0F172A 0%, #111827 60%, #1E293B 100%);
    color: white;
    border: 1px solid #1F2937;
    border-radius: 16px;
    padding: 2.2rem 2.4rem;
    margin-bottom: 1.6rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}
.aura-hero h1 { color: #F8FAFC; margin: 0; font-size: 2.2rem; }
.aura-hero p { color: #CBD5E1; margin: 0.5rem 0 0 0; font-size: 1.05rem; }
.aura-hero .aura-hero-tag {
    display: inline-block;
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.3);
    color: #93C5FD;
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 0.8rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.aura-page-header {
    border-bottom: 1px solid var(--aura-border);
    padding-bottom: 1rem;
    margin-bottom: 1.6rem;
}
.aura-page-header h1 { margin-bottom: 0.2rem; font-size: 1.9rem; color: #F8FAFC; }
.aura-page-header p { color: var(--aura-text-muted); margin: 0; font-size: 0.96rem; }
.aura-page-header .aura-eyebrow {
    color: #93C5FD;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}

.aura-pill {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    line-height: 1.4;
    border: 1px solid transparent;
}
.aura-pill-success { background: rgba(52, 211, 153, 0.12); color: #6EE7B7; border-color: rgba(52, 211, 153, 0.3); }
.aura-pill-warning { background: rgba(251, 191, 36, 0.12); color: #FCD34D; border-color: rgba(251, 191, 36, 0.3); }
.aura-pill-danger  { background: rgba(248, 113, 113, 0.12); color: #FCA5A5; border-color: rgba(248, 113, 113, 0.3); }
.aura-pill-neutral { background: #1E293B; color: #CBD5E1; border-color: #334155; }
.aura-pill-primary { background: rgba(59, 130, 246, 0.14); color: #93C5FD; border-color: rgba(59, 130, 246, 0.3); }

.aura-stat {
    background: var(--aura-surface);
    border: 1px solid var(--aura-border);
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
}
.aura-stat .aura-stat-label {
    color: var(--aura-text-muted);
    font-size: 0.78rem;
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.aura-stat .aura-stat-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #F8FAFC;
    margin-top: 0.25rem;
}
.aura-stat .aura-stat-help {
    color: #64748B;
    font-size: 0.82rem;
    margin-top: 0.2rem;
}

.aura-banner {
    border-radius: 12px;
    padding: 1.1rem 1.4rem;
    margin: 0.4rem 0 1rem 0;
    border-left: 4px solid;
    color: var(--aura-text);
}
.aura-banner h4 { margin: 0; font-size: 1rem; font-weight: 600; }
.aura-banner p { margin: 0.3rem 0 0 0; color: #CBD5E1; }
.aura-banner-success { background: rgba(52, 211, 153, 0.08); border-color: #34D399; }
.aura-banner-success h4 { color: #6EE7B7; }
.aura-banner-warning { background: rgba(251, 191, 36, 0.08); border-color: #FBBF24; }
.aura-banner-warning h4 { color: #FCD34D; }
.aura-banner-danger  { background: rgba(248, 113, 113, 0.08); border-color: #F87171; }
.aura-banner-danger  h4 { color: #FCA5A5; }
.aura-banner-info    { background: rgba(59, 130, 246, 0.08); border-color: #3B82F6; }
.aura-banner-info    h4 { color: #93C5FD; }

.aura-footer {
    text-align: center;
    color: var(--aura-text-muted);
    font-size: 0.82rem;
    margin-top: 3rem;
    padding-top: 1.2rem;
    border-top: 1px solid var(--aura-border);
}

/* Hide the top-right Streamlit menu noise for a cleaner enterprise feel */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header [data-testid="stDecoration"] { display: none; }
header[data-testid="stHeader"] { background: transparent; }
</style>
"""


def apply_theme() -> None:
    """Inject the AURA theme. Call once near the top of every page."""
    st.markdown(_CSS, unsafe_allow_html=True)
    _set_plotly_dark_default()


def _set_plotly_dark_default() -> None:
    """Make plotly default to a dark template that matches the dashboard."""
    try:
        import plotly.io as pio
        if 'aura_dark' not in pio.templates:
            base = pio.templates['plotly_dark'].to_plotly_json()
            base['layout']['paper_bgcolor'] = '#111827'
            base['layout']['plot_bgcolor'] = '#0F172A'
            base['layout']['font'] = {'color': '#E2E8F0', 'family': 'Inter, sans-serif'}
            base['layout']['colorway'] = [
                '#3B82F6', '#A78BFA', '#34D399', '#FBBF24',
                '#F87171', '#22D3EE', '#F472B6', '#A3E635',
            ]
            base['layout']['xaxis'] = {'gridcolor': '#1F2937', 'zerolinecolor': '#1F2937'}
            base['layout']['yaxis'] = {'gridcolor': '#1F2937', 'zerolinecolor': '#1F2937'}
            pio.templates['aura_dark'] = base
        pio.templates.default = 'aura_dark'
    except Exception:  # noqa: BLE001 — plotly missing should not break the app
        pass


# ──────────────────────────────────────────────────────────────────────────
# Components
# ──────────────────────────────────────────────────────────────────────────

def page_header(eyebrow: str, title: str, subtitle: str | None = None) -> None:
    """Consistent page-top banner: small eyebrow, big title, muted subtitle."""
    sub = f'<p>{subtitle}</p>' if subtitle else ''
    st.markdown(
        f'<div class="aura-page-header">'
        f'<div class="aura-eyebrow">{eyebrow}</div>'
        f'<h1>{title}</h1>{sub}</div>',
        unsafe_allow_html=True,
    )


def hero(tag: str, title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="aura-hero">'
        f'<span class="aura-hero-tag">{tag}</span>'
        f'<h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def status_pill(text: str, tone: str = 'neutral') -> str:
    """Return an inline HTML pill — use inside `st.markdown(..., unsafe_allow_html=True)`."""
    return f'<span class="aura-pill aura-pill-{tone}">{text}</span>'


def render_pill(text: str, tone: str = 'neutral') -> None:
    st.markdown(status_pill(text, tone), unsafe_allow_html=True)


def stat_card(label: str, value: str, help_text: str | None = None) -> None:
    h = f'<div class="aura-stat-help">{help_text}</div>' if help_text else ''
    st.markdown(
        f'<div class="aura-stat">'
        f'<div class="aura-stat-label">{label}</div>'
        f'<div class="aura-stat-value">{value}</div>{h}</div>',
        unsafe_allow_html=True,
    )


def banner(title: str, body: str, tone: str = 'info') -> None:
    st.markdown(
        f'<div class="aura-banner aura-banner-{tone}">'
        f'<h4>{title}</h4><p>{body}</p></div>',
        unsafe_allow_html=True,
    )


def card(title: str, body: str) -> None:
    st.markdown(
        f'<div class="aura-card"><h4>{title}</h4><p>{body}</p></div>',
        unsafe_allow_html=True,
    )


def feature_grid(items: Iterable[tuple[str, str]], cols: int = 2) -> None:
    """Layout a grid of (title, description) cards across `cols` columns."""
    items = list(items)
    columns = st.columns(cols)
    for i, (title, body) in enumerate(items):
        with columns[i % cols]:
            card(title, body)


def footer(text: str = 'AURA — Adaptive User Risk Analyzer') -> None:
    st.markdown(f'<div class="aura-footer">{text}</div>', unsafe_allow_html=True)


def zone_pill(zone: str | None) -> str:
    if not zone:
        return status_pill('—', 'neutral')
    tone, _ = ZONE_BADGE.get(zone, ('neutral', zone))
    return status_pill(zone.replace('_', ' '), tone)


def label_pill(label: int) -> str:
    return (
        status_pill('PHISHING', 'danger') if label == 1
        else status_pill('LEGITIMATE', 'success')
    )
