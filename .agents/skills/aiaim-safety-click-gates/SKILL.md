# Skill: aiaim-safety-click-gates

## Purpose

Use this skill whenever AIAIM work involves dry-run behavior, mouse movement, clicking, foreground-window validation, emergency stop, or any real control behavior.

This is a safety-critical skill.

---

## When to Trigger

Trigger this skill when the user asks about:

1. Mouse movement.
2. Mouse clicking.
3. Real execution.
4. Dry-run mode.
5. Safety gates.
6. Foreground-window validation.
7. Emergency stop.
8. Preventing accidental clicks.
9. Control logs.
10. Phase 5, Phase 6, or Phase 7 work.

---

## Default Rule

The default project mode is always:

```text
dry-run = true

Real mouse movement and real clicking must be disabled by default.

Required Gates Before Real Mouse Movement

Before real mouse movement is allowed in a later Phase, all of the following must pass:

User explicitly requested the correct Phase.
Config explicitly enables real movement.
Dry-run validation has already passed.
AIMLAB is confirmed foreground.
Coordinate mapping is validated.
Emergency stop is available.
Logs are enabled.
The action is bounded and reversible where possible.
Required Gates Before Real Clicking

Before real clicking is allowed in Phase 7 or later, all of the following must pass:

All real movement gates pass.
Config explicitly enables real click.
Click is disabled by default.
The target is detected with sufficient confidence.
The mapped coordinate is inside AIMLAB bounds.
No unexpected foreground window is active.
Emergency stop is available.
Click event is logged.
A dry-run record exists before real click testing.
Emergency Stop Principle

Future real-control code must include an emergency stop mechanism.

The emergency stop must be documented clearly for the user.

If emergency stop is unavailable or untested, real clicking must not be enabled.

Logging Requirement

Every future control decision must log:

Timestamp.
Detected target.
Confidence.
Source coordinate.
Mapped coordinate.
Foreground-window state.
Dry-run state.
Movement permission.
Click permission.
Final action taken or blocked.
Reason if blocked.
Forbidden Actions

Codex must not:

Default to real click.
Hide click behavior behind unclear variable names.
Remove safety checks.
Disable logs.
Run control behavior without foreground validation.
Implement stealth automation.
Add anti-cheat bypass logic.
Add online-game automation logic.
Implement mouse control during Phase 0.
Completion Criteria

This skill is applied correctly when any future real-control behavior is explicit, gated, logged, reversible where possible, and disabled by default.
