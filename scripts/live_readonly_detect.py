from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aiaim_collector.monitor_detector import MonitorInfo, get_monitor_for_window
from aiaim_collector.screen_capture import CaptureResult, capture_monitor
from aiaim_collector.window_detector import WindowInfo, find_aimlab_window, get_foreground_window_info


PHASE_NAME = "phase6_live_readonly_detection"
COORDINATE_CONTRACT_VERSION = "phase5_5_image_pixel_monitor_relative_v1"
DEFAULT_MODEL = Path("runs/detect/phase3_yolo11n_baseline/weights/best.pt")
SAFETY_BOUNDARY = {
    "live_readonly_detection": True,
    "realtime_capture": True,
    "aimlab_foreground_gate_required": True,
    "mouse_movement": False,
    "mouse_click": False,
    "mouse_target_output": False,
    "click_target_output": False,
    "auto_aim": False,
    "target_lock": False,
    "closed_loop_automation": False,
    "anti_cheat_bypass": False,
    "process_memory_read": False,
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 6 live read-only AIMLAB yellow-ball detection.")
    parser.add_argument("--mode", choices=("single", "loop"), default="single")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", type=Path, default=Path("runs/detect/phase6_live_readonly"))
    parser.add_argument("--max-frames", type=int, default=30)
    parser.add_argument("--interval-sec", type=float, default=0.5)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.70)
    parser.add_argument("--max-det", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--review-images", action="store_true", default=False)
    parser.add_argument("--overwrite", action="store_true", default=False)
    parser.add_argument("--title-keyword", action="append", dest="title_keywords")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def safe_timestamp(timestamp: str) -> str:
    return timestamp.replace(":", "").replace("-", "").replace(".", "").replace("+", "_")


def round_float(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def rect_to_dict(rect: Any | None) -> dict[str, int] | None:
    return rect.to_dict() if rect is not None else None


def args_to_jsonable(args: argparse.Namespace) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in vars(args).items():
        result[key] = str(value) if isinstance(value, Path) else value
    return result


def prepare_output_dir(output_dir: Path, overwrite: bool) -> None:
    if output_dir.exists():
        if not overwrite:
            raise FileExistsError(f"output directory already exists; pass --overwrite to replace it: {output_dir}")
        shutil.rmtree(output_dir)
    (output_dir / "json").mkdir(parents=True, exist_ok=True)
    (output_dir / "review_images").mkdir(parents=True, exist_ok=True)
    (output_dir / "captured_frames").mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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


def load_inference_context(args: argparse.Namespace) -> InferenceContext:
    if not args.model.exists():
        raise FileNotFoundError(f"model not found: {args.model}")
    actual_device = resolve_device(args.device)
    try:
        from ultralytics import YOLO

        model = YOLO(str(args.model))
    except Exception as exc:
        raise RuntimeError(f"failed to load YOLO model from {args.model}: {exc}") from exc
    return InferenceContext(
        model=model,
        model_path=args.model,
        model_names=normalize_model_names(getattr(model, "names", {})),
        conf=args.conf,
        iou=args.iou,
        max_det=args.max_det,
        imgsz=args.imgsz,
        requested_device=args.device,
        actual_device=actual_device,
    )


def get_gate_state(title_keywords: tuple[str, ...]) -> dict[str, Any]:
    foreground: WindowInfo | None = None
    window: WindowInfo | None = None
    monitor: MonitorInfo | None = None
    blocked = False
    blocked_reason = ""

    try:
        foreground = get_foreground_window_info()
        window = find_aimlab_window(title_keywords)
        if window is None:
            blocked = True
            blocked_reason = "aimlab_window_not_found"
        else:
            monitor = get_monitor_for_window(window)
            if not window.is_foreground:
                blocked = True
                blocked_reason = "aimlab_not_foreground"
    except Exception as exc:
        blocked = True
        blocked_reason = f"foreground_gate_error:{type(exc).__name__}:{exc}"

    return {
        "foreground": foreground,
        "window": window,
        "monitor": monitor,
        "blocked": blocked,
        "blocked_reason": blocked_reason,
    }


def run_inference(ctx: InferenceContext, image_path: Path) -> list[Any]:
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
    return {
        "bbox_within_image": 0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height,
        "center_within_bbox": x1 <= center_x <= x2 and y1 <= center_y <= y2,
        "center_within_image": 0 <= center_x <= width and 0 <= center_y <= height,
    }


def detections_from_results(ctx: InferenceContext, results: list[Any], width: int, height: int) -> list[dict[str, Any]]:
    detections: list[dict[str, Any]] = []
    result = results[0] if results else None
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) <= 0:
        return detections

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
                "center_image_px": {
                    "x": round_float(center_x),
                    "y": round_float(center_y),
                },
                "center_monitor_px": {
                    "x": round_float(center_x),
                    "y": round_float(center_y),
                },
                "coordinate_space": "image_pixel_and_monitor_relative",
                "is_screen_coordinate": False,
                "is_mouse_coordinate": False,
                "is_click_target": False,
                "action_authorized": False,
                "validity": validate_detection(x1, y1, x2, y2, width, height),
            }
        )
    return detections


