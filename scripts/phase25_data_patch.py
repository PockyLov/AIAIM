from __future__ import annotations

import argparse
import csv
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prelabel_yellow_ball_opencv import (
    Candidate,
    build_roi,
    detect_candidates,
    draw_review,
    load_config,
    to_full_image_candidates,
)


IMAGE_EXTENSIONS = {".png"}
CLASS_ID = 0

REVIEW_FIELDS = [
    "image_name",
    "image_path",
    "metadata_path",
    "split_candidate",
    "source",
    "predicted_box_count",
    "is_candidate_negative",
    "needs_human_review",
    "notes",
]

SUMMARY_FIELDS = [
    "raw_png_count",
    "raw_json_count",
    "valid_png_count",
    "selected_count",
    "skipped_png_count",
    "missing_metadata_png_count",
    "invalid_metadata_png_count",
    "blocked_png_count",
    "image_path_none_png_count",
    "invalid_size_png_count",
    "orphan_json_count",
    "blocked_json_count",
    "image_path_none_json_count",
    "draft_label_count",
    "review_image_count",
    "candidate_negative_images",
    "predicted_boxes",
]


@dataclass(frozen=True)
class SelectedImage:
    source_image: Path
    selected_image: Path
    metadata_path: Path
    metadata: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 2.5 data patch draft/review package builder.")
    parser.add_argument("--raw", type=Path, default=Path("data/raw/screenshots"))
    parser.add_argument("--selected-out", type=Path, default=Path("data/selected/aimlab_yellow_ball_v1_1"))
    parser.add_argument("--prelabel-out", type=Path, default=Path("data/prelabels/aimlab_yellow_ball_v1_1"))
    parser.add_argument("--review-out", type=Path, default=Path("data/review/aimlab_yellow_ball_v1_1"))
    parser.add_argument("--dataset-out", type=Path, default=Path("data/yolo/aimlab_yellow_ball_v1_1"))
    parser.add_argument("--config", type=Path, default=Path("config/phase2_prelabel_config.json"))
    parser.add_argument("--roi-mode", choices=("metadata", "ignore-bottom", "full"), default="metadata")
    parser.add_argument("--ignore-bottom-ratio", type=float, default=0.12)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and value > 0


def valid_metadata(metadata: dict[str, Any]) -> tuple[bool, str]:
    if metadata.get("aimlab_window_found") is not True:
        return False, "aimlab_window_not_found"
    if metadata.get("is_foreground") is not True:
        return False, "non_foreground"
    if metadata.get("blocked") is True:
        return False, "blocked"
    if metadata.get("image_path") in (None, ""):
        return False, "image_path_none"
    if not is_positive_number(metadata.get("screenshot_width")) or not is_positive_number(metadata.get("screenshot_height")):
        return False, "invalid_size"
    return True, ""


def ensure_clean_dir(path: Path, overwrite: bool) -> None:
    if path.exists() and overwrite:
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def yolo_line(candidate: Candidate, image_w: int, image_h: int) -> str:
    x_center, y_center, width, height = candidate.yolo_values(image_w, image_h)
    return f"{CLASS_ID} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"


