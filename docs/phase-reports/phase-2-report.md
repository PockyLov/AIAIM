# Phase 2 Report - Dataset Preparation / Annotation Pipeline

## 1. Phase 2 Name

Phase 2: Dataset Preparation / Annotation Pipeline.

## 2. Phase 2 Goal

Prepare Phase 1 AIMLAB screenshots as a reviewed YOLO-format object-detection dataset for the single class `0 yellow_ball`.

## 3. Phase 2 Scope

- Organize Phase 1 PNG screenshots and JSON metadata.
- Create selected image and dataset directory structure.
- Filter usable screenshots using Phase 1 metadata.
- Define yellow-ball annotation rules.
- Add OpenCV offline pre-labeling assistance for static screenshots.
- Generate draft YOLO labels and review overlay images.
- Provide human review and correction workflow.
- Prepare train / val / test split tooling.
- Generate `data.yaml`.
- Validate YOLO label format and dataset structure.

## 4. Phase 2 Non-Goals

- No YOLO training was performed.
- No YOLO inference was performed.
- No real-time detection was performed.
- No mouse movement was performed.
- No mouse click was performed.
- No coordinate mapping was implemented.
- No closed-loop automation was implemented.
- No anti-cheat bypass was attempted.
- No AIMLAB background screenshot extension was implemented.
- Phase 3 was not entered.

OpenCV pre-labeling was implemented only as offline annotation assistance for static screenshots. It is not real-time detection and is not used for control.

## 5. Phase 1 Input Assets

Input source:

```text
data/raw/screenshots/
```

Phase 1 accepted assets:

- 116 PNG screenshots
- Corresponding JSON metadata files
- Metadata verifies AIMLAB foreground, screenshot dimensions, monitor rect, capture mode, and blocked status

## 6. New Directories

- `data/selected/phase2_yellow_ball/`
- `data/prelabels/phase2_yellow_ball/`
- `data/prelabels/phase2_yellow_ball/labels/`
- `data/prelabels/phase2_yellow_ball/review_images/`
- `data/prelabels/phase2_yellow_ball/rejected/`
- `data/yolo/aimlab_yellow_ball_v1/`
- `data/yolo/aimlab_yellow_ball_v1/images/train/`
- `data/yolo/aimlab_yellow_ball_v1/images/val/`
- `data/yolo/aimlab_yellow_ball_v1/images/test/`
- `data/yolo/aimlab_yellow_ball_v1/labels/train/`
- `data/yolo/aimlab_yellow_ball_v1/labels/val/`
- `data/yolo/aimlab_yellow_ball_v1/labels/test/`
- `scripts/`

## 7. New Scripts

- `scripts/prepare_phase2_dataset.py`
- `scripts/prelabel_yellow_ball_opencv.py`
- `scripts/split_yolo_dataset.py`
- `scripts/validate_yolo_dataset.py`

## 8. New Documents

- `docs/annotation-guidelines.md`
- `docs/dataset-preparation.md`
- `docs/runbooks/phase-2-dataset-runbook.md`
- `docs/phase-reports/phase-2-report.md`

## 9. OpenCV Offline Pre-Labeling Plan

`scripts/prelabel_yellow_ball_opencv.py` reads selected static screenshots, applies HSV yellow thresholding, morphological cleanup, contour filtering, area filtering, aspect-ratio filtering, and circularity filtering.

Taskbar false-positive fix:

- Pre-labeling no longer scans the entire screenshot by default.
- Default `--roi-mode metadata` reads Phase 1 metadata from `data/raw/screenshots`.
- If metadata `window_rect` and `monitor_rect` are available, detection runs only inside the AIMLAB window ROI.
- If metadata is unavailable, fallback `ignore-bottom` mode ignores the bottom 12% of the image to reduce Windows taskbar false positives.
- YOLO labels are still written in original full-screenshot coordinates normalized by the original image width and height.
- Review images are drawn on the original full screenshot, but only ROI detections are shown.
- `prelabel_manifest.csv` now records `roi_source`, `roi_x`, `roi_y`, `roi_w`, `roi_h`, and `ignored_bottom_ratio`.

It writes:

- Draft YOLO label files under `data/prelabels/phase2_yellow_ball/labels/`
- Review overlay images under `data/prelabels/phase2_yellow_ball/review_images/`
- `prelabel_manifest.csv`

All pre-labels require human review before they can be considered final labels.

## 10. Annotation Class

Only one class is defined:

