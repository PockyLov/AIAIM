# Phase 1 Report - AIMLAB Foreground Stable Screenshot Collector

## 1. Phase Goal

Implement an AIMLAB foreground-gated collector that captures the entire monitor containing the AIMLAB window when AIMLAB is running in windowed fullscreen or borderless fullscreen and is the current foreground window.

## 2. Work Completed

- Added a Python package under `src/aiaim_collector/`.
- Implemented AIMLAB window discovery by title keyword.
- Implemented foreground-window validation.
- Implemented AIMLAB window title and rectangle metadata.
- Implemented monitor detection using `MonitorFromWindow` and `GetMonitorInfoW`.
- Implemented full-monitor screenshot capture using `mss`.
- Implemented JSON metadata writing for both successful and blocked attempts.
- Implemented logging to `logs/collector.log`.
- Implemented single-shot CLI mode.
- Implemented F8/F9/Esc hotkey mode using `pynput`.
- Added Phase 1 runbook and updated README usage notes.

## 3. Files Created or Modified

Created:

- `pyproject.toml`
- `requirements.txt`
- `src/aiaim_collector/__init__.py`
- `src/aiaim_collector/logging_setup.py`
- `src/aiaim_collector/window_detector.py`
- `src/aiaim_collector/monitor_detector.py`
- `src/aiaim_collector/screen_capture.py`
- `src/aiaim_collector/metadata_writer.py`
- `src/aiaim_collector/collector_service.py`
- `src/aiaim_collector/hotkey_controller.py`
- `src/aiaim_collector/collect_screenshots.py`
- `docs/runbooks/phase-1-collector-runbook.md`
- `docs/phase-reports/phase-1-report.md`

Modified:

- `README.md`

## 4. Usage

Install:

```powershell
cd D:\桌面desktop\AIAIM
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Single screenshot:

```powershell
aiaim-collect-screenshots --mode single
```

Hotkey mode:

```powershell
aiaim-collect-screenshots --mode hotkeys --interval-ms 500
```

Hotkeys:

- F8: start / stop continuous screenshots
- F9: single screenshot
- Esc: exit

## 5. Validation Performed

Initial implementation checks:

- Source files were created under the expected module boundaries.
- Documentation and runbook files were created.
- Python files compile with `python -m py_compile`.
- No files implementing YOLO, mouse movement, mouse clicking, coordinate mapping, or closed-loop automation were added.

Real Windows + AIMLAB acceptance checks:

- AIMLAB not started: collector did not crash and recorded blocked / error information.
- AIMLAB running but not foreground: collector blocked the attempt and did not save a PNG.
- AIMLAB foreground in windowed fullscreen / borderless fullscreen: screenshot capture succeeded.
- F8 started and stopped continuous screenshot capture.
- F9 saved a single screenshot.
- Esc exited hotkey mode.
- 116 PNG screenshots were successfully collected.
- Each collected PNG had corresponding JSON metadata.
- `logs/collector.log` contained matching runtime records.
- Metadata field coverage was verified.

Metadata fields verified:

- `aimlab_window_found`
- `aimlab_window_title`
- `foreground_window_title`
- `is_foreground`
- `blocked`
- `blocked_reason`
- `image_path`
- `metadata_path`
- `window_rect`
- `monitor_rect`
- `screenshot_width`
- `screenshot_height`
- `capture_mode`
- `capture_elapsed_ms`
- `window_monitor_coverage_ratio`

Representative successful metadata values:

- `aimlab_window_found=true`
- `aimlab_window_title="aimlab_tb"`
- `foreground_window_title="aimlab_tb"`
- `is_foreground=true`
- `blocked=false`
- `screenshot_width=1920`
- `screenshot_height=1080`
- `monitor_rect=1920x1080`
- `window_monitor_coverage_ratio≈0.963`

## 6. Acceptance Results

The implementation satisfies the Phase 1 design requirements in real Windows + AIMLAB testing:

- AIMLAB must exist and be foreground before screenshot capture is allowed.
- Blocked attempts write metadata and logs.
- Multi-monitor detection uses the AIMLAB window handle instead of assuming the primary monitor.
- Monitor rectangles support negative coordinates.
- Foreground validation is not bypassed.
- Non-fullscreen foreground AIMLAB can still be captured, but low monitor coverage is recorded as a warning.
- Single-shot capture works.
- Hotkey continuous capture works.
- F8/F9/Esc hotkey controls work.
- AIMLAB not-foreground attempts are blocked and do not save PNG files.
- Metadata contains the required Phase 1 fields.
- Logs are written to `logs/collector.log`.
- 116 PNG screenshots and corresponding JSON metadata files were collected during acceptance.

## 7. Problems Encountered

- The repository documentation still stated Phase 0 as current, while the user explicitly requested Phase 1.
- Initial live collector behavior could not be executed in the coding environment because Windows foreground-window APIs and AIMLAB were unavailable there.
- Real acceptance had to be completed by the user on Windows with AIMLAB.

## 8. How Problems Were Solved

- Treated the user's explicit request as approval to enter Phase 1 while keeping all Phase 1 boundaries from the roadmap.
- Implemented Windows API access behind Phase 1 modules and documented Windows-only runtime expectations.
- Added compile-time validation and manual Windows validation steps instead of claiming live capture was tested here.
- Updated this report with the user's real Windows + AIMLAB acceptance results after testing.

## 9. What Was Intentionally Not Done

- Did not implement YOLO training.
- Did not implement YOLO inference.
- Did not implement yellow-ball recognition.
- Did not implement automatic labeling.
- Did not implement coordinate mapping.
- Did not implement mouse movement.
- Did not implement mouse clicking.
- Did not implement closed-loop automation.
- Did not implement background AIMLAB screenshot capture.
- Did not enter Phase 2 or any later phase.

## 10. Safety Notes

The collector is foreground-gated. If AIMLAB is not the current foreground window, the capture attempt is blocked and the reason is recorded in metadata and logs.

No mouse control code exists in Phase 1.

## 11. Remaining Risks

- AIMLAB window title may vary by version or locale; use `--title-keyword` if the default keywords do not match.
- Windows display scaling and unusual borderless modes may affect coverage ratio interpretation.
- Hotkey behavior depends on Windows permissions and the active desktop session.
- Capture performance and long-session stability can still be measured more deeply in later maintenance work.

## 12. Next Phase Entry Conditions

Before Phase 2 starts:

- Confirm the accepted Phase 1 screenshot and metadata artifacts are the intended source material.
- Preserve raw screenshots and metadata under the Phase 1 artifact layout.
- Keep Phase 2 limited to dataset workflow preparation unless explicitly expanded by the user.
- Confirm no mouse control or YOLO code is needed for Phase 1.
- Re-read `AGENTS.md`, `docs/phase-roadmap.md`, and `docs/safety-boundary.md` before any Phase 2 work.

## 13. Suggested Next Codex Prompt

Execute AIAIM Phase 2 only after Phase 1 is manually validated on Windows. Build a dataset construction workflow from saved Phase 1 screenshots, including folder layout, labeling rules, review checklist, and YOLO dataset structure. Do not train YOLO, do not run YOLO inference, do not move the mouse, do not click, and do not implement closed-loop automation.
