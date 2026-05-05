# Phase 1 Collector Runbook

## Scope

This runbook covers the Phase 1 AIMLAB foreground-gated screenshot collector.

Allowed behavior:

- Detect whether an AIMLAB window exists by window title.
- Verify AIMLAB is the current foreground window.
- Read AIMLAB window title and rectangle.
- Detect the monitor containing AIMLAB.
- Capture the entire AIMLAB monitor only when AIMLAB is foreground.
- Save screenshot PNG files, JSON metadata, and logs.

Forbidden behavior:

- YOLO training or inference
- Yellow-ball recognition
- Automatic labeling
- Coordinate mapping
- Mouse movement
- Mouse clicking
- Closed-loop automation
- Background AIMLAB screenshot capture

## Install Dependencies

Use Windows Python 3.10 or newer.

```powershell
cd D:\桌面desktop\AIAIM
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

If editable install is not needed:

```powershell
python -m pip install -r requirements.txt
```

Dependencies:

- `mss` for monitor screenshot capture
- `pynput` for F8/F9/Esc hotkeys

## Single Screenshot

1. Start AIMLAB.
2. Set AIMLAB to windowed fullscreen or borderless fullscreen.
3. Bring AIMLAB to the foreground.
4. Run:

```powershell
aiaim-collect-screenshots --mode single
```

Fallback when only dependencies were installed:

```powershell
$env:PYTHONPATH = "src"
python -m aiaim_collector.collect_screenshots --mode single
```

Expected output:

- `data/raw/screenshots/<timestamp>_single.png`
- `data/raw/screenshots/<timestamp>_single.json`
- `logs/collector.log`

## Hotkey Continuous Capture

Run:

```powershell
aiaim-collect-screenshots --mode hotkeys --interval-ms 500
```

Hotkeys:

- F8: start or stop continuous capture
- F9: single screenshot attempt
- Esc: exit

The foreground gate is checked on every attempt. If AIMLAB loses focus, screenshots are blocked and metadata/logs record the blocked reason.

Validated Phase 1 hotkey behavior:

- F8 starts and stops continuous capture.
- F9 saves one single screenshot attempt.
- Esc exits hotkey mode.
- Foreground validation still runs for every hotkey-triggered attempt.

## Metadata Fields

Each attempt writes JSON metadata containing:

- `phase`
- `timestamp`
- `image_path`
- `capture_mode`
- `aimlab_window_found`
- `is_foreground`
- `blocked`
- `blocked_reason`
- `warning`
- `aimlab_window_title`
- `foreground_window_title`
- `window_rect`
- `monitor_rect`
- `monitor`
- `screenshot_width`
- `screenshot_height`
- `capture_elapsed_ms`
- `attempt_elapsed_ms`
- `window_monitor_coverage_ratio`

## Validate AIMLAB Not Foreground Is Blocked

1. Start AIMLAB.
2. Leave AIMLAB visible but focus another app such as PowerShell.
3. Run:

```powershell
aiaim-collect-screenshots --mode single
```

Expected result:

- No PNG screenshot is saved for that attempt.
- A JSON metadata file is saved.
- `blocked` is `true`.
- `blocked_reason` is `aimlab_not_foreground`.
- `foreground_window_title` identifies the active non-AIMLAB window.
- `logs/collector.log` records a blocked capture.

Validated Phase 1 result:

- AIMLAB non-foreground attempts were blocked.
- No PNG was saved for blocked non-foreground attempts.
- Metadata and logs recorded the blocked result.

## Validate Multi-Monitor Capture

1. Move AIMLAB to a non-primary monitor.
2. Bring AIMLAB to the foreground.
3. Run:

```powershell
aiaim-collect-screenshots --mode single
```

Expected result:

- `monitor_rect` matches the monitor containing AIMLAB.
- Negative `left` or `top` values are valid when Windows places that monitor left of or above the primary display.
- `screenshot_width` and `screenshot_height` match `monitor_rect.width` and `monitor_rect.height`.
- The saved PNG shows the whole AIMLAB monitor, not the primary monitor by default.

## Fullscreen Coverage Warning

If AIMLAB is foreground but does not cover most of the monitor, capture is allowed in Phase 1. Metadata and logs include a warning when `window_monitor_coverage_ratio` is below the threshold, default `0.95`.

## Phase 1 Real Acceptance Record

Windows + AIMLAB validation confirmed:

- AIMLAB not started does not crash the collector; blocked / error information is recorded.
- AIMLAB not foreground is blocked and does not save PNG.
- AIMLAB foreground in windowed fullscreen / borderless fullscreen captures successfully.
- F8, F9, and Esc hotkeys work as intended.
- 116 PNG screenshots were collected with corresponding JSON metadata.
- Metadata includes the required Phase 1 fields, including window title, foreground title, window rect, monitor rect, screenshot dimensions, capture mode, capture elapsed time, and window-monitor coverage ratio.
- A representative successful capture used title `aimlab_tb`, screenshot size `1920x1080`, monitor rect `1920x1080`, and coverage ratio about `0.963`.
- `logs/collector.log` contains corresponding runtime records.

Phase 1 acceptance did not include YOLO training, YOLO inference, yellow-ball recognition, automatic labeling, mouse movement, mouse clicking, coordinate mapping, closed-loop automation, or background window screenshots.

## Troubleshooting

- `aimlab_window_not_found`: confirm AIMLAB is running and the window title contains `aimlab` or `aim lab`; use `--title-keyword` if needed.
- `aimlab_not_foreground`: click AIMLAB or Alt-Tab to AIMLAB, then retry.
- `Phase 1 collector requires Windows foreground-window APIs`: run on Windows, not WSL/Linux.
- Hotkeys do not trigger: confirm the terminal has permission to receive global keyboard hooks and that `pynput` installed correctly.
