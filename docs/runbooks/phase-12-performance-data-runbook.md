# Phase 12 Runbook: Ultra-low Latency and Failure Evidence Flywheel

## Overview
Phase 12 focuses on significant performance enhancements to break the 200 actions per 60 seconds barrier, and introduces a robust background data saving mechanism (the Failure Evidence Flywheel).

## Performance Optimizations
1. **Low-Level IO Replacement**: `pyautogui` and `pynput` usage have been fully eliminated. All mouse movement and click commands are now dispatched directly through `ctypes.windll.user32.mouse_event`, bypassing struct allocations from `SendInput` where possible.
2. **Zero-Delay Overheads**: All default sleep or pause delays inside the click gate (`time.sleep`) have been removed from the core API calls (`send_left_click`, `send_relative_mouse_move`), relying strictly on configurable system parameters instead.

## Failure Evidence Flywheel
To ensure the main inference loop runs unblocked, we have implemented an asynchronous data-saving system.

- **Trigger Conditions**: Evidence is collected when the main loop encounters:
  - `after_distance > threshold`
  - `after_detection_missing`
  - `click_gate_failed`
  - `no_detection_timeout`
  - `fallback_click_blocked`
- **Background Worker**: A dedicated threading Worker (`evidence_worker_loop`) handles all file writing via a `queue.Queue()`.
- **Location**: All failure data is logged under `data/feedback/phase12_failures/`.
- **Format**: Data is saved as a pair:
  - `[timestamp]_[failure_type].jpg` (The visual frame capture)
  - `[timestamp]_[failure_type].json` (Metadata, distance info, tracking logic)

## Safe Exit Mechanism
The background IO thread is configured as a `daemon` thread but gracefully drains the remaining Queue items on process exit via a `None` sentinel. This guarantees that all detected failure evidences are written fully before shutting down safely, without corrupting the main loop termination.
