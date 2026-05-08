# Phase 10 Report - Finite Repeat Aim + Click

## Status

Implemented. Windows + AIMLAB real-machine validation is pending.

## Goal

Phase 10 implements a finite repeat runner for the accepted Phase 9 one-shot aim + click step.

It repeats fresh screenshot -> detection -> FOV relative move -> after screenshot -> click gate -> optional click until `max_iterations`, `max_duration_sec`, or a safety stop condition is reached.

## Files Added

- `scripts/live_finite_repeat_aim_click.py`
- `tests/test_phase10_finite_repeat_aim_click.py`
- `docs/runbooks/phase-10-finite-repeat-aim-click-runbook.md`
- `docs/phase-reports/phase-10-report.md`

## Phase 9 Reuse

Phase 10 imports and reuses:

- `live_one_shot_click_gate` for startup helpers, click gate, and left-click `SendInput`.
- `live_one_shot_fov_aim` for AIMLAB foreground gate, monitor capture, YOLO detection conversion, target selection, review rendering, and relative movement.
- `compute_fov_relative_move` for the accepted FOV aim calculation.

No new aiming algorithm was introduced.

## Defaults

- `max_iterations=160`
- `max_duration_sec=65`
- `click_threshold_px=8`
- `post_click_wait_sec=0.20`
- `next_target_timeout_sec=0.50`
- `no_detection_poll_interval_sec=0.05`
- `horizontal_fov_deg=103`
- `vertical_fov_deg=70.53`
- `counts_per_degree=39.03`
- `global_gain=1.0`

## Safety Boundary

Phase 10 requires all real-action flags:

- `--execute-move`
- `--allow-click`
- `--confirm-local-aimlab-only`

Phase 10 does not implement Hotkey Runner, GUI, background automation, infinite loop, PID, target lock, smoothing, second correction, AIMLAB memory reading, AIMLAB file modification, or anti-cheat bypass.

Every action iteration uses a fresh screenshot and allows at most one move and one click.

## Phase 10.1 Update - After Validation Robustness + Startup Timing

Phase 10.1 was implemented after a smoke-test false-fail case where after validation selected a far lower target even though the review image suggested a yellow target was near the crosshair.

Fixes implemented:

- Added `--after-validation-mode nearest|hybrid`, default `hybrid`.
- Added YOLO center validation across all after detections.
- Added center ROI yellow fallback for cases where the centered target is partially occluded by the green crosshair and missed by YOLO.
- Added ROI diagnostic fields for yellow pixel count, largest component area, centroid, and centroid distance.
- Added startup / loop timing separation so `max_duration_sec` applies to active loop duration instead of model loading / startup wall time.
- Added summary counters for validation pass/fail methods.
- Added events for `startup_started`, `startup_completed`, `loop_started`, `after_validation_started`, validation pass/fail, and `loop_stopped`.

Hybrid validation order:

1. `yolo_center_detection`: pass if any after detection center is within `click_threshold_px`.
2. `center_roi_yellow_fallback`: pass if centered ROI has enough yellow pixels / area and centroid is within `center_roi_click_threshold_px`.
3. `no_after_detection`: fail safely if no after detections and ROI fallback fails.
4. `nearest_yolo_far`: fail safely if after detections exist but the nearest target is outside threshold and ROI fallback fails.

The center ROI fallback is not a new aiming algorithm. It does not move the mouse, does not lock targets, does not continue after failure, and does not perform a second correction.

Green crosshair exclusion:

- The fallback uses hue/saturation/value plus RGB constraints for yellow.
- Green crosshair pixels are rejected by hue and RGB constraints.

Timing fix:

- Full process wall time is recorded separately as `wall_duration_sec`.
- Startup is recorded separately as `startup_duration_sec` and `model_load_ms`.
- Active loop duration is recorded as `active_loop_duration_sec`.
- `max_duration_sec` is checked against active loop time only.

New fields include:

