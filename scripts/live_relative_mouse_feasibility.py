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


PHASE_NAME = "phase75_relative_mouse_feasibility"
DEFAULT_MODEL = Path("runs/detect/phase3_yolo11n_baseline/weights/best.pt")
DEFAULT_CONFIG = Path("config/phase75-relative-mouse-feasibility.json")
DEFAULT_OUTPUT_ROOT = Path("runs/phase75_relative_mouse_feasibility")
SUPPORTED_TARGET_SELECTION = {"nearest_to_crosshair"}
MOUSEINPUT_MOVE = 0x0001
INPUT_MOUSE = 0
SAFETY_BOUNDARY = {
    "one_shot": True,
    "relative_mouse_move_default": False,
    "relative_mouse_move_requires_config_allow": True,
    "relative_mouse_move_requires_execute_cli": True,
    "relative_mouse_move_requires_local_confirm_cli": True,
    "mouse_click": False,
    "auto_aim": False,
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
    parser = argparse.ArgumentParser(description="Phase 7.5 one-shot relative mouse movement feasibility test.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.70)
    parser.add_argument("--max-det", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--start-delay-sec", type=float, default=5.0)
    parser.add_argument("--relative-dx", type=int)
    parser.add_argument("--relative-dy", type=int)
    parser.add_argument("--settle-sec", type=float)
    parser.add_argument("--execute-relative-move", action="store_true", default=False)
    parser.add_argument("--confirm-local-aimlab-only", action="store_true", default=False)
    parser.add_argument("--target-selection", choices=sorted(SUPPORTED_TARGET_SELECTION))
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
        return json.load(f)


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
        "frames_processed",
        "before_detections_count",
        "after_detections_count",
        "relative_dx",
        "relative_dy",
        "relative_move_executed",
        "move_denied_reason",
        "match_status",
        "calibration_status",
        "px_per_mouse_count_x",
        "px_per_mouse_count_y",
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
        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0
        bbox_w = x2 - x1
        bbox_h = y2 - y1
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
                "center_monitor_px": {"x": round_float(center_x), "y": round_float(center_y)},
                "coordinate_space": "monitor_relative",
                "validity": validate_detection(x1, y1, x2, y2, width, height),
            }
        )
    return detections


def distance(a: dict[str, float | int], b: dict[str, float | int]) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def crosshair_center(monitor: MonitorInfo) -> dict[str, float]:
    return {
        "x": round_float(monitor.monitor_rect.width / 2),
        "y": round_float(monitor.monitor_rect.height / 2),
    }


def choose_reference_target(detections: list[dict[str, Any]], center: dict[str, float]) -> dict[str, Any] | None:
    if not detections:
        return None
    return min(detections, key=lambda item: distance(item["center_monitor_px"], center))


def delta_to_crosshair(target: dict[str, Any] | None, center: dict[str, float]) -> dict[str, float] | None:
    if not target:
        return None
    target_center = target["center_monitor_px"]
    return {
        "dx": round_float(float(target_center["x"]) - float(center["x"])),
        "dy": round_float(float(target_center["y"]) - float(center["y"])),
    }


def require_windows() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("Phase 7.5 relative mouse feasibility requires Windows input APIs.")


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("union", INPUTUNION)]


def send_relative_mouse_move(dx: int, dy: int) -> None:
    require_windows()
    extra = ctypes.c_ulong(0)
    input_event = INPUT(
        type=INPUT_MOUSE,
        union=INPUTUNION(mi=MOUSEINPUT(dx, dy, 0, MOUSEINPUT_MOVE, 0, ctypes.pointer(extra))),
    )
    sent = ctypes.windll.user32.SendInput(1, ctypes.byref(input_event), ctypes.sizeof(INPUT))
    if sent != 1:
        raise ctypes.WinError(ctypes.get_last_error())


def build_relative_move_gate(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    gate: dict[str, Any],
    reference_target: dict[str, Any] | None,
    relative_dx: int,
    relative_dy: int,
) -> dict[str, Any]:
    max_abs_dx = int(config.get("max_abs_relative_dx", 0))
    max_abs_dy = int(config.get("max_abs_relative_dy", 0))
    checks = {
        "config_allow_relative_mouse_move": config.get("allow_relative_mouse_move") is True,
        "cli_execute_relative_move": bool(args.execute_relative_move),
        "cli_confirm_local_aimlab_only": bool(args.confirm_local_aimlab_only),
        "aimlab_foreground_gate_passed": not bool(gate.get("blocked")),
        "config_allow_click_false": config.get("allow_click") is False,
        "config_allow_loop_false": config.get("allow_loop") is False,
        "config_allow_closed_loop_false": config.get("allow_closed_loop") is False,
        "relative_dx_within_limit": abs(relative_dx) <= max_abs_dx,
        "relative_dy_within_limit": abs(relative_dy) <= max_abs_dy,
        "before_reference_target_exists": reference_target is not None,
    }
    denied_reasons = [name for name, passed in checks.items() if not passed]
    return {
        "allowed_to_move": not denied_reasons,
        "checks": checks,
        "move_denied_reason": "" if not denied_reasons else ";".join(denied_reasons),
    }


