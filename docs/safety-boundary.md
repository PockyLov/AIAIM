# Safety Boundary

AIAIM defaults to dry-run. Future real mouse movement and click behavior must be explicitly enabled, gated, logged, and reversible.

## Allowed Direction

The project may research local offline AIMLAB detection and control under staged, documented, user-visible conditions.

## Disallowed Direction

AIAIM must not be used for:

- Anti-cheat bypass
- Hidden automation
- Leaderboard farming
- Multiplayer cheating
- Bypassing safety checks
- Removing foreground validation
- Default real clicking

## Future Required Gates

Before real mouse movement or clicking can exist, the project must include:

- Explicit config switch
- Dry-run default
- AIMLAB foreground window verification
- Emergency stop mechanism
- Structured logging
- Rate limiting
- Phase report
- Runbook update
- Manual validation checklist

## Phase 0 Boundary

Phase 0 does not implement screenshot capture, foreground detection, YOLO, data collection, coordinate mapping, mouse movement, clicking, or real automation.

## Phase 2 Boundary

Phase 2 allows:

- Data organization
- Human annotation guidelines
- OpenCV offline pre-labeling assistance
- YOLO label format preparation
- Train / val / test dataset splitting
- `data.yaml` generation
- Dataset validation

Phase 2 forbids:

- YOLO training
- YOLO inference
- Real-time detection
- Mouse movement
- Mouse clicking
- Coordinate mapping
- Auto-aim
- Closed-loop automation
- Anti-cheat bypass
- AIMLAB background window screenshot expansion

OpenCV pre-labeling only processes static images already saved under the dataset folders. It does not connect to AIMLAB real-time video, does not connect to the Phase 1 collector, and does not drive any input device.

## Phase 4 Boundary

Phase 4 allows:

- Loading the Phase 3 `best.pt` model.
- Offline detect-only inference on saved PNG/JPG/JPEG images.
- Per-image detection JSON output.
- Clean review image output.
- `summary.csv` output.
- `run_config.json` output.
- Input-image pixel coordinate contract.
- Bbox and center validity checks.
- Optional metadata copying into `source_metadata` for reference only.

Phase 4 forbids:

- Real-time screenshots.
- AIMLAB live screen connection.
- Phase 1 collector live loop integration.
- Mouse movement.
- Mouse clicking.
- Mouse target generation.
- Click target generation.
- Auto-aim.
- Closed-loop automation.
- Anti-cheat bypass.
- Phase 5 coordinate mapping.
- Screen coordinate mapping.
- Mouse coordinate mapping.
- DPI or multi-monitor real-time coordinate conversion.
- YOLO retraining.

Phase 4 coordinate outputs are input image pixel coordinates only. They are not screen coordinates, not mouse coordinates, not AIMLAB window coordinates, and not click targets.

Metadata in Phase 4 is reference-only. It must not be used to produce screen coordinates, mouse coordinates, click targets, or Phase 5 mapping results.

## Phase 5 Boundary

Phase 5 allows:

- Reading Phase 4 detection JSON.
- Reading Phase 1 metadata JSON.
- Matching metadata by source image stem.
- Validating screenshot size, monitor rect, window rect, bbox, and center.
- Computing image-pixel centers.
- Computing monitor-relative centers.
- Computing window-relative centers.
- Writing mapped JSON.
- Writing metadata and geometry reports.
- Writing offline geometry review images.

Phase 5 forbids:

- Real-time screenshots.
- AIMLAB live screen connection.
- Phase 1 collector live loop integration.
- Mouse movement.
- Mouse clicking.
- Mouse target output.
- Click target output.
- Auto-aim.
- Closed-loop automation.
- Anti-cheat bypass.
- Treating image-pixel coordinates as screen coordinates.
- Treating image-pixel coordinates as mouse coordinates.
- DPI or multi-monitor real-time conversion.
- Advancing to Phase 6.

Phase 5 may output only these coordinate spaces:

- `image_pixel`
- `monitor_relative`
- `window_relative`

Phase 5 outputs must keep screen-coordinate, mouse-coordinate, and click-target flags false. Phase 5 geometry is offline validation evidence only and must not drive input devices.

## Phase 5.5 Boundary

Phase 5.5 allows:

- Reviewing existing Phase 1 metadata.
- Reviewing existing Phase 5 geometry outputs.
- Documenting the client area / content area coordinate contract before Phase 6 planning.
- Confirming `image_pixel` as the original trusted YOLO detection coordinate.
- Confirming `monitor_relative` as the main coordinate basis candidate for future live read-only detection in the current full-monitor capture mode.
- Recording raw `window_rect`, `window_relative`, and `work_rect` as debug / review / warning information only.

Phase 5.5 forbids:

- Realtime screenshots.
- AIMLAB live screen connection.
- Phase 1 collector live loop integration.
- Mouse movement.
- Mouse clicking.
- Mouse target output.
- Click target output.
- Auto-aim.
- Closed-loop automation.
- Anti-cheat bypass.
- Process memory reading.
- Complex multi-monitor adaptation.
- Complex UI calibration.
- Phase 6 implementation.

