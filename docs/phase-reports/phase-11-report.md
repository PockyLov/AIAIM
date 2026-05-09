# Phase 11 Report - Console Hotkey Runner

## Status

Implemented. Windows + AIMLAB real-machine acceptance is pending.

## Goal

Phase 11 adds a visible console hotkey runner for launching and stopping one finite Phase 10 run. It removes the need to manually type the long Phase 10 PowerShell command for each run.

## Work Completed

- Added `scripts/phase11_hotkey_runner.py`.
- Added `configs/phase11_hotkey_runner.json` with Phase 10 pressure-test preset values and safety caps.
- Added `run_phase11_hotkey_runner.bat` as a visible console launcher.
- Added Phase 10 `--stop-file` support so the runner can request safe child shutdown at loop boundaries.
- Added Phase 11 mock tests.
- Added this phase report and the Phase 11 runbook.
- Updated README with a concise Phase 11 section.

## Phase 10 Core Logic

Phase 10 detection, FOV movement calculation, after validation, retry policy, click guard, and SendInput move/click logic were not changed. The only Phase 10 compatibility change is `--stop-file`, checked at safe loop boundaries.

## Safety Boundary

Phase 11 keeps Phase 10 gates intact:

- Phase 10 child still requires `--execute-move`, `--allow-click`, and `--confirm-local-aimlab-only`.
- AIMLAB foreground is checked before starting the child process.
- Phase 10 continues checking foreground during every iteration.
- Safety caps prevent config from exceeding the accepted pressure-test limits.
- Stop is a soft stop-file request, not a mid-action interrupt.

Phase 11 does not implement GUI, tray, background service, infinite loop, PID, target lock, smoothing, second correction, AIMLAB memory reading, AIMLAB file modification, or anti-cheat bypass.

## Files Changed

- `scripts/live_finite_repeat_aim_click.py`
- `scripts/phase11_hotkey_runner.py`
- `configs/phase11_hotkey_runner.json`
- `run_phase11_hotkey_runner.bat`
- `tests/test_phase11_hotkey_runner.py`
- `docs/runbooks/phase-11-hotkey-runner-runbook.md`
- `docs/phase-reports/phase-11-report.md`
- `README.md`

## Validation

Commands run from the project Windows venv path under WSL:

```bash
/mnt/d/桌面desktop/AIAIM/.venv/Scripts/python.exe -m compileall scripts tests
/mnt/d/桌面desktop/AIAIM/.venv/Scripts/python.exe scripts/phase11_hotkey_runner.py --help
/mnt/d/桌面desktop/AIAIM/.venv/Scripts/python.exe scripts/live_finite_repeat_aim_click.py --help
/mnt/d/桌面desktop/AIAIM/.venv/Scripts/python.exe -m pytest tests/test_phase11_hotkey_runner.py tests/test_phase10_finite_repeat_aim_click.py -q
```

Results:

- `compileall` passed for `scripts` and `tests`.
- Phase 11 `--help` passed.
- Phase 10 `--help` passed and shows `--stop-file`.
- Targeted pytest did not run because the Windows venv does not currently have `pytest` installed (`No module named pytest`).
- Manual no-action assertions passed for Arm/Start/Stop state transitions, stop-file creation, safety-cap blocking, and Phase 10 stop-file detection.
- Static scan found no process-memory API, AIMLAB file modification path, `SetCursorPos`, `mouse_event`, or pyautogui usage in the Phase 11 runner / Phase 10 patch.

No real `--execute-move` or `--allow-click` run was performed by Codex.

## Remaining Risk

Real hotkey behavior depends on Windows console focus, OS-level keyboard hook permissions, and the installed `pynput` dependency. If hotkeys do not fire, run the runner from an elevated or normally focused terminal and verify `.venv` dependencies.

## Next Step

User should perform Windows + AIMLAB manual acceptance:

1. Start `run_phase11_hotkey_runner.bat`.
2. Press Arm then Start.
3. Confirm one Phase 10 child starts.
4. Press Stop and verify `stop_reason=user_stop_requested` in the child Phase 10 summary.

Do not enter Phase 12 until Phase 11 hotkey control is validated.
