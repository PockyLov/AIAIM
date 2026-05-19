# Phase 13 Report: Smooth Pursuit & Dynamic Click Gate

## Goal
Refactor the AIAIM main loop to support Smooth Pursuit (firing at moving targets) by integrating the `TargetTracker` prediction model and overhauling the click trigger logic to fire dynamically during cursor movement.

## Work Completed
1. **`TargetTracker` Implementation**:
   - Authored `src/aiaim_control/target_tracker.py` to calculate moving target velocities using a frame history queue and simple linear regression.
   - Outputs `predicted_x` and `predicted_y` taking `latency_compensation_sec` into account.

2. **Smooth Pursuit Movement**:
   - Refactored `live_finite_repeat_aim_click.py`. Instead of instantaneously moving `dx, dy` using `ctypes`, the movement is chunked into 20px steps allowing polling mid-movement.
   - Intercepted the original `compute_fov_relative_move` invocation to lock onto the `predicted` target coordinate instead of the raw `chosen_center`.

3. **Dynamic Click Gate Refactor (Raw-Input FPS Safe)**:
   - Dropped the rigid `time.sleep` after move.
   - Introduced a dynamic click gate inside the movement loop. Removed the initial `GetCursorPos` reliance, as 3D FPS engines lock the OS cursor. Instead, implemented a mathematical fallback: the script tracks the exact accumulated chunked movement (`acc_dx`, `acc_dy`) against the target required distance.
   - If the remaining `math.hypot` distance between the crosshair and the predicted target drops below `--click-threshold-px`, it fires immediately mid-flight.
   - Bypassed the secondary redundant fallback click if the dynamic click gate already succeeded.
   - Sourced the CLI argument `--latency-compensation-sec` to allow real-time tuning.

4. **Documentation**:
   - Created `docs/runbooks/phase-13-dynamic-prediction-runbook.md` explaining how `LATENCY_COMPENSATION_SEC` works and how to tune it based on trailing/overshooting misses.

## Validation Performed
- **Pytest**: Executed `pytest` successfully. All 92 existing tests across various click gates and missing retries passed flawlessly, confirming that the dynamic gate implementation does not break existing safety mechanics.
- **Code Compilation**: Executed `python -m compileall scripts` successfully to guarantee no syntax breakages.

## What Was Intentionally Not Done
- I did not modify the `after_capture` evidence and fallback retry mechanics. If the dynamic gate fails, the system safely falls back to standard validation to retain all Phase 10 logic.
- Target tracking logic was kept linear and lightweight. Complex predictive Kalman filters were avoided to keep execution times under the 200ms benchmark target established in Phase 12.

## Remaining Risks
- The exact accuracy of mathematical distance mapping relies on consistent Windows sensitivity settings. The fallback bypasses `GetCursorPos`, making it fully FPS raw-input safe, but heavily dependent on the FOV mapping algorithm staying precise during high velocity target tracking.

## Next Phase Conditions
- Validation via a live run on a moving target scenario inside AimLab.
- If hit rate on moving targets exceeds 70%, we can advance to final packaging and testing.