- `after_validation_mode`
- `after_validation_method`
- `after_validation_passed`
- `after_nearest_detection_*`
- `center_roi_*`
- `yolo_center_validation_pass_count`
- `center_roi_fallback_pass_count`
- `after_validation_failed_count`
- `process_started_at`, `startup_started_at`, `loop_started_at`
- `wall_duration_sec`, `startup_duration_sec`, `active_loop_duration_sec`

## Validation Performed

Commands attempted or run:

```bash
PYTHONPYCACHEPREFIX=/tmp/aiaim_phase101_pycache python3 -m compileall scripts tests
PYTHONPATH=src:scripts python3 scripts/live_finite_repeat_aim_click.py --help
.\.venv\Scripts\python.exe -m compileall scripts tests
.\.venv\Scripts\python.exe scripts/live_finite_repeat_aim_click.py --help
PYTHONPATH=src:scripts python3 -m pytest tests/test_phase10_finite_repeat_aim_click.py tests/test_phase10_1_after_validation.py -q
PYTHONPATH=src:scripts python3 scripts/live_finite_repeat_aim_click.py --run-id wsl_phase101_blocked --overwrite --output-dir /tmp/aiaim_phase101_runs
```

Results:

- WSL `compileall` passed for `scripts` and `tests`.
- WSL `--help` passed and showed the new Phase 10.1 CLI parameters.
- Windows `.venv` commands could not be executed from the current WSL shell due a WSL socket binding error.
- WSL `pytest` could not run because the current WSL Python has no `pytest` module.
- Direct manual core checks passed for YOLO center validation and active loop duration helper.
- Blocked run without action flags wrote `phase10_summary.json` with `blocked=true`, `stop_reason=execute_move_false`, `moves_executed=0`, and `clicks_executed=0`.

No real AIMLAB move/click command was run by Codex.

## Next Step

Run the Phase 10.1 10-iteration smoke test from the runbook first. Do not run the 160-iteration validation until the smoke test output confirms hybrid after validation is behaving correctly.


## Phase 10.2 Update - Fast Loop Optimization + Bounded Retry

Status: implemented, pending Windows AIMLAB real-machine validation.

Scope and safety:

- No real mouse movement command was run by Codex.
- No click command was run by Codex.
- No Hotkey Runner, GUI, background automation, infinite loop, PID, target lock, smoothing, or second correction was added.
- No AIMLAB process memory read, AIMLAB file modification, or anti-cheat bypass was added.

Implemented changes:

- Added bounded retry to `scripts/live_finite_repeat_aim_click.py` with `--retry-policy stop|bounded`, default `bounded`.
- Added retry limits: `--max-retries-per-target 1`, `--max-total-retry-attempts 20`, `--retry-distance-px 30`, and `--retry-same-target-distance-px 45`.
- Added a center-ROI near-miss retry path for cases where fallback sees yellow near the crosshair but the stricter click threshold is not met.
- Added nearest-YOLO retry scheduling when the nearest after detection is outside the click threshold but within retry distance.
- Changed default `--evidence-mode` from `full` to `failures`.
- Changed default `--post-click-wait-sec` from `0.20` to `0.05`.
- Added retry, evidence, and I/O timing fields to the iteration CSV and summary JSON.
- Added retry and performance events to `events.jsonl`.

Retry boundaries:

- Retry is always a new iteration with a fresh screenshot, fresh detection, and fresh FOV calculation.
- Each iteration still performs at most one SendInput relative move and at most one click.
- Retry does not reuse old detections and does not track a target continuously.
- Retry is bounded by max iterations, active-loop max duration, per-target retry count, and total retry count.
- Foreground loss, missing explicit flags, retry limit reached, max duration, max iterations, Ctrl+C, and unsafe errors still stop the run.

Fast-loop changes:

