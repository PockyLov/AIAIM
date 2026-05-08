# Phase 7 Direct Cursor Positioning Runbook

Phase 7 name:

```text
Direct Cursor Positioning
```

## Goal

Run one-shot AIMLAB foreground detection, choose one yellow-ball target, and optionally move the Windows cursor directly to the chosen target center.

Phase 7 allows mouse movement only. It does not click, does not run a continuous aim loop, does not lock targets, and does not perform move-detect-move correction.

## Project Directory

```powershell
Set-Location "D:\桌面desktop\AIAIM"
```

## Default Model

```text
runs/detect/phase3_yolo11n_baseline/weights/best.pt
```

## Config

Config file:

```text
config/phase7-cursor-positioning.json
```

Default config keeps real movement disabled:

```json
{
  "allow_mouse_move": false,
  "allow_click": false,
  "allow_loop": false,
  "allow_closed_loop": false,
  "target_selection": "nearest_to_cursor",
  "max_direct_jump_px": null,
  "require_aimlab_foreground": true,
  "require_confirm_local_aimlab_only": true
}
```

Real cursor movement requires all of these:

- config `allow_mouse_move = true`
- CLI `--execute-move`
- CLI `--confirm-local-aimlab-only`
- AIMLAB foreground gate passes
- chosen target exists
- chosen `center_monitor_px` is inside the captured monitor image
- planned cursor position is inside `monitor_rect`
- `allow_click = false`
- `allow_loop = false`
- `allow_closed_loop = false`

`max_direct_jump_px` is optional. `null`, `0`, or missing means no direct jump distance limit. Values greater than `0` enable a maximum movement-distance gate.

## Dry-Run Command

Dry-run is the default and must be run first:

```powershell
Start-Sleep -Seconds 5; .\.venv\Scripts\python.exe scripts\live_direct_cursor_position.py `
  --model runs\detect\phase3_yolo11n_baseline\weights\best.pt `
  --conf 0.25 `
  --start-delay-sec 3 `
  --overwrite
```

Expected dry-run result:

- one frame processed
- detections are written if AIMLAB is foreground
- chosen target is selected if detections exist
- `planned_cursor_screen_px` is written
- `move_executed = false`
- cursor does not move

During `--start-delay-sec`, press Ctrl+C to abort before capture or any movement gate.

## Execute-Move Command

Before running this command, set `allow_mouse_move` to `true` in `config/phase7-cursor-positioning.json`.

```powershell
Start-Sleep -Seconds 5; .\.venv\Scripts\python.exe scripts\live_direct_cursor_position.py `
  --model runs\detect\phase3_yolo11n_baseline\weights\best.pt `
  --conf 0.25 `
  --start-delay-sec 3 `
  --execute-move `
  --confirm-local-aimlab-only `
  --overwrite
```

Expected execute result:

- one frame processed
- chosen target exists
- `cursor_before_screen_px` exists
- `planned_cursor_screen_px` exists
- exactly one `SetCursorPos` cursor movement is attempted
- `cursor_after_screen_px` exists if movement succeeds
- `move_executed = true` if all gates pass
- no click occurs
- program exits after the one-shot attempt

Emergency stop for this one-shot phase is Ctrl+C during `--start-delay-sec`, before the single movement attempt. There is no persistent control loop after the command exits.

## Target Selection

Default target selection:

```text
nearest_to_cursor
```

Supported strategies:

- `nearest_to_cursor`
- `highest_conf`
- `nearest_to_screen_center`

The default strategy selects the detection whose planned screen position is closest to the current cursor position.

## Outputs

Each run creates a run-id directory under:

```text
runs/phase7_direct_cursor_positioning/
```

Files:

- `frame.png`
- `review_image.png`
- `detections.json`
- `chosen_target.json`
- `phase7_summary.json`
- `run_config.json`
- `summary.csv`

Review image marks:

- all detections
- chosen target
- chosen center point
- planned cursor point

It does not draw click effects, continuous trajectories, target lock, or auto-aim indicators.

## Acceptance Steps

1. Run dry-run while AIMLAB is not foreground.
   - expected: `blocked=true`, `move_executed=false`

2. Run dry-run while AIMLAB is foreground.
   - expected: one frame, detections if visible, chosen target, planned cursor position, `move_executed=false`

3. Enable config `allow_mouse_move=true`.

4. Run execute-move while AIMLAB is foreground using both required CLI flags.
   - expected: one frame, chosen target, `move_executed=true`
   - expected: `cursor_after_screen_px` is within 2 px of `planned_cursor_screen_px`

5. Confirm the script exits after one attempt.

## Phase Boundary

Phase 7 forbids:

- clicking
- click target output
- continuous loop movement
- target lock
- auto-aim loop
- move-detect-move correction
- closed-loop automation
- anti-cheat bypass
- process memory reading
- process injection
- AIMLAB file modification
- background automation

Phase 7 does not implement Phase 8.
