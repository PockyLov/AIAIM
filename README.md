# AIAIM

AIAIM is a local offline AIMLAB experiment for staged research into yellow-ball detection, localization, and eventually gated mouse-control feedback.

Current status: Phase 8 one-shot relative aim implemented; Windows + AIMLAB Phase 8 acceptance is pending. Phase 7.5 Windows acceptance confirmed AIMLAB responds to SendInput relative movement.

Phase 1 has been validated on Windows with AIMLAB: foreground capture works, non-foreground attempts are blocked, F8/F9/Esc hotkeys work, and 116 PNG screenshots were collected with corresponding JSON metadata.

## Phase 1 Boundary

Phase 1 implements a foreground-gated screenshot collector for AIMLAB running in windowed fullscreen or borderless fullscreen.

It contains:

- AIMLAB window title discovery
- Foreground-window gate
- AIMLAB window rectangle metadata
- AIMLAB monitor detection
- Full-monitor screenshot capture for the AIMLAB monitor
- Screenshot metadata
- Collector logs
- Single-shot and hotkey capture modes

It does not contain:

- YOLO code
- Mouse movement code
- Mouse click code
- Coordinate mapping
- Real automation execution logic

Default behavior is gated: screenshots are refused unless AIMLAB is the foreground window.

## Install

Use Windows Python 3.10 or newer.

