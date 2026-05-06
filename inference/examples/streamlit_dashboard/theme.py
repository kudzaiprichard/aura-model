"""Shared theme + UI components for the AURA dashboard.

Theming strategy
----------------
The heavy lifting is done by Streamlit's *native* theme (`.streamlit/config.toml`
`[theme]`), which colours every widget — including dropdown popovers, sliders,
and tooltips — through Streamlit's own variables. That is what keeps the UI
consistent and flicker-free.

`apply_theme()` then injects a *small, targeted* CSS layer that only:
  - loads the Inter / JetBrains Mono web fonts,
  - tightens typography and spacing for a compact enterprise density,
  - polishes the sidebar navigation rail,
  - defines the bespoke `.aura-*` components used by the helpers below.

We deliberately avoid broad selectors (`[class*="st-"]`, universal `*`) and
`!important` overrides, and avoid `transition: all` / hover `transform` — those
were the source of the earlier glitching.
"""

from __future__ import annotations

from typing import Iterable

import streamlit as st


# ──────────────────────────────────────────────────────────────────────────
# Design tokens (mirrors .streamlit/config.toml so charts/components match)
# ──────────────────────────────────────────────────────────────────────────

PALETTE = {
    'primary': '#4F7CFF',
    'primary_dim': '#2B4FD6',
    'success': '#34D399',
    'success_text': '#6EE7B7',
    'warning': '#FBBF24',
    'warning_text': '#FCD34D',
    'danger': '#F87171',
    'danger_text': '#FCA5A5',
    'bg': '#0B0F17',
    'surface': '#131A24',
    'surface_elev': '#1C2530',
    'border': '#243042',
    'border_strong': '#33415A',
    'text': '#E6EAF0',
    'text_muted': '#93A1B5',
}

ZONE_BADGE = {
    'SPAM': ('danger', 'High-risk phishing'),
    'NOT_SPAM': ('success', 'Legitimate'),
    'REVIEW': ('warning', 'Manual review'),
}


# ──────────────────────────────────────────────────────────────────────────
# CSS injection — small and targeted
# ──────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --aura-bg: #0B0F17;
    --aura-surface: #131A24;
    --aura-surface-elev: #1C2530;
    --aura-border: #243042;
    --aura-border-strong: #33415A;
    --aura-text: #E6EAF0;
    --aura-text-muted: #93A1B5;
    --aura-primary: #4F7CFF;
    --aura-primary-dim: #2B4FD6;
    --aura-radius: 0.5rem;
}

/* Font — applied narrowly; widgets inherit it. */
html, body, .stApp { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; -webkit-font-smoothing: antialiased; }
button, input, textarea, select, [data-testid="stMarkdownContainer"] { font-family: inherit; }
code, pre, [data-testid="stCodeBlock"] { font-family: 'JetBrains Mono', ui-monospace, monospace; }

/* Canvas — compact density */
.block-container { padding-top: 2rem; padding-bottom: 3.5rem; max-width: 1280px; }

/* Headings */
h1 { font-weight: 700; letter-spacing: -0.02em; }
h2, h3, h4 { font-weight: 600; letter-spacing: -0.01em; }
h2 { font-size: 1.45rem; margin-top: 1.3rem; }
h3 { font-size: 1.1rem; margin-top: 1rem; }

/* Buttons — colours come from the native theme; we only refine shape + motion */
.stButton > button, .stDownloadButton > button {
    font-weight: 600;
    border-radius: var(--aura-radius);
    transition: border-color 120ms ease, background-color 120ms ease, box-shadow 120ms ease;
}
.stButton > button:hover { box-shadow: 0 0 0 3px rgba(79, 124, 255, 0.14); }
.stButton > button:active { box-shadow: none; }

/* Focus rings */
[data-baseweb="input"] input:focus,
[data-baseweb="textarea"] textarea:focus {
    box-shadow: 0 0 0 3px rgba(79, 124, 255, 0.18);
}

/* Metric cards */
[data-testid="stMetric"] {
    background: var(--aura-surface);
    border: 1px solid var(--aura-border);
    border-radius: var(--aura-radius);
    padding: 0.85rem 1rem;
}
[data-testid="stMetricLabel"] { color: var(--aura-text-muted); font-weight: 500; }

/* Tabs — accent the active tab */
[data-baseweb="tab-list"] { gap: 2px; }
[aria-selected="true"][data-baseweb="tab"] {
    color: var(--aura-primary);
    border-bottom: 2px solid var(--aura-primary);
}

/* Dataframe + expander + alert chrome */
[data-testid="stDataFrame"], [data-testid="stExpander"] details {
    border-radius: var(--aura-radius);
    overflow: hidden;
}
[data-testid="stAlert"] { border-radius: var(--aura-radius); border-left-width: 4px; }
[data-testid="stFileUploaderDropzone"] { border-radius: var(--aura-radius); }

