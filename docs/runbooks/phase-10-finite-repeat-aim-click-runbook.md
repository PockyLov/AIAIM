# Phase 10 Finite Repeat Aim + Click Runbook

## Goal

Phase 10 repeats the accepted Phase 9 one-shot aim + click step for a finite number of iterations. It is bounded by `max_iterations` and `max_duration_sec`.

It is not a Hotkey Runner, GUI, background automation, target lock, PID controller, closed loop correction, or infinite loop.

## Safety Boundary

Real action requires all three flags:

- `--execute-move`
- `--allow-click`
- `--confirm-local-aimlab-only`

Every iteration checks AIMLAB foreground, takes a fresh screenshot, runs fresh detection, performs at most one relative `SendInput` move, takes an after screenshot, and clicks at most once if `after_distance_to_crosshair_px <= click_threshold_px`.

Phase 10 stops on foreground block, after-distance miss, after-detection missing, no-detection timeout, max duration, max iterations, or Ctrl+C.

## Defaults

- `max_iterations=160`
- `max_duration_sec=65`
- `click_threshold_px=8`
- `post_click_wait_sec=0.05`
- `next_target_timeout_sec=0.50`
- `no_detection_poll_interval_sec=0.05`
- `horizontal_fov_deg=103`
- `vertical_fov_deg=70.53`
- `counts_per_degree=39.03`
- `global_gain=1.0`

## Phase 10.1 After Validation Robustness + Startup Timing Fix

Phase 10.1 fixes two smoke-test issues without changing the accepted FOV movement formula and without adding second correction, target lock, PID, smoothing, Hotkey Runner, GUI, or background automation.

Why it was needed:

- In multi-target scenes, after validation could select the wrong YOLO target after movement.
- If the centered target was partially hidden by the crosshair, YOLO could miss it and select a farther target, causing a false `after_distance_exceeded_threshold` stop.
- The previous max-duration timing could include model loading / initialization time, reducing the actual active loop window.

Hybrid after validation:

1. `yolo_center_detection`: if any after YOLO detection center is within `click_threshold_px`, validation passes.
2. `center_roi_yellow_fallback`: if YOLO center validation fails, inspect a small crosshair-centered ROI for yellow pixels. This fallback is only for after validation / click gate and never triggers another move.
3. Failure:
   - no after detections and no center yellow: `after_detection_missing`
   - after detections exist but nearest is far and ROI fails: `after_distance_exceeded_threshold`

Center ROI defaults:

- `center_roi_radius_px=20`
- `center_roi_click_threshold_px=10`
- `center_roi_min_yellow_pixels=8`
- `center_roi_min_contour_area_px=4`

The fallback uses a conservative HSV-style yellow check and excludes green crosshair pixels by hue, saturation, and RGB constraints.

Startup timing fix:

- `process_started_at` / `process_ended_at` / `wall_duration_sec` record full process time.
- `startup_started_at` / `startup_ended_at` / `startup_duration_sec` record initialization.
- `loop_started_at` / `loop_ended_at` / `active_loop_duration_sec` record the bounded active loop.
- `max_duration_sec` now applies to active loop duration, not model loading / startup wall time.

New CLI parameters:

- `--after-validation-mode nearest|hybrid`, default `hybrid`
- `--center-roi-radius-px`, default `20`
- `--center-roi-click-threshold-px`, default `10`
- `--center-roi-min-yellow-pixels`, default `8`
- `--center-roi-min-contour-area-px`, default `4`
- `--evidence-mode full|failures|minimal`, default `full`

Phase 10.1 keeps the rule that if after validation fails, the run stops safely. It does not continue to correct the same target.

## Smoke Test Command

