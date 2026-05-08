# Phase 5.5 Report - Client Area / Content Area Coordinate Contract Confirmation

## Phase Goal

Phase 5.5 confirms the coordinate contract needed before any future Phase 6 planning.

This phase is intentionally small. It only reviews existing Phase 1 metadata and Phase 5 offline geometry outputs, then documents which coordinate spaces are suitable for the next read-only phase.

Phase 5.5 does not implement live detection, realtime screenshot capture, mouse movement, clicking, auto-aim, closed-loop automation, or anti-cheat bypass.

## Inputs Reviewed

Project files reviewed:

- `README.md`
- `docs/phase-roadmap.md`
- `docs/safety-boundary.md`
- `docs/phase-reports/phase-5-report.md`
- `docs/runbooks/phase-5-coordinate-mapping-runbook.md`
- `scripts/offline_coordinate_mapping.py`
- `data/raw/screenshots/*.json`
- `runs/detect/phase5_coordinate_mapping/phase5_summary.json`
- `runs/detect/phase5_coordinate_mapping/run_config.json`
- `runs/detect/phase5_coordinate_mapping/geometry_summary.csv`
- `runs/detect/phase5_coordinate_mapping/metadata_match_report.csv`

No new runtime script was needed because the existing metadata and Phase 5 reports already contain the required evidence.

## Phase 5 Result Confirmed

Phase 5 is accepted with geometry warning.

Confirmed Phase 5 statistics:

- total_phase4_json_count = 38
- metadata matched = 38 / 38
- total_detection_count = 225
- mapped_detection_count = 225
- center_inside_image_count = 225
- center_inside_bbox_count = 225
- bbox_inside_image_count = 225
- center_inside_window_count = 225
- detection_invalid_count = 0

## Geometry Warning Confirmed

The tested Phase 1 metadata shows:

- `monitor_rect = 0,0,1920,1080`
- `work_rect = 0,0,1920,1032`
- raw `window_rect = -8,-8,1928,1040`
- `screenshot_size = 1920x1080`

With default `tolerance_px=5`:

- `rect_valid_count = 0`
- `rect_invalid_count = 38`

With comparison `tolerance_px=10`:

- `rect_valid_count = 38`
- `rect_invalid_count = 0`

Conclusion: the rect warning is not a detection failure and not a mapping failure. It is caused by Windows windowed fullscreen / maximized-window outer bounds extending about `8 px` beyond the monitor rectangle.

Phase 5.5 does not correct, hide, or reinterpret the raw `window_rect`. It records the contract implication and keeps the warning visible.

## Coordinate Contract Conclusion

Phase 5.5 confirms this contract for future Phase 6 planning:

- `image_pixel` is the original trusted YOLO detection coordinate space.
- In the current full-monitor capture mode, `monitor_relative` is the main coordinate basis candidate for future live read-only detection.
- raw `window_rect` is debug / review / warning metadata only.
- `window_relative` may remain in offline reports, but it is not a future action coordinate and not a click target.
- `work_rect` is reference metadata only and is not the detection primary coordinate.
- `client_area` / `content_area` is documented here as a future contract topic only. Phase 5.5 does not implement complex calibration or client-area extraction.

Very important:

- `image_pixel` is not a screen coordinate.
- `monitor_relative` is not a mouse coordinate.
- `window_relative` is not a click target.
- No Phase 5.5 output authorizes movement, clicking, auto-aim, or closed-loop behavior.

## Phase 6 Readiness Boundary

If Phase 6 is started later, it must begin as live read-only detection planning and implementation only.

Before any future realtime control or mouse movement work, the project must explicitly define and validate the client area / content area coordinate contract. Raw `window_rect` must not be treated as an action coordinate source.

## Work Completed

- Reviewed the current Phase 5 evidence.
- Confirmed the 8 px raw `window_rect` outer-bounds explanation.
- Documented the Phase 5.5 coordinate contract.
- Added this Phase 5.5 report.
- Added a small Phase 5.5 runbook.
- Updated README, roadmap, and safety boundary with the Phase 5.5 status.

## Problems Encountered

No implementation blocker was found.

The main issue is conceptual: raw Windows `window_rect` includes outer bounds for the tested windowed fullscreen / maximized AIMLAB window. That makes strict `tolerance_px=5` rect validation warn even though detection and mapping are valid.

## How It Was Handled

The project keeps the raw metadata unchanged and records the warning explicitly.

The Phase 5.5 contract selects `image_pixel` and `monitor_relative` as the safe basis for future read-only detection discussion, while treating raw `window_rect` and `window_relative` as debug information only.

## Explicit Non-Goals

No realtime screenshot capture was implemented.

No AIMLAB live screen connection was implemented.

No Phase 1 live loop was connected.

No mouse movement was implemented.

No mouse click was implemented.

No mouse target was output.

No click target was output.

No auto-aim was implemented.

No closed-loop automation was implemented.

No anti-cheat bypass was attempted.

No process memory was read.

No complex multi-monitor adaptation was implemented.

No client-area calibration tool was implemented.

No Phase 6 implementation was started.

## Remaining Risks

- The Phase 5 warning is understood, but raw `window_rect` is still not suitable as an action-coordinate basis.
- Future live read-only detection must keep `image_pixel` / `monitor_relative` separate from screen and mouse coordinates.
- Before any movement phase, the project needs a separate client area / content area contract review.

## Decision

Phase 5.5 is complete as a coordinate-contract confirmation checkpoint.

The next appropriate step is Phase 6 planning for live read-only detection only. It must not include mouse movement, clicking, auto-aim, or closed-loop automation.
