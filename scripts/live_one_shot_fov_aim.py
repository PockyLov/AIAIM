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
from aiaim_control.fov_aim_model import compute_fov_relative_move


PHASE = "8.1"
PHASE_NAME = "phase8_1_fov_one_shot_relative_aim"
DEFAULT_MODEL = Path("runs/detect/phase3_yolo11n_baseline/weights/best.pt")
DEFAULT_OUTPUT_DIR = Path("runs/detect/phase8_1_fov_one_shot")
SUPPORTED_TARGET_SELECTION = {"nearest_to_crosshair"}
MOUSEINPUT_MOVE = 0x0001
INPUT_MOUSE = 0
DEFAULT_HORIZONTAL_FOV_DEG = 103.0
DEFAULT_VERTICAL_FOV_DEG = 70.53
DEFAULT_SCREEN_WIDTH = 1920
DEFAULT_SCREEN_HEIGHT = 1080
DEFAULT_COUNTS_PER_DEGREE = 39.03
DEFAULT_GLOBAL_GAIN = 1.0
DEFAULT_CM_PER_360 = 44.614
DEFAULT_CPI = 800
PHASE8_LINEAR_PX_PER_MOUSE_COUNT_X = -0.3605
PHASE8_LINEAR_PX_PER_MOUSE_COUNT_Y = -0.3024
SAFETY_FLAGS = {
    "no_click": True,
    "no_loop": True,
    "no_second_correction": True,
    "no_target_lock": True,
    "no_pid": True,
    "no_smooth_move": True,
    "no_memory_read": True,
    "no_aimlab_file_modification": True,
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
    parser = argparse.ArgumentParser(description="Phase 8.1 FOV-based one-shot relative aim. No click, no loop, no closed-loop correction.")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.70)
    parser.add_argument("--max-det", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--horizontal-fov-deg", type=float, default=DEFAULT_HORIZONTAL_FOV_DEG)
    parser.add_argument("--vertical-fov-deg", type=float, default=DEFAULT_VERTICAL_FOV_DEG)
    parser.add_argument("--screen-width", type=int, default=DEFAULT_SCREEN_WIDTH)
    parser.add_argument("--screen-height", type=int, default=DEFAULT_SCREEN_HEIGHT)
    parser.add_argument("--counts-per-degree", type=float, default=DEFAULT_COUNTS_PER_DEGREE)
    parser.add_argument("--global-gain", type=float, default=DEFAULT_GLOBAL_GAIN)
    parser.add_argument("--execute-move", action="store_true", default=False)
    parser.add_argument("--confirm-local-aimlab-only", action="store_true", default=False)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id")
    parser.add_argument("--overwrite", action="store_true", default=False)
    parser.add_argument("--start-delay-sec", type=float, default=5.0)
    parser.add_argument("--settle-sec", type=float, default=0.2)
    parser.add_argument("--max-abs-relative-dx", type=int, default=3000)
    parser.add_argument("--max-abs-relative-dy", type=int, default=3000)
    parser.add_argument("--target-selection", choices=sorted(SUPPORTED_TARGET_SELECTION), default="nearest_to_crosshair")
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


def args_to_jsonable(args: argparse.Namespace) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in vars(args).items():
        result[key] = str(value) if isinstance(value, Path) else value
    return result


def prepare_run_dir(output_dir: Path, run_id: str, overwrite: bool) -> Path:
    run_dir = output_dir / run_id
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
        "chosen_detection_index",
        "before_distance_to_crosshair_px",
        "after_distance_to_crosshair_px",
        "distance_reduction_px",
        "distance_reduction_ratio",
        "rounded_relative_dx",
        "rounded_relative_dy",
        "relative_aim_executed",
        "sendinput_attempted",
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
    
    engine_path = args.model.with_suffix(".engine")
    onnx_path = args.model.with_suffix(".onnx")
    
    model_to_load = args.model
    if engine_path.exists():
        model_to_load = engine_path
        print(f"Phase 12.5: Found optimized TensorRT engine: {engine_path}")
    elif onnx_path.exists():
        model_to_load = onnx_path
        print(f"Phase 12.5: Found optimized ONNX model: {onnx_path}")
    else:
        print(f"Phase 12.5: Using raw PyTorch model: {args.model}")

    try:
        from ultralytics import YOLO

        model = YOLO(str(model_to_load), task="detect")
    except Exception as exc:
        raise RuntimeError(f"failed to load YOLO model from {model_to_load}: {exc}") from exc
    return InferenceContext(
        model=model,
        model_path=model_to_load,
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
                "bbox_xyxy": {"x1": round_float(x1), "y1": round_float(y1), "x2": round_float(x2), "y2": round_float(y2)},
                "bbox_xywh": {"x": round_float(center_x), "y": round_float(center_y), "w": round_float(bbox_w), "h": round_float(bbox_h)},
                "center_monitor_px": {"x": round_float(center_x), "y": round_float(center_y)},
                "coordinate_space": "monitor_relative",
                "validity": validate_detection(x1, y1, x2, y2, width, height),
            }
        )
    return detections


