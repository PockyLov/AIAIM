from __future__ import annotations

import argparse
import csv
import json
import ntpath
import platform
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


PHASE_NAME = "Phase 5 - Offline Coordinate Mapping / Geometry Validation"
SAFETY_BOUNDARY = {
    "no_realtime_capture": True,
    "no_live_aimlab_connection": True,
    "no_mouse_movement": True,
    "no_mouse_click": True,
    "no_click_target_output": True,
    "no_mouse_target_output": True,
    "no_closed_loop": True,
    "no_anti_cheat_bypass": True,
}


@dataclass
class Rect:
    left: float
    top: float
    right: float
    bottom: float
    width: float
    height: float

    def to_dict(self) -> dict[str, float]:
        return {
            "left": round_float(self.left),
            "top": round_float(self.top),
            "right": round_float(self.right),
            "bottom": round_float(self.bottom),
            "width": round_float(self.width),
            "height": round_float(self.height),
        }


@dataclass
class MetadataInfo:
    status: str
    candidates: list[Path]
    path: Path | None
    raw: dict[str, Any] | None
    screenshot_size: tuple[float, float] | None
    window_rect: Rect | None
    monitor_rect: Rect | None
    notes: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 5 offline coordinate mapping and geometry validation.")
    parser.add_argument("--phase4-json-dir", type=Path, default=Path("runs/detect/phase4_offline_detection/json"))
    parser.add_argument("--metadata-dir", type=Path, default=Path("data/raw/screenshots"))
    parser.add_argument("--output-dir", type=Path, default=Path("runs/detect/phase5_coordinate_mapping"))
    parser.add_argument("--review-images", action="store_true", default=False)
    parser.add_argument("--metadata-recursive", action="store_true", default=False)
    parser.add_argument("--tolerance-px", type=float, default=5.0)
    parser.add_argument("--overwrite", action="store_true", default=False)
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def round_float(value: float | int | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


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


def jsonable_args(args: argparse.Namespace) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in vars(args).items():
        result[key] = str(value) if isinstance(value, Path) else value
    return result


def prepare_output_dir(output_dir: Path, overwrite: bool) -> None:
    if output_dir.exists():
        if not overwrite:
            raise FileExistsError(f"output directory already exists; pass --overwrite to replace it: {output_dir}")
        shutil.rmtree(output_dir)
    (output_dir / "mapped_json").mkdir(parents=True, exist_ok=True)
    (output_dir / "review_images").mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_nested_value(data: Any, names: set[str]) -> Any:
    if isinstance(data, dict):
        for name in names:
            if name in data:
                value = data[name]
                if isinstance(value, str):
                    return value
        for value in data.values():
            found = find_nested_value(value, names)
            if found:
                return found
    elif isinstance(data, list):
        for value in data:
            found = find_nested_value(value, names)
            if found:
                return found
    return None


def extract_source_image_path(phase4: dict[str, Any]) -> str | None:
    image_obj = phase4.get("image")
    if isinstance(image_obj, dict):
        for key in ("source_path", "source_image", "image_path", "input_image", "source"):
            value = image_obj.get(key)
            if isinstance(value, str):
                return value
    for key in ("source_path", "source_image", "image_path", "input_image", "source"):
        value = phase4.get(key)
        if isinstance(value, str):
            return value
    return find_nested_value(phase4, {"source_path", "source_image", "image_path", "input_image", "source"})


def path_stem(path_text: str | None, fallback: Path) -> str:
    if not path_text:
        return fallback.stem
    normalized = path_text.replace("\\", "/")
    return Path(ntpath.basename(normalized)).stem


def build_metadata_index(metadata_dir: Path, recursive: bool) -> dict[str, list[Path]]:
    pattern = "**/*.json" if recursive else "*.json"
    index: dict[str, list[Path]] = {}
    for path in sorted(metadata_dir.glob(pattern)):
        if path.is_file():
            index.setdefault(path.stem, []).append(path)
    return index


def parse_size(raw: dict[str, Any]) -> tuple[float, float] | None:
    for key in ("screenshot_size", "image_size"):
        value = raw.get(key)
        if isinstance(value, dict):
            width = value.get("width")
            height = value.get("height")
            if width is not None and height is not None:
                return float(width), float(height)
        if isinstance(value, list) and len(value) >= 2:
            return float(value[0]), float(value[1])
    width = raw.get("screenshot_width")
    height = raw.get("screenshot_height")
    if width is not None and height is not None:
        return float(width), float(height)
    return None


def parse_rect(value: Any) -> Rect | None:
    if isinstance(value, dict):
        if all(key in value for key in ("left", "top", "right", "bottom")):
            left = float(value["left"])
            top = float(value["top"])
            right = float(value["right"])
            bottom = float(value["bottom"])
            return Rect(left, top, right, bottom, right - left, bottom - top)
        if all(key in value for key in ("x", "y", "width", "height")):
            left = float(value["x"])
            top = float(value["y"])
            width = float(value["width"])
            height = float(value["height"])
            return Rect(left, top, left + width, top + height, width, height)
    if isinstance(value, list) and len(value) >= 4:
        left, top, right, bottom = (float(value[0]), float(value[1]), float(value[2]), float(value[3]))
        return Rect(left, top, right, bottom, right - left, bottom - top)
    return None


def rect_is_valid(rect: Rect | None) -> bool:
    return bool(rect and rect.right > rect.left and rect.bottom > rect.top and rect.width > 0 and rect.height > 0)


def window_inside_monitor(window: Rect | None, monitor: Rect | None, tolerance_px: float) -> bool:
    if not rect_is_valid(window) or not rect_is_valid(monitor):
        return False
    return (
        window.left >= monitor.left - tolerance_px
        and window.top >= monitor.top - tolerance_px
        and window.right <= monitor.right + tolerance_px
        and window.bottom <= monitor.bottom + tolerance_px
    )


def read_metadata_info(stem: str, metadata_index: dict[str, list[Path]]) -> MetadataInfo:
    candidates = metadata_index.get(stem, [])
    if not candidates:
        return MetadataInfo("missing", [], None, None, None, None, None, ["metadata not found"])
    if len(candidates) > 1:
        return MetadataInfo("duplicate", candidates, None, None, None, None, None, ["multiple metadata files found"])
    path = candidates[0]
    try:
        raw = load_json(path)
        screenshot_size = parse_size(raw)
        window_rect = parse_rect(raw.get("window_rect"))
        monitor_rect = parse_rect(raw.get("monitor_rect"))
    except Exception as exc:
        return MetadataInfo("invalid_metadata", candidates, path, None, None, None, None, [str(exc)])

    notes: list[str] = []
    if not screenshot_size or screenshot_size[0] <= 0 or screenshot_size[1] <= 0:
        notes.append("invalid or missing screenshot size")
    if not rect_is_valid(window_rect):
        notes.append("invalid or missing window_rect")
    if not rect_is_valid(monitor_rect):
        notes.append("invalid or missing monitor_rect")
    status = "invalid_metadata" if notes else "matched"
    return MetadataInfo(status, candidates, path, raw, screenshot_size, window_rect, monitor_rect, notes)


def phase4_image_size(phase4: dict[str, Any]) -> tuple[float | None, float | None]:
    image = phase4.get("image")
    if isinstance(image, dict):
        width = image.get("width")
        height = image.get("height")
        if width is not None and height is not None:
            return float(width), float(height)
    return None, None


def extract_bbox_xyxy(detection: dict[str, Any]) -> dict[str, float] | None:
    bbox = detection.get("bbox_xyxy")
    if isinstance(bbox, dict) and all(key in bbox for key in ("x1", "y1", "x2", "y2")):
        return {key: float(bbox[key]) for key in ("x1", "y1", "x2", "y2")}
    if isinstance(bbox, list) and len(bbox) >= 4:
        return {"x1": float(bbox[0]), "y1": float(bbox[1]), "x2": float(bbox[2]), "y2": float(bbox[3])}
    return None


def extract_center(detection: dict[str, Any], bbox: dict[str, float] | None) -> tuple[float | None, float | None]:
    center = detection.get("center")
    if isinstance(center, dict) and "x" in center and "y" in center:
        return float(center["x"]), float(center["y"])
    bbox_xywh = detection.get("bbox_xywh")
    if isinstance(bbox_xywh, dict) and "x" in bbox_xywh and "y" in bbox_xywh:
        return float(bbox_xywh["x"]), float(bbox_xywh["y"])
    if bbox:
        return (bbox["x1"] + bbox["x2"]) / 2.0, (bbox["y1"] + bbox["y2"]) / 2.0
    return None, None


def detection_validity(
    detection: dict[str, Any], image_width: float, image_height: float
) -> tuple[dict[str, bool], dict[str, float] | None, float | None, float | None]:
    bbox = extract_bbox_xyxy(detection)
    center_x, center_y = extract_center(detection, bbox)
    bbox_basic = bool(bbox and bbox["x1"] < bbox["x2"] and bbox["y1"] < bbox["y2"])
    center_inside_image = bool(
        center_x is not None and center_y is not None and 0 <= center_x <= image_width and 0 <= center_y <= image_height
    )
    center_inside_bbox = bool(
        bbox
        and center_x is not None
        and center_y is not None
        and bbox["x1"] <= center_x <= bbox["x2"]
        and bbox["y1"] <= center_y <= bbox["y2"]
    )
    bbox_inside_image = bool(
        bbox
        and 0 <= bbox["x1"] < bbox["x2"] <= image_width
        and 0 <= bbox["y1"] < bbox["y2"] <= image_height
    )
    return (
        {
            "bbox_basic_valid": bbox_basic,
            "center_inside_image": center_inside_image,
            "center_inside_bbox": center_inside_bbox,
            "bbox_inside_image": bbox_inside_image,
        },
        bbox,
        center_x,
        center_y,
    )


def geometry_values(
    image_x: float,
    image_y: float,
    image_size: tuple[float, float],
    metadata_size: tuple[float, float],
    monitor_rect: Rect,
    window_rect: Rect,
) -> tuple[float, float, float, float, float, float]:
    scale_x = metadata_size[0] / image_size[0]
    scale_y = metadata_size[1] / image_size[1]
    monitor_x = image_x * scale_x
    monitor_y = image_y * scale_y
    window_left_in_monitor = window_rect.left - monitor_rect.left
    window_top_in_monitor = window_rect.top - monitor_rect.top
    window_x = monitor_x - window_left_in_monitor
    window_y = monitor_y - window_top_in_monitor
    return scale_x, scale_y, monitor_x, monitor_y, window_x, window_y


def class_id_of(detection: dict[str, Any]) -> int | None:
    value = detection.get("class_id", detection.get("cls"))
    return int(value) if value is not None else None


def confidence_of(detection: dict[str, Any]) -> float | None:
    value = detection.get("confidence", detection.get("conf"))
    return round_float(value) if value is not None else None


def draw_review_image(
    phase4: dict[str, Any],
    mapped_detections: list[dict[str, Any]],
    window_rect: Rect | None,
    monitor_rect: Rect | None,
    output_path: Path,
    notes: list[str],
) -> None:
    source_path_text = extract_source_image_path(phase4)
    if not source_path_text:
        notes.append("source image path missing; review image skipped")
        return
    source_path = Path(source_path_text.replace("\\", "/"))
    if not source_path.exists():
        notes.append(f"source image not found; review image skipped: {source_path_text}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path).convert("RGB") as image:
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 10)
        except OSError:
            font = ImageFont.load_default()

        if window_rect and monitor_rect:
            left = window_rect.left - monitor_rect.left
            top = window_rect.top - monitor_rect.top
            right = window_rect.right - monitor_rect.left
            bottom = window_rect.bottom - monitor_rect.top
            draw.rectangle((left, top, right, bottom), outline=(0, 128, 255), width=2)

        for item in mapped_detections:
            bbox = item.get("bbox_xyxy") or {}
            center = item.get("image_pixel_center") or {}
            if all(k in bbox for k in ("x1", "y1", "x2", "y2")):
                draw.rectangle((bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]), outline=(0, 255, 0), width=1)
            if "x" in center and "y" in center:
                x = center["x"]
                y = center["y"]
                draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 0, 0))
                win = item.get("window_relative_center") or {}
                text = f"img:({x:.0f},{y:.0f})"
                if "x" in win and "y" in win:
                    text += f" win:({win['x']:.0f},{win['y']:.0f})"
                text += f" inside_window:{item['validity'].get('center_inside_window')}"
                draw.text((min(x + 4, image.width - 260), max(0, y - 10)), text, fill=(0, 255, 0), font=font)
        image.save(output_path)


