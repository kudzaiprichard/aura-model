"""Tests for DriftMonitor."""

from __future__ import annotations

import json
import threading
import uuid

import pytest

from inference import DriftMonitor, DriftSignal, DriftStatus


def _uid() -> str:
    return str(uuid.uuid4())


# -- confusion matrix ----------------------------------------------------


def test_true_positive_increments(tmp_path):
    mon = DriftMonitor(tmp_path / 'drift.jsonl')
    pid = _uid()
    mon.record_prediction(pid, predicted_label=1, predicted_probability=0.9, model_version='v1_0')
    mon.record_confirmation(pid, confirmed_label=1)
    assert mon.confusion_matrix() == {'tp': 1, 'tn': 0, 'fp': 0, 'fn': 0}


def test_true_negative_increments(tmp_path):
    mon = DriftMonitor(tmp_path / 'drift.jsonl')
    pid = _uid()
    mon.record_prediction(pid, predicted_label=0, predicted_probability=0.1, model_version='v1_0')
    mon.record_confirmation(pid, confirmed_label=0)
    assert mon.confusion_matrix() == {'tp': 0, 'tn': 1, 'fp': 0, 'fn': 0}


def test_false_positive_increments(tmp_path):
    mon = DriftMonitor(tmp_path / 'drift.jsonl')
    pid = _uid()
    mon.record_prediction(pid, predicted_label=1, predicted_probability=0.9, model_version='v1_0')
    mon.record_confirmation(pid, confirmed_label=0)
    assert mon.confusion_matrix() == {'tp': 0, 'tn': 0, 'fp': 1, 'fn': 0}


def test_false_negative_increments(tmp_path):
    mon = DriftMonitor(tmp_path / 'drift.jsonl')
    pid = _uid()
    mon.record_prediction(pid, predicted_label=0, predicted_probability=0.1, model_version='v1_0')
    mon.record_confirmation(pid, confirmed_label=1)
    assert mon.confusion_matrix() == {'tp': 0, 'tn': 0, 'fp': 0, 'fn': 1}


# -- FPR edge cases ------------------------------------------------------


def test_fpr_zero_when_no_confirmed_negatives(tmp_path):
    mon = DriftMonitor(tmp_path / 'drift.jsonl')
    assert mon.false_positive_rate() == 0.0
    # Even after a TP-only sequence, FP + TN = 0 → still returns 0.0.
    pid = _uid()
    mon.record_prediction(pid, predicted_label=1, predicted_probability=0.9, model_version='v1_0')
    mon.record_confirmation(pid, confirmed_label=1)
    assert mon.false_positive_rate() == 0.0


def test_fpr_computed_correctly(tmp_path):
    mon = DriftMonitor(tmp_path / 'drift.jsonl')
    # Two FPs, three TNs → FPR = 2 / (2+3) = 0.4
    for _ in range(2):
        pid = _uid()
        mon.record_prediction(pid, predicted_label=1, predicted_probability=0.9, model_version='v1')
        mon.record_confirmation(pid, confirmed_label=0)
    for _ in range(3):
        pid = _uid()
        mon.record_prediction(pid, predicted_label=0, predicted_probability=0.1, model_version='v1')
        mon.record_confirmation(pid, confirmed_label=0)
    assert mon.false_positive_rate() == pytest.approx(0.4)


# -- drift signal --------------------------------------------------------


def test_drift_signal_ok_below_threshold(tmp_path):
    mon = DriftMonitor(tmp_path / 'drift.jsonl', fpr_threshold=0.5)
    pid = _uid()
    mon.record_prediction(pid, predicted_label=0, predicted_probability=0.1, model_version='v1')
    mon.record_confirmation(pid, confirmed_label=0)
    sig = mon.drift_signal()
    assert isinstance(sig, DriftSignal)
    assert sig.status == DriftStatus.OK
    assert sig.false_positive_rate == 0.0
    assert sig.threshold == 0.5


def test_drift_signal_warns_when_fpr_exceeds_threshold(tmp_path):
    mon = DriftMonitor(tmp_path / 'drift.jsonl', fpr_threshold=0.10)
    # Force FPR = 0.5 > 0.10: 1 FP + 1 TN.
    fp = _uid()
    mon.record_prediction(fp, predicted_label=1, predicted_probability=0.9, model_version='v1')
    mon.record_confirmation(fp, confirmed_label=0)
    tn = _uid()
    mon.record_prediction(tn, predicted_label=0, predicted_probability=0.1, model_version='v1')
    mon.record_confirmation(tn, confirmed_label=0)
    sig = mon.drift_signal()
    assert sig.status == DriftStatus.WARNING
    assert sig.false_positive_rate == pytest.approx(0.5)
    assert sig.total_predictions == 2
    assert sig.confirmed_predictions == 2
    assert 'threshold' in sig.message
    # to_dict() serialises status as the plain string.
    assert sig.to_dict()['status'] == 'WARNING'


# -- JSONL persistence ---------------------------------------------------


