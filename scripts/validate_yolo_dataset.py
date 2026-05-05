from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Phase 2 YOLO detection dataset format.")
    parser.add_argument("--dataset", type=Path, default=Path("data/yolo/aimlab_yellow_ball_v1"))
    return parser.parse_args()


def list_images(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)


def validate_label_file(label_path: Path) -> tuple[list[str], int, Counter]:
    errors: list[str] = []
    box_count = 0
    class_distribution: Counter = Counter()
    text = label_path.read_text(encoding="utf-8")
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) != 5:
            errors.append(f"{label_path}:{line_number}: expected 5 columns, got {len(parts)}")
            continue
        class_id = parts[0]
        if class_id != "0":
            errors.append(f"{label_path}:{line_number}: class_id must be 0, got {class_id}")
        values: list[float] = []
        for value in parts[1:]:
            try:
                values.append(float(value))
            except ValueError:
                errors.append(f"{label_path}:{line_number}: non-numeric value {value}")
        if len(values) != 4:
            continue
        x_center, y_center, width, height = values
        for name, value in [
            ("x_center", x_center),
            ("y_center", y_center),
            ("width", width),
            ("height", height),
        ]:
            if value < 0 or value > 1:
                errors.append(f"{label_path}:{line_number}: {name} out of range 0..1: {value}")
        if width <= 0 or height <= 0:
            errors.append(f"{label_path}:{line_number}: width and height must be > 0")
        box_count += 1
        class_distribution[class_id] += 1
    return errors, box_count, class_distribution


def main() -> int:
    args = parse_args()
    dataset = args.dataset
    errors: list[str] = []
    stats = {
        "total_images": 0,
        "train_images": 0,
        "val_images": 0,
        "test_images": 0,
        "total_labels": 0,
        "positive_images": 0,
        "negative_images": 0,
        "total_boxes": 0,
        "invalid_label_files": 0,
        "missing_label_files": 0,
    }
    class_distribution: Counter = Counter()

    required_paths = [
        dataset / "data.yaml",
        dataset / "images" / "train",
        dataset / "images" / "val",
        dataset / "images" / "test",
        dataset / "labels" / "train",
        dataset / "labels" / "val",
        dataset / "labels" / "test",
    ]
    for path in required_paths:
        if not path.exists():
            errors.append(f"missing required path: {path}")

    for split_name in ("train", "val", "test"):
        image_dir = dataset / "images" / split_name
        label_dir = dataset / "labels" / split_name
        images = list_images(image_dir)
        stats[f"{split_name}_images"] = len(images)
        stats["total_images"] += len(images)
        for image_path in images:
            label_path = label_dir / f"{image_path.stem}.txt"
            if not label_path.exists():
                stats["missing_label_files"] += 1
                errors.append(f"missing label file: {label_path}")
                continue
            stats["total_labels"] += 1
            label_errors, box_count, label_distribution = validate_label_file(label_path)
            if label_errors:
                stats["invalid_label_files"] += 1
                errors.extend(label_errors)
            if box_count > 0:
                stats["positive_images"] += 1
            else:
                stats["negative_images"] += 1
            stats["total_boxes"] += box_count
            class_distribution.update(label_distribution)

    for key, value in stats.items():
        print(f"{key}={value}")
    print(f"class_distribution={dict(class_distribution)}")

    if errors:
        print("VALIDATION FAILED")
        for error in errors[:100]:
            print(error)
        if len(errors) > 100:
            print(f"... {len(errors) - 100} more errors")
        return 1

    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
