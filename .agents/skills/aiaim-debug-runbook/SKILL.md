# Skill: aiaim-debug-runbook

## Purpose

Use this skill when AIAIM has bugs, failed validation, unstable screenshots, wrong coordinates, YOLO errors, dry-run mismatches, or blocked control gates.

This skill forces Codex to debug systematically instead of guessing.

---

## When to Trigger

Trigger this skill when the user reports:

1. Screenshot does not work.
2. AIMLAB is foreground but detection says it is not.
3. YOLO detects the wrong object.
4. Yellow ball is missed.
5. Coordinates are wrong.
6. Mouse would move to the wrong place.
7. Safety gate blocks unexpectedly.
8. Logs are missing.
9. A validation script fails.
10. The same bug keeps returning.

---

## Debugging Principles

Codex must debug in layers:

1. Confirm Phase boundary.
2. Read relevant documentation.
3. Identify the failing layer.
4. Reproduce the issue.
5. Inspect logs or artifacts.
6. Isolate cause.
7. Apply minimal fix.
8. Re-run validation.
9. Update report or runbook.

---

## Layer Order

Debug in this order unless evidence suggests otherwise:

1. Configuration
2. Environment
3. AIMLAB foreground/window state
4. Screenshot/capture
5. Dataset/image artifacts
6. YOLO inference
7. Coordinate mapping
8. Safety gate
9. Mouse control
10. Logging/reporting

---

## Required Bug Report Format

When documenting a bug, use:

```md
## Bug

## Current Phase

## Expected Behavior

## Actual Behavior

## Reproduction Steps

## Evidence

## Suspected Layer

## Root Cause

## Fix Applied

## Validation After Fix

## Remaining Risk
Gate Debug Rule

If a safety gate blocks execution, Codex must not immediately remove or weaken the gate.

Codex must first determine:

Which gate blocked the action.
Whether the block was correct.
What input caused the block.
Whether the config is correct.
Whether the foreground-window check is correct.
Whether logs are sufficient.

Only after that may Codex propose a minimal safe fix.

Coordinate Debug Rule

If coordinates are wrong, Codex must check:

Screenshot dimensions.
Detection center.
Window position.
Display scaling.
Monitor index.
Mapped screen coordinate.
Whether the coordinate is inside AIMLAB bounds.
Dry-run logs.

Do not jump directly to mouse-control changes.

Forbidden Actions

Codex must not:

Guess blindly.
Remove safety gates to make tests pass.
Skip logs.
Fix multiple layers at once without explanation.
Implement real control while debugging earlier Phases.
Claim fixed without validation.
Completion Criteria

This skill is applied correctly when the issue has a clear reproduction path, suspected layer, minimal fix, and post-fix validation.
