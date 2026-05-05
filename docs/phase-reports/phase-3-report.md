# Phase 3 Report - YOLO Training / Baseline Evaluation

## 1. Phase Goal

Train the first YOLO11n offline baseline on `aimlab_yellow_ball_v1_1`, evaluate validation metrics, and generate offline prediction review images for val/test splits.

## 2. Scope

- Environment check for Python, Ultralytics, torch, CUDA, and GPU.
- Ultralytics YOLO11n baseline training.
- Offline validation on the dataset defined by `data.yaml`.
- Offline prediction review on val/test images at `conf=0.25` and `conf=0.50`.
- Metrics and risk reporting.

## 3. Explicit Non-Goals

- No real-time detection was performed.
- No AIMLAB live screen connection was performed.
- No mouse movement was performed.
- No mouse click was performed.
- No coordinate mapping was implemented.
- No auto-aim was implemented.
- No closed-loop automation was implemented.
- No anti-cheat bypass was attempted.

## 4. Dataset Used

```text
data/yolo/aimlab_yellow_ball_v1_1/data.yaml
```

## 5. Dataset Statistics

- total_images = 364
- train_images = 254
- val_images = 72
- test_images = 38
- total_labels = 364
- positive_images = 347
- negative_images = 17
- total_boxes = 2054
- invalid_label_files = 0
- missing_label_files = 0
- class_distribution = `{'0': 2054}`
- VALIDATION PASSED

Risk: `negative_images = 17`, still limited.

## 6. Environment

- python = 3.12.10
- ultralytics = 8.4.46
- torch = 2.6.0+cu124
- cuda_available = true
- gpu_name = NVIDIA GeForce RTX 4060 Ti
- device used = 0

CUDA was available, so no CPU fallback was needed.

## 7. Training Configuration

- model: `yolo11n.pt`
- epochs: 100
- imgsz: 640
- batch: 16
- device: 0
- workers: 0
- patience: 30
- seed: 42
- project: default Ultralytics detect project, producing files under `runs/detect/`
- name: `phase3_yolo11n_baseline`

Training command:

```powershell
.\.venv\Scripts\python.exe scripts\train_yolo_baseline.py --exist-ok
```

## 8. Training Outputs

Training completed successfully in approximately 0.303 hours.

Generated outputs:

- `runs/detect/phase3_yolo11n_baseline/weights/best.pt`
- `runs/detect/phase3_yolo11n_baseline/weights/last.pt`
- `runs/detect/phase3_yolo11n_baseline/results.csv`
- `runs/detect/phase3_yolo11n_baseline/results.png`

Final training row from `results.csv`:

- train/box_loss = 1.76906
- train/cls_loss = 0.46909
- train/dfl_loss = 0.65282
- val/box_loss = 2.01779
- val/cls_loss = 0.48232
- val/dfl_loss = 0.63193
- final-row precision = 0.94306
- final-row recall = 0.86516
- final-row mAP50 = 0.87592
- final-row mAP50-95 = 0.49686

## 9. Metrics

Independent offline validation command:

```powershell
.\.venv\Scripts\python.exe scripts\eval_yolo_baseline.py
```

Validation output:

- metrics file: `runs/detect/phase3_eval_metrics.csv`
- precision = 0.975152
- recall = 0.878610
- mAP50 = 0.892387
- mAP50-95 = 0.534663

The training run's built-in best-weight validation reported:

- precision = 0.963095
- recall = 0.863184
- mAP50 = 0.876394
- mAP50-95 = 0.511387

## 10. Offline Prediction Review

Prediction review command:

```powershell
.\.venv\Scripts\python.exe scripts\predict_yolo_review.py
```

Generated review outputs:

- `runs/detect/phase3_predict_val_conf025/`
- `runs/detect/phase3_predict_test_conf025/`
- `runs/detect/phase3_predict_val_conf050/`
- `runs/detect/phase3_predict_test_conf050/`
- `runs/detect/phase3_prediction_review_summary.csv`

Review summary:

- val, conf=0.25: 72 images, 420 predictions
- val, conf=0.50: 72 images, 344 predictions
- test, conf=0.25: 38 images, 225 predictions
- test, conf=0.50: 38 images, 185 predictions
- summary rows = 220

These predictions are offline review artifacts only. They were generated from dataset images, not from a live AIMLAB screen.

## 11. Findings

- YOLO11n at `imgsz=640` trains successfully on `aimlab_yellow_ball_v1_1`.
- GPU training on RTX 4060 Ti worked with CUDA torch.
- Baseline validation metrics are usable for a first offline model checkpoint.
- Recall is lower than precision, so missed yellow balls remain a concrete review risk.
- Prediction review images were generated for both val and test splits at two confidence thresholds.
- Human review of prediction images has been completed for the Phase 3 baseline acceptance decision.

## 12. Manual Prediction Review

The user manually reviewed the offline prediction review images, with emphasis on:

- `runs/detect/phase3_predict_test_conf025/`
- `runs/detect/phase3_predict_test_conf050/`

Review observation:

- The rendered blue label text in review images is visually large and covers part of some small yellow balls.
- Despite the overlay text size, the predicted positions and prediction counts are broadly acceptable for a baseline.
- Phase 4 should consume bbox coordinates and confidence values, not rendered review-image label text.

## 13. Human Review Result

Phase 3 baseline accepted.

No immediate retraining is required.

No immediate return to Phase 2.5 is required.

`imgsz=960` is not needed at this point, but remains a future option if small-ball misses become obvious.

The model is acceptable for Phase 4 detect-only planning.

This does not mean the system is ready for real-time detection or mouse control.

## 14. Remaining Risks

- `negative_images = 17`, still limited.
- If false positives appear on yellow UI/buttons/lights in later testing, return to Phase 2.5 and add more negative samples.
- If small balls are missed in later testing, either add more small-ball samples or run a controlled `imgsz=960` experiment.
- Current review image overlay labels are visually large, but Phase 4 should consume bbox coordinates, not rendered label text.
- This baseline uses only YOLO11n at `imgsz=640`.
- The dataset is still small and may have correlated frames from continuous capture.
- Offline metrics do not prove real-time stability.

## 15. Final Phase 3 Decision

Phase 3 baseline training, offline validation, offline prediction review, and manual prediction review are complete.

Final decision:

- Phase 3 baseline accepted.
- No immediate retraining is required.
- No immediate return to Phase 2.5 is required.
- The model is acceptable for Phase 4 detect-only planning.
- Phase 4 implementation has not started in this task.

## 16. Phase 4 Readiness

The project may proceed to Phase 4 detect-only planning in a future task or conversation.

Phase 4 readiness means planning an offline-to-detect-only transition. It does not authorize:

- mouse movement
- mouse clicking
- coordinate mapping
- auto-aim
- closed-loop automation
- safety-gate bypass

Phase 4 must remain detect-only and must explicitly preserve the no-control boundary.

## 17. Phase Boundary Confirmation

No real-time detection was performed.

No AIMLAB live screen connection was performed.

No mouse movement was performed.

No mouse click was performed.

No coordinate mapping was implemented.

No auto-aim was implemented.

No closed-loop automation was implemented.

No anti-cheat bypass was attempted.