def process_phase4_json(
    phase4_path: Path,
    args: argparse.Namespace,
    metadata_index: dict[str, list[Path]],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    phase4 = load_json(phase4_path)
    source_image_path = extract_source_image_path(phase4)
    source_stem = path_stem(source_image_path, phase4_path)
    metadata = read_metadata_info(source_stem, metadata_index)
    image_width, image_height = phase4_image_size(phase4)
    detections = phase4.get("detections") if isinstance(phase4.get("detections"), list) else []
    metadata_width = metadata.screenshot_size[0] if metadata.screenshot_size else None
    metadata_height = metadata.screenshot_size[1] if metadata.screenshot_size else None
    size_match = bool(
        image_width is not None
        and image_height is not None
        and metadata_width is not None
        and metadata_height is not None
        and abs(image_width - metadata_width) <= args.tolerance_px
        and abs(image_height - metadata_height) <= args.tolerance_px
    )
    has_window_rect = metadata.window_rect is not None
    has_monitor_rect = metadata.monitor_rect is not None
    rect_valid = bool(
        rect_is_valid(metadata.window_rect)
        and rect_is_valid(metadata.monitor_rect)
        and window_inside_monitor(metadata.window_rect, metadata.monitor_rect, args.tolerance_px)
    )
    notes = list(metadata.notes)
    if has_window_rect and has_monitor_rect and not rect_valid:
        notes.append("window_rect is outside monitor_rect tolerance or rect is invalid")
    if metadata.status == "matched" and not size_match:
        notes.append("image size does not match metadata screenshot size")

    mapped_detections: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    image_size_tuple = (float(image_width or 0), float(image_height or 0))
    metadata_size_tuple = (float(metadata_width or 0), float(metadata_height or 0))

    for index, detection in enumerate(detections):
        detection_notes: list[str] = []
        class_id = class_id_of(detection)
        confidence = confidence_of(detection)
        validity, bbox, center_x, center_y = detection_validity(detection, image_size_tuple[0], image_size_tuple[1])
        detection_valid = all(validity.values())
        if not detection_valid:
            detection_notes.append("detection bbox or center invalid")

        scale_x = scale_y = None
        monitor_x = monitor_y = None
        window_x = window_y = None
        center_inside_window = False
        mapping_status = "metadata_missing"
        mapping_confidence = "none"

        can_compute = (
            metadata.status == "matched"
            and metadata.screenshot_size is not None
            and metadata.window_rect is not None
            and metadata.monitor_rect is not None
            and center_x is not None
            and center_y is not None
            and image_size_tuple[0] > 0
            and image_size_tuple[1] > 0
            and metadata_size_tuple[0] > 0
            and metadata_size_tuple[1] > 0
        )

        if metadata.status == "missing":
            mapping_status = "metadata_missing"
        elif metadata.status == "duplicate":
            mapping_status = "metadata_duplicate"
        elif metadata.status == "invalid_metadata":
            mapping_status = "invalid_metadata"
        elif not detection_valid:
            mapping_status = "detection_invalid"
        elif can_compute:
            scale_x, scale_y, monitor_x, monitor_y, window_x, window_y = geometry_values(
                center_x,
                center_y,
                image_size_tuple,
                metadata_size_tuple,
                metadata.monitor_rect,
                metadata.window_rect,
            )
            center_inside_window = 0 <= window_x < metadata.window_rect.width and 0 <= window_y < metadata.window_rect.height
            mapping_status = "mapped"
            if size_match and rect_valid:
                mapping_confidence = "high"
            elif size_match:
                mapping_confidence = "medium"
            else:
                mapping_confidence = "low"
                mapping_status = "size_mismatch"
        else:
            mapping_status = "geometry_invalid"

        bbox_out = bbox or {"x1": None, "y1": None, "x2": None, "y2": None}
        mapped_detection = {
            "detection_index": index,
            "class_id": class_id,
            "confidence": confidence,
            "bbox_xyxy": {key: round_float(value) for key, value in bbox_out.items()},
            "bbox_xywh": detection.get("bbox_xywh", {}),
            "image_pixel_center": {"x": round_float(center_x), "y": round_float(center_y)},
            "monitor_relative_center": {"x": round_float(monitor_x), "y": round_float(monitor_y)},
            "window_relative_center": {"x": round_float(window_x), "y": round_float(window_y)},
            "validity": {
                "center_inside_image": validity["center_inside_image"],
                "center_inside_bbox": validity["center_inside_bbox"],
                "bbox_inside_image": validity["bbox_inside_image"],
                "center_inside_window": center_inside_window,
                "is_screen_coordinate": False,
                "is_mouse_coordinate": False,
                "is_click_target": False,
            },
            "mapping_status": mapping_status,
            "mapping_confidence": mapping_confidence,
            "notes": "; ".join(detection_notes + notes),
        }
        mapped_detections.append(mapped_detection)
        geometry_rows.append(
            {
                "source_image_stem": source_stem,
                "detection_json": str(phase4_path),
                "metadata_path": str(metadata.path) if metadata.path else "",
                "detection_index": index,
                "class_id": class_id,
                "confidence": confidence,
                "image_width": image_width,
                "image_height": image_height,
                "image_center_x": round_float(center_x),
                "image_center_y": round_float(center_y),
                "monitor_relative_x": round_float(monitor_x),
                "monitor_relative_y": round_float(monitor_y),
                "window_relative_x": round_float(window_x),
                "window_relative_y": round_float(window_y),
                "bbox_x1": round_float(bbox_out["x1"]),
                "bbox_y1": round_float(bbox_out["y1"]),
                "bbox_x2": round_float(bbox_out["x2"]),
                "bbox_y2": round_float(bbox_out["y2"]),
                "center_inside_image": validity["center_inside_image"],
                "center_inside_bbox": validity["center_inside_bbox"],
                "bbox_inside_image": validity["bbox_inside_image"],
                "center_inside_window": center_inside_window,
                "size_match": size_match,
                "rect_valid": rect_valid,
                "mapping_status": mapping_status,
                "mapping_confidence": mapping_confidence,
                "notes": "; ".join(detection_notes + notes),
            }
        )

    mapped_json = {
        "phase": PHASE_NAME,
        "source": {
            "phase4_json": str(phase4_path),
            "source_image_path": source_image_path,
            "source_image_stem": source_stem,
            "metadata_path": str(metadata.path) if metadata.path else None,
        },
        "metadata_match": {
            "status": metadata.status,
            "metadata_candidates_count": len(metadata.candidates),
            "size_match": size_match,
            "rect_valid": rect_valid,
        },
        "coordinate_spaces": {
            "image_pixel": True,
            "monitor_relative": metadata.status == "matched",
            "window_relative": metadata.status == "matched",
            "screen_coordinate": False,
            "mouse_coordinate": False,
            "click_target": False,
        },
        "geometry": {
            "image_size": {"width": image_width, "height": image_height},
            "metadata_screenshot_size": {"width": metadata_width, "height": metadata_height},
            "monitor_rect": metadata.monitor_rect.to_dict() if metadata.monitor_rect else None,
            "window_rect": metadata.window_rect.to_dict() if metadata.window_rect else None,
            "scale": {
                "x": round_float(metadata_size_tuple[0] / image_size_tuple[0]) if image_size_tuple[0] else None,
                "y": round_float(metadata_size_tuple[1] / image_size_tuple[1]) if image_size_tuple[1] else None,
            },
        },
        "detections": mapped_detections,
    }

    match_row = {
        "detection_json": str(phase4_path),
        "source_image_stem": source_stem,
        "source_image_path": source_image_path or "",
        "metadata_candidates_count": len(metadata.candidates),
        "metadata_path": str(metadata.path) if metadata.path else "",
        "match_status": metadata.status,
        "image_width": image_width,
        "image_height": image_height,
        "metadata_screenshot_width": metadata_width,
        "metadata_screenshot_height": metadata_height,
        "size_match": size_match,
        "has_window_rect": has_window_rect,
        "has_monitor_rect": has_monitor_rect,
        "rect_valid": rect_valid,
        "detection_count": len(detections),
        "notes": "; ".join(notes),
    }
    return mapped_json, geometry_rows, match_row


def write_run_config(args: argparse.Namespace, timestamp: str) -> None:
    write_json(
        args.output_dir / "run_config.json",
        {
            "phase": PHASE_NAME,
            "phase4_json_dir": str(args.phase4_json_dir),
            "metadata_dir": str(args.metadata_dir),
            "output_dir": str(args.output_dir),
            "metadata_recursive": args.metadata_recursive,
            "tolerance_px": args.tolerance_px,
            "review_images": args.review_images,
            "review_images_enabled": args.review_images,
            "overwrite": args.overwrite,
            "timestamp": timestamp,
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "script_path": str(Path(__file__)),
            "command_args": jsonable_args(args),
            "safety_boundary_confirmed": True,
            "safety_boundary": SAFETY_BOUNDARY,
        },
    )


def summarize(
    phase4_count: int,
    match_rows: list[dict[str, Any]],
    geometry_rows: list[dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    def count_match(status: str) -> int:
        return sum(1 for row in match_rows if row["match_status"] == status)

    return {
        "phase": PHASE_NAME,
        "total_phase4_json_count": phase4_count,
        "total_detection_count": len(geometry_rows),
        "metadata_matched_count": count_match("matched"),
        "metadata_missing_count": count_match("missing"),
        "metadata_duplicate_count": count_match("duplicate"),
        "metadata_invalid_count": count_match("invalid_metadata"),
        "size_match_count": sum(1 for row in match_rows if row["size_match"] is True),
        "size_mismatch_count": sum(1 for row in match_rows if row["size_match"] is False),
        "rect_valid_count": sum(1 for row in match_rows if row["rect_valid"] is True),
        "rect_invalid_count": sum(1 for row in match_rows if row["rect_valid"] is False),
        "mapped_detection_count": sum(1 for row in geometry_rows if row["mapping_status"] == "mapped"),
        "detection_invalid_count": sum(1 for row in geometry_rows if row["mapping_status"] == "detection_invalid"),
        "center_inside_image_count": sum(1 for row in geometry_rows if row["center_inside_image"] is True),
        "center_inside_bbox_count": sum(1 for row in geometry_rows if row["center_inside_bbox"] is True),
        "bbox_inside_image_count": sum(1 for row in geometry_rows if row["bbox_inside_image"] is True),
        "center_inside_window_count": sum(1 for row in geometry_rows if row["center_inside_window"] is True),
        "output_dir": str(args.output_dir),
        "phase4_json_dir": str(args.phase4_json_dir),
        "metadata_dir": str(args.metadata_dir),
        "review_images_enabled": args.review_images,
        "safety_boundary_confirmed": True,
        "safety_boundary": SAFETY_BOUNDARY,
    }


def main() -> int:
    args = parse_args()
    timestamp = now_iso()
    if not args.phase4_json_dir.exists() or not args.phase4_json_dir.is_dir():
        print(f"ERROR: phase4 json directory not found: {args.phase4_json_dir}", file=sys.stderr)
        return 2
    if not args.metadata_dir.exists() or not args.metadata_dir.is_dir():
        print(f"ERROR: metadata directory not found: {args.metadata_dir}", file=sys.stderr)
        return 2
    try:
        prepare_output_dir(args.output_dir, args.overwrite)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    phase4_paths = sorted(path for path in args.phase4_json_dir.glob("*.json") if path.is_file())
    metadata_index = build_metadata_index(args.metadata_dir, args.metadata_recursive)
    match_rows: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []

    for phase4_path in phase4_paths:
        try:
            mapped_json, rows, match_row = process_phase4_json(phase4_path, args, metadata_index)
            mapped_path = args.output_dir / "mapped_json" / f"{phase4_path.stem}.phase5_mapped.json"
            write_json(mapped_path, mapped_json)
            if args.review_images:
                notes: list[str] = []
                monitor = None
                window = None
                geometry = mapped_json.get("geometry", {})
                if isinstance(geometry, dict):
                    monitor = parse_rect(geometry.get("monitor_rect"))
                    window = parse_rect(geometry.get("window_rect"))
                draw_review_image(
                    load_json(phase4_path),
                    mapped_json["detections"],
                    window,
                    monitor,
                    args.output_dir / "review_images" / f"{phase4_path.stem}_geometry_review.png",
                    notes,
                )
                if notes:
                    match_row["notes"] = (str(match_row.get("notes") or "") + "; " + "; ".join(notes)).strip("; ")
            geometry_rows.extend(rows)
            match_rows.append(match_row)
        except Exception as exc:
            stem = phase4_path.stem
            match_rows.append(
                {
                    "detection_json": str(phase4_path),
                    "source_image_stem": stem,
                    "source_image_path": "",
                    "metadata_candidates_count": 0,
                    "metadata_path": "",
                    "match_status": "invalid_metadata",
                    "image_width": "",
                    "image_height": "",
                    "metadata_screenshot_width": "",
                    "metadata_screenshot_height": "",
                    "size_match": False,
                    "has_window_rect": False,
                    "has_monitor_rect": False,
                    "rect_valid": False,
                    "detection_count": 0,
                    "notes": str(exc),
                }
            )

    match_fields = [
        "detection_json",
        "source_image_stem",
        "source_image_path",
        "metadata_candidates_count",
        "metadata_path",
        "match_status",
        "image_width",
        "image_height",
        "metadata_screenshot_width",
        "metadata_screenshot_height",
        "size_match",
        "has_window_rect",
        "has_monitor_rect",
        "rect_valid",
        "detection_count",
        "notes",
    ]
    geometry_fields = [
        "source_image_stem",
        "detection_json",
        "metadata_path",
        "detection_index",
        "class_id",
        "confidence",
        "image_width",
        "image_height",
        "image_center_x",
        "image_center_y",
        "monitor_relative_x",
        "monitor_relative_y",
        "window_relative_x",
        "window_relative_y",
        "bbox_x1",
        "bbox_y1",
        "bbox_x2",
        "bbox_y2",
        "center_inside_image",
        "center_inside_bbox",
        "bbox_inside_image",
        "center_inside_window",
        "size_match",
        "rect_valid",
        "mapping_status",
        "mapping_confidence",
        "notes",
    ]
    write_csv(args.output_dir / "metadata_match_report.csv", match_rows, match_fields)
    write_csv(args.output_dir / "geometry_summary.csv", geometry_rows, geometry_fields)
    summary = summarize(len(phase4_paths), match_rows, geometry_rows, args)
    write_json(args.output_dir / "phase5_summary.json", summary)
    write_run_config(args, timestamp)

    print(f"phase={PHASE_NAME}")
    print(f"phase4_json={len(phase4_paths)}")
    print(f"detections={len(geometry_rows)}")
    print(f"metadata_matched={summary['metadata_matched_count']}")
    print(f"metadata_missing={summary['metadata_missing_count']}")
    print(f"metadata_duplicate={summary['metadata_duplicate_count']}")
    print(f"metadata_invalid={summary['metadata_invalid_count']}")
    print(f"mapped_detections={summary['mapped_detection_count']}")
    print(f"output_dir={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
