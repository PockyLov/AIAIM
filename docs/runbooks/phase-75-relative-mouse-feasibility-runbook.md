# Phase 7.5 Relative Mouse Feasibility Runbook

Phase 7.5 name:

```text
One-Shot Relative Mouse Actuation Feasibility
```

## Goal

Verify whether AIMLAB responds to one fixed relative mouse movement, then estimate how much the screen target position shifts in pixels.

Phase 7.5 is not auto-aim. It sends at most one relative mouse movement, captures one before frame and one after frame, then exits.

## Why Phase 7 SetCursorPos Is Not Enough

Phase 7 executed Windows `SetCursorPos`, but AIMLAB gameplay kept the system cursor near the center:

- `move_executed = true`
- planned cursor position was not reached by `cursor_after_screen_px`

This indicates direct absolute cursor positioning is not suitable as the AIMLAB in-game aim actuation method.

## Why SendInput Relative Movement

Games often consume relative mouse input rather than absolute OS cursor position. Phase 7.5 therefore uses Windows `SendInput` with `MOUSEEVENTF_MOVE` for one fixed relative movement:

- `dx = 100`
- `dy = 0`

It does not click and does not repeat movement.

## Project Directory

```powershell
Set-Location "D:\桌面desktop\AIAIM"
```

## Config

```text
config/phase75-relative-mouse-feasibility.json
```

Default config:

```json
{
  "allow_relative_mouse_move": false,
  "allow_click": false,
  "allow_loop": false,
  "allow_closed_loop": false,
  "target_selection": "nearest_to_crosshair",
  "default_relative_dx": 100,
  "default_relative_dy": 0,
  "max_abs_relative_dx": 500,
  "max_abs_relative_dy": 500,
  "settle_sec": 0.2,
  "max_match_distance_px": 300
}
```

Real relative movement requires:

- config `allow_relative_mouse_move=true`
- CLI `--execute-relative-move`
- CLI `--confirm-local-aimlab-only`
- AIMLAB foreground gate passed
- `allow_click=false`
- `allow_loop=false`
- `allow_closed_loop=false`
- `relative_dx` / `relative_dy` within configured absolute limits
- before reference target exists

## Dry-Run Command

```powershell
.\.venv\Scripts\python.exe scripts\live_relative_mouse_feasibility.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --conf 0.25 `
  --start-delay-sec 8 `
  --relative-dx 100 `
  --relative-dy 0 `
  --run-id phase75_windows_dry_run_dx100 `
  --overwrite
```

Expected:

- AIMLAB foreground gate passes
- before frame is saved
- before detections exist
- reference target is selected by nearest-to-crosshair
- planned relative move is recorded
- `relative_move_executed=false`
- no `SendInput` is sent
- no click occurs

## Execute DX Test

Before running, set config `allow_relative_mouse_move=true`.

```powershell
.\.venv\Scripts\python.exe scripts\live_relative_mouse_feasibility.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --conf 0.25 `
  --start-delay-sec 8 `
  --relative-dx 100 `
  --relative-dy 0 `
  --execute-relative-move `
  --confirm-local-aimlab-only `
  --run-id phase75_windows_execute_dx100 `
  --overwrite
```

Expected:

- one before frame
- one `SendInput` relative movement
- one after frame
- before and after detections
- observed shift if matching succeeds
- manual review required if matching is uncertain
- program exits after one attempt

## Optional DY Test

```powershell
.\.venv\Scripts\python.exe scripts\live_relative_mouse_feasibility.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --conf 0.25 `
  --start-delay-sec 8 `
  --relative-dx 0 `
  --relative-dy 100 `
  --execute-relative-move `
  --confirm-local-aimlab-only `
  --run-id phase75_windows_execute_dy100 `
  --overwrite
```

## Outputs

Each run creates:

```text
runs/phase75_relative_mouse_feasibility/<run_id>/
```

Files:

- `before_frame.png`
- `after_frame.png` if execute movement succeeds
- `before_review_image.png`
- `after_review_image.png` if after frame exists
- `before_detections.json`
- `after_detections.json` if after frame exists or movement was attempted
- `relative_move_event.json`
- `phase75_summary.json`
- `run_config.json`
- `summary.csv`

## How To Judge Pass / Fail

Dry-run passes when:

- before frame and detections are saved
- reference target exists
- planned relative move is recorded
- `relative_move_executed=false`

Execute DX passes as a feasibility test when:

- `relative_move_gate.allowed_to_move=true`
- `relative_move_executed=true`
- after frame is saved
- review images show clear before / after scene movement
- `observed_screen_shift_px` is computed, or `match_status=manual_review_required` with useful review images

If `dx=100` produces visible horizontal movement, AIMLAB responds to relative mouse movement.

If `px_per_mouse_count_x` is computed, it can be used in Phase 8 to design a one-shot relative aim estimate. Phase 7.5 does not use it for aiming.

## Phase Boundary

Phase 7.5 forbids:

- clicking
- auto-aim
- target lock
- looped movement
- closed-loop correction
- second movement after after-frame detection
- anti-cheat bypass
- process memory reading
- process injection
- AIMLAB file modification
- background automation

Phase 8 is not implemented here.
