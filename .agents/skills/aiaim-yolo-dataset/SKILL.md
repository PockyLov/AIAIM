# Skill: aiaim-yolo-dataset

## Purpose

Use this skill when working on AIAIM screenshot datasets, YOLO labels, dataset structure, model training, validation split, and inference evaluation.

This skill does not apply to Phase 0 implementation. During Phase 0 it is only a planning document.

---

## When to Trigger

Trigger this skill when the user asks about:

1. Collecting AIMLAB screenshots.
2. Labeling yellow balls.
3. Creating YOLO-format datasets.
4. Splitting train/val data.
5. Training YOLO.
6. Evaluating detection performance.
7. Debugging false positives or false negatives.
8. Organizing dataset files.

---

## Dataset Principles

Codex must keep these separate:

1. Raw screenshots.
2. Annotated images.
3. YOLO label files.
4. Dataset config.
5. Train/val/test split.
6. Model outputs.
7. Evaluation reports.

Do not mix dataset files with code files.

---

## Recommended Future Dataset Layout

Future dataset layout may follow:

```text
data/
├─ raw/
│  └─ screenshots/
├─ yolo/
│  ├─ images/
│  │  ├─ train/
│  │  └─ val/
│  ├─ labels/
│  │  ├─ train/
│  │  └─ val/
│  └─ dataset.yaml
└─ reports/
   └─ dataset-summary.md

During Phase 0, Codex must not create real dataset files unless the user explicitly asks for placeholder README files only.

YOLO Label Rule

For a yellow ball target, labels must represent the visible yellow ball bounding box.

Future YOLO label files should use normalized YOLO format:

class_id x_center y_center width height

Where all coordinates are normalized between 0 and 1 relative to the image dimensions.

Class design should start simple:

0 yellow_ball

Do not introduce unnecessary classes unless the user requests a more complex target taxonomy.

Data Collection Principles

When the project reaches Phase 2, dataset collection should consider:

Different AIMLAB scenes.
Different target positions.
Different backgrounds.
Different lighting or visual effects.
Motion blur if relevant.
Negative samples if useful.
Screenshots where target is partially visible, if applicable.
Validation Checklist

For dataset work, Codex must validate:

Images and labels count match.
Label files are not empty unless intentionally negative.
Class IDs are valid.
Label coordinates are within 0 to 1.
Train/val split exists.
Dataset config points to correct paths.
A dataset summary report exists.
Forbidden Actions

Codex must not:

Train YOLO during Phase 0.
Write screenshot collector code during Phase 0.
Generate fake labels and present them as real data.
Overwrite raw data without backup.
Mix model weights into the dataset folder.
Skip dataset summary reporting.
Completion Criteria

This skill is applied correctly when dataset work is reproducible, separated from code, documented, and validated before training.
