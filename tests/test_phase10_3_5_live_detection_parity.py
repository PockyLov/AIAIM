from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np

sys.path.insert(0, str(Path("scripts").resolve()))

import live_finite_repeat_aim_click as phase10


class FakeTensor:
    def __init__(self, values):
        self.values = values
    def detach(self):
        return self
    def cpu(self):
        return self
    def tolist(self):
        return self.values


class FakeBoxes:
    def __init__(self):
        self.xyxy = FakeTensor([[10, 20, 30, 40]])
        self.conf = FakeTensor([0.75])
        self.cls = FakeTensor([0])
    def __len__(self):
        return 1


class FakeResult:
    boxes = FakeBoxes()


def ctx():
    return SimpleNamespace(model_names={0: "yellow_ball"}, conf=0.25, iou=0.7, max_det=50, imgsz=640, actual_device="cpu")


def test_live_frame_bgra_conversion_contract() -> None:
    bgra = np.zeros((2, 3, 4), dtype=np.uint8)
    bgr = bgra[:, :, :3].copy()
    rgb = bgr[:, :, ::-1].copy()
    capture = phase10.CapturedFrame(Path("before.png"), frame=rgb, screenshot_width=3, screenshot_height=2, capture_elapsed_ms=1.0, yolo_frame=bgr)
    yolo = phase10.yolo_input_frame(capture)
    assert yolo.shape == (2, 3, 3)
    assert yolo.dtype == np.uint8


def test_detection_parser_does_not_drop_valid_boxes() -> None:
    detections = phase10.phase81.detections_from_results(ctx(), [FakeResult()], 1920, 1080)
    assert len(detections) == 1
    assert detections[0]["confidence"] == 0.75


def test_parity_mismatch_flags_input_format_suspected() -> None:
    flags = phase10.parity_flags(0, 5)
    assert flags["live_vs_file_detection_mismatch"] is True
    assert flags["live_detection_input_format_mismatch_suspected"] is True


def test_parity_match_flag() -> None:
    flags = phase10.parity_flags(5, 5)
    assert flags["live_vs_file_detection_mismatch"] is False
    assert flags["live_detection_input_format_mismatch_suspected"] is False


def test_run_config_fields_are_written_in_source() -> None:
    source = Path("scripts/live_finite_repeat_aim_click.py").read_text(encoding="utf-8")
    for field in ("conf", "iou", "max_det", "imgsz", "device", "debug_detection_parity"):
        assert f'"{field}"' in source