def match_after_target(
    reference_target: dict[str, Any] | None,
    after_detections: list[dict[str, Any]],
    max_match_distance_px: float,
) -> tuple[dict[str, Any] | None, str, str, float | None]:
    if reference_target is None:
        return None, "no_before_reference", "insufficient_before_reference", None
    if not after_detections:
        return None, "manual_review_required", "no_after_detections", None
    before_center = reference_target["center_monitor_px"]
    candidate = min(after_detections, key=lambda item: distance(item["center_monitor_px"], before_center))
    candidate_distance = distance(candidate["center_monitor_px"], before_center)
    if candidate_distance <= max_match_distance_px:
        return candidate, "matched", "matched", candidate_distance
    return candidate, "manual_review_required", "insufficient_match_confidence", candidate_distance


def observed_shift(before_target: dict[str, Any] | None, after_target: dict[str, Any] | None) -> dict[str, float] | None:
    if before_target is None or after_target is None:
        return None
    before_center = before_target["center_monitor_px"]
    after_center = after_target["center_monitor_px"]
    return {
        "dx": round_float(float(after_center["x"]) - float(before_center["x"])),
        "dy": round_float(float(after_center["y"]) - float(before_center["y"])),
    }


def calibration_from_shift(shift: dict[str, float] | None, relative_dx: int, relative_dy: int) -> tuple[float | None, float | None]:
    px_per_x = None
    px_per_y = None
    if shift and relative_dx != 0:
        px_per_x = round_float(float(shift["dx"]) / float(relative_dx))
    if shift and relative_dy != 0:
        px_per_y = round_float(float(shift["dy"]) / float(relative_dy))
    return px_per_x, px_per_y


def draw_review_image(
    image_path: Path,
    output_path: Path,
    detections: list[dict[str, Any]],
    crosshair: dict[str, float],
    reference_target: dict[str, Any] | None,
    matched_target: dict[str, Any] | None = None,
    shift: dict[str, float] | None = None,
) -> None:
    from PIL import Image, ImageDraw, ImageFont

    with Image.open(image_path).convert("RGB") as image:
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 11)
        except OSError:
            font = ImageFont.load_default()
        reference_index = reference_target.get("detection_index") if reference_target else None
        matched_index = matched_target.get("detection_index") if matched_target else None
        for detection in detections:
            bbox = detection["bbox_xyxy"]
            center = detection["center_monitor_px"]
            is_reference = detection.get("detection_index") == reference_index
            is_matched = detection.get("detection_index") == matched_index
            color = (255, 0, 0) if is_reference else (0, 128, 255) if is_matched else (0, 255, 0)
            width = 3 if is_reference or is_matched else 1
            x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
            cx, cy = center["x"], center["y"]
            draw.rectangle((x1, y1, x2, y2), outline=color, width=width)
            draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), outline=color, width=2)
            draw.text((max(0, x1), max(0, y1 - 13)), f"{detection['confidence']:.2f}", fill=color, font=font)
        cx = float(crosshair["x"])
        cy = float(crosshair["y"])
        draw.line((cx - 10, cy, cx + 10, cy), fill=(255, 255, 0), width=2)
        draw.line((cx, cy - 10, cx, cy + 10), fill=(255, 255, 0), width=2)
        draw.text((cx + 8, cy + 8), "crosshair", fill=(255, 255, 0), font=font)
        if reference_target and matched_target and shift:
            b = reference_target["center_monitor_px"]
            a = matched_target["center_monitor_px"]
            draw.line((b["x"], b["y"], a["x"], a["y"]), fill=(255, 255, 0), width=2)
            draw.text((a["x"] + 8, a["y"] + 8), f"shift({shift['dx']:.1f},{shift['dy']:.1f})", fill=(255, 255, 0), font=font)
        image.save(output_path)


