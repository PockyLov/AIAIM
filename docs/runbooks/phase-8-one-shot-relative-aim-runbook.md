# Phase 8 One-Shot Relative Aim Runbook

## Goal

Phase 8 computes one relative mouse movement from the nearest YOLO yellow-ball target to the screen-center crosshair and optionally sends exactly one Windows `SendInput` relative mouse movement.

It is one-shot only. It does not click, does not lock a target, does not loop, and does not perform closed-loop correction.

## Why Not SetCursorPos

Phase 7 showed that direct Windows cursor positioning with `SetCursorPos` executed at the OS level but did not move AIMLAB gameplay aim as intended. AIMLAB keeps gameplay aiming tied to relative mouse input rather than absolute system cursor position.

## Why SendInput Relative Movement

Phase 7.5 Windows validation confirmed AIMLAB gameplay responds to one `SendInput` relative mouse movement. Therefore Phase 8 uses `SendInput` with `MOUSEEVENTF_MOVE` and relative `dx/dy` only.

## Phase 7.5 Calibration Values

Validated values:

- `px_per_mouse_count_x = -0.3605`
- `px_per_mouse_count_y = -0.3024`

Observed validation:

- `dx=100` produced screen shift `{"dx": -36.0487, "dy": 0.4371}`
- `dy=100` produced screen shift `{"dx": 0.166, "dy": -30.2367}`

## Formula

Phase 8 uses monitor-relative screenshot coordinates.

Crosshair center:

```text
crosshair_center_monitor_px.x = monitor_width / 2
crosshair_center_monitor_px.y = monitor_height / 2
```

Target delta:

```text
delta_x = target_center_x - crosshair_center_x
delta_y = target_center_y - crosshair_center_y
```

Desired screen shift moves the target to the crosshair:

```text
desired_screen_shift_x = -delta_x
desired_screen_shift_y = -delta_y
```

Mouse counts:

```text
mouse_dx = -delta_x / px_per_mouse_count_x
mouse_dy = -delta_y / px_per_mouse_count_y
```

The script rounds `mouse_dx/mouse_dy` to integers and sends at most one relative move if all gates pass.

## Safety Boundary

Real relative aim requires all of these:

- config `allow_relative_mouse_move=true`
- CLI `--execute-relative-aim`
- CLI `--confirm-local-aimlab-only`
- AIMLAB foreground gate passed
- config `allow_click=false`
- config `allow_loop=false`
- config `allow_closed_loop=false`
- before target exists
- `px_per_mouse_count_x/y` are present and non-zero
- rounded relative `dx/dy` are inside configured max absolute limits

If any condition fails, no `SendInput` is sent.

Phase 8 forbids:

- clicking
- automatic clicking
- target lock
- looped movement
- closed-loop correction
- second move after after-frame detection
- PID
- micro-step movement
- smoothing movement
- anti-cheat bypass
- process memory reading
- AIMLAB file modification
- background automation

## Dry-run Command

```powershell
.\.venv\Scripts\python.exe scripts\live_one_shot_relative_aim.py `
  --model "D:\桌面desktop\AIAIMuns\detect\phase3_yolo11n_baseline\weightsest.pt" `
  --conf 0.25 `
  --start-delay-sec 8 `
  --run-id phase8_windows_dry_run `
  --overwrite
```

Expected dry-run behavior:

- AIMLAB foreground gate passes on Windows with AIMLAB foreground
- before frame is saved
- detections are saved
- chosen target is selected by `nearest_to_crosshair`
- planned relative move is recorded
- `relative_aim_executed=false`
- `sendinput_attempted=false`
- no click occurs

## Execute One-shot Relative Aim Command

Before running, temporarily set `config/phase8-one-shot-relative-aim.json` `allow_relative_mouse_move=true` locally.

```powershell
.\.venv\Scripts\python.exe scripts\live_one_shot_relative_aim.py `
  --model "D:\桌面desktop\AIAIMuns\detect\phase3_yolo11n_baseline\weightsest.pt" `
  --conf 0.25 `
  --start-delay-sec 8 `
  --execute-relative-aim `
  --confirm-local-aimlab-only `
  --run-id phase8_windows_execute_one_shot `
  --overwrite
```

After running, restore `allow_relative_mouse_move=false`.

## Output Files

Default root:

```text
runs/phase8_one_shot_relative_aim/
```

Each run writes:

- `before_frame.png`
- `before_review_image.png`
- `before_detections.json`
- `chosen_target.json`
- `relative_aim_event.json`
- `phase8_summary.json`
- `run_config.json`
- `summary.csv`

If after validation runs, it also writes:

- `after_frame.png`
- `after_review_image.png`
- `after_detections.json`

## Acceptance Checks

Dry-run acceptance:

- foreground gate passes
- `detections_count >= 1`
- chosen target exists
- crosshair center is monitor center
- target delta is recorded
- planned relative move is recorded
- no SendInput attempted
- no click occurs

Execute acceptance:

- foreground gate passes
- chosen target exists
- `relative_aim_gate.allowed_to_move=true`
- `relative_aim_executed=true`
- `sendinput_attempted=true`
- exactly one relative SendInput movement is attempted
- command exits after one attempt
- no click, no loop, no closed-loop correction, no target lock

If after validation runs, reasonable first-pass success is:

- `after_distance_to_crosshair_px < before_distance_to_crosshair_px`, or
- `distance_reduction_ratio >= 0.6`, or
- `after_distance_to_crosshair_px <= 40`

If it does not pass, record the observation. Do not add a second move or closed-loop correction in Phase 8.
