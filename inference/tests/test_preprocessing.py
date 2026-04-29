"""Unit tests for preprocessing primitives not covered by the parity fixture."""

from __future__ import annotations

import numpy as np
import pytest

from inference.preprocessing import (
    clean_encoding,
    extract_engineered_features,
    normalize_for_tfidf,
)
from inference.schema import ENGINEERED_FEATURE_ORDER


class TestCleanEncoding:
    def test_replaces_nbsp(self):
        assert clean_encoding('hello&nbsp;world') == 'hello world'

    def test_decodes_entities(self):
        assert clean_encoding('a &lt;b&gt; &amp; &quot;c&quot;') == 'a <b> & "c"'

    def test_strips_replacement_char_and_null(self):
        assert clean_encoding('hi\ufffdthere\x00!') == 'hi there!'

    def test_preserves_html_tags(self):
        # §1.B only decodes entities; <b> is left alone.
        assert clean_encoding('<b>hi</b>&nbsp;world') == '<b>hi</b> world'

    def test_empty_and_none(self):
        assert clean_encoding('') == ''
        assert clean_encoding(None) == ''


class TestNormalizeForTfidf:
    def test_removes_urls_and_punct(self):
        assert normalize_for_tfidf('Visit https://x.com! NOW') == 'visit now'

    def test_lowercases(self):
        assert normalize_for_tfidf('ABC XYZ') == 'abc xyz'

    def test_collapses_whitespace(self):
        assert normalize_for_tfidf('a    b\tc\nd') == 'a b c d'

    def test_empty(self):
        assert normalize_for_tfidf('') == ''
        assert normalize_for_tfidf(None) == ''


class TestEngineeredFeatures:
    def test_shape_and_order(self):
        v = extract_engineered_features(
            'Alice <alice@example.com>', 'Hi!', 'Hello world'
        )
        assert v.shape == (len(ENGINEERED_FEATURE_ORDER),)
        assert v.dtype == np.float64

    def test_sender_name_present(self):
        v = extract_engineered_features(
            'Alice <alice@example.com>', '', 'x'
        )
        idx = ENGINEERED_FEATURE_ORDER.index('sender_name_exists')
        assert v[idx] == 1.0

    def test_sender_name_absent(self):
        v = extract_engineered_features(
            'alice@example.com', '', 'x'
        )
        idx = ENGINEERED_FEATURE_ORDER.index('sender_name_exists')
        assert v[idx] == 0.0

    def test_domain_entropy_excludes_tld(self):
        # 'example.com' -> main domain 'example' -> entropy(example lowercased)
        v = extract_engineered_features('a@example.com', '', '')
        # compare with an equivalent construction
        ref = extract_engineered_features('a@example.co', '', '')  # main='example'
        idx = ENGINEERED_FEATURE_ORDER.index('domain_entropy')
        assert pytest.approx(v[idx]) == ref[idx]

    def test_body_url_density_is_percent(self):
        v = extract_engineered_features(
            '', '', 'hello world https://x.com bye now'
        )
        # 1 url / 5 words * 100 == 20
        idx = ENGINEERED_FEATURE_ORDER.index('body_url_density')
        assert pytest.approx(v[idx]) == 20.0

    def test_body_avg_word_length(self):
        v = extract_engineered_features('', '', 'ab cde f')
        idx = ENGINEERED_FEATURE_ORDER.index('body_avg_word_length')
        assert pytest.approx(v[idx]) == (2 + 3 + 1) / 3
