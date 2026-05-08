from __future__ import annotations

import argparse
import ctypes
import csv
import json
import math
import platform
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


PHASE_NAME = "phase7_direct_cursor_positioning"
DEFAULT_MODEL = Path("runs/detect/phase3_yolo11n_baseline/weights/best.pt")
DEFAULT_CONFIG = Path("config/phase7-cursor-positioning.json")
DEFAULT_OUTPUT_ROOT = Path("runs/phase7_direct_cursor_positioning")
COORDINATE_CONTRACT_VERSION = "phase7_monitor_relative_to_windows_screen_v1"
SUPPORTED_TARGET_SELECTION = {"nearest_to_cursor", "highest_conf", "nearest_to_screen_center"}
SAFETY_BOUNDARY = {
    "one_shot": True,
    "aimlab_foreground_required": True,
    "mouse_movement_default": False,
    "mouse_movement_requires_config_allow": True,
    "mouse_movement_requires_execute_move_cli": True,
    "mouse_movement_requires_local_confirm_cli": True,
    "mouse_click": False,
    "auto_aim_loop": False,
    "target_lock": False,
    "closed_loop_automation": False,
    "anti_cheat_bypass": False,
    "process_memory_read": False,
    "aimlab_file_modification": False,
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
    parser = argparse.ArgumentParser(description="Phase 7 one-shot direct cursor positioning for local AIMLAB.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.70)
    parser.add_argument("--max-det", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--start-delay-sec", type=float, default=3.0)
    parser.add_argument("--execute-move", action="store_true", default=False)
    parser.add_argument("--confirm-local-aimlab-only", action="store_true", default=False)
    parser.add_argument("--target-selection", choices=sorted(SUPPORTED_TARGET_SELECTION))
    parser.add_argument("--review-image", dest="review_image", action="store_true", default=True)
    parser.add_argument("--no-review-image", dest="review_image", action="store_false")
    parser.add_argument("--overwrite", action="store_true", default=False)
    parser.add_argument("--title-keyword", action="append", dest="title_keywords")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def default_run_id() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")


def round_float(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)
    return config


def args_to_jsonable(args: argparse.Namespace) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in vars(args).items():
        result[key] = str(value) if isinstance(value, Path) else value
    return result


def prepare_run_dir(output_root: Path, run_id: str, overwrite: bool) -> Path:
    run_dir = output_root / run_id
    if run_dir.exists():
        if not overwrite:
            raise FileExistsError(f"run directory already exists; pass --overwrite to replace it: {run_dir}")
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_summary_csv(path: Path, row: dict[str, Any]) -> None:
    fieldnames = [
        "phase",
        "timestamp",
        "blocked",
        "blocked_reason",
        "detections_count",
        "target_selection",
        "chosen_detection_index",
        "chosen_conf",
        "cursor_before_screen_x",
        "cursor_before_screen_y",
        "planned_cursor_screen_x",
        "planned_cursor_screen_y",
        "cursor_after_screen_x",
        "cursor_after_screen_y",
        "move_executed",
        "move_denied_reason",
        "run_dir",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)


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


def rect_to_dict(rect: Any | None) -> dict[str, int] | None:
    return rect.to_dict() if rect is not None else None


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
    for detection_index, (xyxy, confidence, class_id_value) in enumerate(zip(xyxy_values, conf_values, cls_values)):
        x1, y1, x2, y2 = [float(value) for value in xyxy]
        bbox_w = x2 - x1
        bbox_h = y2 - y1
        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0
        class_id = int(class_id_value)
        detections.append(
            {
                "detection_index": detection_index,
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
                "center_image_px": {"x": round_float(center_x), "y": round_float(center_y)},
                "center_monitor_px": {"x": round_float(center_x), "y": round_float(center_y)},
                "coordinate_space": "image_pixel_and_monitor_relative",
                "validity": validate_detection(x1, y1, x2, y2, width, height),
            }
        )
    return detections


def require_windows() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("Phase 7 cursor positioning requires Windows cursor APIs.")


def user32() -> ctypes.WinDLL:
    require_windows()
    return ctypes.WinDLL("user32", use_last_error=True)


def get_cursor_pos() -> dict[str, int]:
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    point = POINT()
    api = user32()
    if not api.GetCursorPos(ctypes.byref(point)):
        raise ctypes.WinError(ctypes.get_last_error())
    return {"x": int(point.x), "y": int(point.y)}


def set_cursor_pos(x: int, y: int) -> None:
    api = user32()
    if not api.SetCursorPos(int(x), int(y)):
        raise ctypes.WinError(ctypes.get_last_error())


def distance(a: dict[str, float | int], b: dict[str, float | int]) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def detection_screen_center(detection: dict[str, Any], monitor: MonitorInfo) -> dict[str, float]:
    center = detection["center_monitor_px"]
    return {
        "x": float(monitor.monitor_rect.left) + float(center["x"]),
        "y": float(monitor.monitor_rect.top) + float(center["y"]),
    }


def choose_primary_target(
    detections: list[dict[str, Any]],
    monitor: MonitorInfo,
    cursor_before: dict[str, int] | None,
    strategy: str,
) -> dict[str, Any] | None:
    if not detections:
        return None
    if strategy == "highest_conf":
        return max(detections, key=lambda item: float(item.get("confidence") or 0))
    if strategy == "nearest_to_screen_center":
        screen_center = {
            "x": monitor.monitor_rect.left + monitor.monitor_rect.width / 2,
            "y": monitor.monitor_rect.top + monitor.monitor_rect.height / 2,
        }
        return min(detections, key=lambda item: distance(detection_screen_center(item, monitor), screen_center))
    if cursor_before is None:
        return max(detections, key=lambda item: float(item.get("confidence") or 0))
    return min(detections, key=lambda item: distance(detection_screen_center(item, monitor), cursor_before))


def point_inside_monitor(point: dict[str, float | int], monitor: MonitorInfo) -> bool:
    rect = monitor.monitor_rect
    return rect.left <= float(point["x"]) < rect.right and rect.top <= float(point["y"]) < rect.bottom


def center_inside_capture(center: dict[str, float | int], capture: CaptureResult) -> bool:
    return 0 <= float(center["x"]) <= capture.screenshot_width and 0 <= float(center["y"]) <= capture.screenshot_height


def build_move_gate(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    gate: dict[str, Any],
    chosen: dict[str, Any] | None,
    capture: CaptureResult | None,
    monitor: MonitorInfo | None,
    planned: dict[str, float] | None,
    cursor_before: dict[str, int] | None,
) -> dict[str, Any]:
    checks: dict[str, bool] = {
        "config_allow_mouse_move": bool(config.get("allow_mouse_move") is True),
        "cli_execute_move": bool(args.execute_move),
        "cli_confirm_local_aimlab_only": bool(args.confirm_local_aimlab_only),
        "config_allow_click_false": config.get("allow_click") is False,
        "config_allow_loop_false": config.get("allow_loop") is False,
        "config_allow_closed_loop_false": config.get("allow_closed_loop") is False,
        "aimlab_foreground_gate_passed": bool(not gate.get("blocked")),
        "chosen_target_exists": chosen is not None,
        "center_monitor_inside_capture": bool(chosen and capture and center_inside_capture(chosen["center_monitor_px"], capture)),
        "planned_cursor_inside_monitor": bool(planned and monitor and point_inside_monitor(planned, monitor)),
    }
    max_jump = config.get("max_direct_jump_px")
    if max_jump in (None, 0):
        checks["max_direct_jump_ok"] = True
    else:
        checks["max_direct_jump_ok"] = bool(
            cursor_before and planned and distance(cursor_before, planned) <= float(max_jump)
        )

    denied_reasons = [name for name, passed in checks.items() if not passed]
    return {
        "checks": checks,
        "allowed_to_move": not denied_reasons,
        "move_denied_reason": "" if not denied_reasons else ";".join(denied_reasons),
    }


def draw_review_image(
    image_path: Path,
    detections: list[dict[str, Any]],
    chosen: dict[str, Any] | None,
    planned_monitor_px: dict[str, float] | None,
    output_path: Path,
) -> None:
    from PIL import Image, ImageDraw, ImageFont

    with Image.open(image_path).convert("RGB") as image:
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 11)
        except OSError:
            font = ImageFont.load_default()
        chosen_index = chosen.get("detection_index") if chosen else None
        for detection in detections:
            bbox = detection["bbox_xyxy"]
            center = detection["center_monitor_px"]
            is_chosen = detection.get("detection_index") == chosen_index
            color = (255, 0, 0) if is_chosen else (0, 255, 0)
            width = 3 if is_chosen else 1
            x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
            cx, cy = center["x"], center["y"]
            draw.rectangle((x1, y1, x2, y2), outline=color, width=width)
            draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), outline=color, width=2)
            draw.text((max(0, x1), max(0, y1 - 13)), f"{detection['confidence']:.2f}", fill=color, font=font)
        if planned_monitor_px:
            px = planned_monitor_px["x"]
            py = planned_monitor_px["y"]
            draw.line((px - 8, py, px + 8, py), fill=(255, 255, 0), width=2)
            draw.line((px, py - 8, px, py + 8), fill=(255, 255, 0), width=2)
            draw.text((max(0, px + 6), max(0, py + 6)), "planned cursor", fill=(255, 255, 0), font=font)
        image.save(output_path)


