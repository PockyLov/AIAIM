# AIAIM Phase Roadmap

## 1. Purpose

This document defines the full phase-by-phase development roadmap for AIAIM.

AIAIM must be developed incrementally. Codex must not skip ahead or implement later-phase features early.

Current active phase:

```text
Phase 11 console hotkey runner implemented; Windows + AIMLAB acceptance pending
```

2. Phase 0: Project Initialization and Codex Collaboration System
Goal

Set up the project structure, documentation system, Codex collaboration rules, Agent Team plan, Skills, MCP plan, safety boundary, and Phase report mechanism.

Do
Create project directories.
Create AGENTS.md.
Create README.md.
Create documentation under docs/.
Create Skill documents under .agents/skills/.
Create MCP planning document.
Create safety boundary document.
Create docs/phase-reports/phase-0-report.md.
Do Not
Do not write screenshot code.
Do not write AIMLAB foreground detection code.
Do not write YOLO code.
Do not write dataset collection code.
Do not write mouse movement code.
Do not write mouse click code.
Do not write executable automation scripts.
Completion Criteria
Required directories exist.
AGENTS.md exists and defines project rules.
docs/ contains project planning documents.
.agents/skills/ contains project Skills.
docs/phase-reports/phase-0-report.md exists.
No core functionality code exists.
Main Difficulties
Keeping Codex inside Phase 0.
Avoiding premature implementation.
Establishing clear safety and documentation rules.
3. Phase 1: AIMLAB Foreground Stable Screenshot / Collector - completed
Goal

Build a stable screenshot collection foundation for fullscreen AIMLAB while AIMLAB is in the foreground.

Do
Design a controlled screenshot collector.
Verify AIMLAB foreground state before capture.
Capture screenshots only when AIMLAB is active.
Save screenshots to a clear data directory.
Record screenshot metadata such as time, image size, and foreground state.
Support manual trigger or simple controlled collection.
Keep behavior observable and logged.
Do Not
Do not train YOLO.
Do not run YOLO inference.
Do not move the mouse.
Do not click.
Do not build a full closed loop.
Do not bypass foreground-window checks.
Completion Criteria
AIMLAB foreground screenshots can be captured reliably.
Screenshots have correct dimensions.
Capture metadata is recorded.
Collector does not perform any mouse control.
Failure cases are documented.
Main Difficulties
Fullscreen capture reliability.
Foreground-window verification.
DPI scaling.
Multi-monitor behavior.
Capture performance.
4. Phase 2: Dataset Preparation / Annotation Pipeline - completed
Goal

Prepare Phase 1 AIMLAB screenshots as a reviewed YOLO-format yellow-ball dataset structure.

Do
Use Phase 1 screenshots and metadata from `data/raw/screenshots/`.
Define yellow-ball labeling rules.
Organize raw images and YOLO labels.
Create selected image, prelabel, and YOLO dataset directories.
Use OpenCV offline pre-labeling assistance on static screenshots.
Generate draft YOLO labels and review overlay images.
Require human review before labels are treated as final.
Create train/validation/test split.
Create dataset configuration.
Validate image-label consistency.
Produce dataset summary report.
Do Not
Do not train YOLO.
Do not run YOLO inference.
Do not run real-time detection.
Do not move the mouse.
Do not click.
Do not implement coordinate mapping.
Do not implement auto-aim or closed-loop automation.
Do not use OpenCV pre-labels as final truth without human review.
Completion Criteria
Dataset directory structure is clear.
Images and labels match.
YOLO labels use correct normalized format.
Train/validation/test split exists.
Dataset summary exists.
Dataset is ready for Phase 3 only after human review and validation.
Main Difficulties
Label quality.
Sufficient data coverage.
Yellow target boundary consistency.
Avoiding false labels.
Efficient manual or semi-automatic labeling workflow.
5. Phase 3: YOLO Training / Baseline Evaluation - baseline accepted
Goal

Train a YOLO model to detect yellow AIMLAB targets and validate it on offline images.

