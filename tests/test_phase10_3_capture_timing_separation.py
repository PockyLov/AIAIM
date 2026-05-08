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
        save_evidence_on_fallback_click=True,
        capture_benchmark_include_encode=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_capture_elapsed_excludes_evidence_encode_ms() -> None:
    timings = {
        "capture_object_init_ms": 2.0,
        "monitor_lookup_ms": 1.0,
        "raw_grab_ms": 20.0,
        "buffer_to_numpy_ms": 3.0,
        "color_convert_ms": 4.0,
        "evidence_encode_ms": 500.0,
    }
    assert phase10.capture_elapsed_from_timings(timings) == 30.0


def test_capture_benchmark_default_does_not_include_encode() -> None:
    parsed = args()
    assert parsed.capture_benchmark_include_encode is False
    timings = {"raw_grab_ms": 18.0, "evidence_encode_ms": 0.0}
    assert phase10.capture_elapsed_from_timings(timings) == 18.0


def test_failures_mode_clicked_success_skips_evidence_encode() -> None:
    row = {"click_executed": True, "retry_scheduled": False, "blocked": False, "stop_reason": None, "fallback_click_evidence_saved": False}
    assert phase10.should_save_iteration_evidence(row, args()) is False


def test_retry_or_failure_saves_evidence() -> None:
    retry_row = {"click_executed": False, "retry_scheduled": True, "blocked": False, "stop_reason": None, "fallback_click_evidence_saved": False}
    fail_row = {"click_executed": False, "retry_scheduled": False, "blocked": True, "stop_reason": "after_distance_exceeded_threshold", "fallback_click_evidence_saved": False}
    assert phase10.should_save_iteration_evidence(retry_row, args()) is True
    assert phase10.should_save_iteration_evidence(fail_row, args()) is True


def test_fallback_click_forces_evidence() -> None:
    row = {"click_executed": True, "retry_scheduled": False, "blocked": False, "stop_reason": None, "fallback_click_evidence_saved": True}
    assert phase10.should_save_iteration_evidence(row, args()) is True


def test_save_iteration_evidence_records_independent_timing(monkeypatch, tmp_path: Path) -> None:
    calls = {"encode": 0, "draw": 0, "write": 0}

    def fake_encode(capture):
        calls["encode"] += 1
        return 5.0

    def fake_draw(*_args, **_kwargs):
        calls["draw"] += 1

    def fake_write(_path, _data):
        calls["write"] += 1

    monkeypatch.setattr(phase10, "encode_capture_image", fake_encode)
    monkeypatch.setattr(phase10.phase81, "draw_review_image", fake_draw)
    monkeypatch.setattr(phase10, "write_json", fake_write)

    before = phase10.CapturedFrame(tmp_path / "before.png", frame=None, screenshot_width=10, screenshot_height=10, capture_elapsed_ms=3.0)
    after = phase10.CapturedFrame(tmp_path / "after.png", frame=None, screenshot_width=10, screenshot_height=10, capture_elapsed_ms=4.0)
    row = {}
    phase10.save_iteration_evidence(
        row=row,
        iter_dir=tmp_path,
        before_capture=before,
        after_capture=after,
        before_detections=[],
        after_detections=[],
        crosshair={"x": 5.0, "y": 5.0},
        chosen=None,
        fov_move={"planned_relative_move_dxdy": {"dx": 0, "dy": 0}},
        after_chosen=None,
        after_distance=None,
    )
    assert calls["encode"] == 2
    assert calls["draw"] == 2
    assert calls["write"] == 1
    assert row["evidence_encode_ms"] == 10.0
    assert row["evidence_total_ms"] >= row["evidence_encode_ms"]
    assert row["total_io_ms"] == row["evidence_total_ms"]
