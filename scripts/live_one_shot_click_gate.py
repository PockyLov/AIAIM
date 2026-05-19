from __future__ import annotations

import argparse
import ctypes
import csv
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
for candidate in (SRC_DIR, SCRIPTS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import live_one_shot_fov_aim as phase81
from aiaim_control.fov_aim_model import compute_fov_relative_move

PHASE = "9"
MODE = "one_shot_click_gate"
DEFAULT_OUTPUT_DIR = Path("runs/detect/phase9_one_shot_click_gate")
DEFAULT_MODEL = Path("runs/detect/phase3_yolo11n_baseline/weights/best.pt")
INPUT_MOUSE = 0
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
DEFAULT_CLICK_THRESHOLD_PX = 8.0
DEFAULT_AFTER_MOVE_WAIT_MS = 100
DEFAULT_CLICK_DOWN_UP_DELAY_MS = 50
DEFAULT_HORIZONTAL_FOV_DEG = 103.0
DEFAULT_VERTICAL_FOV_DEG = 70.53
DEFAULT_SCREEN_WIDTH = 1920
DEFAULT_SCREEN_HEIGHT = 1080
DEFAULT_COUNTS_PER_DEGREE = 39.03
DEFAULT_GLOBAL_GAIN = 1.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 9 one-shot click gate. One FOV relative move, optional gated single click, no loop.")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.70)
    parser.add_argument("--max-det", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id")
    parser.add_argument("--overwrite", action="store_true", default=False)
    parser.add_argument("--start-delay-sec", type=float, default=5.0)
    parser.add_argument("--execute-move", action="store_true", default=False)
    parser.add_argument("--allow-click", action="store_true", default=False)
    parser.add_argument("--confirm-local-aimlab-only", action="store_true", default=False)
    parser.add_argument("--click-threshold-px", type=float, default=DEFAULT_CLICK_THRESHOLD_PX)
    parser.add_argument("--after-move-wait-ms", type=int, default=DEFAULT_AFTER_MOVE_WAIT_MS)
    parser.add_argument("--click-down-up-delay-ms", type=int, default=DEFAULT_CLICK_DOWN_UP_DELAY_MS)
    parser.add_argument("--horizontal-fov-deg", type=float, default=DEFAULT_HORIZONTAL_FOV_DEG)
    parser.add_argument("--vertical-fov-deg", type=float, default=DEFAULT_VERTICAL_FOV_DEG)
    parser.add_argument("--screen-width", type=int, default=DEFAULT_SCREEN_WIDTH)
    parser.add_argument("--screen-height", type=int, default=DEFAULT_SCREEN_HEIGHT)
    parser.add_argument("--counts-per-degree", type=float, default=DEFAULT_COUNTS_PER_DEGREE)
    parser.add_argument("--global-gain", type=float, default=DEFAULT_GLOBAL_GAIN)
    parser.add_argument("--max-abs-relative-dx", type=int, default=3000)
    parser.add_argument("--max-abs-relative-dy", type=int, default=3000)
    parser.add_argument("--target-selection", choices=sorted(phase81.SUPPORTED_TARGET_SELECTION), default="nearest_to_crosshair")
    parser.add_argument("--title-keyword", action="append", dest="title_keywords")
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def default_run_id() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")


def round_float(value: float | int | None) -> float | None:
    return phase81.round_float(value)


def args_to_jsonable(args: argparse.Namespace) -> dict[str, Any]:
    return phase81.args_to_jsonable(args)


def prepare_run_dir(output_dir: Path, run_id: str, overwrite: bool) -> Path:
    run_dir = output_dir / run_id
    if run_dir.exists():
        if not overwrite:
            raise FileExistsError(f"run directory already exists; pass --overwrite to replace it: {run_dir}")
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_json(path: Path, data: dict[str, Any]) -> None:
    phase81.write_json(path, data)


def write_summary_csv(path: Path, row: dict[str, Any]) -> None:
    fieldnames = [
        "phase",
        "timestamp",
        "blocked",
        "blocked_reason",
        "detections_count_before",
        "detections_count_after_move",
        "chosen_detection_index_before",
        "before_distance_to_crosshair_px",
        "after_distance_to_crosshair_px",
        "rounded_relative_dx",
        "rounded_relative_dy",
        "relative_aim_executed",
        "click_gate_passed",
        "click_attempted",
        "click_executed",
        "run_dir",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)


MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

def send_left_click(click_down_up_delay_ms: int) -> dict[str, Any]:
    phase81.require_windows()
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    # Ensure all sleep or default PAUSE overheads are completely stripped out
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    return {
        "api": "mouse_event",
        "mode": "left_click_down_up",
        "sent_down": 1,
        "sent_up": 1,
        "click_down_up_delay_ms": int(click_down_up_delay_ms),
    }


def first_failed_check(checks: dict[str, bool]) -> str | None:
    for name, passed in checks.items():
        if not passed:
            return name
    return None


def build_click_gate(
    *,
    execute_move: bool,
    allow_click: bool,
    confirm_local_aimlab_only: bool,
    foreground_before_capture: bool,
    foreground_before_move: bool,
    foreground_before_click: bool,
    after_detection_exists: bool,
    after_distance_to_crosshair_px: float | None,
    click_threshold_px: float,
    already_clicked_once: bool,
) -> dict[str, Any]:
    checks = {
        "aimlab_foreground_before_capture": bool(foreground_before_capture),
        "aimlab_foreground_before_move": bool(foreground_before_move),
        "aimlab_foreground_before_click": bool(foreground_before_click),
        "execute_move": bool(execute_move),
        "allow_click": bool(allow_click),
        "confirm_local_aimlab_only": bool(confirm_local_aimlab_only),
        "after_detection_exists": bool(after_detection_exists),
        "after_distance_within_threshold": after_distance_to_crosshair_px is not None and float(after_distance_to_crosshair_px) <= float(click_threshold_px),
        "not_already_clicked_once": not bool(already_clicked_once),
    }
    reason_map = {
        "aimlab_foreground_before_capture": "aimlab_not_foreground_before_capture",
        "aimlab_foreground_before_move": "aimlab_not_foreground_before_move",
        "aimlab_foreground_before_click": "aimlab_not_foreground_before_click",
        "execute_move": "execute_move_false",
        "allow_click": "allow_click_false",
        "confirm_local_aimlab_only": "confirm_local_aimlab_only_false",
        "after_detection_exists": "no_detection_after_move",
        "after_distance_within_threshold": "after_distance_above_threshold",
        "not_already_clicked_once": "already_clicked_once",
    }
    failed = first_failed_check(checks)
    return {
        "allowed_to_click": failed is None,
        "checks": checks,
        "click_denied_reason": None if failed is None else reason_map[failed],
    }


def build_initial_result(args: argparse.Namespace, run_dir: Path, started_at: str) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "mode": MODE,
        "aimlab_foreground_before_capture": False,
        "aimlab_foreground_before_move": False,
        "aimlab_foreground_before_click": False,
        "resolution_expected": [int(args.screen_width), int(args.screen_height)],
        "screenshot_size": None,
        "horizontal_fov_deg": float(args.horizontal_fov_deg),
        "vertical_fov_deg": float(args.vertical_fov_deg),
        "counts_per_degree": float(args.counts_per_degree),
        "global_gain": float(args.global_gain),
        "detections_count_before": 0,
        "chosen_detection_index_before": None,
        "chosen_detection_before": None,
        "before_distance_to_crosshair_px": None,
        "pixel_delta_xy": None,
        "angle_delta_deg_xy": None,
        "rounded_relative_move_dxdy": None,
        "execute_move": bool(args.execute_move),
        "sendinput_move_attempted": False,
        "relative_aim_executed": False,
        "after_move_wait_ms": int(args.after_move_wait_ms),
        "detections_count_after_move": 0,
        "chosen_detection_index_after_move": None,
        "after_distance_to_crosshair_px": None,
        "click_threshold_px": float(args.click_threshold_px),
        "allow_click": bool(args.allow_click),
        "confirm_local_aimlab_only": bool(args.confirm_local_aimlab_only),
        "click_gate_passed": False,
        "click_attempted": False,
        "click_executed": False,
        "click_down_up_delay_ms": int(args.click_down_up_delay_ms),
        "blocked": False,
        "blocked_reason": None,
        "errors": [],
        "run_dir": str(run_dir),
        "started_at": started_at,
        "ended_at": None,
        "no_loop": True,
        "no_second_correction": True,
        "no_target_lock": True,
        "no_pid": True,
        "no_smooth_move": True,
        "no_memory_read": True,
        "no_aimlab_file_modification": True,
        "anti_cheat_bypass": False,
    }


def set_blocked_reason(result: dict[str, Any], reason: str | None) -> None:
    if reason and result.get("blocked_reason") is None:
        result["blocked_reason"] = reason


def main() -> int:
    args = parse_args()
    started_at = now_iso()
    try:
        run_id = args.run_id or default_run_id()
        run_dir = prepare_run_dir(args.output_dir, run_id, args.overwrite)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    result = build_initial_result(args, run_dir, started_at)
    run_config = {"phase": PHASE, "mode": MODE, "args": args_to_jsonable(args)}
    title_keywords = tuple(args.title_keywords or ("aimlab", "aim lab"))

    if args.start_delay_sec > 0:
        time.sleep(max(0.0, float(args.start_delay_sec)))

    ctx = None
    before_capture = None
    after_capture = None
    post_click_capture = None
    before_detections: list[dict[str, Any]] = []
    after_detections: list[dict[str, Any]] = []
    chosen_before: dict[str, Any] | None = None
    chosen_after: dict[str, Any] | None = None
    crosshair = phase81.crosshair_center_from_screen(args.screen_width, args.screen_height)
    fov_move: dict[str, Any] | None = None
    rounded_move: dict[str, int] | None = None
    click_result: dict[str, Any] | None = None
    sendinput_move_result: dict[str, Any] | None = None
    click_gate: dict[str, Any] | None = None

    gate_before_capture = phase81.get_gate_state(title_keywords)
    result["aimlab_foreground_before_capture"] = not bool(gate_before_capture.get("blocked"))
    monitor = gate_before_capture.get("monitor")

    try:
        if gate_before_capture.get("blocked"):
            result["blocked"] = True
            set_blocked_reason(result, "aimlab_not_foreground_before_capture")
        else:
            ctx = phase81.load_inference_context(args)
            before_capture = phase81.capture_monitor(monitor, run_dir / "before.png")
            result["screenshot_size"] = [before_capture.screenshot_width, before_capture.screenshot_height]
            before_results = phase81.run_inference(ctx, before_capture.image_path)
            before_detections = phase81.detections_from_results(ctx, before_results, before_capture.screenshot_width, before_capture.screenshot_height)
            chosen_before = phase81.choose_primary_target(before_detections, crosshair)
            write_json(run_dir / "before_detection.json", {"detections": before_detections})
            if chosen_before is None:
                set_blocked_reason(result, "no_detection_before")
    except Exception as exc:
        result["blocked"] = True
        result["errors"].append(f"before_phase_error:{type(exc).__name__}:{exc}")
        set_blocked_reason(result, "before_phase_error")

    chosen_center = chosen_before.get("center_monitor_px") if chosen_before else None
    before_distance = phase81.distance(chosen_center, crosshair) if chosen_center else None
    if chosen_center:
        try:
            fov_move = compute_fov_relative_move(
                target_center_x=float(chosen_center["x"]),
                target_center_y=float(chosen_center["y"]),
                crosshair_x=float(crosshair["x"]),
                crosshair_y=float(crosshair["y"]),
                screen_width=int(args.screen_width),
                screen_height=int(args.screen_height),
                horizontal_fov_deg=float(args.horizontal_fov_deg),
                vertical_fov_deg=float(args.vertical_fov_deg),
                counts_per_degree=float(args.counts_per_degree),
                global_gain=float(args.global_gain),
            )
            rounded_move = fov_move["rounded_relative_move_dxdy"]
        except Exception as exc:
            result["blocked"] = True
            result["errors"].append(f"fov_model_error:{type(exc).__name__}:{exc}")
            set_blocked_reason(result, "fov_model_error")

    result.update(
        {
            "detections_count_before": len(before_detections),
            "chosen_detection_index_before": chosen_before.get("detection_index") if chosen_before else None,
            "chosen_detection_before": chosen_before,
            "before_distance_to_crosshair_px": round_float(before_distance),
            "pixel_delta_xy": fov_move.get("target_delta_px") if fov_move else None,
            "angle_delta_deg_xy": {
                "yaw": round_float(fov_move["angle_delta_deg"]["x"]),
                "pitch": round_float(fov_move["angle_delta_deg"]["y"]),
            }
            if fov_move
            else None,
            "rounded_relative_move_dxdy": rounded_move,
        }
    )

    move_gate = phase81.build_move_gate(args=args, gate=gate_before_capture, chosen=chosen_before, rounded_move=rounded_move)
    result["relative_aim_gate"] = move_gate
    gate_before_move = phase81.get_gate_state(title_keywords)
    result["aimlab_foreground_before_move"] = not bool(gate_before_move.get("blocked"))
    if move_gate["allowed_to_move"] and result["aimlab_foreground_before_move"] and rounded_move is not None:
        try:
            result["sendinput_move_attempted"] = True
            sendinput_move_result = phase81.send_relative_mouse_move(int(rounded_move["dx"]), int(rounded_move["dy"]))
            result["relative_aim_executed"] = True
        except Exception as exc:
            result["blocked"] = True
            result["errors"].append(f"sendinput_move_failed:{type(exc).__name__}:{exc}")
            set_blocked_reason(result, "sendinput_move_failed")
    elif args.execute_move and not result["aimlab_foreground_before_move"]:
        set_blocked_reason(result, "aimlab_not_foreground_before_move")
    elif not args.execute_move:
        set_blocked_reason(result, "execute_move_false")
    result["sendinput_move_result"] = sendinput_move_result

    if result["relative_aim_executed"]:
        time.sleep(max(0.0, float(args.after_move_wait_ms) / 1000.0))
        try:
            after_capture = phase81.capture_monitor(monitor, run_dir / "after_move.png")
            after_results = phase81.run_inference(ctx, after_capture.image_path)
            after_detections = phase81.detections_from_results(ctx, after_results, after_capture.screenshot_width, after_capture.screenshot_height)
            chosen_after, _ = phase81.match_after_target(after_detections, crosshair)
            write_json(run_dir / "after_move_detection.json", {"detections": after_detections})
        except Exception as exc:
            result["errors"].append(f"after_move_phase_error:{type(exc).__name__}:{exc}")
            set_blocked_reason(result, "no_detection_after_move")

    after_center = chosen_after.get("center_monitor_px") if chosen_after else None
    after_distance = phase81.distance(after_center, crosshair) if after_center else None
    result.update(
        {
            "detections_count_after_move": len(after_detections),
            "chosen_detection_index_after_move": chosen_after.get("detection_index") if chosen_after else None,
            "chosen_detection_after_move": chosen_after,
            "after_distance_to_crosshair_px": round_float(after_distance),
        }
    )

    gate_before_click = phase81.get_gate_state(title_keywords)
    result["aimlab_foreground_before_click"] = not bool(gate_before_click.get("blocked"))
    click_gate = build_click_gate(
        execute_move=bool(args.execute_move),
        allow_click=bool(args.allow_click),
        confirm_local_aimlab_only=bool(args.confirm_local_aimlab_only),
        foreground_before_capture=bool(result["aimlab_foreground_before_capture"]),
        foreground_before_move=bool(result["aimlab_foreground_before_move"]),
        foreground_before_click=bool(result["aimlab_foreground_before_click"]),
        after_detection_exists=chosen_after is not None,
        after_distance_to_crosshair_px=after_distance,
        click_threshold_px=float(args.click_threshold_px),
        already_clicked_once=bool(result["click_executed"]),
    )
    result["click_gate"] = click_gate
    result["click_gate_passed"] = bool(click_gate["allowed_to_click"])
    if not click_gate["allowed_to_click"]:
        set_blocked_reason(result, click_gate["click_denied_reason"])

    if click_gate["allowed_to_click"]:
        try:
            result["click_attempted"] = True
            click_result = send_left_click(int(args.click_down_up_delay_ms))
            result["click_executed"] = True
        except Exception as exc:
            result["blocked"] = True
            result["errors"].append(f"sendinput_click_failed:{type(exc).__name__}:{exc}")
            set_blocked_reason(result, "sendinput_click_failed")

    result["sendinput_click_result"] = click_result
    if result["click_executed"]:
        try:
            post_click_capture = phase81.capture_monitor(monitor, run_dir / "post_click.png")
        except Exception as exc:
            result["errors"].append(f"post_click_capture_error:{type(exc).__name__}:{exc}")

    if before_capture:
        phase81.draw_review_image(before_capture.image_path, run_dir / "before_review.png", before_detections, crosshair, chosen_before, planned_move=fov_move.get("planned_relative_move_dxdy") if fov_move else None)
    if after_capture:
        phase81.draw_review_image(after_capture.image_path, run_dir / "after_move_review.png", after_detections, crosshair, chosen_before, planned_move=fov_move.get("planned_relative_move_dxdy") if fov_move else None, after_target=chosen_after, after_distance=after_distance)
    if post_click_capture:
        # Post-click screenshot is audit only. No post-click detection, no second correction.
        pass

    if result["blocked_reason"] is None and not result["click_executed"]:
        set_blocked_reason(result, "allow_click_false" if not args.allow_click else None)
    result["ended_at"] = now_iso()
    write_json(run_dir / "phase9_result.json", result)
    write_json(run_dir / "run_config.json", run_config)
    write_summary_csv(
        run_dir / "phase9_summary.csv",
        {
            "phase": PHASE,
            "timestamp": result["ended_at"],
            "blocked": result["blocked"],
            "blocked_reason": result["blocked_reason"],
            "detections_count_before": result["detections_count_before"],
            "detections_count_after_move": result["detections_count_after_move"],
            "chosen_detection_index_before": result["chosen_detection_index_before"],
            "before_distance_to_crosshair_px": result["before_distance_to_crosshair_px"],
            "after_distance_to_crosshair_px": result["after_distance_to_crosshair_px"],
            "rounded_relative_dx": rounded_move.get("dx") if rounded_move else None,
            "rounded_relative_dy": rounded_move.get("dy") if rounded_move else None,
            "relative_aim_executed": result["relative_aim_executed"],
            "click_gate_passed": result["click_gate_passed"],
            "click_attempted": result["click_attempted"],
            "click_executed": result["click_executed"],
            "run_dir": str(run_dir),
        },
    )
    print(f"phase={PHASE}")
    print(f"mode={MODE}")
    print(f"blocked={result['blocked']}")
    print(f"blocked_reason={result['blocked_reason']}")
    print(f"relative_aim_executed={result['relative_aim_executed']}")
    print(f"click_gate_passed={result['click_gate_passed']}")
    print(f"click_executed={result['click_executed']}")
    print(f"run_dir={run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
