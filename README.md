# AIAIM

AIAIM is a local offline AIMLAB experiment for staged research into yellow-ball detection, localization, and eventually gated mouse-control feedback.

Current status: Phase 3 baseline accepted. Phase 4 is allowed only for detect-only planning; Phase 4 implementation has not started.

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

## Start Here

Read these documents before any future change:

- `AGENTS.md`
- `docs/project-overview.md`
- `docs/safety-boundary.md`
- `docs/phase-roadmap.md`
- `docs/agent-team.md`
- `docs/mcp-plan.md`

Every phase must end with a report in `docs/phase-reports/`.
