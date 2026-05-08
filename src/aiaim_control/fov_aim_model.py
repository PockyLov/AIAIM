from __future__ import annotations

import math
from typing import Any


def compute_focal_px(
    screen_width: int,
    screen_height: int,
    horizontal_fov_deg: float,
    vertical_fov_deg: float,
) -> dict[str, float]:
    if screen_width <= 0 or screen_height <= 0:
        raise ValueError("screen_width and screen_height must be positive")
    if horizontal_fov_deg <= 0 or horizontal_fov_deg >= 180:
        raise ValueError("horizontal_fov_deg must be between 0 and 180")
    if vertical_fov_deg <= 0 or vertical_fov_deg >= 180:
        raise ValueError("vertical_fov_deg must be between 0 and 180")
    horizontal_fov_rad = math.radians(horizontal_fov_deg)
    vertical_fov_rad = math.radians(vertical_fov_deg)
    return {
        "focal_x": (float(screen_width) / 2.0) / math.tan(horizontal_fov_rad / 2.0),
        "focal_y": (float(screen_height) / 2.0) / math.tan(vertical_fov_rad / 2.0),
    }


def compute_angle_delta_deg(
    delta_x_px: float,
    delta_y_px: float,
    focal_x: float,
    focal_y: float,
) -> dict[str, float]:
    if focal_x <= 0 or focal_y <= 0:
        raise ValueError("focal_x and focal_y must be positive")
    return {
        "x": math.degrees(math.atan(float(delta_x_px) / float(focal_x))),
        "y": math.degrees(math.atan(float(delta_y_px) / float(focal_y))),
    }


def compute_fov_relative_move(
    target_center_x: float,
    target_center_y: float,
    crosshair_x: float,
    crosshair_y: float,
    screen_width: int,
    screen_height: int,
    horizontal_fov_deg: float,
    vertical_fov_deg: float,
    counts_per_degree: float,
    global_gain: float = 1.0,
) -> dict[str, Any]:
    if counts_per_degree <= 0:
        raise ValueError("counts_per_degree must be positive")
    if global_gain <= 0:
        raise ValueError("global_gain must be positive")
    delta_x = float(target_center_x) - float(crosshair_x)
    delta_y = float(target_center_y) - float(crosshair_y)
    focal = compute_focal_px(screen_width, screen_height, horizontal_fov_deg, vertical_fov_deg)
    angles = compute_angle_delta_deg(delta_x, delta_y, focal["focal_x"], focal["focal_y"])
    mouse_dx = angles["x"] * float(counts_per_degree) * float(global_gain)
    mouse_dy = angles["y"] * float(counts_per_degree) * float(global_gain)
    return {
        "target_delta_px": {"dx": delta_x, "dy": delta_y},
        "focal_px": {"x": focal["focal_x"], "y": focal["focal_y"]},
        "angle_delta_deg": angles,
        "counts_per_degree": float(counts_per_degree),
        "global_gain": float(global_gain),
        "planned_relative_move_dxdy": {"dx": mouse_dx, "dy": mouse_dy},
        "rounded_relative_move_dxdy": {"dx": int(round(mouse_dx)), "dy": int(round(mouse_dy))},
    }