def distance(a: dict[str, float | int], b: dict[str, float | int]) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def crosshair_center_from_screen(screen_width: int, screen_height: int) -> dict[str, float]:
    return {"x": round_float(float(screen_width) / 2.0), "y": round_float(float(screen_height) / 2.0)}


def choose_primary_target(detections: list[dict[str, Any]], center: dict[str, float]) -> dict[str, Any] | None:
    if not detections:
        return None
    return min(detections, key=lambda item: distance(item["center_monitor_px"], center))


def require_windows() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("Phase 8.1 FOV one-shot aim requires Windows input APIs.")


MOUSEEVENTF_MOVE = 0x0001

def send_relative_mouse_move(dx: int, dy: int) -> dict[str, Any]:
    require_windows()
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, dx, dy, 0, 0)
    return {"sent": 1, "requested_dx": int(dx), "requested_dy": int(dy), "api": "mouse_event", "mode": "relative_move"}



def build_move_gate(
    *,
    args: argparse.Namespace,
    gate: dict[str, Any],
    chosen: dict[str, Any] | None,
    rounded_move: dict[str, int] | None,
) -> dict[str, Any]:
    checks = {
        "cli_execute_move": bool(args.execute_move),
        "cli_confirm_local_aimlab_only": bool(args.confirm_local_aimlab_only),
        "aimlab_foreground_gate_passed": not bool(gate.get("blocked")),
        "before_target_exists": chosen is not None,
        "rounded_move_exists": rounded_move is not None,
        "relative_dx_within_limit": rounded_move is not None and abs(int(rounded_move["dx"])) <= int(args.max_abs_relative_dx),
        "relative_dy_within_limit": rounded_move is not None and abs(int(rounded_move["dy"])) <= int(args.max_abs_relative_dy),
        "no_click": True,
        "no_loop": True,
        "no_closed_loop": True,
    }
    denied = [name for name, passed in checks.items() if not passed]
    return {"allowed_to_move": not denied, "checks": checks, "move_denied_reason": "" if not denied else ";".join(denied)}


def phase8_linear_reference(target_delta: dict[str, float] | None) -> dict[str, Any] | None:
    if target_delta is None:
        return None
    dx = -float(target_delta["dx"]) / PHASE8_LINEAR_PX_PER_MOUSE_COUNT_X
    dy = -float(target_delta["dy"]) / PHASE8_LINEAR_PX_PER_MOUSE_COUNT_Y
    return {
        "px_per_mouse_count_x": PHASE8_LINEAR_PX_PER_MOUSE_COUNT_X,
        "px_per_mouse_count_y": PHASE8_LINEAR_PX_PER_MOUSE_COUNT_Y,
        "planned_relative_move_dxdy": {"dx": round_float(dx), "dy": round_float(dy)},
    }


def match_after_target(after_detections: list[dict[str, Any]], crosshair: dict[str, float] | None) -> tuple[dict[str, Any] | None, str]:
    if not after_detections:
        return None, "no_after_detections"
    if crosshair is None:
        return None, "no_crosshair"
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
                draw.text((12, 12), f"FOV move dx={planned_move['dx']:.1f} dy={planned_move['dy']:.1f}", fill=(255, 255, 0), font=font)
        if after_target and after_distance is not None:
            draw.text((12, 28), f"after distance={after_distance:.1f}px", fill=(0, 128, 255), font=font)
        image.save(output_path)


