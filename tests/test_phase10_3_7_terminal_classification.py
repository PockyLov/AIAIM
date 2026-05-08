from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path("scripts").resolve()))

import live_finite_repeat_aim_click as phase10


def args(**overrides):
    base = dict(
        max_iterations=300,
        max_loop_iterations=2000,
        max_duration_sec=120.0,
        max_consecutive_no_detection_timeouts=30,
        max_no_detection_timeouts=200,
        max_no_detection_evidence=10,
        save_evidence_on_no_detection=False,
        debug_detection_parity=False,
        debug_detection_parity_on_no_detection=True,
        no_detection_policy="continue",
        after_validation_mode="hybrid",
        capture_backend="auto",
        after_fast_mode="roi_only",
        click_guard_mode="strict",
        retry_policy="bounded",
        max_retries_per_target=2,
        max_total_retry_attempts=100,
        evidence_mode="minimal",
        save_evidence_on_fallback_click=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def action_row(clicked=True, retry=False):
    return {
        "iteration_total_ms": 250.0,
        "action_round_ms": 230.0,
        "before_detections_count": 1,
        "click_executed": clicked,
        "relative_aim_executed": True,
        "retry_scheduled": retry,
        "retry_limit_reached": False,
    }


def no_detection_row():
    return {
        "iteration_total_ms": 100.0,
        "before_detections_count": 0,
        "stop_reason": "no_detection_timeout",
        "click_executed": False,
        "retry_limit_reached": False,
    }


def summary(rows, stop_reason="max_consecutive_no_detection_timeouts_reached", timing=None):
    return phase10.build_summary(
        args(),
        Path("dummy"),
        rows,
        stop_reason=stop_reason,
        blocked=False,
        keyboard_interrupt=False,
        timing=timing or {"active_loop_duration_sec": 10.0},
    )


def test_likely_task_ended_classification() -> None:
    rows = [action_row(clicked=True), action_row(clicked=True)] + [no_detection_row() for _ in range(30)]
    result = summary(rows)
    assert result["task_end_likely"] is True
    assert result["terminal_classification"] == "likely_task_ended_or_targets_exhausted"


def test_no_clicks_should_not_classify_as_task_ended() -> None:
    rows = [action_row(clicked=False)] + [no_detection_row() for _ in range(30)]
    result = summary(rows)
    assert result["task_end_likely"] is False


def test_foreground_blocked_should_not_classify_as_task_ended() -> None:
    rows = [action_row(clicked=True)] + [no_detection_row() for _ in range(30)] + [{"stop_reason": "foreground_blocked", "before_detections_count": 0, "iteration_total_ms": 1.0}]
    result = summary(rows)
    assert result["task_end_likely"] is False


def test_max_duration_reached_should_not_classify_as_task_ended() -> None:
    rows = [action_row(clicked=True)] + [no_detection_row() for _ in range(30)]
    result = summary(rows, stop_reason="max_duration_reached")
    assert result["task_end_likely"] is False


def test_metric_calculations() -> None:
    rows = [action_row(clicked=True), action_row(clicked=False, retry=True)]
    result = summary(rows, stop_reason="max_iterations_reached", timing={"active_loop_duration_sec": 2.0})
    assert result["clicks_per_active_second"] == 0.5
    assert result["actions_per_active_second"] == 1.0
    assert result["click_rate_over_actions"] == 0.5
    assert result["retry_rate_over_actions"] == 0.5
