from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}
MANIFEST_FIELDS = [
    "filename",
    "image_path",
    "label_path",
    "review_image_path",
    "detected",
    "detection_count",
    "bbox_pixel_x",
    "bbox_pixel_y",
    "bbox_pixel_w",
    "bbox_pixel_h",
    "bbox_yolo_x_center",
    "bbox_yolo_y_center",
    "bbox_yolo_w",
    "bbox_yolo_h",
    "contour_area",
    "circularity",
    "aspect_ratio",
    "confidence_heuristic",
    "roi_source",
    "roi_x",
    "roi_y",
    "roi_w",
    "roi_h",
    "ignored_bottom_ratio",
    "status",
    "review_required",
    "notes",
]


@dataclass(frozen=True)
class Candidate:
    x: int
    y: int
    w: int
    h: int
    area: float
    circularity: float
    aspect_ratio: float
    confidence: float

    def yolo_values(self, image_w: int, image_h: int) -> tuple[float, float, float, float]:
        return (
            (self.x + self.w / 2) / image_w,
            (self.y + self.h / 2) / image_h,
            self.w / image_w,
            self.h / image_h,
        )


@dataclass(frozen=True)
class Roi:
    x: int
    y: int
    w: int
    h: int
    source: str
    ignored_bottom_ratio: float


def load_config(path: Path) -> dict[str, Any]:
    default = {
        "hsv_lower": [18, 80, 80],
        "hsv_upper": [40, 255, 255],
        "min_area": 20,
        "max_area": 20000,
        "min_circularity": 0.45,
        "min_aspect_ratio": 0.5,
        "max_aspect_ratio": 1.8,
        "morph_kernel_size": 3,
        "write_empty_labels": True,
        "class_id": 0,
        "class_name": "yellow_ball",
    }
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        default.update(loaded)
    return default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline OpenCV yellow-ball pre-labeling assistance.")
    parser.add_argument("--input", type=Path, default=Path("data/selected/phase2_yellow_ball"))
    parser.add_argument("--out", type=Path, default=Path("data/prelabels/phase2_yellow_ball"))
    parser.add_argument("--config", type=Path, default=Path("config/phase2_prelabel_config.json"))
    parser.add_argument("--metadata-dir", type=Path, default=Path("data/raw/screenshots"))
    parser.add_argument("--ignore-bottom-ratio", type=float, default=0.12)
    parser.add_argument("--roi-mode", choices=("metadata", "ignore-bottom", "full"), default="metadata")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--min-area", type=float, default=None)
    parser.add_argument("--max-area", type=float, default=None)
    parser.add_argument("--min-circularity", type=float, default=None)
    parser.add_argument("--min-aspect-ratio", type=float, default=None)
    parser.add_argument("--max-aspect-ratio", type=float, default=None)
    parser.add_argument("--write-empty-labels", action="store_true")
    parser.add_argument("--review-images", action="store_true")
    return parser.parse_args()


