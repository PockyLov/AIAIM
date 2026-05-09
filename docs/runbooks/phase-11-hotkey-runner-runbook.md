# Phase 11 Hotkey Runner Runbook

## Goal

Phase 11 provides a visible console runner for starting and stopping one finite Phase 10 run with hotkeys. It is a control layer only. It does not change Phase 10 detection, FOV aiming, retry, click gate, or logging logic.

## Not Implemented

Phase 11 is not a GUI, tray app, background service, infinite loop, PID controller, target lock, smoothing system, second-correction loop, AIMLAB memory reader, AIMLAB file modifier, or anti-cheat bypass.

## Hotkeys

- `Ctrl+Alt+F8`: Arm
- `Ctrl+Alt+F9`: Start one finite Phase 10 run
- `Ctrl+Alt+F10`: Request stop through the Phase 10 stop file
- `Ctrl+C`: Exit the visible runner console

Start only works after Arm. Arm expires after 5 seconds by default. Pressing Start while a child Phase 10 process is already running is ignored.

## Safety Model

The runner enforces Phase 10 caps before launching the child process:

- `max_iterations <= 300`
- `max_duration_sec <= 120`
- `max_loop_iterations <= 2000`
- `max_retries_per_target <= 2`
- `max_total_retry_attempts <= 100`
- `max_no_detection_timeouts <= 200`
- `max_consecutive_no_detection_timeouts <= 30`

The child command must still include Phase 10's explicit action flags:

- `--execute-move`
- `--allow-click`
- `--confirm-local-aimlab-only`

The runner also checks the AIMLAB foreground gate before starting the child process. Phase 10 performs its own foreground checks every iteration.

## Start Runner

```powershell
.\run_phase11_hotkey_runner.bat
```

Equivalent direct command:

```powershell
.\.venv\Scripts\python.exe scripts\phase11_hotkey_runner.py --config configs\phase11_hotkey_runner.json
```

Keep the console visible. This is not intended to run hidden in the background.

## Stop Behavior

`Ctrl+Alt+F10` creates:

```text
runs\detect\phase11_hotkey_runner\<runner_run_id>\stop_requested.json
```

Phase 10 checks this file at loop boundaries and exits safely with:

```text
stop_reason=user_stop_requested
```

The runner does not interrupt a move or click in the middle of the action.

## Output Files

Each runner session writes:

```text
runs/detect/phase11_hotkey_runner/<run_id>/
  runner_config.json
  runner_summary.json
  runner_events.jsonl
  command_preview.txt
  stop_requested.json        # only after user stop
```

Phase 10 child outputs are written under:

```text
runs/detect/phase11_hotkey_runner/phase10_child_runs/
```

## Common Blocked Reasons

- `not_armed_or_arm_expired`: Start was pressed without a fresh Arm.
- `safety_cap_exceeded:<name>`: config exceeded a Phase 11 safety cap.
- `missing_required_action_flag:<name>`: config omitted a required Phase 10 real-action flag.
- `aimlab_not_foreground`: AIMLAB was not foreground when Start was requested.
- `runner_error:<type>:<message>`: runner-level failure, usually dependency or environment related.

## Acceptance Steps

1. Start AIMLAB fullscreen / borderless fullscreen and make it foreground.
2. Run `run_phase11_hotkey_runner.bat` in a visible console.
3. Press `Ctrl+Alt+F8`; console should show `State: ARMED`.
4. Within 5 seconds, press `Ctrl+Alt+F9`; console should show `State: RUNNING`.
5. Optionally press `Ctrl+Alt+F10`; Phase 10 should stop through `--stop-file`.
6. Inspect `runner_summary.json`, `runner_events.jsonl`, and the child Phase 10 summary.

Do not run hidden. Do not use this outside the local offline AIMLAB test environment.
