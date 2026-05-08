# Phase 4 Offline Detection Runbook

Phase 4 name:

```text
Phase 4 - Offline Detect-Only Inference Pipeline + Coordinate Contract v0
```

## Goal

Run YOLO11n `best.pt` on offline PNG/JPG/JPEG images and write machine-readable detection JSON, clean review images, `summary.csv`, and `run_config.json`.

All `bbox` and `center` values are input image pixel coordinates. They are not screen coordinates, mouse coordinates, AIMLAB window coordinates, or click targets.

## Boundary

Phase 4 allows offline detect-only inference against saved images.

Phase 4 does not:

- perform real-time screenshots
- connect to AIMLAB live screen
- connect to the Phase 1 collector live loop
- move the mouse
- click the mouse
- generate mouse targets
- generate click targets
- implement auto-aim
- implement closed-loop automation
- attempt anti-cheat bypass
- enter Phase 5 coordinate mapping

## Project Directory

```powershell
Set-Location "D:\桌面desktop\AIAIM"
```

## Default Assets

Default model:

```text
runs/detect/phase3_yolo11n_baseline/weights/best.pt
```

Default test image directory:

```text
data/yolo/aimlab_yellow_ball_v1_1/images/test
```

Default output directory:

```text
runs/detect/phase4_offline_detection
```

## Single Image

```powershell
.\.venv\Scripts\python.exe scripts\offline_detect.py `
  --model runs\detect\phase3_yolo11n_baseline\weights\best.pt `
  --image data\yolo\aimlab_yellow_ball_v1_1\images\test\20260505T154818297_0800_hotkey_continuous.png `
  --output-dir runs\detect\phase4_offline_detection_single `
  --conf 0.25 `
  --iou 0.70 `
  --max-det 50 `
  --imgsz 640 `
  --device auto
```

## Batch Directory

```powershell
.\.venv\Scripts\python.exe scripts\offline_detect.py `
  --model runs\detect\phase3_yolo11n_baseline\weights\best.pt `
  --image-dir data\yolo\aimlab_yellow_ball_v1_1\images\test `
  --output-dir runs\detect\phase4_offline_detection `
  --conf 0.25 `
  --iou 0.70 `
  --max-det 50 `
  --imgsz 640 `
  --device auto
```

## Optional Conf 0.50 Review

```powershell
.\.venv\Scripts\python.exe scripts\offline_detect.py `
  --model runs\detect\phase3_yolo11n_baseline\weights\best.pt `
  --image-dir data\yolo\aimlab_yellow_ball_v1_1\images\test `
  --output-dir runs\detect\phase4_offline_detection_conf050 `
  --conf 0.50 `
  --iou 0.70 `
  --max-det 50 `
  --imgsz 640 `
  --device auto
```

## Parameters

- `--model`: YOLO weights path. Defaults to Phase 3 `best.pt`.
- `--image`: one offline image.
- `--image-dir`: directory of offline images. Mutually exclusive with `--image`.
- `--output-dir`: output directory.
- `--conf`: confidence threshold. Default `0.25`.
- `--iou`: NMS IoU threshold. Default `0.70`.
- `--max-det`: max detections per image. Default `50`.
- `--imgsz`: YOLO inference image size. Default `640`.
- `--device`: `auto`, `cpu`, or explicit CUDA device such as `cuda:0`.
- `--save-review` / `--no-save-review`: write clean review images or skip them.
- `--save-json` / `--no-save-json`: write detection JSON or skip it.
- `--metadata`: optional same-image metadata JSON for single-image mode.
- `--metadata-dir`: optional directory for same-stem metadata JSON in batch mode.

Metadata is copied into `source_metadata` only. It is not used for screen coordinates, mouse coordinates, click targets, or Phase 5 mapping.

## Outputs

Default output structure:

```text
runs/detect/phase4_offline_detection/
  run_config.json
  summary.csv
  json/
    <stem>.json
  review_images/
    <stem>_review.png
```

## JSON Schema Summary

Each image JSON includes:

- `phase`
- `run`
- `coordinate_space`
- `image`
- `source_metadata`
- `summary`
- `detections`

Each detection includes:

- `class_id`
- `class_name`
- `confidence`
- `bbox_xyxy`
- `bbox_xywh`
- `center`
- `area_px`
- `validity`

`bbox_xywh.x` and `bbox_xywh.y` are the bbox center, not the top-left corner.

## Coordinate Space

The coordinate contract is:

```json
{
  "type": "input_image_pixel",
  "origin": "top_left",
  "x_axis": "right",
  "y_axis": "down",
  "unit": "pixel",
  "is_screen_coordinate": false,
  "is_mouse_coordinate": false,
  "is_window_coordinate": false,
  "is_click_target": false
}
```

`center.x` and `center.y` are valid only inside the input PNG/JPG/JPEG pixel coordinate system.

## Clean Review Image

Phase 4 does not use Ultralytics default rendered labels because large label text can hide small yellow balls.

The script draws:

- thin bbox lines
- small center cross
- small confidence text

Review images are for human inspection only and are not machine input.

## Common Issues

- `best.pt` missing: confirm Phase 3 output exists under `runs/detect/phase3_yolo11n_baseline/weights/best.pt`.
- CUDA unavailable: `--device auto` falls back to CPU.
- Wrong dataset path: the current YOLO dataset uses `data/yolo/aimlab_yellow_ball_v1_1/images/test`.
- Zero detections: this is not a failure; JSON and review image are still written.
- Large review text concern: Phase 4 clean review image intentionally avoids large label blocks.
- False positives in later testing: return to Phase 2.5 and add more negative samples.
- Small-ball misses in later testing: add small-ball samples or run a controlled `imgsz=960` experiment.

## Phase Boundary Confirmation

No real-time detection is performed.

No AIMLAB live screen connection is performed.

No mouse movement is performed.

No mouse click is performed.

No coordinate mapping is implemented.

No auto-aim is implemented.

No closed-loop automation is implemented.

No anti-cheat bypass is attempted.
