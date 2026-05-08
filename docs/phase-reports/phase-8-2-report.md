# Phase 8.2 Report - FOV One-Shot Robustness Validation

## Phase Goal

Phase 8.2 validates the Phase 8.1 FOV-based one-shot relative aim script across multiple Windows + AIMLAB target positions.

This phase is not a new algorithm and does not add new control capability. It reuses the Phase 8.1 one-shot FOV model and records robustness results from repeated real-machine execution.

## Test Method

Validation environment:

- AIMLAB display mode: fullscreen / borderless fullscreen
- Resolution: 1920x1080
- horizontal_fov_deg: 103
- vertical_fov_deg: 70.53
- counts_per_degree: 39.03
- global_gain: 1.0
- selection_strategy: nearest_to_crosshair
- execute mode: one-shot relative `SendInput`
- output_dir: `D:\桌面desktop\AIAIM\runs\detect\phase8_2_fov_robustness`

Each validation run used the existing Phase 8.1 one-shot FOV script to:

1. Detect yellow targets with YOLO.
2. Select the target nearest the monitor-center crosshair.
3. Convert pixel delta to FOV angular delta.
4. Convert angular delta to a single relative mouse movement.
5. Execute exactly one relative `SendInput` move.
6. Capture after-frame validation only for measurement.
7. Exit without any second correction.

## Real-machine Validation Results

Status: Phase 8.2 accepted.

| Run | before_distance_to_crosshair_px | after_distance_to_crosshair_px | distance_reduction_ratio | rounded_relative_move_dxdy | relative_aim_executed |
| --- | ---: | ---: | ---: | --- | --- |
| 20260507_183231 | 81.4231 | 4.6847 | 0.9425 | {"dx": 234, "dy": -43} | true |
| 20260507_183303 | 115.8176 | 5.7985 | 0.9499 | {"dx": -336, "dy": 27} | true |
| 20260507_183417 | 120.9481 | 4.5273 | 0.9626 | {"dx": 332, "dy": 117} | true |
| 20260507_183441 | 245.1422 | 6.0199 | 0.9754 | {"dx": 693, "dy": -53} | true |

Aggregate acceptance summary:

- 4/4 execute one-shot runs passed.
- Maximum after distance was 6.0199 px.
- Minimum distance reduction ratio was 0.9425.
- All runs executed one relative movement successfully.
- All runs ended within the Phase 8.1 preferred residual target.
- `global_gain = 1.0` remains fixed and does not need adjustment.
- `counts_per_degree = 39.03` remains fixed and does not need adjustment.
- The FOV one-shot model was stable across multiple target positions.

## Acceptance Conclusion

Phase 8.2 accepted.

The robustness validation confirms that the Phase 8.1 FOV-based one-shot model is stable under the tested fullscreen AIMLAB conditions. The worst observed after-distance was 6.0199 px, and the weakest reduction ratio was still 94.25%, so there is no current evidence requiring `global_gain` or `counts_per_degree` changes.

## Safety Boundary

Phase 8.2 did not implement or add:

- clicking
- automatic clicking
- looped movement
- closed-loop correction
- second correction
- target lock
- PID
- micro-step movement
- smooth movement
- AIMLAB process memory reading
- AIMLAB file modification
- anti-cheat bypass
- background automation

Phase 8.2 remains a one-shot validation phase only. After-frame detection is used for measurement and acceptance reporting, not for a second movement.

## Files Changed

- `docs/phase-reports/phase-8-2-report.md`
- `README.md`

No code, tests, detection logic, `SendInput` implementation, YOLO code, or Phase 8 / Phase 8.1 scripts were modified for this report update.

## Next Phase Recommendation

If the project continues, the next discussion should stay separate from Phase 8.1 / Phase 8.2 one-shot aiming. Any Phase 9 scope should be explicitly gated and limited to click gate / manual click validation discussion. Phase 8.1 should not be converted into closed-loop control, target lock, automatic clicking, PID, smoothing, or repeated correction.
