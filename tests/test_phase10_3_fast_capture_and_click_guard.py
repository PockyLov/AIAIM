from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path("scripts").resolve()))

import live_finite_repeat_aim_click as phase10


def args(**overrides):
    base = dict(
        click_guard_mode="strict",
        click_threshold_px=8.0,
        strict_center_roi_click_threshold_px=6.0,
        fallback_click_allowed=True,
        center_roi_min_yellow_pixels=8,
        center_roi_min_contour_area_px=4,
        after_fast_mode="roi_only",
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


def row(**overrides):
    base = dict(
        iteration_index=1,
        chosen_center_x=100.0,
        chosen_center_y=100.0,
        before_distance_to_crosshair_px=80.0,
        after_validation_method="center_roi_yellow_fallback",
        after_validation_passed=True,
        after_distance_to_crosshair_px=7.5,
        after_nearest_detection_distance_px=None,
        center_roi_yellow_centroid_distance_px=7.5,
        center_roi_yellow_pixel_count=20,
        center_roi_largest_contour_area_px=10,
        click_gate_passed=True,
        click_executed=False,
    )
    base.update(overrides)
    return base


def test_strict_fallback_click_guard_schedules_retry() -> None:
    a = args(click_guard_mode="strict")
    r = row()
    allowed, reason = phase10.click_guard_allows_click(r, a)
    assert allowed is False
    assert reason == "strict_fallback_click_guard_retry"
    r["strict_fallback_guard_retry"] = True
    state = phase10.new_retry_state()
    stop = phase10.mark_retry_or_stop(r, a, state, None)
    assert stop is None
    assert r["retry_scheduled"] is True
    assert r["retry_reason"] == "strict_fallback_click_guard_retry"


def test_standard_fallback_click_guard_allows_click() -> None:
    allowed, reason = phase10.click_guard_allows_click(row(), args(click_guard_mode="standard"))
    assert allowed is True
    assert reason is None


def test_yolo_center_detection_ignores_strict_fallback_threshold() -> None:
    r = row(after_validation_method="yolo_center_detection", after_distance_to_crosshair_px=7.5)
    allowed, reason = phase10.click_guard_allows_click(r, args(click_guard_mode="strict"))
    assert allowed is True
    assert reason is None


def test_roi_only_after_fast_mode_skips_after_yolo() -> None:
    assert phase10.should_run_after_yolo(args(after_fast_mode="roi_only")) is False


def test_full_after_fast_mode_runs_after_yolo() -> None:
    assert phase10.should_run_after_yolo(args(after_fast_mode="full")) is True


def test_capture_backend_auto_falls_back_when_dxcam_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(phase10, "dxcam_status", lambda: {"dxcam_available": False, "dxcam_import_error": "missing"})
    backend, status = phase10.resolve_runtime_capture_backend("auto")
    assert backend == "mss_persistent"
    assert status["dxcam_available"] is False


def test_benchmark_under_400ms_field() -> None:
    assert phase10.benchmark_under_400(350) is True
    assert phase10.benchmark_under_400(450) is False
