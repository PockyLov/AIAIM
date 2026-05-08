# Phase 6 Live Read-Only Detection Runbook

Phase 6 name:

```text
Live Read-Only Detection Pipeline
```

## Goal

Run live read-only detection while AIMLAB is the foreground window in windowed fullscreen / borderless fullscreen mode.

Phase 6 only captures the AIMLAB monitor, runs YOLO detection, and writes JSON / review images / summaries. It does not move the mouse, click, auto-aim, lock targets, or run a closed loop.

## Project Directory

```powershell
Set-Location "D:\桌面desktop\AIAIM"
```

## Default Model

```text
runs/detect/phase3_yolo11n_baseline/weights/best.pt
```

## Single-Frame Command

```powershell
.\.venv\Scripts\python.exe scripts\live_readonly_detect.py `
  --mode single `
  --model runs\detect\phase3_yolo11n_baseline\weights\best.pt `
  --output-dir runs\detect\phase6_live_readonly `
  --conf 0.25 `
  --review-images `
  --overwrite
```

Expected behavior:

- If AIMLAB is not started or is not foreground, the frame is blocked and no detection runs.
- If AIMLAB is foreground, the script captures one full monitor screenshot, runs YOLO, writes one frame JSON, writes a review image, updates `live_summary.csv`, writes `phase6_summary.json`, and exits.

## Finite-Loop Command

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

The loop is finite. It processes `max_frames` using `for frame_index in range(max_frames)` and exits automatically.

## Outputs

```text
runs/detect/phase6_live_readonly/
  captured_frames/
  json/
  review_images/
  live_summary.csv
  phase6_summary.json
  run_config.json
```

## Frame JSON Contract

Each frame JSON includes:

- `phase = "phase6_live_readonly_detection"`
- `frame_index`
- `timestamp`
- `source = "live_monitor_capture"`
- `aimlab_foreground_gate_passed`
- `blocked`
- `blocked_reason`
- `monitor_rect`
- `work_rect`
- `window_rect`
- `screenshot_size`
- `coordinate_contract_version`
- `detections`

Each detection includes:

- `class_id`
- `class_name`
- `confidence`
- `bbox_xyxy`
- `bbox_xywh`
- `center_image_px`
- `center_monitor_px`
- `coordinate_space = "image_pixel_and_monitor_relative"`
- `is_screen_coordinate = false`
- `is_mouse_coordinate = false`
- `is_click_target = false`
- `action_authorized = false`

## Coordinate Contract

Phase 6 follows the Phase 5.5 contract:

- `image_pixel` is the original trusted YOLO detection coordinate.
- In full-monitor capture mode, `monitor_relative` is the live read-only basis.
- raw `window_rect` and `window_relative` are debug / review information only.
- output coordinates are not mouse coordinates.
- output detections are not click targets.

## Review Images

Review images draw:

- detection bbox
- center point
- confidence
- `center_image_px` / `center_monitor_px`

Review images must not draw mouse targets, click targets, lock-on markers, movement vectors, or auto-aim visuals.

## Blocked-Gate Test

Run the single-frame command while AIMLAB is closed or not foreground.

Expected result:

- script exits cleanly
- `blocked=true`
- `aimlab_foreground_gate_passed=false`
- `detections=[]`
- `live_summary.csv` records status `blocked`

## Phase Boundary

Phase 6 forbids:

- mouse movement
- mouse clicking
- mouse target output
- click target output
- auto-aim
- target lock
- closed-loop automation
- anti-cheat bypass
- process memory reading
- injection into AIMLAB
- modifying AIMLAB files
- infinite control loops

Phase 7 is not implemented in Phase 6.

Direct cursor positioning belongs to a later-phase discussion only. Do not add it to this Phase 6 runbook or script.
