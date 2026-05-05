from __future__ import annotations

import argparse
import csv
import json
import logging
import shutil
from pathlib import Path
from typing import Any


MANIFEST_FIELDS = [
    "filename",
    "source_image_path",
    "source_metadata_path",
    "selected_image_path",
    "aimlab_window_title",
    "foreground_window_title",
    "screenshot_width",
    "screenshot_height",
    "window_rect",
    "monitor_rect",
    "capture_mode",
    "capture_elapsed_ms",
    "window_monitor_coverage_ratio",
    "selected",
    "skip_reason",
]


def configure_logger(project_root: Path) -> logging.Logger:
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("aiaim.phase2.dataset_prep")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.FileHandler(log_dir / "dataset_prep.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def load_metadata(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def compact_json(value: Any) -> str:
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and value > 0


def evaluate_png(png_path: Path, metadata_path: Path) -> tuple[bool, str, dict[str, Any] | None]:
    if not metadata_path.exists():
        return False, "missing_metadata", None
    metadata = load_metadata(metadata_path)
    if metadata is None:
        return False, "invalid_metadata_json", None
    if metadata.get("aimlab_window_found") is not True:
        return False, "aimlab_window_not_found", metadata
    if metadata.get("is_foreground") is not True:
        return False, "non_foreground", metadata
    if metadata.get("blocked") is True:
        return False, "blocked", metadata
    if not is_positive_number(metadata.get("screenshot_width")) or not is_positive_number(
        metadata.get("screenshot_height")
    ):
        return False, "invalid_size", metadata
    metadata_image = metadata.get("image_path")
    metadata_image_exists = bool(metadata_image and Path(str(metadata_image)).exists())
    if not metadata_image_exists and not png_path.exists():
        return False, "image_path_missing", metadata
    return True, "", metadata


def build_row(
    *,
    png_path: Path,
    metadata_path: Path,
    selected_path: Path | None,
    selected: bool,
    skip_reason: str,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    metadata = metadata or {}
    return {
        "filename": png_path.name,
        "source_image_path": str(png_path),
        "source_metadata_path": str(metadata_path),
        "selected_image_path": str(selected_path) if selected_path else "",
        "aimlab_window_title": metadata.get("aimlab_window_title", ""),
        "foreground_window_title": metadata.get("foreground_window_title", ""),
        "screenshot_width": metadata.get("screenshot_width", ""),
        "screenshot_height": metadata.get("screenshot_height", ""),
        "window_rect": compact_json(metadata.get("window_rect")),
        "monitor_rect": compact_json(metadata.get("monitor_rect")),
        "capture_mode": metadata.get("capture_mode", ""),
        "capture_elapsed_ms": metadata.get("capture_elapsed_ms", ""),
        "window_monitor_coverage_ratio": metadata.get("window_monitor_coverage_ratio", ""),
        "selected": str(selected).lower(),
        "skip_reason": skip_reason,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare Phase 2 selected AIMLAB screenshot dataset.")
    parser.add_argument("--source", type=Path, default=Path("data/raw/screenshots"))
    parser.add_argument("--out", type=Path, default=Path("data/selected/phase2_yellow_ball"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path.cwd()
    logger = configure_logger(project_root)
    source = args.source
    out_dir = args.out
    manifest_path = out_dir / "dataset_manifest.csv"

    png_paths = sorted(source.glob("*.png"))
    if args.limit is not None:
        png_paths = png_paths[: args.limit]

    stats = {
        "scanned_png_count": 0,
        "selected_count": 0,
        "skipped_count": 0,
        "missing_metadata_count": 0,
        "blocked_count": 0,
        "non_foreground_count": 0,
        "invalid_size_count": 0,
    }
    rows: list[dict[str, Any]] = []

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    for png_path in png_paths:
        stats["scanned_png_count"] += 1
        metadata_path = png_path.with_suffix(".json")
        selected, skip_reason, metadata = evaluate_png(png_path, metadata_path)
        selected_path = out_dir / png_path.name if selected else None

        if selected:
            stats["selected_count"] += 1
            if not args.dry_run:
                shutil.copy2(png_path, selected_path)
        else:
            stats["skipped_count"] += 1
            if skip_reason == "missing_metadata":
                stats["missing_metadata_count"] += 1
            elif skip_reason == "blocked":
                stats["blocked_count"] += 1
            elif skip_reason == "non_foreground":
                stats["non_foreground_count"] += 1
            elif skip_reason == "invalid_size":
                stats["invalid_size_count"] += 1

        rows.append(
            build_row(
                png_path=png_path,
                metadata_path=metadata_path,
                selected_path=selected_path,
                selected=selected,
                skip_reason=skip_reason,
                metadata=metadata,
            )
        )

    if not args.dry_run:
        with manifest_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    logger.info("prepare_phase2_dataset dry_run=%s stats=%s", args.dry_run, stats)
    for key, value in stats.items():
        print(f"{key}={value}")
    if args.dry_run:
        print("dry_run=true manifest_written=false")
    else:
        print(f"manifest_path={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