```powershell
Start-Sleep -Seconds 3; .\.venv\Scripts\python.exe scripts\live_finite_repeat_aim_click.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --max-iterations 10 `
  --max-duration-sec 30 `
  --click-threshold-px 8 `
  --post-click-wait-sec 0.20 `
  --next-target-timeout-sec 0.50 `
  --no-detection-poll-interval-sec 0.05 `
  --horizontal-fov-deg 103 `
  --vertical-fov-deg 70.53 `
  --counts-per-degree 39.03 `
  --global-gain 1.0 `
  --after-validation-mode hybrid `
  --center-roi-radius-px 20 `
  --center-roi-click-threshold-px 10 `
  --center-roi-min-yellow-pixels 8 `
  --center-roi-min-contour-area-px 4 `
  --execute-move `
  --allow-click `
  --confirm-local-aimlab-only `
  --output-dir "D:\桌面desktop\AIAIM\runs\detect\phase10_finite_repeat_aim_click"
```

## Formal Phase 10 Command

```powershell
Start-Sleep -Seconds 3; .\.venv\Scripts\python.exe scripts\live_finite_repeat_aim_click.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --max-iterations 160 `
  --max-duration-sec 65 `
  --click-threshold-px 8 `
  --post-click-wait-sec 0.20 `
  --next-target-timeout-sec 0.50 `
  --no-detection-poll-interval-sec 0.05 `
  --horizontal-fov-deg 103 `
  --vertical-fov-deg 70.53 `
  --counts-per-degree 39.03 `
  --global-gain 1.0 `
  --after-validation-mode hybrid `
  --center-roi-radius-px 20 `
  --center-roi-click-threshold-px 10 `
  --center-roi-min-yellow-pixels 8 `
  --center-roi-min-contour-area-px 4 `
  --execute-move `
  --allow-click `
  --confirm-local-aimlab-only `
  --output-dir "D:\桌面desktop\AIAIM\runs\detect\phase10_finite_repeat_aim_click"
```

## Outputs

Default root:

```text
runs/detect/phase10_finite_repeat_aim_click/<run_id>/
```

Files:

- `run_config.json`
- `phase10_summary.json`
- `iteration_summary.csv` with after-validation and timing fields
- `events.jsonl` with startup / loop / after-validation events
- `iterations/iter_###/before_detection.json`
- `iterations/iter_###/after_detection.json`
- `iterations/iter_###/step_result.json`
- optional review images with `--save-review-images`

## Acceptance Steps

1. Run the 10-iteration smoke test first.
2. Confirm `clicks_executed > 0`, `false_click_count = 0` by manual review, and no unexpected stop reason.
3. Run the formal 160 / 65s command only after smoke test passes.
4. Inspect `phase10_summary.json`, `iteration_summary.csv`, and `events.jsonl`.


## Phase 10.2 - Fast Loop Optimization + Bounded Retry

Phase 10.2 keeps the Phase 10 architecture: finite repeat only, no Hotkey Runner, no GUI, no background automation, no infinite loop, no PID, no target lock, no smoothing, and no second correction inside an iteration.

Changes:

- Added `--retry-policy stop|bounded`, default `bounded`.
- Added bounded retry controls: `--max-retries-per-target`, `--max-total-retry-attempts`, `--retry-distance-px`, and `--retry-same-target-distance-px`.
- Changed default `--evidence-mode` to `failures` so clicked success iterations skip review images and per-iteration `step_result.json` unless explicitly requested.
- Changed default `--post-click-wait-sec` to `0.05`.
- Added retry and I/O timing fields to `iteration_summary.csv`, `phase10_summary.json`, and `events.jsonl`.

Bounded retry is not target lock and not PID. A retry means the next iteration starts from a fresh screenshot, fresh YOLO detection, fresh FOV calculation, and still allows at most one move and one click. Retries are bounded by `max_iterations`, `max_duration_sec`, `max_retries_per_target`, and `max_total_retry_attempts`.

Retry can be scheduled when:

- Center ROI fallback sees yellow near the crosshair but the click threshold is still not met.
- The nearest after YOLO detection is outside the click threshold but within `retry_distance_px`.
- The before target was already near the crosshair but no click was executed.