/* ── Sidebar rail ─────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #080B12 0%, #0E141E 100%);
    border-right: 1px solid var(--aura-border);
}
/* Navigation list — rounded, padded items with hover + active accent */
[data-testid="stSidebarNav"] { padding-top: 0.5rem; }
[data-testid="stSidebarNav"] a {
    border-radius: var(--aura-radius);
    margin: 1px 6px;
    padding: 0.32rem 0.6rem;
    transition: background-color 120ms ease, color 120ms ease;
}
[data-testid="stSidebarNav"] a:hover { background: var(--aura-surface-elev); }
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(79, 124, 255, 0.14);
    box-shadow: inset 2px 0 0 var(--aura-primary);
}
[data-testid="stSidebarNav"] a[aria-current="page"] span { color: #C9D6FF; font-weight: 600; }

/* ── Bespoke AURA components ──────────────────────────────────────── */

.aura-card {
    background: var(--aura-surface);
    border: 1px solid var(--aura-border);
    border-radius: var(--aura-radius);
    padding: 1rem 1.15rem;
    margin-bottom: 0.75rem;
    transition: border-color 140ms ease;
}
.aura-card:hover { border-color: var(--aura-border-strong); }
.aura-card h4 { margin: 0 0 0.3rem 0; font-weight: 600; font-size: 1rem; }
.aura-card p { color: var(--aura-text-muted); margin: 0.15rem 0 0 0; font-size: 0.9rem; }

.aura-hero {
    background:
        radial-gradient(ellipse 70% 60% at 0% 0%, rgba(79,124,255,0.30), transparent 60%),
        radial-gradient(ellipse 60% 80% at 100% 100%, rgba(139,124,246,0.18), transparent 60%),
        linear-gradient(135deg, #0E141E 0%, #131A24 60%, #1C2530 100%);
    border: 1px solid var(--aura-border);
    border-radius: 0.75rem;
    padding: 1.7rem 1.9rem;
    margin-bottom: 1.3rem;
}
.aura-hero h1 { margin: 0; font-size: 1.95rem; }
.aura-hero p { color: var(--aura-text-muted); margin: 0.4rem 0 0 0; font-size: 1rem; }
.aura-hero .aura-hero-tag {
    display: inline-block;
    background: rgba(79, 124, 255, 0.14);
    border: 1px solid rgba(79, 124, 255, 0.30);
    color: #9DB6FF;
    padding: 0.18rem 0.65rem;
    border-radius: 999px;
    font-size: 0.74rem; font-weight: 600;
    margin-bottom: 0.7rem;
    letter-spacing: 0.05em; text-transform: uppercase;
}

.aura-page-header { border-bottom: 1px solid var(--aura-border); padding-bottom: 0.85rem; margin-bottom: 1.3rem; }
.aura-page-header h1 { margin-bottom: 0.15rem; font-size: 1.7rem; }
.aura-page-header p { color: var(--aura-text-muted); margin: 0; font-size: 0.92rem; }
.aura-page-header .aura-eyebrow {
    color: #9DB6FF; font-size: 0.74rem; font-weight: 600;
    letter-spacing: 0.09em; text-transform: uppercase; margin-bottom: 0.25rem;
}

.aura-pill {
    display: inline-block; padding: 0.16rem 0.6rem; border-radius: 999px;
    font-size: 0.74rem; font-weight: 600; line-height: 1.4; border: 1px solid transparent;
}
.aura-pill-success { background: rgba(52, 211, 153, 0.12); color: #6EE7B7; border-color: rgba(52, 211, 153, 0.3); }
.aura-pill-warning { background: rgba(251, 191, 36, 0.12); color: #FCD34D; border-color: rgba(251, 191, 36, 0.3); }
.aura-pill-danger  { background: rgba(248, 113, 113, 0.12); color: #FCA5A5; border-color: rgba(248, 113, 113, 0.3); }
.aura-pill-neutral { background: var(--aura-surface-elev); color: var(--aura-text-muted); border-color: var(--aura-border-strong); }
.aura-pill-primary { background: rgba(79, 124, 255, 0.14); color: #9DB6FF; border-color: rgba(79, 124, 255, 0.3); }

.aura-stat {
    background: var(--aura-surface);
    border: 1px solid var(--aura-border);
    border-radius: var(--aura-radius);
    padding: 0.85rem 1rem;
}
.aura-stat .aura-stat-label { color: var(--aura-text-muted); font-size: 0.74rem; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; }
.aura-stat .aura-stat-value { font-size: 1.4rem; font-weight: 700; margin-top: 0.2rem; }
.aura-stat .aura-stat-help { color: #6B7888; font-size: 0.78rem; margin-top: 0.15rem; }

.aura-banner {
    border-radius: var(--aura-radius); padding: 0.9rem 1.15rem; margin: 0.3rem 0 0.9rem 0;
    border-left: 4px solid; background: var(--aura-surface);
}
.aura-banner h4 { margin: 0; font-size: 0.95rem; font-weight: 600; }
.aura-banner p { margin: 0.25rem 0 0 0; color: var(--aura-text-muted); font-size: 0.9rem; }
.aura-banner-success { border-color: #34D399; } .aura-banner-success h4 { color: #6EE7B7; }
.aura-banner-warning { border-color: #FBBF24; } .aura-banner-warning h4 { color: #FCD34D; }
.aura-banner-danger  { border-color: #F87171; } .aura-banner-danger  h4 { color: #FCA5A5; }
.aura-banner-info    { border-color: #4F7CFF; } .aura-banner-info    h4 { color: #9DB6FF; }

.aura-footer { text-align: center; color: var(--aura-text-muted); font-size: 0.8rem; margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid var(--aura-border); }

/* Trim Streamlit chrome for a cleaner console */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header [data-testid="stDecoration"] { display: none; }
header[data-testid="stHeader"] { background: transparent; }
</style>
"""


def apply_theme() -> None:
    """Inject the AURA CSS layer. Call once near the top of every page."""
    st.markdown(_CSS, unsafe_allow_html=True)
    _set_plotly_dark_default()


def _set_plotly_dark_default() -> None:
    """Make Plotly default to a dark template that matches the dashboard tokens."""
    try:
        import plotly.io as pio
        if 'aura_dark' not in pio.templates:
            base = pio.templates['plotly_dark'].to_plotly_json()
            base['layout']['paper_bgcolor'] = PALETTE['surface']
            base['layout']['plot_bgcolor'] = PALETTE['bg']
            base['layout']['font'] = {'color': PALETTE['text'], 'family': 'Inter, sans-serif'}
            base['layout']['colorway'] = [
                '#4F7CFF', '#8B7CF6', '#34D399', '#FBBF24',
                '#F87171', '#22D3EE', '#F472B6', '#A3E635',
            ]
            base['layout']['xaxis'] = {'gridcolor': PALETTE['border'], 'zerolinecolor': PALETTE['border']}
            base['layout']['yaxis'] = {'gridcolor': PALETTE['border'], 'zerolinecolor': PALETTE['border']}
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


# ──────────────────────────────────────────────────────────────────────────
# Benchmark / comparison helpers
# ──────────────────────────────────────────────────────────────────────────

MEDALS = {0: '🥇', 1: '🥈', 2: '🥉'}


def medal(rank: int) -> str:
    """Return a medal emoji for a 0-based rank (4th place onwards gets a dot)."""
    return MEDALS.get(rank, '▪️')


def delta_icon(value: float, eps: float = 1e-9) -> str:
    """▲ for an improvement, ▼ for a regression, ▬ for no change."""
    if value > eps:
        return '🔺'
    if value < -eps:
        return '🔻'
    return '▬'


def trend_html(value: float, eps: float = 1e-4) -> str:
    """Inline coloured delta, e.g. ``+0.021`` green or ``-0.013`` red."""
    if value > eps:
        return f'<span style="color:#6EE7B7;font-weight:600;">▲ +{value:.3f}</span>'
    if value < -eps:
        return f'<span style="color:#FCA5A5;font-weight:600;">▼ {value:.3f}</span>'
    return '<span style="color:#93A1B5;font-weight:600;">▬ 0.000</span>'


def winner_card(metric: str, model: str, value: float) -> None:
    """Highlight the best model for a single metric."""
    shown = '—' if value != value else f'{value:.3f}'  # NaN != NaN
    st.markdown(
        f'<div class="aura-stat" style="border-color:#34D399;'
        f'background:rgba(52,211,153,0.06);">'
        f'<div class="aura-stat-label">🏆 Best {metric}</div>'
        f'<div class="aura-stat-value">{shown}</div>'
        f'<div class="aura-stat-help">{model}</div></div>',
        unsafe_allow_html=True,
    )


def model_compare_card(
    title: str,
    metrics: dict[str, float],
    *,
    rank: int = 0,
    is_active: bool = False,
    deltas: dict[str, float] | None = None,
    best_flags: dict[str, bool] | None = None,
) -> None:
    """A side-by-side model card for the benchmark leaderboard.

    ``rank`` drives the medal; ``deltas`` (vs the previous version) render small
    coloured trend lines; ``best_flags`` star the metrics this model wins.
    """
    deltas = deltas or {}
    best_flags = best_flags or {}
    active_pill = (
        '<span class="aura-pill aura-pill-primary" '
        'style="margin-left:6px;">active</span>' if is_active else ''
    )
    rows = []
    for k, v in metrics.items():
        star = ' ⭐' if best_flags.get(k) else ''
        d = deltas.get(k)
        trend = f'  {trend_html(d)}' if d is not None else ''
        rows.append(
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:3px 0;border-bottom:1px solid var(--aura-border);">'
            f'<span style="color:var(--aura-text-muted);">{k}{star}</span>'
            f'<span style="color:var(--aura-text);font-weight:600;">{v:.3f}{trend}</span>'
            f'</div>'
        )
    border = '#34D399' if rank == 0 else 'var(--aura-border)'
    st.markdown(
        f'<div class="aura-card" style="border-color:{border};">'
        f'<h4 style="margin-bottom:0.5rem;">{medal(rank)} {title}{active_pill}</h4>'
        f'{"".join(rows)}</div>',
        unsafe_allow_html=True,
    )