def draw_review_image(image_path: Path, detections: list[dict[str, Any]], output_path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path).convert("RGB") as image:
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 10)
        except OSError:
            font = ImageFont.load_default()
        for detection in detections:
            bbox = detection["bbox_xyxy"]
            center = detection["center_image_px"]
            x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
            cx, cy = center["x"], center["y"]
            draw.rectangle((x1, y1, x2, y2), outline=(0, 255, 0), width=2)
            draw.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), outline=(255, 0, 0), width=2)
            text = f"{detection['confidence']:.2f} img({cx:.0f},{cy:.0f}) mon({cx:.0f},{cy:.0f})"
            text_x = max(0, min(float(x1), image.width - 130))
            text_y = max(0, float(y1) - 12)
            draw.text((text_x, text_y), text, fill=(0, 255, 0), font=font)
        image.save(output_path)


def build_frame_json(
    *,
    args: argparse.Namespace,
    frame_index: int,
    timestamp: str,
    gate: dict[str, Any],
    capture: CaptureResult | None,
    detections: list[dict[str, Any]],
    ctx: InferenceContext | None,
    error: str = "",
) -> dict[str, Any]:
    window: WindowInfo | None = gate.get("window")
    foreground: WindowInfo | None = gate.get("foreground")
    monitor: MonitorInfo | None = gate.get("monitor")
    blocked = bool(gate.get("blocked")) or bool(error)
    blocked_reason = str(gate.get("blocked_reason") or error)
    confidences = [detection["confidence"] for detection in detections if detection.get("confidence") is not None]
    return {
        "phase": PHASE_NAME,
        "frame_index": frame_index,
        "timestamp": timestamp,
        "source": "live_monitor_capture",
        "aimlab_foreground_gate_passed": bool(window and window.is_foreground and not blocked),
        "blocked": blocked,
        "blocked_reason": blocked_reason,
        "aimlab_window_found": window is not None,
        "aimlab_window_title": window.title if window else None,
        "foreground_window_title": foreground.title if foreground else None,
        "monitor_rect": rect_to_dict(monitor.monitor_rect) if monitor else None,
        "work_rect": rect_to_dict(monitor.work_rect) if monitor else None,
        "window_rect": rect_to_dict(window.rect) if window else None,
        "window_monitor_coverage_ratio": monitor.window_monitor_coverage_ratio if monitor else None,
        "screenshot_size": {
            "width": capture.screenshot_width if capture else None,
            "height": capture.screenshot_height if capture else None,
        },
        "capture_elapsed_ms": capture.capture_elapsed_ms if capture else None,
        "image_path": str(capture.image_path) if capture else None,
        "coordinate_contract_version": COORDINATE_CONTRACT_VERSION,
        "coordinate_contract": {
            "primary_detection_coordinate": "image_pixel",
            "primary_live_readonly_basis": "monitor_relative",
            "center_image_px_equals_center_monitor_px": True if capture else None,
            "is_screen_coordinate": False,
            "is_mouse_coordinate": False,
            "is_click_target": False,
            "action_authorized": False,
        },
        "model": {
            "model_path": str(args.model),
            "loaded": ctx is not None,
            "device": ctx.actual_device if ctx else None,
            "conf": args.conf,
            "iou": args.iou,
            "max_det": args.max_det,
            "imgsz": args.imgsz,
        },
        "summary": {
            "num_detections": len(detections),
            "max_confidence": max(confidences) if confidences else None,
            "min_confidence": min(confidences) if confidences else None,
        },
        "detections": detections,
        "safety": SAFETY_BOUNDARY,
    }


def process_frame(
    *,
    args: argparse.Namespace,
    frame_index: int,
    title_keywords: tuple[str, ...],
    ctx: InferenceContext | None,
) -> tuple[dict[str, Any], InferenceContext | None]:
    timestamp = now_iso()
    stem = f"frame_{frame_index:04d}_{safe_timestamp(timestamp)}"
    gate = get_gate_state(title_keywords)
    capture: CaptureResult | None = None
    detections: list[dict[str, Any]] = []
    error = ""

    if not gate["blocked"]:
        try:
            if ctx is None:
                ctx = load_inference_context(args)
            capture_path = args.output_dir / "captured_frames" / f"{stem}.png"
            capture = capture_monitor(gate["monitor"], capture_path)
            results = run_inference(ctx, capture.image_path)
            detections = detections_from_results(ctx, results, capture.screenshot_width, capture.screenshot_height)
            if args.review_images:
                review_path = args.output_dir / "review_images" / f"{stem}_review.png"
                draw_review_image(capture.image_path, detections, review_path)
        except Exception as exc:
            error = f"frame_error:{type(exc).__name__}:{exc}"

    frame_json = build_frame_json(
        args=args,
        frame_index=frame_index,
        timestamp=timestamp,
        gate=gate,
        capture=capture,
        detections=detections,
        ctx=ctx,
        error=error,
    )
    json_path = args.output_dir / "json" / f"{stem}.json"
    write_json(json_path, frame_json)
    frame_json["_json_path"] = str(json_path)
    if capture and args.review_images:
        frame_json["_review_image_path"] = str(args.output_dir / "review_images" / f"{stem}_review.png")
    else:
        frame_json["_review_image_path"] = ""
    return frame_json, ctx


