# AIAIM Phase Roadmap

## 1. Purpose

This document defines the full phase-by-phase development roadmap for AIAIM.

AIAIM must be developed incrementally. Codex must not skip ahead or implement later-phase features early.

Current active phase:

```text
Phase 3 baseline accepted; Phase 4 detect-only planning allowed, implementation not started
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
6. Phase 4: Real-Time YOLO Detect-Only - future
Goal

Connect screenshot capture to YOLO inference and output real-time detection results without controlling the mouse.

Do
Run real-time capture.
Run YOLO inference on captured frames.
Output detection box, center point, and confidence.
Save detect-only logs.
Optionally save debug images with detection overlays.
Measure basic latency and FPS.
Do Not
Do not move the mouse.
Do not click.
Do not implement coordinate-to-control behavior.
Do not run hidden background automation.
Do not disable safety rules for speed.
Completion Criteria
Real-time detect-only pipeline runs.
Detection results are logged.
Target center is computed in screenshot coordinates.
No mouse control occurs.
Performance and failure cases are documented.
Main Difficulties
Capture/inference latency.
Detection stability.
Confidence threshold tuning.
Frame rate limitations.
Handling missed detections.
7. Phase 5: Coordinate Mapping Dry-Run - future
Goal

Map detected yellow-ball center from screenshot coordinates to screen coordinates in dry-run mode only.

Do
Define screenshot coordinate system.
Define screen coordinate system.
Account for fullscreen window bounds.
Account for DPI scaling.
Account for monitor configuration.
Convert detected center to mapped screen coordinate.
Log mapping results.
Generate dry-run coordinate validation evidence.
Do Not
Do not move the mouse.
Do not click.
Do not assume screenshot coordinates equal mouse coordinates.
Do not skip dry-run validation.
Do not remove safety gate placeholders.
Completion Criteria
Coordinate mapping outputs are logged.
Mapped coordinates are plausibly inside AIMLAB bounds.
Dry-run evidence exists.
Coordinate assumptions are documented.
QA validation says Phase 6 is safe to start.
Main Difficulties
DPI scaling.
Fullscreen border/bounds.
Multiple monitors.
Coordinate origin differences.
Verifying mapping accuracy without real movement.
8. Phase 6: Real Mouse Movement Without Clicking
Goal

Allow real mouse movement to the detected target coordinate under strict safety gates, but do not click.

Do
Keep dry-run as default.
Add explicit config switch for real movement.
Validate AIMLAB foreground state.
Validate mapped coordinate is inside AIMLAB bounds.
Add emergency stop.
Move mouse only when all gates pass.
Log every movement decision.
Do Not
Do not click.
Do not enable real movement by default.
Do not move mouse when AIMLAB is not foreground.
Do not weaken safety gates.
Do not run uncontrolled high-frequency movement.
Completion Criteria
Default behavior remains dry-run.
Real movement requires explicit enablement.
Mouse moves only under valid gate conditions.
Emergency stop is documented and tested.
All movement decisions are logged.
No click behavior exists.
Main Difficulties
Preventing accidental movement outside AIMLAB.
Movement accuracy.
Emergency stop reliability.
Foreground-window race conditions.
User safety and observability.
9. Phase 7: Real Click Closed Loop
Goal

Implement a minimal controlled closed loop: detect yellow ball, map coordinate, move mouse, and click under strict safety gates.

Do
Keep real click disabled by default.
Add explicit config switch for real click.
Require all movement gates to pass.
Verify target confidence.
Verify mapped coordinate is inside AIMLAB.
Perform click only when all gates pass.
Log every click decision.
Provide emergency stop.
Produce closed-loop report.
Do Not
Do not use the tool for multiplayer cheating.
Do not bypass anti-cheat.
Do not manipulate leaderboards.
Do not hide automation behavior.
Do not remove dry-run fallback.
Do not click when AIMLAB is not foreground.
Completion Criteria
Real click requires explicit enablement.
Default mode remains dry-run.
Clicks occur only when all safety gates pass.
Emergency stop is available.
Click logs are complete.
Failure cases safely block actions.
Closed-loop behavior is documented.
Main Difficulties
Preventing wrong clicks.
Target may move or disappear.
False positives.
Timing and latency.
Safe loop frequency.
10. Phase 8: Performance Optimization and Data Feedback Loop
Goal

Improve speed, stability, accuracy, and dataset quality through performance tuning and data feedback.

Do
Measure capture latency.
Measure inference latency.
Measure end-to-end loop timing.
Tune confidence thresholds.
Save false positive / false negative cases.
Feed difficult samples back into dataset.
Retrain or fine-tune model when needed.
Compare model versions.
Generate performance reports.
Do Not
Do not weaken safety gates for speed.
Do not hide failed detections.
Do not delete failure evidence.
Do not skip regression validation.
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
11. Phase 9: Tooling, Reporting, and Long-Term Maintenance
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
12. Global Phase Rules

Across all phases:

Read AGENTS.md before modifying the project.
Stay inside the active Phase.
Keep dry-run as default.
Keep safety gates explicit.
Keep modules layered.
Write or update a Phase report.
Do not claim unverified behavior works.
Record future ideas as notes instead of implementing them early.
