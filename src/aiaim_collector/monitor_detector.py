from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

from .window_detector import Rect, WindowInfo, _require_windows


MONITOR_DEFAULTTONEAREST = 2
CCHDEVICENAME = 32


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * CCHDEVICENAME),
    ]


@dataclass(frozen=True)
class MonitorInfo:
    handle: int
    device_name: str
    monitor_rect: Rect
    work_rect: Rect
    is_primary: bool
    window_monitor_coverage_ratio: float

    def to_dict(self) -> dict[str, object]:
        return {
            "handle": self.handle,
            "device_name": self.device_name,
            "monitor_rect": self.monitor_rect.to_dict(),
            "work_rect": self.work_rect.to_dict(),
            "is_primary": self.is_primary,
            "window_monitor_coverage_ratio": self.window_monitor_coverage_ratio,
        }


def _rect_from_win(rect: wintypes.RECT) -> Rect:
    return Rect(rect.left, rect.top, rect.right, rect.bottom)


def _intersection_area(a: Rect, b: Rect) -> int:
    left = max(a.left, b.left)
    top = max(a.top, b.top)
    right = min(a.right, b.right)
    bottom = min(a.bottom, b.bottom)
    return max(0, right - left) * max(0, bottom - top)


def get_monitor_for_window(window: WindowInfo) -> MonitorInfo:
    _require_windows()
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    hmonitor_type = getattr(wintypes, "HMONITOR", wintypes.HANDLE)
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.MonitorFromWindow.restype = hmonitor_type
    user32.GetMonitorInfoW.argtypes = [hmonitor_type, ctypes.POINTER(MONITORINFOEXW)]
    user32.GetMonitorInfoW.restype = wintypes.BOOL
    monitor = user32.MonitorFromWindow(wintypes.HWND(window.hwnd), MONITOR_DEFAULTTONEAREST)
    if not monitor:
        raise ctypes.WinError(ctypes.get_last_error())

    info = MONITORINFOEXW()
    info.cbSize = ctypes.sizeof(MONITORINFOEXW)
    if not user32.GetMonitorInfoW(hmonitor_type(monitor), ctypes.byref(info)):
        raise ctypes.WinError(ctypes.get_last_error())

    monitor_rect = _rect_from_win(info.rcMonitor)
    work_rect = _rect_from_win(info.rcWork)
    intersection = _intersection_area(window.rect, monitor_rect)
    coverage = intersection / monitor_rect.area if monitor_rect.area else 0.0

    return MonitorInfo(
        handle=int(monitor),
        device_name=info.szDevice,
        monitor_rect=monitor_rect,
        work_rect=work_rect,
        is_primary=bool(info.dwFlags & 1),
        window_monitor_coverage_ratio=round(coverage, 6),
    )
