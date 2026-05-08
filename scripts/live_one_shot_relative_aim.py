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


PHASE_NAME = "phase8_one_shot_relative_aim"
DEFAULT_MODEL = Path("runs/detect/phase3_yolo11n_baseline/weights/best.pt")
DEFAULT_CONFIG = Path("config/phase8-one-shot-relative-aim.json")
DEFAULT_OUTPUT_ROOT = Path("runs/phase8_one_shot_relative_aim")
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
    "auto_click": False,
    "auto_aim_loop": False,
    "target_lock": False,
    "closed_loop_correction": False,
    "pid": False,
    "micro_step_move": False,
    "smooth_move": False,
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
    parser = argparse.ArgumentParser(description="Phase 8 one-shot relative aim to nearest AIMLAB yellow target.")
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
    parser.add_argument("--execute-relative-aim", action="store_true", default=False)
    parser.add_argument("--confirm-local-aimlab-only", action="store_true", default=False)
    parser.add_argument("--target-selection", choices=sorted(SUPPORTED_TARGET_SELECTION))
    parser.add_argument("--settle-sec", type=float)
    parser.add_argument("--px-per-mouse-count-x", type=float)
    parser.add_argument("--px-per-mouse-count-y", type=float)
    parser.add_argument("--max-abs-relative-dx", type=int)
    parser.add_argument("--max-abs-relative-dy", type=int)
    parser.add_argument("--no-after-validation", action="store_true", default=False)
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
        "detections_count",
        "after_detections_count",
        "chosen_detection_index",
        "before_distance_to_crosshair_px",
        "after_distance_to_crosshair_px",
        "distance_reduction_px",
        "distance_reduction_ratio",
        "rounded_relative_dx",
        "rounded_relative_dy",
        "relative_aim_executed",
        "aim_denied_reason",
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


def choose_primary_target(detections: list[dict[str, Any]], center: dict[str, float]) -> dict[str, Any] | None:
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


def planned_relative_move(
    delta: dict[str, float] | None,
    px_per_mouse_count_x: float | None,
    px_per_mouse_count_y: float | None,
) -> tuple[dict[str, float] | None, dict[str, int] | None]:
    if delta is None or px_per_mouse_count_x in (None, 0) or px_per_mouse_count_y in (None, 0):
        return None, None
    mouse_dx = -float(delta["dx"]) / float(px_per_mouse_count_x)
    mouse_dy = -float(delta["dy"]) / float(px_per_mouse_count_y)
    planned = {"dx": round_float(mouse_dx), "dy": round_float(mouse_dy)}
    rounded = {"dx": int(round(mouse_dx)), "dy": int(round(mouse_dy))}
    return planned, rounded


def require_windows() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("Phase 8 relative aim requires Windows input APIs.")


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


def build_relative_aim_gate(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    gate: dict[str, Any],
    target: dict[str, Any] | None,
    px_per_mouse_count_x: float | None,
    px_per_mouse_count_y: float | None,
    rounded_move: dict[str, int] | None,
    max_abs_relative_dx: int,
    max_abs_relative_dy: int,
) -> dict[str, Any]:
    checks = {
        "config_allow_relative_mouse_move": config.get("allow_relative_mouse_move") is True,
        "cli_execute_relative_aim": bool(args.execute_relative_aim),
        "cli_confirm_local_aimlab_only": bool(args.confirm_local_aimlab_only),
        "aimlab_foreground_gate_passed": not bool(gate.get("blocked")),
        "config_allow_click_false": config.get("allow_click") is False,
        "config_allow_loop_false": config.get("allow_loop") is False,
        "config_allow_closed_loop_false": config.get("allow_closed_loop") is False,
        "before_target_exists": target is not None,
        "px_per_mouse_count_x_valid": px_per_mouse_count_x not in (None, 0),
        "px_per_mouse_count_y_valid": px_per_mouse_count_y not in (None, 0),
        "relative_dx_within_limit": rounded_move is not None and abs(int(rounded_move["dx"])) <= max_abs_relative_dx,
        "relative_dy_within_limit": rounded_move is not None and abs(int(rounded_move["dy"])) <= max_abs_relative_dy,
    }
    denied_reasons = [name for name, passed in checks.items() if not passed]
    return {
        "allowed_to_move": not denied_reasons,
        "checks": checks,
        "aim_denied_reason": "" if not denied_reasons else ";".join(denied_reasons),
    }


