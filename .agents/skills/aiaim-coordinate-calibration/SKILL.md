# Skill: aiaim-coordinate-calibration

## Purpose

Use this skill when AIAIM needs to map a detected yellow ball center from screenshot coordinates to actual screen or mouse coordinates.

This skill is especially important before any real mouse movement.

---

## When to Trigger

Trigger this skill when the task involves:

1. Screenshot pixel coordinates.
2. AIMLAB window coordinates.
3. Fullscreen coordinates.
4. DPI scaling.
5. Multi-monitor behavior.
6. Mouse destination coordinates.
7. Dry-run coordinate logs.
8. Coordinate overlay/debug artifacts.

---

## Core Principle

Codex must never assume all coordinate systems are identical.

AIAIM must distinguish:

1. Screenshot coordinates.
2. Window-local coordinates.
3. Display coordinates.
4. DPI-scaled coordinates.
5. Mouse control coordinates.

---

## Required Coordinate Documentation

Any future coordinate module must document:

1. Input coordinate system.
2. Output coordinate system.
3. Image width and height.
4. Screen width and height.
5. DPI scaling assumptions.
6. Active monitor.
7. Window foreground state.
8. Whether AIMLAB is fullscreen.
9. Conversion formula or mapping logic.
10. Dry-run evidence.

---

## Dry-Run First Rule

Before any real mouse movement, coordinate mapping must pass dry-run validation.

Dry-run logs should include:

1. Timestamp.
2. Screenshot size.
3. Detection box.
4. Detected center in image coordinates.
5. Mapped screen coordinate.
6. Foreground-window status.
7. Whether real control was allowed.
8. Final action decision.

---

## Visual Debug Rule

Before real movement, the project should produce visual or textual debug evidence, such as:

1. Saved screenshot with detection box.
2. Saved screenshot with target center marker.
3. JSON run log with mapped coordinate.
4. Optional overlay preview in later tools.

---

## Safety Dependency

Coordinate mapping is not enough to permit real control.

Before real mouse movement, the following must also pass:

1. Safety gate.
2. Foreground-window check.
3. Config permission.
4. Emergency stop availability.
5. Logging enabled.

---

## Forbidden Actions

Codex must not:

1. Move the mouse based only on unverified coordinates.
2. Click based only on a detection result.
3. Assume DPI scaling is 100%.
4. Assume the primary monitor is always the active monitor.
5. Skip dry-run logs.
6. Implement coordinate mapping during Phase 0.

---

## Completion Criteria

This skill is applied correctly when coordinate conversion is explicit, testable, logged, and validated before being connected to any real control behavior.