- `evidence-mode=failures` skips heavy image / step-result evidence for clicked success iterations.
- Retry, blocked, failed, and no-click iterations still keep evidence for diagnosis.
- Detailed timing fields now include action round, post-move sleep, after validation, evidence write, CSV write placeholder, events write placeholder, total I/O, and iteration total.
- This phase does not claim 100 ms loop time. It is intended to test whether the loop can move from about 2 seconds per round toward sub-500 ms before deeper Phase 10.3 profiling.

New / updated files:

- `scripts/live_finite_repeat_aim_click.py`
- `tests/test_phase10_finite_repeat_aim_click.py`
- `tests/test_phase10_2_retry_and_fast_mode.py`
- `docs/runbooks/phase-10-finite-repeat-aim-click-runbook.md`
- `docs/phase-reports/phase-10-report.md`
- `README.md`

Validation:

```bash
python3 -m compileall scripts tests
python3 scripts/live_finite_repeat_aim_click.py --help
python3 scripts/live_finite_repeat_aim_click.py --output-dir /tmp/aiaim_phase10_2_blocked --run-id blocked_check --overwrite
.\.venv\Scripts\python.exe -m compileall scripts tests
.\.venv\Scripts\python.exe scripts\live_finite_repeat_aim_click.py --help
.\.venv\Scripts\python.exe -m pytest tests/test_phase10_finite_repeat_aim_click.py tests/test_phase10_1_after_validation.py tests/test_phase10_2_retry_and_fast_mode.py -q
```

Results:

- WSL `compileall` passed for `scripts` and `tests`.
- WSL `--help` passed and showed Phase 10.2 retry parameters.
- Default blocked run without action flags wrote `blocked=true`, `stop_reason=execute_move_false`, `moves_executed=0`, and `clicks_executed=0`.
- Windows `.venv` `compileall` passed.
- Windows `.venv` `--help` passed.
- Windows `.venv` pytest was not run because that venv reports `No module named pytest`.
- WSL pytest was not run because the WSL Python also reports `No module named pytest`.
- Manual helper assertions for retry scheduling, retry limit, and evidence skipping passed.

Next validation step:

Run the Phase 10.2 10-iteration smoke test from the runbook first. Do not start with the 160-round validation. Inspect `iteration_summary.csv`, `phase10_summary.json`, and `events.jsonl` for retry counts, evidence skipped/saved counts, and iteration timing.


## Phase 10.3 Update - Capture Fast Path + Click Accuracy Guard + 30-Round Benchmark

Status: implemented, pending Windows AIMLAB benchmark and real-machine validation.

Scope and safety:

- No real mouse movement command was run by Codex.
- No click command was run by Codex.
- No 30-round or 160-round live test was run by Codex.
- No Hotkey Runner, GUI, background automation, infinite loop, PID, target lock, smoothing, second correction, AIMLAB memory reading, AIMLAB file modification, or anti-cheat bypass was added.

Implemented changes:

- Added strict fallback click guard to reduce suspicious center-ROI fallback clicks.
- Added `--click-guard-mode standard|strict`, default `strict`.
- Added `--strict-center-roi-click-threshold-px`, default `6`.
- Added fallback click evidence flags so fallback clicks save evidence even in `failures` mode.
- Added persistent capture manager and `--capture-backend auto|mss|dxcam`, default `auto`.
- Added capture timing breakdown: `capture_object_init_ms`, `monitor_lookup_ms`, `raw_grab_ms`, `buffer_to_numpy_ms`, `color_convert_ms`, and `evidence_encode_ms`.
- Added `--capture-benchmark-only` and `--capture-benchmark-frames` to compare current mss, persistent mss, and optional dxcam.
- Added `--after-fast-mode full|roi_only`, default `roi_only`.
- Added benchmark fields for 400 ms target, capture backend, after fast mode, click guard mode, fallback click counts, strict guard retry counts, and average after validation time.

Capture benchmark behavior:

