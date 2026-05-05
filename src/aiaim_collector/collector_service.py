from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .metadata_writer import local_timestamp, safe_timestamp_for_filename, write_metadata
from .monitor_detector import MonitorInfo, get_monitor_for_window
from .screen_capture import CaptureResult, capture_monitor
from .window_detector import WindowInfo, find_aimlab_window, get_foreground_window_info


@dataclass(frozen=True)
class CollectorSettings:
    project_root: Path
    title_keywords: tuple[str, ...] = ("aimlab", "aim lab")
    output_dir: Path | None = None
    fullscreen_warning_threshold: float = 0.95

    @property
    def screenshot_dir(self) -> Path:
        return self.output_dir or self.project_root / "data" / "raw" / "screenshots"


class CollectorService:
    def __init__(self, settings: CollectorSettings, logger: logging.Logger) -> None:
        self.settings = settings
        self.logger = logger

    def capture_once(self, capture_mode: str) -> dict[str, Any]:
        timestamp = local_timestamp()
        stem = f"{safe_timestamp_for_filename(timestamp)}_{capture_mode}"
        image_path = self.settings.screenshot_dir / f"{stem}.png"
        metadata_path = self.settings.screenshot_dir / f"{stem}.json"

        attempt_started = time.perf_counter()
        window: WindowInfo | None = None
        foreground: WindowInfo | None = None
        monitor: MonitorInfo | None = None
        capture: CaptureResult | None = None
        blocked = False
        blocked_reason = ""
        warning = ""

        try:
            foreground = get_foreground_window_info()
            window = find_aimlab_window(self.settings.title_keywords)
            if window is None:
                blocked = True
                blocked_reason = "aimlab_window_not_found"
            else:
                monitor = get_monitor_for_window(window)
                if not window.is_foreground:
                    blocked = True
                    blocked_reason = "aimlab_not_foreground"
                elif monitor.window_monitor_coverage_ratio < self.settings.fullscreen_warning_threshold:
                    warning = (
                        "aimlab_window_coverage_below_fullscreen_threshold:"
                        f"{monitor.window_monitor_coverage_ratio}"
                    )

            if not blocked and monitor is not None:
                capture = capture_monitor(monitor, image_path)
        except Exception as exc:  # noqa: BLE001 - metadata must capture unexpected gate/capture failures.
            blocked = True
            blocked_reason = f"collector_error:{type(exc).__name__}:{exc}"
            self.logger.exception("collector attempt failed")

        elapsed_ms = round((time.perf_counter() - attempt_started) * 1000, 3)
        metadata = self._build_metadata(
            timestamp=timestamp,
            capture_mode=capture_mode,
            window=window,
            foreground=foreground,
            monitor=monitor,
            capture=capture,
            blocked=blocked,
            blocked_reason=blocked_reason,
            warning=warning,
            elapsed_ms=elapsed_ms,
        )
        write_metadata(metadata, metadata_path)

        if blocked:
            self.logger.warning("capture blocked reason=%s metadata=%s", blocked_reason, metadata_path)
        else:
            self.logger.info("capture saved image=%s metadata=%s warning=%s", image_path, metadata_path, warning)

        return metadata

    def _build_metadata(
        self,
        *,
        timestamp: str,
        capture_mode: str,
        window: WindowInfo | None,
        foreground: WindowInfo | None,
        monitor: MonitorInfo | None,
        capture: CaptureResult | None,
        blocked: bool,
        blocked_reason: str,
        warning: str,
        elapsed_ms: float,
    ) -> dict[str, Any]:
        return {
            "phase": "Phase 1",
            "timestamp": timestamp,
            "image_path": str(capture.image_path) if capture else None,
            "capture_mode": capture_mode,
            "aimlab_window_found": window is not None,
            "is_foreground": bool(window and window.is_foreground),
            "blocked": blocked,
            "blocked_reason": blocked_reason,
            "warning": warning,
            "aimlab_window_title": window.title if window else None,
            "foreground_window_title": foreground.title if foreground else None,
            "window_rect": window.rect.to_dict() if window else None,
            "monitor_rect": monitor.monitor_rect.to_dict() if monitor else None,
            "monitor": monitor.to_dict() if monitor else None,
            "screenshot_width": capture.screenshot_width if capture else None,
            "screenshot_height": capture.screenshot_height if capture else None,
            "capture_elapsed_ms": capture.capture_elapsed_ms if capture else None,
            "attempt_elapsed_ms": elapsed_ms,
            "window_monitor_coverage_ratio": (
                monitor.window_monitor_coverage_ratio if monitor else None
            ),
        }
