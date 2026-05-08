# Phase 5 Coordinate Mapping Runbook

Phase 5 name:

```text
Phase 5 - Offline Coordinate Mapping / Geometry Validation
```

## Goal

Read Phase 4 detection JSON files, match each source image to Phase 1 metadata, and validate offline geometry across these coordinate spaces:

- `image_pixel`
- `monitor_relative`
- `window_relative`

Phase 5 does not produce screen coordinates, mouse coordinates, mouse targets, click targets, auto-aim targets, or movement commands.

## Project Directory

```powershell
Set-Location "D:\桌面desktop\AIAIM"
```

## Inputs

Phase 4 detection JSON:

```text
runs/detect/phase4_offline_detection/json
```

Phase 1 metadata:

```text
data/raw/screenshots
```

## Command

```powershell
.\.venv\Scripts\python.exe scripts\offline_coordinate_mapping.py `
  --phase4-json-dir runs\detect\phase4_offline_detection\json `
  --metadata-dir data\raw\screenshots `
  --output-dir runs\detect\phase5_coordinate_mapping `
  --review-images `
  --overwrite
```

## CLI Parameters

- `--phase4-json-dir`: directory containing Phase 4 detection JSON files.
- `--metadata-dir`: directory containing Phase 1 metadata JSON files.
- `--output-dir`: Phase 5 output directory.
- `--review-images`: write geometry review images for human inspection.
- `--metadata-recursive`: search metadata recursively instead of only the top directory.
- `--tolerance-px`: geometry tolerance in pixels. Default `5`.
- `--overwrite`: replace an existing output directory.

If `--output-dir` already exists and `--overwrite` is not passed, the script exits with a clear error.

## Outputs

```text
runs/detect/phase5_coordinate_mapping/
  mapped_json/
  review_images/
  metadata_match_report.csv
  geometry_summary.csv
  phase5_summary.json
  run_config.json
```

## Coordinate Contract

`image_pixel`:

- origin: input image top-left
- x: right
- y: down
- unit: pixel

`monitor_relative`:

- origin: screenshot monitor top-left
- equals image pixel coordinates when image size matches metadata screenshot size
- scaled only if image size and metadata screenshot size differ, with low confidence

`window_relative`:

- origin: AIMLAB `window_rect` top-left relative to monitor
- computed from metadata `window_rect` and `monitor_rect`

All mapped JSON files explicitly keep:

- `screen_coordinate=false`
- `mouse_coordinate=false`
- `click_target=false`
- `is_screen_coordinate=false`
- `is_mouse_coordinate=false`
- `is_click_target=false`

## Actual Phase 5 Result

The accepted Phase 5 run produced:

- total_phase4_json_count = 38
- total_detection_count = 225
- metadata_matched_count = 38
- metadata_missing_count = 0
- metadata_duplicate_count = 0
- metadata_invalid_count = 0
- size_match_count = 38
- size_mismatch_count = 0
- rect_valid_count = 0
- rect_invalid_count = 38
- mapped_detection_count = 225
- detection_invalid_count = 0
- center_inside_image_count = 225
- center_inside_bbox_count = 225
- bbox_inside_image_count = 225
- center_inside_window_count = 225
- review_images_enabled = true

`rect_valid_count = 0` is caused by the Phase 1 window rect extending slightly outside the monitor rect, e.g. fullscreen border offsets around `-8 px`, while the default tolerance is `5 px`. Mapping still succeeds and is recorded as `mapping_confidence=medium`.

## Review Images

When `--review-images` is enabled, review images show:

- window rectangle outline
- detection bbox
- detection center
- short text with image and window-relative coordinates

Review images do not show mouse targets, click points, aim targets, movement vectors, or lock-on visuals.

## Phase Boundary Confirmation

No real-time screenshots are performed.

No AIMLAB live screen connection is performed.

No Phase 1 collector live loop is connected.

No mouse movement is performed.

No mouse click is performed.

No click target is output.

No mouse target is output.

No auto-aim is implemented.

No closed-loop automation is implemented.

No anti-cheat bypass is attempted.
