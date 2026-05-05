# Phase 3 YOLO Training Runbook

Phase 3 goal: train a YOLO11n baseline on the reviewed offline dataset, run offline validation, and generate offline prediction review images.

This phase does not perform real-time detection, does not connect to AIMLAB live screen, does not move or click the mouse, does not implement coordinate mapping, and does not implement closed-loop automation.

## Project Directory

```powershell
Set-Location "D:\桌面desktop\AIAIM"
```

## Preconditions

- Phase 2.5 v1_1 dataset is finalized and validated.
- Dataset path:

```text
data/yolo/aimlab_yellow_ball_v1_1/
```

- Data config:

```text
data/yolo/aimlab_yellow_ball_v1_1/data.yaml
```

Validation baseline:

- total images: 364
- train images: 254
- val images: 72
- test images: 38
- total labels: 364
- positive images: 347
- negative images: 17
- total boxes: 2054
- invalid label files: 0
- missing label files: 0
- result: VALIDATION PASSED

## Environment Check

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import ultralytics, torch; print('ultralytics', ultralytics.__version__); print('torch', torch.__version__); print('cuda', torch.cuda.is_available()); print('gpu', torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)"
```

Install dependencies if needed:

```powershell
.\.venv\Scripts\python.exe -m pip install ultralytics
```

## Dataset Validation

```powershell
.\.venv\Scripts\python.exe scripts\validate_yolo_dataset.py --dataset data\yolo\aimlab_yellow_ball_v1_1
```

## Train Baseline

Default training:

```powershell
.\.venv\Scripts\python.exe scripts\train_yolo_baseline.py
```

Equivalent explicit command:

```powershell
.\.venv\Scripts\python.exe scripts\train_yolo_baseline.py --model yolo11n.pt --epochs 100 --imgsz 640 --batch 16 --device 0 --workers 0 --patience 30 --seed 42 --name phase3_yolo11n_baseline
```

Expected outputs:

```text
runs/detect/phase3_yolo11n_baseline/weights/best.pt
runs/detect/phase3_yolo11n_baseline/weights/last.pt
runs/detect/phase3_yolo11n_baseline/results.csv
```

## Offline Validation

```powershell
.\.venv\Scripts\python.exe scripts\eval_yolo_baseline.py
```

Metrics summary:

```text
runs/detect/phase3_eval_metrics.csv
```

Current baseline metrics recorded for the completed Phase 3 run:

- precision: 0.975152
- recall: 0.878610
- mAP50: 0.892387
- mAP50-95: 0.534663

## Offline Prediction Review

```powershell
.\.venv\Scripts\python.exe scripts\predict_yolo_review.py
```

Expected review outputs:

```text
runs/detect/phase3_predict_val_conf025/
runs/detect/phase3_predict_test_conf025/
runs/detect/phase3_predict_val_conf050/
runs/detect/phase3_predict_test_conf050/
runs/detect/phase3_prediction_review_summary.csv
```

Use `conf=0.25` to expose false positives and `conf=0.50` to inspect more conservative predictions.

Current completed review summary:

- val, conf=0.25: 72 images, 420 predictions
- val, conf=0.50: 72 images, 344 predictions
- test, conf=0.25: 38 images, 225 predictions
- test, conf=0.50: 38 images, 185 predictions

Manual review conclusion:

- The user reviewed the prediction review images, with emphasis on test `conf=0.25` and test `conf=0.50`.
- The blue rendered label text in review images is visually large and can cover part of some small yellow balls.
- Overall prediction positions and counts are acceptable for the Phase 3 baseline.
- Phase 3 baseline accepted.
- No immediate retraining is required.
- No immediate return to Phase 2.5 is required.
- `imgsz=960` is not needed at this point, but remains a future option if small-ball misses become obvious.
- The model is acceptable for Phase 4 detect-only planning.
- This does not mean the system is ready for real-time detection or mouse control.

## Review best.pt

```powershell
dir runs\detect\phase3_yolo11n_baseline\weights
```

Use `best.pt` for offline validation and offline prediction review only.

## Review Metrics

Open:

```text
runs/detect/phase3_yolo11n_baseline/results.csv
runs/detect/phase3_eval_metrics.csv
```

Record precision, recall, mAP50, mAP50-95, and loss curves.

## Review Prediction Images

Open the four prediction review folders and inspect:

- false positives on yellow UI, buttons, or lights
- missed small yellow balls
- duplicate boxes
- low-confidence useful detections at `conf=0.25`
- overly conservative missed detections at `conf=0.50`

## Common Issues

- CUDA unavailable: script falls back to CPU and the report must record it.
- Ultralytics missing: install with `.\.venv\Scripts\python.exe -m pip install ultralytics`.
- Windows workers error: use `--workers 0`.
- Batch too large / out of memory: reduce `--batch`.
- Negative samples limited: current `negative_images=17`; if false positives appear on yellow UI/buttons/lights in later testing, return to Phase 2.5 and add negatives.
- Small balls missed: add more small-ball samples or run a future controlled `imgsz=960` experiment if later testing makes the issue obvious.
- Large review overlay text: review images may show large blue label text, but future Phase 4 detect-only work should consume bbox coordinates and confidence values, not rendered label text.

## Final Phase 3 Status

Phase 3 baseline accepted.

Phase 4 may be discussed only as detect-only planning in a future task. This runbook does not authorize Phase 4 implementation, real-time screen connection, mouse movement, mouse clicking, coordinate mapping, auto-aim, or closed-loop automation.

## Phase Boundary Confirmation

No real-time detection was performed.

No AIMLAB live screen connection was performed.

No mouse movement was performed.

No mouse click was performed.

No coordinate mapping was implemented.

No auto-aim was implemented.

No closed-loop automation was implemented.

No anti-cheat bypass was attempted.
