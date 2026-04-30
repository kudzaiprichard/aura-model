"""CLI example.

Single-email:
    python -m inference.examples.cli --sender X --subject Y --body Z

Batch (JSONL, one email per line with sender/subject/body):
    python -m inference.examples.cli --batch emails.jsonl

Optional flags bring in calibration, three-zone classification, drift
logging, and LLM auto-review. See --help for the full list.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from inference import (
    AutoReviewer,
    ConfidenceZone,
    DriftMonitor,
    LLMProvider,
    ModelRegistry,
    PhishingDetector,
)
from inference.registry import default_models_root


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog='aura-predict')
    p.add_argument('--sender')
    p.add_argument('--subject')
    p.add_argument('--body')
    p.add_argument('--batch', type=Path, help='Path to JSONL input')
    p.add_argument('--threshold', type=float, default=0.75)
    p.add_argument('--version', help='Specific registered version (default: active)')
    p.add_argument('--models-root', type=Path, default=None,
                   help='Model registry root (default: $AURA_MODELS_DIR or ./models)')
    p.add_argument('--calibrator-path', type=Path, default=None,
                   help='Calibrator pickle; enables calibrated probabilities')
    p.add_argument('--review-low', type=float, default=None,
                   help='Lower REVIEW-zone threshold; requires --review-high')
    p.add_argument('--review-high', type=float, default=None,
                   help='Upper REVIEW-zone threshold; requires --review-low')
    p.add_argument('--drift-log', type=Path, default=None,
                   help='JSONL path for append-only drift monitoring')
    p.add_argument('--review-provider', choices=[p.value for p in LLMProvider],
                   default=None, help='Enable LLM auto-review for REVIEW-zone results')
    p.add_argument('--review-api-key', default=None,
                   help='API key for --review-provider (required when set)')
    return p


def _build_detector(args: argparse.Namespace) -> PhishingDetector:
    root = Path(args.models_root).resolve() if args.models_root else default_models_root()
    registry = ModelRegistry(root)
    version = args.version or registry.active_version() or registry.latest_version()
    if version is None:
        raise FileNotFoundError(f'No versions found under {root}')
    paths = registry.paths_for(version)

    calibrator_path = args.calibrator_path or paths.get('calibrator')

    drift_monitor = DriftMonitor(args.drift_log) if args.drift_log else None

    detector = PhishingDetector.from_paths(
        model_path=paths['model'],
        subject_vectorizer_path=paths['subject_vectorizer'],
        body_vectorizer_path=paths['body_vectorizer'],
        calibrator_path=calibrator_path,
        review_low_threshold=args.review_low,
        review_high_threshold=args.review_high,
        drift_monitor=drift_monitor,
    )
    # `from_paths` doesn't set `version`; expose it for result.model_version.
    detector.version = version
    return detector


def _maybe_auto_review(args: argparse.Namespace, result, sender, subject, body):
    if args.review_provider is None:
        return None
    if args.review_api_key is None:
        raise SystemExit('--review-provider requires --review-api-key')
    if result.confidence_zone != ConfidenceZone.REVIEW:
        return None
    reviewer = AutoReviewer(LLMProvider(args.review_provider), args.review_api_key)
    return reviewer.review_if_uncertain(result, sender, subject, body)


def _print_with_review(result, review) -> None:
    payload = result.to_dict()
    if review is not None:
        payload['auto_review'] = review.to_dict()
    print(json.dumps(payload, indent=2, default=float))


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if (args.review_low is None) ^ (args.review_high is None):
        print('--review-low and --review-high must be provided together', file=sys.stderr)
        return 2
    detector = _build_detector(args)
    if args.batch:
        emails = [
            json.loads(line)
            for line in args.batch.read_text(encoding='utf-8').splitlines()
            if line.strip()
        ]
        results = detector.predict_batch(emails, threshold=args.threshold)
        for email, r in zip(emails, results):
            review = _maybe_auto_review(
                args, r, email['sender'], email['subject'], email['body'],
            )
            payload = r.to_dict()
            if review is not None:
                payload['auto_review'] = review.to_dict()
            print(json.dumps(payload, default=float))
        return 0
    if not (args.sender and args.subject is not None and args.body is not None):
        print('Provide --sender/--subject/--body or --batch', file=sys.stderr)
        return 2
    result = detector.predict(
        args.sender, args.subject, args.body, threshold=args.threshold,
    )
    review = _maybe_auto_review(args, result, args.sender, args.subject, args.body)
    _print_with_review(result, review)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
