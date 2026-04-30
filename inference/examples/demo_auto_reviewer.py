"""Live demo of AutoReviewer against Groq and Google Gemini.

Run:
    python -m inference.examples.demo_auto_reviewer

Set one or both API keys below (or via environment variables
GROQ_API_KEY / GOOGLE_API_KEY). Providers with a missing key are
skipped with a clear notice; providers with a key are exercised
against the live API.

Exercises per configured provider:
  - `review()` happy path on a phishing-looking email
  - `review()` happy path on a clearly legitimate email
  - `review_if_uncertain()` gating (REVIEW vs SPAM/NOT_SPAM)
"""

from __future__ import annotations

import os

from inference import (
    AutoReviewer,
    AutoReviewFailure,
    AutoReviewSuccess,
    ConfidenceZone,
    LLMProvider,
    PredictionResult,
)

# ── API keys ───────────────────────────────────────────────────────────────
# Paste keys here, or leave blank and set GROQ_API_KEY / GOOGLE_API_KEY
# in the environment. A blank key means "skip this provider".
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')
# ──────────────────────────────────────────────────────────────────────────


# Sample emails reused across providers so results are directly comparable.
_PHISHING_EMAIL = {
    'sender': '"PayPal Security" <service@paypa1-alerts.com>',
    'subject': 'URGENT: verify your account',
    'body': (
        'Dear customer, unusual activity was detected on your account. '
        'Click http://paypa1-alerts.com/verify within 24 hours to avoid '
        'permanent suspension. Failure to act will result in account closure.'
    ),
    'features': {
        'body_url_count': 1,
        'body_url_density': 12.5,
        'name_email_consistency': 0.0,
        'domain_entropy': 3.4,
    },
}

_LEGITIMATE_EMAIL = {
    'sender': '"GitHub" <noreply@github.com>',
    'subject': '[repo] Pull request #482 merged',
    'body': (
        'Your pull request "Add retry logic to ingest pipeline" has been '
        'merged into main by alice. You can view the commit on github.com.'
    ),
    'features': {
        'body_url_count': 0,
        'body_url_density': 0.0,
        'name_email_consistency': 1.0,
        'domain_entropy': 2.1,
    },
}


def _banner(title: str) -> None:
    print('\n' + '=' * 72)
    print(title)
    print('=' * 72)


def _print_response(label: str, response) -> None:
    """Pretty-print either an AutoReviewSuccess or AutoReviewFailure."""
    print(f'\n  [{label}]')
    if isinstance(response, AutoReviewSuccess):
        print(f'    outcome      : success')
        print(f'    review_label : {response.review_label.value}')
        print(f'    confidence   : {response.confidence}')
        print(f'    provider     : {response.provider.value}')
        print(f'    model_name   : {response.model_name}')
        print(f'    reasoning    : {response.reasoning}')
    else:  # AutoReviewFailure
        print(f'    outcome      : failure')
        print(f'    provider     : {response.provider.value}')
        print(f'    model_name   : {response.model_name}')
        print(f'    user_message : {response.user_message}')
        print(f'    tech_error   : {response.technical_error}')


def _fake_prediction(zone: ConfidenceZone) -> PredictionResult:
    return PredictionResult(
        predicted_label=1 if zone == ConfidenceZone.SPAM else 0,
        phishing_probability=0.5,
        legitimate_probability=0.5,
        threshold=0.75,
        confidence_zone=zone,
        review_low_threshold=0.3,
        review_high_threshold=0.8,
    )


def _summarise(response) -> str:
    """One-line summary used in the gating table."""
    if response is None:
        return 'None (skipped)'
    if isinstance(response, AutoReviewSuccess):
        return response.review_label.value
    return f'FAILURE ({response.user_message})'


def run_provider(provider: LLMProvider, api_key: str) -> None:
    name = provider.value
    _banner(f'Provider: {name}')

    if not api_key:
        print(f'  SKIPPED — no API key configured for {name}.')
        print(f'  Set the key in the script or export '
              f'{"GROQ_API_KEY" if provider == LLMProvider.GROQ else "GOOGLE_API_KEY"}.')
        return

    try:
        reviewer = AutoReviewer(provider, api_key)
    except Exception as e:  # construction-level validation errors
        print(f'  FAILED to construct AutoReviewer: {e}')
        return

    # 1. Phishing-looking email
    response = reviewer.review(
        sender=_PHISHING_EMAIL['sender'],
        subject=_PHISHING_EMAIL['subject'],
        body=_PHISHING_EMAIL['body'],
        engineered_features=_PHISHING_EMAIL['features'],
    )
    _print_response('phishing-looking email', response)

    # 2. Legitimate email
    response = reviewer.review(
        sender=_LEGITIMATE_EMAIL['sender'],
        subject=_LEGITIMATE_EMAIL['subject'],
        body=_LEGITIMATE_EMAIL['body'],
        engineered_features=_LEGITIMATE_EMAIL['features'],
    )
    _print_response('legitimate email', response)

    # 3. Gating: only REVIEW-zone predictions should trigger a call.
    print('\n  [review_if_uncertain gating]')
    for zone in (ConfidenceZone.SPAM, ConfidenceZone.NOT_SPAM, ConfidenceZone.REVIEW):
        out = reviewer.review_if_uncertain(
            _fake_prediction(zone),
            _PHISHING_EMAIL['sender'],
            _PHISHING_EMAIL['subject'],
            _PHISHING_EMAIL['body'],
        )
        print(f'    zone={zone.value:9s} -> {_summarise(out)}')


def main() -> int:
    _banner('AutoReviewer live demo — Groq + Gemini')

    if not GROQ_API_KEY and not GOOGLE_API_KEY:
        print('\n  No API keys configured for either provider.')
        print('  Set GROQ_API_KEY and/or GOOGLE_API_KEY in the environment,')
        print('  or edit this file, and re-run.')
        return 1

    run_provider(LLMProvider.GROQ, GROQ_API_KEY)
    run_provider(LLMProvider.GOOGLE, GOOGLE_API_KEY)

    _banner('Done.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())