```powershell
cd D:\桌面desktop\AIAIM
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Alternatively:

```powershell
python -m pip install -r requirements.txt
```

## Single Screenshot

Start AIMLAB in windowed fullscreen or borderless fullscreen, make it the foreground window, then run:

```powershell
aiaim-collect-screenshots --mode single
```

If the package was not installed editable and only dependencies were installed, run with `PYTHONPATH`:

```powershell
$env:PYTHONPATH = "src"
python -m aiaim_collector.collect_screenshots --mode single
```

Screenshots and JSON metadata are saved to `data/raw/screenshots/`. Logs are written to `logs/collector.log`.

## Hotkey Mode

```powershell
aiaim-collect-screenshots --mode hotkeys --interval-ms 500
```

Hotkeys:

- F8: start / stop continuous screenshots
- F9: single screenshot
- Esc: exit

Every capture attempt still requires AIMLAB to be the foreground window.

## Phase 1 Acceptance

Validated on Windows with AIMLAB:

- AIMLAB not started does not crash the collector.
- AIMLAB not foreground is blocked and does not save PNG.
- AIMLAB foreground windowed fullscreen / borderless fullscreen captures successfully.
- F8 starts and stops continuous capture.
- F9 saves a single screenshot.
- Esc exits hotkey mode.
- Metadata contains the required Phase 1 fields.
- Logs are written to `logs/collector.log`.

Phase 1 still does not include YOLO, yellow-ball recognition, automatic labeling, mouse movement, mouse clicking, coordinate mapping, closed-loop automation, or background window screenshots.

## Phase 2 Dataset Preparation

Phase 2 prepares the Phase 1 screenshots for a future reviewed YOLO-format object-detection dataset. It covers selection, OpenCV offline pre-labeling assistance, human review workflow, train / val / test splitting, `data.yaml`, and dataset validation.

Phase 2 is completed for the current reviewed dataset:

- Dataset path: `data/yolo/aimlab_yellow_ball_v1/`
- `data.yaml` generated
- split completed: train 81 / val 23 / test 12
- validation passed
- total images: 116
- total labels: 116
- positive images: 115
- negative images: 1
- total boxes: 689
- class distribution: `{'0': 689}`

The current dataset has only one negative image. If future model checks show false positives, add negative samples toward a 10%-20% negative ratio.

Phase 2 command entry points:

```powershell
python scripts/prepare_phase2_dataset.py --dry-run
python scripts/prepare_phase2_dataset.py
python scripts/prelabel_yellow_ball_opencv.py --dry-run
python scripts/prelabel_yellow_ball_opencv.py --overwrite --review-images
python scripts/split_yolo_dataset.py --allow-empty-labels
python scripts/validate_yolo_dataset.py
```

Phase 2 data directories:

- `data/raw/screenshots/`: Phase 1 source screenshots and metadata
- `data/selected/phase2_yellow_ball/`: filtered images for annotation
- `data/prelabels/phase2_yellow_ball/`: OpenCV draft labels, review images, and manifest
- `data/yolo/aimlab_yellow_ball_v1/`: reviewed YOLO dataset structure

OpenCV pre-labels are draft annotation assistance only and require human review.

Phase 2 does not include YOLO training, YOLO inference, real-time detection, mouse movement, mouse clicking, coordinate mapping, closed-loop automation, or background window screenshots.

No YOLO training was performed. No YOLO inference was performed. No real-time detection was performed. No mouse movement was performed. No mouse click was performed. No coordinate mapping was implemented. No closed-loop automation was implemented. No anti-cheat bypass was attempted.

Phase 2 documents:

- `docs/annotation-guidelines.md`
- `docs/dataset-preparation.md`
- `docs/runbooks/phase-2-dataset-runbook.md`
- `docs/phase-reports/phase-2-report.md`

## Phase 3 YOLO Baseline

Phase 3 trained and evaluated an offline YOLO11n baseline on:

```text
data/yolo/aimlab_yellow_ball_v1_1/data.yaml
```

Dataset summary:

- total images: 364
- train / val / test: 254 / 72 / 38
- positive images: 347
- negative images: 17
- total boxes: 2054
- validation result before training: VALIDATION PASSED

Commands:

```powershell
.\.venv\Scripts\python.exe scripts\train_yolo_baseline.py
.\.venv\Scripts\python.exe scripts\eval_yolo_baseline.py
.\.venv\Scripts\python.exe scripts\predict_yolo_review.py
```

Outputs:

- `runs/detect/phase3_yolo11n_baseline/`
- `runs/detect/phase3_eval_metrics.csv`
- `runs/detect/phase3_prediction_review_summary.csv`
- `runs/detect/phase3_predict_val_conf025/`
- `runs/detect/phase3_predict_val_conf050/`
- `runs/detect/phase3_predict_test_conf025/`
- `runs/detect/phase3_predict_test_conf050/`

Baseline validation metrics from `scripts/eval_yolo_baseline.py`:

- precision: 0.975152
- recall: 0.878610
- mAP50: 0.892387
- mAP50-95: 0.534663

Best checkpoint:

```text
runs/detect/phase3_yolo11n_baseline/weights/best.pt
```

The current negative sample count is still limited (`negative_images=17`). If prediction review shows false positives on yellow UI/buttons/lights, return to Phase 2.5 and add more negative samples.

Manual prediction review result:

- User reviewed prediction review images, especially test `conf=0.25` and test `conf=0.50`.
- Review image blue label text is visually large and covers part of some small yellow balls.
- Overall prediction positions and counts are acceptable for this baseline.
- Phase 3 baseline accepted.
- No immediate retraining is required.
- No immediate return to Phase 2.5 is required.
- `imgsz=960` is not needed now, but remains a future option if small-ball misses become obvious.
- The model is acceptable for Phase 4 detect-only planning.

This does not mean the system is ready for real-time detection or mouse control.

Phase 3 does not include real-time detection, AIMLAB live screen connection, mouse movement, mouse clicking, coordinate mapping, auto-aim, closed-loop automation, or anti-cheat bypass.

Phase 3 documents:

- `docs/runbooks/phase-3-yolo-training-runbook.md`
- `docs/phase-reports/phase-3-report.md`

## Phase 4 Offline Detect-Only Inference

Phase 4 implements:

```text
Phase 4 - Offline Detect-Only Inference Pipeline + Coordinate Contract v0
```

It loads the Phase 3 `best.pt` checkpoint and runs detect-only inference against saved offline images.

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

Single image:

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

Batch directory:

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

Outputs:

- `runs/detect/phase4_offline_detection/run_config.json`
- `runs/detect/phase4_offline_detection/summary.csv`
- `runs/detect/phase4_offline_detection/json/*.json`
- `runs/detect/phase4_offline_detection/review_images/*_review.png`

Coordinate contract:

- bbox and center values are input image pixel coordinates.
- `center.x` and `center.y` are not screen coordinates.
- `center.x` and `center.y` are not mouse coordinates.
- `center.x` and `center.y` are not AIMLAB window coordinates.
- detections are not click targets.

Phase 4 does not include real-time screenshots, AIMLAB live screen connection, Phase 1 collector live loop integration, mouse movement, mouse clicking, coordinate mapping, auto-aim, closed-loop automation, or anti-cheat bypass.

Phase 4 documents:

- `docs/runbooks/phase-4-offline-detection-runbook.md`
- `docs/phase-reports/phase-4-report.md`

## Phase 5 Offline Coordinate Mapping

Phase 5 implements:

```text
Phase 5 - Offline Coordinate Mapping / Geometry Validation
```

It reads Phase 4 detection JSON files, matches Phase 1 metadata by source image stem, and validates image-pixel, monitor-relative, and window-relative geometry.

Default input:

```text
runs/detect/phase4_offline_detection/json
data/raw/screenshots
```

Default output:

```text
runs/detect/phase5_coordinate_mapping
```

Run:

```powershell
.\.venv\Scripts\python.exe scripts\offline_coordinate_mapping.py `
  --phase4-json-dir runs\detect\phase4_offline_detection\json `
  --metadata-dir data\raw\screenshots `
  --output-dir runs\detect\phase5_coordinate_mapping `
  --review-images `
  --overwrite
```

Accepted Phase 5 result:

- total Phase 4 JSON files: 38
- metadata matched: 38
- metadata missing: 0
- metadata duplicate: 0
- metadata invalid: 0
- total detections: 225
- mapped detections: 225
- center inside image: 225
- center inside bbox: 225
- bbox inside image: 225
- center inside window: 225
- review images generated: true

Note: Phase 1 `window_rect` extends slightly outside `monitor_rect` by about 8 px on the tested borderless/fullscreen captures, so Phase 5 records rect warnings with `mapping_confidence=medium`.

Phase 5 does not include real-time screenshots, AIMLAB live screen connection, Phase 1 live loop integration, mouse movement, mouse clicking, click targets, mouse targets, auto-aim, closed-loop automation, or anti-cheat bypass.

Phase 5 documents:

- `docs/runbooks/phase-5-coordinate-mapping-runbook.md`
- `docs/phase-reports/phase-5-report.md`

## Phase 5.5 Coordinate Contract Confirmation

Phase 5.5 is a small checkpoint before any future Phase 6 planning:

```text
Client Area / Content Area Coordinate Contract Confirmation
```

It reviews the Phase 1 metadata and Phase 5 geometry outputs and records the coordinate contract:

- Phase 5 is accepted with geometry warning.
- Phase 1 raw `window_rect` extends about 8 px beyond `monitor_rect` on the tested windowed fullscreen / maximized AIMLAB captures.
- `tolerance_px=10` covers this Windows outer-bounds difference.
- `image_pixel` is the original trusted YOLO detection coordinate.
- `monitor_relative` is the main coordinate basis candidate for future live read-only detection in the current full-monitor capture mode.
- raw `window_rect` and `window_relative` are debug / review / warning information only.
- `work_rect` is reference metadata only.
- `client_area` / `content_area` remains a future contract topic before any movement phase.

Phase 5.5 does not include realtime detection, AIMLAB live screen connection, Phase 1 live loop integration, mouse movement, mouse clicking, click targets, mouse targets, auto-aim, closed-loop automation, or anti-cheat bypass.

Phase 6, if started later, must begin as live read-only detection. It must not start with mouse movement or clicking.

Phase 5.5 documents:

- `docs/runbooks/phase-5-5-coordinate-contract-runbook.md`
- `docs/phase-reports/phase-5-5-coordinate-contract-report.md`

## Phase 6 Live Read-Only Detection

Phase 6 implements:

```text
Live Read-Only Detection Pipeline
```

It reuses Phase 1 AIMLAB foreground gate / monitor capture and Phase 3 YOLO `best.pt` to detect yellow balls from the current live monitor screenshot. Phase 6 is read-only: it outputs JSON, optional review images, and summaries.

Default model:

```text
runs/detect/phase3_yolo11n_baseline/weights/best.pt
```

Default output:

```text
runs/detect/phase6_live_readonly
```

Single-frame:

```powershell
.\.venv\Scripts\python.exe scripts\live_readonly_detect.py `
  --mode single `
  --model runs\detect\phase3_yolo11n_baseline\weights\best.pt `
  --output-dir runs\detect\phase6_live_readonly `
  --conf 0.25 `
  --review-images `
  --overwrite
```

Finite loop:

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

Outputs:

- `runs/detect/phase6_live_readonly/captured_frames/`
- `runs/detect/phase6_live_readonly/json/`
- `runs/detect/phase6_live_readonly/review_images/`
- `runs/detect/phase6_live_readonly/live_summary.csv`
- `runs/detect/phase6_live_readonly/phase6_summary.json`
- `runs/detect/phase6_live_readonly/run_config.json`

Coordinate boundary:

- detection center is reported as `center_image_px` and `center_monitor_px`
- output coordinate space is `image_pixel_and_monitor_relative`
- `is_screen_coordinate=false`
- `is_mouse_coordinate=false`
- `is_click_target=false`
- `action_authorized=false`

Phase 6 does not include mouse movement, mouse clicking, mouse targets, click targets, auto-aim, target lock, closed-loop automation, process memory reading, injection, AIMLAB file modification, or anti-cheat bypass.

Direct cursor positioning is a later-phase discussion only; it is not implemented or authorized in Phase 6.

Phase 6 documents:

- `docs/runbooks/phase-6-live-readonly-detection-runbook.md`
- `docs/phase-reports/phase-6-report.md`

## Phase 7 Direct Cursor Positioning

Phase 7 implements one-shot direct cursor positioning:

```text
Phase 7 - Direct Cursor Positioning
```

It detects yellow balls from one AIMLAB foreground monitor screenshot, chooses a primary target, computes `planned_cursor_screen_px`, and can move the Windows cursor once only when all safety gates pass.

Default config keeps movement disabled:

```text
config/phase7-cursor-positioning.json
```

Dry-run:

```powershell
Start-Sleep -Seconds 5; .\.venv\Scripts\python.exe scripts\live_direct_cursor_position.py `
  --model runs\detect\phase3_yolo11n_baseline\weights\best.pt `
  --conf 0.25 `
  --start-delay-sec 3 `
  --overwrite
```

Execute move requires all of:

- config `allow_mouse_move=true`
- CLI `--execute-move`
- CLI `--confirm-local-aimlab-only`

```powershell
Start-Sleep -Seconds 5; .\.venv\Scripts\python.exe scripts\live_direct_cursor_position.py `
  --model runs\detect\phase3_yolo11n_baseline\weights\best.pt `
  --conf 0.25 `
  --start-delay-sec 3 `
  --execute-move `
  --confirm-local-aimlab-only `
  --overwrite
```

Phase 7 does not click, does not run a continuous loop, does not implement target lock, does not run auto-aim correction, and does not implement closed-loop automation.

Emergency stop for this one-shot phase is Ctrl+C during `--start-delay-sec`, before capture or movement. There is no persistent cursor-control loop after the command exits.

Phase 7 documents:

- `docs/runbooks/phase-7-direct-cursor-positioning-runbook.md`
- `docs/phase-reports/phase-7-report.md`

## Phase 7.5 Relative Mouse Feasibility

Phase 7.5 implements:

```text
One-Shot Relative Mouse Actuation Feasibility
```

It exists because Phase 7 showed that `SetCursorPos` executed but AIMLAB gameplay kept the cursor near center. Phase 7.5 tests one fixed `SendInput` relative mouse movement and measures before / after YOLO target shift.

Default config:

```text
config/phase75-relative-mouse-feasibility.json
```

Dry-run:

```powershell
.\.venv\Scripts\python.exe scripts\live_relative_mouse_feasibility.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --conf 0.25 `
  --start-delay-sec 8 `
  --relative-dx 100 `
  --relative-dy 0 `
  --run-id phase75_windows_dry_run_dx100 `
  --overwrite
```

Execute one relative movement requires config `allow_relative_mouse_move=true` plus both CLI flags:

```powershell
.\.venv\Scripts\python.exe scripts\live_relative_mouse_feasibility.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --conf 0.25 `
  --start-delay-sec 8 `
  --relative-dx 100 `
  --relative-dy 0 `
  --execute-relative-move `
  --confirm-local-aimlab-only `
  --run-id phase75_windows_execute_dx100 `
  --overwrite
```

Phase 7.5 does not click, does not auto-aim, does not lock targets, does not loop movement, and does not do closed-loop correction.

Phase 7.5 documents:

- `docs/runbooks/phase-75-relative-mouse-feasibility-runbook.md`
- `docs/phase-reports/phase-75-report.md`

## Phase 8 One-Shot Relative Aim

Phase 8 implements one-shot relative aim planning and optional one-time `SendInput` relative mouse movement using Phase 7.5 calibration. It selects the YOLO yellow target nearest the monitor-center crosshair, computes target delta, converts it to one relative mouse move, and exits.

Default config:

```text
config/phase8-one-shot-relative-aim.json
```

Dry-run:

```powershell
.\.venv\Scripts\python.exe scripts\live_one_shot_relative_aim.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --conf 0.25 `
  --start-delay-sec 8 `
  --run-id phase8_windows_dry_run `
  --overwrite
```

Execute one-shot relative aim requires config `allow_relative_mouse_move=true` plus both CLI flags:

```powershell
.\.venv\Scripts\python.exe scripts\live_one_shot_relative_aim.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --conf 0.25 `
  --start-delay-sec 8 `
  --execute-relative-aim `
  --confirm-local-aimlab-only `
  --run-id phase8_windows_execute_one_shot `
  --overwrite
```

Phase 8 does not click, does not auto-click, does not target-lock, does not loop movement, and does not perform closed-loop correction.

Phase 8 documents:

- `docs/runbooks/phase-8-one-shot-relative-aim-runbook.md`
- `docs/phase-reports/phase-8-report.md`

## Phase 8.1 FOV-based One-Shot Relative Aim

Phase 8.1 adds an alternative one-shot model:

```text
pixel_delta -> FOV angle_delta -> mouse_count
```

It uses VALORANT hipfire FOV defaults (`horizontal_fov_deg=103`, `vertical_fov_deg=70.53`) and theoretical `counts_per_degree=39.03` with `global_gain=1.0`.

Dry-run:

```powershell
.\.venv\Scripts\python.exe scripts\live_one_shot_fov_aim.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --conf 0.25 `
  --horizontal-fov-deg 103 `
  --vertical-fov-deg 70.53 `
  --screen-width 1920 `
  --screen-height 1080 `
  --counts-per-degree 39.03 `
  --global-gain 1.0 `
  --output-dir "D:\桌面desktop\AIAIM\runs\detect\phase8_1_fov_one_shot"
```

Execute one-shot:

```powershell
.\.venv\Scripts\python.exe scripts\live_one_shot_fov_aim.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --conf 0.25 `
  --horizontal-fov-deg 103 `
  --vertical-fov-deg 70.53 `
  --screen-width 1920 `
  --screen-height 1080 `
  --counts-per-degree 39.03 `
  --global-gain 1.0 `
  --execute-move `
  --confirm-local-aimlab-only `
  --output-dir "D:\桌面desktop\AIAIM\runs\detect\phase8_1_fov_one_shot"
```

Phase 8.1 does not click, auto-click, target-lock, loop, perform closed-loop correction, use PID, micro-step, smooth movement, read process memory, or modify AIMLAB files.

Documents:

- `docs/runbooks/phase-8-1-fov-one-shot-aim-runbook.md`
- `docs/phase-reports/phase-8-1-report.md`

## Start Here

Read these documents before any future change:

- `AGENTS.md`
- `docs/project-overview.md`
- `docs/safety-boundary.md`
- `docs/phase-roadmap.md`
- `docs/agent-team.md`
- `docs/mcp-plan.md`

Every phase must end with a report in `docs/phase-reports/`.
