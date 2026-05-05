# Phase 2 Dataset Runbook

All commands start from the project directory:

```powershell
cd /d D:\桌面desktop\AIAIM
```

## 1. Check Phase 1 Raw Screenshots

```powershell
dir data\raw\screenshots\*.png
dir data\raw\screenshots\*.json
```

The expected Phase 1 input is 116 PNG screenshots with corresponding JSON metadata.

## 2. Run Prepare Dry-Run

```powershell
python scripts\prepare_phase2_dataset.py --dry-run
```

Review the printed counts:

- `scanned_png_count`
- `selected_count`
- `skipped_count`
- `missing_metadata_count`
- `blocked_count`
- `non_foreground_count`
- `invalid_size_count`

## 3. Run Prepare Selection

```powershell
python scripts\prepare_phase2_dataset.py
```

Expected output:

```text
data\selected\phase2_yellow_ball\dataset_manifest.csv
```

This copies selected screenshots. It does not modify raw screenshots.

## 4. Install Phase 2 Pre-Label Dependencies

```powershell
pip install -r requirements-phase2.txt
```

Allowed dependencies:

- `opencv-python`
- `numpy`

Do not install YOLO training dependencies for Phase 2.

## 5. Run OpenCV Pre-Label Dry-Run

```powershell
python scripts\prelabel_yellow_ball_opencv.py --dry-run
```

This checks input images only and does not write labels or review images.

## 6. Generate OpenCV Draft Labels and Review Images

```powershell
python scripts\prelabel_yellow_ball_opencv.py --overwrite --review-images
```

Default behavior uses Phase 1 metadata to restrict detection to the AIMLAB window ROI:

```powershell
python scripts\prelabel_yellow_ball_opencv.py --roi-mode metadata --metadata-dir data\raw\screenshots --ignore-bottom-ratio 0.12 --overwrite --review-images
```

If metadata is missing or invalid, the script falls back to ignoring the bottom 12% of the screenshot to avoid Windows taskbar false positives.

To force the fallback mode:

```powershell
python scripts\prelabel_yellow_ball_opencv.py --roi-mode ignore-bottom --ignore-bottom-ratio 0.12 --overwrite --review-images
```

Expected outputs:

```text
data\prelabels\phase2_yellow_ball\labels\
data\prelabels\phase2_yellow_ball\review_images\
data\prelabels\phase2_yellow_ball\prelabel_manifest.csv
```

OpenCV pre-labeling is offline annotation assistance only. It does not connect to AIMLAB, the collector, or any input device.

The review image is drawn on the original full screenshot, but detections are only produced from the ROI. The manifest records `roi_source`, `roi_x`, `roi_y`, `roi_w`, `roi_h`, and `ignored_bottom_ratio`.

## 7. Inspect Review Images

Open:

```text
data\prelabels\phase2_yellow_ball\review_images\
```

Check each overlay:

- Correct yellow-ball boxes can remain.
- False detections on yellow UI, text, highlights, or effects must be removed.
- Any box outside the AIMLAB ROI or on the Windows taskbar indicates a bug and should be reported before continuing.
- Missed yellow balls must be manually added.
- Loose or incorrect boxes must be adjusted.
- No-yellow-ball images should keep empty `.txt` labels.

## 8. Correct Labels With LabelImg

Use LabelImg to review and correct:

- Open images from `data\selected\phase2_yellow_ball\`.
- Load labels from `data\prelabels\phase2_yellow_ball\labels\`.
- Use YOLO format.
- Use only class `yellow_ball`.
- Fix missed boxes.
- Delete false boxes.
- Adjust inaccurate boxes.
- Keep empty `.txt` labels for negative samples.

## 9. Ensure Every Image Has a Label

```powershell
dir data\selected\phase2_yellow_ball\*.png
dir data\prelabels\phase2_yellow_ball\labels\*.txt
```

Every image must have a same-stem `.txt` label file before splitting.

## 10. Split Dataset

```powershell
python scripts\split_yolo_dataset.py --allow-empty-labels
```

Default split ratio is 70 / 20 / 10.

Current completed split result:

```text
total_pairs=116
train=81
val=23
test=12
dataset=data\yolo\aimlab_yellow_ball_v1
training_not_performed=true
```

## 11. Validate Dataset

```powershell
python scripts\validate_yolo_dataset.py
```

Expected success output:

```text
VALIDATION PASSED
```

If validation fails, fix the listed label or structure errors and run validation again.

Current completed validation result:

```text
total_images=116
train_images=81
val_images=23
test_images=12
total_labels=116
positive_images=115
negative_images=1
total_boxes=689
invalid_label_files=0
missing_label_files=0
class_distribution={'0': 689}
VALIDATION PASSED
```

The current negative sample count is low. If future model checks show false positives, add negative samples toward a 10%-20% negative ratio.

## 12. View data.yaml

```powershell
type data\yolo\aimlab_yellow_ball_v1\data.yaml
```

Expected class:

```text
0: yellow_ball
```

## 13. Phase 2 Acceptance

Phase 2 is acceptable when:

- Selected screenshots are copied from raw without modifying raw.
- `dataset_manifest.csv` exists.
- OpenCV draft labels and review images exist.
- Human review has corrected labels.
- Dataset split exists.
- `data.yaml` exists.
- `validate_yolo_dataset.py` passes.

Current status: Phase 2 acceptance criteria are met for the current reviewed dataset at `data\yolo\aimlab_yellow_ball_v1\`.

## 14. Explicitly Forbidden in Phase 2

Do not run YOLO training commands.

Do not run YOLO inference commands.

Do not run real-time detection.

Do not move or click the mouse.

Do not implement coordinate mapping or closed-loop automation.

No YOLO training was performed.

No YOLO inference was performed.

No real-time detection was performed.

No mouse movement was performed.

No mouse click was performed.

No coordinate mapping was implemented.

No closed-loop automation was implemented.

No anti-cheat bypass was attempted.
