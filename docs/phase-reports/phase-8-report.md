# Phase 8 Report - One-Shot Relative Aim to Target

## Phase Goal

Use YOLO live detection to select the yellow target nearest the monitor-center crosshair, compute its pixel offset from the crosshair, convert that offset to one relative mouse movement using Phase 7.5 calibration, and optionally send exactly one Windows `SendInput` relative mouse movement under explicit gates.

## Implementation Completed

Added:

- `scripts/live_one_shot_relative_aim.py`
- `config/phase8-one-shot-relative-aim.json`
- `docs/runbooks/phase-8-one-shot-relative-aim-runbook.md`
- `docs/phase-reports/phase-8-report.md`

Minimally updated:

- `README.md`
- `docs/phase-roadmap.md`
- `docs/safety-boundary.md`

## Safety Boundary

Phase 8 defaults to dry-run because `allow_relative_mouse_move=false` in config.

Real relative aim requires:

- config `allow_relative_mouse_move=true`
- CLI `--execute-relative-aim`
- CLI `--confirm-local-aimlab-only`
- AIMLAB foreground gate passed
- config `allow_click=false`
- config `allow_loop=false`
- config `allow_closed_loop=false`
- before target exists
- calibration values exist and are non-zero
- rounded relative movement is inside configured max absolute limits

Phase 8 did not implement clicking, automatic clicking, target lock, looped movement, closed-loop correction, PID, micro-step movement, smoothing movement, anti-cheat bypass, or process memory reading.

## Coordinate Contract

Coordinate space is monitor-relative screenshot pixels.

- `crosshair_center_monitor_px` is the monitor screenshot center.
- `target_selection=nearest_to_crosshair` selects the detection nearest that center.
- `target_delta_to_crosshair_px.dx = target_center_x - crosshair_center_x`.
- `target_delta_to_crosshair_px.dy = target_center_y - crosshair_center_y`.
- Windows cursor position is not the aiming basis.

## Calculation Formula

Phase 7.5 calibration values:

- `px_per_mouse_count_x = -0.3605`
- `px_per_mouse_count_y = -0.3024`

Formula:

```text
mouse_dx = -delta_x / px_per_mouse_count_x
mouse_dy = -delta_y / px_per_mouse_count_y
```

The values are rounded to integers before the one-shot relative movement.

## Validation Performed

Commands run from the current WSL/Linux Codex shell:

```bash
PYTHONPYCACHEPREFIX=/tmp/aiaim_pycache python3 -m compileall scripts
python3 scripts/live_one_shot_relative_aim.py --help
python3 -m json.tool config/phase8-one-shot-relative-aim.json
python3 scripts/live_one_shot_relative_aim.py --start-delay-sec 0 --run-id wsl_phase8_dry_run_blocked --overwrite --output-root /tmp/aiaim_phase8_runs
rg -n "SetCursorPos|pyautogui|pynput|keyboard|mouse_event|\.click\(|MOUSEEVENTF_LEFT|MOUSEEVENTF_RIGHT" scripts/live_one_shot_relative_aim.py
rg -n "send_relative_mouse_move\(|SendInput|MOUSEEVENTF_MOVE|allowed_to_move|while " scripts/live_one_shot_relative_aim.py
```

Results:

- `compileall scripts` passed when `PYTHONPYCACHEPREFIX` was redirected to `/tmp/aiaim_pycache`. The default pycache location is read-only in this sandbox.
- `scripts/live_one_shot_relative_aim.py --help` passed.
- `json.tool config/phase8-one-shot-relative-aim.json` passed.
- WSL blocked dry-run completed with `blocked=True`, `frames_processed=0`, `relative_aim_executed=False`, and `sendinput_attempted=False`.
- Safety scan found no `SetCursorPos`, `pyautogui`, `pynput`, `keyboard`, `mouse_event`, click call, or mouse button flags in the Phase 8 script.
- Phase 8 script has exactly one `send_relative_mouse_move(...)` call site and it is guarded by `relative_aim_gate["allowed_to_move"]`.
- No `while` loop is present in the Phase 8 script.

Current Codex environment is WSL/Linux, not the Windows desktop session with AIMLAB. Windows + AIMLAB full-screen acceptance was completed by the user and is recorded below.

Implemented code-level safety checks:

- dry-run does not call `SendInput` because `relative_aim_gate.allowed_to_move=false` without config and CLI gates
- no click function is implemented
- no looped movement is implemented
- no `SetCursorPos` action call is used
- `SendInput` is called only after `relative_aim_gate["allowed_to_move"]` is true
- there is only one `send_relative_mouse_move(...)` call site

## Windows Full-screen Acceptance Result

Phase 8 accepted.

AIMLAB full-screen validation confirms that monitor center can be used as the crosshair / gameplay center in this tested full-screen setup. One-shot relative aim successfully reduced target distance from `78.3356px` to `10.9768px`.

Acceptance data:

- blocked = false
- frames_processed = 1
- after_validation_frame_processed = true
- detections_count = 8
- target_selection = nearest_to_crosshair
- chosen_detection_index = 2
- chosen_conf = 0.6328
- crosshair_center_monitor_px = `{"x": 960.0, "y": 540.0}`
- chosen_center_monitor_px = `{"x": 915.7538, "y": 604.6432}`
- target_delta_to_crosshair_px = `{"dx": -44.2462, "dy": 64.6432}`
- before_distance_to_crosshair_px = 78.3356
- px_per_mouse_count_x = -0.3605
- px_per_mouse_count_y = -0.3024
- planned_relative_move_dxdy = `{"dx": -122.7356, "dy": 213.7672}`
- rounded_relative_move_dxdy = `{"dx": -123, "dy": 214}`
- relative_aim_gate.allowed_to_move = true
- relative_aim_executed = true
- sendinput_attempted = true
- after_detections_count = 8
- after_chosen_center_monitor_px = `{"x": 953.935, "y": 530.8509}`
- after_distance_to_crosshair_px = 10.9768
- distance_reduction_px = 67.3588
- distance_reduction_ratio = 0.8599
- after_match_status = matched_nearest_to_crosshair
- monitor_rect = `0,0,1920,1080`
- window_rect = `0,0,1920,1080`

Acceptance interpretation:

- The one-shot relative movement reduced distance by `67.3588px`.
- Distance reduction ratio was `85.99%`.
- The final distance `10.9768px` is close enough to confirm the Phase 8 one-shot relative aim approach is viable.
- This acceptance does not imply clicking is allowed; Phase 8 remains movement-only.

## Known Risks

- Phase 7.5 calibration is based on two single-axis samples and may be approximate.
- AIMLAB sensitivity or resolution changes can invalidate `px_per_mouse_count`.
- Matching after-frame targets can be ambiguous when multiple yellow targets are visible.
- One-shot movement may undershoot or overshoot; Phase 8 records this but does not correct it.

## What Was Intentionally Not Done

- No clicking.
- No automatic clicking.
- No target lock.
- No looped movement.
- No closed-loop correction.
- No second move after after-frame detection.
- No PID.
- No micro-step movement.
- No smoothing movement.
- No anti-cheat bypass.
- No process memory reading.
- No AIMLAB file modification.

## Next Phase Suggestion

Phase 8 is accepted. If the project enters Phase 9, the scope should be limited to click gate / manual click validation design. Do not modify Phase 8 into a closed-loop system, target lock, looped mover, PID controller, micro-step mover, smoothing mover, or auto-clicker.
