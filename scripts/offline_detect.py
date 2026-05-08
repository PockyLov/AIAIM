from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


PHASE_NAME = "phase_4_offline_detect_only_inference_coordinate_contract_v0"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
SAFETY_BOUNDARY = {
    "realtime_capture": False,
    "aimlab_live_connection": False,
    "mouse_movement": False,
    "mouse_click": False,
    "auto_aim": False,
    "closed_loop_automation": False,
    "anti_cheat_bypass": False,
    "phase_5_mapping": False,
}


@dataclass
class InferenceContext:
    model: Any
    model_path: Path
    model_names: dict[int, str]
    conf: float
    iou: float
    max_det: int
    imgsz: int
    requested_device: str
    actual_device: str
    timestamp: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 4 offline detect-only inference with input-image pixel coordinate contract."
    )
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--image", type=Path, help="Single PNG/JPG/JPEG image path.")
    inputs.add_argument("--image-dir", type=Path, help="Directory containing PNG/JPG/JPEG images.")

    parser.add_argument("--model", type=Path, default=Path("runs/detect/phase3_yolo11n_baseline/weights/best.pt"))
    parser.add_argument("--output-dir", type=Path, default=Path("runs/detect/phase4_offline_detection"))
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.70)
    parser.add_argument("--max-det", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--save-review", dest="save_review", action="store_true", default=True)
    parser.add_argument("--no-save-review", dest="save_review", action="store_false")
    parser.add_argument("--save-json", dest="save_json", action="store_true", default=True)
    parser.add_argument("--no-save-json", dest="save_json", action="store_false")
    parser.add_argument("--metadata", type=Path, help="Optional metadata JSON for --image mode.")
    parser.add_argument("--metadata-dir", type=Path, help="Optional directory for same-stem metadata JSON files.")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def round_float(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def path_to_str(path: Path | None) -> str | None:
    return str(path) if path is not None else None


def args_to_jsonable(args: argparse.Namespace) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in vars(args).items():
        if isinstance(value, Path):
            result[key] = str(value)
        else:
            result[key] = value
    return result


def resolve_device(requested_device: str) -> str:
    import torch

    if requested_device == "auto":
        return "cuda:0" if torch.cuda.is_available() else "cpu"
    if requested_device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError(f"requested device {requested_device!r}, but CUDA is not available")
    return requested_device


def normalize_model_names(names: Any) -> dict[int, str]:
    if isinstance(names, dict):
        normalized: dict[int, str] = {}
        for key, value in names.items():
            try:
                normalized[int(key)] = str(value)
            except (TypeError, ValueError):
                continue
        return normalized
    if isinstance(names, (list, tuple)):
        return {index: str(value) for index, value in enumerate(names)}
    return {}


def load_model(model_path: Path) -> tuple[Any, dict[int, str]]:
    if not model_path.exists():
        raise FileNotFoundError(f"model not found: {model_path}")
    try:
        from ultralytics import YOLO

        model = YOLO(str(model_path))
        model_names = normalize_model_names(getattr(model, "names", {}))
    except Exception as exc:  # pragma: no cover - kept explicit for CLI diagnostics
        raise RuntimeError(f"failed to load YOLO model from {model_path}: {exc}") from exc
    return model, model_names


def collect_images(args: argparse.Namespace) -> list[Path]:
    if args.image:
        if not args.image.exists():
            raise FileNotFoundError(f"image not found: {args.image}")
        if args.image.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError(f"unsupported image extension: {args.image}")
        return [args.image]

    image_dir: Path = args.image_dir
    if not image_dir.exists() or not image_dir.is_dir():
        raise NotADirectoryError(f"image directory not found: {image_dir}")
    images = sorted(path for path in image_dir.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)
    if not images:
        raise FileNotFoundError(f"no PNG/JPG/JPEG images found in: {image_dir}")
    return images


def read_image_size(image_path: Path) -> tuple[int, int]:
    with Image.open(image_path) as image:
        return image.size


def read_metadata(metadata_path: Path | None) -> dict[str, Any]:
    if not metadata_path or not metadata_path.exists():
        return {"has_metadata": False}
    try:
        with metadata_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as exc:
        return {"has_metadata": False, "metadata_path": str(metadata_path), "metadata_error": str(exc)}

    screenshot_size = None
    width = raw.get("screenshot_width")
    height = raw.get("screenshot_height")
    if width is not None or height is not None:
        screenshot_size = {"width": width, "height": height}

    result = {
        "has_metadata": True,
        "metadata_path": str(metadata_path),
        "window_title": raw.get("aimlab_window_title") or raw.get("window_title"),
        "window_rect": raw.get("window_rect"),
        "monitor_rect": raw.get("monitor_rect"),
        "screenshot_size": screenshot_size,
        "blocked": raw.get("blocked"),
        "blocked_reason": raw.get("blocked_reason"),
    }
    return {key: value for key, value in result.items() if value is not None}


def metadata_for_image(image_path: Path, args: argparse.Namespace) -> dict[str, Any]:
    if args.metadata:
        return read_metadata(args.metadata)
    if args.metadata_dir:
        return read_metadata(args.metadata_dir / f"{image_path.stem}.json")
    return {"has_metadata": False}


def run_inference_on_image(ctx: InferenceContext, image_path: Path) -> list[Any]:
    return ctx.model.predict(
        source=str(image_path),
        conf=ctx.conf,
        iou=ctx.iou,
        max_det=ctx.max_det,
        imgsz=ctx.imgsz,
        device=ctx.actual_device,
        save=False,
        verbose=False,
    )


def validate_detection(x1: float, y1: float, x2: float, y2: float, width: int, height: int) -> dict[str, bool]:
    center_x = (x1 + x2) / 2.0
    center_y = (y1 + y2) / 2.0
    bbox_within_image = 0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height
    center_within_bbox = x1 <= center_x <= x2 and y1 <= center_y <= y2
    center_within_image = 0 <= center_x <= width and 0 <= center_y <= height
    return {
        "bbox_within_image": bbox_within_image,
        "center_within_bbox": center_within_bbox,
        "center_within_image": center_within_image,
    }


def build_detection_json(
    ctx: InferenceContext,
    image_path: Path,
    width: int,
    height: int,
    results: list[Any],
    source_metadata: dict[str, Any],
) -> dict[str, Any]:
    detections: list[dict[str, Any]] = []
    warnings: list[str] = []
    result = results[0] if results else None
    boxes = getattr(result, "boxes", None)

    if boxes is not None and len(boxes) > 0:
        xyxy_values = boxes.xyxy.detach().cpu().tolist()
        conf_values = boxes.conf.detach().cpu().tolist()
        cls_values = boxes.cls.detach().cpu().tolist()
        for detection_id, (xyxy, confidence, class_id_value) in enumerate(zip(xyxy_values, conf_values, cls_values)):
            x1, y1, x2, y2 = [float(value) for value in xyxy]
            bbox_w = x2 - x1
            bbox_h = y2 - y1
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            class_id = int(class_id_value)
            validity = validate_detection(x1, y1, x2, y2, width, height)
            if not all(validity.values()):
                warnings.append(f"detection {detection_id} has invalid bbox or center")
            detections.append(
                {
                    "id": detection_id,
                    "class_id": class_id,
                    "class_name": ctx.model_names.get(class_id, f"class_{class_id}"),
                    "confidence": round_float(confidence),
                    "bbox_xyxy": {
                        "x1": round_float(x1),
                        "y1": round_float(y1),
                        "x2": round_float(x2),
                        "y2": round_float(y2),
                    },
                    "bbox_xywh": {
                        "x": round_float(center_x),
                        "y": round_float(center_y),
                        "w": round_float(bbox_w),
                        "h": round_float(bbox_h),
                    },
                    "center": {
                        "x": round_float(center_x),
                        "y": round_float(center_y),
                    },
                    "area_px": round_float(bbox_w * bbox_h),
                    "validity": validity,
                }
            )

    confidences = [detection["confidence"] for detection in detections]
    return {
        "phase": PHASE_NAME,
        "run": {
            "model_path": str(ctx.model_path),
            "conf": ctx.conf,
            "iou": ctx.iou,
            "max_det": ctx.max_det,
            "imgsz": ctx.imgsz,
            "device": ctx.actual_device,
            "timestamp": ctx.timestamp,
        },
        "coordinate_space": {
            "type": "input_image_pixel",
            "origin": "top_left",
            "x_axis": "right",
            "y_axis": "down",
            "unit": "pixel",
            "is_screen_coordinate": False,
            "is_mouse_coordinate": False,
            "is_window_coordinate": False,
            "is_click_target": False,
        },
        "image": {
            "source_path": str(image_path),
            "file_name": image_path.name,
            "width": width,
            "height": height,
        },
        "source_metadata": source_metadata,
        "summary": {
            "num_detections": len(detections),
            "max_confidence": max(confidences) if confidences else None,
            "min_confidence": min(confidences) if confidences else None,
            "warnings": warnings,
        },
        "detections": detections,
    }


def draw_clean_review_image(image_path: Path, detections: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path).convert("RGB") as image:
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 10)
        except OSError:
            font = ImageFont.load_default()

        for detection in detections:
            bbox = detection["bbox_xyxy"]
            center = detection["center"]
            x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
            cx, cy = center["x"], center["y"]
            draw.rectangle((x1, y1, x2, y2), outline=(0, 255, 0), width=2)
            draw.line((cx - 4, cy, cx + 4, cy), fill=(255, 0, 0), width=1)
            draw.line((cx, cy - 4, cx, cy + 4), fill=(255, 0, 0), width=1)
            confidence = detection.get("confidence")
            if confidence is not None:
                text_x = max(0, min(float(x1), image.width - 36))
                text_y = max(0, float(y1) - 12)
                draw.text((text_x, text_y), f"{confidence:.2f}", fill=(0, 255, 0), font=font)
        image.save(output_path)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "image_path",
        "file_name",
        "width",
        "height",
        "num_detections",
        "max_confidence",
        "min_confidence",
        "json_path",
        "review_image_path",
        "status",
        "error",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_run_config(args: argparse.Namespace, ctx: InferenceContext, input_mode: str, input_path: Path) -> None:
    config = {
        "phase": PHASE_NAME,
        "timestamp": ctx.timestamp,
        "command_args": args_to_jsonable(args),
        "model_path": str(ctx.model_path),
        "model_names": {str(key): value for key, value in ctx.model_names.items()},
        "conf": ctx.conf,
        "iou": ctx.iou,
        "max_det": ctx.max_det,
        "imgsz": ctx.imgsz,
        "requested_device": ctx.requested_device,
        "actual_device": ctx.actual_device,
        "input_mode": input_mode,
        "input_path": str(input_path),
        "output_dir": str(args.output_dir),
        "save_json": args.save_json,
        "save_review": args.save_review,
        "safety_boundary": SAFETY_BOUNDARY,
    }
    write_json(args.output_dir / "run_config.json", config)


def run_one_image(ctx: InferenceContext, args: argparse.Namespace, image_path: Path) -> dict[str, Any]:
    json_path = args.output_dir / "json" / f"{image_path.stem}.json"
    review_path = args.output_dir / "review_images" / f"{image_path.stem}_review.png"
    try:
        width, height = read_image_size(image_path)
        source_metadata = metadata_for_image(image_path, args)
        results = run_inference_on_image(ctx, image_path)
        detection_json = build_detection_json(ctx, image_path, width, height, results, source_metadata)
        if args.save_json:
            write_json(json_path, detection_json)
        if args.save_review:
            draw_clean_review_image(image_path, detection_json["detections"], review_path)
        return {
            "image_path": str(image_path),
            "file_name": image_path.name,
            "width": width,
            "height": height,
            "num_detections": detection_json["summary"]["num_detections"],
            "max_confidence": detection_json["summary"]["max_confidence"],
            "min_confidence": detection_json["summary"]["min_confidence"],
            "json_path": str(json_path) if args.save_json else "",
            "review_image_path": str(review_path) if args.save_review else "",
            "status": "ok",
            "error": "",
        }
    except Exception as exc:
        return {
            "image_path": str(image_path),
            "file_name": image_path.name,
            "width": "",
            "height": "",
            "num_detections": "",
            "max_confidence": "",
            "min_confidence": "",
            "json_path": str(json_path) if args.save_json else "",
            "review_image_path": str(review_path) if args.save_review else "",
            "status": "failed",
            "error": str(exc),
        }


def main() -> int:
    args = parse_args()
    timestamp = now_iso()
    try:
        images = collect_images(args)
        actual_device = resolve_device(args.device)
        model, model_names = load_model(args.model)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    ctx = InferenceContext(
        model=model,
        model_path=args.model,
        model_names=model_names,
        conf=args.conf,
        iou=args.iou,
        max_det=args.max_det,
        imgsz=args.imgsz,
        requested_device=args.device,
        actual_device=actual_device,
        timestamp=timestamp,
    )
    input_mode = "single_image" if args.image else "image_dir"
    input_path = args.image if args.image else args.image_dir
    write_run_config(args, ctx, input_mode, input_path)

    rows = [run_one_image(ctx, args, image_path) for image_path in images]
    write_summary_csv(args.output_dir / "summary.csv", rows)
    ok_count = sum(1 for row in rows if row["status"] == "ok")
    failed_count = len(rows) - ok_count
    print(f"phase={PHASE_NAME}")
    print(f"model={args.model}")
    print(f"actual_device={actual_device}")
    print(f"images={len(rows)} ok={ok_count} failed={failed_count}")
    print(f"output_dir={args.output_dir}")
    print(f"summary_csv={args.output_dir / 'summary.csv'}")
    return 1 if failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
