from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import sys
sys.path.insert(0, str(Path("scripts").resolve()))

import live_finite_repeat_aim_click as phase10


def args(**overrides):
    base = dict(
        after_validation_mode="hybrid",
        click_threshold_px=8.0,
        center_roi_radius_px=20,
        center_roi_click_threshold_px=10.0,
        center_roi_min_yellow_pixels=8,
        center_roi_min_contour_area_px=4,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def detection(index: int, x: float, y: float) -> dict:
    return {"detection_index": index, "center_monitor_px": {"x": x, "y": y}}


def make_image(path: Path, *, yellow: bool = False, green: bool = False) -> None:
    pil = pytest.importorskip("PIL")
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (120, 120), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    if green:
        draw.line((50, 60, 70, 60), fill=(0, 255, 0), width=2)
        draw.line((60, 50, 60, 70), fill=(0, 255, 0), width=2)
    if yellow:
        draw.ellipse((56, 56, 64, 64), fill=(255, 230, 0))
    image.save(path)


def test_yolo_center_validation_pass(tmp_path: Path) -> None:
    image_path = tmp_path / "after.png"
    make_image(image_path)
    result = phase10.validate_after_move(
        after_detections=[detection(0, 80, 80), detection(1, 63, 62)],
        crosshair={"x": 60.0, "y": 60.0},
        after_image_path=image_path,
        args=args(),
    )
    assert result["after_validation_passed"] is True
    assert result["after_validation_method"] == "yolo_center_detection"
    assert result["after_nearest_detection_index"] == 1
    assert result["after_distance_to_crosshair_px"] <= 8


def test_center_roi_fallback_pass_when_yolo_missed_centered_ball(tmp_path: Path) -> None:
    image_path = tmp_path / "after.png"
    make_image(image_path, yellow=True)
    result = phase10.validate_after_move(
        after_detections=[detection(0, 20, 100)],
        crosshair={"x": 60.0, "y": 60.0},
        after_image_path=image_path,
        args=args(),
    )
    assert result["after_validation_passed"] is True
    assert result["after_validation_method"] == "center_roi_yellow_fallback"
    assert result["center_roi_fallback_passed"] is True
    assert result["after_nearest_detection_distance_px"] > 8


def test_center_roi_fallback_does_not_pass_green_crosshair_only(tmp_path: Path) -> None:
    image_path = tmp_path / "after.png"
    make_image(image_path, green=True)
    result = phase10.validate_after_move(
        after_detections=[],
        crosshair={"x": 60.0, "y": 60.0},
        after_image_path=image_path,
        args=args(),
    )
    assert result["after_validation_passed"] is False
    assert result["center_roi_fallback_passed"] is False
    assert result["center_roi_yellow_pixel_count"] == 0


def test_far_yolo_detection_without_center_yellow_fails(tmp_path: Path) -> None:
    image_path = tmp_path / "after.png"
    make_image(image_path)
    result = phase10.validate_after_move(
        after_detections=[detection(0, 10, 10)],
        crosshair={"x": 60.0, "y": 60.0},
        after_image_path=image_path,
        args=args(),
    )
    assert result["after_validation_passed"] is False
    assert result["after_validation_method"] == "nearest_yolo_far"
    assert result["stop_reason"] == "after_distance_exceeded_threshold"


def test_no_after_detection_without_center_yellow_fails(tmp_path: Path) -> None:
    image_path = tmp_path / "after.png"
    make_image(image_path)
    result = phase10.validate_after_move(
        after_detections=[],
        crosshair={"x": 60.0, "y": 60.0},
        after_image_path=image_path,
        args=args(),
    )
    assert result["after_validation_passed"] is False
    assert result["after_validation_method"] == "no_after_detection"
    assert result["stop_reason"] == "after_detection_missing"


def test_max_duration_uses_active_loop_duration_not_startup() -> None:
    assert phase10.should_stop_for_active_duration(loop_start_perf=100.0, max_duration_sec=10.0, now_perf=109.9) is False
    assert phase10.should_stop_for_active_duration(loop_start_perf=100.0, max_duration_sec=10.0, now_perf=110.0) is True