The run still stops on foreground block, missing explicit action flags, Ctrl+C, `max_duration_sec`, `max_iterations`, retry limit reached, after detection missing with no center evidence, or any state where safety cannot be confirmed.

Evidence modes:

- `full`: save review images and per-iteration JSON for every iteration.
- `failures`: save evidence for retry / blocked / failed / no-click iterations; skip heavy evidence for clicked successes.
- `minimal`: write summary CSV / JSON / events only where possible.

Phase 10.2 is the first step toward faster loops. It does not claim 100 ms iterations. The immediate target is to see whether the loop can move from roughly 2 seconds per round toward sub-500 ms rounds. If still slow, Phase 10.3 should profile capture backend, ROI capture, after-validation fast path, model inference, and disk I/O.

### Phase 10.2 Smoke Test

```powershell
Start-Sleep -Seconds 3; .\.venv\Scripts\python.exe scripts\live_finite_repeat_aim_click.py `
  --model "D:\桌面desktop\AIAIM
uns\detect\phase3_yolo11n_baseline\weightsest.pt" `
  --max-iterations 10 `
  --max-duration-sec 30 `
  --click-threshold-px 8 `
  --post-click-wait-sec 0.05 `
  --next-target-timeout-sec 0.50 `
  --no-detection-poll-interval-sec 0.05 `
  --horizontal-fov-deg 103 `
  --vertical-fov-deg 70.53 `
  --counts-per-degree 39.03 `
  --global-gain 1.0 `
  --after-validation-mode hybrid `
  --retry-policy bounded `
  --max-retries-per-target 1 `
  --max-total-retry-attempts 20 `
  --retry-distance-px 30 `
  --retry-same-target-distance-px 45 `
  --evidence-mode failures `
  --execute-move `
  --allow-click `
  --confirm-local-aimlab-only `
  --output-dir "D:\桌面desktop\AIAIM
uns\detect\phase10_finite_repeat_aim_click"
```

### Faster 30-Iteration Smoke Test

```powershell
Start-Sleep -Seconds 3; .\.venv\Scripts\python.exe scripts\live_finite_repeat_aim_click.py `
  --model "D:\桌面desktop\AIAIM
uns\detect\phase3_yolo11n_baseline\weightsest.pt" `
  --max-iterations 30 `
  --max-duration-sec 30 `
  --click-threshold-px 8 `
  --post-click-wait-sec 0.05 `
  --next-target-timeout-sec 0.50 `
  --no-detection-poll-interval-sec 0.05 `
  --horizontal-fov-deg 103 `
  --vertical-fov-deg 70.53 `
  --counts-per-degree 39.03 `
  --global-gain 1.0 `
  --after-validation-mode hybrid `
  --retry-policy bounded `
  --max-retries-per-target 1 `
  --max-total-retry-attempts 20 `
  --retry-distance-px 30 `
  --retry-same-target-distance-px 45 `
  --evidence-mode failures `
  --execute-move `
  --allow-click `
  --confirm-local-aimlab-only `
  --output-dir "D:\桌面desktop\AIAIM