Do
Choose YOLO implementation and version.
Configure dataset.
Train model offline.
Save model artifacts under models/.
Run offline inference on validation images.
Generate detection outputs.
Analyze false positives and false negatives.
Write model report.
Do Not
Do not connect YOLO to real-time mouse control.
Do not perform real clicking.
Do not assume model is reliable without validation.
Do not overwrite model artifacts without metadata.
Completion Criteria
A trained model exists.
Offline inference works on test images.
Detection boxes and confidence scores are produced.
Model metadata is documented.
Validation results are recorded.
Known limitations are documented.
Current Result
YOLO11n baseline training completed on `data/yolo/aimlab_yellow_ball_v1_1/data.yaml`.
The best checkpoint exists at `runs/detect/phase3_yolo11n_baseline/weights/best.pt`.
Offline validation metrics were recorded in `runs/detect/phase3_eval_metrics.csv`.
Offline prediction review images were generated for val/test at `conf=0.25` and `conf=0.50`.
Manual prediction review was completed by the user, focused on test `conf=0.25` and test `conf=0.50`.
The rendered blue review labels are visually large and cover part of some small yellow balls, but prediction positions and counts are acceptable for this baseline.
Phase 3 baseline accepted.
No immediate retraining is required.
No immediate return to Phase 2.5 is required.
`imgsz=960` is not needed at this point, but remains a future option if small-ball misses become obvious.
The model is acceptable for Phase 4 detect-only planning.
This does not mean the system is ready for real-time detection or mouse control.
Main Difficulties
Small-target detection.
Overfitting.
Dataset size.
Yellow background false positives.
Balancing speed and accuracy.
6. Phase 4: Offline Detect-Only Inference Pipeline + Coordinate Contract v0 - implemented / accepted candidate
Goal

Run YOLO inference on offline saved images and output standard detection JSON, clean review images, summary records, and an explicit input-image pixel coordinate contract.

Do
Load Phase 3 `best.pt`.
Run detect-only inference on a single offline image.
Run detect-only inference on an offline image directory.
Output `bbox_xyxy`, `bbox_xywh`, center, confidence, and validity checks.
Write per-image detection JSON.
Write clean review images without large label blocks.
Write `summary.csv`.
Write `run_config.json`.
Define coordinate space as input image pixels only.
Do Not
Do not do real-time screenshots.
Do not connect to AIMLAB live screen.
Do not connect to the Phase 1 collector live loop.
Do not move the mouse.
Do not click.
Do not generate mouse targets.
Do not generate click targets.
Do not implement coordinate mapping.
Do not implement auto-aim.
Do not implement closed-loop automation.
Do not attempt anti-cheat bypass.
Do not enter Phase 5.
Completion Criteria
Offline single-image inference runs.
Offline directory inference runs.
Per-image JSON is generated.
Clean review images are generated.
`summary.csv` and `run_config.json` are generated.
Detection bbox and center validity are checked.
Coordinate contract clearly marks image pixel coordinates only.
No mouse control occurs.
No live screen connection occurs.
Phase report and runbook exist.
Current Result
Single-image offline inference passed on one test image.
Batch offline inference passed on 38 test images.
Default output exists under `runs/detect/phase4_offline_detection/`.
The batch run generated 38 JSON files, 38 clean review images, and 225 detections at `conf=0.25`.
The optional `conf=0.50` comparison generated 185 detections under `runs/detect/phase4_offline_detection_conf050/`.
All checked bbox and center coordinates were valid input image pixel coordinates.
Main Difficulties
Maintaining a strict offline-only boundary.
Avoiding accidental screen or mouse coordinate interpretation.
Keeping review images readable for small targets.
Handling zero-detection images without failure.
Preserving Phase 5 mapping as a separate future phase.
7. Phase 5: Offline Coordinate Mapping / Geometry Validation - implemented
Goal

Validate offline geometry between Phase 4 image-pixel detections and Phase 1 metadata-derived monitor/window rectangles.

