from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from .monitor_detector import MonitorInfo


@dataclass(frozen=True)
class CaptureResult:
    image_path: Path
    screenshot_width: int
    screenshot_height: int
    capture_elapsed_ms: float


def capture_monitor(monitor: MonitorInfo, image_path: Path) -> CaptureResult:
    import mss
    import mss.tools

    rect = monitor.monitor_rect
    region = {
        "left": rect.left,
        "top": rect.top,
        "width": rect.width,
        "height": rect.height,
    }

    image_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with mss.mss() as sct:
        image = sct.grab(region)
        mss.tools.to_png(image.rgb, image.size, output=str(image_path))
    elapsed_ms = (time.perf_counter() - started) * 1000

    return CaptureResult(
        image_path=image_path,
        screenshot_width=region["width"],
        screenshot_height=region["height"],
        capture_elapsed_ms=round(elapsed_ms, 3),
    )