def write_dataset_readme(dataset_out: Path) -> None:
    dataset_out.mkdir(parents=True, exist_ok=True)
    (dataset_out / "README.md").write_text(
        """# AIMLAB Yellow Ball Dataset v1_1

Phase 2.5 status: draft/review package generated.

This directory is reserved for the finalized v1_1 YOLO dataset after human review.

Do not treat the current draft labels as final training labels until review is complete and the finalize/split step has been run.

No YOLO training was performed.
No YOLO inference was performed.
No real-time detection was performed.
No mouse movement was performed.
No mouse click was performed.
No coordinate mapping was implemented.
No closed-loop automation was implemented.
No anti-cheat bypass was attempted.
""",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    label_dir = args.prelabel_out / "labels"
    review_manifest_path = args.review_out / "review_manifest.csv"
    summary_path = args.review_out / "phase25_summary.csv"

    raw_pngs = sorted(args.raw.glob("*.png"))
    raw_jsons = sorted(args.raw.glob("*.json"))
    if args.limit is not None:
        raw_pngs = raw_pngs[: args.limit]

    png_stems = {path.stem for path in raw_pngs}
    orphan_jsons = [path for path in raw_jsons if path.stem not in png_stems]
    blocked_json_count = 0
    image_path_none_json_count = 0
    for json_path in raw_jsons:
        metadata = read_json(json_path)
        if not metadata:
            continue
        if metadata.get("blocked") is True:
            blocked_json_count += 1
        if metadata.get("image_path") in (None, ""):
            image_path_none_json_count += 1

    stats = {
        "raw_png_count": len(list(args.raw.glob("*.png"))),
        "raw_json_count": len(raw_jsons),
        "valid_png_count": 0,
        "selected_count": 0,
        "skipped_png_count": 0,
        "missing_metadata_png_count": 0,
        "invalid_metadata_png_count": 0,
        "blocked_png_count": 0,
        "image_path_none_png_count": 0,
        "invalid_size_png_count": 0,
        "orphan_json_count": len(orphan_jsons),
        "blocked_json_count": blocked_json_count,
        "image_path_none_json_count": image_path_none_json_count,
        "draft_label_count": 0,
        "review_image_count": 0,
        "candidate_negative_images": 0,
        "predicted_boxes": 0,
    }

    selected: list[SelectedImage] = []
    skipped_rows: list[dict[str, Any]] = []
    for png_path in raw_pngs:
        metadata_path = args.raw / f"{png_path.stem}.json"
        metadata = read_json(metadata_path) if metadata_path.exists() else None
        if metadata is None:
            stats["skipped_png_count"] += 1
            key = "missing_metadata_png_count" if not metadata_path.exists() else "invalid_metadata_png_count"
            stats[key] += 1
            skipped_rows.append({"image": str(png_path), "metadata": str(metadata_path), "reason": key})
            continue
        ok, reason = valid_metadata(metadata)
        if not ok:
            stats["skipped_png_count"] += 1
            if reason == "blocked":
                stats["blocked_png_count"] += 1
            elif reason == "image_path_none":
                stats["image_path_none_png_count"] += 1
            elif reason == "invalid_size":
                stats["invalid_size_png_count"] += 1
            skipped_rows.append({"image": str(png_path), "metadata": str(metadata_path), "reason": reason})
            continue
        selected_path = args.selected_out / png_path.name
        selected.append(SelectedImage(png_path, selected_path, metadata_path, metadata))

    stats["valid_png_count"] = len(selected)
    stats["selected_count"] = len(selected)

    print(f"raw_png_count={stats['raw_png_count']}")
    print(f"raw_json_count={stats['raw_json_count']}")
    print(f"selected_count={stats['selected_count']}")
    print(f"skipped_png_count={stats['skipped_png_count']}")
    print(f"orphan_json_count={stats['orphan_json_count']}")
    print(f"blocked_json_count={stats['blocked_json_count']}")
    print(f"image_path_none_json_count={stats['image_path_none_json_count']}")
    print(f"dry_run={str(args.dry_run).lower()}")
    if args.dry_run:
        return 0

    import cv2

    ensure_clean_dir(args.selected_out, args.overwrite)
    ensure_clean_dir(label_dir, args.overwrite)
    ensure_clean_dir(args.review_out, args.overwrite)
    write_dataset_readme(args.dataset_out)

    review_rows: list[dict[str, Any]] = []
    for item in selected:
        shutil.copy2(item.source_image, item.selected_image)
        label_path = label_dir / f"{item.source_image.stem}.txt"
        review_path = args.review_out / item.source_image.name

        image = cv2.imread(str(item.source_image))
        if image is None:
            review_rows.append(
                {
                    "image_name": item.source_image.name,
                    "image_path": str(item.source_image),
                    "metadata_path": str(item.metadata_path),
                    "split_candidate": "false",
                    "source": "raw",
                    "predicted_box_count": 0,
                    "is_candidate_negative": "false",
                    "needs_human_review": "true",
                    "notes": "cv2_read_failed",
                }
            )
            continue

        image_h, image_w = image.shape[:2]
        roi = build_roi(
            image_path=item.source_image,
            metadata_dir=args.raw,
            roi_mode=args.roi_mode,
            ignore_bottom_ratio=args.ignore_bottom_ratio,
            image_w=image_w,
            image_h=image_h,
        )
        roi_image = image[roi.y : roi.y + roi.h, roi.x : roi.x + roi.w]
        candidates = to_full_image_candidates(detect_candidates(roi_image, config), roi)
        label_path.write_text("\n".join(yolo_line(c, image_w, image_h) for c in candidates) + ("\n" if candidates else ""), encoding="utf-8")
        draw_review(image, candidates, review_path, roi)

        stats["draft_label_count"] += 1
        stats["review_image_count"] += 1
        stats["predicted_boxes"] += len(candidates)
        if not candidates:
            stats["candidate_negative_images"] += 1

        review_rows.append(
            {
                "image_name": item.source_image.name,
                "image_path": str(item.source_image),
                "metadata_path": str(item.metadata_path),
                "split_candidate": "true",
                "source": "raw",
                "predicted_box_count": len(candidates),
                "is_candidate_negative": str(len(candidates) == 0).lower(),
                "needs_human_review": "true",
                "notes": f"draft_prelabel_roi={roi.source};review_required",
            }
        )

    with review_manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(review_rows)

    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerow(stats)

    for key in SUMMARY_FIELDS:
        print(f"{key}={stats[key]}")
    print(f"selected_dir={args.selected_out}")
    print(f"label_dir={label_dir}")
    print(f"review_dir={args.review_out}")
    print(f"review_manifest={review_manifest_path}")
    print(f"dataset_placeholder={args.dataset_out}")
    print("final_dataset_generated=false")
    print("human_review_required=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
