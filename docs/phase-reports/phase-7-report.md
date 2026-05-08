# Phase 7 Report - Direct Cursor Positioning

## Phase Goal

Implement one-shot direct cursor positioning for local offline AIMLAB.

Phase 7 detects yellow balls from the current AIMLAB foreground monitor screenshot, chooses one target, computes a planned Windows screen cursor position from `center_monitor_px`, and optionally moves the cursor once using Windows `SetCursorPos` when all gates pass.

## Scope

Allowed:

- AIMLAB foreground gate.
- Full-monitor screenshot capture.
- YOLO detection with the Phase 3 `best.pt` model.
- Primary target selection.
- Dry-run planned cursor position.
- One-shot direct cursor movement only when explicitly enabled.
- Structured output JSON and review image.

Forbidden:

- clicking
- auto-aim loop
- target lock
- closed-loop control
- move-detect-move correction
- process memory reading
- process injection
- AIMLAB file modification
- anti-cheat bypass
- background automation

## Added Or Modified Files

Added:

- `scripts/live_direct_cursor_position.py`
- `config/phase7-cursor-positioning.json`
- `docs/runbooks/phase-7-direct-cursor-positioning-runbook.md`
- `docs/phase-reports/phase-7-report.md`

Modified:

- `README.md`
- `docs/phase-roadmap.md`
- `docs/safety-boundary.md`

## Implementation Summary

`scripts/live_direct_cursor_position.py`:

- reads `config/phase7-cursor-positioning.json`
- waits `--start-delay-sec`
- can be aborted with Ctrl+C during `--start-delay-sec` before capture or the one-shot movement attempt
- checks AIMLAB foreground status
- captures one monitor frame
- runs YOLO once
- selects a primary target
- computes `planned_cursor_screen_px`
- blocks real movement by default
- requires config `allow_mouse_move=true`
- requires CLI `--execute-move`
- requires CLI `--confirm-local-aimlab-only`
- attempts exactly one Windows `SetCursorPos` only when all gates pass
- writes `detections.json`
- writes `chosen_target.json`
- writes `phase7_summary.json`
- writes `run_config.json`
- writes `summary.csv`
- optionally writes `review_image.png`

There is no continuous movement loop.

## Coordinate Contract

Phase 7 uses the Phase 5.5 / Phase 6 coordinate contract:

- YOLO center is read as `center_monitor_px` under full-monitor capture.
- Windows screen position is computed as:
  - `cursor_screen_x = monitor_rect.left + center_monitor_px.x`
  - `cursor_screen_y = monitor_rect.top + center_monitor_px.y`
- raw `window_rect` remains debug / warning information only.
- `window_relative` is not used as an action coordinate.

## Target Selection

Default:

```text
nearest_to_cursor
```

Supported:

- `nearest_to_cursor`
- `highest_conf`
- `nearest_to_screen_center`

## Safety Gates

Real movement requires all of these:

- config `allow_mouse_move = true`
- CLI `--execute-move`
- CLI `--confirm-local-aimlab-only`
- AIMLAB foreground gate passed
- chosen target exists
- chosen `center_monitor_px` is inside the captured monitor image
- planned cursor position is inside `monitor_rect`
- config `allow_click = false`
- config `allow_loop = false`
- config `allow_closed_loop = false`

Default behavior is dry-run:

- config `allow_mouse_move = false`
- `move_executed = false`
- planned cursor position is written when available
- cursor is not moved

## Output Directory

Default root:

```text
runs/phase7_direct_cursor_positioning/
```

Each run creates a run-id subdirectory containing:

- `frame.png`
- `review_image.png`
- `detections.json`
- `chosen_target.json`
- `phase7_summary.json`
- `run_config.json`
- `summary.csv`

## Validation Performed

Static checks:

```bash
python3 -m py_compile scripts/live_direct_cursor_position.py
python3 scripts/live_direct_cursor_position.py --help
python3 -m json.tool config/phase7-cursor-positioning.json
```

WSL dry-run blocked check:

```bash
python3 scripts/live_direct_cursor_position.py --start-delay-sec 0 --run-id wsl_dry_run_blocked --overwrite
```

Observed WSL result:

- phase = phase7_direct_cursor_positioning
- mode = dry-run
- frames_processed = 1
- blocked = true
- detections_count = 0
- chosen_detection_index = None
- move_executed = false
- output = `runs/phase7_direct_cursor_positioning/wsl_dry_run_blocked`

This WSL result is expected because the Windows foreground and cursor APIs are unavailable from the current shell. Windows + AIMLAB validation is still required for real dry-run and execute-move acceptance.

## Required Windows + AIMLAB Acceptance

Dry-run AIMLAB non-foreground:

- expected: `blocked=true`
- expected: `move_executed=false`
- expected: no cursor movement

Dry-run AIMLAB foreground:

- expected: `frames_processed=1`
- expected: `detections_count >= 1`
- expected: chosen target exists
- expected: `planned_cursor_screen_px` exists
- expected: `move_executed=false`
- expected: cursor position unchanged

Execute-move AIMLAB foreground:

- set config `allow_mouse_move=true`
- pass `--execute-move`
- pass `--confirm-local-aimlab-only`
- expected: `frames_processed=1`
- expected: `detections_count >= 1`
- expected: chosen target exists
- expected: `move_executed=true`
- expected: `cursor_before_screen_px`, `cursor_screen_px`, `planned_cursor_screen_px`, and `cursor_after_screen_px` exist
- expected: `cursor_after_screen_px` is within 2 px of `planned_cursor_screen_px`

## Explicit Non-Goals

Phase 7 did not implement clicking.

Phase 7 did not implement click targets.

Phase 7 did not implement an auto-aim loop.

Phase 7 did not implement target lock.

Phase 7 did not implement closed-loop automation.

Phase 7 did not implement move-detect-move correction.

Phase 7 did not implement anti-cheat bypass.

Phase 7 did not read process memory.

Phase 7 did not inject into AIMLAB.

Phase 7 did not modify AIMLAB files.

Phase 7 did not implement background automation.

## Known Risks

- Cursor positioning must be validated on Windows with AIMLAB foreground before acceptance.
- False positives could move the cursor to a wrong yellow UI element if execute mode is enabled.
- Emergency stop for this one-shot phase is Ctrl+C during `--start-delay-sec`; after the single movement attempt there is no persistent loop to stop.
- Phase 7 must not be expanded into a control loop without a separate later-phase design.

## Next Phase Suggestion

Do not proceed to clicking.

The next appropriate work is Windows + AIMLAB Phase 7 acceptance logging. Any later click-related phase requires a separate safety design, explicit config, dry-run default, emergency stop, and report.