- Benchmark-only checks AIMLAB foreground and captures frames only.
- It does not load YOLO, move the mouse, or click.
- With `--capture-backend auto`, it measures `mss_current`, `mss_persistent`, and `dxcam` availability.
- If dxcam is missing, output records `dxcam_available=false` and `dxcam_import_error`.

Expected interpretation:

- If persistent mss is still above 100 ms/frame, the current screenshot path is not enough for a reliable sub-400 ms full loop.
- Next optimization would need dxcam, Windows Graphics Capture, ROI capture, or capture-side profiling before changing aim/click logic.

Validation:

```bash
python3 -m compileall scripts tests
.\.venv\Scripts\python.exe -m compileall scripts tests
.\.venv\Scripts\python.exe scripts\live_finite_repeat_aim_click.py --help
.\.venv\Scripts\python.exe -m pytest tests/test_phase10_finite_repeat_aim_click.py tests/test_phase10_1_after_validation.py tests/test_phase10_2_retry_and_fast_mode.py tests/test_phase10_3_fast_capture_and_click_guard.py -q
```

Results:

- WSL `compileall` passed for `scripts` and `tests`.
- Windows `.venv` `compileall` passed.
- Windows `.venv` `--help` passed and showed Phase 10.3 CLI parameters.
- Windows `.venv` pytest was not run because that venv reports `No module named pytest`.
- Manual helper checks passed for strict fallback guard, yolo-center guard, roi/full after-fast-mode helper, benchmark under-400 calculation, and strict-guard retry scheduling.

Next step:

Run capture benchmark first. If capture is acceptable, run the 30-round Phase 10.3 command. Do not jump to 160 rounds until the 30-round benchmark confirms click accuracy and average loop timing.


## Phase 10.3.1 Patch - Capture Timing / Evidence Encode Separation

Status: implemented, pending renewed capture benchmark.

Problem:

- Capture benchmark showed `raw_grab_ms` around 20 ms.
- `evidence_encode_ms` was around 450-490 ms.
- Previous `average_capture_ms` included PNG evidence encoding, making capture look like a 470-500 ms bottleneck.

Fix:

- Raw capture now returns an in-memory frame.
- YOLO inference and center ROI validation use the in-memory frame.
- PNG encoding is deferred until evidence saving is required.
- `before_capture_ms` / `after_capture_ms` now exclude `evidence_encode_ms`.
- `capture_benchmark_only` defaults to no image encode.
- New `--capture-benchmark-include-encode` can explicitly measure PNG encode cost.
- Evidence timing is separated into `evidence_encode_ms`, `evidence_write_ms`, and `evidence_total_ms`.
- `total_io_ms` remains I/O-oriented and does not affect capture timing.

Safety:

- No real mouse movement command was run.
- No click command was run.
- No 30-round or 160-round live test was run.
- No Hotkey Runner, GUI, background automation, memory reading, file modification, or anti-cheat bypass was added.

Validation:

```bash
python3 -m compileall scripts tests
.\.venv\Scripts\python.exe -m compileall scripts tests
.\.venv\Scripts\python.exe scripts\live_finite_repeat_aim_click.py --help
.\.venv\Scripts\python.exe -m pytest tests/test_phase10_3_capture_timing_separation.py -q
```

Results:

- WSL `compileall` passed.
- Windows `.venv` `compileall` passed.
- Windows `.venv` `--help` passed and shows `--capture-benchmark-include-encode`.
- Windows `.venv` pytest was not run because that venv reports `No module named pytest`.
- Manual helper checks passed for capture elapsed excluding encode, failures-mode success evidence skipping, and fallback evidence forcing.

Next step:

Re-run capture benchmark first. Do not run the 30-round command until benchmark confirms the corrected capture timing.

## Phase 10.3.2 Patch - YOLO Warmup + No Detection Startup Stability + CSV Header Fix

Status: implemented; Windows real-machine 30-round retest pending.

This patch addresses the first-run `no_detection_timeout` case observed after Phase 10.3.1. Capture timing was already fixed, and the remaining startup issue was the first YOLO detection running cold inside the active loop.

