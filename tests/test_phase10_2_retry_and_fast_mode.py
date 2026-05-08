from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path("scripts").resolve()))

import live_finite_repeat_aim_click as phase10


def args(**overrides):
    base = dict(
        retry_policy="bounded",
        max_retries_per_target=1,
        max_total_retry_attempts=20,
        retry_distance_px=30.0,
        retry_same_target_distance_px=45.0,
        allow_retry_after_center_roi_fallback=True,
        save_review_images=False,
        evidence_mode="failures",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def base_row(**overrides):
    row = dict(
        iteration_index=1,
        chosen_center_x=100.0,
        chosen_center_y=100.0,
        before_distance_to_crosshair_px=80.0,
        after_validation_method="center_roi_yellow_fallback",
        after_validation_passed=True,
        after_distance_to_crosshair_px=8.9,
        after_nearest_detection_distance_px=50.0,
        click_gate_passed=False,
        click_executed=False,
        blocked=False,
        stop_reason=None,
    )
    row.update(overrides)
    return row


def test_center_roi_fallback_passed_but_click_threshold_failed_schedules_retry() -> None:
    state = phase10.new_retry_state()
    row = base_row()
    stop = phase10.mark_retry_or_stop(row, args(), state, None)
    assert stop is None
    assert row["retry_scheduled"] is True
    assert row["retry_reason"] == "center_roi_passed_but_click_threshold_failed"
    assert row["iteration_status"] == "retry_scheduled"
    assert row["click_executed"] is False


def test_nearest_yolo_far_within_retry_distance_schedules_retry() -> None:
    state = phase10.new_retry_state()
    row = base_row(
        after_validation_method="nearest_yolo_far",
        after_validation_passed=False,
        after_distance_to_crosshair_px=25.0,
        after_nearest_detection_distance_px=25.0,
        stop_reason="after_distance_exceeded_threshold",
    )
    stop = phase10.mark_retry_or_stop(row, args(), state, "after_distance_exceeded_threshold")
    assert stop is None
    assert row["retry_scheduled"] is True
    assert row["retry_reason"] == "after_nearest_within_retry_distance"


def test_retry_policy_stop_keeps_old_no_retry_behavior() -> None:
    state = phase10.new_retry_state()
    row = base_row()
    stop = phase10.mark_retry_or_stop(row, args(retry_policy="stop"), state, None)
    assert stop is None
    assert row["retry_scheduled"] is False


def test_max_retries_per_target_limits_same_target_retry() -> None:
    state = phase10.new_retry_state()
    first = base_row(iteration_index=1, chosen_center_x=100.0, chosen_center_y=100.0)
    assert phase10.mark_retry_or_stop(first, args(max_retries_per_target=1), state, None) is None
    second = base_row(iteration_index=2, chosen_center_x=110.0, chosen_center_y=105.0)
    stop = phase10.mark_retry_or_stop(second, args(max_retries_per_target=1), state, None)
    assert stop == "retry_limit_reached"
    assert second["retry_limit_reached"] is True
    assert second["retry_reason"] == "max_retries_per_target_reached"


def test_max_total_retry_attempts_limits_global_retries() -> None:
    state = phase10.new_retry_state()
    state["total_retry_attempts"] = 1
    row = base_row()
    stop = phase10.mark_retry_or_stop(row, args(max_total_retry_attempts=1), state, None)
    assert stop == "retry_limit_reached"
    assert row["retry_reason"] == "max_total_retry_attempts_reached"


def test_evidence_mode_failures_skips_evidence_for_clicked_success() -> None:
    row = base_row(click_executed=True, retry_scheduled=False, blocked=False, stop_reason=None)
    assert phase10.should_save_iteration_evidence(row, args(evidence_mode="failures")) is False


def test_evidence_mode_failures_saves_evidence_for_retry_or_failure() -> None:
    retry_row = base_row(retry_scheduled=True, click_executed=False)
    fail_row = base_row(blocked=True, stop_reason="after_distance_exceeded_threshold", click_executed=False)
    assert phase10.should_save_iteration_evidence(retry_row, args(evidence_mode="failures")) is True
    assert phase10.should_save_iteration_evidence(fail_row, args(evidence_mode="failures")) is True


def test_post_click_wait_default_is_005(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["live_finite_repeat_aim_click.py"])
    parsed = phase10.parse_args()
    assert parsed.post_click_wait_sec == 0.03
    assert parsed.evidence_mode == "failures"
    assert parsed.retry_policy == "bounded"
