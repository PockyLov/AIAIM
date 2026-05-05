# AIAIM Project Overview

AIAIM is a local offline AIMLAB experiment. The long-term research goal is to build a strictly gated pipeline that can identify randomly appearing yellow balls in AIMLAB full-screen mode, map detected positions to screen coordinates, and eventually close a controlled mouse movement and click loop.

## Product Intent

The project is designed as a phased engineering system, not a one-shot automation script. Each phase must leave clear evidence, verification notes, and safety boundaries before the next phase begins.

## Non-Goals

- No anti-cheat bypass
- No hidden automation
- No leaderboard farming
- No multiplayer cheating
- No default real clicking
- No skipping safety gates

## Architecture Direction

Future implementation must be modular:

- Capture layer: screenshot and foreground validation
- Dataset layer: collection, labeling, review, export
- Vision layer: YOLO training and inference
- Calibration layer: coordinate mapping and dry-run overlays
- Control layer: gated movement and clicking
- Safety layer: configuration, logging, emergency stop, validation gates
- Reporting layer: phase reports and debug runbooks

Phase 0 creates only the planning and collaboration foundation.
