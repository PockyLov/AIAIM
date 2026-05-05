# Dataset Preparation - Phase 2

## Goal

Phase 2 prepares the Phase 1 AIMLAB screenshots for a future YOLO object-detection dataset. It creates dataset structure, selection manifests, offline OpenCV pre-label drafts, human review workflow, train / val / test splitting, `data.yaml`, and dataset validation.

## Phase Boundaries

Phase 1 produced foreground-gated AIMLAB screenshots, metadata, and logs.

Phase 2 uses those static screenshots to prepare a reviewed dataset. OpenCV pre-labeling is allowed only as offline annotation assistance.

Phase 3 is the first phase where YOLO training may happen. Phase 2 does not train, run inference, control the mouse, map coordinates, or automate AIMLAB.

## Data Locations

Raw Phase 1 source:

```text
data/raw/screenshots/
```

Selected Phase 2 images:

```text
data/selected/phase2_yellow_ball/
```

OpenCV pre-label outputs:

```text
data/prelabels/phase2_yellow_ball/
```

YOLO dataset output:

```text
data/yolo/aimlab_yellow_ball_v1/
```

Current Phase 2 dataset status:

- Selected images completed.
- OpenCV offline pre-labeling completed.
- Manual review / correction completed.
- Train / val / test split completed.
- `data.yaml` generated.
- Dataset validation passed.

## Prepare Selected Screenshots

Dry-run:

```powershell
python scripts/prepare_phase2_dataset.py --dry-run
```

Run selection and copy:

```powershell
python scripts/prepare_phase2_dataset.py
```

Output manifest:

```text
data/selected/phase2_yellow_ball/dataset_manifest.csv
```

The prepare script only filters and copies. It does not pre-label images.

## OpenCV Offline Pre-Labeling

Install Phase 2 pre-label dependencies:

```powershell
pip install -r requirements-phase2.txt
```

Dry-run:

```powershell
python scripts/prelabel_yellow_ball_opencv.py --dry-run
```

Generate draft labels and review images:

```powershell
python scripts/prelabel_yellow_ball_opencv.py --overwrite --review-images
```

Default ROI behavior:

- `--roi-mode metadata` uses Phase 1 metadata from `--metadata-dir data/raw/screenshots`.
- When metadata `window_rect` and `monitor_rect` are available, HSV detection runs only inside the AIMLAB window ROI.
- Windows taskbar, desktop, and other UI outside the AIMLAB window are excluded.
- If metadata is unavailable, the fallback ignores the bottom `--ignore-bottom-ratio` of the image, default `0.12`.
- `--roi-mode ignore-bottom` forces bottom exclusion.
- `--roi-mode full` scans the full image and should be used only for debugging.

Outputs:

```text
data/prelabels/phase2_yellow_ball/labels/
data/prelabels/phase2_yellow_ball/review_images/
data/prelabels/phase2_yellow_ball/prelabel_manifest.csv
```

These labels are drafts only and must be manually reviewed.

The generated YOLO label coordinates are always converted back to full original screenshot coordinates and normalized by the original full image width and height.

## Review Images

Open `data/prelabels/phase2_yellow_ball/review_images/` and inspect each overlay:

- Keep correct boxes.
- Delete false boxes on UI, score text, effects, or highlights.
- Add missed yellow-ball boxes.
- Tighten boxes that are too large or too loose.
- Preserve empty `.txt` files for negative samples.

## Human Review / Correction

Use LabelImg as the preferred correction tool:

1. Open `data/selected/phase2_yellow_ball/`.
2. Load YOLO labels from `data/prelabels/phase2_yellow_ball/labels/`.
3. Use only class `yellow_ball`.
4. Save labels in YOLO format.
5. Ensure every image has a same-stem `.txt` label file.

## Split Dataset

Recommended split ratio: 70 / 20 / 10.

```powershell
python scripts/split_yolo_dataset.py --allow-empty-labels
```

Output:

```text
data/yolo/aimlab_yellow_ball_v1/
```

Current split result:

- total pairs: 116
- train: 81
- val: 23
- test: 12
- dataset: `data/yolo/aimlab_yellow_ball_v1/`
- training was not performed

## Validate Dataset

```powershell
python scripts/validate_yolo_dataset.py
```

Expected success output:

```text
VALIDATION PASSED
```

Validation checks file structure, matching image/label pairs, YOLO label format, class IDs, normalized coordinates, empty negative labels, and class distribution.

Current validation result:

- total images: 116
- train images: 81
- val images: 23
- test images: 12
- total labels: 116
- positive images: 115
- negative images: 1
- total boxes: 689
- invalid label files: 0
- missing label files: 0
- class distribution: `{'0': 689}`
- result: `VALIDATION PASSED`

The current dataset has only one negative image. If future model checks show false positives, add negative samples until negatives are closer to 10%-20% of the dataset.

## Dataset Size Guidance

The current 116 Phase 1 screenshots are enough to validate the Phase 2 workflow.

Before Phase 3 training, expand toward:

- Positive samples: 200-300
- Negative samples: 30-60
- Total: 250-350

## Phase 2 Non-Goals

Phase 2 does not train YOLO, run YOLO inference, perform real-time detection, move the mouse, click the mouse, map coordinates, or implement closed-loop automation.

No YOLO training was performed. No YOLO inference was performed. No real-time detection was performed. No mouse movement was performed. No mouse click was performed. No coordinate mapping was implemented. No closed-loop automation was implemented. No anti-cheat bypass was attempted.

Phase 3 is the first phase that may use `data.yaml` for YOLO training.
