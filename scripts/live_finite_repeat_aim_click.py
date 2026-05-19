from __future__ import annotations

import argparse
import csv
import json
import colorsys
import statistics
import sys
import time
import queue
import threading
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
for candidate in (SRC_DIR, SCRIPTS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import live_one_shot_click_gate as phase9
import live_one_shot_fov_aim as phase81
from aiaim_control.fov_aim_model import compute_fov_relative_move
from aiaim_control.target_tracker import TargetTracker

PHASE = "10"
MODE = "finite_repeat_aim_click"
DEFAULT_MODEL = Path("runs/detect/phase3_yolo11n_baseline/weights/best.pt")
DEFAULT_OUTPUT_DIR = Path("runs/detect/phase10_finite_repeat_aim_click")
ITERATION_FIELDS = [
    "iteration_index", "loop_iteration_index", "action_iteration_index", "iteration_total_ms", "action_round_ms", "wait_for_target_ms", "before_capture_ms", "before_detect_ms",
    "before_capture_image_path", "before_review_image_path",
    "raw_yolo_boxes_count", "parsed_detections_count", "live_in_memory_detections_count", "file_path_detections_count",
    "live_vs_file_detection_mismatch", "live_detection_input_format_mismatch_suspected",
    "live_detect_conf", "live_detect_iou", "live_detect_max_det", "live_detect_imgsz", "live_detect_device",
    "target_select_ms", "fov_compute_ms", "sendinput_move_ms", "post_move_sleep_ms", "after_capture_ms", "after_detect_ms",
    "capture_object_init_ms", "monitor_lookup_ms", "raw_grab_ms", "buffer_to_numpy_ms", "color_convert_ms",
    "after_validate_ms", "after_validation_ms", "click_ms", "post_click_wait_ms", "logging_ms", "blocked", "blocked_reason",
    "after_validation_mode", "after_validation_method", "after_validation_passed", "after_detection_missing_retry",
    "after_nearest_detection_index", "after_nearest_detection_center_x", "after_nearest_detection_center_y", "after_nearest_detection_distance_px",
    "center_roi_radius_px", "center_roi_click_threshold_px", "center_roi_yellow_pixel_count", "center_roi_largest_contour_area_px",
    "center_roi_yellow_centroid_x", "center_roi_yellow_centroid_y", "center_roi_yellow_centroid_distance_px", "center_roi_fallback_passed",
    "capture_backend", "capture_reuse_enabled", "after_fast_mode", "click_guard_mode", "strict_center_roi_click_threshold_px",
    "fallback_click_evidence_saved", "strict_fallback_guard_retry", "benchmark_under_400ms",
    "no_detection_policy", "no_detection_timeout_count_so_far", "consecutive_no_detection_timeout_count",
    "save_evidence_on_no_detection", "no_detection_evidence_saved", "no_detection_evidence_saved_reason",
    "retry_policy", "retry_scheduled", "retry_reason", "retry_group_id", "retry_count_for_group",
    "max_retries_per_target", "max_total_retry_attempts", "total_retry_attempts_so_far", "same_target_distance_px", "retry_limit_reached",
    "evidence_mode", "save_evidence_on_fallback_click", "evidence_saved", "evidence_saved_reason", "evidence_encode_ms", "evidence_write_ms", "evidence_total_ms", "csv_write_ms", "events_write_ms", "total_io_ms",
    "before_detections_count", "chosen_detection_index", "chosen_center_x", "chosen_center_y", "crosshair_x",
    "crosshair_y", "before_distance_to_crosshair_px", "angle_delta_x_deg", "angle_delta_y_deg",
    "rounded_relative_dx", "rounded_relative_dy", "relative_aim_executed", "sendinput_attempted",
    "after_detections_count", "after_chosen_center_x", "after_chosen_center_y", "after_distance_to_crosshair_px",
    "click_threshold_px", "click_gate_passed", "click_executed", "iteration_status", "stop_reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 10 finite repeat aim + click. Bounded repeat of Phase 9 one-shot step; no runner mode, no infinite loop.")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id")
    parser.add_argument("--overwrite", action="store_true", default=False)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.70)
    parser.add_argument("--max-det", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-iterations", type=int, default=160)
    parser.add_argument("--max-loop-iterations", type=int, default=1000)
    parser.add_argument("--max-duration-sec", type=float, default=65.0)
    parser.add_argument("--click-threshold-px", type=float, default=8.0)
    parser.add_argument("--post-click-wait-sec", type=float, default=0.03)
    parser.add_argument("--next-target-timeout-sec", type=float, default=0.50)
    parser.add_argument("--no-detection-poll-interval-sec", type=float, default=0.05)
    parser.add_argument("--after-move-wait-ms", type=int, default=100)
    parser.add_argument("--click-down-up-delay-ms", type=int, default=50)
    parser.add_argument("--horizontal-fov-deg", type=float, default=103.0)
    parser.add_argument("--vertical-fov-deg", type=float, default=70.53)
    parser.add_argument("--screen-width", type=int, default=1920)
    parser.add_argument("--screen-height", type=int, default=1080)
    parser.add_argument("--counts-per-degree", type=float, default=39.03)
    parser.add_argument("--global-gain", type=float, default=1.0)
    parser.add_argument("--max-abs-relative-dx", type=int, default=3000)
    parser.add_argument("--max-abs-relative-dy", type=int, default=3000)
    parser.add_argument("--execute-move", action="store_true", default=False)
    parser.add_argument("--allow-click", action="store_true", default=False)
    parser.add_argument("--confirm-local-aimlab-only", action="store_true", default=False)
    parser.add_argument("--save-review-images", action="store_true", default=False)
    parser.add_argument("--after-validation-mode", choices=("nearest", "hybrid"), default="hybrid")
    parser.add_argument("--after-fast-mode", choices=("full", "roi_only"), default="roi_only")
    parser.add_argument("--click-guard-mode", choices=("standard", "strict"), default="strict")
    parser.add_argument("--strict-center-roi-click-threshold-px", type=float, default=6.0)
    parser.add_argument("--fallback-click-allowed", action="store_true", default=True)
    parser.add_argument("--no-fallback-click-allowed", dest="fallback_click_allowed", action="store_false")
    parser.add_argument("--save-evidence-on-fallback-click", action="store_true", default=False)
    parser.add_argument("--no-save-evidence-on-fallback-click", dest="save_evidence_on_fallback_click", action="store_false")
    parser.add_argument("--capture-backend", choices=("auto", "mss", "dxcam"), default="auto")
    parser.add_argument("--capture-benchmark-only", action="store_true", default=False)
    parser.add_argument("--capture-benchmark-frames", type=int, default=30)
    parser.add_argument("--capture-benchmark-include-encode", action="store_true", default=False)
    parser.add_argument("--no-warmup-inference", dest="warmup_inference", action="store_false", default=True)
    parser.add_argument("--center-roi-radius-px", type=int, default=20)
    parser.add_argument("--center-roi-click-threshold-px", type=float, default=10.0)
    parser.add_argument("--center-roi-min-yellow-pixels", type=int, default=8)
    parser.add_argument("--center-roi-min-contour-area-px", type=int, default=4)
    parser.add_argument("--evidence-mode", choices=("full", "failures", "minimal"), default="failures")
    parser.add_argument("--no-detection-policy", choices=("stop", "continue"), default="continue")
    parser.add_argument("--max-no-detection-timeouts", type=int, default=20)
    parser.add_argument("--max-consecutive-no-detection-timeouts", type=int, default=5)
    parser.add_argument("--save-evidence-on-no-detection", action="store_true", default=True)
    parser.add_argument("--no-save-evidence-on-no-detection", dest="save_evidence_on_no_detection", action="store_false")
    parser.add_argument("--max-no-detection-evidence", type=int, default=10)
    parser.add_argument("--debug-detection-parity", action="store_true", default=False)
    parser.add_argument("--debug-detection-parity-on-no-detection", action="store_true", default=True)
    parser.add_argument("--stop-file", type=Path, default=None)
    parser.add_argument("--retry-policy", choices=("stop", "bounded"), default="bounded")
    parser.add_argument("--max-retries-per-target", type=int, default=1)
    parser.add_argument("--max-total-retry-attempts", "--max-retries", dest="max_total_retry_attempts", type=int, default=20)
    parser.add_argument("--retry-distance-px", type=float, default=30.0)
    parser.add_argument("--retry-same-target-distance-px", type=float, default=45.0)
    parser.add_argument("--no-retry-after-center-roi-fallback", dest="allow_retry_after_center_roi_fallback", action="store_false", default=True)
    parser.add_argument("--title-keyword", action="append", dest="title_keywords")
    parser.add_argument("--latency-compensation-sec", type=float, default=0.05)
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def default_run_id() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")


def ms_since(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 3)


def round_float(value: float | int | None) -> float | None:
    return phase81.round_float(value)


evidence_queue = queue.Queue(maxsize=100)
evidence_worker_running = True

def evidence_worker_loop():
    base_dir = Path("data/feedback/phase12_failures")
    base_dir.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    while True:
        try:
            task = evidence_queue.get(timeout=0.1)
            if task is None:
                break
            timestamp, failure_type, frame, metadata = task
            image_path = base_dir / f"{timestamp}_{failure_type}.jpg"
            json_path = base_dir / f"{timestamp}_{failure_type}.json"
            Image.fromarray(frame).save(image_path, quality=85)
            write_json(json_path, metadata)
            evidence_queue.task_done()
        except queue.Empty:
            if not evidence_worker_running:
                break
        except Exception as exc:
            print(f"Evidence Worker Error: {exc}", file=sys.stderr)


def enqueue_failure_evidence(failure_type: str, capture: Any | None, row: dict[str, Any]) -> None:
    if capture is None:
        return
    frame = capture.yolo_frame if getattr(capture, "yolo_frame", None) is not None else getattr(capture, "frame", None)
    if frame is None:
        return
    if hasattr(frame, "copy"):
        frame = frame.copy()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    metadata = {
        "failure_type": failure_type,
        "iteration_index": row.get("iteration_index"),
        "chosen_center_x": row.get("chosen_center_x"),
        "chosen_center_y": row.get("chosen_center_y"),
        "crosshair_x": row.get("crosshair_x"),
        "crosshair_y": row.get("crosshair_y"),
        "after_chosen_center_x": row.get("after_chosen_center_x"),
        "after_chosen_center_y": row.get("after_chosen_center_y"),
        "after_distance_to_crosshair_px": row.get("after_distance_to_crosshair_px"),
        "rounded_relative_dx": row.get("rounded_relative_dx"),
        "rounded_relative_dy": row.get("rounded_relative_dy"),
        "blocked_reason": row.get("blocked_reason"),
    }
    try:
        evidence_queue.put_nowait((timestamp, failure_type, frame, metadata))
    except queue.Full:
        pass


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def append_event(path: Path, event_type: str, **payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": now_iso(), "event_type": event_type, **payload}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_iteration_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    validate_unique_csv_headers(ITERATION_FIELDS)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ITERATION_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in ITERATION_FIELDS})


def validate_unique_csv_headers(headers: list[str]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for header in headers:
        if header in seen and header not in duplicates:
            duplicates.append(header)
        seen.add(header)
    if duplicates:
        raise ValueError(f"duplicate CSV header(s): {', '.join(duplicates)}")


def prepare_run_dir(output_dir: Path, run_id: str, overwrite: bool) -> Path:
    return phase9.prepare_run_dir(output_dir, run_id, overwrite)


def args_to_jsonable(args: argparse.Namespace) -> dict[str, Any]:
    return phase9.args_to_jsonable(args)


def startup_gate(args: argparse.Namespace) -> tuple[bool, str | None]:
    if getattr(args, "capture_benchmark_only", False):
        if not args.confirm_local_aimlab_only:
            return False, "confirm_local_aimlab_only_false"
    else:
        if not args.execute_move:
            return False, "execute_move_false"
        if not args.allow_click:
            return False, "allow_click_false"
        if not args.confirm_local_aimlab_only:
            return False, "confirm_local_aimlab_only_false"
    if args.max_iterations <= 0:
        return False, "max_iterations_invalid"
    if getattr(args, "max_loop_iterations", 1) <= 0:
        return False, "max_loop_iterations_invalid"
    if args.max_duration_sec <= 0:
        return False, "max_duration_sec_invalid"
    if args.next_target_timeout_sec < 0 or args.no_detection_poll_interval_sec <= 0 or args.post_click_wait_sec < 0:
        return False, "timing_parameter_invalid"
    if args.center_roi_radius_px <= 0 or args.center_roi_click_threshold_px < 0 or args.center_roi_min_yellow_pixels < 0 or args.center_roi_min_contour_area_px < 0:
        return False, "center_roi_parameter_invalid"
    if args.max_retries_per_target < 0 or args.max_total_retry_attempts < 0 or args.retry_distance_px < 0 or args.retry_same_target_distance_px < 0:
        return False, "retry_parameter_invalid"
    if getattr(args, "strict_center_roi_click_threshold_px", 0) < 0 or getattr(args, "capture_benchmark_frames", 1) <= 0:
        return False, "phase103_parameter_invalid"
    if getattr(args, "max_no_detection_timeouts", 0) < 0 or getattr(args, "max_consecutive_no_detection_timeouts", 0) < 0 or getattr(args, "max_no_detection_evidence", 0) < 0:
        return False, "no_detection_policy_parameter_invalid"
    return True, None


def stop_file_requested(args: argparse.Namespace) -> bool:
    stop_file = getattr(args, "stop_file", None)
    return bool(stop_file and Path(stop_file).exists())


def build_summary(
    args: argparse.Namespace,
    run_dir: Path,
    rows: list[dict[str, Any]],
    *,
    stop_reason: str,
    blocked: bool,
    keyboard_interrupt: bool,
    timing: dict[str, Any],
) -> dict[str, Any]:
    durations = [float(row["iteration_total_ms"]) for row in rows if row.get("iteration_total_ms") is not None]
    before_detects = [float(row["before_detect_ms"]) for row in rows if row.get("before_detect_ms") is not None]
    after_detects = [float(row["after_detect_ms"]) for row in rows if row.get("after_detect_ms") is not None]
    after_validations = [float(row["after_validation_ms"]) for row in rows if row.get("after_validation_ms") is not None]
    action_rounds = [float(row["action_round_ms"]) for row in rows if row.get("action_round_ms") is not None]
    total_ios = [float(row["total_io_ms"]) for row in rows if row.get("total_io_ms") is not None]
    before_captures = [float(row["before_capture_ms"]) for row in rows if row.get("before_capture_ms") is not None]
    after_captures = [float(row["after_capture_ms"]) for row in rows if row.get("after_capture_ms") is not None]
    retry_scheduled_rows = [row for row in rows if row.get("retry_scheduled")]
    action_iterations_attempted = sum(1 for row in rows if row.get("before_detections_count", 0))
    clicks_executed = sum(1 for row in rows if row.get("click_executed"))
    no_detection_timeout_count = sum(1 for row in rows if row.get("stop_reason") == "no_detection_timeout")
    foreground_blocked_count = sum(1 for row in rows if row.get("stop_reason") == "foreground_blocked")
    retry_limit_reached_count = sum(1 for row in rows if row.get("retry_limit_reached"))
    max_duration_reached = stop_reason == "max_duration_reached"
    active_loop_duration_sec = timing.get("active_loop_duration_sec")
    try:
        active_loop_duration = float(active_loop_duration_sec) if active_loop_duration_sec is not None else None
    except (TypeError, ValueError):
        active_loop_duration = None
    task_end_likely = (
        stop_reason == "max_consecutive_no_detection_timeouts_reached"
        and clicks_executed > 0
        and action_iterations_attempted > 0
        and no_detection_timeout_count >= int(args.max_consecutive_no_detection_timeouts)
        and foreground_blocked_count == 0
        and not max_duration_reached
        and retry_limit_reached_count == 0
    )
    terminal_classification = "likely_task_ended_or_targets_exhausted" if task_end_likely else (stop_reason or "unknown")
    terminal_classification_reason = (
        "completed clicks/actions followed by consecutive no-detection timeouts without safety block"
        if task_end_likely
        else f"terminal stop reason: {stop_reason or 'unknown'}"
    )
    return {
        "phase": 10,
        "mode": MODE,
        "blocked": bool(blocked),
        "stop_reason": stop_reason,
        "iterations_requested": int(args.max_iterations),
        "max_loop_iterations": int(getattr(args, "max_loop_iterations", 1)),
        "loop_iterations_attempted": len(rows),
        "action_iterations_attempted": action_iterations_attempted,
        "clicks_executed": clicks_executed,
        "moves_executed": sum(1 for row in rows if row.get("relative_aim_executed")),
        "no_detection_policy": getattr(args, "no_detection_policy", "continue"),
        "max_no_detection_timeouts": getattr(args, "max_no_detection_timeouts", 0),
        "max_consecutive_no_detection_timeouts": getattr(args, "max_consecutive_no_detection_timeouts", 0),
        "save_evidence_on_no_detection": bool(getattr(args, "save_evidence_on_no_detection", False)),
        "max_no_detection_evidence": int(getattr(args, "max_no_detection_evidence", 0)),
        "debug_detection_parity": bool(getattr(args, "debug_detection_parity", False)),
        "debug_detection_parity_on_no_detection": bool(getattr(args, "debug_detection_parity_on_no_detection", False)),
        "no_detection_timeout_count": no_detection_timeout_count,
        "no_detection_evidence_saved_count": sum(1 for row in rows if row.get("no_detection_evidence_saved")),
        "no_detection_evidence_skipped_count": sum(1 for row in rows if row.get("stop_reason") == "no_detection_timeout" and not row.get("no_detection_evidence_saved")),
        "consecutive_no_detection_timeout_count": next((row.get("consecutive_no_detection_timeout_count") for row in reversed(rows) if row.get("stop_reason") == "no_detection_timeout"), 0),
        "aim_miss_count": sum(1 for row in rows if row.get("stop_reason") == "after_distance_exceeded_threshold"),
        "after_detection_missing_count": sum(1 for row in rows if row.get("stop_reason") == "after_detection_missing"),
        "after_detection_missing_retry_count": sum(1 for row in rows if row.get("retry_reason") == "after_detection_missing_retry"),
        "after_detection_missing_stop_count": sum(1 for row in rows if row.get("after_validation_method") == "no_after_detection" and row.get("stop_reason") == "after_detection_missing"),
        "max_iterations": int(getattr(args, "max_iterations", 0)),
        "max_duration_sec": float(getattr(args, "max_duration_sec", 65.0)),
        "foreground_blocked_count": foreground_blocked_count,
        "keyboard_interrupt": bool(keyboard_interrupt),
        "max_duration_reached": max_duration_reached,
        "after_validation_mode": args.after_validation_mode,
        "benchmark_target_iteration_ms": 400,
        "benchmark_passed_under_400ms": bool(durations) and statistics.mean(durations) < 400.0,
        "requested_capture_backend": args.capture_backend,
        "capture_backend": next((row.get("capture_backend") for row in rows if row.get("capture_backend")), args.capture_backend),
        "selected_capture_backend": next((row.get("capture_backend") for row in rows if row.get("capture_backend")), None),
        "capture_reuse_enabled": any(row.get("capture_reuse_enabled") for row in rows),
        "after_fast_mode": args.after_fast_mode,
        "click_guard_mode": args.click_guard_mode,
        "fallback_click_count": sum(1 for row in rows if row.get("click_executed") and row.get("after_validation_method") == "center_roi_yellow_fallback"),
        "save_evidence_on_fallback_click": bool(getattr(args, "save_evidence_on_fallback_click", False)),
        "fallback_click_evidence_saved_count": sum(1 for row in rows if row.get("fallback_click_evidence_saved")),
        "strict_fallback_guard_retry_count": sum(1 for row in rows if row.get("retry_reason") == "strict_fallback_click_guard_retry"),
        "suspicious_click_guard_retry_count": sum(1 for row in rows if row.get("strict_fallback_guard_retry")),
        "yolo_center_validation_pass_count": sum(1 for row in rows if row.get("after_validation_method") == "yolo_center_detection"),
        "center_roi_fallback_pass_count": sum(1 for row in rows if row.get("after_validation_method") == "center_roi_yellow_fallback"),
        "after_validation_failed_count": sum(1 for row in rows if row.get("after_validation_passed") is False),
        "after_validation_nearest_yolo_far_count": sum(1 for row in rows if row.get("after_validation_method") == "nearest_yolo_far"),
        "after_validation_no_detection_count": sum(1 for row in rows if row.get("after_validation_method") == "no_after_detection"),
        "retry_policy": args.retry_policy,
        "max_retries_per_target": args.max_retries_per_target,
        "max_total_retry_attempts": args.max_total_retry_attempts,
        "total_retry_attempts": len(retry_scheduled_rows),
        "retry_groups_started": len({row.get("retry_group_id") for row in retry_scheduled_rows if row.get("retry_group_id") is not None}),
        "retry_limit_reached_count": retry_limit_reached_count,
        "center_roi_near_miss_retry_count": sum(1 for row in retry_scheduled_rows if str(row.get("retry_reason", "")).startswith("center_roi")),
        "nearest_yolo_retry_count": sum(1 for row in retry_scheduled_rows if str(row.get("retry_reason", "")).startswith("after_nearest")),
        "same_target_retry_count": sum(1 for row in retry_scheduled_rows if row.get("same_target_distance_px") is not None),
        "successful_clicks_after_retry": sum(1 for row in rows if row.get("click_executed") and row.get("retry_count_for_group", 0)),
        "evidence_mode": getattr(args, "evidence_mode", "failures"),
        "save_evidence_on_fallback_click": bool(getattr(args, "save_evidence_on_fallback_click", False)),
        "evidence_saved_reason": None,
        "successful_iterations_without_image_evidence": sum(1 for row in rows if row.get("click_executed") and not row.get("evidence_saved")),
        "failure_or_retry_iterations_with_evidence": sum(1 for row in rows if row.get("evidence_saved") and (row.get("retry_scheduled") or row.get("blocked") or row.get("stop_reason") or not row.get("click_executed"))),
        "started_at": timing.get("process_started_at"),
        "ended_at": timing.get("process_ended_at"),
        "duration_sec": timing.get("wall_duration_sec"),
        "process_started_at": timing.get("process_started_at"),
        "process_ended_at": timing.get("process_ended_at"),
        "wall_duration_sec": timing.get("wall_duration_sec"),
        "startup_started_at": timing.get("startup_started_at"),
        "startup_ended_at": timing.get("startup_ended_at"),
        "startup_duration_sec": timing.get("startup_duration_sec"),
        "model_load_ms": timing.get("model_load_ms"),
        "warmup_enabled": timing.get("warmup_enabled"),
        "warmup_ms": timing.get("warmup_ms"),
        "warmup_capture_ms": timing.get("warmup_capture_ms"),
        "warmup_detect_ms": timing.get("warmup_detect_ms"),
        "warmup_detections_count": timing.get("warmup_detections_count"),
        "warmup_error": timing.get("warmup_error"),
        "first_active_before_detect_ms": next((row.get("before_detect_ms") for row in rows if row.get("before_detect_ms") is not None), None),
        "first_active_iteration_total_ms": next((row.get("iteration_total_ms") for row in rows if row.get("iteration_total_ms") is not None), None),
        "csv_headers_unique": True,
        "loop_started_at": timing.get("loop_started_at"),
        "loop_ended_at": timing.get("loop_ended_at"),
        "active_loop_duration_sec": active_loop_duration_sec,
        "task_end_likely": task_end_likely,
        "terminal_classification": terminal_classification,
        "terminal_classification_reason": terminal_classification_reason,
        "clicks_per_active_second": round_float(clicks_executed / active_loop_duration) if active_loop_duration and active_loop_duration > 0 else None,
        "actions_per_active_second": round_float(action_iterations_attempted / active_loop_duration) if active_loop_duration and active_loop_duration > 0 else None,
        "click_rate_over_actions": round_float(clicks_executed / action_iterations_attempted) if action_iterations_attempted else None,
        "retry_rate_over_actions": round_float(len(retry_scheduled_rows) / action_iterations_attempted) if action_iterations_attempted else None,
        "average_iteration_total_ms": round_float(statistics.mean(durations)) if durations else None,
        "median_iteration_total_ms": round_float(statistics.median(durations)) if durations else None,
        "min_iteration_total_ms": round_float(min(durations)) if durations else None,
        "max_iteration_total_ms": round_float(max(durations)) if durations else None,
        "p90_iteration_total_ms": p90(durations),
        "average_action_round_ms": round_float(statistics.mean(action_rounds)) if action_rounds else None,
        "average_total_io_ms": round_float(statistics.mean(total_ios)) if total_ios else None,
        "average_evidence_total_ms": round_float(statistics.mean([float(row["evidence_total_ms"]) for row in rows if row.get("evidence_total_ms") is not None])) if any(row.get("evidence_total_ms") is not None for row in rows) else None,
        "average_evidence_encode_ms": round_float(statistics.mean([float(row["evidence_encode_ms"]) for row in rows if row.get("evidence_encode_ms") is not None])) if any(row.get("evidence_encode_ms") is not None for row in rows) else None,
        "average_before_capture_ms": round_float(statistics.mean(before_captures)) if before_captures else None,
        "average_before_detect_ms": round_float(statistics.mean(before_detects)) if before_detects else None,
        "average_after_capture_ms": round_float(statistics.mean(after_captures)) if after_captures else None,
        "average_after_detect_ms": round_float(statistics.mean(after_detects)) if after_detects else None,
        "average_after_validation_ms": round_float(statistics.mean(after_validations)) if after_validations else None,
        "performance": {
            "average_iteration_total_ms": round_float(statistics.mean(durations)) if durations else None,
            "median_iteration_total_ms": round_float(statistics.median(durations)) if durations else None,
            "min_iteration_total_ms": round_float(min(durations)) if durations else None,
            "max_iteration_total_ms": round_float(max(durations)) if durations else None,
            "p90_iteration_total_ms": p90(durations),
            "average_action_round_ms": round_float(statistics.mean(action_rounds)) if action_rounds else None,
            "average_total_io_ms": round_float(statistics.mean(total_ios)) if total_ios else None,
            "average_evidence_total_ms": round_float(statistics.mean([float(row["evidence_total_ms"]) for row in rows if row.get("evidence_total_ms") is not None])) if any(row.get("evidence_total_ms") is not None for row in rows) else None,
            "average_evidence_encode_ms": round_float(statistics.mean([float(row["evidence_encode_ms"]) for row in rows if row.get("evidence_encode_ms") is not None])) if any(row.get("evidence_encode_ms") is not None for row in rows) else None,
            "average_before_capture_ms": round_float(statistics.mean(before_captures)) if before_captures else None,
            "average_before_detect_ms": round_float(statistics.mean(before_detects)) if before_detects else None,
            "average_after_capture_ms": round_float(statistics.mean(after_captures)) if after_captures else None,
            "average_after_detect_ms": round_float(statistics.mean(after_detects)) if after_detects else None,
            "average_after_validation_ms": round_float(statistics.mean(after_validations)) if after_validations else None,
        },
        "run_dir": str(run_dir),
    }


def summarize_numbers(values: list[float]) -> dict[str, float | None]:
    return {
        "average": round_float(statistics.mean(values)) if values else None,
        "median": round_float(statistics.median(values)) if values else None,
        "min": round_float(min(values)) if values else None,
        "max": round_float(max(values)) if values else None,
        "p90": p90(values),
    }


def dxcam_status() -> dict[str, Any]:
    try:
        import dxcam  # noqa: F401
    except Exception as exc:
        return {"dxcam_available": False, "dxcam_import_error": f"{type(exc).__name__}: {exc}"}
    return {"dxcam_available": True, "dxcam_import_error": None}


@dataclass
class CapturedFrame:
    image_path: Path
    frame: Any
    screenshot_width: int
    screenshot_height: int
    capture_elapsed_ms: float
    yolo_frame: Any = None
    encoded: bool = False


class CaptureManager:
    def __init__(self, backend: str) -> None:
        self.backend = backend
        self.capture_reuse_enabled = backend in {"mss_persistent", "dxcam"}
        self.sct = None
        self.dxcam_camera = None
        self.init_ms = 0.0
        self.dxcam_available = None
        self.dxcam_import_error = None
        if backend == "mss_persistent":
            started = time.perf_counter()
            import mss
            self.sct = mss.mss()
            self.init_ms = ms_since(started)
        elif backend == "dxcam":
            started = time.perf_counter()
            try:
                import dxcam
                self.dxcam_camera = dxcam.create(output_color="RGB")
                self.dxcam_available = True
            except Exception as exc:
                self.dxcam_available = False
                self.dxcam_import_error = f"{type(exc).__name__}: {exc}"
                raise RuntimeError(f"dxcam backend requested but unavailable: {self.dxcam_import_error}") from exc
            self.init_ms = ms_since(started)

    def close(self) -> None:
        try:
            if self.sct is not None:
                self.sct.close()
        finally:
            self.sct = None
            self.dxcam_camera = None

    def capture(self, monitor: Any, image_path: Path) -> tuple[CapturedFrame, dict[str, Any]]:
        rect = monitor.monitor_rect
        timings = {
            "capture_backend": self.backend,
            "capture_reuse_enabled": self.capture_reuse_enabled,
            "capture_object_init_ms": 0.0,
            "monitor_lookup_ms": 0.0,
            "raw_grab_ms": 0.0,
            "buffer_to_numpy_ms": 0.0,
            "color_convert_ms": 0.0,
            "evidence_encode_ms": 0.0,
        }
        monitor_start = time.perf_counter()
        region = {"left": rect.left, "top": rect.top, "width": rect.width, "height": rect.height}
        timings["monitor_lookup_ms"] = ms_since(monitor_start)
        if self.backend in {"mss_current", "mss_persistent"}:
            import mss
            import numpy as np
            init_start = time.perf_counter()
            sct = self.sct
            owns_sct = False
            if sct is None:
                sct = mss.mss()
                owns_sct = True
            timings["capture_object_init_ms"] = ms_since(init_start)
            raw_start = time.perf_counter()
            image = sct.grab(region)
            timings["raw_grab_ms"] = ms_since(raw_start)
            buffer_start = time.perf_counter()
            bgra = np.asarray(image)
            timings["buffer_to_numpy_ms"] = ms_since(buffer_start)
            color_start = time.perf_counter()
            bgr = bgra[:, :, :3].copy()
            rgb = bgr[:, :, ::-1].copy()
            timings["color_convert_ms"] = ms_since(color_start)
            if owns_sct:
                sct.close()
            elapsed = capture_elapsed_from_timings(timings)
            return CapturedFrame(image_path, rgb, region["width"], region["height"], round(elapsed, 3), yolo_frame=bgr), timings
        if self.backend == "dxcam":
            if self.dxcam_camera is None:
                raise RuntimeError("dxcam backend is not initialized")
            raw_start = time.perf_counter()
            frame = self.dxcam_camera.grab(region=(rect.left, rect.top, rect.left + rect.width, rect.top + rect.height))
            timings["raw_grab_ms"] = ms_since(raw_start)
            if frame is None:
                raise RuntimeError("dxcam returned no frame")
            try:
                yolo_frame = frame[:, :, ::-1].copy()
            except Exception:
                yolo_frame = frame
            elapsed = capture_elapsed_from_timings(timings)
            return CapturedFrame(image_path, frame, rect.width, rect.height, round(elapsed, 3), yolo_frame=yolo_frame), timings
        raise ValueError(f"unsupported capture backend: {self.backend}")


def capture_elapsed_from_timings(timings: dict[str, Any]) -> float:
    return sum(float(timings.get(key) or 0.0) for key in (
        "capture_object_init_ms", "monitor_lookup_ms", "raw_grab_ms", "buffer_to_numpy_ms", "color_convert_ms"
    ))


def encode_capture_image(capture: CapturedFrame) -> float:
    if capture.encoded and capture.image_path.exists():
        return 0.0
    capture.image_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    from PIL import Image
    Image.fromarray(capture.frame).save(capture.image_path)
    capture.encoded = True
    return ms_since(started)


def resolve_runtime_capture_backend(requested: str) -> tuple[str, dict[str, Any]]:
    status = dxcam_status()
    if requested == "dxcam":
        if not status["dxcam_available"]:
            raise RuntimeError(f"dxcam requested but unavailable: {status['dxcam_import_error']}")
        return "dxcam", status
    if requested == "auto" and status["dxcam_available"]:
        return "dxcam", status
    return "mss_persistent", status


def benchmark_backend_names(requested: str) -> list[str]:
    if requested == "dxcam":
        return ["dxcam"]
    if requested == "mss":
        return ["mss_current", "mss_persistent"]
    return ["mss_current", "mss_persistent", "dxcam"]

def should_stop_for_active_duration(loop_start_perf: float, max_duration_sec: float, now_perf: float | None = None) -> bool:
    current = time.perf_counter() if now_perf is None else now_perf
    return (current - loop_start_perf) >= float(max_duration_sec)


def nearest_detection_to_crosshair(detections: list[dict[str, Any]], crosshair: dict[str, float]) -> tuple[dict[str, Any] | None, float | None]:
    if not detections:
        return None, None
    nearest = min(detections, key=lambda item: phase81.distance(item["center_monitor_px"], crosshair))
    return nearest, phase81.distance(nearest["center_monitor_px"], crosshair)


def is_yellow_rgb(r: int, g: int, b: int) -> bool:
    hue, saturation, value = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    hue_deg = hue * 360.0
    return 35.0 <= hue_deg <= 68.0 and saturation >= 0.35 and value >= 0.35 and r >= 100 and g >= 80 and b <= 170


def largest_component_area(points: set[tuple[int, int]]) -> int:
    remaining = set(points)
    largest = 0
    while remaining:
        stack = [remaining.pop()]
        area = 0
        while stack:
            x, y = stack.pop()
            area += 1
            for nx in (x - 1, x, x + 1):
                for ny in (y - 1, y, y + 1):
                    if (nx, ny) in remaining:
                        remaining.remove((nx, ny))
                        stack.append((nx, ny))
        largest = max(largest, area)
    return largest


def analyze_center_roi_yellow(image_source: Any, crosshair: dict[str, float], args: argparse.Namespace) -> dict[str, Any]:
    from PIL import Image

    radius = int(args.center_roi_radius_px)
    cx = int(round(float(crosshair["x"])))
    cy = int(round(float(crosshair["y"])))
    if isinstance(image_source, (str, Path)):
        image_context = Image.open(image_source).convert("RGB")
    else:
        image_context = Image.fromarray(image_source).convert("RGB")
    with image_context as image:
        width, height = image.size
        x1 = max(0, cx - radius)
        y1 = max(0, cy - radius)
        x2 = min(width - 1, cx + radius)
        y2 = min(height - 1, cy + radius)
        yellow_points: set[tuple[int, int]] = set()
        sum_x = 0
        sum_y = 0
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                r, g, b = image.getpixel((x, y))
                if is_yellow_rgb(r, g, b):
                    yellow_points.add((x, y))
                    sum_x += x
                    sum_y += y
    count = len(yellow_points)
    largest = largest_component_area(yellow_points) if yellow_points else 0
    centroid_x = (sum_x / count) if count else None
    centroid_y = (sum_y / count) if count else None
    centroid_distance = phase81.distance({"x": centroid_x, "y": centroid_y}, crosshair) if centroid_x is not None and centroid_y is not None else None
    passed = (
        count >= int(args.center_roi_min_yellow_pixels)
        and largest >= int(args.center_roi_min_contour_area_px)
        and centroid_distance is not None
        and centroid_distance <= float(args.center_roi_click_threshold_px)
    )
    return {
        "center_roi_radius_px": radius,
        "center_roi_click_threshold_px": float(args.center_roi_click_threshold_px),
        "center_roi_yellow_pixel_count": count,
        "center_roi_largest_contour_area_px": largest,
        "center_roi_yellow_centroid_x": round_float(centroid_x),
        "center_roi_yellow_centroid_y": round_float(centroid_y),
        "center_roi_yellow_centroid_distance_px": round_float(centroid_distance),
        "center_roi_fallback_passed": bool(passed),
    }


def validate_after_move(
    *,
    after_detections: list[dict[str, Any]],
    crosshair: dict[str, float],
    after_image_path: Path | None = None,
    after_frame: Any | None = None,
    args: argparse.Namespace,
) -> dict[str, Any]:
    nearest, nearest_distance = nearest_detection_to_crosshair(after_detections, crosshair)
    base = {
        "after_validation_mode": args.after_validation_mode,
        "after_validation_method": None,
        "after_validation_passed": False,
        "after_nearest_detection_index": nearest.get("detection_index") if nearest else None,
        "after_nearest_detection_center_x": nearest.get("center_monitor_px", {}).get("x") if nearest else None,
        "after_nearest_detection_center_y": nearest.get("center_monitor_px", {}).get("y") if nearest else None,
        "after_nearest_detection_distance_px": round_float(nearest_distance),
        "after_chosen": nearest,
        "after_distance_to_crosshair_px": round_float(nearest_distance),
        "stop_reason": None,
    }
    threshold = float(args.click_threshold_px)
    if nearest is not None and nearest_distance is not None and nearest_distance <= threshold:
        base.update({
            "after_validation_method": "yolo_center_detection",
            "after_validation_passed": True,
            "after_chosen": nearest,
            "after_distance_to_crosshair_px": round_float(nearest_distance),
        })
        return base
    if args.after_validation_mode == "hybrid":
        roi = analyze_center_roi_yellow(after_frame if after_frame is not None else after_image_path, crosshair, args)
        base.update(roi)
        if roi["center_roi_fallback_passed"]:
            base.update({
                "after_validation_method": "center_roi_yellow_fallback",
                "after_validation_passed": True,
                "after_distance_to_crosshair_px": roi["center_roi_yellow_centroid_distance_px"],
            })
            return base
    else:
        base.update({
            "center_roi_radius_px": args.center_roi_radius_px,
            "center_roi_click_threshold_px": args.center_roi_click_threshold_px,
            "center_roi_yellow_pixel_count": None,
            "center_roi_largest_contour_area_px": None,
            "center_roi_yellow_centroid_x": None,
            "center_roi_yellow_centroid_y": None,
            "center_roi_yellow_centroid_distance_px": None,
            "center_roi_fallback_passed": False,
        })
    if not after_detections:
        base.update({"after_validation_method": "no_after_detection", "stop_reason": "after_detection_missing", "after_distance_to_crosshair_px": None})
    else:
        base.update({"after_validation_method": "nearest_yolo_far", "stop_reason": "after_distance_exceeded_threshold"})
    return base



def p90(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.90)))
    return round_float(ordered[index])


def new_retry_state() -> dict[str, Any]:
    return {
        "current_group_id": 0,
        "groups_started": 0,
        "retry_count_for_group": 0,
        "total_retry_attempts": 0,
        "last_before_center": None,
        "original_before_center": None,
        "retry_started_at_iteration": None,
        "retry_limit_reached_count": 0,
        "center_roi_near_miss_retry_count": 0,
        "nearest_yolo_retry_count": 0,
        "same_target_retry_count": 0,
        "successful_clicks_after_retry": 0,
    }


def row_before_center(row: dict[str, Any]) -> dict[str, float] | None:
    x = row.get("chosen_center_x")
    y = row.get("chosen_center_y")
    if x is None or y is None:
        return None
    return {"x": float(x), "y": float(y)}


def ensure_retry_group(row: dict[str, Any], args: argparse.Namespace, retry_state: dict[str, Any]) -> None:
    center = row_before_center(row)
    last = retry_state.get("last_before_center")
    same_distance = phase81.distance(last, center) if last and center else None
    if retry_state.get("current_group_id") and same_distance is not None and same_distance <= float(args.retry_same_target_distance_px):
        row["retry_group_id"] = retry_state["current_group_id"]
        row["same_target_distance_px"] = round_float(same_distance)
    else:
        retry_state["current_group_id"] = int(retry_state.get("current_group_id", 0)) + 1
        retry_state["groups_started"] = int(retry_state.get("groups_started", 0)) + 1
        retry_state["retry_count_for_group"] = 0
        retry_state["original_before_center"] = center
        retry_state["retry_started_at_iteration"] = row.get("iteration_index")
        row["retry_group_id"] = retry_state["current_group_id"]
        row["same_target_distance_px"] = round_float(same_distance)
    row["retry_count_for_group"] = int(retry_state.get("retry_count_for_group", 0))
    row["total_retry_attempts_so_far"] = int(retry_state.get("total_retry_attempts", 0))




def should_run_after_yolo(args: argparse.Namespace) -> bool:
    return args.after_fast_mode == "full"


def click_guard_allows_click(row: dict[str, Any], args: argparse.Namespace) -> tuple[bool, str | None]:
    method = row.get("after_validation_method")
    if method == "yolo_center_detection":
        return True, None
    if method != "center_roi_yellow_fallback":
        return True, None
    if not args.fallback_click_allowed:
        return False, "fallback_click_disabled"
    if args.click_guard_mode == "standard":
        return True, None
    centroid_distance = row.get("center_roi_yellow_centroid_distance_px")
    yellow_count = row.get("center_roi_yellow_pixel_count")
    contour_area = row.get("center_roi_largest_contour_area_px")
    strict_ok = (
        centroid_distance is not None
        and float(centroid_distance) <= float(args.strict_center_roi_click_threshold_px)
        and yellow_count is not None
        and int(yellow_count) >= int(args.center_roi_min_yellow_pixels)
        and contour_area is not None
        and float(contour_area) >= float(args.center_roi_min_contour_area_px)
    )
    if strict_ok:
        return True, None
    return False, "strict_fallback_click_guard_retry"


def benchmark_under_400(iteration_total_ms: float | int | None) -> bool | None:
    if iteration_total_ms is None:
        return None
    return float(iteration_total_ms) < 400.0

def retry_candidate_reason(row: dict[str, Any], args: argparse.Namespace) -> str | None:
    method = row.get("after_validation_method")
    validation_passed = bool(row.get("after_validation_passed"))
    click_gate_passed = bool(row.get("click_gate_passed"))
    nearest_distance = row.get("after_nearest_detection_distance_px")
    after_distance = row.get("after_distance_to_crosshair_px")
    before_distance = row.get("before_distance_to_crosshair_px")
    retry_distance = float(args.retry_distance_px)
    if row.get("strict_fallback_guard_retry"):
        return "strict_fallback_click_guard_retry"
    if method == "no_after_detection" or row.get("stop_reason") == "after_detection_missing":
        return "after_detection_missing_retry"
    if (
        method == "center_roi_yellow_fallback"
        and validation_passed
        and not click_gate_passed
        and getattr(args, "allow_retry_after_center_roi_fallback", True)
    ):
        return "center_roi_passed_but_click_threshold_failed"
    if method == "nearest_yolo_far" and nearest_distance is not None and float(nearest_distance) <= retry_distance:
        return "after_nearest_within_retry_distance"
    if not validation_passed:
        for value in (after_distance, nearest_distance):
            if value is not None and float(value) <= retry_distance:
                return "after_distance_within_retry_distance"
    if before_distance is not None and float(before_distance) <= retry_distance and not row.get("click_executed"):
        return "before_target_within_retry_distance"
    return None


def evaluate_retry_decision(row: dict[str, Any], args: argparse.Namespace, retry_state: dict[str, Any]) -> dict[str, Any]:
    row.update({
        "retry_policy": args.retry_policy,
        "retry_scheduled": False,
        "retry_reason": None,
        "max_retries_per_target": args.max_retries_per_target,
        "max_total_retry_attempts": args.max_total_retry_attempts,
        "retry_limit_reached": False,
    })
    ensure_retry_group(row, args, retry_state)
    if args.retry_policy != "bounded":
        return {"retry_scheduled": False, "retry_limit_reached": False, "retry_reason": None}
    reason = retry_candidate_reason(row, args)
    if reason is None:
        return {"retry_scheduled": False, "retry_limit_reached": False, "retry_reason": None}
    if int(retry_state.get("total_retry_attempts", 0)) >= int(args.max_total_retry_attempts):
        row.update({"retry_limit_reached": True, "retry_reason": "max_total_retry_attempts_reached"})
        retry_state["retry_limit_reached_count"] = int(retry_state.get("retry_limit_reached_count", 0)) + 1
        return {"retry_scheduled": False, "retry_limit_reached": True, "retry_reason": "max_total_retry_attempts_reached"}
    if int(retry_state.get("retry_count_for_group", 0)) >= int(args.max_retries_per_target):
        row.update({"retry_limit_reached": True, "retry_reason": "max_retries_per_target_reached"})
        retry_state["retry_limit_reached_count"] = int(retry_state.get("retry_limit_reached_count", 0)) + 1
        return {"retry_scheduled": False, "retry_limit_reached": True, "retry_reason": "max_retries_per_target_reached"}
    retry_state["total_retry_attempts"] = int(retry_state.get("total_retry_attempts", 0)) + 1
    retry_state["retry_count_for_group"] = int(retry_state.get("retry_count_for_group", 0)) + 1
    retry_state["last_before_center"] = row_before_center(row)
    if row.get("same_target_distance_px") is not None:
        retry_state["same_target_retry_count"] = int(retry_state.get("same_target_retry_count", 0)) + 1
    if reason.startswith("center_roi"):
        retry_state["center_roi_near_miss_retry_count"] = int(retry_state.get("center_roi_near_miss_retry_count", 0)) + 1
    if reason.startswith("after_nearest"):
        retry_state["nearest_yolo_retry_count"] = int(retry_state.get("nearest_yolo_retry_count", 0)) + 1
    row.update({
        "retry_scheduled": True,
        "retry_reason": reason,
        "after_detection_missing_retry": reason == "after_detection_missing_retry",
        "retry_count_for_group": retry_state["retry_count_for_group"],
        "total_retry_attempts_so_far": retry_state["total_retry_attempts"],
    })
    return {"retry_scheduled": True, "retry_limit_reached": False, "retry_reason": reason}


def mark_retry_or_stop(row: dict[str, Any], args: argparse.Namespace, retry_state: dict[str, Any], default_stop: str | None) -> str | None:
    decision = evaluate_retry_decision(row, args, retry_state)
    if decision["retry_scheduled"]:
        row.update({"blocked": False, "blocked_reason": None, "iteration_status": "retry_scheduled", "stop_reason": None})
        return None
    if decision["retry_limit_reached"]:
        row.update({"blocked": True, "blocked_reason": decision["retry_reason"], "iteration_status": "blocked", "stop_reason": "retry_limit_reached"})
        return "retry_limit_reached"
    return default_stop



def save_iteration_evidence(
    *,
    row: dict[str, Any],
    iter_dir: Path,
    before_capture: CapturedFrame,
    after_capture: CapturedFrame,
    before_detections: list[dict[str, Any]],
    after_detections: list[dict[str, Any]],
    crosshair: dict[str, float],
    chosen: dict[str, Any] | None,
    fov_move: dict[str, Any],
    after_chosen: dict[str, Any] | None,
    after_distance: float | None,
) -> None:
    total_start = time.perf_counter()
    encode_ms = 0.0
    encode_ms += encode_capture_image(before_capture)
    encode_ms += encode_capture_image(after_capture)
    phase81.draw_review_image(before_capture.image_path, iter_dir / "before_review.png", before_detections, crosshair, chosen, planned_move=fov_move["planned_relative_move_dxdy"])
    phase81.draw_review_image(after_capture.image_path, iter_dir / "after_review.png", after_detections, crosshair, chosen, planned_move=fov_move["planned_relative_move_dxdy"], after_target=after_chosen, after_distance=after_distance)
    total_ms = ms_since(total_start)
    row["evidence_encode_ms"] = round_float(encode_ms) or 0.0
    row["evidence_total_ms"] = total_ms
    row["evidence_write_ms"] = round(max(0.0, total_ms - encode_ms), 3)
    row["total_io_ms"] = row["evidence_total_ms"]
    write_json(iter_dir / "step_result.json", row)


def clear_iteration_evidence_timings(row: dict[str, Any]) -> None:
    row["evidence_encode_ms"] = 0.0
    row["evidence_write_ms"] = 0.0
    row["evidence_total_ms"] = 0.0
    row["total_io_ms"] = 0.0

def should_save_iteration_evidence(row: dict[str, Any], args: argparse.Namespace) -> bool:
    if row.get("fallback_click_evidence_saved"):
        return True
    if args.save_review_images or args.evidence_mode == "full":
        return True
    if args.evidence_mode == "minimal":
        return False
    return bool(row.get("retry_scheduled") or row.get("blocked") or row.get("stop_reason") or not row.get("click_executed"))

def capture_frame(capture_manager: CaptureManager, monitor: Any, image_path: Path) -> tuple[Any, dict[str, Any]]:
    capture, timings = capture_manager.capture(monitor, image_path)
    timings["capture_ms"] = round(capture_elapsed_from_timings(timings), 3)
    return capture, timings




def yolo_input_frame(capture: CapturedFrame) -> Any:
    return capture.yolo_frame if capture.yolo_frame is not None else capture.frame


def run_yolo_on_frame(ctx: Any, frame: Any) -> list[Any]:
    return ctx.model.predict(
        source=frame,
        conf=ctx.conf,
        iou=ctx.iou,
        max_det=ctx.max_det,
        imgsz=ctx.imgsz,
        device=ctx.actual_device,
        save=False,
        verbose=False,
    )


def run_yolo_on_file_path(ctx: Any, image_path: Path) -> list[Any]:
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


def raw_yolo_boxes_count(results: list[Any]) -> int:
    result = results[0] if results else None
    boxes = getattr(result, "boxes", None)
    return int(len(boxes)) if boxes is not None else 0


def detection_diagnostics(ctx: Any, results: list[Any], detections: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    raw_count = raw_yolo_boxes_count(results)
    parsed_count = len(detections)
    return {
        "raw_yolo_boxes_count": raw_count,
        "parsed_detections_count": parsed_count,
        "live_in_memory_detections_count": parsed_count,
        "live_detect_conf": float(ctx.conf),
        "live_detect_iou": float(ctx.iou),
        "live_detect_max_det": int(ctx.max_det),
        "live_detect_imgsz": int(ctx.imgsz),
        "live_detect_device": ctx.actual_device,
    }


def parity_flags(live_count: int | None, file_count: int | None) -> dict[str, Any]:
    mismatch = live_count is not None and file_count is not None and int(live_count) != int(file_count)
    suspected = live_count == 0 and file_count is not None and int(file_count) > 0
    return {
        "live_vs_file_detection_mismatch": bool(mismatch),
        "live_detection_input_format_mismatch_suspected": bool(suspected),
    }


def run_detection_parity_check(ctx: Any, capture: CapturedFrame | None, args: argparse.Namespace) -> dict[str, Any]:
    if capture is None or not capture.image_path.exists():
        return {"file_path_detections_count": None, **parity_flags(None, None)}
    try:
        file_results = run_yolo_on_file_path(ctx, capture.image_path)
        file_detections = phase81.detections_from_results(ctx, file_results, capture.screenshot_width, capture.screenshot_height)
        file_count = len(file_detections)
    except Exception as exc:
        return {"file_path_detections_count": None, "debug_detection_parity_error": f"{type(exc).__name__}: {exc}", **parity_flags(None, None)}
    return {"file_path_detections_count": file_count, **parity_flags(0, file_count)}


def capture_and_detect(ctx: Any, monitor: Any, image_path: Path, args: argparse.Namespace, capture_manager: CaptureManager) -> tuple[Any, list[dict[str, Any]], float, float, dict[str, Any]]:
    capture, capture_timings = capture_frame(capture_manager, monitor, image_path)
    t1 = time.perf_counter()
    results = run_yolo_on_frame(ctx, yolo_input_frame(capture))
    detections = phase81.detections_from_results(ctx, results, capture.screenshot_width, capture.screenshot_height)
    detect_ms = ms_since(t1)
    capture_timings.update(detection_diagnostics(ctx, results, detections, args))
    return capture, detections, capture_timings["capture_ms"], detect_ms, capture_timings




def should_save_no_detection_evidence(row: dict[str, Any], args: argparse.Namespace, saved_count: int) -> bool:
    if not args.save_evidence_on_no_detection:
        return False
    if saved_count >= int(args.max_no_detection_evidence):
        return False
    return args.evidence_mode in {"full", "failures"}


def save_no_detection_evidence(row: dict[str, Any], capture: CapturedFrame | None, args: argparse.Namespace, saved_count: int) -> None:
    if capture is None:
        row["evidence_saved"] = False
        row["evidence_saved_reason"] = "no_detection_no_capture"
        row["no_detection_evidence_saved"] = False
        row["no_detection_evidence_saved_reason"] = "no_capture"
        clear_iteration_evidence_timings(row)
        return
    row["before_capture_image_path"] = str(capture.image_path)
    if should_save_no_detection_evidence(row, args, saved_count):
        started = time.perf_counter()
        encode_ms = encode_capture_image(capture)
        total_ms = ms_since(started)
        row["evidence_saved"] = True
        row["evidence_saved_reason"] = "no_detection_timeout"
        row["no_detection_evidence_saved"] = True
        row["no_detection_evidence_saved_reason"] = "no_detection_timeout"
        row["evidence_encode_ms"] = round_float(encode_ms) or 0.0
        row["evidence_total_ms"] = total_ms
        row["evidence_write_ms"] = round(max(0.0, total_ms - encode_ms), 3)
        row["total_io_ms"] = row["evidence_total_ms"]
    else:
        row["evidence_saved"] = False
        row["evidence_saved_reason"] = "no_detection_evidence_limit_or_mode"
        row["no_detection_evidence_saved"] = False
        row["no_detection_evidence_saved_reason"] = "limit_or_mode"
        clear_iteration_evidence_timings(row)


def run_warmup_inference(
    *,
    args: argparse.Namespace,
    ctx: Any,
    capture_manager: CaptureManager,
    title_keywords: tuple[str, ...],
    run_dir: Path,
    events_path: Path,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "warmup_enabled": bool(args.warmup_inference),
        "warmup_ms": None,
        "warmup_capture_ms": None,
        "warmup_detect_ms": None,
        "warmup_detections_count": None,
        "warmup_error": None,
    }
    if not args.warmup_inference:
        append_event(events_path, "warmup_skipped", reason="disabled")
        return result
    started = time.perf_counter()
    append_event(events_path, "warmup_started")
    try:
        gate = phase81.get_gate_state(title_keywords)
        if gate.get("blocked"):
            result["warmup_error"] = gate.get("blocked_reason") or "foreground_blocked"
            append_event(events_path, "warmup_completed", **result)
            result["warmup_ms"] = ms_since(started)
            return result
        capture, detections, capture_ms, detect_ms, _timings = capture_and_detect(
            ctx, gate["monitor"], run_dir / "warmup.png", args, capture_manager
        )
        result.update({
            "warmup_capture_ms": capture_ms,
            "warmup_detect_ms": detect_ms,
            "warmup_detections_count": len(detections),
        })
    except Exception as exc:
        result["warmup_error"] = f"{type(exc).__name__}: {exc}"
    result["warmup_ms"] = ms_since(started)
    append_event(events_path, "warmup_completed", **result)
    return result


def run_iteration(
    *,
    args: argparse.Namespace,
    ctx: Any,
    monitor: Any,
    title_keywords: tuple[str, ...],
    run_dir: Path,
    events_path: Path,
    iteration_index: int,
    action_iteration_index: int,
    no_detection_timeout_count_so_far: int,
    consecutive_no_detection_timeout_count: int,
    no_detection_evidence_saved_count: int,
    previous_clicked_center: dict[str, float] | None,
    retry_state: dict[str, Any],
    capture_manager: CaptureManager,
    tracker: TargetTracker,
) -> tuple[dict[str, Any], str | None, dict[str, float] | None]:
    iter_start = time.perf_counter()
    iter_dir = run_dir / "iterations" / f"iter_{iteration_index:03d}"
    iter_dir.mkdir(parents=True, exist_ok=True)
    row: dict[str, Any] = {
        "iteration_index": iteration_index,
        "loop_iteration_index": iteration_index,
        "action_iteration_index": action_iteration_index,
        "before_capture_image_path": None,
        "before_review_image_path": None,
        "no_detection_policy": args.no_detection_policy,
        "no_detection_timeout_count_so_far": no_detection_timeout_count_so_far,
        "consecutive_no_detection_timeout_count": consecutive_no_detection_timeout_count,
        "save_evidence_on_no_detection": bool(args.save_evidence_on_no_detection),
        "no_detection_evidence_saved": False,
        "no_detection_evidence_saved_reason": None,
        "raw_yolo_boxes_count": None,
        "parsed_detections_count": None,
        "live_in_memory_detections_count": None,
        "file_path_detections_count": None,
        "live_vs_file_detection_mismatch": False,
        "live_detection_input_format_mismatch_suspected": False,
        "live_detect_conf": args.conf,
        "live_detect_iou": args.iou,
        "live_detect_max_det": args.max_det,
        "live_detect_imgsz": args.imgsz,
        "live_detect_device": getattr(ctx, "actual_device", args.device),
        "blocked": False,
        "blocked_reason": None,
        "click_threshold_px": args.click_threshold_px,
        "retry_policy": args.retry_policy,
        "retry_scheduled": False,
        "retry_reason": None,
        "retry_group_id": None,
        "retry_count_for_group": 0,
        "max_retries_per_target": args.max_retries_per_target,
        "max_total_retry_attempts": args.max_total_retry_attempts,
        "total_retry_attempts_so_far": retry_state.get("total_retry_attempts", 0),
        "same_target_distance_px": None,
        "retry_limit_reached": False,
        "evidence_mode": args.evidence_mode,
        "save_evidence_on_fallback_click": bool(args.save_evidence_on_fallback_click),
        "evidence_saved_reason": None,
        "strict_center_roi_click_threshold_px": args.strict_center_roi_click_threshold_px,
        "fallback_click_evidence_saved": False,
        "strict_fallback_guard_retry": False,
        "after_detection_missing_retry": False,
        "benchmark_under_400ms": None,
        "evidence_saved": False,
        "evidence_encode_ms": 0.0,
        "evidence_write_ms": 0.0,
        "evidence_total_ms": 0.0,
        "csv_write_ms": None,
        "events_write_ms": None,
        "total_io_ms": 0.0,
    }
    append_event(events_path, "iteration_started", iteration_index=iteration_index)

    gate = phase81.get_gate_state(title_keywords)
    if gate.get("blocked"):
        row.update({"blocked": True, "blocked_reason": "foreground_blocked", "iteration_status": "blocked", "stop_reason": "foreground_blocked", "iteration_total_ms": ms_since(iter_start)})
        append_event(events_path, "foreground_gate_blocked", iteration_index=iteration_index)
        return row, "foreground_blocked", previous_clicked_center
    append_event(events_path, "foreground_gate_passed", iteration_index=iteration_index)

    append_event(events_path, "wait_for_target_started", iteration_index=iteration_index)
    wait_start = time.perf_counter()
    before_capture = None
    before_detections: list[dict[str, Any]] = []
    before_capture_ms = before_detect_ms = 0.0
    while time.perf_counter() - wait_start <= args.next_target_timeout_sec:
        before_capture, before_detections, before_capture_ms, before_detect_ms, before_capture_timings = capture_and_detect(ctx, monitor, iter_dir / "before.png", args, capture_manager)
        write_json(iter_dir / "before_detection.json", {"detections": before_detections})
        if before_detections:
            break
        time.sleep(args.no_detection_poll_interval_sec)
    wait_ms = ms_since(wait_start)
    row.update({"wait_for_target_ms": wait_ms, "before_capture_ms": before_capture_ms, "before_detect_ms": before_detect_ms, "before_detections_count": len(before_detections)})
    row.update({k: before_capture_timings.get(k) for k in ("capture_backend", "capture_reuse_enabled", "capture_object_init_ms", "monitor_lookup_ms", "raw_grab_ms", "buffer_to_numpy_ms", "color_convert_ms", "evidence_encode_ms", "raw_yolo_boxes_count", "parsed_detections_count", "live_in_memory_detections_count", "live_detect_conf", "live_detect_iou", "live_detect_max_det", "live_detect_imgsz", "live_detect_device")})
    if not before_detections:
        row.update({"blocked": False, "blocked_reason": None, "action_iteration_index": None, "no_detection_timeout_count_so_far": no_detection_timeout_count_so_far + 1, "consecutive_no_detection_timeout_count": consecutive_no_detection_timeout_count + 1, "iteration_status": "no_detection_timeout", "stop_reason": "no_detection_timeout", "iteration_total_ms": ms_since(iter_start)})
        save_no_detection_evidence(row, before_capture, args, no_detection_evidence_saved_count)
        enqueue_failure_evidence("no_detection_timeout", before_capture, row)
        if args.debug_detection_parity or args.debug_detection_parity_on_no_detection:
            parity = run_detection_parity_check(ctx, before_capture, args)
            row.update(parity)
            append_event(events_path, "debug_detection_parity_completed", iteration_index=iteration_index, **parity)
        append_event(events_path, "no_detection_timeout", iteration_index=iteration_index, wait_for_target_ms=wait_ms, blocked=False, evidence_saved=row.get("no_detection_evidence_saved"))
        write_json(iter_dir / "step_result.json", row)
        return row, "no_detection_timeout", previous_clicked_center
    append_event(events_path, "before_detection_completed", iteration_index=iteration_index, detections_count=len(before_detections))

    crosshair = phase81.crosshair_center_from_screen(args.screen_width, args.screen_height)
    t_select = time.perf_counter()
    chosen = phase81.choose_primary_target(before_detections, crosshair)
    target_select_ms = ms_since(t_select)
    chosen_center = chosen.get("center_monitor_px") if chosen else None
    
    predicted_x = float(chosen_center["x"]) if chosen_center else 0.0
    predicted_y = float(chosen_center["y"]) if chosen_center else 0.0
    if chosen_center:
        tracker.update(predicted_x, predicted_y)
        predicted_x, predicted_y = tracker.predict()

    before_distance = phase81.distance({"x": predicted_x, "y": predicted_y}, crosshair) if chosen_center else None
    fov_start = time.perf_counter()
    fov_move = compute_fov_relative_move(
        target_center_x=predicted_x, target_center_y=predicted_y,
        crosshair_x=float(crosshair["x"]), crosshair_y=float(crosshair["y"]),
        screen_width=args.screen_width, screen_height=args.screen_height,
        horizontal_fov_deg=args.horizontal_fov_deg, vertical_fov_deg=args.vertical_fov_deg,
        counts_per_degree=args.counts_per_degree, global_gain=args.global_gain,
    )
    fov_compute_ms = ms_since(fov_start)
    rounded_move = fov_move["rounded_relative_move_dxdy"]
    row.update({
        "target_select_ms": target_select_ms, "fov_compute_ms": fov_compute_ms,
        "chosen_detection_index": chosen.get("detection_index") if chosen else None,
        "chosen_center_x": chosen_center.get("x") if chosen_center else None,
        "chosen_center_y": chosen_center.get("y") if chosen_center else None,
        "crosshair_x": crosshair["x"], "crosshair_y": crosshair["y"],
        "before_distance_to_crosshair_px": round_float(before_distance),
        "angle_delta_x_deg": round_float(fov_move["angle_delta_deg"]["x"]),
        "angle_delta_y_deg": round_float(fov_move["angle_delta_deg"]["y"]),
        "rounded_relative_dx": rounded_move["dx"], "rounded_relative_dy": rounded_move["dy"],
        "distance_from_previous_target_px": phase81.distance(previous_clicked_center, chosen_center) if previous_clicked_center and chosen_center else None,
        "possible_same_target_as_previous": phase81.distance(previous_clicked_center, chosen_center) < 8 if previous_clicked_center and chosen_center else False,
    })

    move_gate = phase81.build_move_gate(args=args, gate=gate, chosen=chosen, rounded_move=rounded_move)
    gate_before_move = phase81.get_gate_state(title_keywords)
    if gate_before_move.get("blocked"):
        row.update({"blocked": True, "blocked_reason": "foreground_blocked", "iteration_status": "blocked", "stop_reason": "foreground_blocked", "iteration_total_ms": ms_since(iter_start)})
        write_json(iter_dir / "step_result.json", row)
        return row, "foreground_blocked", previous_clicked_center
    sendinput_attempted = False
    relative_aim_executed = False
    click_executed = False
    click_ms = 0.0
    t_move = time.perf_counter()
    if move_gate["allowed_to_move"]:
        sendinput_attempted = True
        dx = int(rounded_move["dx"])
        dy = int(rounded_move["dy"])
        
        # Smooth pursuit move (Mathematical Fallback, max 3 steps)
        target_dx = float(dx)
        target_dy = float(dy)
        steps = min(3, max(1, int(math.hypot(dx, dy) / 20.0)))
        
        acc_dx = 0
        acc_dy = 0
        
        for i in range(steps):
            target_x_at_step = target_dx * (i + 1) / steps
            target_y_at_step = target_dy * (i + 1) / steps
            step_dx = int(target_x_at_step) - acc_dx
            step_dy = int(target_y_at_step) - acc_dy
            
            if step_dx != 0 or step_dy != 0:
                phase81.send_relative_mouse_move(step_dx, step_dy)
                
            acc_dx += step_dx
            acc_dy += step_dy
            time.sleep(0.002) # Hardware breathing time to prevent engine swallowing
            
        if not click_executed and args.allow_click:
            time.sleep(0.015) # Engine Settle Time
            t_click = time.perf_counter()
            phase9.send_left_click(args.click_down_up_delay_ms)
            click_ms = ms_since(t_click)
            click_executed = True
            append_event(events_path, "click_executed", iteration_index=iteration_index, dynamic_gate=True)

        relative_aim_executed = True
        append_event(events_path, "relative_move_executed", iteration_index=iteration_index, dx=rounded_move["dx"], dy=rounded_move["dy"])
    sendinput_move_ms = ms_since(t_move)
    row.update({"sendinput_move_ms": sendinput_move_ms, "relative_aim_executed": relative_aim_executed, "sendinput_attempted": sendinput_attempted, "click_executed": click_executed, "click_ms": click_ms})

    post_move_start = time.perf_counter()
    # Sleep removed to abandon hard block
    row["post_move_sleep_ms"] = ms_since(post_move_start)
    after_capture, after_capture_timings = capture_frame(capture_manager, monitor, iter_dir / "after.png")
    after_capture_ms = after_capture_timings["capture_ms"]
    if not should_run_after_yolo(args):
        after_detections = []
        after_detect_ms = 0.0
    else:
        t_after_detect = time.perf_counter()
        after_results = ctx.model.predict(
            source=after_capture.frame,
            conf=ctx.conf,
            iou=ctx.iou,
            max_det=ctx.max_det,
            imgsz=ctx.imgsz,
            device=ctx.actual_device,
            save=False,
            verbose=False,
        )
        after_detections = phase81.detections_from_results(ctx, after_results, after_capture.screenshot_width, after_capture.screenshot_height)
        after_detect_ms = ms_since(t_after_detect)
    write_json(iter_dir / "after_detection.json", {"detections": after_detections, "after_fast_mode": args.after_fast_mode})
    row.update({"after_capture_ms": after_capture_ms, "after_detect_ms": after_detect_ms, "after_detections_count": len(after_detections)})
    after_validate_start = time.perf_counter()
    append_event(events_path, "after_validation_started", iteration_index=iteration_index, mode=args.after_validation_mode)
    validation = validate_after_move(after_detections=after_detections, crosshair=crosshair, after_image_path=after_capture.image_path, after_frame=after_capture.frame, args=args)
    after_validate_ms = ms_since(after_validate_start)
    after_chosen = validation.get("after_chosen")
    after_center = after_chosen.get("center_monitor_px") if after_chosen else None
    after_distance = validation.get("after_distance_to_crosshair_px")
    row.update({
        "after_validate_ms": after_validate_ms,
        "after_validation_ms": after_validate_ms,
        "after_chosen_center_x": after_center.get("x") if after_center else validation.get("center_roi_yellow_centroid_x"),
        "after_chosen_center_y": after_center.get("y") if after_center else validation.get("center_roi_yellow_centroid_y"),
        "after_distance_to_crosshair_px": round_float(after_distance),
        **{k: v for k, v in validation.items() if k not in {"after_chosen", "stop_reason"}},
    })
    append_event(events_path, "after_validation_completed", iteration_index=iteration_index, after_distance_to_crosshair_px=round_float(after_distance), method=validation.get("after_validation_method"), passed=validation.get("after_validation_passed"))
    if validation.get("after_validation_method") == "yolo_center_detection":
        append_event(events_path, "after_validation_yolo_center_passed", iteration_index=iteration_index, after_distance_to_crosshair_px=round_float(after_distance))
    elif validation.get("after_validation_method") == "center_roi_yellow_fallback":
        append_event(events_path, "after_validation_center_roi_fallback_passed", iteration_index=iteration_index, after_distance_to_crosshair_px=round_float(after_distance))
    if not validation.get("after_validation_passed"):
        stop = validation.get("stop_reason") or "after_distance_exceeded_threshold"
        enqueue_failure_evidence(stop, after_capture, row)
        append_event(events_path, "after_validation_failed", iteration_index=iteration_index, method=validation.get("after_validation_method"), stop_reason=stop)
        row.update({"blocked": True, "blocked_reason": stop, "iteration_status": "blocked", "stop_reason": stop})
        row_stop = mark_retry_or_stop(row, args, retry_state, stop)
        if row.get("retry_scheduled"):
            append_event(events_path, "retry_scheduled", iteration_index=iteration_index, retry_reason=row.get("retry_reason"), retry_group_id=row.get("retry_group_id"))
            append_event(events_path, "retry_group_continued" if row.get("same_target_distance_px") is not None else "retry_group_started", iteration_index=iteration_index, retry_group_id=row.get("retry_group_id"))
        elif row.get("retry_limit_reached"):
            append_event(events_path, "retry_limit_reached", iteration_index=iteration_index, retry_reason=row.get("retry_reason"))
        row["iteration_total_ms"] = ms_since(iter_start)
        row["action_round_ms"] = row["iteration_total_ms"]
        evidence_start = time.perf_counter()
        row["fallback_click_evidence_saved"] = False
        row["evidence_saved"] = should_save_iteration_evidence(row, args)
        if row["evidence_saved"]:
            row["evidence_saved_reason"] = "fallback_click" if row.get("fallback_click_evidence_saved") else "retry_or_failure"
            save_iteration_evidence(row=row, iter_dir=iter_dir, before_capture=before_capture, after_capture=after_capture, before_detections=before_detections, after_detections=after_detections, crosshair=crosshair, chosen=chosen, fov_move=fov_move, after_chosen=after_chosen, after_distance=after_distance)
            append_event(events_path, "evidence_saved", iteration_index=iteration_index)
        else:
            clear_iteration_evidence_timings(row)
        row["iteration_total_ms"] = ms_since(iter_start)
        row["action_round_ms"] = row["iteration_total_ms"]
        row["benchmark_under_400ms"] = benchmark_under_400(row["iteration_total_ms"])
        return row, row_stop, previous_clicked_center

    if not row.get("click_executed"):
        gate_before_click = phase81.get_gate_state(title_keywords)
        if gate_before_click.get("blocked"):
            row.update({"blocked": True, "blocked_reason": "foreground_blocked", "iteration_status": "blocked", "stop_reason": "foreground_blocked", "iteration_total_ms": ms_since(iter_start)})
            write_json(iter_dir / "step_result.json", row)
            return row, "foreground_blocked", previous_clicked_center
        click_gate = phase9.build_click_gate(
            execute_move=args.execute_move, allow_click=args.allow_click, confirm_local_aimlab_only=args.confirm_local_aimlab_only,
            foreground_before_capture=True, foreground_before_move=True, foreground_before_click=True,
            after_detection_exists=True, after_distance_to_crosshair_px=after_distance,
            click_threshold_px=args.click_threshold_px, already_clicked_once=False,
        )
        guard_allowed, guard_reason = click_guard_allows_click(row, args)
        row["strict_fallback_guard_retry"] = guard_reason == "strict_fallback_click_guard_retry"
        row["click_gate_passed"] = bool(click_gate["allowed_to_click"] and guard_allowed)
        if click_gate["allowed_to_click"] and not guard_allowed:
            row["blocked_reason"] = guard_reason
        
        if not row["click_gate_passed"] and move_gate["allowed_to_move"]:
            failure_type = "fallback_click_blocked" if (click_gate["allowed_to_click"] and not guard_allowed) else "click_gate_failed"
            enqueue_failure_evidence(failure_type, after_capture, row)

        if row["click_gate_passed"]:
            append_event(events_path, "click_gate_passed", iteration_index=iteration_index)
            t_click = time.perf_counter()
            phase9.send_left_click(args.click_down_up_delay_ms)
            row["click_ms"] = ms_since(t_click)
            row["click_executed"] = True
            append_event(events_path, "click_executed", iteration_index=iteration_index)
    else:
        row["click_gate_passed"] = True

    click_executed = row.get("click_executed", False)
    row.update({"iteration_status": "clicked" if click_executed else "completed_no_click", "stop_reason": None})
    row_stop = None
    if click_executed:
        if retry_state.get("last_before_center") is not None:
            ensure_retry_group(row, args, retry_state)
        if int(row.get("retry_count_for_group") or 0) > 0:
            retry_state["successful_clicks_after_retry"] = int(retry_state.get("successful_clicks_after_retry", 0)) + 1
        retry_state["last_before_center"] = None
        retry_state["retry_count_for_group"] = 0
    else:
        row_stop = mark_retry_or_stop(row, args, retry_state, None)
        if row.get("retry_scheduled"):
            append_event(events_path, "retry_scheduled", iteration_index=iteration_index, retry_reason=row.get("retry_reason"), retry_group_id=row.get("retry_group_id"))
            append_event(events_path, "retry_group_continued" if row.get("same_target_distance_px") is not None else "retry_group_started", iteration_index=iteration_index, retry_group_id=row.get("retry_group_id"))
        elif row.get("retry_limit_reached"):
            append_event(events_path, "retry_limit_reached", iteration_index=iteration_index, retry_reason=row.get("retry_reason"))

    post_wait_start = time.perf_counter()
    if click_executed and args.post_click_wait_sec > 0:
        time.sleep(args.post_click_wait_sec)
    row["post_click_wait_ms"] = ms_since(post_wait_start)
    log_start = time.perf_counter()
    row["iteration_total_ms"] = ms_since(iter_start)
    row["action_round_ms"] = row["iteration_total_ms"]
    evidence_start = time.perf_counter()
    row["fallback_click_evidence_saved"] = bool(click_executed and row.get("after_validation_method") == "center_roi_yellow_fallback" and getattr(args, "save_evidence_on_fallback_click", False))
    row["evidence_saved"] = should_save_iteration_evidence(row, args)
    if row["evidence_saved"]:
        row["evidence_saved_reason"] = "fallback_click" if row.get("fallback_click_evidence_saved") else "retry_or_failure"
        save_iteration_evidence(row=row, iter_dir=iter_dir, before_capture=before_capture, after_capture=after_capture, before_detections=before_detections, after_detections=after_detections, crosshair=crosshair, chosen=chosen, fov_move=fov_move, after_chosen=after_chosen, after_distance=after_distance)
        append_event(events_path, "evidence_saved", iteration_index=iteration_index)
    else:
        clear_iteration_evidence_timings(row)
        append_event(events_path, "evidence_skipped_for_success", iteration_index=iteration_index)
    row["logging_ms"] = ms_since(log_start)
    row["iteration_total_ms"] = ms_since(iter_start)
    row["action_round_ms"] = row["iteration_total_ms"]
    row["benchmark_under_400ms"] = benchmark_under_400(row["iteration_total_ms"])
    append_event(events_path, "iteration_completed", iteration_index=iteration_index, click_executed=click_executed, retry_scheduled=row.get("retry_scheduled"))
    return row, row_stop, after_center if click_executed else previous_clicked_center





def should_stop_after_no_detection_timeout(
    *,
    policy: str,
    total_count: int,
    consecutive_count: int,
    max_total: int,
    max_consecutive: int,
) -> tuple[bool, str | None]:
    if policy == "stop":
        return True, "no_detection_timeout"
    if total_count >= max_total:
        return True, "max_no_detection_timeouts_reached"
    if consecutive_count >= max_consecutive:
        return True, "max_consecutive_no_detection_timeouts_reached"
    return False, None

def run_capture_benchmark(args: argparse.Namespace, run_dir: Path, events_path: Path, title_keywords: tuple[str, ...]) -> int:
    append_event(events_path, "capture_benchmark_started", backend=args.capture_backend, frames=args.capture_benchmark_frames)
    gate = phase81.get_gate_state(title_keywords)
    summary: dict[str, Any] = {
        "phase": 10,
        "mode": "capture_benchmark_only",
        "blocked": bool(gate.get("blocked")),
        "blocked_reason": gate.get("blocked_reason") if gate.get("blocked") else None,
        "requested_capture_backend": args.capture_backend,
        "frames": args.capture_benchmark_frames,
        "capture_benchmark_include_encode": bool(args.capture_benchmark_include_encode),
        **dxcam_status(),
        "backends": {},
    }
    if gate.get("blocked"):
        write_json(run_dir / "capture_benchmark_summary.json", summary)
        append_event(events_path, "capture_benchmark_blocked", blocked_reason=summary["blocked_reason"])
        return 0
    monitor = gate["monitor"]
    for backend in benchmark_backend_names(args.capture_backend):
        backend_dir = run_dir / "capture_benchmark" / backend
        values: list[float] = []
        breakdown: dict[str, list[float]] = {key: [] for key in ("capture_object_init_ms", "monitor_lookup_ms", "raw_grab_ms", "buffer_to_numpy_ms", "color_convert_ms", "evidence_encode_ms")}
        backend_summary: dict[str, Any] = {"capture_backend": backend, "frames_requested": args.capture_benchmark_frames}
        try:
            manager = CaptureManager(backend)
            try:
                for index in range(1, int(args.capture_benchmark_frames) + 1):
                    capture, timings = capture_frame(manager, monitor, backend_dir / f"frame_{index:03d}.png")
                    if args.capture_benchmark_include_encode:
                        timings["evidence_encode_ms"] = encode_capture_image(capture)
                    values.append(float(timings["capture_ms"]))
                    for key in breakdown:
                        breakdown[key].append(float(timings.get(key) or 0.0))
            finally:
                manager.close()
            backend_summary.update({
                "available": True,
                "capture_reuse_enabled": backend in {"mss_persistent", "dxcam"},
                "frames_processed": len(values),
                "average_capture_ms": summarize_numbers(values)["average"],
                "median_capture_ms": summarize_numbers(values)["median"],
                "min_capture_ms": summarize_numbers(values)["min"],
                "max_capture_ms": summarize_numbers(values)["max"],
                "p90_capture_ms": summarize_numbers(values)["p90"],
                "breakdown_average_ms": {key: summarize_numbers(items)["average"] for key, items in breakdown.items()},
                "breakdown_p90_ms": {key: summarize_numbers(items)["p90"] for key, items in breakdown.items()},
            })
        except Exception as exc:
            backend_summary.update({
                "available": False,
                "error": f"{type(exc).__name__}: {exc}",
                "frames_processed": len(values),
            })
            if backend == "dxcam":
                summary["dxcam_available"] = False
                summary["dxcam_import_error"] = backend_summary["error"]
        summary["backends"][backend] = backend_summary
    write_json(run_dir / "capture_benchmark_summary.json", summary)
    append_event(events_path, "capture_benchmark_completed", summary_path=str(run_dir / "capture_benchmark_summary.json"))
    print(f"phase={PHASE}")
    print("mode=capture_benchmark_only")
    print(f"blocked={summary['blocked']}")
    print(f"run_dir={run_dir}")
    return 0

def main() -> int:
    global evidence_worker_running
    evidence_worker_running = True
    evidence_worker_thread = threading.Thread(target=evidence_worker_loop, daemon=True)
    evidence_worker_thread.start()

    args = parse_args()
    process_started_at = now_iso()
    process_started_perf = time.perf_counter()
    run_id = args.run_id or default_run_id()
    run_dir = prepare_run_dir(args.output_dir, run_id, args.overwrite)
    events_path = run_dir / "events.jsonl"
    rows: list[dict[str, Any]] = []
    stop_reason = "not_started"
    blocked = False
    keyboard_interrupt = False
    write_json(run_dir / "run_config.json", {
        "phase": 10,
        "mode": MODE,
        "args": phase9.args_to_jsonable(args),
        "model": str(args.model),
        "conf": args.conf,
        "iou": args.iou,
        "max_det": args.max_det,
        "imgsz": args.imgsz,
        "device": args.device,
        "capture_backend": args.capture_backend,
        "debug_detection_parity": bool(args.debug_detection_parity),
        "debug_detection_parity_on_no_detection": bool(args.debug_detection_parity_on_no_detection),
    })
    append_event(events_path, "run_started", run_id=run_id)
    allowed, gate_reason = startup_gate(args)
    if not allowed:
        blocked = True
        stop_reason = gate_reason or "startup_gate_blocked"
        timing = {"process_started_at": process_started_at, "process_ended_at": now_iso(), "wall_duration_sec": round(time.perf_counter() - process_started_perf, 4)}
        summary = build_summary(args, run_dir, rows, stop_reason=stop_reason, blocked=blocked, keyboard_interrupt=False, timing=timing)
        write_json(run_dir / "phase10_summary.json", summary)
        write_iteration_csv(run_dir / "iteration_summary.csv", rows)
        append_event(events_path, "run_stopped", stop_reason=stop_reason, blocked=True)
        print(f"phase={PHASE}")
        print(f"mode={MODE}")
        print(f"blocked=True")
        print(f"stop_reason={stop_reason}")
        print(f"run_dir={run_dir}")
        return 0

    title_keywords = tuple(args.title_keywords or ("aimlab", "aim lab"))
    if args.capture_benchmark_only:
        return run_capture_benchmark(args, run_dir, events_path, title_keywords)
    ctx = None
    previous_clicked_center: dict[str, float] | None = None
    retry_state = new_retry_state()
    startup_started_at = now_iso()
    startup_started_perf = time.perf_counter()
    append_event(events_path, "startup_started")
    model_load_ms = None
    warmup_info: dict[str, Any] = {
        "warmup_enabled": bool(args.warmup_inference),
        "warmup_ms": None,
        "warmup_capture_ms": None,
        "warmup_detect_ms": None,
        "warmup_detections_count": None,
        "warmup_error": None,
    }
    warmup_ms = None
    loop_started_at = None
    loop_started_perf = None
    capture_manager = None
    tracker = TargetTracker(latency_compensation_sec=args.latency_compensation_sec)
    try:
        runtime_capture_backend, capture_backend_status = resolve_runtime_capture_backend(args.capture_backend)
        capture_manager = CaptureManager(runtime_capture_backend)
        append_event(events_path, "capture_backend_selected", requested=args.capture_backend, selected=runtime_capture_backend, **capture_backend_status)
        model_start = time.perf_counter()
        ctx = phase81.load_inference_context(args)
        model_load_ms = ms_since(model_start)
        warmup_info = run_warmup_inference(
            args=args,
            ctx=ctx,
            capture_manager=capture_manager,
            title_keywords=title_keywords,
            run_dir=run_dir,
            events_path=events_path,
        )
        warmup_ms = warmup_info.get("warmup_ms")
        startup_ended_at = now_iso()
        startup_duration_sec = round(time.perf_counter() - startup_started_perf, 4)
        append_event(events_path, "startup_completed", model_load_ms=model_load_ms, warmup_ms=warmup_ms, startup_duration_sec=startup_duration_sec)
        loop_started_at = now_iso()
        loop_started_perf = time.perf_counter()
        append_event(events_path, "loop_started", max_duration_sec=args.max_duration_sec)
        loop_iteration_index = 1
        action_iteration_count = 0
        no_detection_timeout_count = 0
        consecutive_no_detection_timeout_count = 0
        no_detection_evidence_saved_count = 0
        while action_iteration_count < int(args.max_iterations):
            if stop_file_requested(args):
                stop_reason = "user_stop_requested"
                append_event(events_path, "user_stop_requested", stop_file=str(args.stop_file))
                break
            if loop_iteration_index > int(args.max_loop_iterations):
                stop_reason = "max_loop_iterations_reached"
                break
            if should_stop_for_active_duration(loop_started_perf, args.max_duration_sec):
                stop_reason = "max_duration_reached"
                break
            gate = phase81.get_gate_state(title_keywords)
            if gate.get("blocked"):
                stop_reason = "foreground_blocked"
                blocked = True
                append_event(events_path, "foreground_gate_blocked", iteration_index=loop_iteration_index)
                break
            row, row_stop, previous_clicked_center = run_iteration(
                args=args, ctx=ctx, monitor=gate["monitor"], title_keywords=title_keywords,
                run_dir=run_dir, events_path=events_path, iteration_index=loop_iteration_index,
                action_iteration_index=action_iteration_count + 1,
                no_detection_timeout_count_so_far=no_detection_timeout_count,
                consecutive_no_detection_timeout_count=consecutive_no_detection_timeout_count,
                no_detection_evidence_saved_count=no_detection_evidence_saved_count,
                previous_clicked_center=previous_clicked_center,
                retry_state=retry_state,
                capture_manager=capture_manager,
                tracker=tracker,
            )
            rows.append(row)
            if row_stop == "no_detection_timeout" and args.no_detection_policy == "continue":
                no_detection_timeout_count += 1
                consecutive_no_detection_timeout_count += 1
                should_stop_no_detection, no_detection_stop_reason = should_stop_after_no_detection_timeout(
                    policy=args.no_detection_policy,
                    total_count=no_detection_timeout_count,
                    consecutive_count=consecutive_no_detection_timeout_count,
                    max_total=int(args.max_no_detection_timeouts),
                    max_consecutive=int(args.max_consecutive_no_detection_timeouts),
                )
                if should_stop_no_detection:
                    stop_reason = no_detection_stop_reason or "no_detection_timeout"
                    blocked = False
                    break
                if row.get("no_detection_evidence_saved"):
                    no_detection_evidence_saved_count += 1
                append_event(events_path, "no_detection_continue", iteration_index=loop_iteration_index, no_detection_timeout_count=no_detection_timeout_count, consecutive_no_detection_timeout_count=consecutive_no_detection_timeout_count)
                loop_iteration_index += 1
                continue
            if row.get("stop_reason") != "no_detection_timeout":
                consecutive_no_detection_timeout_count = 0
            if row.get("before_detections_count", 0):
                action_iteration_count += 1
                if row.get("click_executed") or not row.get("retry_scheduled"):
                    tracker.reset()
            if row_stop:
                stop_reason = row_stop
                blocked = bool(row.get("blocked"))
                break
            loop_iteration_index += 1
        else:
            stop_reason = "max_iterations_reached"
        if stop_reason == "not_started":
            stop_reason = "max_iterations_reached"
    except KeyboardInterrupt:
        keyboard_interrupt = True
        blocked = True
        stop_reason = "keyboard_interrupt"
        append_event(events_path, "keyboard_interrupt")
    finally:
        evidence_worker_running = False
        evidence_queue.put(None)
        evidence_worker_thread.join(timeout=2.0)
        if capture_manager is not None:
            capture_manager.close()
        process_ended_at = now_iso()
        loop_ended_at = now_iso() if loop_started_perf is not None else None
        active_loop_duration_sec = round(time.perf_counter() - loop_started_perf, 4) if loop_started_perf is not None else None
        timing = {
            "process_started_at": process_started_at,
            "process_ended_at": process_ended_at,
            "wall_duration_sec": round(time.perf_counter() - process_started_perf, 4),
            "startup_started_at": locals().get("startup_started_at"),
            "startup_ended_at": locals().get("startup_ended_at"),
            "startup_duration_sec": locals().get("startup_duration_sec"),
            "model_load_ms": model_load_ms,
            "warmup_enabled": warmup_info.get("warmup_enabled"),
            "warmup_ms": warmup_info.get("warmup_ms"),
            "warmup_capture_ms": warmup_info.get("warmup_capture_ms"),
            "warmup_detect_ms": warmup_info.get("warmup_detect_ms"),
            "warmup_detections_count": warmup_info.get("warmup_detections_count"),
            "warmup_error": warmup_info.get("warmup_error"),
            "loop_started_at": loop_started_at,
            "loop_ended_at": loop_ended_at,
            "active_loop_duration_sec": active_loop_duration_sec,
            "max_duration_sec": getattr(args, "max_duration_sec", None),
        }
        summary = build_summary(args, run_dir, rows, stop_reason=stop_reason, blocked=blocked, keyboard_interrupt=keyboard_interrupt, timing=timing)
        write_json(run_dir / "phase10_summary.json", summary)
        write_iteration_csv(run_dir / "iteration_summary.csv", rows)
        append_event(events_path, "loop_stopped", stop_reason=stop_reason, active_loop_duration_sec=active_loop_duration_sec)
        append_event(events_path, "performance_summary", performance=summary.get("performance"))
        append_event(events_path, "run_stopped", stop_reason=stop_reason, blocked=blocked)
    print(f"phase={PHASE}")
    print(f"mode={MODE}")
    print(f"blocked={blocked}")
    print(f"stop_reason={stop_reason}")
    print(f"action_iterations_attempted={len(rows)}")
    print(f"clicks_executed={sum(1 for row in rows if row.get('click_executed'))}")
    print(f"run_dir={run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
