"""Regression guard against the 0.7650 stair-step collapse.

When the saved calibrator was an `sklearn.isotonic.IsotonicRegression` fitted on
the MLP's bimodal output, it collapsed every raw probability in
`[0.9557, 0.9951]` to exactly `0.765000`, so structurally different emails
came back with identical calibrated phishing probabilities. The fix swapped in
a strictly-monotonic `betacal.BetaCalibration`; see `fix.md` for the full
write-up. This test is the lasting guard against regressing into that class of
bug: for every pair of fixture emails, whenever their **raw** phishing
probabilities differ by at least `1e-3`, their **calibrated** probabilities
must differ by at least `1e-4`.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import pytest

from inference import PhishingDetector

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_ROOT = REPO_ROOT / 'models'

# Fixture lifted verbatim from demo_predict.ipynb §7 — the three emails that
# collided at 0.7650 under the old isotonic calibrator, plus a clearly distinct
# legitimate email to exercise the low-probability band. Keep this list small;
# it is the regression fixture, not a smoke test.
_FIXTURE = [
    ('MOM',
        '"Mom" <mom@familymail.net>',
        'Recipe for that soup you liked',
        'Hi sweetie, here is the lentil soup recipe I promised. Soak the '
        'lentils overnight, then simmer with carrots and celery for an hour.'),
    ('GITHUB',
        '"GitHub" <noreply@github.com>',
        'Your weekly digest: 5 new repositories trending',
        'Here are the repositories trending this week in your languages. '
        'Visit github.com/trending to see the full list.'),
    ('IT_HELPDESK',
        '"IT Helpdesk" <helpdesk@company-support.co>',
        'Please review the attached document',
        'Hi, we are rolling out a new policy. You can review the draft at '
        'http://company-support.co/policy-draft and let us know if anything '
        'looks off. No action required today.'),
    ('JANE_LUNCH',
        '"Jane Doe" <jane.doe@gmail.com>',
        'Lunch on Saturday?',
        'Hey, are you free for lunch Saturday around noon? Thinking of that '
        'ramen place on 5th. Let me know.'),
]

_RAW_DELTA_TRIGGER = 1e-3
_CAL_DELTA_FLOOR = 1e-4


@pytest.fixture(scope='module')
def detector():
    if not MODELS_ROOT.exists():
        pytest.skip('models/ directory not present')
    det = PhishingDetector.load_production(MODELS_ROOT)
    if det.calibrator is None:
        pytest.skip('no calibrator configured on the production detector')
    return det


def test_calibrated_outputs_distinct_when_raw_outputs_are(detector):
    results = [
        (tag, detector.predict(sender, subject, body))
        for tag, sender, subject, body in _FIXTURE
    ]

    # Sanity: the fixture must contain at least one pair whose raw probabilities
    # differ by enough to trigger the assertion below, otherwise the test would
    # pass vacuously and stop guarding anything.
    triggered = [
        (tag_a, tag_b)
        for (tag_a, r_a), (tag_b, r_b) in combinations(results, 2)
        if abs(r_a.raw_phishing_probability - r_b.raw_phishing_probability)
        >= _RAW_DELTA_TRIGGER
    ]
    assert triggered, (
        'regression fixture does not produce any pair with raw_delta '
        f'>= {_RAW_DELTA_TRIGGER}; the test would pass vacuously — '
        'add a pair with clearly different raw probabilities.'
    )

    violations = []
    for (tag_a, r_a), (tag_b, r_b) in combinations(results, 2):
        raw_delta = abs(r_a.raw_phishing_probability - r_b.raw_phishing_probability)
        cal_delta = abs(r_a.phishing_probability - r_b.phishing_probability)
        if raw_delta >= _RAW_DELTA_TRIGGER and cal_delta < _CAL_DELTA_FLOOR:
            violations.append(
                f'{tag_a} vs {tag_b}: raw_delta={raw_delta:.6f} '
                f'(>= {_RAW_DELTA_TRIGGER}) but cal_delta={cal_delta:.6f} '
                f'(< {_CAL_DELTA_FLOOR}) — stair-step collapse'
            )

    assert not violations, (
        'calibrator is collapsing distinct raw probabilities onto identical '
        'calibrated outputs (the 0.7650 bug class):\n'
        + '\n'.join(violations)
    )
