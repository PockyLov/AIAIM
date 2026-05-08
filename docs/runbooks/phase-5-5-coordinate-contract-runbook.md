# Phase 5.5 Coordinate Contract Runbook

Phase 5.5 name:

```text
Client Area / Content Area Coordinate Contract Confirmation
```

## Goal

Confirm the coordinate contract after Phase 5 and before any future Phase 6 planning.

Phase 5.5 is a documentation and review checkpoint. It does not run realtime detection and does not control the mouse.

## Project Directory

```powershell
Set-Location "D:\桌面desktop\AIAIM"
```

## Files To Review

```text
docs/phase-reports/phase-5-report.md
docs/runbooks/phase-5-coordinate-mapping-runbook.md
runs/detect/phase5_coordinate_mapping/phase5_summary.json
runs/detect/phase5_coordinate_mapping/run_config.json
runs/detect/phase5_coordinate_mapping/geometry_summary.csv
runs/detect/phase5_coordinate_mapping/metadata_match_report.csv
data/raw/screenshots/*.json
```

## Confirmed Phase 5 Result

- Phase 5 accepted with geometry warning.
- 38 / 38 Phase 4 JSON files matched metadata.
- 225 / 225 detections mapped.
- 225 / 225 detection centers are inside image bounds.
- 225 / 225 detection centers are inside bbox bounds.
- 225 / 225 bboxes are inside image bounds.
- 225 / 225 detection centers are inside window-relative bounds.
- detection_invalid_count = 0.

## Geometry Warning Interpretation

Observed metadata:

- `monitor_rect = 0,0,1920,1080`
- `work_rect = 0,0,1920,1032`
- raw `window_rect = -8,-8,1928,1040`
- `screenshot_size = 1920x1080`

Validation:

- `tolerance_px=5`: `rect_valid_count = 0`, `rect_invalid_count = 38`
- `tolerance_px=10`: `rect_valid_count = 38`, `rect_invalid_count = 0`

Interpretation:

The warning is caused by Windows windowed fullscreen / maximized-window outer bounds extending about `8 px` beyond the monitor rectangle. It is not a detection failure and not a mapping failure.

## Coordinate Contract

Use this contract for future Phase 6 planning:

- `image_pixel` is the original trusted YOLO detection coordinate.
- `monitor_relative` is the main coordinate basis candidate for future live read-only detection in the current full-monitor capture mode.
- raw `window_rect` is debug / review / warning information only.
- `window_relative` may remain in offline reports, but must not become an action coordinate or click target.
- `work_rect` is reference metadata only.
- `client_area` / `content_area` remains a future contract topic and is not calibrated in Phase 5.5.

## Phase Boundary

Phase 5.5 forbids:

- realtime screenshots
- AIMLAB live screen connection
- Phase 1 collector live loop integration
- mouse movement
- mouse clicking
- mouse target output
- click target output
- auto-aim
- closed-loop automation
- anti-cheat bypass
- process memory reading
- complex UI calibration
- Phase 6 implementation

## Acceptance Checklist

- Phase 5.5 report exists.
- README mentions Phase 5.5.
- roadmap mentions Phase 5.5.
- safety boundary mentions Phase 5.5.
- The report confirms `image_pixel` / `monitor_relative` as the future read-only coordinate basis.
- The report confirms raw `window_rect` / `window_relative` are debug-only and not action coordinates.