def match_after_target(
    before_target: dict[str, Any] | None,
    after_detections: list[dict[str, Any]],
    crosshair: dict[str, float] | None,
) -> tuple[dict[str, Any] | None, str]:
    if before_target is None:
        return None, "no_before_target"
    if not after_detections:
        return None, "no_after_detections"
    if crosshair is None:
        return min(after_detections, key=lambda item: distance(item["center_monitor_px"], before_target["center_monitor_px"])), "matched_by_before_center"
    return min(after_detections, key=lambda item: distance(item["center_monitor_px"], crosshair)), "matched_nearest_to_crosshair"


def distance_reduction(before_distance: float | None, after_distance: float | None) -> tuple[float | None, float | None]:
    if before_distance is None or after_distance is None:
        return None, None
    reduction = float(before_distance) - float(after_distance)
    ratio = None if before_distance == 0 else reduction / float(before_distance)
    return round_float(reduction), round_float(ratio)


def draw_review_image(
    image_path: Path,
    output_path: Path,
    detections: list[dict[str, Any]],
    crosshair: dict[str, float],
    chosen_target: dict[str, Any] | None,
    *,
    planned_move: dict[str, float] | None = None,
    after_target: dict[str, Any] | None = None,
    after_distance: float | None = None,
) -> None:
    from PIL import Image, ImageDraw, ImageFont

    with Image.open(image_path).convert("RGB") as image:
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except OSError:
            font = ImageFont.load_default()
        chosen_index = chosen_target.get("detection_index") if chosen_target else None
        after_index = after_target.get("detection_index") if after_target else None
        for detection in detections:
            bbox = detection["bbox_xyxy"]
            center = detection["center_monitor_px"]
            is_chosen = detection.get("detection_index") == chosen_index
            is_after = detection.get("detection_index") == after_index
            color = (255, 0, 0) if is_chosen else (0, 128, 255) if is_after else (0, 255, 0)
            width = 3 if is_chosen or is_after else 1
            x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
            cx, cy = center["x"], center["y"]
            draw.rectangle((x1, y1, x2, y2), outline=color, width=width)
            draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), outline=color, width=2)
            draw.text((max(0, x1), max(0, y1 - 14)), f"{detection['confidence']:.2f}", fill=color, font=font)
        cx = float(crosshair["x"])
        cy = float(crosshair["y"])
        draw.line((cx - 12, cy, cx + 12, cy), fill=(255, 255, 0), width=2)
        draw.line((cx, cy - 12, cx, cy + 12), fill=(255, 255, 0), width=2)
        draw.text((cx + 8, cy + 8), "crosshair", fill=(255, 255, 0), font=font)
        if chosen_target:
            t = chosen_target["center_monitor_px"]
            draw.line((cx, cy, t["x"], t["y"]), fill=(255, 255, 0), width=2)
            if planned_move:
                draw.text((12, 12), f"planned relative move dx={planned_move['dx']:.1f} dy={planned_move['dy']:.1f}", fill=(255, 255, 0), font=font)
        if after_target and after_distance is not None:
            draw.text((12, 28), f"after distance to crosshair={after_distance:.1f}px", fill=(0, 128, 255), font=font)
        image.save(output_path)