def apply_overrides(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    for arg_name, config_name in [
        ("min_area", "min_area"),
        ("max_area", "max_area"),
        ("min_circularity", "min_circularity"),
        ("min_aspect_ratio", "min_aspect_ratio"),
        ("max_aspect_ratio", "max_aspect_ratio"),
    ]:
        value = getattr(args, arg_name)
        if value is not None:
            config[config_name] = value
    if args.write_empty_labels:
        config["write_empty_labels"] = True
    if args.review_images:
        config["review_images"] = True
    return config


def list_images(input_dir: Path, limit: int | None) -> list[Path]:
    images = sorted(p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)
    return images[:limit] if limit is not None else images


def detect_candidates(image: Any, config: dict[str, Any]) -> list[Candidate]:
    import cv2
    import numpy as np

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower = np.array(config["hsv_lower"], dtype=np.uint8)
    upper = np.array(config["hsv_upper"], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower, upper)
    kernel_size = max(1, int(config.get("morph_kernel_size", 3)))
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates: list[Candidate] = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < float(config["min_area"]) or area > float(config["max_area"]):
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if w <= 0 or h <= 0:
            continue
        aspect_ratio = w / h
        if aspect_ratio < float(config["min_aspect_ratio"]) or aspect_ratio > float(config["max_aspect_ratio"]):
            continue
        perimeter = float(cv2.arcLength(contour, True))
        circularity = (4 * math.pi * area / (perimeter * perimeter)) if perimeter > 0 else 0.0
        if circularity < float(config["min_circularity"]):
            continue
        aspect_score = max(0.0, 1.0 - abs(1.0 - aspect_ratio))
        circularity_score = min(1.0, circularity)
        confidence = round((aspect_score * 0.4) + (circularity_score * 0.6), 4)
        candidates.append(
            Candidate(
                x=int(x),
                y=int(y),
                w=int(w),
                h=int(h),
                area=round(area, 3),
                circularity=round(circularity, 4),
                aspect_ratio=round(aspect_ratio, 4),
                confidence=confidence,
            )
        )
    return sorted(candidates, key=lambda c: c.confidence, reverse=True)


def load_metadata(metadata_dir: Path, image_path: Path) -> dict[str, Any] | None:
    metadata_path = metadata_dir / f"{image_path.stem}.json"
    if not metadata_path.exists():
        return None
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def rect_value(rect: dict[str, Any], key: str) -> int | None:
    value = rect.get(key)
    return int(value) if isinstance(value, (int, float)) else None


def clip_roi(x: int, y: int, w: int, h: int, image_w: int, image_h: int, source: str, ignored: float) -> Roi:
    x1 = max(0, min(image_w, x))
    y1 = max(0, min(image_h, y))
    x2 = max(0, min(image_w, x + w))
    y2 = max(0, min(image_h, y + h))
    return Roi(x=x1, y=y1, w=max(0, x2 - x1), h=max(0, y2 - y1), source=source, ignored_bottom_ratio=ignored)


def roi_from_metadata(metadata: dict[str, Any] | None, image_w: int, image_h: int) -> Roi | None:
    if not metadata:
        return None
    window_rect = metadata.get("window_rect")
    monitor_rect = metadata.get("monitor_rect")
    if not isinstance(window_rect, dict) or not isinstance(monitor_rect, dict):
        return None

    window_left = rect_value(window_rect, "left")
    window_top = rect_value(window_rect, "top")
    window_right = rect_value(window_rect, "right")
    window_bottom = rect_value(window_rect, "bottom")
    monitor_left = rect_value(monitor_rect, "left")
    monitor_top = rect_value(monitor_rect, "top")
    if None in (window_left, window_top, window_right, window_bottom, monitor_left, monitor_top):
        return None

    roi_x = int(window_left - monitor_left)
    roi_y = int(window_top - monitor_top)
    roi_w = int(window_right - window_left)
    roi_h = int(window_bottom - window_top)
    if roi_w <= 0 or roi_h <= 0:
        return None
    roi = clip_roi(roi_x, roi_y, roi_w, roi_h, image_w, image_h, "metadata", 0.0)
    return roi if roi.w > 0 and roi.h > 0 else None


def build_roi(
    *,
    image_path: Path,
    metadata_dir: Path,
    roi_mode: str,
    ignore_bottom_ratio: float,
    image_w: int,
    image_h: int,
) -> Roi:
    bounded_ignore = max(0.0, min(0.9, ignore_bottom_ratio))
    if roi_mode == "full":
        return Roi(0, 0, image_w, image_h, "full", 0.0)

    if roi_mode == "metadata":
        metadata_roi = roi_from_metadata(load_metadata(metadata_dir, image_path), image_w, image_h)
        if metadata_roi is not None:
            return metadata_roi

    roi_h = int(round(image_h * (1.0 - bounded_ignore)))
    return Roi(0, 0, image_w, max(1, roi_h), "ignore-bottom", bounded_ignore)


def to_full_image_candidates(candidates: list[Candidate], roi: Roi) -> list[Candidate]:
    return [
        Candidate(
            x=candidate.x + roi.x,
            y=candidate.y + roi.y,
            w=candidate.w,
            h=candidate.h,
            area=candidate.area,
            circularity=candidate.circularity,
            aspect_ratio=candidate.aspect_ratio,
            confidence=candidate.confidence,
        )
        for candidate in candidates
    ]


def draw_review(image: Any, candidates: list[Candidate], output_path: Path, roi: Roi) -> None:
    import cv2

    canvas = image.copy()
    cv2.rectangle(canvas, (roi.x, roi.y), (roi.x + roi.w, roi.y + roi.h), (255, 180, 0), 2)
    cv2.putText(
        canvas,
        f"ROI: {roi.source} x={roi.x} y={roi.y} w={roi.w} h={roi.h}",
        (max(10, roi.x + 10), max(25, roi.y + 25)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 180, 0),
        2,
    )
    if not candidates:
        cv2.putText(canvas, "no detection in ROI", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
    for idx, candidate in enumerate(candidates):
        p1 = (candidate.x, candidate.y)
        p2 = (candidate.x + candidate.w, candidate.y + candidate.h)
        cv2.rectangle(canvas, p1, p2, (0, 255, 255), 2)
        text = (
            f"#{idx} score={candidate.confidence:.2f} "
            f"area={candidate.area:.0f} circ={candidate.circularity:.2f}"
        )
        text_y = max(20, candidate.y - 8)
        cv2.putText(canvas, text, (candidate.x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), canvas)


def manifest_row(
    image_path: Path,
    label_path: Path,
    review_path: Path,
    candidate: Candidate | None,
    image_w: int,
    image_h: int,
    detection_count: int,
    status: str,
    notes: str,
    roi: Roi,
) -> dict[str, Any]:
    if candidate is None:
        return {
            "filename": image_path.name,
            "image_path": str(image_path),
            "label_path": str(label_path),
            "review_image_path": str(review_path),
            "detected": "false",
            "detection_count": detection_count,
            "bbox_pixel_x": "",
            "bbox_pixel_y": "",
            "bbox_pixel_w": "",
            "bbox_pixel_h": "",
            "bbox_yolo_x_center": "",
            "bbox_yolo_y_center": "",
            "bbox_yolo_w": "",
            "bbox_yolo_h": "",
            "contour_area": "",
            "circularity": "",
            "aspect_ratio": "",
            "confidence_heuristic": "",
            "roi_source": roi.source,
            "roi_x": roi.x,
            "roi_y": roi.y,
            "roi_w": roi.w,
            "roi_h": roi.h,
            "ignored_bottom_ratio": roi.ignored_bottom_ratio,
            "status": status,
            "review_required": "true",
            "notes": notes,
        }
    yolo = candidate.yolo_values(image_w, image_h)
    return {
        "filename": image_path.name,
        "image_path": str(image_path),
        "label_path": str(label_path),
        "review_image_path": str(review_path),
        "detected": "true",
        "detection_count": detection_count,
        "bbox_pixel_x": candidate.x,
        "bbox_pixel_y": candidate.y,
        "bbox_pixel_w": candidate.w,
        "bbox_pixel_h": candidate.h,
        "bbox_yolo_x_center": f"{yolo[0]:.6f}",
        "bbox_yolo_y_center": f"{yolo[1]:.6f}",
        "bbox_yolo_w": f"{yolo[2]:.6f}",
        "bbox_yolo_h": f"{yolo[3]:.6f}",
        "contour_area": candidate.area,
        "circularity": candidate.circularity,
        "aspect_ratio": candidate.aspect_ratio,
        "confidence_heuristic": candidate.confidence,
        "roi_source": roi.source,
        "roi_x": roi.x,
        "roi_y": roi.y,
        "roi_w": roi.w,
        "roi_h": roi.h,
        "ignored_bottom_ratio": roi.ignored_bottom_ratio,
        "status": status,
        "review_required": "true",
        "notes": notes,
    }


def main() -> int:
    args = parse_args()
    config = apply_overrides(load_config(args.config), args)
    images = list_images(args.input, args.limit)
    label_dir = args.out / "labels"
    review_dir = args.out / "review_images"
    manifest_path = args.out / "prelabel_manifest.csv"

    print(f"input_image_count={len(images)}")
    print(f"dry_run={str(args.dry_run).lower()}")
    if args.dry_run:
        return 0

    import cv2

    label_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    detected_images = 0
    total_boxes = 0

    for image_path in images:
        label_path = label_dir / f"{image_path.stem}.txt"
        review_path = review_dir / image_path.name
        if not args.overwrite and (label_path.exists() or review_path.exists()):
            rows.append(
                manifest_row(
                    image_path,
                    label_path,
                    review_path,
                    None,
                    0,
                    0,
                    0,
                    "skipped_exists",
                    "use --overwrite",
                    Roi(0, 0, 0, 0, "not_evaluated", 0.0),
                )
            )
            continue

        image = cv2.imread(str(image_path))
        if image is None:
            rows.append(
                manifest_row(
                    image_path,
                    label_path,
                    review_path,
                    None,
                    0,
                    0,
                    0,
                    "read_failed",
                    "cv2.imread failed",
                    Roi(0, 0, 0, 0, "not_evaluated", 0.0),
                )
            )
            continue

        image_h, image_w = image.shape[:2]
        roi = build_roi(
            image_path=image_path,
            metadata_dir=args.metadata_dir,
            roi_mode=args.roi_mode,
            ignore_bottom_ratio=args.ignore_bottom_ratio,
            image_w=image_w,
            image_h=image_h,
        )
        roi_image = image[roi.y : roi.y + roi.h, roi.x : roi.x + roi.w]
        candidates = to_full_image_candidates(detect_candidates(roi_image, config), roi)
        if candidates:
            detected_images += 1
            total_boxes += len(candidates)

        label_lines = []
        for candidate in candidates:
            x_center, y_center, width, height = candidate.yolo_values(image_w, image_h)
            label_lines.append(
                f"{int(config['class_id'])} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
            )

        if label_lines or bool(config.get("write_empty_labels", True)):
            label_path.write_text("\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8")
        draw_review(image, candidates, review_path, roi)

        if candidates:
            for candidate in candidates:
                rows.append(
                    manifest_row(
                        image_path,
                        label_path,
                        review_path,
                        candidate,
                        image_w,
                        image_h,
                        len(candidates),
                        "prelabeled",
                        "offline_opencv_prelabel_requires_human_review_roi_limited",
                        roi,
                    )
                )
        else:
            rows.append(
                manifest_row(
                    image_path,
                    label_path,
                    review_path,
                    None,
                    image_w,
                    image_h,
                    0,
                    "no_detection",
                    "empty_label_is_negative_sample_candidate_requires_human_review_roi_limited",
                    roi,
                )
            )

    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"detected_images={detected_images}")
    print(f"detected_count={detected_images}")
    print(f"no_detection_count={len(images) - detected_images}")
    print(f"total_boxes={total_boxes}")
    print(f"label_dir={label_dir}")
    print(f"review_dir={review_dir}")
    print(f"manifest_path={manifest_path}")
    print("review_required=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
