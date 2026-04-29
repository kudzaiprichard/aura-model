"""Tests for AutoReviewer — no live network calls.

The httpx.Client is injected in the constructor, so every test here uses a
MagicMock client that returns fake Response objects.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx
import pytest

from inference import (
    AutoReviewer,
    AutoReviewResult,
    ConfidenceZone,
    LLMProvider,
    PredictionResult,
    ReviewLabel,
)


def _mock_response(status_code: int, json_body: dict | None = None, text: str = '') -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if json_body is not None:
        resp.json.return_value = json_body
    else:
        resp.json.side_effect = ValueError('no json')
    resp.text = text or (json.dumps(json_body) if json_body is not None else '')
    return resp


def _groq_ok_body(label: str = 'PHISHING', confidence: str = 'high',
                  reasoning: str = 'URL mimics a known brand.') -> dict:
    content = json.dumps({
        'label': label,
        'confidence': confidence,
        'reasoning': reasoning,
    })
    return {
        'choices': [
            {'message': {'content': content, 'role': 'assistant'}},
        ],
    }


def _google_ok_body(label: str = 'LEGITIMATE', confidence: str = 'medium',
                    reasoning: str = 'No suspicious signals.') -> dict:
    content = json.dumps({
        'label': label,
        'confidence': confidence,
        'reasoning': reasoning,
    })
    return {
        'candidates': [
            {'content': {'parts': [{'text': content}]}},
        ],
    }


def _mock_client(responses) -> MagicMock:
    """Build a mock client whose post() returns the given sequence of responses."""
    client = MagicMock(spec=httpx.Client)
    if not isinstance(responses, list):
        responses = [responses]
    client.post.side_effect = responses
    return client


# -- construction --------------------------------------------------------


def test_defaults_groq_model():
    r = AutoReviewer(LLMProvider.GROQ, 'secret', http_client=_mock_client([]))
    assert r.model_name == 'llama-3.3-70b-versatile'


def test_defaults_google_model():
    r = AutoReviewer(LLMProvider.GOOGLE, 'secret', http_client=_mock_client([]))
    assert r.model_name == 'gemini-2.0-flash'


def test_constructor_rejects_empty_api_key():
    with pytest.raises(ValueError):
        AutoReviewer(LLMProvider.GROQ, '')


def test_constructor_rejects_non_enum_provider():
    with pytest.raises(TypeError):
        AutoReviewer('groq', 'secret')  # type: ignore[arg-type]


# -- happy paths ---------------------------------------------------------


def test_groq_happy_path_returns_phishing():
    client = _mock_client(_mock_response(200, _groq_ok_body()))
    r = AutoReviewer(LLMProvider.GROQ, 'key', http_client=client)
    result = r.review('alice@bank.com', 'Verify now',
                      'Click https://bank-verify.example to confirm')
    assert isinstance(result, AutoReviewResult)
    assert result.review_label == ReviewLabel.PHISHING
    assert result.confidence == 'high'
    assert 'URL' in result.reasoning
    assert result.error is None
    assert result.provider == LLMProvider.GROQ
    assert result.model_name == 'llama-3.3-70b-versatile'
    # Groq endpoint + bearer header sanity check.
    call = client.post.call_args
    assert call.args[0] == 'https://api.groq.com/openai/v1/chat/completions'
    assert call.kwargs['headers']['Authorization'] == 'Bearer key'


def test_google_happy_path_returns_legitimate():
    client = _mock_client(_mock_response(200, _google_ok_body()))
    r = AutoReviewer(LLMProvider.GOOGLE, 'key', http_client=client)
    result = r.review('alice@example.com', 'Lunch?', 'Free at noon?')
    assert result.review_label == ReviewLabel.LEGITIMATE
    assert result.confidence == 'medium'
    assert result.error is None
    assert result.provider == LLMProvider.GOOGLE
    # Google endpoint contains the model path, and the key goes on the query string.
    call = client.post.call_args
    assert 'generativelanguage.googleapis.com' in call.args[0]
    assert call.kwargs['params'] == {'key': 'key'}


def test_prompt_includes_supporting_signals():
    client = _mock_client(_mock_response(200, _groq_ok_body()))
    r = AutoReviewer(LLMProvider.GROQ, 'key', http_client=client, max_retries=0)
    r.review(
        'alice@example.com', 'Hi', 'Body',
        engineered_features={'body_url_count': 3, 'body_url_density': 0.4,
                             'name_email_consistency': 0.0, 'domain_entropy': 2.1},
    )
    prompt = client.post.call_args.kwargs['json']['messages'][0]['content']
    assert 'body_url_count' in prompt
    assert 'Supporting signals' in prompt


# -- error paths: HTTP status codes --------------------------------------


def test_http_429_returns_uncertain_with_error():
    # 429 is retryable per the server contract, but a client can also choose
    # to surface it; our policy is: 5xx is retryable, 4xx surfaces as an error.
    client = _mock_client(_mock_response(429, json_body={'error': 'rate limited'}, text='rate limited'))
    r = AutoReviewer(LLMProvider.GROQ, 'key', http_client=client, max_retries=0)
    result = r.review('a@b.c', 's', 'b')
    assert result.review_label == ReviewLabel.UNCERTAIN
    assert result.error is not None
    assert '429' in result.error


def test_http_500_returns_uncertain_after_retries_exhausted():
    # 5xx is retryable: with max_retries=1 we expect 2 total attempts, both 500.
    client = _mock_client([
        _mock_response(500, text='boom'),
        _mock_response(500, text='boom'),
    ])
    r = AutoReviewer(LLMProvider.GROQ, 'key', http_client=client, max_retries=1)
    result = r.review('a@b.c', 's', 'b')
    assert result.review_label == ReviewLabel.UNCERTAIN
    assert result.error is not None
    assert '500' in result.error
    assert client.post.call_count == 2


def test_timeout_returns_uncertain():
    client = MagicMock(spec=httpx.Client)
    client.post.side_effect = httpx.TimeoutException('timeout')
    r = AutoReviewer(LLMProvider.GROQ, 'key', http_client=client, max_retries=0)
    result = r.review('a@b.c', 's', 'b')
    assert result.review_label == ReviewLabel.UNCERTAIN
    assert 'timeout' in (result.error or '').lower()


def test_transport_error_retries_then_fails():
    client = MagicMock(spec=httpx.Client)
    client.post.side_effect = [
        httpx.TimeoutException('t1'),
        httpx.TimeoutException('t2'),
    ]
    r = AutoReviewer(LLMProvider.GROQ, 'key', http_client=client, max_retries=1)
    result = r.review('a@b.c', 's', 'b')
    assert result.review_label == ReviewLabel.UNCERTAIN
    assert client.post.call_count == 2


# -- error paths: malformed content --------------------------------------


def test_content_is_not_json_returns_uncertain():
    # HTTP 200 but the LLM wrote prose instead of JSON.
    bad_body = {
        'choices': [{'message': {'content': 'Here is my analysis: the email is bad.'}}],
    }
    client = _mock_client(_mock_response(200, bad_body))
    r = AutoReviewer(LLMProvider.GROQ, 'key', http_client=client, max_retries=0)
    result = r.review('a@b.c', 's', 'b')
    assert result.review_label == ReviewLabel.UNCERTAIN
    assert result.error is not None
    assert 'json' in result.error.lower()


def test_content_missing_label_returns_uncertain():
    # Valid JSON but the label field is absent — counts as malformed.
    content = json.dumps({'confidence': 'high', 'reasoning': 'sketchy'})
    body = {'choices': [{'message': {'content': content}}]}
    client = _mock_client(_mock_response(200, body))
    r = AutoReviewer(LLMProvider.GROQ, 'key', http_client=client, max_retries=0)
    result = r.review('a@b.c', 's', 'b')
    assert result.review_label == ReviewLabel.UNCERTAIN
    assert result.error is not None
    assert 'label' in result.error.lower() or 'field' in result.error.lower()


def test_content_unrecognised_label_returns_uncertain():
    content = json.dumps({'label': 'SPAM', 'confidence': 'high', 'reasoning': 'x'})
    body = {'choices': [{'message': {'content': content}}]}
    client = _mock_client(_mock_response(200, body))
    r = AutoReviewer(LLMProvider.GROQ, 'key', http_client=client, max_retries=0)
    result = r.review('a@b.c', 's', 'b')
    assert result.review_label == ReviewLabel.UNCERTAIN
    assert result.error is not None


def test_provider_response_shape_wrong_returns_uncertain():
    # 200 with JSON, but the shape doesn't match the provider's contract.
    client = _mock_client(_mock_response(200, {'unexpected': 'shape'}))
    r = AutoReviewer(LLMProvider.GROQ, 'key', http_client=client, max_retries=0)
    result = r.review('a@b.c', 's', 'b')
    assert result.review_label == ReviewLabel.UNCERTAIN
    assert result.error is not None


# -- review_if_uncertain gating -----------------------------------------


def _prediction_with_zone(zone: ConfidenceZone | None) -> PredictionResult:
    return PredictionResult(
        predicted_label=0,
        phishing_probability=0.5,
        legitimate_probability=0.5,
        threshold=0.75,
        confidence_zone=zone,
        review_low_threshold=0.3,
        review_high_threshold=0.8,
    )


def test_review_if_uncertain_skips_spam_zone():
    client = _mock_client([])  # would error if called
    r = AutoReviewer(LLMProvider.GROQ, 'key', http_client=client)
    out = r.review_if_uncertain(
        _prediction_with_zone(ConfidenceZone.SPAM), 'a@b.c', 's', 'b',
    )
    assert out is None
    client.post.assert_not_called()


def test_review_if_uncertain_skips_not_spam_zone():
    client = _mock_client([])
    r = AutoReviewer(LLMProvider.GROQ, 'key', http_client=client)
    out = r.review_if_uncertain(
        _prediction_with_zone(ConfidenceZone.NOT_SPAM), 'a@b.c', 's', 'b',
    )
    assert out is None
    client.post.assert_not_called()


def test_review_if_uncertain_skips_unset_zone():
    client = _mock_client([])
    r = AutoReviewer(LLMProvider.GROQ, 'key', http_client=client)
    out = r.review_if_uncertain(
        _prediction_with_zone(None), 'a@b.c', 's', 'b',
    )
    assert out is None
    client.post.assert_not_called()


def test_review_if_uncertain_calls_provider_for_review_zone():
    client = _mock_client(_mock_response(200, _groq_ok_body(label='PHISHING')))
    r = AutoReviewer(LLMProvider.GROQ, 'key', http_client=client, max_retries=0)
    out = r.review_if_uncertain(
        _prediction_with_zone(ConfidenceZone.REVIEW), 'a@b.c', 's', 'b',
    )
    assert isinstance(out, AutoReviewResult)
    assert out.review_label == ReviewLabel.PHISHING
    client.post.assert_called_once()


# -- DTO serialisation ---------------------------------------------------


def test_to_dict_serialises_enums_as_strings():
    result = AutoReviewResult(
        review_label=ReviewLabel.PHISHING,
        reasoning='r',
        confidence='high',
        provider=LLMProvider.GROQ,
        model_name='m',
    )
    d = result.to_dict()
    assert d['review_label'] == 'PHISHING'
    assert d['provider'] == 'groq'
    # Must survive json.dumps round-trip.
    reloaded = json.loads(json.dumps(d))
    assert reloaded['review_label'] == 'PHISHING'
    assert reloaded['provider'] == 'groq'