Implemented:
- Added default startup YOLO warmup after model load and before `loop_started`.
- Warmup records `warmup_enabled`, `warmup_ms`, `warmup_capture_ms`, `warmup_detect_ms`, `warmup_detections_count`, and `warmup_error`.
- Warmup does not move, does not click, does not increment action iterations, and is excluded from `active_loop_duration_sec`.
- Added `first_active_before_detect_ms` and `first_active_iteration_total_ms` to the summary for startup stability diagnosis.
- Changed `no_detection_timeout` to `blocked=false`; it is a normal stop reason, not a safety gate failure.
- Removed duplicate `evidence_encode_ms` from `iteration_summary.csv` fields and added CSV header uniqueness validation.

Validation performed:
- `python3 -m compileall scripts tests`: passed.
- `.\.venv\Scripts\python.exe scripts\live_finite_repeat_aim_click.py --help`: passed and includes `--no-warmup-inference`.
- `.\.venv\Scripts\python.exe -m pytest tests/test_phase10_3_2_warmup_and_csv_headers.py -q`: not run because the Windows venv does not have pytest installed.
- Manual assertions for CSV header uniqueness, active-loop timing, warmup summary fields, and `no_detection_timeout blocked=false`: passed.

No real mouse movement command was run. No click command was run. No 30-round or 160-round run was executed by Codex.

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

## Phase 10.3.6 / 10.3.7 Pressure Test Result

User-run Windows + AIMLAB 300-round pressure test result:

| Metric | Value |
| --- | ---: |
| phase | 10 |
| mode | finite_repeat_aim_click |
| stop_reason | max_consecutive_no_detection_timeouts_reached |
| iterations_requested | 300 |
| loop_iterations_attempted | 254 |
| action_iterations_attempted | 224 |
| clicks_executed | 198 |
| moves_executed | 224 |
| no_detection_timeout_count | 30 |
| after_detection_missing_retry_count | 8 |
| after_detection_missing_stop_count | 0 |
| total_retry_attempts | 26 |
| retry_limit_reached_count | 0 |
| benchmark_passed_under_400ms | true |
| active_loop_duration_sec | 73.6419 |
| average_iteration_total_ms | 287.1995 |
| median_iteration_total_ms | 264.3435 |
| p90_iteration_total_ms | 508.388 |
| average_action_round_ms | 255.9552 |
| average_before_capture_ms | 26.3892 |
| average_before_detect_ms | 10.9655 |
| average_after_capture_ms | 26.4478 |
| average_after_detect_ms | 0.0 |
| average_after_validation_ms | 7.4884 |
| evidence_mode | minimal |
| average_evidence_total_ms | 0.0 |
| fallback_click_count | 198 |
| strict_fallback_guard_retry_count | 18 |

Derived metrics from this run:

| Metric | Approx Value |
| --- | ---: |
| clicks_per_active_second | 2.6887 |
| actions_per_active_second | 3.0418 |
| click_rate_over_actions | 0.8839 |
| retry_rate_over_actions | 0.1161 |

Conclusion:
- Phase 10 high-speed finite repeat aim + click has completed real-machine pressure validation.
- The program stopped safely after AIMLAB task completion / target exhaustion, represented by consecutive no-detection timeouts.
- This stop is not a safety failure. There was no foreground block, no keyboard interrupt, no max-duration stop, and no retry-limit stop.
- Speed target is met: average iteration was about 287 ms, average action round was about 256 ms, and `benchmark_passed_under_400ms=true`.
- Bounded retry is working: after-detection-missing produced retries and did not stop the run.
- `evidence-mode=minimal` avoided I/O overhead; average evidence time was 0 ms.
- Current implementation still does not include Hotkey Runner, GUI, background automation, PID, target lock, smoothing, AIMLAB process memory reads, AIMLAB file modification, or anti-cheat bypass.