uns\detect\phase10_finite_repeat_aim_click"
```


## Phase 10.3 - Capture Fast Path + Click Accuracy Guard + 30-Round Benchmark

Phase 10.3 addresses two observed Phase 10.2 issues: one suspicious fallback click and loop speed dominated by screenshot capture. It still does not add Hotkey Runner, GUI, background automation, infinite loop, PID, target lock, smoothing, second correction, AIMLAB memory reading, AIMLAB file modification, or anti-cheat bypass.

### Click Accuracy Guard

New parameters:

- `--click-guard-mode standard|strict`, default `strict`.
- `--strict-center-roi-click-threshold-px`, default `6`.
- `--fallback-click-allowed` / `--no-fallback-click-allowed`, default allowed.
- `--save-evidence-on-fallback-click` / `--no-save-evidence-on-fallback-click`, default save.

Rules:

- `yolo_center_detection` can click when `after_distance_to_crosshair_px <= click_threshold_px`.
- `center_roi_yellow_fallback` in `standard` mode keeps Phase 10.2 behavior.
- `center_roi_yellow_fallback` in `strict` mode requires centroid distance <= `strict_center_roi_click_threshold_px` plus yellow pixel and contour area thresholds.
- Fallback validation between 6 and 8 px no longer clicks in strict mode; it schedules bounded retry with `retry_reason=strict_fallback_click_guard_retry`.
- Fallback clicks save evidence even when `--evidence-mode failures` is active.

### Capture Fast Path

New parameters:

- `--capture-backend auto|mss|dxcam`, default `auto`.
- `--capture-benchmark-only`.
- `--capture-benchmark-frames`, default `30`.

Capture timing is split into:

- `capture_object_init_ms`
- `monitor_lookup_ms`
- `raw_grab_ms`
- `buffer_to_numpy_ms`
- `color_convert_ms`
- `evidence_encode_ms`

Regular Phase 10.3 runtime uses a persistent capture object where possible. Benchmark mode compares:

- current mss style (`mss_current`)
- persistent mss (`mss_persistent`)
- optional `dxcam`

If `dxcam` is not installed, benchmark output records `dxcam_available=false` and `dxcam_import_error`. It is not silently skipped. Optional install command:

```powershell
.\.venv\Scripts\python.exe -m pip install dxcam
```

If persistent mss remains above 100 ms per frame, the report should treat the current screenshot path as insufficient for a 400 ms loop and consider `dxcam`, Windows Graphics Capture, or ROI capture in a later phase.

### After Fast Mode

New parameter:

- `--after-fast-mode full|roi_only`, default `roi_only`.

Modes:

- `full`: after screenshot + after YOLO + hybrid validation.
- `roi_only`: after screenshot + center ROI yellow validation only. It does not skip after screenshot and does not perform predictive click.

### Capture Benchmark Command

```powershell
Start-Sleep -Seconds 3; .\.venv\Scripts\python.exe scripts\live_finite_repeat_aim_click.py `
  --capture-benchmark-only `
  --capture-benchmark-frames 30 `
  --capture-backend auto `
  --confirm-local-aimlab-only `
  --output-dir "D:\桌面desktop\AIAIM
uns\detect\phase10_capture_benchmark"
```

Benchmark-only never moves or clicks.

### 30-Round Phase 10.3 Benchmark Command

```powershell
Start-Sleep -Seconds 3; .\.venv\Scripts\python.exe scripts\live_finite_repeat_aim_click.py `
  --model "D:\桌面desktop\AIAIM
uns\detect\phase3_yolo11n_baseline\weightsest.pt" `
  --max-iterations 30 `
  --max-duration-sec 30 `
  --click-threshold-px 8 `
  --post-click-wait-sec 0.03 `
  --next-target-timeout-sec 0.50 `
  --no-detection-poll-interval-sec 0.05 `
  --horizontal-fov-deg 103 `
  --vertical-fov-deg 70.53 `
  --counts-per-degree 39.03 `
  --global-gain 1.0 `
  --after-validation-mode hybrid `
  --after-fast-mode roi_only `
  --click-guard-mode strict `
  --strict-center-roi-click-threshold-px 6 `
  --retry-policy bounded `
  --max-retries-per-target 1 `
  --max-total-retry-attempts 20 `
  --retry-distance-px 30 `
  --retry-same-target-distance-px 45 `
  --capture-backend auto `
  --evidence-mode failures `
  --execute-move `
  --allow-click `
  --confirm-local-aimlab-only `
  --output-dir "D:\桌面desktop\AIAIM
