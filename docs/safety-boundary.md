# Safety Boundary

AIAIM defaults to dry-run. Future real mouse movement and click behavior must be explicitly enabled, gated, logged, and reversible.

## Allowed Direction

The project may research local offline AIMLAB detection and control under staged, documented, user-visible conditions.

## Disallowed Direction

AIAIM must not be used for:

- Anti-cheat bypass
- Hidden automation
- Leaderboard farming
- Multiplayer cheating
- Bypassing safety checks
- Removing foreground validation
- Default real clicking

## Future Required Gates

Before real mouse movement or clicking can exist, the project must include:

- Explicit config switch
- Dry-run default
- AIMLAB foreground window verification
- Emergency stop mechanism
- Structured logging
- Rate limiting
- Phase report
- Runbook update
- Manual validation checklist

## Phase 0 Boundary

Phase 0 does not implement screenshot capture, foreground detection, YOLO, data collection, coordinate mapping, mouse movement, clicking, or real automation.

## Phase 2 Boundary

Phase 2 allows:

- Data organization
- Human annotation guidelines
- OpenCV offline pre-labeling assistance
- YOLO label format preparation
- Train / val / test dataset splitting
- `data.yaml` generation
- Dataset validation

Phase 2 forbids:

- YOLO training
- YOLO inference
- Real-time detection
- Mouse movement
- Mouse clicking
- Coordinate mapping
- Auto-aim
- Closed-loop automation
- Anti-cheat bypass
- AIMLAB background window screenshot expansion

OpenCV pre-labeling only processes static images already saved under the dataset folders. It does not connect to AIMLAB real-time video, does not connect to the Phase 1 collector, and does not drive any input device.