def build_outputs(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    run_dir: Path,
    gate: dict[str, Any],
    capture: CaptureResult | None,
    detections: list[dict[str, Any]],
    chosen: dict[str, Any] | None,
    cursor_before: dict[str, int] | None,
    planned: dict[str, float] | None,
    cursor_after: dict[str, int] | None,
    move_gate: dict[str, Any],
    move_executed: bool,
    error: str,
    started_at: str,
    ended_at: str,
    ctx: InferenceContext | None,
) -> dict[str, Any]:
    window: WindowInfo | None = gate.get("window")
    foreground: WindowInfo | None = gate.get("foreground")
    monitor: MonitorInfo | None = gate.get("monitor")
    chosen_target = {
        "target_selection": config.get("target_selection", "nearest_to_cursor"),
        "detections_count": len(detections),
        "chosen_detection_index": chosen.get("detection_index") if chosen else None,
        "chosen_conf": chosen.get("confidence") if chosen else None,
        "chosen_bbox_xyxy": chosen.get("bbox_xyxy") if chosen else None,
        "chosen_center_monitor_px": chosen.get("center_monitor_px") if chosen else None,
        "cursor_before_screen_px": cursor_before,
        "cursor_screen_px": planned,
        "planned_cursor_screen_px": planned,
        "cursor_after_screen_px": cursor_after,
        "move_executed": move_executed,
        "move_denied_reason": move_gate.get("move_denied_reason", ""),
    }
    summary = {
        "phase": PHASE_NAME,
        "started_at": started_at,
        "ended_at": ended_at,
        "run_dir": str(run_dir),
        "blocked": bool(gate.get("blocked")) or bool(error),
        "blocked_reason": str(gate.get("blocked_reason") or error),
        "frames_processed": 1,
        "detections_count": len(detections),
        "target_selection": config.get("target_selection", "nearest_to_cursor"),
        "chosen_detection_index": chosen_target["chosen_detection_index"],
        "chosen_conf": chosen_target["chosen_conf"],
        "coordinate_space": "monitor_relative_to_windows_screen",
        "monitor_rect": rect_to_dict(monitor.monitor_rect) if monitor else None,
        "work_rect": rect_to_dict(monitor.work_rect) if monitor else None,
        "window_rect": rect_to_dict(window.rect) if window else None,
        "screenshot_size": {
            "width": capture.screenshot_width if capture else None,
            "height": capture.screenshot_height if capture else None,
        },
        "cursor_before_screen_px": cursor_before,
        "cursor_screen_px": planned,
        "planned_cursor_screen_px": planned,
        "cursor_after_screen_px": cursor_after,
        "move_gate": move_gate,
        "move_executed": move_executed,
        "move_denied_reason": move_gate.get("move_denied_reason", ""),
        "no_click_performed": True,
        "one_shot": True,
        "closed_loop": False,
        "target_lock": False,
        "safety_boundary": SAFETY_BOUNDARY,
    }
    detections_json = {
        "phase": PHASE_NAME,
        "coordinate_contract_version": COORDINATE_CONTRACT_VERSION,
        "coordinate_space": {
            "center_monitor_px": "monitor_relative",
            "cursor_screen_px": "windows_screen_pixel",
            "is_click_target": False,
            "click_authorized": False,
        },
        "aimlab_foreground_gate_passed": bool(not gate.get("blocked")),
        "aimlab_window_title": window.title if window else None,
        "foreground_window_title": foreground.title if foreground else None,
        "monitor_rect": summary["monitor_rect"],
        "window_rect": summary["window_rect"],
        "image_path": str(capture.image_path) if capture else None,
        "detections": detections,
    }
    run_config = {
        "phase": PHASE_NAME,
        "started_at": started_at,
        "ended_at": ended_at,
        "args": args_to_jsonable(args),
        "config_path": str(args.config),
        "config": config,
        "model_path": str(args.model),
        "model_loaded": ctx is not None,
        "device": ctx.actual_device if ctx else None,
        "output_files": {
            "frame": str(run_dir / "frame.png"),
            "review_image": str(run_dir / "review_image.png"),
            "detections": str(run_dir / "detections.json"),
            "chosen_target": str(run_dir / "chosen_target.json"),
            "phase7_summary": str(run_dir / "phase7_summary.json"),
            "summary_csv": str(run_dir / "summary.csv"),
        },
        "safety_boundary": SAFETY_BOUNDARY,
    }
    return {
        "detections_json": detections_json,
        "chosen_target": chosen_target,
        "summary": summary,
        "run_config": run_config,
    }


