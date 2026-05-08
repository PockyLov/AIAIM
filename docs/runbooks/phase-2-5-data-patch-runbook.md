# Phase 2.5 Data Patch Runbook

Phase 2.5 builds a draft review package for the expanded AIMLAB yellow-ball dataset version `v1_1`.

This is not Phase 3. Do not train YOLO, run YOLO inference, run real-time detection, move the mouse, click the mouse, implement coordinate mapping, or build closed-loop automation.

All commands start from:

```powershell
Set-Location "D:\桌面desktop\AIAIM"
```

## Inputs

Raw source:

```text
data/raw/screenshots/
```

Current raw counts:

- PNG: 364
- JSON: 368

JSON files may be greater than PNG files because blocked capture attempts write metadata without screenshots. Orphan JSON and blocked metadata are counted but not included as YOLO images.

Existing reviewed dataset to preserve:

```text
data/yolo/aimlab_yellow_ball_v1/
```

Do not overwrite, delete, or modify `aimlab_yellow_ball_v1`.

## Generate Phase 2.5 Draft / Review Package

Dry-run:

```powershell
.\.venv\Scripts\python.exe scripts\phase25_data_patch.py --dry-run
```

Generate draft labels and review images:

```powershell
.\.venv\Scripts\python.exe scripts\phase25_data_patch.py --overwrite
```

Outputs:

```text
data/selected/aimlab_yellow_ball_v1_1/
data/prelabels/aimlab_yellow_ball_v1_1/labels/
data/review/aimlab_yellow_ball_v1_1/
data/review/aimlab_yellow_ball_v1_1/review_manifest.csv
data/review/aimlab_yellow_ball_v1_1/phase25_summary.csv
data/yolo/aimlab_yellow_ball_v1_1/README.md
```

The `data/yolo/aimlab_yellow_ball_v1_1/` directory is a placeholder until human review is complete. It is not a finalized dataset yet.

## Review Manifest

`review_manifest.csv` includes:

- `image_name`
- `image_path`
- `metadata_path`
- `split_candidate`
- `source`
- `predicted_box_count`
- `is_candidate_negative`
- `needs_human_review`
- `notes`

Every row must be treated as requiring human review.

## Human Review

Open:

```text
data/review/aimlab_yellow_ball_v1_1/
```

Review each image:

- Keep correct yellow-ball boxes.
- Remove false positives on UI, highlights, effects, or non-target yellow areas.
- Add missed yellow balls.
- Tighten loose boxes.
- Keep empty `.txt` files for true negative samples.

Draft labels live in:

```text
data/prelabels/aimlab_yellow_ball_v1_1/labels/
```

Negative samples must have an existing empty `.txt` file. Missing label files are not valid negative samples.

## Finalize v1_1 After Review

Only after human review is complete, split into the final v1_1 dataset:

```powershell
.\.venv\Scripts\python.exe scripts\split_yolo_dataset.py --input-images data\selected\aimlab_yellow_ball_v1_1 --input-labels data\prelabels\aimlab_yellow_ball_v1_1\labels --out data\yolo\aimlab_yellow_ball_v1_1 --allow-empty-labels
```

Then update `data/yolo/aimlab_yellow_ball_v1_1/data.yaml` path if needed to:

```text
path: data/yolo/aimlab_yellow_ball_v1_1
```

## Validate v1_1 After Finalize

```powershell
.\.venv\Scripts\python.exe scripts\validate_yolo_dataset.py --dataset data\yolo\aimlab_yellow_ball_v1_1
```

Expected after successful finalize:

```text
VALIDATION PASSED
```

## Explicit Non-Goals

No YOLO training was performed.

No YOLO inference was performed.

No real-time detection was performed.

No mouse movement was performed.

No mouse click was performed.

No coordinate mapping was implemented.

No closed-loop automation was implemented.

No anti-cheat bypass was attempted.
