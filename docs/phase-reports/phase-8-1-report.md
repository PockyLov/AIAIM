# Phase 8.1 Report - FOV-based One-Shot Relative Aim Model

## Phase Goal

Implement a FOV-based one-shot relative aim model that converts YOLO target pixel delta into angular delta and then into one relative mouse movement using theoretical `counts_per_degree=39.03`.

Phase 8.1 remains one-shot only. It is not a closed-loop control system.

## Work Completed

Added:

- `src/aiaim_control/__init__.py`
- `src/aiaim_control/fov_aim_model.py`
- `scripts/live_one_shot_fov_aim.py`
- `tests/test_phase8_1_fov_aim_model.py`
- `docs/runbooks/phase-8-1-fov-one-shot-aim-runbook.md`
- `docs/phase-reports/phase-8-1-report.md`

Updated:

- `README.md`

## FOV Model

The model computes:

```text
focal_x = (screen_width / 2) / tan(horizontal_fov_rad / 2)
focal_y = (screen_height / 2) / tan(vertical_fov_rad / 2)
angle_x_deg = degrees(atan(delta_x_px / focal_x))
angle_y_deg = degrees(atan(delta_y_px / focal_y))
mouse_dx = angle_x_deg * counts_per_degree * global_gain
mouse_dy = angle_y_deg * counts_per_degree * global_gain
```

Defaults:

- `horizontal_fov_deg=103`
- `vertical_fov_deg=70.53`
- `screen_width=1920`
- `screen_height=1080`
- `counts_per_degree=39.03`
- `global_gain=1.0`

For the Phase 8 accepted sample, the unit test expects approximately:

- `angle_x_deg ≈ -3.31`
- `angle_y_deg ≈ 4.84`
- rounded move `dx ≈ -129`
- rounded move `dy ≈ 189`

## Safety Boundary

Phase 8.1 did not implement:

- clicking
- automatic clicking
- target lock
- looped movement
- closed-loop correction
- second correction after after-frame detection
- PID
- micro-step movement
- smooth movement
- anti-cheat bypass
- process memory reading
- AIMLAB file modification
- background automation

The script has a single guarded `SendInput` call path and only executes when both `--execute-move` and `--confirm-local-aimlab-only` are present and the AIMLAB foreground / target / movement-limit gates pass.

## Validation Performed

Commands run in the current WSL/Linux Codex shell:

```bash
PYTHONPYCACHEPREFIX=/tmp/aiaim_pycache python3 -m compileall scripts src tests
PYTHONPATH=src python3 scripts/live_one_shot_fov_aim.py --help
PYTHONPATH=src python3 -m pytest tests/test_phase8_1_fov_aim_model.py
PYTHONPATH=src python3 scripts/live_one_shot_fov_aim.py --start-delay-sec 0 --run-id wsl_phase8_1_dry_run_blocked --overwrite --output-dir /tmp/aiaim_phase8_1_runs
rg -n "SetCursorPos|pyautogui|pynput|keyboard|mouse_event|\.click\(|MOUSEEVENTF_LEFT|MOUSEEVENTF_RIGHT|while " scripts/live_one_shot_fov_aim.py src/aiaim_control
rg -n "send_relative_mouse_move\(|SendInput|MOUSEEVENTF_MOVE|allowed_to_move" scripts/live_one_shot_fov_aim.py
```

Results:

- `compileall` passed with pycache redirected to `/tmp/aiaim_pycache`.
- `scripts/live_one_shot_fov_aim.py --help` passed.
- `python3 -m pytest` could not run because the current system Python has no `pytest` module.
- The five pure Phase 8.1 test functions were executed directly with `PYTHONPATH=src`; all passed.
- WSL blocked dry-run wrote `/tmp/aiaim_phase8_1_runs/wsl_phase8_1_dry_run_blocked/phase8_1_result.json` with `relative_aim_executed=false` and `sendinput_attempted=false`.
- Safety scan found no `SetCursorPos`, `pyautogui`, `pynput`, `keyboard`, `mouse_event`, click call, mouse-button flags, or `while` loop in the Phase 8.1 script/control module.
- `SendInput` appears only in the relative-move helper and the one guarded call path after `move_gate["allowed_to_move"]`.

Recommended Windows setup if needed:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

This Codex environment is WSL/Linux, not the Windows desktop session. Windows + AIMLAB real-machine validation is pending.

## Real-machine Validation Status

Pending.

Phase 8 remains accepted. Phase 8.1 does not change the Phase 8 accepted result; it adds an alternative FOV-based one-shot model for comparison.

## Known Risks

- FOV values must match AIMLAB's effective non-ADS Hipfire FOV.
- `counts_per_degree=39.03` is theoretical and may need manual `global_gain` tuning.
- If residual remains high, adjust `global_gain` manually in a later validation pass; do not add automatic calibration or closed-loop correction in Phase 8.1.
- YOLO target choice can still be wrong if detections are ambiguous.

## Next Step

Run Phase 8.1 dry-run on Windows + AIMLAB, inspect `phase8_1_result.json`, then run one explicit `--execute-move` test only if dry-run output is correct. If residual is still large, record the observation and consider manual `global_gain` tuning such as `0.95` or `1.05` in a later phase.