def main() -> int:
    args = parse_args()
    started_at = now_iso()
    try:
        config = load_config(args.config)
        target_selection = args.target_selection or config.get("target_selection", "nearest_to_cursor")
        if target_selection not in SUPPORTED_TARGET_SELECTION:
            raise ValueError(f"unsupported target_selection: {target_selection}")
        config["target_selection"] = target_selection
        run_id = args.run_id or default_run_id()
        run_dir = prepare_run_dir(args.output_root, run_id, args.overwrite)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.start_delay_sec > 0:
        time.sleep(args.start_delay_sec)

    title_keywords = tuple(args.title_keywords or ("aimlab", "aim lab"))
    gate = get_gate_state(title_keywords)
    ctx: InferenceContext | None = None
    capture: CaptureResult | None = None
    detections: list[dict[str, Any]] = []
    chosen: dict[str, Any] | None = None
    cursor_before: dict[str, int] | None = None
    cursor_after: dict[str, int] | None = None
    planned: dict[str, float] | None = None
    move_executed = False
    error = ""

    try:
        try:
            cursor_before = get_cursor_pos()
        except Exception as exc:
            error = f"cursor_before_error:{type(exc).__name__}:{exc}"

        if not gate["blocked"] and not error:
            ctx = load_inference_context(args)
            capture = capture_monitor(gate["monitor"], run_dir / "frame.png")
            results = run_inference(ctx, capture.image_path)
            detections = detections_from_results(ctx, results, capture.screenshot_width, capture.screenshot_height)
            chosen = choose_primary_target(detections, gate["monitor"], cursor_before, target_selection)
            if chosen:
                planned = detection_screen_center(chosen, gate["monitor"])
                planned = {"x": round_float(planned["x"]), "y": round_float(planned["y"])}
    except Exception as exc:
        error = f"phase7_error:{type(exc).__name__}:{exc}"

    move_gate = build_move_gate(
        args=args,
        config=config,
        gate=gate,
        chosen=chosen,
        capture=capture,
        monitor=gate.get("monitor"),
        planned=planned,
        cursor_before=cursor_before,
    )
    if move_gate["allowed_to_move"] and planned:
        try:
            set_cursor_pos(int(round(planned["x"])), int(round(planned["y"])))
            move_executed = True
        except Exception as exc:
            move_gate["allowed_to_move"] = False
            move_gate["move_denied_reason"] = f"set_cursor_pos_error:{type(exc).__name__}:{exc}"
    if move_executed:
        try:
            cursor_after = get_cursor_pos()
        except Exception as exc:
            cursor_after = None
            move_gate["cursor_after_error"] = f"{type(exc).__name__}:{exc}"

    if capture and args.review_image:
        planned_monitor_px = chosen["center_monitor_px"] if chosen else None
        draw_review_image(capture.image_path, detections, chosen, planned_monitor_px, run_dir / "review_image.png")

    ended_at = now_iso()
    outputs = build_outputs(
        args=args,
        config=config,
        run_dir=run_dir,
        gate=gate,
        capture=capture,
        detections=detections,
        chosen=chosen,
        cursor_before=cursor_before,
        planned=planned,
        cursor_after=cursor_after,
        move_gate=move_gate,
        move_executed=move_executed,
        error=error,
        started_at=started_at,
        ended_at=ended_at,
        ctx=ctx,
    )
    write_json(run_dir / "detections.json", outputs["detections_json"])
    write_json(run_dir / "chosen_target.json", outputs["chosen_target"])
    write_json(run_dir / "phase7_summary.json", outputs["summary"])
    write_json(run_dir / "run_config.json", outputs["run_config"])
    summary = outputs["summary"]
    write_summary_csv(
        run_dir / "summary.csv",
        {
            "phase": PHASE_NAME,
            "timestamp": ended_at,
            "blocked": summary["blocked"],
            "blocked_reason": summary["blocked_reason"],
            "detections_count": summary["detections_count"],
            "target_selection": summary["target_selection"],
            "chosen_detection_index": summary["chosen_detection_index"],
            "chosen_conf": summary["chosen_conf"],
            "cursor_before_screen_x": (cursor_before or {}).get("x"),
            "cursor_before_screen_y": (cursor_before or {}).get("y"),
            "planned_cursor_screen_x": (planned or {}).get("x"),
            "planned_cursor_screen_y": (planned or {}).get("y"),
            "cursor_after_screen_x": (cursor_after or {}).get("x"),
            "cursor_after_screen_y": (cursor_after or {}).get("y"),
            "move_executed": move_executed,
            "move_denied_reason": summary["move_denied_reason"],
            "run_dir": str(run_dir),
        },
    )

    print(f"phase={PHASE_NAME}")
    print("mode=execute-move" if args.execute_move else "mode=dry-run")
    print("frames_processed=1")
    print(f"blocked={summary['blocked']}")
    print(f"detections_count={summary['detections_count']}")
    print(f"chosen_detection_index={summary['chosen_detection_index']}")
    print(f"move_executed={move_executed}")
    print(f"move_denied_reason={summary['move_denied_reason']}")
    print(f"run_dir={run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
