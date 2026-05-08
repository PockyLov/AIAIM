from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path("scripts").resolve()))

import live_finite_repeat_aim_click as phase10


def args(**overrides):
    base = dict(
        evidence_mode="failures",
        save_review_images=False,
        save_evidence_on_fallback_click=False,
        no_detection_policy="continue",
        max_no_detection_timeouts=20,
        max_consecutive_no_detection_timeouts=5,
        after_validation_mode="hybrid",
        capture_backend="auto",
        after_fast_mode="roi_only",
        click_guard_mode="strict",
        retry_policy="bounded",
        max_retries_per_target=1,
        max_total_retry_attempts=20,
        max_iterations=30,
        max_loop_iterations=1000,
        max_duration_sec=30,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_no_detection_continue_policy_does_not_stop_before_limits() -> None:
    stop, reason = phase10.should_stop_after_no_detection_timeout(
        policy="continue", total_count=1, consecutive_count=1, max_total=20, max_consecutive=5
    )
    assert stop is False
    assert reason is None


def test_no_detection_stop_policy_keeps_old_behavior() -> None:
    stop, reason = phase10.should_stop_after_no_detection_timeout(
        policy="stop", total_count=1, consecutive_count=1, max_total=20, max_consecutive=5
    )
    assert stop is True
    assert reason == "no_detection_timeout"


def test_consecutive_no_detection_limit_stops() -> None:
    stop, reason = phase10.should_stop_after_no_detection_timeout(
        policy="continue", total_count=5, consecutive_count=5, max_total=20, max_consecutive=5
    )
    assert stop is True
    assert reason == "max_consecutive_no_detection_timeouts_reached"


def test_total_no_detection_limit_stops() -> None:
    stop, reason = phase10.should_stop_after_no_detection_timeout(
        policy="continue", total_count=20, consecutive_count=1, max_total=20, max_consecutive=5
    )
    assert stop is True
    assert reason == "max_no_detection_timeouts_reached"


def test_fallback_click_default_does_not_save_evidence() -> None:
    row = {
        "click_executed": True,
        "retry_scheduled": False,
        "blocked": False,
        "stop_reason": None,
        "fallback_click_evidence_saved": False,
    }
    assert phase10.should_save_iteration_evidence(row, args()) is False


def test_explicit_fallback_click_evidence_saves() -> None:
    row = {
        "click_executed": True,
        "retry_scheduled": False,
        "blocked": False,
        "stop_reason": None,
        "fallback_click_evidence_saved": True,
    }
    assert phase10.should_save_iteration_evidence(row, args(save_evidence_on_fallback_click=True)) is True


def test_no_detection_timeout_is_not_blocked_in_summary() -> None:
    summary = phase10.build_summary(
        args(),
        Path("dummy"),
        [{"iteration_total_ms": 100.0, "stop_reason": "no_detection_timeout", "blocked": False, "before_detections_count": 0}],
        stop_reason="no_detection_timeout",
        blocked=False,
        keyboard_interrupt=False,
        timing={"active_loop_duration_sec": 0.1},
    )
    assert summary["blocked"] is False
    assert summary["no_detection_timeout_count"] == 1
    assert summary["loop_iterations_attempted"] == 1
    assert summary["action_iterations_attempted"] == 0