uns\detect\phase10_finite_repeat_aim_click"
```

Do not run the 30-round command before running capture benchmark. If average iteration time is still over 400 ms, inspect `average_before_capture_ms`, `average_after_capture_ms`, `average_before_detect_ms`, `average_after_detect_ms`, `average_after_validation_ms`, and `average_total_io_ms` before changing aim/click logic.


## Phase 10.3.1 - Capture Timing / Evidence Encode Separation

Phase 10.3.1 fixes capture timing attribution. Benchmark data showed `raw_grab_ms` around 20 ms while PNG evidence encoding was around 450-490 ms. `before_capture_ms` and `after_capture_ms` now represent raw capture plus required buffer/color conversion only, not PNG encode or review-image writing.

Changes:

- Capture returns an in-memory frame for YOLO and center-ROI validation.
- PNG encoding is deferred until evidence is actually saved.
- `--capture-benchmark-only` defaults to raw capture timing only and does not encode PNG frames.
- Added `--capture-benchmark-include-encode` to explicitly benchmark PNG encode cost.
- Success iterations with `--evidence-mode failures` do not encode before/after images unless forced by fallback-click evidence.
- Evidence timing is recorded separately as `evidence_encode_ms`, `evidence_write_ms`, and `evidence_total_ms`.
- `total_io_ms` tracks evidence I/O and no longer pollutes capture timing.

Re-run capture benchmark after this patch. Expected result: `average_capture_ms` should be close to `raw_grab_ms + buffer/color conversion`, not 470-500 ms. If it is still above 100 ms, inspect the split fields to identify whether raw grab, buffer conversion, or color conversion is the bottleneck.

## Phase 10.3.2 - YOLO Warmup + Startup Stability

Phase 10.3.2 keeps the Phase 10.3 control model unchanged and only hardens startup timing and logging. It does not add a Hotkey Runner, GUI, background automation, target lock, PID, smoothing, memory reads, AIMLAB file changes, or anti-cheat bypass.

Changes:
- Startup now performs one YOLO warmup inference by default after model load and before the active loop starts.
- Warmup uses a current foreground frame when available, but never moves the mouse and never clicks.
- Warmup time is recorded separately as `warmup_ms`, `warmup_capture_ms`, `warmup_detect_ms`, and `warmup_detections_count`; it does not count toward `active_loop_duration_sec` or `action_iterations_attempted`.
- `--no-warmup-inference` disables this behavior for diagnostics.
- `no_detection_timeout` is now a normal stop reason, not a safety block. Safety blocks remain reserved for foreground loss and missing required explicit flags.
- `iteration_summary.csv` headers are validated for uniqueness before writing so PowerShell `Import-Csv` can read the file.

The 30-round command remains the Phase 10.3 command. If the first YOLO inference was previously cold and slow, the default warmup should prevent that cold inference from consuming the first target wait window.

## Phase 10.3.4 - No-Detection Evidence + Loop Semantics Cleanup

Phase 10.3.4 keeps the Phase 10.3 control boundaries unchanged. It does not change the FOV formula, click threshold, YOLO model, SendInput behavior, or safety gates. It does not add a Hotkey Runner, GUI, background automation, PID, target lock, smoothing, AIMLAB memory reads, AIMLAB file changes, or anti-cheat bypass.

Changes:
- `max_iterations` now limits action iterations only: a loop with a detected target that proceeds into aim/move/after-validation/click handling.
- No-detection loops increment `loop_iterations_attempted`, `no_detection_timeout_count`, and `consecutive_no_detection_timeout_count`, but do not consume `max_iterations`.
- Added `--max-loop-iterations` as a hard cap over all loop attempts, including empty no-detection loops. Default: `1000`.
- Added no-detection evidence capture. With `--evidence-mode failures` and default `--save-evidence-on-no-detection`, no-detection timeout iterations save the last before frame so it is possible to distinguish an empty screen from a YOLO miss or bad capture.
- Added `--max-no-detection-evidence`, default `10`, to avoid excessive disk writes during long no-detection periods.
- Fallback click evidence remains off by default; do not add `--save-evidence-on-fallback-click` for speed tests unless specifically diagnosing fallback clicks.

Recommended 30-round diagnostic command:

```powershell
Start-Sleep -Seconds 3; .\.venv\Scripts\python.exe scripts\live_finite_repeat_aim_click.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --max-iterations 30 `
  --max-duration-sec 30 `
  --click-threshold-px 8 `
  --post-click-wait-sec 0.03 `
  --next-target-timeout-sec 0.50 `
  --no-detection-poll-interval-sec 0.05 `
  --horizontal-fov-deg 103 `
  --vertical-fov-deg 70.53 `
  --counts-per-degree 39.03 `
  --global-gain 1.0 `
  --after-validation-mode hybrid `
  --after-fast-mode roi_only `
  --click-guard-mode strict `
  --strict-center-roi-click-threshold-px 6 `
  --retry-policy bounded `
  --max-retries-per-target 1 `
  --max-total-retry-attempts 20 `
  --retry-distance-px 30 `
  --retry-same-target-distance-px 45 `
  --capture-backend auto `
  --evidence-mode failures `
  --no-detection-policy continue `
  --max-no-detection-timeouts 100 `
  --max-consecutive-no-detection-timeouts 20 `
  --max-no-detection-evidence 10 `
  --save-evidence-on-no-detection `
  --execute-move `
  --allow-click `
  --confirm-local-aimlab-only `
  --output-dir "D:\桌面desktop\AIAIM\runs\detect\phase10_finite_repeat_aim_click"
```

