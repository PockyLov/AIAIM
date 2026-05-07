# Phase 8.1 FOV-based One-Shot Aim Runbook

## Goal

Phase 8.1 upgrades Phase 8 one-shot relative aim from a pixel-linear calibration model to a FOV angular model:

```text
pixel_delta -> FOV angle_delta -> mouse_count
```

It still sends at most one relative `SendInput` movement. It does not click, does not loop, does not target-lock, and does not perform closed-loop correction.

## Why Upgrade From Pixel-linear To FOV-angular

Phase 8 was accepted using `pixel_delta / px_per_mouse_count`, reducing distance from `78.3356px` to `10.9768px`. The remaining residual suggests that a camera/FOV angular model may better approximate how AIMLAB converts mouse counts into view rotation.

Phase 8.1 uses a pinhole camera model to estimate angular offset from monitor-center crosshair to the chosen YOLO target.

## Fixed Environment Parameters

Initial Phase 8.1 assumptions:

- AIMLAB true fullscreen / borderless fullscreen
- resolution: `1920x1080`
- monitor_rect: `0,0,1920,1080`
- crosshair / gameplay center: `960,540`
- mouse CPI/DPI: `800`
- AIMLAB Game Profile: `VALORANT`
- aspect ratio: `16:9`
- non-ADS Hipfire FOV:
  - `horizontal_fov_deg=103`
  - `vertical_fov_deg=70.53`
- `360° Distance = 44.614 cm`
- `Sensitivity = 0.366`
- `theoretical_counts_per_degree = 39.03`
- `global_gain = 1.0`

## Formula

Focal length in pixels:

```text
focal_x = (screen_width / 2) / tan(horizontal_fov_rad / 2)
focal_y = (screen_height / 2) / tan(vertical_fov_rad / 2)
```

Angle delta:

```text
angle_x_deg = degrees(atan(delta_x_px / focal_x))
angle_y_deg = degrees(atan(delta_y_px / focal_y))
```

Relative mouse counts:

```text
mouse_dx = angle_x_deg * counts_per_degree * global_gain
mouse_dy = angle_y_deg * counts_per_degree * global_gain
```

Sign convention matches the Phase 8 accepted sample:

- target left -> negative mouse dx
- target right -> positive mouse dx
- target down -> positive mouse dy
- target up -> negative mouse dy

## Dry-run Command

```powershell
.\.venv\Scripts\python.exe scripts\live_one_shot_fov_aim.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --conf 0.25 `
  --horizontal-fov-deg 103 `
  --vertical-fov-deg 70.53 `
  --screen-width 1920 `
  --screen-height 1080 `
  --counts-per-degree 39.03 `
  --global-gain 1.0 `
  --output-dir "D:\桌面desktop\AIAIM\runs\detect\phase8_1_fov_one_shot"
```

Dry-run should output a complete JSON result and should not attempt `SendInput`.

## Execute One-shot Command

```powershell
.\.venv\Scripts\python.exe scripts\live_one_shot_fov_aim.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --conf 0.25 `
  --horizontal-fov-deg 103 `
  --vertical-fov-deg 70.53 `
  --screen-width 1920 `
  --screen-height 1080 `
  --counts-per-degree 39.03 `
  --global-gain 1.0 `
  --execute-move `
  --confirm-local-aimlab-only `
  --output-dir "D:\桌面desktop\AIAIM\runs\detect\phase8_1_fov_one_shot"
```

Execute mode still sends at most one relative movement and then exits. After-frame capture is validation only and must not trigger a second move.

## Outputs

Default output root:

```text
runs/detect/phase8_1_fov_one_shot/
```

Each run writes:

- `before_screenshot.png` when capture succeeds
- `after_screenshot.png` when execute succeeds
- `before_review_image.png`
- `after_review_image.png` when after validation exists
- `phase8_1_result.json`
- `run_config.json`
- `phase8_1_summary.csv`

`phase8_1_result.json` includes FOV, focal length, angle delta, counts per degree, global gain, planned move, rounded move, SendInput status, after distance, and safety flags.

## Acceptance Criteria

Code-level acceptance:

- unit tests pass
- dry-run emits complete JSON without SendInput
- execute mode has exactly one guarded SendInput call
- no click implementation
- no loop / continuous control
- no second correction
- no target lock

Real-machine effect goal:

- `before_distance_to_crosshair_px >= 50`
- prefer `after_distance_to_crosshair_px <= 8`
- prefer `distance_reduction_ratio >= 0.90`

If after distance is `8-12px` but visibly close, record as partial improvement. Do not add closed-loop correction in Phase 8.1.

## Safety Boundary

Phase 8.1 forbids:

- clicking
- automatic clicking
- target lock
- looped movement
- closed-loop correction
- second movement after after-frame detection
- PID
- micro-step movement
- smooth movement
- process memory reading
- AIMLAB file modification
- anti-cheat bypass
- background automation