def detection_doc(
    *,
    phase: str,
    image_path: Path | None,
    detections: list[dict[str, Any]],
    monitor: MonitorInfo | None,
    crosshair: dict[str, float] | None,
    reference: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "image_path": str(image_path) if image_path else None,
        "monitor_rect": rect_to_dict(monitor.monitor_rect) if monitor else None,
        "crosshair_center_monitor_px": crosshair,
        "reference_detection_index": reference.get("detection_index") if reference else None,
        "detections_count": len(detections),
        "detections": detections,
    }


def main() -> int:
    args = parse_args()
    started_at = now_iso()
    try:
        config = load_config(args.config)
        target_selection = args.target_selection or config.get("target_selection", "nearest_to_crosshair")
        if target_selection not in SUPPORTED_TARGET_SELECTION:
            raise ValueError(f"unsupported target_selection: {target_selection}")
        relative_dx = int(args.relative_dx if args.relative_dx is not None else config.get("default_relative_dx", 100))
        relative_dy = int(args.relative_dy if args.relative_dy is not None else config.get("default_relative_dy", 0))
        settle_sec = float(args.settle_sec if args.settle_sec is not None else config.get("settle_sec", 0.2))
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
    before_capture: CaptureResult | None = None
    after_capture: CaptureResult | None = None
    before_detections: list[dict[str, Any]] = []
    after_detections: list[dict[str, Any]] = []
    reference_target: dict[str, Any] | None = None
    after_reference: dict[str, Any] | None = None
    crosshair: dict[str, float] | None = None
    error = ""
    relative_move_executed = False
    sendinput_attempted = False

    try:
        if not gate["blocked"]:
            monitor: MonitorInfo = gate["monitor"]
            crosshair = crosshair_center(monitor)
            ctx = load_inference_context(args)
            before_capture = capture_monitor(monitor, run_dir / "before_frame.png")
            before_results = run_inference(ctx, before_capture.image_path)
            before_detections = detections_from_results(
                ctx, before_results, before_capture.screenshot_width, before_capture.screenshot_height
            )
            reference_target = choose_reference_target(before_detections, crosshair)
    except Exception as exc:
        error = f"before_phase_error:{type(exc).__name__}:{exc}"

    relative_move_gate = build_relative_move_gate(
        args=args,
        config=config,
        gate=gate,
        reference_target=reference_target,
        relative_dx=relative_dx,
        relative_dy=relative_dy,
    )

    if relative_move_gate["allowed_to_move"]:
        try:
            sendinput_attempted = True
            send_relative_mouse_move(relative_dx, relative_dy)
            relative_move_executed = True
        except Exception as exc:
            relative_move_gate["allowed_to_move"] = False
            relative_move_gate["move_denied_reason"] = f"sendinput_error:{type(exc).__name__}:{exc}"

    if relative_move_executed:
        time.sleep(settle_sec)
        try:
            monitor = gate["monitor"]
            after_capture = capture_monitor(monitor, run_dir / "after_frame.png")
            after_results = run_inference(ctx, after_capture.image_path)
            after_detections = detections_from_results(
                ctx, after_results, after_capture.screenshot_width, after_capture.screenshot_height
            )
        except Exception as exc:
            error = f"after_phase_error:{type(exc).__name__}:{exc}"

    match_distance: float | None = None
    if after_detections:
        after_reference, match_status, calibration_status, match_distance = match_after_target(
            reference_target,
            after_detections,
            float(config.get("max_match_distance_px", 300)),
        )
    elif relative_move_executed:
        match_status = "manual_review_required"
        calibration_status = "no_after_detections"
    else:
        match_status = "not_attempted_dry_run" if not relative_move_executed else "manual_review_required"
        calibration_status = "dry_run_no_after_frame" if not relative_move_executed else "insufficient_match_confidence"

    shift = observed_shift(reference_target, after_reference) if match_status == "matched" else None
    px_per_x, px_per_y = calibration_from_shift(shift, relative_dx, relative_dy)
    before_delta = delta_to_crosshair(reference_target, crosshair) if crosshair else None
    frames_processed = 1 + (1 if after_capture else 0)
    blocked = bool(gate.get("blocked")) or bool(error)
    blocked_reason = str(gate.get("blocked_reason") or error)

    if before_capture and crosshair:
        draw_review_image(
            before_capture.image_path,
            run_dir / "before_review_image.png",
            before_detections,
            crosshair,
            reference_target,
        )
    if after_capture and crosshair:
        draw_review_image(
            after_capture.image_path,
            run_dir / "after_review_image.png",
            after_detections,
            crosshair,
            reference_target,
            after_reference,
            shift,
        )

    monitor = gate.get("monitor")
    summary = {
        "phase": PHASE_NAME,
        "blocked": blocked,
        "blocked_reason": blocked_reason,
        "frames_processed": frames_processed,
        "before_detections_count": len(before_detections),
        "after_detections_count": len(after_detections),
        "target_selection": target_selection,
        "crosshair_center_monitor_px": crosshair,
        "before_reference_center_monitor_px": reference_target.get("center_monitor_px") if reference_target else None,
        "before_reference_delta_to_crosshair_px": before_delta,
        "planned_relative_move_dxdy": {"dx": relative_dx, "dy": relative_dy},
        "relative_move_gate": relative_move_gate,
        "relative_move_executed": relative_move_executed,
        "sendinput_attempted": sendinput_attempted,
        "after_reference_center_monitor_px": after_reference.get("center_monitor_px") if after_reference else None,
        "observed_screen_shift_px": shift,
        "px_per_mouse_count_x": px_per_x,
        "px_per_mouse_count_y": px_per_y,
        "match_status": match_status,
        "match_distance_px": round_float(match_distance),
        "calibration_status": calibration_status,
        "monitor_rect": rect_to_dict(monitor.monitor_rect) if monitor else None,
        "window_rect": rect_to_dict(gate["window"].rect) if gate.get("window") else None,
        "no_click_performed": True,
        "one_shot": True,
        "closed_loop": False,
        "target_lock": False,
        "safety_boundary": SAFETY_BOUNDARY,
        "run_dir": str(run_dir),
        "started_at": started_at,
        "ended_at": now_iso(),
    }
    run_config = {
        "phase": PHASE_NAME,
        "args": args_to_jsonable(args),
        "config_path": str(args.config),
        "config": config,
        "relative_dx": relative_dx,
        "relative_dy": relative_dy,
        "settle_sec": settle_sec,
        "model_path": str(args.model),
        "model_loaded": ctx is not None,
        "device": ctx.actual_device if ctx else None,
        "safety_boundary": SAFETY_BOUNDARY,
    }
    event = {
        "phase": PHASE_NAME,
        "relative_dx": relative_dx,
        "relative_dy": relative_dy,
        "relative_move_gate": relative_move_gate,
        "relative_move_executed": relative_move_executed,
        "sendinput_attempted": sendinput_attempted,
        "no_click_performed": True,
    }

    write_json(
        run_dir / "before_detections.json",
        detection_doc(
            phase=PHASE_NAME,
            image_path=before_capture.image_path if before_capture else None,
            detections=before_detections,
            monitor=monitor,
            crosshair=crosshair,
            reference=reference_target,
        ),
    )
    if after_capture or relative_move_executed:
        write_json(
            run_dir / "after_detections.json",
            detection_doc(
                phase=PHASE_NAME,
                image_path=after_capture.image_path if after_capture else None,
                detections=after_detections,
                monitor=monitor,
                crosshair=crosshair,
                reference=after_reference,
            ),
        )
    write_json(run_dir / "relative_move_event.json", event)
    write_json(run_dir / "phase75_summary.json", summary)
    write_json(run_dir / "run_config.json", run_config)
    write_summary_csv(
        run_dir / "summary.csv",
        {
            "phase": PHASE_NAME,
            "timestamp": summary["ended_at"],
            "blocked": blocked,
            "blocked_reason": blocked_reason,
            "frames_processed": frames_processed,
            "before_detections_count": len(before_detections),
            "after_detections_count": len(after_detections),
            "relative_dx": relative_dx,
            "relative_dy": relative_dy,
            "relative_move_executed": relative_move_executed,
            "move_denied_reason": relative_move_gate["move_denied_reason"],
            "match_status": match_status,
            "calibration_status": calibration_status,
            "px_per_mouse_count_x": px_per_x,
            "px_per_mouse_count_y": px_per_y,
            "run_dir": str(run_dir),
        },
    )

    print(f"phase={PHASE_NAME}")
    print("mode=execute-relative-move" if args.execute_relative_move else "mode=dry-run")
    print(f"blocked={blocked}")
    print(f"frames_processed={frames_processed}")
    print(f"before_detections_count={len(before_detections)}")
    print(f"after_detections_count={len(after_detections)}")
    print(f"relative_move_executed={relative_move_executed}")
    print(f"match_status={match_status}")
    print(f"calibration_status={calibration_status}")
    print(f"run_dir={run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
