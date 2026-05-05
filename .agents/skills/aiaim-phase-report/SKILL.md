# Skill: aiaim-phase-report

## Purpose

Use this skill at the end of every AIAIM Phase.

Every Phase must produce a report under:

```text
docs/phase-reports/

No Phase is considered complete without a Phase report.

When to Trigger

Trigger this skill when:

A Phase is completed.
A major task is completed.
The user asks for a summary.
Codex needs to hand off to a new chat.
Codex needs to prepare the next Phase prompt.
Required Report Location

Reports must be saved in:

docs/phase-reports/

Recommended naming:

phase-0-report.md
phase-1-report.md
phase-2-report.md

If a Phase has multiple attempts, use:

phase-1-report-v2.md

or include run/date metadata inside the report.

Required Report Template

Each Phase report must include:

# Phase X Report - <Phase Name>

## 1. Phase Goal

## 2. Work Completed

## 3. Files Created or Modified

## 4. Validation Performed

## 5. What Was Intentionally Not Done

## 6. Safety Notes

## 7. Problems Encountered

## 8. How Problems Were Solved

## 9. Remaining Risks

## 10. Next Phase Entry Conditions

## 11. Suggested Next Codex Prompt
Report Quality Rules

The report must be specific.

Bad:

Created docs.

Good:

Created docs/phase-roadmap.md to define Phase 0-9 boundaries and prevent Codex from implementing YOLO or control code before the correct Phase.
Validation Section Rule

The validation section must state:

What was checked.
How it was checked.
What was not checked.
Whether the Phase is ready for the next Phase.

For Phase 0, validation means checking that required directories and planning documents exist.

Forbidden Actions

Codex must not:

Finish a Phase without a report.
Claim untested behavior works.
Omit known issues.
Hide skipped work.
Write vague reports.
Use the report to justify cross-Phase implementation.
Completion Criteria

This skill is applied correctly when the Phase can be continued in a new chat using the report alone.