Do
Read Phase 4 detection JSON.
Match Phase 1 metadata by source image stem.
Validate screenshot size, monitor rect, and window rect.
Validate detection bbox and center.
Compute image-pixel center.
Compute monitor-relative center.
Compute window-relative center.
Write mapped JSON.
Write metadata match report.
Write geometry summary.
Write Phase 5 summary.
Optionally write geometry review images.
Do Not
Do not move the mouse.
Do not click.
Do not output mouse targets.
Do not output click targets.
Do not implement auto-aim.
Do not implement closed-loop automation.
Do not connect to AIMLAB live screen.
Do not connect Phase 1 collector live loop.
Do not implement screen-coordinate or mouse-coordinate mapping.
Completion Criteria
All Phase 4 JSON files are processed.
Metadata match report exists.
Geometry summary exists.
Mapped JSON exists.
Phase summary exists.
Coordinate assumptions are documented.
Outputs explicitly mark screen coordinate, mouse coordinate, and click target as false.
No mouse control occurs.
Current Result
38 Phase 4 JSON files were processed.
38 metadata files were matched.
225 detections were mapped.
225 centers were inside image bounds.
225 centers were inside bbox bounds.
225 bboxes were inside image bounds.
225 centers were inside window-relative bounds.
Review images were generated.
Phase 1 `window_rect` extends slightly outside `monitor_rect`, so rect validation produced warnings and mapping confidence is medium.
Main Difficulties
Fullscreen border/bounds.
Coordinate origin differences.
Keeping screen/mouse coordinates out of Phase 5.
Verifying geometry without live input or mouse movement.
8. Phase 5.5: Client Area / Content Area Coordinate Contract Confirmation - completed
Goal

Confirm the coordinate contract after Phase 5 and before any future Phase 6 planning.

Do
Review Phase 1 metadata and Phase 5 geometry outputs.
Document the final interpretation of the Phase 5 geometry warning.
Confirm `image_pixel` as the original trusted YOLO detection coordinate.
Confirm `monitor_relative` as the main coordinate basis candidate for future live read-only detection in the current full-monitor capture mode.
Record raw `window_rect`, `window_relative`, and `work_rect` as debug / review / warning information only.
Record that client area / content area needs a separate future contract discussion before any movement phase.
Do Not
Do not implement Phase 6.
Do not run realtime detection.
Do not connect to AIMLAB live screen.
Do not connect Phase 1 collector live loop.
Do not move the mouse.
Do not click.
Do not output mouse targets.
Do not output click targets.
Do not implement auto-aim.
Do not implement closed-loop automation.
Do not attempt anti-cheat bypass.
Completion Criteria
Phase 5.5 report exists.
Phase 5.5 runbook exists.
README, roadmap, and safety boundary mention Phase 5.5.
The coordinate contract is explicit.
The 8 px Windows windowed fullscreen / maximized-window outer-bounds warning is documented.
Phase 6 remains not started.
Current Result
Phase 5 accepted with geometry warning.
38/38 metadata records matched.
225/225 detections mapped.
225/225 detections had centers inside window-relative bounds.
Default `tolerance_px=5` produced rect warnings because raw `window_rect = -8,-8,1928,1040` extends beyond `monitor_rect = 0,0,1920,1080`.
Comparison `tolerance_px=10` validates the observed geometry envelope.
`image_pixel` and `monitor_relative` are the future read-only coordinate basis candidates.
Raw `window_rect` and `window_relative` are debug-only and not action coordinates.
Main Difficulties
Keeping raw Windows outer bounds distinct from content/client-area geometry.
Preventing window-relative debug data from becoming an action coordinate.
Keeping Phase 6 out of Phase 5.5.
9. Phase 6: Live Read-Only Detection Pipeline - implemented / Windows acceptance pending
Goal

Run live read-only YOLO detection against the current AIMLAB monitor screenshot while AIMLAB is foreground.