def test_jsonl_log_is_written_correctly(tmp_path):
    log_path = tmp_path / 'drift.jsonl'
    mon = DriftMonitor(log_path)
    pid = _uid()
    mon.record_prediction(
        pid, predicted_label=1, predicted_probability=0.87, model_version='v1_0',
    )
    mon.record_confirmation(pid, confirmed_label=0)
    lines = log_path.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 2
    pred = json.loads(lines[0])
    conf = json.loads(lines[1])
    assert pred['type'] == 'prediction'
    assert pred['prediction_id'] == pid
    assert pred['predicted_label'] == 1
    assert pred['predicted_probability'] == 0.87
    assert pred['model_version'] == 'v1_0'
    assert 'timestamp' in pred
    assert conf['type'] == 'confirmation'
    assert conf['prediction_id'] == pid
    assert conf['confirmed_label'] == 0
    assert 'timestamp' in conf


def test_reconstructs_state_from_existing_log(tmp_path):
    log_path = tmp_path / 'drift.jsonl'
    mon1 = DriftMonitor(log_path)
    for _ in range(3):
        pid = _uid()
        mon1.record_prediction(pid, predicted_label=1, predicted_probability=0.9, model_version='v1')
        mon1.record_confirmation(pid, confirmed_label=0)  # all FPs
    tn_id = _uid()
    mon1.record_prediction(tn_id, predicted_label=0, predicted_probability=0.05, model_version='v1')
    mon1.record_confirmation(tn_id, confirmed_label=0)

    # Simulate a restart: new monitor reads the same log and must rebuild state.
    mon2 = DriftMonitor(log_path)
    assert mon2.confusion_matrix() == mon1.confusion_matrix()
    assert mon2.false_positive_rate() == mon1.false_positive_rate()
    assert mon2.drift_signal().total_predictions == mon1.drift_signal().total_predictions


def test_reconstruct_respects_pending_predictions(tmp_path):
    # A prediction recorded but never confirmed must still be counted in
    # total_predictions after replay.
    log_path = tmp_path / 'drift.jsonl'
    mon1 = DriftMonitor(log_path)
    pending_id = _uid()
    mon1.record_prediction(pending_id, predicted_label=1, predicted_probability=0.9, model_version='v1')
    mon2 = DriftMonitor(log_path)
    assert mon2.drift_signal().total_predictions == 1
    assert mon2.drift_signal().confirmed_predictions == 0
    # Confirming after the restart still lands in the matrix correctly.
    mon2.record_confirmation(pending_id, confirmed_label=0)
    assert mon2.confusion_matrix()['fp'] == 1


# -- error paths ---------------------------------------------------------


def test_confirmation_with_unknown_id_raises(tmp_path):
    mon = DriftMonitor(tmp_path / 'drift.jsonl')
    with pytest.raises(ValueError):
        mon.record_confirmation('no-such-id', confirmed_label=1)


def test_duplicate_confirmation_raises(tmp_path):
    mon = DriftMonitor(tmp_path / 'drift.jsonl')
    pid = _uid()
    mon.record_prediction(pid, predicted_label=1, predicted_probability=0.9, model_version='v1')
    mon.record_confirmation(pid, confirmed_label=1)
    with pytest.raises(ValueError):
        mon.record_confirmation(pid, confirmed_label=1)


def test_invalid_labels_rejected(tmp_path):
    mon = DriftMonitor(tmp_path / 'drift.jsonl')
    with pytest.raises(ValueError):
        mon.record_prediction(_uid(), predicted_label=2, predicted_probability=0.5, model_version='v1')
    pid = _uid()
    mon.record_prediction(pid, predicted_label=1, predicted_probability=0.9, model_version='v1')
    with pytest.raises(ValueError):
        mon.record_confirmation(pid, confirmed_label=5)


def test_fpr_threshold_out_of_range_rejected(tmp_path):
    with pytest.raises(ValueError):
        DriftMonitor(tmp_path / 'drift.jsonl', fpr_threshold=1.5)
    with pytest.raises(ValueError):
        DriftMonitor(tmp_path / 'drift.jsonl', fpr_threshold=-0.1)


# -- concurrent writes ---------------------------------------------------


def test_concurrent_writes_do_not_corrupt_log(tmp_path):
    log_path = tmp_path / 'drift.jsonl'
    # Two independent monitors sharing one log — each thread writes N records.
    N = 40

    def writer(label: int) -> None:
        mon = DriftMonitor(log_path)
        for _ in range(N):
            mon.record_prediction(
                _uid(),
                predicted_label=label,
                predicted_probability=0.9 if label == 1 else 0.1,
                model_version='v1',
            )

    t1 = threading.Thread(target=writer, args=(1,))
    t2 = threading.Thread(target=writer, args=(0,))
    t1.start(); t2.start()
    t1.join(); t2.join()

    lines = log_path.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 2 * N
    # Every line must be a complete, parseable JSON record.
    for line in lines:
        record = json.loads(line)
        assert record['type'] == 'prediction'
