"""Parity test — inference preprocessing must reproduce training outputs.

This test is the cornerstone. Every fixture record is a frozen snapshot of
what training produced for a specific email; the implementations in
`inference.preprocessing` must match within numeric tolerance.

Run:
    pytest inference/tests/test_parity.py
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pytest

from inference.preprocessing import (
    build_feature_row,
    extract_engineered_features,
    normalize_for_tfidf,
)
from inference.schema import (
    BODY_TFIDF_DIM,
    ENGINEERED_FEATURE_ORDER,
    SUBJECT_TFIDF_DIM,
    TOTAL_FEATURES,
)

FIXTURE_PATH = Path(__file__).parent / 'fixtures' / 'training_parity.json'
REPO_ROOT = Path(__file__).resolve().parents[2]
SUBJECT_VEC_PATH = REPO_ROOT / 'models' / 'pipeline_components' / 'subject_vectorizer.pkl'
BODY_VEC_PATH = REPO_ROOT / 'models' / 'pipeline_components' / 'body_vectorizer.pkl'


@pytest.fixture(scope='module')
def fixture_data():
    if not FIXTURE_PATH.exists():
        pytest.skip(f'Fixture missing: {FIXTURE_PATH}')
    return json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))


@pytest.fixture(scope='module')
def vectorizers():
    if not SUBJECT_VEC_PATH.exists() or not BODY_VEC_PATH.exists():
        pytest.skip('Vectorisers not available on disk')
    return joblib.load(SUBJECT_VEC_PATH), joblib.load(BODY_VEC_PATH)


def test_fixture_metadata(fixture_data):
    meta = fixture_data['metadata']
    assert meta['engineered_feature_order'] == list(ENGINEERED_FEATURE_ORDER)
    assert meta['subject_tfidf_dim'] == SUBJECT_TFIDF_DIM
    assert meta['body_tfidf_dim'] == BODY_TFIDF_DIM
    assert meta['total_features'] == TOTAL_FEATURES
    assert len(fixture_data['records']) >= 20


def test_engineered_features_match(fixture_data):
    failures: list[str] = []
    for rec in fixture_data['records']:
        actual = extract_engineered_features(rec['sender'], rec['subject'], rec['body'])
        for i, name in enumerate(ENGINEERED_FEATURE_ORDER):
            expected = rec['engineered_features'][name]
            if not np.isclose(actual[i], expected, atol=1e-10, rtol=0):
                failures.append(
                    f"id={rec['id']} feature={name} expected={expected!r} "
                    f"actual={actual[i]!r}"
                )
    if failures:
        pytest.fail('Engineered feature drift:\n' + '\n'.join(failures))


def test_tfidf_parity(fixture_data, vectorizers):
    subject_vec, body_vec = vectorizers
    failures: list[str] = []
    for rec in fixture_data['records']:
        normalized_subj = normalize_for_tfidf(rec['subject'])
        normalized_body = normalize_for_tfidf(rec['body'])

        # normalized text should equal what the generator recorded
        assert normalized_subj == rec['normalized']['subject'], (
            f"id={rec['id']}: normalize_for_tfidf disagrees on subject"
        )
        assert normalized_body == rec['normalized']['body'], (
            f"id={rec['id']}: normalize_for_tfidf disagrees on body"
        )

        subj_sparse = subject_vec.transform([normalized_subj])
        body_sparse = body_vec.transform([normalized_body])

        actual_subj = sorted(
            zip(subj_sparse.indices.tolist(), subj_sparse.data.tolist()),
            key=lambda p: p[0],
        )
        expected_subj = sorted(
            [(int(i), float(v)) for i, v in rec['subject_tfidf_nonzero']],
            key=lambda p: p[0],
        )
        if len(actual_subj) != len(expected_subj):
            failures.append(
                f"id={rec['id']} subject nonzero count differs: "
                f"{len(actual_subj)} vs {len(expected_subj)}"
            )
            continue
        for (ai, av), (ei, ev) in zip(actual_subj, expected_subj):
            if ai != ei or not np.isclose(av, ev, atol=1e-8, rtol=0):
                failures.append(
                    f"id={rec['id']} subject tfidf mismatch: "
                    f"actual=({ai},{av}) expected=({ei},{ev})"
                )

        actual_body = sorted(
            zip(body_sparse.indices.tolist(), body_sparse.data.tolist()),
            key=lambda p: p[0],
        )
        expected_body = sorted(
            [(int(i), float(v)) for i, v in rec['body_tfidf_nonzero']],
            key=lambda p: p[0],
        )
        if len(actual_body) != len(expected_body):
            failures.append(
                f"id={rec['id']} body nonzero count differs: "
                f"{len(actual_body)} vs {len(expected_body)}"
            )
            continue
        for (ai, av), (ei, ev) in zip(actual_body, expected_body):
            if ai != ei or not np.isclose(av, ev, atol=1e-8, rtol=0):
                failures.append(
                    f"id={rec['id']} body tfidf mismatch: "
                    f"actual=({ai},{av}) expected=({ei},{ev})"
                )

    if failures:
        pytest.fail('TF-IDF drift:\n' + '\n'.join(failures))


def test_build_feature_row_shape(fixture_data, vectorizers):
    subject_vec, body_vec = vectorizers
    for rec in fixture_data['records'][:3]:
        row = build_feature_row(
            rec['sender'], rec['subject'], rec['body'], subject_vec, body_vec
        )
        assert row.shape == (1, TOTAL_FEATURES), (
            f"id={rec['id']} shape={row.shape}"
        )
