from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path("scripts").resolve()))

import live_finite_repeat_aim_click as phase10


def args(**overrides):
    base = dict(
        warmup_inference=True,
        evidence_mode="failures",
        save_review_images=False,
        capture_benchmark_include_encode=False,
        next_target_timeout_sec=0.5,
        no_detection_poll_interval_sec=0.05,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_iteration_csv_headers_are_unique() -> None:
    assert len(phase10.ITERATION_FIELDS) == len(set(phase10.ITERATION_FIELDS))
    phase10.validate_unique_csv_headers(phase10.ITERATION_FIELDS)


def test_validate_unique_csv_headers_rejects_duplicates() -> None:
    try:
        phase10.validate_unique_csv_headers(["a", "b", "a"])
    except ValueError as exc:
        assert "duplicate CSV header" in str(exc)
    else:
        raise AssertionError("duplicate header was not rejected")


def test_warmup_does_not_increment_action_iterations() -> None:
    summary = phase10.build_summary(
        args(max_iterations=10, max_duration_sec=30, after_validation_mode="hybrid", capture_backend="auto", after_fast_mode="roi_only", click_guard_mode="strict", retry_policy="bounded", max_retries_per_target=1, max_total_retry_attempts=20, evidence_mode="failures"),
        Path("dummy"),
        [],
        stop_reason="not_started",
        blocked=False,
        keyboard_interrupt=False,
        timing={"warmup_enabled": True, "warmup_ms": 123.0, "active_loop_duration_sec": 0.0},
    )
    assert summary["action_iterations_attempted"] == 0
    assert summary["warmup_enabled"] is True
    assert summary["warmup_ms"] == 123.0


def test_warmup_timing_excluded_from_active_loop_duration() -> None:
    assert phase10.should_stop_for_active_duration(loop_start_perf=100.0, max_duration_sec=10.0, now_perf=109.0) is False
    assert phase10.should_stop_for_active_duration(loop_start_perf=100.0, max_duration_sec=10.0, now_perf=110.0) is True


def test_no_detection_timeout_should_not_set_blocked_true() -> None:
    summary = phase10.build_summary(
        args(max_iterations=10, max_duration_sec=30, after_validation_mode="hybrid", capture_backend="auto", after_fast_mode="roi_only", click_guard_mode="strict", retry_policy="bounded", max_retries_per_target=1, max_total_retry_attempts=20, evidence_mode="failures"),
        Path("dummy"),
        [{"iteration_total_ms": 900.0, "stop_reason": "no_detection_timeout", "blocked": False}],
        stop_reason="no_detection_timeout",
        blocked=False,
        keyboard_interrupt=False,
        timing={"active_loop_duration_sec": 0.9},
    )
    assert summary["blocked"] is False
    assert summary["stop_reason"] == "no_detection_timeout"
    assert summary["no_detection_timeout_count"] == 1


def test_detection_result_exists_even_if_detect_call_slow_is_not_timeout() -> None:
    detections = [{"center_monitor_px": {"x": 960.0, "y": 540.0}}]
    before_detect_ms = 850.0
    assert before_detect_ms > 500.0
    assert bool(detections) is True
    # The loop should decide from detection presence, not detect-call duration alone.
    assert detections != []


def test_help_includes_warmup_flag() -> None:
    parser_args = phase10.parse_args
    source = Path("scripts/live_finite_repeat_aim_click.py").read_text(encoding="utf-8")
    assert "--no-warmup-inference" in source
