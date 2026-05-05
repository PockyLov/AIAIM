# AIAIM Debug Runbook

Current phase: Phase 0.

## General Debug Rules

1. Read `AGENTS.md`, `docs/safety-boundary.md`, and the active phase report before changing anything.
2. Confirm the active Phase.
3. Keep dry-run as the default.
4. Do not skip safety gates.
5. Record what changed and how it was verified.

## Phase 0 Debug Checklist

- Confirm required directories exist.
- Confirm required documentation files exist.
- Confirm skills exist under `.agents/skills/`.
- Confirm no core functionality code exists.
- Confirm safety boundary is documented.

## Future Debug Categories

- Capture failures
- Foreground validation failures
- Dataset quality issues
- YOLO inference mismatch
- Coordinate calibration mismatch
- Movement gate failures
- Click gate failures
- Emergency stop verification

Each future category must include symptoms, likely causes, diagnostic steps, and rollback guidance before it is considered operational.
