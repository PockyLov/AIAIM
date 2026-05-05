from __future__ import annotations

import ctypes
import platform
from ctypes import wintypes
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_dict(self) -> dict[str, int]:
        return asdict(self) | {"width": self.width, "height": self.height}


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    title: str
    rect: Rect
    is_foreground: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "hwnd": self.hwnd,
            "title": self.title,
            "rect": self.rect.to_dict(),
            "is_foreground": self.is_foreground,
        }


def _require_windows() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("Phase 1 collector requires Windows foreground-window APIs.")


def _user32() -> ctypes.WinDLL:
    _require_windows()
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    return user32


def _normalized(value: str) -> str:
    return "".join(value.lower().split())


def _matches_title(title: str, keywords: Iterable[str]) -> bool:
    normalized_title = _normalized(title)
    return any(_normalized(keyword) in normalized_title for keyword in keywords if keyword)


def get_window_title(hwnd: int) -> str:
    user32 = _user32()
    length = user32.GetWindowTextLengthW(wintypes.HWND(hwnd))
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(wintypes.HWND(hwnd), buffer, length + 1)
    return buffer.value


def get_window_rect(hwnd: int) -> Rect:
    user32 = _user32()
    rect = wintypes.RECT()
    if not user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect)):
        raise ctypes.WinError(ctypes.get_last_error())
    return Rect(rect.left, rect.top, rect.right, rect.bottom)


def get_foreground_window_info() -> WindowInfo | None:
    user32 = _user32()
    hwnd = int(user32.GetForegroundWindow())
    if hwnd == 0:
        return None
    return WindowInfo(
        hwnd=hwnd,
        title=get_window_title(hwnd),
        rect=get_window_rect(hwnd),
        is_foreground=True,
    )


def find_aimlab_window(title_keywords: Iterable[str]) -> WindowInfo | None:
    user32 = _user32()
    foreground_hwnd = int(user32.GetForegroundWindow())
    matches: list[WindowInfo] = []

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd: int, _: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        title = get_window_title(hwnd)
        if not title or not _matches_title(title, title_keywords):
            return True
        try:
            rect = get_window_rect(hwnd)
        except OSError:
            return True
        matches.append(
            WindowInfo(
                hwnd=int(hwnd),
                title=title,
                rect=rect,
                is_foreground=int(hwnd) == foreground_hwnd,
            )
        )
        return True

    user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    if not user32.EnumWindows(EnumWindowsProc(callback), 0):
        raise ctypes.WinError(ctypes.get_last_error())

    for window in matches:
        if window.is_foreground:
            return window
    return matches[0] if matches else None
