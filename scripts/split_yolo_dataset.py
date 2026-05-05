from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split reviewed Phase 2 images and labels into YOLO dataset folders.")
    parser.add_argument("--input-images", type=Path, default=Path("data/selected/phase2_yellow_ball"))
    parser.add_argument("--input-labels", type=Path, default=Path("data/prelabels/phase2_yellow_ball/labels"))
    parser.add_argument("--out", type=Path, default=Path("data/yolo/aimlab_yellow_ball_v1"))
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--allow-empty-labels", action="store_true")
    return parser.parse_args()


def list_images(path: Path) -> list[Path]:
    return sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)


def validate_ratios(train_ratio: float, val_ratio: float, test_ratio: float) -> None:
    total = train_ratio + val_ratio + test_ratio
    if abs(total - 1.0) > 0.0001:
        raise ValueError(f"ratios must sum to 1.0, got {total}")


def split_items(items: list[tuple[Path, Path]], train_ratio: float, val_ratio: float) -> dict[str, list[tuple[Path, Path]]]:
    train_end = int(len(items) * train_ratio)
    val_end = train_end + int(len(items) * val_ratio)
    return {
        "train": items[:train_end],
        "val": items[train_end:val_end],
        "test": items[val_end:],
    }


def write_data_yaml(out: Path) -> None:
    content = """path: data/yolo/aimlab_yellow_ball_v1
train: images/train
val: images/val
test: images/test

names:
  0: yellow_ball
"""
    (out / "data.yaml").write_text(content, encoding="utf-8")


def write_readme(out: Path, splits: dict[str, list[tuple[Path, Path]]]) -> None:
    content = f"""# AIMLAB Yellow Ball YOLO Dataset v1

This dataset directory is prepared by Phase 2 only.

It contains reviewed image/label pairs split for future YOLO object-detection training.

Class:

- `0 yellow_ball`

Split counts:

- train: {len(splits["train"])}
- val: {len(splits["val"])}
- test: {len(splits["test"])}

Important: Phase 2 does not train YOLO and does not run YOLO inference. Labels generated from OpenCV pre-labeling must be human reviewed before this dataset is treated as training-ready.
"""
    (out / "README.md").write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    validate_ratios(args.train_ratio, args.val_ratio, args.test_ratio)

    pairs: list[tuple[Path, Path]] = []
    errors: list[str] = []
    for image_path in list_images(args.input_images):
        label_path = args.input_labels / f"{image_path.stem}.txt"
        if not label_path.exists():
            errors.append(f"missing label for {image_path}")
            continue
        if not args.allow_empty_labels and label_path.read_text(encoding="utf-8").strip() == "":
            errors.append(f"empty label requires --allow-empty-labels: {label_path}")
            continue
        pairs.append((image_path, label_path))

    if errors:
        print("SPLIT FAILED")
        for error in errors[:50]:
            print(error)
        if len(errors) > 50:
            print(f"... {len(errors) - 50} more errors")
        return 1

    random.Random(args.seed).shuffle(pairs)
    splits = split_items(pairs, args.train_ratio, args.val_ratio)

    for split_name in ("train", "val", "test"):
        image_out = args.out / "images" / split_name
        label_out = args.out / "labels" / split_name
        image_out.mkdir(parents=True, exist_ok=True)
        label_out.mkdir(parents=True, exist_ok=True)
        for image_path, label_path in splits[split_name]:
            shutil.copy2(image_path, image_out / image_path.name)
            shutil.copy2(label_path, label_out / label_path.name)

    write_data_yaml(args.out)
    write_readme(args.out, splits)
    print(f"total_pairs={len(pairs)}")
    print(f"train={len(splits['train'])}")
    print(f"val={len(splits['val'])}")
    print(f"test={len(splits['test'])}")
    print(f"dataset={args.out}")
    print("training_not_performed=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
