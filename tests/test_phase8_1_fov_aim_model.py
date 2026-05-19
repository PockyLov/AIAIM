from __future__ import annotations

import ast
from pathlib import Path

from aiaim_control.fov_aim_model import compute_focal_px, compute_fov_relative_move


def test_compute_focal_px_for_1920_1080_valorant_fov() -> None:
    focal = compute_focal_px(1920, 1080, 103, 70.53)
    assert abs(focal["focal_x"] - 763.6) < 2.0
    assert abs(focal["focal_y"] - 763.6) < 2.0


def test_phase8_real_sample_fov_relative_move_sign_and_magnitude() -> None:
    result = compute_fov_relative_move(
        target_center_x=915.7538,
        target_center_y=604.6432,
        crosshair_x=960,
        crosshair_y=540,
        screen_width=1920,
        screen_height=1080,
        horizontal_fov_deg=103,
        vertical_fov_deg=70.53,
        counts_per_degree=39.03,
        global_gain=1.0,
    )
    assert abs(result["angle_delta_deg"]["x"] - (-3.31)) < 0.08
    assert abs(result["angle_delta_deg"]["y"] - 4.84) < 0.08
    assert abs(result["rounded_relative_move_dxdy"]["dx"] - (-129)) <= 4
    assert abs(result["rounded_relative_move_dxdy"]["dy"] - 189) <= 4


def test_phase8_1_script_has_no_click_or_continuous_control_tokens() -> None:
    source = Path("scripts/live_one_shot_fov_aim.py").read_text(encoding="utf-8")
    lowered = source.lower()
    forbidden = ["setcursorpos", "pyautogui", "pynput", ".click(", "target_lock = true"]
    for token in forbidden:
        assert token not in lowered
    tree = ast.parse(source)
    assert not any(isinstance(node, ast.While) for node in ast.walk(tree))


def test_phase8_1_sendinput_guard_and_single_call_site() -> None:
    source = Path("scripts/live_one_shot_fov_aim.py").read_text(encoding="utf-8")
    assert source.count("send_relative_mouse_move(") == 2  # function definition plus one guarded call site
    assert 'if move_gate["allowed_to_move"] and rounded_move is not None:' in source
    guarded_index = source.index('if move_gate["allowed_to_move"] and rounded_move is not None:')
    call_index = source.rindex("send_relative_mouse_move(")
    assert guarded_index < call_index


def test_phase8_1_default_dry_run_flags_exist() -> None:
    source = Path("scripts/live_one_shot_fov_aim.py").read_text(encoding="utf-8")
    assert 'parser.add_argument("--execute-move", action="store_true", default=False)' in source
    assert 'parser.add_argument("--confirm-local-aimlab-only", action="store_true", default=False)' in source
