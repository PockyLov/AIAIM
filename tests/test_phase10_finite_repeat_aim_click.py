from __future__ import annotations

import ast
from pathlib import Path
import sys

sys.path.insert(0, str(Path("scripts").resolve()))

import live_finite_repeat_aim_click as phase10


class Args:
    execute_move = True
    allow_click = True
    confirm_local_aimlab_only = True
    max_iterations = 160
    max_duration_sec = 65.0
    next_target_timeout_sec = 0.5
    no_detection_poll_interval_sec = 0.05
    post_click_wait_sec = 0.03
    center_roi_radius_px = 20
    center_roi_click_threshold_px = 10.0
    center_roi_min_yellow_pixels = 8
    center_roi_min_contour_area_px = 4
    max_retries_per_target = 1
    max_total_retry_attempts = 20
    retry_distance_px = 30.0
    retry_same_target_distance_px = 45.0


def test_startup_gate_requires_all_explicit_action_flags() -> None:
    args = Args()
    assert phase10.startup_gate(args) == (True, None)
    args.execute_move = False
    assert phase10.startup_gate(args)[1] == "execute_move_false"
    args.execute_move = True
    args.allow_click = False
    assert phase10.startup_gate(args)[1] == "allow_click_false"
    args.allow_click = True
    args.confirm_local_aimlab_only = False
    assert phase10.startup_gate(args)[1] == "confirm_local_aimlab_only_false"


def test_default_constants_and_reuse_phase9() -> None:
    source = Path("scripts/live_finite_repeat_aim_click.py").read_text(encoding="utf-8")
    assert "import live_one_shot_click_gate as phase9" in source
    assert "import live_one_shot_fov_aim as phase81" in source
    assert 'parser.add_argument("--max-iterations", type=int, default=160)' in source
    assert 'parser.add_argument("--max-duration-sec", type=float, default=65.0)' in source
    assert 'parser.add_argument("--post-click-wait-sec", type=float, default=0.03)' in source
    assert 'parser.add_argument("--next-target-timeout-sec", type=float, default=0.50)' in source


def test_phase10_has_keyboard_interrupt_and_no_hotkey_or_setcursorpos() -> None:
    source = Path("scripts/live_finite_repeat_aim_click.py").read_text(encoding="utf-8")
    lowered = source.lower()
    assert "keyboardinterrupt" in source.lower()
    for token in ["setcursorpos", "hotkey", "pynput", "readprocessmemory", "openprocess", "writeprocessmemory"]:
        assert token not in lowered
    tree = ast.parse(source)
    assert any(isinstance(node, ast.While) for node in ast.walk(tree))  # bounded by timeout / max iterations
