from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path("scripts").resolve()))

import live_finite_repeat_aim_click as phase10


def args(**overrides):
    base = dict(
        retry_policy="bounded",
        retry_same_target_distance_px=45.0,
        max_total_retry_attempts=100,
        max_retries_per_target=2,
        retry_distance_px=30.0,
        allow_retry_after_center_roi_fallback=True,
        max_iterations=300,
        max_loop_iterations=1000,
        max_duration_sec=120.0,
        after_validation_mode="hybrid",
        capture_backend="auto",
        after_fast_mode="roi_only",
        click_guard_mode="strict",
        evidence_mode="failures",
        save_evidence_on_fallback_click=False,
        max_no_detection_timeouts=200,
        max_consecutive_no_detection_timeouts=30,
        no_detection_policy="continue",
        save_evidence_on_no_detection=True,
        max_no_detection_evidence=10,
        debug_detection_parity=False,
        debug_detection_parity_on_no_detection=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def row(**overrides):
    base = dict(
        iteration_index=1,
        chosen_center_x=100.0,
        chosen_center_y=100.0,
        before_detections_count=7,
        before_distance_to_crosshair_px=279.0,
        after_validation_method="no_after_detection",
        after_validation_passed=False,
        after_distance_to_crosshair_px=None,
        stop_reason="after_detection_missing",
        click_executed=False,
        blocked=True,
        blocked_reason="after_detection_missing",
    )
    base.update(overrides)
    return base


def test_bounded_after_detection_missing_schedules_retry() -> None:
    r = row()
    stop = phase10.mark_retry_or_stop(r, args(), phase10.new_retry_state(), "after_detection_missing")
    assert stop is None
    assert r["blocked"] is False
    assert r["retry_scheduled"] is True
    assert r["retry_reason"] == "after_detection_missing_retry"
    assert r["after_detection_missing_retry"] is True
    assert r["stop_reason"] is None
    assert r["click_executed"] is False


def test_stop_policy_keeps_old_behavior() -> None:
    r = row()
    stop = phase10.mark_retry_or_stop(r, args(retry_policy="stop"), phase10.new_retry_state(), "after_detection_missing")
    assert stop == "after_detection_missing"
    assert r.get("retry_scheduled") is False


def test_max_total_retry_attempts_reached_stops() -> None:
    r = row()
    state = phase10.new_retry_state()
    state["total_retry_attempts"] = 1
    stop = phase10.mark_retry_or_stop(r, args(max_total_retry_attempts=1), state, "after_detection_missing")
    assert stop == "retry_limit_reached"
    assert r["retry_limit_reached"] is True


def test_max_retries_per_target_reached_stops() -> None:
    r = row()
    state = phase10.new_retry_state()
    state["retry_count_for_group"] = 1
    stop = phase10.mark_retry_or_stop(r, args(max_retries_per_target=1), state, "after_detection_missing")
    assert stop == "retry_limit_reached"
    assert r["retry_limit_reached"] is True


def test_after_missing_retry_does_not_increment_clicks() -> None:
    rows = [row(retry_scheduled=True, retry_reason="after_detection_missing_retry", blocked=False, stop_reason=None, click_executed=False)]
    summary = phase10.build_summary(args(), Path("dummy"), rows, stop_reason="max_iterations_reached", blocked=False, keyboard_interrupt=False, timing={})
    assert summary["clicks_executed"] == 0
    assert summary["after_detection_missing_retry_count"] == 1


def test_after_missing_retry_action_semantics() -> None:
    rows = [row(retry_scheduled=True, retry_reason="after_detection_missing_retry", blocked=False, stop_reason=None, click_executed=False, before_detections_count=7)]
    summary = phase10.build_summary(args(), Path("dummy"), rows, stop_reason="max_iterations_reached", blocked=False, keyboard_interrupt=False, timing={})
    assert summary["action_iterations_attempted"] == 1
