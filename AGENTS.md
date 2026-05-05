# AIAIM - Codex Collaboration Rules

## 0. Project Identity

AIAIM is a local offline AIMLAB experiment project.

The long-term goal is to detect yellow targets appearing inside fullscreen AIMLAB, estimate the target center, and eventually move/click the mouse under strict safety gates.

This project is only for local offline experimentation.

AIAIM must not be used for:

- Anti-cheat bypass
- Leaderboard manipulation
- Multiplayer cheating
- Online competitive advantage
- Hidden automation
- Any behavior outside the user's local offline AIMLAB experiment

Current phase:

```text
Phase 2 only
```

1. Hard Constraints

Codex must always obey these constraints:

Default to dry-run.
Real click behavior is never allowed by default.
Real mouse movement is never allowed by default.
Safety gates must not be deleted, bypassed, weakened, hidden, or renamed unclearly.
Every Phase must produce a report under:
docs/phase-reports/
Do not work across Phase boundaries without explicit user approval.
Before modifying the project, read existing relevant documents first.
After each completed task, report:
What was done
Which files changed
How it was verified
Remaining issues
Coordinates, screenshot capture, YOLO, mouse movement, and mouse click control must be modular and layered.
Phase 0 must not write core functionality code.
2. Phase 0 Scope

During Phase 0, Codex may create or modify only documentation and project-planning files.

Allowed in Phase 0:

Project directory structure
AGENTS.md
README.md
Documents under docs/
Phase reports under docs/phase-reports/
Runbooks under docs/runbooks/
Skill documents under .agents/skills/
Placeholder README.md files inside config/, data/, models/, runs/, and logs/

Forbidden in Phase 0:

Screenshot code
AIMLAB foreground detection code
YOLO code
Dataset collection code
Mouse movement code
Mouse click code
Automation scripts
Real execution logic
Any .py, .js, .ts, .ps1, or executable core-functionality code unless explicitly approved for documentation tooling only

Phase 0 is complete only when the collaboration system, documentation structure, Agent Team plan, Skills, MCP plan, safety boundary, roadmap, and Phase 0 report exist.

3. Safety Position

AIAIM must remain dry-run by default.

Future real mouse movement and clicking require all of the following:

Explicit configuration switch
Dry-run fallback
Safety gate checks
Structured logs
AIMLAB foreground window verification
Emergency stop mechanism
Clear runbook
Clear phase report
User explicitly entering the correct later Phase

Real clicking must never be introduced casually.

Real clicking must never be enabled by default.

4. Phase Discipline

Codex must work phase by phase.

If a task asks for functionality from a later Phase, Codex must stop and record that the request is out of scope for the current Phase unless the user explicitly changes the active Phase.

Examples:

During Phase 0, do not write screenshot code.
During Phase 1, do not train YOLO.
During Phase 2, do not implement mouse movement.
During Phase 2, do not train YOLO or run YOLO inference.
During Phase 3, do not implement real-time clicking.
During Phase 4, do not control the mouse.
During Phase 5, do not move the mouse.
During Phase 6, do not click.
During Phase 7, do not remove safety gates.

Future-Phase ideas should be documented as notes, not implemented early.

5. Documentation-First Rule

Before modifying files, Codex must read:

AGENTS.md
README.md, if it exists
Relevant files under docs/
Relevant latest report under docs/phase-reports/
Relevant Skill documents under .agents/skills/

Existing documentation is the source of truth.

If documentation conflicts with the user request, Codex must report the conflict before making changes.

6. Modular Architecture Rule

Future implementation must keep these layers separated:

Screen / Capture layer
Dataset / Labeling layer
Vision / YOLO layer
Coordinate mapping layer
Control / Mouse layer
Safety gate layer
Logging / Run records layer
Validation / QA layer
Configuration layer

Codex must not merge all logic into one large uncontrolled script.

Safety and logging must remain explicit even in prototypes.

7. Coordinate Rule

Future coordinate-related work must clearly distinguish:

Screenshot pixel coordinates
Display coordinates
AIMLAB window coordinates
DPI-scaled coordinates
Mouse control coordinates

Codex must never assume these coordinate systems are identical without validation.

Coordinate mapping must be dry-run validated before any real mouse movement is allowed.

8. YOLO and Dataset Rule

YOLO-related work belongs only to later Phases.

Dataset work must keep these separate:

Raw screenshots
Labeled images
YOLO label files
Train / validation split
Dataset config
Model outputs
Evaluation reports

Codex must not train or run YOLO during Phase 0.

9. Logging and Validation Rule

Every meaningful future behavior must be logged and validated.

For future control decisions, logs should eventually include:

Timestamp
Screenshot size
Detection box
Detection confidence
Detected center coordinate
Mapped screen coordinate
AIMLAB foreground status
Dry-run status
Movement permission
Click permission
Final action taken or blocked
Reason if blocked

For Phase 0, validation means checking that required folders and documentation files exist and contain the expected planning content.

10. Phase Report Rule

Every Phase must end with a report under:

docs/phase-reports/

The report must include:

Phase name
Phase goal
Work completed
Files created or modified
Validation performed
What was intentionally not done
Safety notes
Problems encountered
How problems were solved
Remaining risks
Next Phase entry conditions
Suggested next Codex prompt

No Phase is complete without a Phase report.

11. Completion Response Rule

After completing any task, Codex must summarize:

What was done
Which files changed
How it was verified
What was intentionally not done
Remaining issues
Recommended next step

Codex must not claim untested behavior works.

12. Current Instruction

Current active phase is:

Phase 0: Project initialization and Codex collaboration system setup

Codex must not proceed to Phase 1 until the user explicitly asks to start Phase 1.
