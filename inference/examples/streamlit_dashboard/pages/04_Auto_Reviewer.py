"""Auto Reviewer page — LLM adjudication for REVIEW-zone predictions."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(_DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_ROOT))

from theme import apply_theme, banner, footer, page_header  # noqa: E402
from utils import (  # noqa: E402
    SAMPLE_EMAILS,
    get_registry,
    load_detector,
)
from inference import (  # noqa: E402
    AutoReviewer,
    AutoReviewSuccess,
    LLMProvider,
)

st.set_page_config(page_title='Auto Reviewer — AURA', layout='wide')
apply_theme()
page_header(
    eyebrow='Augmentation',
    title='Auto Reviewer',
    subtitle='Ask Groq or Google Gemini to adjudicate REVIEW-zone predictions. API keys live only in this session.',
)

# ── Provider config ───────────────────────────────────────────────────────
with st.sidebar:
    st.header('Provider')
    provider_value = st.radio(
        'Provider',
        options=[p.value for p in LLMProvider],
        format_func=str.title,
    )
    provider = LLMProvider(provider_value)
    api_key = st.text_input('API key', type='password',
                            value=st.session_state.get(f'apikey_{provider.value}', ''))
    st.session_state[f'apikey_{provider.value}'] = api_key
    timeout = st.slider('Timeout (s)', 5, 60, 30, 5)
    max_retries = st.slider('Max retries', 0, 3, 2)
    model_name = st.text_input(
        'Model (blank = default)',
        value=st.session_state.get(f'model_{provider.value}', ''),
    )
    st.session_state[f'model_{provider.value}'] = model_name

# ── Email under review ────────────────────────────────────────────────────
st.subheader('Email under review')
sample_names = ['(custom)'] + [s['name'] for s in SAMPLE_EMAILS]
sel = st.selectbox('Pre-loaded samples', options=range(len(sample_names)),
                   format_func=lambda i: sample_names[i])
prefill = SAMPLE_EMAILS[sel - 1] if sel > 0 else {'sender': '', 'subject': '', 'body': ''}
sender = st.text_input('Sender', value=prefill['sender'])
subject = st.text_input('Subject', value=prefill['subject'])
body = st.text_area('Body', value=prefill['body'], height=200)

# ── Optional ML pre-check ─────────────────────────────────────────────────
st.markdown('### Optional: run ML model first')
st.caption(
    'Show why the email lands in the REVIEW zone — `review_if_uncertain` '
    'short-circuits SPAM and NOT_SPAM zones.'
)
run_ml = st.toggle('Run model and use review_if_uncertain', value=True)

prediction = None
engineered_features: dict | None = None
zone = None

if run_ml:
    try:
        detector = load_detector(
            version=None,
            review_low=0.30,
            review_high=0.80,
            use_calibrator=False,
        )
        if sender or subject or body:
            prediction = detector.predict(sender, subject, body)
            engineered_features = prediction.engineered_features
            zone = prediction.confidence_zone.value if prediction.confidence_zone else None
            cols = st.columns(3)
            cols[0].metric('Phish prob', f'{prediction.phishing_probability:.4f}')
            cols[1].metric('Predicted label',
                           'PHISHING' if prediction.predicted_label == 1 else 'LEGITIMATE')
            cols[2].metric('Zone', zone or '—')
    except Exception as e:  # noqa: BLE001
        st.warning(f'Could not run model: {e}')

# ── Run review ────────────────────────────────────────────────────────────
st.markdown('### Send to LLM')
col_a, col_b = st.columns(2)
do_review = col_a.button('review() — always call', type='primary',
                         use_container_width=True, disabled=not api_key)
do_gated = col_b.button('review_if_uncertain() — only if REVIEW zone',
                        use_container_width=True,
                        disabled=not (api_key and prediction is not None))
if not api_key:
    st.info('Enter an API key on the left to enable LLM review.')

if do_review or do_gated:
    try:
        reviewer = AutoReviewer(
            provider, api_key,
            model_name=model_name or None,
            timeout_seconds=timeout,
            max_retries=max_retries,
        )
    except Exception as e:  # noqa: BLE001
        st.error(f'Failed to construct AutoReviewer: {e}')
        st.stop()

    with st.spinner(f'Calling {provider.value}…'):
        if do_gated:
            response = reviewer.review_if_uncertain(prediction, sender, subject, body)
            if response is None:
                st.warning(
                    f'Skipped — prediction is in zone "{zone}", not REVIEW. '
                    'Use the always-call button to force a review.'
                )
                st.stop()
        else:
            response = reviewer.review(
                sender, subject, body, engineered_features=engineered_features,
            )

    st.markdown('### Response')
    if isinstance(response, AutoReviewSuccess):
        tone = {
            'PHISHING': 'danger',
            'LEGITIMATE': 'success',
            'UNCERTAIN': 'warning',
        }.get(response.review_label.value, 'neutral')
        banner(
            title=f'{response.review_label.value} — confidence: {response.confidence}',
            body=(
                f'{response.reasoning}<br><span style="color:#64748B;">'
                f'provider: <code>{response.provider.value}</code> · '
                f'model: <code>{response.model_name}</code></span>'
            ),
            tone=tone,
        )
        with st.expander('Raw response payload'):
            st.json(response.to_dict())
    else:
        banner(
            title='Review unavailable',
            body=response.user_message,
            tone='danger',
        )
        with st.expander('Technical detail'):
            st.code(response.technical_error)
            if response.raw_response is not None:
                st.json(response.raw_response)

footer()
