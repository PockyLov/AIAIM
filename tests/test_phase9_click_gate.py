from __future__ import annotations

import ast
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path("scripts").resolve()))

import live_one_shot_click_gate as phase9


def test_click_gate_requires_execute_allow_confirm_and_threshold() -> None:
    gate = phase9.build_click_gate(
        execute_move=True,
        allow_click=True,
        confirm_local_aimlab_only=True,
        foreground_before_capture=True,
        foreground_before_move=True,
        foreground_before_click=True,
        after_detection_exists=True,
        after_distance_to_crosshair_px=6.0,
        click_threshold_px=8.0,
        already_clicked_once=False,
    )
    assert gate["allowed_to_click"] is True
    assert gate["click_denied_reason"] is None


@pytest.mark.parametrize(
    ("field", "expected_reason"),
    [
        ("execute_move", "execute_move_false"),
        ("allow_click", "allow_click_false"),
        ("confirm_local_aimlab_only", "confirm_local_aimlab_only_false"),
        ("foreground_before_click", "aimlab_not_foreground_before_click"),
        ("after_detection_exists", "no_detection_after_move"),
    ],
)
def test_click_gate_denial_reasons(field: str, expected_reason: str) -> None:
    kwargs = {
        "execute_move": True,
        "allow_click": True,
        "confirm_local_aimlab_only": True,
        "foreground_before_capture": True,
        "foreground_before_move": True,
        "foreground_before_click": True,
        "after_detection_exists": True,
        "after_distance_to_crosshair_px": 6.0,
        "click_threshold_px": 8.0,
        "already_clicked_once": False,
    }
    kwargs[field] = False
    gate = phase9.build_click_gate(**kwargs)
    assert gate["allowed_to_click"] is False
    assert gate["click_denied_reason"] == expected_reason


def test_click_gate_rejects_distance_above_threshold_and_double_click() -> None:
    far = phase9.build_click_gate(
        execute_move=True,
        allow_click=True,
        confirm_local_aimlab_only=True,
        foreground_before_capture=True,
        foreground_before_move=True,
        foreground_before_click=True,
        after_detection_exists=True,
        after_distance_to_crosshair_px=9.0,
        click_threshold_px=8.0,
        already_clicked_once=False,
    )
    assert far["allowed_to_click"] is False
    assert far["click_denied_reason"] == "after_distance_above_threshold"
    repeated = phase9.build_click_gate(
        execute_move=True,
        allow_click=True,
        confirm_local_aimlab_only=True,
        foreground_before_capture=True,
        foreground_before_move=True,
        foreground_before_click=True,
        after_detection_exists=True,
        after_distance_to_crosshair_px=6.0,
        click_threshold_px=8.0,
        already_clicked_once=True,
    )
    assert repeated["click_denied_reason"] == "already_clicked_once"


def test_phase9_script_reuses_phase81_fov_model_and_has_no_setcursorpos_or_loop() -> None:
    source = Path("scripts/live_one_shot_click_gate.py").read_text(encoding="utf-8")
    lowered = source.lower()
    assert "import live_one_shot_fov_aim as phase81" in source
    assert "compute_fov_relative_move" in source
    forbidden = ["setcursorpos", "mouse_event", "pyautogui", "pynput", "keyboard", "target_lock = true"]
    for token in forbidden:
        assert token not in lowered
    tree = ast.parse(source)
    assert not any(isinstance(node, ast.While) for node in ast.walk(tree))


def test_phase9_click_and_move_are_guarded_and_single_call_sites() -> None:
    source = Path("scripts/live_one_shot_click_gate.py").read_text(encoding="utf-8")
    assert source.count("send_relative_mouse_move(") == 1
    assert source.count("send_left_click(") == 2  # function definition plus one guarded call site
    assert 'if click_gate["allowed_to_click"]:' in source
    guarded_index = source.index('if click_gate["allowed_to_click"]:')
    call_index = source.rindex("send_left_click(")
    assert guarded_index < call_index


def test_phase9_default_args_disable_move_and_click() -> None:
    source = Path("scripts/live_one_shot_click_gate.py").read_text(encoding="utf-8")
    assert 'parser.add_argument("--execute-move", action="store_true", default=False)' in source
    assert 'parser.add_argument("--allow-click", action="store_true", default=False)' in source
    assert 'parser.add_argument("--confirm-local-aimlab-only", action="store_true", default=False)' in source
