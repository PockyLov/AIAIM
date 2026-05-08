# Phase 2.5 Report - Data Patch / v1_1 Draft Review Package

## Goal

Build a Phase 2.5 data patch from expanded Phase 1 raw screenshots and prepare a draft review package for `aimlab_yellow_ball_v1_1`.

This is not Phase 3.

## Scope

- Read all valid PNG screenshots from `data/raw/screenshots/`.
- Match same-stem JSON metadata when available.
- Count orphan JSON metadata, blocked metadata, and metadata with `image_path=None`.
- Use metadata `window_rect` / `monitor_rect` ROI to reduce taskbar and desktop false positives.
- Generate draft YOLO labels for class `0 yellow_ball`.
- Generate review images for human inspection.
- Generate `review_manifest.csv`.
- Preserve existing `data/yolo/aimlab_yellow_ball_v1/`.
- Create only a placeholder for `data/yolo/aimlab_yellow_ball_v1_1/` until human review is complete.

## Inputs

- Raw PNG count: 364
- Raw JSON count: 368
- Source: `data/raw/screenshots/`
- Existing dataset preserved: `data/yolo/aimlab_yellow_ball_v1/`

JSON count is higher than PNG count because blocked capture attempts may write metadata without screenshots. Orphan JSON and blocked metadata are counted but not included as YOLO images.

## Outputs

- `data/selected/aimlab_yellow_ball_v1_1/`
- `data/prelabels/aimlab_yellow_ball_v1_1/labels/`
- `data/review/aimlab_yellow_ball_v1_1/`
- `data/review/aimlab_yellow_ball_v1_1/review_manifest.csv`
- `data/review/aimlab_yellow_ball_v1_1/phase25_summary.csv`
- `data/yolo/aimlab_yellow_ball_v1_1/README.md`

## Processing Rules

- Valid PNG files require valid same-stem metadata.
- `blocked=True` metadata is not included as YOLO images.
- `image_path=None` metadata is not included as YOLO images.
- Missing or invalid metadata PNGs are skipped and counted.
- Orphan JSON files are counted and ignored for image labeling.
- Draft labels are not final truth.
- Negative samples are represented by existing empty `.txt` files.

## Current Execution Results

Command:

```powershell
.\.venv\Scripts\python.exe scripts\phase25_data_patch.py --overwrite
```

Results:

- `raw_png_count`: 364
- `raw_json_count`: 368
- `valid_png_count`: 364
- `selected_count`: 364
- `skipped_png_count`: 0
- `missing_metadata_png_count`: 0
- `invalid_metadata_png_count`: 0
- `blocked_png_count`: 0
- `image_path_none_png_count`: 0
- `invalid_size_png_count`: 0
- `orphan_json_count`: 4
- `blocked_json_count`: 4
- `image_path_none_json_count`: 4
- `draft_label_count`: 364
- `review_image_count`: 364
- `candidate_negative_images`: 7
- `predicted_boxes`: 2118

Generated files:

- 364 selected PNG files under `data/selected/aimlab_yellow_ball_v1_1/`
- 364 draft label `.txt` files under `data/prelabels/aimlab_yellow_ball_v1_1/labels/`
- 364 review images under `data/review/aimlab_yellow_ball_v1_1/`
- `data/review/aimlab_yellow_ball_v1_1/review_manifest.csv`
- `data/review/aimlab_yellow_ball_v1_1/phase25_summary.csv`
- `data/yolo/aimlab_yellow_ball_v1_1/README.md`

Final v1_1 dataset generated: no.

Human review required: yes.

Existing `data/yolo/aimlab_yellow_ball_v1/` was not used as an output target for this Phase 2.5 package.

## Review Status

Human review is required. Phase 2.5 does not claim that labels are final.

Final train / val / test split and validation for `aimlab_yellow_ball_v1_1` must happen only after human review is complete.

## Finalize Command After Review

```powershell
.\.venv\Scripts\python.exe scripts\split_yolo_dataset.py --input-images data\selected\aimlab_yellow_ball_v1_1 --input-labels data\prelabels\aimlab_yellow_ball_v1_1\labels --out data\yolo\aimlab_yellow_ball_v1_1 --allow-empty-labels
```

## Validate Command After Finalize

```powershell
.\.venv\Scripts\python.exe scripts\validate_yolo_dataset.py --dataset data\yolo\aimlab_yellow_ball_v1_1
```

## Explicit Safety Confirmation

No YOLO training was performed.

No YOLO inference was performed.

No real-time detection was performed.

No mouse movement was performed.

No mouse click was performed.

No coordinate mapping was implemented.

No closed-loop automation was implemented.

No anti-cheat bypass was attempted.