Do
Reuse Phase 1 AIMLAB window detection.
Reuse Phase 1 foreground gate.
Reuse Phase 1 monitor detection and full-monitor capture.
Load the Phase 3 `best.pt` checkpoint.
Run one-frame live read-only detection.
Run finite-loop live read-only detection with a fixed max frame count.
Write per-frame detection JSON.
Write optional clean review images.
Write `live_summary.csv`.
Write `phase6_summary.json`.
Keep `image_pixel` and `monitor_relative` as detection coordinate spaces.
Do Not
Do not implement Phase 7.
Do not move the mouse.
Do not click.
Do not output mouse targets.
Do not output click targets.
Do not implement auto-aim.
Do not implement target lock.
Do not implement closed-loop automation.
Do not attempt anti-cheat bypass.
Do not read process memory.
Do not inject into AIMLAB.
Do not modify AIMLAB files.
Do not implement infinite control loops.
Completion Criteria
Single-frame mode writes JSON / review image / summary when AIMLAB is foreground.
Blocked frames are recorded cleanly when AIMLAB is missing or not foreground.
Finite-loop mode stops after `max_frames`.
Each detection includes `center_image_px` and `center_monitor_px`.
Each detection marks screen, mouse, and click-target authorization as false.
No mouse control occurs.
No click behavior exists.
Current Result
`scripts/live_readonly_detect.py` exists.
Local syntax and CLI help checks passed.
A local WSL blocked-gate run completed with `blocked_frames=1` and `total_detections=0`.
Windows + AIMLAB foreground single-frame and finite-loop acceptance still needs to be run in the desktop environment.
Main Difficulties
Maintaining a strict read-only boundary.
Avoiding mouse or click target semantics in detection output.
Keeping the live loop finite.
Handling Windows foreground gate failures clearly.
Separating Phase 6 from later action phases.
10. Phase 7: Direct Cursor Positioning - implemented / Windows acceptance pending
Goal

Move the Windows cursor once to the selected yellow-ball target center under explicit gates.

Do
Keep dry-run as default.
Require config `allow_mouse_move=true` for real movement.
Require CLI `--execute-move`.
Require CLI `--confirm-local-aimlab-only`.
Require AIMLAB foreground gate.
Capture exactly one frame.
Run YOLO once.
Choose one primary target.
Compute `planned_cursor_screen_px`.
Move the cursor once only if all gates pass.
Write JSON, review image, and summary outputs.
Do Not
Do not click.
Do not implement continuous movement.
Do not implement target lock.
Do not implement auto-aim loop.
Do not implement move-detect-move correction.
Do not implement closed-loop automation.
Do not bypass anti-cheat.
Do not read process memory.
Do not inject into AIMLAB.
Do not modify AIMLAB files.
Completion Criteria
Default dry-run produces planned cursor output without moving the cursor.
Non-foreground AIMLAB blocks movement.
Execute mode moves once only when all gates pass.
No click behavior exists.
Program exits after one attempt.
Outputs include move gate, planned cursor coordinate, and before/after cursor coordinates.
Current Result
`scripts/live_direct_cursor_position.py` exists.
`config/phase7-cursor-positioning.json` defaults `allow_mouse_move=false`.
Static syntax and CLI checks passed.
WSL dry-run blocked validation wrote outputs with `move_executed=false`.
Windows + AIMLAB dry-run and execute-move acceptance still needs to be run.
Main Difficulties
Preventing wrong cursor movements.
Target may move or disappear.
False positives.
Timing and latency.
Keeping the action one-shot instead of a loop.
11. Phase 7.5: One-Shot Relative Mouse Actuation Feasibility - accepted
Goal

Verify whether AIMLAB responds to one fixed relative mouse movement and estimate the resulting screen target shift.

Do
Use AIMLAB foreground gate.
Capture one before frame.
Run YOLO on the before frame.
Select a reference target nearest to crosshair center.
Optionally send exactly one `SendInput` relative mouse move when gates pass.
Capture one after frame.
Run YOLO on the after frame.
Estimate observed target shift and `px_per_mouse_count` when matching succeeds.
Write before / after review images and JSON.
Do Not
Do not click.
Do not implement auto-aim.
Do not implement target lock.
Do not implement looped movement.
Do not implement closed-loop correction.
Do not send a second movement after after-frame detection.
Do not bypass anti-cheat.
Do not read process memory.
Do not inject into AIMLAB.
Do not modify AIMLAB files.
Completion Criteria
Dry-run records planned relative move without sending input.
Execute mode sends one relative movement only when all gates pass.
Before / after frames and detections are saved.
Observed shift is computed or manual review is requested.
Program exits after one attempt.
Current Result
`scripts/live_relative_mouse_feasibility.py` exists.
`config/phase75-relative-mouse-feasibility.json` defaults `allow_relative_mouse_move=false`.
Static syntax, help, and JSON config checks passed.
WSL dry-run blocked validation wrote outputs with `relative_move_executed=false` and `sendinput_attempted=false`.
Windows + AIMLAB dx=100 and dy=100 execute-relative-move acceptance passed; AIMLAB gameplay responds to SendInput relative movement.
Main Difficulties
Matching targets before and after movement.
Sensitivity depends on AIMLAB and Windows settings.
Keeping the test one-shot and not an aiming loop.
12. Phase 8: One-Shot Relative Aim to Target - implemented / Windows acceptance pending
Goal