Do not add `--save-evidence-on-fallback-click` to the normal 30-round command; fallback click evidence is intentionally opt-in because image encoding can dominate round time.

## Phase 10.3.5 - Live Detection Parity Fix

Phase 10.3.5 fixes the live detection path used by Phase 10 after evidence showed that no-detection frames visibly contained yellow balls and `offline_detect.py` could detect them. The likely discrepancy was live ndarray input format versus file-path inference.

Changes:
- mss capture now keeps separate frame contracts: RGB for evidence/ROI and BGR 3-channel for YOLO ndarray inference.
- dxcam RGB frames are converted to BGR for YOLO ndarray inference.
- The live detection path records raw/parsed detection diagnostics: `raw_yolo_boxes_count`, `parsed_detections_count`, `live_in_memory_detections_count`, and live conf/iou/max-det/imgsz/device.
- Added no-detection parity diagnostics. When no-detection occurs and a before frame was saved, Phase 10 can run file-path inference on that same `before.png` and compare it with the live in-memory detection count.
- Added CLI flags: `--debug-detection-parity` and `--debug-detection-parity-on-no-detection`.

Interpretation:
- `file_path_detections_count > 0` and `live_in_memory_detections_count = 0` means live input/parsing parity is still suspect.
- Both counts at 0 means the issue is more likely confidence/model/capture content.
- Do not retrain before live/offline parity is confirmed.

Recommended next diagnostic: run a 3-action test with no-detection evidence and parity enabled, then inspect `step_result.json`, `before_detection.json`, and the saved `before.png` for any no-detection iterations.

## Phase 10.3.6 - After-Missing Bounded Retry + 300-Round Defaults

Phase 10.3.6 treats `after_detection_missing` as a bounded retry condition when `--retry-policy bounded` is active. It still does not click when after validation is missing; it records the failed action iteration, schedules a retry, and the next iteration must use a fresh screenshot, fresh detection, and fresh FOV computation.

Retry behavior:
- `after_validation_method=no_after_detection` or `stop_reason=after_detection_missing` schedules `retry_reason=after_detection_missing_retry` under bounded retry.
- The iteration remains `blocked=false`, `click_executed=false`, and `retry_scheduled=true`.
- Retry limits still apply: `max_total_retry_attempts`, `max_retries_per_target`, `max_iterations`, `max_duration_sec`, `max_loop_iterations`, foreground gate, and KeyboardInterrupt.
- With `--retry-policy stop`, old stop behavior is preserved for debugging.

