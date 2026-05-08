# Phase 9 Report - One-Shot Click Gate

## Implementation Status

Phase 9 accepted. Windows + AIMLAB real-machine validation passed.

The accepted run executed one `SendInput` relative move and one gated left click after the click gate passed.

## Goal

Phase 9 adds a strictly gated one-shot click decision after the Phase 8.1 / Phase 8.2 FOV one-shot relative aim flow.

Implemented flow:

```text
one before detection -> one FOV relative move -> one after detection -> optional one gated click -> exit
```

## Files Added / Updated

Added:

- `scripts/live_one_shot_click_gate.py`
- `tests/test_phase9_click_gate.py`
- `docs/runbooks/phase-9-one-shot-click-gate-runbook.md`
- `docs/phase-reports/phase-9-report.md`

Updated:

- `README.md`
- `docs/phase-roadmap.md`

## Implementation Summary

The Phase 9 script reuses Phase 8.1 logic instead of duplicating the FOV aim implementation:

- AIMLAB foreground gate from Phase 8.1.
- Monitor screenshot capture from Phase 8.1.
- YOLO loading and detection conversion from Phase 8.1.
- nearest-to-crosshair target selection from Phase 8.1.
- FOV relative move calculation through `src/aiaim_control/fov_aim_model.py`.
- Review image drawing from Phase 8.1.
- Relative movement through Phase 8.1 `SendInput` relative move helper.

Phase 9 adds:

- click gate checks
- one guarded `SendInput` left down/up helper
- `phase9_result.json`
- `phase9_summary.csv`
- post-click screenshot audit when click executes

## Safety Boundary

Phase 9 defaults to no movement and no click.

Real movement requires:

- `--execute-move`
- `--confirm-local-aimlab-only`
- AIMLAB foreground gate
- before target exists
- valid rounded relative move

Real click additionally requires:

- `--allow-click`
- AIMLAB foreground before capture
- AIMLAB foreground before move
- AIMLAB foreground before click
- after detection exists
- `after_distance_to_crosshair_px <= click_threshold_px`
- no prior click in this run

Phase 9 does not implement:

- repeated clicking
- finite repeat runner
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

## Output Contract

`phase9_result.json` records:

- foreground gate fields
- expected resolution and screenshot size
- FOV parameters
- before detections and chosen target
- before distance and pixel delta
- angle delta and rounded relative move
- move execution fields
- after-move detections and after distance
- click threshold and click gate fields
- click attempted / executed fields
- blocked reason and errors

When `--allow-click` is missing, the run is treated as a normal move-only audit. It must write `click_gate_passed=false`, `click_attempted=false`, `click_executed=false`, and `blocked_reason=allow_click_false` when no earlier denial reason exists.

## Validation Performed

Commands run in the current WSL/Linux Codex shell:

```bash
PYTHONPYCACHEPREFIX=/tmp/aiaim_phase9_pycache python3 -m compileall scripts src tests
PYTHONPATH=src python3 scripts/live_one_shot_click_gate.py --help
PYTHONPATH=src python3 -m pytest tests/test_phase8_1_fov_aim_model.py tests/test_phase9_click_gate.py
./.venv/Scripts/python.exe -m pytest tests/test_phase8_1_fov_aim_model.py tests/test_phase9_click_gate.py
PYTHONPATH=src:scripts python3 -c "direct Phase 9 gate / AST checks"
PYTHONPATH=src python3 scripts/live_one_shot_click_gate.py --start-delay-sec 0 --run-id wsl_phase9_dry_run_blocked --overwrite --output-dir /tmp/aiaim_phase9_runs
rg -n "SetCursorPos|mouse_event|pyautogui|pynput|keyboard|ReadProcessMemory|OpenProcess|WriteProcessMemory|while " scripts/live_one_shot_click_gate.py src/aiaim_control scripts/live_one_shot_fov_aim.py
```

Results:

- `compileall` passed with pycache redirected to `/tmp/aiaim_phase9_pycache`.
- `scripts/live_one_shot_click_gate.py --help` passed.
- System Python pytest could not run because the current WSL Python has no `pytest` module.
- Windows `.venv` pytest could not run from WSL due a WSL socket binding error.
- Direct Python Phase 9 gate checks passed: required explicit move/click/confirm flags, distance threshold rejection, double-click rejection, Phase 8.1 reuse, and no AST `while` loop.
- WSL dry-run blocked safely at foreground gate and wrote `/tmp/aiaim_phase9_runs/wsl_phase9_dry_run_blocked/phase9_result.json` with `relative_aim_executed=false`, `click_gate_passed=false`, and `click_executed=false`.
- Static safety scan found no `SetCursorPos`, `mouse_event`, `pyautogui`, `pynput`, `keyboard`, process-memory API tokens, or `while` loop in the Phase 9 / Phase 8.1 control paths scanned.

Safety checks confirmed:

- no `SetCursorPos` aiming path added
- no loop / continuous control added
- no hotkey runner added
- no AIMLAB process memory read added
- no AIMLAB file modification added
- real click requires `--execute-move`, `--allow-click`, and `--confirm-local-aimlab-only`

## Real-machine Acceptance Status

Status: Phase 9 accepted.

One-Shot Click Gate Windows real-machine validation passed.

Accepted run:

```text
phase=9
mode=one_shot_click_gate
blocked=False
blocked_reason=None
relative_aim_executed=True
click_gate_passed=True
click_executed=True
run_dir=D:\桌面desktop\AIAIM\runs\detect\phase9_one_shot_click_gate\20260507_202455
```

Validation conclusion:

- Phase 9 accepted.
- One-Shot Click Gate Windows real-machine validation passed.
- One `SendInput` relative move was executed.
- One left click was executed after the click gate passed.
- No loop was implemented or executed.
- No second correction was implemented or executed.
- No target lock was implemented.
- No PID was implemented.
- No Hotkey Runner was implemented.
- No background automation was implemented.
- No AIMLAB process memory was read.
- No AIMLAB files were modified.
- No anti-cheat bypass was implemented.

## Next Phase Recommendation

Phase 9.5 or Phase 10 should only be considered after several Phase 9 real-machine validations show:

- correct after-distance gate behavior
- zero false clicks
- foreground-loss refusal works
- missing `--allow-click` never clicks

Do not extend Phase 9 into closed-loop correction, target lock, repeated clicking, or a hotkey runner without a separate phase and safety review.
