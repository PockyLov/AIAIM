# Phase 6 Report - Live Read-Only Detection Pipeline

## Phase Goal

Implement live read-only detection for AIMLAB while AIMLAB is foreground in windowed fullscreen / borderless fullscreen mode.

Phase 6 only answers: where does the detector currently see yellow balls in the live captured monitor image?

It does not implement mouse movement, clicking, auto-aim, target lock, closed-loop control, or anti-cheat bypass.

## Inputs

- Phase 1 collector modules for AIMLAB window detection, foreground gate, monitor detection, and full-monitor screenshot capture.
- Phase 3 model checkpoint: `runs/detect/phase3_yolo11n_baseline/weights/best.pt`.
- Phase 5.5 coordinate contract: `image_pixel` and `monitor_relative` are the read-only coordinate basis; raw `window_rect` is debug / warning information only.

## Added Or Modified Files

Added:

- `scripts/live_readonly_detect.py`
- `docs/runbooks/phase-6-live-readonly-detection-runbook.md`
- `docs/phase-reports/phase-6-report.md`

Modified:

- `README.md`
- `docs/phase-roadmap.md`
- `docs/safety-boundary.md`

## Implementation Summary

`scripts/live_readonly_detect.py`:

- supports `--mode single`
- supports `--mode loop`
- uses a finite loop with `for frame_index in range(max_frames)`
- reuses Phase 1 window / foreground / monitor / screenshot modules
- lazily loads the YOLO model only when the foreground gate passes
- blocks cleanly if AIMLAB is missing or not foreground
- writes per-frame JSON to `json/`
- writes optional clean review images to `review_images/`
- writes captured monitor frames to `captured_frames/`
- writes `live_summary.csv`
- writes `phase6_summary.json`
- writes `run_config.json`

## Output Directory

Default output:

```text
runs/detect/phase6_live_readonly/
```

Local WSL blocked-gate validation output:

```text
runs/detect/phase6_live_readonly_wsl_blocked/
```

## Commands

Single-frame Windows command:

```powershell
.\.venv\Scripts\python.exe scripts\live_readonly_detect.py `
  --mode single `
  --model runs\detect\phase3_yolo11n_baseline\weights\best.pt `
  --output-dir runs\detect\phase6_live_readonly `
  --conf 0.25 `
  --review-images `
  --overwrite
```

Finite-loop Windows command:

```powershell
.\.venv\Scripts\python.exe scripts\live_readonly_detect.py `
  --mode loop `
  --max-frames 30 `
  --interval-sec 0.5 `
  --model runs\detect\phase3_yolo11n_baseline\weights\best.pt `
  --output-dir runs\detect\phase6_live_readonly `
  --conf 0.25 `
  --review-images `
  --overwrite
```

Local syntax / help checks:

```bash
python3 -m py_compile scripts/live_readonly_detect.py
python3 scripts/live_readonly_detect.py --help
```

Windows venv help check attempted from WSL:

```bash
.venv/Scripts/python.exe scripts/live_readonly_detect.py --help
```

Result: WSL could not launch the Windows venv Python from this shell and returned `UtilBindVsockAnyPort:307: socket failed 1`. This is an environment limitation of the current Codex shell, not a Phase 6 script error.

Local blocked-gate check in WSL:

```bash
python3 scripts/live_readonly_detect.py --mode single --output-dir runs/detect/phase6_live_readonly_wsl_blocked --overwrite
```

Local finite-loop blocked-gate check in WSL:

```bash
python3 scripts/live_readonly_detect.py --mode loop --max-frames 2 --interval-sec 0 --output-dir runs/detect/phase6_live_readonly_wsl_loop_blocked --overwrite
```

## Local Validation Result

The current Codex environment is WSL/Linux, not the Windows desktop session with AIMLAB. Therefore live Windows foreground capture could not be fully exercised here.

The WSL blocked-gate validation passed:

- frames_processed = 1
- blocked_frames = 1
- total_detections = 0
- `blocked_reason = foreground_gate_error:RuntimeError:Phase 1 collector requires Windows foreground-window APIs.`
- per-frame JSON was written
- `live_summary.csv` was written
- `phase6_summary.json` was written
- `run_config.json` was written
- no model was loaded because the gate blocked before detection
- no screenshot was taken

The WSL finite-loop blocked validation also passed:

- frames_requested = 2
- frames_processed = 2
- blocked_frame_count = 2
- total_detection_count = 0
- 2 per-frame JSON files were written
- `live_summary.csv` contains one header row plus two frame rows
- the finite loop exited automatically

This validates that blocked frames do not crash and do not emit detections. Full AIMLAB foreground validation must be run in the Windows desktop environment.

## Windows + AIMLAB Live Validation Result

Windows PowerShell + AIMLAB foreground windowed fullscreen validation has been completed.

### Single-Frame Windows Live Validation

Command:

```powershell
Start-Sleep -Seconds 5; .\.venv\Scripts\python.exe scripts\live_readonly_detect.py --mode single --output-dir runs\detect\phase6_live_readonly_windows_single --conf 0.25 --review-images --overwrite
```

Result:

