# Phase 5 Report - Offline Coordinate Mapping / Geometry Validation

## Phase Goal

Implement offline geometry validation between Phase 4 detection JSON and Phase 1 metadata. The phase maps detection centers across:

- `image_pixel`
- `monitor_relative`
- `window_relative`

This phase does not implement screen-coordinate mapping, mouse-coordinate mapping, mouse movement, clicking, auto-aim, or closed-loop automation.

## Input Directories

- Phase 4 JSON: `runs/detect/phase4_offline_detection/json`
- Phase 1 metadata: `data/raw/screenshots`

## Output Directory

```text
runs/detect/phase5_coordinate_mapping/
```

Generated outputs:

- `mapped_json/`
- `review_images/`
- `metadata_match_report.csv`
- `geometry_summary.csv`
- `phase5_summary.json`
- `run_config.json`

## Added Or Modified Files

Added:

- `scripts/offline_coordinate_mapping.py`
- `docs/runbooks/phase-5-coordinate-mapping-runbook.md`
- `docs/phase-reports/phase-5-report.md`

Modified:

- `README.md`
- `docs/phase-roadmap.md`
- `docs/safety-boundary.md`

## Implementation Summary

`scripts/offline_coordinate_mapping.py`:

- reads Phase 4 detection JSON files
- extracts source image path or falls back to detection JSON stem
- matches Phase 1 metadata by source image stem
- parses screenshot size, `monitor_rect`, and `window_rect`
- validates detection bbox and center
- computes monitor-relative center
- computes window-relative center
- writes per-image mapped JSON
- writes metadata match report
- writes per-detection geometry summary
- writes phase summary and run config
- optionally writes geometry review images

## Actual Run Command

```powershell
.\.venv\Scripts\python.exe scripts\offline_coordinate_mapping.py `
  --phase4-json-dir runs\detect\phase4_offline_detection\json `
  --metadata-dir data\raw\screenshots `
  --output-dir runs\detect\phase5_coordinate_mapping `
  --review-images `
  --overwrite
```

## Metadata Match Result

- total_phase4_json_count = 38
- metadata_matched_count = 38
- metadata_missing_count = 0
- metadata_duplicate_count = 0
- metadata_invalid_count = 0

All 38 Phase 4 JSON files matched Phase 1 metadata by source image stem.

## Detection Geometry Result

- total_detection_count = 225
- mapped_detection_count = 225
- detection_invalid_count = 0
- center_inside_image_count = 225
- center_inside_bbox_count = 225
- bbox_inside_image_count = 225
- center_inside_window_count = 225

All 225 detections were mapped into image, monitor-relative, and window-relative coordinate spaces.

## Size And Rect Validation

- size_match_count = 38
- size_mismatch_count = 0
- rect_valid_count = 0
- rect_invalid_count = 38

All image sizes matched metadata screenshot sizes.

Final geometry warning explanation:

- confirmed `monitor_rect = 0,0,1920,1080`
- confirmed `work_rect = 0,0,1920,1032`
- confirmed raw `window_rect = -8,-8,1928,1040`
- confirmed `screenshot_size = 1920x1080`
- default `tolerance_px=5` produced `rect_valid_count = 0` and `rect_invalid_count = 38`
- comparison run with `tolerance_px=10` produced `rect_valid_count = 38` and `rect_invalid_count = 0`

Conclusion: the `rect_invalid` result is not caused by detection failure or coordinate mapping failure. It is caused by Windows windowed fullscreen / maximized-window bounds extending roughly `8 px` beyond the monitor rectangle. A `tolerance_px=10` threshold covers this system boundary error.

Current Phase 5 keeps the warning explicit. It does not correct, hide, or reinterpret the raw metadata. It also does not enter control logic.

Phase 5 is accepted with geometry warning.

## Review Images

Review images were generated:

- review_images_enabled = true
- review image count = 38

The review images are for human geometry inspection only. They show window outline, detection bbox, center point, and short image/window coordinate text. They do not show mouse targets, click targets, aim targets, movement vectors, or lock-on visuals.

## Coordinate Contract

Phase 5 mapped JSON keeps:

- `screen_coordinate=false`
- `mouse_coordinate=false`
- `click_target=false`
- `is_screen_coordinate=false`
- `is_mouse_coordinate=false`
- `is_click_target=false`

Phase 5 does not treat `image_pixel` as screen coordinates or mouse coordinates.

## Safety Boundary

No real-time screenshots were performed.

No live AIMLAB connection was performed.

No Phase 1 live loop was connected.

No mouse movement was performed.

No mouse click was performed.

No click target was output.

No mouse target was output.

No auto-aim was implemented.

No closed-loop automation was implemented.

No anti-cheat bypass was attempted.

## Problems Encountered

The Phase 4 source image paths contain Windows-style backslashes. The script normalizes path text for stem extraction so metadata matching works consistently.

Phase 1 fullscreen `window_rect` extends slightly outside the monitor rectangle. The script records this as a rect warning instead of hiding it, while still producing recoverable window-relative geometry.

The final interpretation is that the warning reflects Windows window-frame / maximized-window geometry, not failed detections and not failed mapping. All 38 metadata records matched, all 225 detections mapped, and all 225 mapped centers were inside the window-relative bounds.

## Remaining Risks

- Rect validation is currently warning-level because of the observed fullscreen border offset.
- Any future realtime-control or Phase 6 work must revisit the coordinate contract around client area / content area versus raw `window_rect`.
- Window-relative geometry is offline-only and must not be used for mouse control.
- More geometry validation is needed before any future screen-coordinate or mouse-coordinate work.

## Decision

Phase 5 offline coordinate mapping and geometry validation is implemented and accepted with geometry warning.

Final accepted facts:

- 38/38 metadata records matched.
- 225/225 detections mapped.
- 225/225 detections have centers inside the window-relative bounds.
- The default `tolerance_px=5` rect warning is explained by approximately `8 px` Windows windowed fullscreen / maximized-window outer bounds.
- `tolerance_px=10` validates the observed geometry envelope.
- Phase 5 does not correct or disguise this metadata behavior.
- Phase 5 does not output mouse targets, click targets, screen targets, or control commands.

Do not enter Phase 6. The next appropriate discussion is Phase 6 planning only after a separate Phase 5 review confirms whether the geometry contract is sufficient for later dry-run work.

Before any realtime control or Phase 6 work, the project must explicitly discuss and document the client area / content area coordinate contract.