Use Phase 7.5 `SendInput` relative-mouse calibration to compute and optionally send one relative mouse movement toward the YOLO target nearest the monitor-center crosshair.

Do
Use AIMLAB foreground gate.
Capture one before frame.
Run YOLO on the before frame.
Select target by nearest-to-crosshair.
Compute target delta from monitor-center crosshair.
Convert delta to one relative mouse movement using `px_per_mouse_count_x/y`.
Optionally send exactly one `SendInput` relative movement when all gates pass.
Optionally capture one after frame for validation only.
Write JSON, CSV, and review images.
Do Not
Do not click.
Do not implement automatic clicking.
Do not implement target lock.
Do not implement looped movement.
Do not implement closed-loop correction.
Do not send a second movement after after-frame detection.
Do not use `SetCursorPos` for AIMLAB gameplay actuation.
Do not bypass anti-cheat.
Do not read process memory.
Do not modify AIMLAB files.
Current Result
`scripts/live_one_shot_relative_aim.py` exists.
`config/phase8-one-shot-relative-aim.json` defaults `allow_relative_mouse_move=false`.
Windows + AIMLAB dry-run and execute acceptance still needs to be run.
Do not optimize before measuring.
Completion Criteria
Performance baseline exists.
Optimization changes are measured.
Data feedback process exists.
Model versions are documented.
Regressions are checked.
Safety remains intact.
Main Difficulties
Speed vs. accuracy tradeoff.
Dataset drift.
Reproducible benchmarking.
Long-run stability.
Log and artifact volume control.
13. Phase 9: Tooling, Reporting, and Long-Term Maintenance
Goal

Turn AIAIM from an experimental project into a maintainable local tool with clear configuration, reporting, and operational documentation.

Do
Standardize project commands.
Standardize configuration files.
Standardize run logs.
Standardize report format.
Create long-term runbook.
Optionally add local dashboard.
Version models and datasets.
Document maintenance workflow.
Do Not
Do not turn the project into an online cheating tool.
Do not remove local-only safety boundary.
Do not remove dry-run default.
Do not hide control behavior.
Do not make dashboard features more important than core safety.
Completion Criteria
Project can be resumed from documentation.
Configuration is understandable.
Logs and reports are consistent.
Model versions are traceable.
Safety defaults are stable.
Long-term maintenance guide exists.
Main Difficulties
Keeping docs synchronized with code.
Avoiding tool bloat.
Managing many run artifacts.
Keeping safety visible.
Making future development reproducible.
14. Global Phase Rules

Across all phases:

Read AGENTS.md before modifying the project.
Stay inside the active Phase.
Keep dry-run as default.
Keep safety gates explicit.
Keep modules layered.
Write or update a Phase report.
Do not claim unverified behavior works.
Record future ideas as notes instead of implementing them early.

## Phase 9: One-Shot Click Gate - accepted

Goal: Add a strictly gated single left click after the accepted Phase 8.1 / Phase 8.2 FOV one-shot aim flow.

Do:
- Reuse Phase 8.1 FOV one-shot target selection and relative movement.
- Require explicit `--execute-move`, `--allow-click`, and `--confirm-local-aimlab-only` for real click.
- Require after-move detection and `after_distance_to_crosshair_px <= click_threshold_px`.
- Write JSON, CSV, and review outputs.

Do Not:
- Do not add loops, repeats, hotkey runner, target lock, PID, second correction, smooth movement, background automation, process memory reading, AIMLAB file modification, or anti-cheat bypass.

Current Result:
- Implementation added in `scripts/live_one_shot_click_gate.py`.
- Windows + AIMLAB real-machine acceptance passed. Accepted run: `20260507_202455`; `relative_aim_executed=True`, `click_gate_passed=True`, `click_executed=True`.
