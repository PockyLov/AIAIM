# Skill: aiaim-phase-planner

## Purpose

Use this skill whenever AIAIM starts a new Phase, modifies Phase scope, or needs task decomposition.

This skill ensures Codex works within the correct Phase boundary and does not implement future-Phase features prematurely.

---

## When to Trigger

Trigger this skill when the user asks to:

1. Start a new Phase.
2. Continue a Phase.
3. Split a Phase into tasks.
4. Decide what belongs in the current Phase.
5. Generate a Codex execution prompt.
6. Review whether a Phase is complete.

---

## Core Rules

Codex must:

1. Identify the current Phase before doing any work.
2. Read `AGENTS.md`.
3. Read `docs/phase-roadmap.md`.
4. Read the latest relevant report in `docs/phase-reports/`.
5. Define:
   - Goal
   - Allowed work
   - Forbidden work
   - Deliverables
   - Validation method
   - Next Phase entry condition
6. Avoid cross-Phase implementation.

---

## Phase Boundary Rules

### Phase 0

Allowed:

- Create folders.
- Create documentation.
- Create Skills.
- Create Agent Team plan.
- Create MCP plan.
- Create Phase roadmap.
- Create Phase 0 report.

Forbidden:

- Screenshot code.
- AIMLAB detection code.
- YOLO code.
- Dataset collection code.
- Mouse movement code.
- Mouse click code.
- Any real automation logic.

### Later Phases

For later Phases, Codex must follow `docs/phase-roadmap.md`.

If a requested feature belongs to a later Phase, Codex must document it as a future note instead of implementing it immediately.

---

## Required Output For Any Phase Plan

Every Phase plan must include:

1. Phase name.
2. Phase objective.
3. Files likely to be created or modified.
4. Explicit non-goals.
5. Safety notes.
6. Validation checklist.
7. Risks.
8. Suggested next prompt.

---

## Completion Criteria

This skill is applied correctly when:

1. Codex states the current Phase.
2. Codex does not exceed the Phase boundary.
3. The Phase output has clear validation criteria.
4. Future work is documented but not implemented early.
