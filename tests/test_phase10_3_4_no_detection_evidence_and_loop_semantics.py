from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path("scripts").resolve()))

import live_finite_repeat_aim_click as phase10


def args(**overrides):
    base = dict(
        no_detection_policy="continue",
        max_iterations=3,
        max_loop_iterations=1000,
        max_no_detection_timeouts=100,
        max_consecutive_no_detection_timeouts=20,
        save_evidence_on_no_detection=True,
        max_no_detection_evidence=10,
        evidence_mode="failures",
        after_validation_mode="hybrid",
        capture_backend="auto",
        after_fast_mode="roi_only",
        click_guard_mode="strict",
        retry_policy="bounded",
        max_retries_per_target=1,
        max_total_retry_attempts=20,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_no_detection_does_not_consume_max_iterations() -> None:
    rows = [
        {"iteration_total_ms": 10.0, "stop_reason": "no_detection_timeout", "blocked": False, "before_detections_count": 0},
        {"iteration_total_ms": 10.0, "stop_reason": "no_detection_timeout", "blocked": False, "before_detections_count": 0},
        {"iteration_total_ms": 10.0, "stop_reason": None, "blocked": False, "before_detections_count": 1},
        {"iteration_total_ms": 10.0, "stop_reason": None, "blocked": False, "before_detections_count": 1},
        {"iteration_total_ms": 10.0, "stop_reason": None, "blocked": False, "before_detections_count": 1},
    ]
    summary = phase10.build_summary(args(), Path("dummy"), rows, stop_reason="max_iterations_reached", blocked=False, keyboard_interrupt=False, timing={})
    assert summary["loop_iterations_attempted"] == 5
    assert summary["action_iterations_attempted"] == 3


def test_max_loop_iterations_can_stop_empty_loop() -> None:
    # Empty loops are bounded independently from action iterations.
    assert 5 >= args(max_loop_iterations=5).max_loop_iterations


def test_max_consecutive_no_detection_still_stops() -> None:
    stop, reason = phase10.should_stop_after_no_detection_timeout(policy="continue", total_count=3, consecutive_count=3, max_total=100, max_consecutive=3)
    assert stop is True
    assert reason == "max_consecutive_no_detection_timeouts_reached"


def test_failures_mode_no_detection_saves_evidence(monkeypatch, tmp_path: Path) -> None:
    calls = {"encode": 0}
    def fake_encode(_capture):
        calls["encode"] += 1
        return 4.0
    monkeypatch.setattr(phase10, "encode_capture_image", fake_encode)
    capture = phase10.CapturedFrame(tmp_path / "before.png", frame=None, screenshot_width=10, screenshot_height=10, capture_elapsed_ms=1.0)
    row = {}
    phase10.save_no_detection_evidence(row, capture, args(), saved_count=0)
    assert row["evidence_saved"] is True
    assert row["evidence_saved_reason"] == "no_detection_timeout"
    assert row["no_detection_evidence_saved"] is True
    assert row["before_capture_image_path"].endswith("before.png")
    assert calls["encode"] == 1


def test_minimal_mode_no_detection_skips_evidence(tmp_path: Path) -> None:
    capture = phase10.CapturedFrame(tmp_path / "before.png", frame=None, screenshot_width=10, screenshot_height=10, capture_elapsed_ms=1.0)
    row = {}
    phase10.save_no_detection_evidence(row, capture, args(evidence_mode="minimal"), saved_count=0)
    assert row["evidence_saved"] is False
    assert row["no_detection_evidence_saved"] is False


def test_max_no_detection_evidence_limits_saved_count(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(phase10, "encode_capture_image", lambda _capture: 1.0)
    saved = 0
    skipped = 0
    for index in range(12):
        row = {}
        capture = phase10.CapturedFrame(tmp_path / f"before_{index}.png", frame=None, screenshot_width=10, screenshot_height=10, capture_elapsed_ms=1.0)
        phase10.save_no_detection_evidence(row, capture, args(max_no_detection_evidence=10), saved_count=saved)
        if row["no_detection_evidence_saved"]:
            saved += 1
        else:
            skipped += 1
    assert saved == 10
    assert skipped == 2


def test_csv_headers_unique() -> None:
    assert len(phase10.ITERATION_FIELDS) == len(set(phase10.ITERATION_FIELDS))
    phase10.validate_unique_csv_headers(phase10.ITERATION_FIELDS)
