# Phase 9 One-Shot Click Gate Runbook

## Goal

Phase 9 adds a strictly gated single-click decision after the accepted Phase 8.1 / Phase 8.2 FOV one-shot relative aim flow.

The flow is intentionally one-shot:

```text
one detection -> one FOV relative move -> one after screenshot -> optional one click if gate passes -> exit
```

## Non-goals

Phase 9 does not implement:

- automatic clicking by default
- repeated clicking
- finite repeat runs
- hotkey runner
- app mode
- target lock
- PID
- second correction
- closed-loop movement
- smooth movement
- background automation
- AIMLAB process memory reading
- AIMLAB file modification
- anti-cheat bypass

## Safety Boundary

Movement and click are both disabled by default.

A real relative move requires:

- `--execute-move`
- `--confirm-local-aimlab-only`
- AIMLAB foreground gate
- a valid before detection
- a valid FOV relative move within configured limits

A real click additionally requires:

- `--allow-click`
- AIMLAB foreground before capture
- AIMLAB foreground before move
- AIMLAB foreground before click
- after-move detection exists
- `after_distance_to_crosshair_px <= click_threshold_px`
- no click has already occurred in this run

If any click gate check fails, Phase 9 writes the denial reason and exits without clicking.

## Parameters

Key parameters:

- `--model`: YOLO checkpoint path.
- `--conf`: YOLO confidence threshold, default `0.25`.
- `--output-dir`: output root, default `runs/detect/phase9_one_shot_click_gate`.
- `--execute-move`: permits the one relative `SendInput` movement.
- `--allow-click`: permits the click gate to execute one click if all checks pass.
- `--confirm-local-aimlab-only`: explicit local AIMLAB confirmation required for real move/click.
- `--click-threshold-px`: after-move max distance for click gate, default `8`.
- `--after-move-wait-ms`: wait before after screenshot, default `100`.
- `--click-down-up-delay-ms`: left down/up delay, default `50`.
- `--horizontal-fov-deg`: default `103`.
- `--vertical-fov-deg`: default `70.53`.
- `--counts-per-degree`: default `39.03`.
- `--global-gain`: default `1.0`.

## Dry-run: No Move, No Click

```powershell
.\.venv\Scripts\python.exe scripts\live_one_shot_click_gate.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --conf 0.25 `
  --click-threshold-px 8 `
  --output-dir "D:\桌面desktop\AIAIM\runs\detect\phase9_one_shot_click_gate"
```

Expected: no `SendInput` move and no click.

## Execute Move, No Click

```powershell
.\.venv\Scripts\python.exe scripts\live_one_shot_click_gate.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --conf 0.25 `
  --execute-move `
  --confirm-local-aimlab-only `
  --click-threshold-px 8 `
  --output-dir "D:\桌面desktop\AIAIM\runs\detect\phase9_one_shot_click_gate"
```

Expected: one relative move, after screenshot validation, no click. `blocked_reason` should normally be `allow_click_false`.

## Execute Move + Allow One Click

```powershell
.\.venv\Scripts\python.exe scripts\live_one_shot_click_gate.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --conf 0.25 `
  --execute-move `
  --allow-click `
  --confirm-local-aimlab-only `
  --click-threshold-px 8 `
  --after-move-wait-ms 100 `
  --click-down-up-delay-ms 50 `
  --output-dir "D:\桌面desktop\AIAIM\runs\detect\phase9_one_shot_click_gate"
```

Expected: one relative move, after screenshot validation, one left click only if the click gate passes, then exit.

## Outputs

Each run writes under:

```text
runs/detect/phase9_one_shot_click_gate/<run_id>/
```

Files:

- `before.png`
- `before_detection.json`
- `before_review.png`
- `after_move.png` when movement executes
- `after_move_detection.json` when after validation runs
- `after_move_review.png` when after validation runs
- `post_click.png` when click executes
- `phase9_result.json`
- `phase9_summary.csv`
- `run_config.json`

## Common blocked_reason Values

- `aimlab_not_foreground_before_capture`: AIMLAB was not foreground at initial gate.
- `aimlab_not_foreground_before_move`: AIMLAB lost foreground before movement.
- `aimlab_not_foreground_before_click`: AIMLAB lost foreground before click.
- `no_detection_before`: no YOLO target before movement.
- `execute_move_false`: normal dry-run / no real movement requested.
- `confirm_local_aimlab_only_false`: real action confirmation missing.
- `allow_click_false`: move-only audit; click disabled.
- `no_detection_after_move`: after-move validation found no target.
- `after_distance_above_threshold`: target is too far from crosshair for click.
- `already_clicked_once`: second click is refused.
- `sendinput_move_failed`: Windows relative move call failed.
- `sendinput_click_failed`: Windows click call failed.

## Acceptance Criteria

Minimum acceptance:

- AIMLAB foreground gate is true.
- Before screenshot succeeds.
- Before detection succeeds.
- FOV relative move calculation succeeds.
- One relative `SendInput` movement executes when explicitly enabled.
- After screenshot succeeds.
- After detection succeeds.
- `after_distance_to_crosshair_px <= 8`.
- With `--allow-click`, `click_gate_passed=true` and `click_executed=true`.
- The run performs at most one movement and at most one click.
- No loop, no second correction, no PID, no target lock, and no hotkey runner.
- `phase9_result.json`, `run_config.json`, review images, and summary CSV are written.

Recommended acceptance:

- 3 to 5 different yellow target positions.
- `click_executed_count >= 3`.
- `false_click_count = 0`.
- Missing `--allow-click` must never click.
- Distance above threshold must never click.
- Foreground loss must never click.