def main() -> int:
    args = parse_args()
    started_at = now_iso()
    try:
        run_id = args.run_id or default_run_id()
        run_dir = prepare_run_dir(args.output_dir, run_id, args.overwrite)
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
    crosshair = crosshair_center_from_screen(args.screen_width, args.screen_height)
    error = ""
    relative_aim_executed = False
    sendinput_attempted = False
    sendinput_result: dict[str, Any] | None = None

    try:
        if not gate["blocked"]:
            monitor: MonitorInfo = gate["monitor"]
            ctx = load_inference_context(args)
            before_capture = capture_monitor(monitor, run_dir / "before_screenshot.png")
            before_results = run_inference(ctx, before_capture.image_path)
            before_detections = detections_from_results(ctx, before_results, before_capture.screenshot_width, before_capture.screenshot_height)
            chosen_target = choose_primary_target(before_detections, crosshair)
    except Exception as exc:
        error = f"before_phase_error:{type(exc).__name__}:{exc}"

    chosen_center = chosen_target.get("center_monitor_px") if chosen_target else None
    fov_move: dict[str, Any] | None = None
    if chosen_center:
        try:
            fov_move = compute_fov_relative_move(
                target_center_x=float(chosen_center["x"]),
                target_center_y=float(chosen_center["y"]),
                crosshair_x=float(crosshair["x"]),
                crosshair_y=float(crosshair["y"]),
                screen_width=args.screen_width,
                screen_height=args.screen_height,
                horizontal_fov_deg=args.horizontal_fov_deg,
                vertical_fov_deg=args.vertical_fov_deg,
                counts_per_degree=args.counts_per_degree,
                global_gain=args.global_gain,
            )
        except Exception as exc:
            error = f"fov_model_error:{type(exc).__name__}:{exc}"

    target_delta = fov_move.get("target_delta_px") if fov_move else None
    rounded_move = fov_move.get("rounded_relative_move_dxdy") if fov_move else None
    planned_move = fov_move.get("planned_relative_move_dxdy") if fov_move else None
    before_distance = distance(chosen_center, crosshair) if chosen_center else None
    move_gate = build_move_gate(args=args, gate=gate, chosen=chosen_target, rounded_move=rounded_move)

    if move_gate["allowed_to_move"] and rounded_move is not None:
        try:
            sendinput_attempted = True
            sendinput_result = send_relative_mouse_move(int(rounded_move["dx"]), int(rounded_move["dy"]))
            relative_aim_executed = True
        except Exception as exc:
            move_gate["allowed_to_move"] = False
            move_gate["move_denied_reason"] = f"sendinput_error:{type(exc).__name__}:{exc}"
            sendinput_result = {"sent": 0, "error": move_gate["move_denied_reason"]}

    if relative_aim_executed:
        time.sleep(max(0.0, float(args.settle_sec)))
        try:
            monitor = gate["monitor"]
            after_capture = capture_monitor(monitor, run_dir / "after_screenshot.png")
            after_results = run_inference(ctx, after_capture.image_path)
            after_detections = detections_from_results(ctx, after_results, after_capture.screenshot_width, after_capture.screenshot_height)
            after_chosen, after_match_status = match_after_target(after_detections, crosshair)
        except Exception as exc:
            error = f"after_phase_error:{type(exc).__name__}:{exc}"

    after_center = after_chosen.get("center_monitor_px") if after_chosen else None
    after_distance = distance(after_center, crosshair) if after_center else None
    reduction_px, reduction_ratio = distance_reduction(before_distance, after_distance)
    blocked = bool(gate.get("blocked")) or bool(error)
    blocked_reason = str(gate.get("blocked_reason") or error or "") or None
    monitor = gate.get("monitor")

    if before_capture:
        draw_review_image(before_capture.image_path, run_dir / "before_review_image.png", before_detections, crosshair, chosen_target, planned_move=planned_move)
    if after_capture:
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

    result = {
        "phase": PHASE,
        "model": "fov_based_one_shot_relative_aim",
        "blocked": blocked,
        "blocked_reason": blocked_reason,
        "detections_count": len(before_detections),
        "chosen_detection_index": chosen_target.get("detection_index") if chosen_target else None,
        "chosen_conf": chosen_target.get("confidence") if chosen_target else None,
        "selection_strategy": args.target_selection,
        "screen_width": args.screen_width,
        "screen_height": args.screen_height,
        "monitor_rect": rect_to_dict(monitor.monitor_rect) if monitor else None,
        "window_rect": rect_to_dict(gate["window"].rect) if gate.get("window") else None,
        "crosshair_center_monitor_px": crosshair,
        "chosen_center_monitor_px": chosen_center,
        "target_delta_to_crosshair_px": target_delta,
        "before_distance_to_crosshair_px": round_float(before_distance),
        "horizontal_fov_deg": args.horizontal_fov_deg,
        "vertical_fov_deg": args.vertical_fov_deg,
        "focal_px": fov_move.get("focal_px") if fov_move else None,
        "angle_delta_deg": fov_move.get("angle_delta_deg") if fov_move else None,
        "counts_per_degree": args.counts_per_degree,
        "counts_per_degree_source": "theoretical_cm360_cpi",
        "cm_per_360": DEFAULT_CM_PER_360,
        "cpi": DEFAULT_CPI,
        "global_gain": args.global_gain,
        "planned_relative_move_dxdy": planned_move,
        "rounded_relative_move_dxdy": rounded_move,
        "relative_aim_gate": move_gate,
        "relative_aim_executed": relative_aim_executed,
        "sendinput_attempted": sendinput_attempted,
        "sendinput_result": sendinput_result,
        "after_chosen_center_monitor_px": after_center,
        "after_distance_to_crosshair_px": round_float(after_distance),
        "distance_reduction_px": reduction_px,
        "distance_reduction_ratio": reduction_ratio,
        "after_match_status": after_match_status,
        "phase8_linear_reference": phase8_linear_reference(target_delta),
        **SAFETY_FLAGS,
        "run_dir": str(run_dir),
        "started_at": started_at,
        "ended_at": now_iso(),
    }
    run_config = {
        "phase": PHASE,
        "phase_name": PHASE_NAME,
        "args": args_to_jsonable(args),
        "safety_flags": SAFETY_FLAGS,
        "model_path": str(args.model),
        "model_loaded": ctx is not None,
        "device": ctx.actual_device if ctx else None,
    }
    write_json(run_dir / "phase8_1_result.json", result)
    write_json(run_dir / "run_config.json", run_config)
    write_summary_csv(
        run_dir / "phase8_1_summary.csv",
        {
            "phase": PHASE,
            "timestamp": result["ended_at"],
            "blocked": blocked,
            "blocked_reason": blocked_reason,
            "detections_count": len(before_detections),
            "chosen_detection_index": result["chosen_detection_index"],
            "before_distance_to_crosshair_px": result["before_distance_to_crosshair_px"],
            "after_distance_to_crosshair_px": result["after_distance_to_crosshair_px"],
            "distance_reduction_px": result["distance_reduction_px"],
            "distance_reduction_ratio": result["distance_reduction_ratio"],
            "rounded_relative_dx": rounded_move.get("dx") if rounded_move else None,
            "rounded_relative_dy": rounded_move.get("dy") if rounded_move else None,
            "relative_aim_executed": relative_aim_executed,
            "sendinput_attempted": sendinput_attempted,
            "run_dir": str(run_dir),
        },
    )

    print(f"phase={PHASE}")
    print("mode=execute-move" if args.execute_move else "mode=dry-run")
    print(f"blocked={blocked}")
    print(f"detections_count={len(before_detections)}")
    print(f"chosen_detection_index={result['chosen_detection_index']}")
    print(f"rounded_relative_move_dxdy={rounded_move}")
    print(f"relative_aim_executed={relative_aim_executed}")
    print(f"sendinput_attempted={sendinput_attempted}")
    print(f"run_dir={run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