def summary_row(frame_json: dict[str, Any]) -> dict[str, Any]:
    return {
        "frame_index": frame_json["frame_index"],
        "timestamp": frame_json["timestamp"],
        "blocked": frame_json["blocked"],
        "blocked_reason": frame_json["blocked_reason"],
        "aimlab_foreground_gate_passed": frame_json["aimlab_foreground_gate_passed"],
        "screenshot_width": frame_json["screenshot_size"]["width"],
        "screenshot_height": frame_json["screenshot_size"]["height"],
        "num_detections": frame_json["summary"]["num_detections"],
        "max_confidence": frame_json["summary"]["max_confidence"],
        "min_confidence": frame_json["summary"]["min_confidence"],
        "image_path": frame_json["image_path"] or "",
        "json_path": frame_json.get("_json_path", ""),
        "review_image_path": frame_json.get("_review_image_path", ""),
        "is_mouse_coordinate": False,
        "is_click_target": False,
        "action_authorized": False,
        "status": "blocked" if frame_json["blocked"] else "ok",
    }


def write_run_config(args: argparse.Namespace, title_keywords: tuple[str, ...], started_at: str) -> None:
    write_json(
        args.output_dir / "run_config.json",
        {
            "phase": PHASE_NAME,
            "timestamp": started_at,
            "command_args": args_to_jsonable(args),
            "mode": args.mode,
            "model_path": str(args.model),
            "output_dir": str(args.output_dir),
            "title_keywords": list(title_keywords),
            "coordinate_contract_version": COORDINATE_CONTRACT_VERSION,
            "coordinate_contract": {
                "image_pixel": True,
                "monitor_relative": True,
                "screen_coordinate_authorized": False,
                "mouse_coordinate_authorized": False,
                "click_target_authorized": False,
                "action_authorized": False,
            },
            "safety_boundary": SAFETY_BOUNDARY,
        },
    )


def write_phase_summary(args: argparse.Namespace, rows: list[dict[str, Any]], started_at: str, ended_at: str) -> None:
    total_detections = sum(int(row["num_detections"] or 0) for row in rows)
    blocked_count = sum(1 for row in rows if row["blocked"])
    write_json(
        args.output_dir / "phase6_summary.json",
        {
            "phase": PHASE_NAME,
            "started_at": started_at,
            "ended_at": ended_at,
            "mode": args.mode,
            "frames_requested": 1 if args.mode == "single" else args.max_frames,
            "frames_processed": len(rows),
            "blocked_frame_count": blocked_count,
            "unblocked_frame_count": len(rows) - blocked_count,
            "total_detection_count": total_detections,
            "output_dir": str(args.output_dir),
            "review_images_enabled": args.review_images,
            "coordinate_contract_version": COORDINATE_CONTRACT_VERSION,
            "safety_boundary_confirmed": True,
            "safety_boundary": SAFETY_BOUNDARY,
        },
    )


def main() -> int:
    args = parse_args()
    if args.max_frames < 1:
        print("ERROR: --max-frames must be >= 1", file=sys.stderr)
        return 2
    if args.interval_sec < 0:
        print("ERROR: --interval-sec must be >= 0", file=sys.stderr)
        return 2

    try:
        prepare_output_dir(args.output_dir, args.overwrite)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    title_keywords = tuple(args.title_keywords or ("aimlab", "aim lab"))
    started_at = now_iso()
    write_run_config(args, title_keywords, started_at)

    frame_count = 1 if args.mode == "single" else args.max_frames
    ctx: InferenceContext | None = None
    rows: list[dict[str, Any]] = []
    for frame_index in range(frame_count):
        frame_json, ctx = process_frame(args=args, frame_index=frame_index, title_keywords=title_keywords, ctx=ctx)
        rows.append(summary_row(frame_json))
        if args.mode == "loop" and frame_index < frame_count - 1:
            time.sleep(args.interval_sec)

    summary_fields = [
        "frame_index",
        "timestamp",
        "blocked",
        "blocked_reason",
        "aimlab_foreground_gate_passed",
        "screenshot_width",
        "screenshot_height",
        "num_detections",
        "max_confidence",
        "min_confidence",
        "image_path",
        "json_path",
        "review_image_path",
        "is_mouse_coordinate",
        "is_click_target",
        "action_authorized",
        "status",
    ]
    write_csv(args.output_dir / "live_summary.csv", rows, summary_fields)
    ended_at = now_iso()
    write_phase_summary(args, rows, started_at, ended_at)

    blocked_count = sum(1 for row in rows if row["blocked"])
    total_detections = sum(int(row["num_detections"] or 0) for row in rows)
    print(f"phase={PHASE_NAME}")
    print(f"mode={args.mode}")
    print(f"frames_processed={len(rows)}")
    print(f"blocked_frames={blocked_count}")
    print(f"total_detections={total_detections}")
    print(f"output_dir={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