- phase = phase6_live_readonly_detection
- mode = single
- frames_processed = 1
- blocked_frames = 0
- total_detection = 6
- output_dir = `runs\detect\phase6_live_readonly_windows_single`

### Finite-Loop 5-Frame Windows Live Validation

Command:

```powershell
Start-Sleep -Seconds 5; .\.venv\Scripts\python.exe scripts\live_readonly_detect.py --mode loop --max-frames 5 --interval-sec 0.5 --output-dir runs\detect\phase6_live_readonly_windows_loop5 --conf 0.25 --review-images --overwrite
```

Result:

- phase = phase6_live_readonly_detection
- mode = loop
- frames_processed = 5
- blocked_frames = 0
- total_detection = 32
- output_dir = `runs\detect\phase6_live_readonly_windows_loop5`

### Finite-Loop 30-Frame Windows Live Validation

Command:

```powershell
Start-Sleep -Seconds 5; .\.venv\Scripts\python.exe scripts\live_readonly_detect.py --mode loop --max-frames 30 --interval-sec 0.5 --output-dir runs\detect\phase6_live_readonly_windows_loop30 --conf 0.25 --review-images --overwrite
```

Result:

- phase = phase6_live_readonly_detection
- mode = loop
- frames_processed = 30
- blocked_frames = 0
- total_detection = 192
- output_dir = `runs\detect\phase6_live_readonly_windows_loop30`

### Human Review Result

Review images were inspected by the user. Detection boxes and center points are basically correct.

The AIMLAB foreground gate passed in all Windows live validation runs:

- single-frame: blocked_frames = 0
- 5-frame finite loop: blocked_frames = 0
- 30-frame finite loop: blocked_frames = 0

Single-frame and finite-loop modes both completed live read-only detection in the Windows + AIMLAB foreground environment.

The finite-loop mode used a bounded loop and exited automatically. No infinite control loop was used.

## Coordinate Contract

Every detection includes:

- `center_image_px`
- `center_monitor_px`
- `coordinate_space = "image_pixel_and_monitor_relative"`
- `is_screen_coordinate = false`
- `is_mouse_coordinate = false`
- `is_click_target = false`
- `action_authorized = false`

Phase 6 outputs detection coordinates only. They are not mouse targets and not click targets.

Direct cursor positioning is a later-phase discussion only and was not implemented in Phase 6.

Phase 6 outputs detection coordinates including `center_image_px` and `center_monitor_px`.

`center_monitor_px` is only a candidate coordinate basis for later Phase 7 direct cursor positioning discussion. It is not a mouse target in Phase 6.

Phase 6 still keeps:

- `is_mouse_coordinate = false`
- `is_click_target = false`
- `action_authorized = false`

Phase 6 does not output mouse targets, does not output click targets, and does not authorize any action.

## Safety Self-Check

The Phase 6 script does not import or call:

- `pyautogui`
- `pynput`
- `mouse_event`
- `SendInput`
- `keyboard`
- `moveTo`
- `press`

The word `click` appears only in safety fields such as `is_click_target=false` and `click_target_output=false`.

No infinite `while True` loop was implemented.

Note: the existing Phase 1 hotkey module still uses `pynput` for F8/F9/Esc capture control. Phase 6 does not import or use that module.

## Explicit Non-Goals

No mouse movement was implemented.

No mouse click was implemented.

No mouse target was output.

No click target was output.

No auto-aim was implemented.

No target lock was implemented.

No closed-loop automation was implemented.

No anti-cheat bypass was attempted.

No process memory was read.

No injection into AIMLAB was implemented.

No AIMLAB files were modified.

No Phase 7 implementation was started.

No direct cursor positioning was implemented.

No Phase 7 direct cursor positioning was implemented.

## Problems Encountered

The local Codex shell has `python3` but not `python`, and it does not have Pillow installed. The Phase 6 script was adjusted so `--help` and blocked-gate runs do not require Pillow; Pillow is imported only when review images are actually drawn.

The local environment is WSL/Linux, so Phase 1 Windows foreground APIs correctly block with a clear error. This is expected outside the Windows desktop session.

The Windows `.venv\Scripts\python.exe` exists, but launching it from this WSL shell failed with a WSL socket error. Windows + AIMLAB acceptance should be run directly from Windows PowerShell.

## Remaining Risks

- False positives may appear on live screenshots if yellow UI or lights differ from the training set.
- The negative sample count from Phase 3 remains limited.
- Phase 6 still must not be used as an action pipeline.
- Any future Phase 7 direct cursor positioning discussion must add a separate safety design and must not treat Phase 6 detections as authorized action targets.

## Decision

Phase 6 accepted after Windows live validation.

The code path has been locally checked for syntax, CLI help, blocked-gate behavior, finite-loop structure, and safety-boundary fields.

Windows + AIMLAB single-frame, 5-frame finite-loop, and 30-frame finite-loop validation passed with AIMLAB foreground and `blocked_frames=0`.

Phase 6 remains read-only. It does not implement mouse movement, clicking, auto-aim, target lock, closed-loop control, Phase 7, anti-cheat bypass, process injection, process memory reading, or AIMLAB file modification.
