# Phase 7.5 Report - One-Shot Relative Mouse Actuation Feasibility

## Phase Goal

Verify whether AIMLAB responds to one fixed relative mouse movement and estimate the resulting screen target shift from before / after YOLO detections.

Phase 7.5 is a feasibility test. It is not auto-aim and does not try to move the crosshair onto a yellow ball.

## Background

Phase 7 direct cursor positioning used Windows `SetCursorPos` and reached the movement code path:

- blocked = false
- frames_processed = 1
- detections_count = 7
- chosen_detection_index = 2
- move_gate.allowed_to_move = true
- move_executed = true
- cursor_before_screen_px = `{"x": 959, "y": 526}`
- planned_cursor_screen_px = `{"x": 1039.6901, "y": 498.7671}`
- cursor_after_screen_px = `{"x": 959, "y": 527}`

Conclusion: `SetCursorPos` executed, but AIMLAB gameplay kept the cursor near the center. Direct cursor positioning is not suitable as the AIMLAB gameplay actuation method.

## Added Or Modified Files

Added:

- `scripts/live_relative_mouse_feasibility.py`
- `config/phase75-relative-mouse-feasibility.json`
- `docs/runbooks/phase-75-relative-mouse-feasibility-runbook.md`
- `docs/phase-reports/phase-75-report.md`

Modified:

- `README.md`
- `docs/phase-roadmap.md`
- `docs/safety-boundary.md`

## Implementation Summary

`scripts/live_relative_mouse_feasibility.py`:

- reads Phase 7.5 config
- waits `--start-delay-sec`
- checks AIMLAB foreground gate
- captures one before frame
- runs YOLO on before frame
- selects a reference target by nearest-to-crosshair
- records before reference center and delta to crosshair
- records planned relative move
- blocks real movement by default
- sends exactly one `SendInput` relative mouse movement only when all gates pass
- waits `settle_sec`
- captures one after frame if movement executed
- runs YOLO on after frame
- tries conservative before/after target matching
- computes observed screen shift if matched
- computes `px_per_mouse_count_x` / `px_per_mouse_count_y` when possible
- writes JSON, CSV, and review images

There is no loop, no second movement, and no closed-loop correction.

## Safety Gates

Real relative movement requires:

- config `allow_relative_mouse_move = true`
- CLI `--execute-relative-move`
- CLI `--confirm-local-aimlab-only`
- AIMLAB foreground gate passed
- config `allow_click = false`
- config `allow_loop = false`
- config `allow_closed_loop = false`
- `relative_dx` / `relative_dy` within configured max absolute limits
- before reference target exists

Default config keeps movement disabled.

## Coordinate Contract

Phase 7.5 uses monitor-relative coordinates:

- crosshair center is `monitor_rect` center
- before reference target is selected by nearest-to-crosshair
- observed shift is computed as after matched center minus before reference center
- `px_per_mouse_count_x = observed_shift.dx / relative_dx` when `relative_dx != 0`
- `px_per_mouse_count_y = observed_shift.dy / relative_dy` when `relative_dy != 0`

This is calibration evidence only. It is not used to aim in Phase 7.5.

## Outputs

Default root:

```text
runs/phase75_relative_mouse_feasibility/
```

Each run writes:

- `before_frame.png`
- `after_frame.png` if movement executes
- `before_review_image.png`
- `after_review_image.png` if after frame exists
- `before_detections.json`
- `after_detections.json` if after frame exists or movement was attempted
- `relative_move_event.json`
- `phase75_summary.json`
- `run_config.json`
- `summary.csv`

## Validation Performed

Static checks:

```bash
python3 -m py_compile scripts/live_relative_mouse_feasibility.py
python3 scripts/live_relative_mouse_feasibility.py --help
python3 -m json.tool config/phase75-relative-mouse-feasibility.json
```

WSL dry-run blocked check:

```bash
python3 scripts/live_relative_mouse_feasibility.py --start-delay-sec 0 --run-id wsl_dry_run_blocked --overwrite
```

Observed WSL result:

- phase = phase75_relative_mouse_feasibility
- mode = dry-run
- blocked = true
- frames_processed = 1
- before_detections_count = 0
- after_detections_count = 0
- relative_move_executed = false
- sendinput_attempted = false
- match_status = not_attempted_dry_run
- calibration_status = dry_run_no_after_frame
- output = `runs/phase75_relative_mouse_feasibility/wsl_dry_run_blocked`

This is expected because Windows foreground and input APIs are unavailable from WSL. Windows + AIMLAB acceptance has now been completed on the Windows desktop environment.

## Windows + AIMLAB Acceptance Result

Phase 7.5 accepted.

Windows real-machine validation confirms that the AIMLAB gameplay scene responds to Windows `SendInput` relative mouse movement.

### dx=100 Acceptance

- blocked = false
- frames_processed = 2
- before_detections_count = 6
- after_detections_count = 7
- relative_move_executed = true
- sendinput_attempted = true
- match_status = matched
- calibration_status = matched
- observed_screen_shift_px = `{"dx": -36.0487, "dy": 0.4371}`
- px_per_mouse_count_x = -0.3605

### dy=100 Acceptance

- blocked = false
- frames_processed = 2
- before_detections_count = 6
- after_detections_count = 7
- relative_move_executed = true
- sendinput_attempted = true
- match_status = matched
- calibration_status = matched
- observed_screen_shift_px = `{"dx": 0.166, "dy": -30.2367}`
- px_per_mouse_count_y = -0.3024

### Acceptance Interpretation

Phase 7.5 validates the intended feasibility question: AIMLAB gameplay responds to `SendInput` relative mouse movement, and the before / after detections can be matched well enough to estimate screen response.

Phase 7 `SetCursorPos` direct cursor positioning is not suitable as the AIMLAB in-game actuation method. It can execute at the Windows cursor API level, but AIMLAB gameplay does not use that direct absolute cursor position as the aiming input. Relative `SendInput` movement is the appropriate actuation basis for later discussion.

## Explicit Non-Goals

Phase 7.5 did not implement clicking.

Phase 7.5 did not implement automatic aiming.

Phase 7.5 did not implement target lock.

Phase 7.5 did not implement looped movement.

Phase 7.5 did not implement closed-loop correction.

Phase 7.5 did not implement a second movement after after-frame detection.

Phase 7.5 did not implement anti-cheat bypass.

Phase 7.5 did not read process memory.

Phase 7.5 did not implement process-memory automation or target-program inspection.

Phase 7.5 did not inject into AIMLAB.

Phase 7.5 did not modify AIMLAB files.

Phase 7.5 did not implement background automation.

## Known Risks

- Matching before and after targets may be ambiguous when multiple yellow balls are visible.
- A visible shift may require manual review even if automatic matching is uncertain.
- Relative mouse sensitivity may depend on AIMLAB and Windows settings.
- `px_per_mouse_count` from one sample is only a first estimate.

## Next Phase Suggestion

Do not proceed to clicking.

After Windows Phase 7.5 acceptance, Phase 8 can discuss One-Shot Relative Aim to Target using measured `px_per_mouse_count`. Phase 8 must still be gated, one-shot first, and must not become target lock, looped movement, closed-loop auto-aim, or clicking without a separate explicit safety design.