Recommended 300-round pressure command:

```powershell
Start-Sleep -Seconds 3; .\.venv\Scripts\python.exe scripts\live_finite_repeat_aim_click.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --max-iterations 300 `
  --max-duration-sec 120 `
  --click-threshold-px 8 `
  --post-click-wait-sec 0.03 `
  --next-target-timeout-sec 0.50 `
  --no-detection-poll-interval-sec 0.05 `
  --horizontal-fov-deg 103 `
  --vertical-fov-deg 70.53 `
  --counts-per-degree 39.03 `
  --global-gain 1.0 `
  --after-validation-mode hybrid `
  --after-fast-mode roi_only `
  --click-guard-mode strict `
  --strict-center-roi-click-threshold-px 6 `
  --retry-policy bounded `
  --max-retries-per-target 2 `
  --max-total-retry-attempts 100 `
  --retry-distance-px 30 `
  --retry-same-target-distance-px 45 `
  --capture-backend auto `
  --evidence-mode failures `
  --no-detection-policy continue `
  --max-no-detection-timeouts 200 `
  --max-consecutive-no-detection-timeouts 30 `
  --max-no-detection-evidence 10 `
  --save-evidence-on-no-detection `
  --execute-move `
  --allow-click `
  --confirm-local-aimlab-only `
  --output-dir "D:\桌面desktop\AIAIM\runs\detect\phase10_finite_repeat_aim_click"
```

Do not add `--save-evidence-on-fallback-click` to this command unless diagnosing fallback clicks.

## Phase 10.3.7 pressure-test interpretation

A 300-round pressure test can end with `stop_reason=max_consecutive_no_detection_timeouts_reached` after the AIMLAB task finishes and targets are exhausted. When clicks/actions have already completed, there is no foreground block, max duration is not reached, and retry limits are not reached, this is classified in summary as:

```text
task_end_likely=true
terminal_classification=likely_task_ended_or_targets_exhausted
```

Recommended pressure test command remains:

```powershell
Start-Sleep -Seconds 3; .\.venv\Scripts\python.exe scripts\live_finite_repeat_aim_click.py `
  --model "D:\桌面desktop\AIAIM\runs\detect\phase3_yolo11n_baseline\weights\best.pt" `
  --max-iterations 300 `
  --max-duration-sec 120 `
  --max-loop-iterations 2000 `
  --conf 0.10 `
  --max-det 20 `
  --click-threshold-px 8 `
  --post-click-wait-sec 0.03 `
  --next-target-timeout-sec 0.50 `
  --no-detection-poll-interval-sec 0.05 `
  --horizontal-fov-deg 103 `
  --vertical-fov-deg 70.53 `
  --counts-per-degree 39.03 `
  --global-gain 1.0 `
  --after-validation-mode hybrid `
  --after-fast-mode roi_only `
  --click-guard-mode strict `
  --strict-center-roi-click-threshold-px 6 `
  --retry-policy bounded `
  --max-retries-per-target 2 `
  --max-total-retry-attempts 100 `
  --retry-distance-px 30 `
  --retry-same-target-distance-px 45 `
  --capture-backend auto `
  --evidence-mode minimal `
  --no-detection-policy continue `
  --max-no-detection-timeouts 200 `
  --max-consecutive-no-detection-timeouts 30 `
  --execute-move `
  --allow-click `
  --confirm-local-aimlab-only `
  --output-dir "D:\桌面desktop\AIAIM\runs\detect\phase10_finite_repeat_aim_click"
```

For no-detection diagnosis, temporarily add `--save-evidence-on-no-detection`. For normal high-speed pressure tests, prefer `--evidence-mode minimal`. Do not add `--save-evidence-on-fallback-click` unless specifically diagnosing fallback clicks.