```text
0 yellow_ball
```

## 11. Annotation Rule Summary

- Box the visible yellow-ball body.
- Keep boxes close to the ball outline.
- Do not label yellow UI, text, crosshair, weapon effects, background highlights, or uncertain tiny points.
- Label every clear yellow ball in the image.
- Remove OpenCV false positives.
- Add missed yellow balls.

## 12. Negative Sample Rule

Images without yellow balls may be retained as negative samples. Their same-stem `.txt` label file must exist and remain empty.

Recommended negative sample ratio: 10%-20%.

## 13. Train / Val / Test Strategy

Default split:

- train: 70%
- val: 20%
- test: 10%

The split script copies images and labels into the YOLO dataset directory. It does not move or delete source files.

## 14. Current Status

- Phase 2 dataset infrastructure prepared.
- OpenCV offline pre-labeling assistance prepared.
- Selected dataset step completed.
- OpenCV pre-label step completed.
- Manual review / label correction completed by the user.
- Train / val / test split completed.
- Dataset validation completed.
- `data.yaml` generated under `data/yolo/aimlab_yellow_ball_v1/`.
- `scripts/prepare_phase2_dataset.py --dry-run` passed with 116 scanned PNG and 116 selected candidates.
- `scripts/prepare_phase2_dataset.py` copied 116 selected PNG files and wrote `data/selected/phase2_yellow_ball/dataset_manifest.csv`.
- `scripts/prelabel_yellow_ball_opencv.py --dry-run` scanned 116 selected images.
- Human review has been completed for the current Phase 2 dataset.
- Dataset path: `data/yolo/aimlab_yellow_ball_v1/`.
- YOLO training not performed.
- YOLO inference not performed.

ROI pre-label rerun result:

- Old Phase 2 prelabel labels and review images were cleared.
- OpenCV dependencies were installed in the project Windows virtual environment from `requirements-phase2.txt`.
- `scripts/prelabel_yellow_ball_opencv.py --overwrite --review-images` was rerun with default metadata ROI mode.
- Input images: 116.
- `detected_count`: 116.
- `no_detection_count`: 0.
- `total_boxes`: 695.
- Label files generated: 116.
- Review images generated: 116.
- Manifest rows: 695.
- `roi_source`: metadata for all detections.
- Sample ROI: `x=0`, `y=0`, `w=1920`, `h=1040`.
- `bbox_roi_violations`: 0.
- Maximum detected bbox bottom: 951, below the ROI bottom 1040.
- Windows taskbar false positives are excluded by the metadata ROI check in this rerun.

Split result:

- Command: `split_yolo_dataset.py --allow-empty-labels`
- `total_pairs`: 116
- `train`: 81
- `val`: 23
- `test`: 12
- `dataset`: `data/yolo/aimlab_yellow_ball_v1`
- `training_not_performed`: true

Validation result:

- Command: `validate_yolo_dataset.py`
- `total_images`: 116
- `train_images`: 81
- `val_images`: 23
- `test_images`: 12
- `total_labels`: 116
- `positive_images`: 115
- `negative_images`: 1
- `total_boxes`: 689
- `invalid_label_files`: 0
- `missing_label_files`: 0
- `class_distribution`: `{'0': 689}`
- Result: `VALIDATION PASSED`

Explicit safety confirmation:

- No YOLO training was performed.
- No YOLO inference was performed.
- No real-time detection was performed.
- No mouse movement was performed.
- No mouse click was performed.
- No coordinate mapping was implemented.
- No closed-loop automation was implemented.
- No anti-cheat bypass was attempted.

## 15. Risks

- Current data volume is small for robust training.
- Continuous screenshots may have high duplication.
- OpenCV thresholds may falsely label yellow UI.
- OpenCV may miss small yellow balls.
- Manual annotation consistency may vary.
- Negative samples are currently low: `negative_images=1`. If future model checks show false positives, expand negative samples toward 10%-20% of the dataset.
- Train / val / test leakage is possible if near-duplicate frames are split across sets.

## 16. Next Steps

1. Preserve the completed Phase 2 dataset at `data/yolo/aimlab_yellow_ball_v1/`.
2. If future validation shows false positives, collect and label additional negative samples toward a 10%-20% negative ratio.
3. Re-read `AGENTS.md`, `docs/phase-roadmap.md`, and `docs/safety-boundary.md` before any Phase 3 work.
4. Enter Phase 3 only with explicit user approval.