Phase 5.5 confirms that raw `window_rect` can include Windows windowed fullscreen / maximized-window outer bounds of about `8 px`. This value must not be used as an action coordinate source. Future Phase 6 work, if started, must begin as live read-only detection and must keep mouse movement and clicking out of scope.

## Phase 6 Boundary

Phase 6 allows:

- AIMLAB foreground-window validation.
- Full-monitor screenshot capture only after the foreground gate passes.
- Loading the Phase 3 YOLO `best.pt` model.
- Live read-only detection on the current monitor screenshot.
- Single-frame detection.
- Finite-loop detection with a fixed maximum frame count.
- Per-frame detection JSON output.
- Clean review image output.
- `live_summary.csv` output.
- `phase6_summary.json` and `run_config.json` output.
- `image_pixel` and `monitor_relative` detection coordinates.

Phase 6 forbids:

- Mouse movement.
- Mouse clicking.
- Mouse target output.
- Click target output.
- Auto-aim.
- Target lock.
- Closed-loop automation.
- Anti-cheat bypass.
- Process memory reading.
- Injection into AIMLAB.
- AIMLAB file modification.
- Infinite control loops.
- Phase 7 implementation.

Phase 6 detection coordinates are not action coordinates. Outputs must keep `is_screen_coordinate=false`, `is_mouse_coordinate=false`, `is_click_target=false`, and `action_authorized=false`.

Direct cursor positioning is outside Phase 6 and may only be discussed in a later phase with separate safety gates.

## Phase 7 Boundary

Phase 7 allows:

- AIMLAB foreground validation.
- One monitor screenshot.
- One YOLO detection pass.
- One primary target selection.
- Dry-run planned cursor output.
- Direct Windows cursor positioning only when all explicit gates pass.
- Structured JSON, summary, and review image output.

Phase 7 real movement requires:

- config `allow_mouse_move=true`
- CLI `--execute-move`
- CLI `--confirm-local-aimlab-only`
- AIMLAB foreground gate passed
- chosen target exists
- planned cursor position is inside the AIMLAB monitor rect
- config `allow_click=false`
- config `allow_loop=false`
- config `allow_closed_loop=false`

Phase 7 forbids:

- Mouse clicking.
- Click target output.
- Continuous movement loops.
- Target lock.
- Auto-aim loops.
- Move-detect-move correction.
- Closed-loop automation.
- Anti-cheat bypass.
- Process memory reading.
- Process injection.
- AIMLAB file modification.
- Background automation.

Phase 7 does not implement clicking. Phase 7 movement is one-shot only and defaults to dry-run.

Emergency stop for Phase 7 is Ctrl+C during `--start-delay-sec`, before the one-shot movement attempt. Phase 7 must not introduce a persistent movement loop.

## Phase 7.5 Boundary

Phase 7.5 allows:

- AIMLAB foreground validation.
- One before screenshot.
- One before YOLO detection pass.
- One reference target selection by nearest-to-crosshair.
- One fixed relative mouse movement using Windows `SendInput` only when all gates pass.
- One after screenshot if movement executes.
- One after YOLO detection pass.
- Conservative before / after target matching.
- `px_per_mouse_count` estimation when matching succeeds.
- JSON, CSV, and review image output.

Phase 7.5 real movement requires:

- config `allow_relative_mouse_move=true`
- CLI `--execute-relative-move`
- CLI `--confirm-local-aimlab-only`
- AIMLAB foreground gate passed
- config `allow_click=false`
- config `allow_loop=false`
- config `allow_closed_loop=false`
- relative dx/dy inside configured safety limits
- before reference target exists

Phase 7.5 forbids:

- Mouse clicking.
- Auto-aim.
- Target lock.
- Looped movement.
- Closed-loop correction.
- A second movement after after-frame detection.
- Anti-cheat bypass.
- Process memory reading.
- Process injection.
- AIMLAB file modification.
- Background automation.

Phase 7.5 is feasibility evidence only. It must not become automatic aiming.


## Phase 8 Boundary

Phase 8 allows:

- AIMLAB foreground validation.
- One before screenshot.
- One before YOLO detection pass.
- One target selection by nearest-to-crosshair.
- One planned relative mouse movement computed from Phase 7.5 calibration.
- One Windows `SendInput` relative movement only when all gates pass.
- One after screenshot for validation only.
- JSON, CSV, and review image output.

Phase 8 real movement requires:

- config `allow_relative_mouse_move=true`
- CLI `--execute-relative-aim`
- CLI `--confirm-local-aimlab-only`
- AIMLAB foreground gate passed
- config `allow_click=false`
- config `allow_loop=false`
- config `allow_closed_loop=false`
- before target exists
- non-zero calibration values
- rounded relative dx/dy inside configured limits

Phase 8 forbids:

- Mouse clicking.
- Automatic clicking.
- Target lock.
- Looped movement.
- Closed-loop correction.
- A second movement after after-frame detection.
- PID, micro-step, or smoothing movement.
- Anti-cheat bypass.
- Process memory reading.
- Process injection.
- AIMLAB file modification.
- Background automation.
