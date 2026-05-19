# Phase 13 Runbook: Dynamic Prediction & Smooth Pursuit

## Overview

This runbook outlines how to operate the AIAIM system utilizing the Phase 13 enhancements. Phase 13 introduces real-time target velocity tracking (`TargetTracker`) and dynamic click gates to seamlessly intercept moving targets.

The traditional blocking paradigm ("stop to validate then click") has been abandoned. Instead, the `TargetTracker` computes velocity from history and injects a predicted coordinate based on the `LATENCY_COMPENSATION_SEC` parameter, and the mouse movement is chunked to allow a continuous click gate polling routine mid-movement.

## Running Phase 13

Execute the standard loop with the new dynamic parameter:

```powershell
.\.venv\Scripts\python.exe scripts/live_finite_repeat_aim_click.py --execute-move --allow-click --confirm-local-aimlab-only --latency-compensation-sec 0.05 --click-threshold-px 10.0
```

## Parameter: LATENCY_COMPENSATION_SEC

**The most crucial parameter in Phase 13 is `--latency-compensation-sec`.**

This value dictates how far ahead in time the `TargetTracker` extrapolates the current target trajectory. Since hardware, system, and display input latency are inherent delays between seeing the frame and Windows physically registering the click:
- The system must predict where the target *will be* at the time the OS actually dispatches the click.
- Setting `--latency-compensation-sec` too low means the click will trail behind fast-moving targets (underaim).
- Setting it too high will cause the model to overshoot the target.

### Tuning LATENCY_COMPENSATION_SEC

1. **Start with 0.05 (50ms)**: This is a safe baseline for typical 144Hz setups with moderate hardware rendering latency.
2. **Review Misses in `data/feedback/phase12_failures/`**:
   - If evidence shows the crosshair was consistently *behind* the target's trajectory at the moment of click, **increase** the value (e.g., 0.06 or 0.08).
   - If the crosshair *overshot* the target before the click registered, **decrease** the value (e.g., 0.03).
3. **Hardware Considerations**: If using the TensorRT/ONNX fast-path (Phase 12.5), system latency is heavily reduced. You might need to decrease `latency-compensation-sec`.

## Dynamic Click Gate

The click gate is no longer limited to `after_capture`. Instead:
1. `dx, dy` inputs are chopped into micro-movements.
2. A fast polling `ctypes.windll.user32.GetCursorPos()` operation checks the active screen distance to the `predicted_x, predicted_y` anchor.
3. If `< click-threshold-px` triggers mid-flight, the system instantly fires and aborts the remaining micro-moves asynchronously.

## Safety Red Lines
- The Phase 11 Hotkey Kill Switch (`phase11_hotkey_runner.py`) remains the absolute authority over the process.
- All iteration limits (`max_iterations`, `max_duration_sec`) remain rigidly enforced. 