def detection_doc(
    *,
    phase: str,
    image_path: Path | None,
    detections: list[dict[str, Any]],
    monitor: MonitorInfo | None,
    crosshair: dict[str, float] | None,
    chosen: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "image_path": str(image_path) if image_path else None,
        "monitor_rect": rect_to_dict(monitor.monitor_rect) if monitor else None,
        "crosshair_center_monitor_px": crosshair,
        "chosen_detection_index": chosen.get("detection_index") if chosen else None,
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
        px_per_mouse_count_x = float(
            args.px_per_mouse_count_x if args.px_per_mouse_count_x is not None else config.get("px_per_mouse_count_x")
        )
        px_per_mouse_count_y = float(
            args.px_per_mouse_count_y if args.px_per_mouse_count_y is not None else config.get("px_per_mouse_count_y")
        )
        max_abs_relative_dx = int(
            args.max_abs_relative_dx if args.max_abs_relative_dx is not None else config.get("max_abs_relative_dx", 3000)
        )
        max_abs_relative_dy = int(
            args.max_abs_relative_dy if args.max_abs_relative_dy is not None else config.get("max_abs_relative_dy", 3000)
        )
        settle_sec = float(args.settle_sec if args.settle_sec is not None else config.get("settle_sec", 0.2))
        capture_after_for_validation = bool(config.get("capture_after_for_validation", True)) and not args.no_after_validation
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
    chosen_target: dict[str, Any] | None = None
    after_chosen: dict[str, Any] | None = None
    after_match_status = "not_attempted"
    crosshair: dict[str, float] | None = None
    error = ""
    relative_aim_executed = False
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
            chosen_target = choose_primary_target(before_detections, crosshair)
    except Exception as exc:
        error = f"before_phase_error:{type(exc).__name__}:{exc}"

    target_delta = delta_to_crosshair(chosen_target, crosshair) if crosshair else None
    planned_move, rounded_move = planned_relative_move(target_delta, px_per_mouse_count_x, px_per_mouse_count_y)
    before_distance = distance(chosen_target["center_monitor_px"], crosshair) if chosen_target and crosshair else None

    relative_aim_gate = build_relative_aim_gate(
        args=args,
        config=config,
        gate=gate,
        target=chosen_target,
        px_per_mouse_count_x=px_per_mouse_count_x,
        px_per_mouse_count_y=px_per_mouse_count_y,
        rounded_move=rounded_move,
        max_abs_relative_dx=max_abs_relative_dx,
        max_abs_relative_dy=max_abs_relative_dy,
    )

    if relative_aim_gate["allowed_to_move"] and rounded_move is not None:
        try:
            sendinput_attempted = True
            send_relative_mouse_move(int(rounded_move["dx"]), int(rounded_move["dy"]))
            relative_aim_executed = True
        except Exception as exc:
            relative_aim_gate["allowed_to_move"] = False
            relative_aim_gate["aim_denied_reason"] = f"sendinput_error:{type(exc).__name__}:{exc}"

    if relative_aim_executed and capture_after_for_validation:
        time.sleep(settle_sec)
        try:
            monitor = gate["monitor"]
            after_capture = capture_monitor(monitor, run_dir / "after_frame.png")
            after_results = run_inference(ctx, after_capture.image_path)
            after_detections = detections_from_results(
                ctx, after_results, after_capture.screenshot_width, after_capture.screenshot_height
            )
            after_chosen, after_match_status = match_after_target(chosen_target, after_detections, crosshair)
        except Exception as exc:
            error = f"after_phase_error:{type(exc).__name__}:{exc}"

    after_distance = distance(after_chosen["center_monitor_px"], crosshair) if after_chosen and crosshair else None
    reduction_px, reduction_ratio = distance_reduction(before_distance, after_distance)
    frames_processed = 1 if before_capture else 0
    after_frame_processed = after_capture is not None
    blocked = bool(gate.get("blocked")) or bool(error)
    blocked_reason = str(gate.get("blocked_reason") or error)

    if before_capture and crosshair:
        draw_review_image(
            before_capture.image_path,
            run_dir / "before_review_image.png",
            before_detections,
            crosshair,
            chosen_target,
            planned_move=planned_move,
        )
    if after_capture and crosshair:
        draw_review_image(
            after_capture.image_path,
            run_dir / "after_review_image.png",
            after_detections,
            crosshair,
            chosen_target,
            planned_move=planned_move,
            after_target=after_chosen,
            after_distance=after_distance,
        )

    monitor = gate.get("monitor")
    summary = {
        "phase": PHASE_NAME,
        "blocked": blocked,
        "blocked_reason": blocked_reason,
        "frames_processed": frames_processed,
        "after_validation_frame_processed": after_frame_processed,
        "detections_count": len(before_detections),
        "target_selection": target_selection,
        "chosen_detection_index": chosen_target.get("detection_index") if chosen_target else None,
        "chosen_conf": chosen_target.get("confidence") if chosen_target else None,
        "chosen_bbox_xyxy": chosen_target.get("bbox_xyxy") if chosen_target else None,
        "crosshair_center_monitor_px": crosshair,
        "chosen_center_monitor_px": chosen_target.get("center_monitor_px") if chosen_target else None,
        "target_delta_to_crosshair_px": target_delta,
        "before_distance_to_crosshair_px": round_float(before_distance),
        "px_per_mouse_count_x": round_float(px_per_mouse_count_x),
        "px_per_mouse_count_y": round_float(px_per_mouse_count_y),
        "planned_relative_move_dxdy": planned_move,
        "rounded_relative_move_dxdy": rounded_move,
        "relative_aim_gate": relative_aim_gate,
        "relative_aim_executed": relative_aim_executed,
        "sendinput_attempted": sendinput_attempted,
        "after_detections_count": len(after_detections) if after_capture else None,
        "after_chosen_center_monitor_px": after_chosen.get("center_monitor_px") if after_chosen else None,
        "after_distance_to_crosshair_px": round_float(after_distance),
        "distance_reduction_px": reduction_px,
        "distance_reduction_ratio": reduction_ratio,
        "after_match_status": after_match_status,
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
        "px_per_mouse_count_x": px_per_mouse_count_x,
        "px_per_mouse_count_y": px_per_mouse_count_y,
        "max_abs_relative_dx": max_abs_relative_dx,
        "max_abs_relative_dy": max_abs_relative_dy,
        "settle_sec": settle_sec,
        "capture_after_for_validation": capture_after_for_validation,
        "model_path": str(args.model),
        "model_loaded": ctx is not None,
        "device": ctx.actual_device if ctx else None,
        "safety_boundary": SAFETY_BOUNDARY,
    }
    event = {
        "phase": PHASE_NAME,
        "target_delta_to_crosshair_px": target_delta,
        "planned_relative_move_dxdy": planned_move,
        "rounded_relative_move_dxdy": rounded_move,
        "relative_aim_gate": relative_aim_gate,
        "relative_aim_executed": relative_aim_executed,
        "sendinput_attempted": sendinput_attempted,
        "no_click_performed": True,
        "one_shot": True,
        "closed_loop": False,
    }
    chosen_doc = {
        "phase": PHASE_NAME,
        "target_selection": target_selection,
        "chosen_target": chosen_target,
        "crosshair_center_monitor_px": crosshair,
        "target_delta_to_crosshair_px": target_delta,
        "before_distance_to_crosshair_px": round_float(before_distance),
        "px_per_mouse_count_x": round_float(px_per_mouse_count_x),
        "px_per_mouse_count_y": round_float(px_per_mouse_count_y),
        "planned_relative_move_dxdy": planned_move,
        "rounded_relative_move_dxdy": rounded_move,
    }

    write_json(
        run_dir / "before_detections.json",
        detection_doc(
            phase=PHASE_NAME,
            image_path=before_capture.image_path if before_capture else None,
            detections=before_detections,
            monitor=monitor,
            crosshair=crosshair,
            chosen=chosen_target,
        ),
    )
    if after_capture:
        write_json(
            run_dir / "after_detections.json",
            detection_doc(
                phase=PHASE_NAME,
                image_path=after_capture.image_path,
                detections=after_detections,
                monitor=monitor,
                crosshair=crosshair,
                chosen=after_chosen,
            ),
        )
    write_json(run_dir / "chosen_target.json", chosen_doc)
    write_json(run_dir / "relative_aim_event.json", event)
    write_json(run_dir / "phase8_summary.json", summary)
    write_json(run_dir / "run_config.json", run_config)
    write_summary_csv(
        run_dir / "summary.csv",
        {
            "phase": PHASE_NAME,
            "timestamp": summary["ended_at"],
            "blocked": blocked,
            "blocked_reason": blocked_reason,
            "frames_processed": frames_processed,
            "detections_count": len(before_detections),
            "after_detections_count": len(after_detections) if after_capture else None,
            "chosen_detection_index": summary["chosen_detection_index"],
            "before_distance_to_crosshair_px": summary["before_distance_to_crosshair_px"],
            "after_distance_to_crosshair_px": summary["after_distance_to_crosshair_px"],
            "distance_reduction_px": summary["distance_reduction_px"],
            "distance_reduction_ratio": summary["distance_reduction_ratio"],
            "rounded_relative_dx": rounded_move.get("dx") if rounded_move else None,
            "rounded_relative_dy": rounded_move.get("dy") if rounded_move else None,
            "relative_aim_executed": relative_aim_executed,
            "aim_denied_reason": relative_aim_gate["aim_denied_reason"],
            "run_dir": str(run_dir),
        },
    )

    print(f"phase={PHASE_NAME}")
    print("mode=execute-relative-aim" if args.execute_relative_aim else "mode=dry-run")
    print(f"blocked={blocked}")
    print(f"frames_processed={frames_processed}")
    print(f"detections_count={len(before_detections)}")
    print(f"chosen_detection_index={summary['chosen_detection_index']}")
    print(f"relative_aim_executed={relative_aim_executed}")
    print(f"sendinput_attempted={sendinput_attempted}")
    print(f"run_dir={run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
