# AIAIM MCP Plan

## 1. Purpose

This document defines which MCP tools may be useful for AIAIM and when they should be used.

Current Phase:

```text
Phase 0 only

Phase 0 only plans MCP usage. It must not install, configure, or require any MCP.

2. MCP Strategy

AIAIM should keep MCP usage minimal.

MCP tools should only be introduced when they clearly improve:

Library documentation lookup
UI validation
Project maintenance
Future dashboard testing

MCP tools must not replace AIAIM's own safety gates.

MCP tools must not be used to bypass foreground-window checks, dry-run rules, emergency stop, or logging requirements.

3. Recommended MCPs
MCP	Current Status	Future Use	Recommended Scope
Context7 MCP	Planned, not required in Phase 0	Lookup latest library docs	Global config
Playwright MCP	Not needed now	Future Web dashboard / local UI validation	Global or project config
GitHub MCP	Optional later	Repo management, issues, PRs	Global config
4. Context7 MCP
Status

Planned for later phases. Not required in Phase 0.

Purpose in AIAIM

Context7 MCP may be used to check current documentation for:

Ultralytics YOLO
OpenCV
PyTorch
ONNX Runtime
MSS / DXCam / screenshot libraries
PyAutoGUI / pynput
Python logging
Python testing tools
Recommended Configuration

Use global Codex configuration.

Reason:

It is useful across many projects.
It is not specific to AIAIM.
It avoids repeated setup in every project.
Phase Usage
Phase	Usage
Phase 0	Planning only
Phase 1	Check screenshot library docs if needed
Phase 2	Check dataset / annotation tooling docs
Phase 3	Check YOLO training docs
Phase 4	Check inference API docs
Phase 5-7	Check coordinate, input-control, safety-related library docs only
5. Playwright MCP
Status

Not needed in Phase 0.

Purpose in AIAIM

Playwright MCP is only useful if AIAIM later adds:

Local Web dashboard
Browser-based run report viewer
Dataset review page
Model result visualization page
Config management UI
Recommended Configuration

Global config is acceptable if already used in other projects.

Project config is also acceptable if it becomes AIAIM-specific later.

Not For

Playwright MCP should not be used for:

AIMLAB desktop control
Mouse-click automation
Screenshot collector core logic
YOLO inference
Safety gate bypassing
6. GitHub MCP
Status

Optional later.

Purpose in AIAIM

GitHub MCP may be useful if the project is pushed to GitHub and needs:

Issue tracking
Pull request review
Version history
Release notes
Project documentation review
Recommended Configuration

Global config is preferred.

Reason:

GitHub usage is not unique to AIAIM.
Other projects may reuse it.
7. MCPs Not Needed Now

The following MCPs are not needed in Phase 0:

MCP Type	Reason
Figma MCP	AIAIM is not UI-first right now
Remotion / video MCP	No video generation needed
Database MCP	Local files are enough for early phases
Browser automation MCP beyond Playwright	Not useful until Web UI exists
Desktop control / Computer Use MCP	Should not replace project safety gates
Complex agent orchestration MCP	AGENTS.md + Skills are enough for now
8. Safety Notes

MCP tools are helper tools only.

They must not become hidden execution paths.

Any future feature involving real mouse movement or real clicking must still pass:

Explicit config switch
Dry-run fallback
Safety gate
Foreground AIMLAB verification
Emergency stop
Structured logs
Phase report
9. Phase 0 Decision

For Phase 0:

Do not install MCPs.
Do not write MCP setup commands.
Do not require MCPs for project initialization.
Only document future MCP usage.
Continue using Markdown documentation as the source of truth.
10. Next Review Point

Review MCP needs again at:

Phase 1: AIMLAB foreground stable screenshot / Collector

At that point, Context7 MCP may be useful for checking screenshot library documentation.

Playwright MCP should still remain unused unless a Web UI is introduced.