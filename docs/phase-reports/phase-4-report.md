# Phase 4 Report - Offline Detect-Only Inference Pipeline + Coordinate Contract v0

## Phase Name

Phase 4 - Offline Detect-Only Inference Pipeline + Coordinate Contract v0

## Goal

Use the Phase 3 YOLO11n `best.pt` checkpoint to run detect-only inference on offline PNG/JPG/JPEG images, then produce detection JSON, clean review images, `summary.csv`, and `run_config.json`.

All detection coordinates are defined only in the input image pixel coordinate system.

## Input Assets

- model: `runs/detect/phase3_yolo11n_baseline/weights/best.pt`
- test images: `data/yolo/aimlab_yellow_ball_v1_1/images/test`
- Phase 3 validation metrics:
  - precision = 0.975152
  - recall = 0.878610
  - mAP50 = 0.892387
  - mAP50-95 = 0.534663

## Environment

- Python = 3.12.10
- Ultralytics = 8.4.46
- torch = 2.6.0+cu124
- CUDA available = true
- GPU = NVIDIA GeForce RTX 4060 Ti
- actual Phase 4 device = `cuda:0`

## Added Or Modified Files

Added:

- `scripts/offline_detect.py`
- `docs/runbooks/phase-4-offline-detection-runbook.md`
- `docs/phase-reports/phase-4-report.md`

Modified:

- `README.md`
- `docs/phase-roadmap.md`
- `docs/safety-boundary.md`

## Implementation

`scripts/offline_detect.py` implements:

- single-image offline inference via `--image`
- directory offline inference via `--image-dir`
- mutual exclusion between `--image` and `--image-dir`
- model existence checks
- Ultralytics YOLO model loading
- device resolution for `auto`, `cpu`, and explicit CUDA devices
- `run_config.json`
- per-image detection JSON under `json/`
- clean review images under `review_images/`
- batch `summary.csv`
- optional metadata copying into `source_metadata`
- bbox and center validity checks

The script does not import or call mouse-control libraries and does not connect to the Phase 1 collector.

## Output Format

Default output directory:

```text
runs/detect/phase4_offline_detection/
```

Default structure:

```text
runs/detect/phase4_offline_detection/
  run_config.json
  summary.csv
  json/
    <stem>.json
  review_images/
    <stem>_review.png
```

Each detection JSON includes:

- `phase`
- `run`
- `coordinate_space`
- `image`
- `source_metadata`
- `summary`
- `detections`

Each detection includes:

- `bbox_xyxy`
- `bbox_xywh`
- `center`
- `area_px`
- `validity`

## Coordinate Contract

Phase 4 coordinate values are input image pixel coordinates only.

The JSON explicitly records:

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

`center.x` and `center.y` do not represent screen coordinates, mouse coordinates, AIMLAB window coordinates, or click targets.

## Validation Results

### Model Load

Result: passed.

- `best.pt` exists.
- Ultralytics YOLO loaded the model.
- `model.names` was read.
- actual device was recorded as `cuda:0`.

### Single Image Test

Command:

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

Result:

- images = 1
- ok = 1
- failed = 0
- detections = 6
- JSON files = 1
- clean review images = 1
- `summary.csv` generated
- `run_config.json` generated

### Batch Directory Test

Command:

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

Result:

- images = 38
- ok = 38
- failed = 0
- detections = 225
- JSON files = 38
- clean review images = 38
- `summary.csv` rows = 38
- `run_config.json` generated

### Conf 0.50 Comparison

Command:

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

Result:

- images = 38
- ok = 38
- failed = 0
- detections = 185
- JSON files = 38
- clean review images = 38

### Coordinate Validation

Result: passed.

- All checked detection bboxes were within image bounds.
- All checked centers were inside their bbox.
- All checked centers were inside image bounds.
- `is_screen_coordinate=false`
- `is_mouse_coordinate=false`
- `is_window_coordinate=false`
- `is_click_target=false`

## Risks

- `negative_images = 17`, still limited.
- If false positives appear on yellow UI/buttons/lights in later testing, return to Phase 2.5 and add more negative samples.
- If small balls are missed in later testing, either add more small-ball samples or run a controlled `imgsz=960` experiment.
- Offline inference does not prove real-time stability.
- Phase 4 coordinates are not suitable for mouse control.

## Not Done

- 未接入 AIMLAB 实时画面。
- 未接 Phase 1 collector live loop。
- 未做实时截图。
- 未做鼠标移动。
- 未做鼠标点击。
- 未做自动瞄准。
- 未做闭环自动化。
- 未做反作弊绕过。
- 未进入 Phase 5 坐标映射。

## Phase Boundary Confirmation

No real-time detection was performed.

No AIMLAB live screen connection was performed.

No mouse movement was performed.

No mouse click was performed.

No coordinate mapping was implemented.

No auto-aim was implemented.

No closed-loop automation was implemented.

No anti-cheat bypass was attempted.

## Decision

Phase 4 offline detect-only inference and coordinate contract v0 are implemented and accepted as a candidate based on offline tests.

Do not enter Phase 5 implementation yet. The next appropriate discussion is Phase 5 Offline Coordinate Mapping / Geometry Validation planning.
