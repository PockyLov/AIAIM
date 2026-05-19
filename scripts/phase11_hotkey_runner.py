from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SRC_DIR = PROJECT_ROOT / "src"
for candidate in (SCRIPTS_DIR, SRC_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import live_one_shot_fov_aim as phase81

PHASE = "11"
MODE = "hotkey_runner"
DEFAULT_CONFIG = Path("configs/phase11_hotkey_runner.json")
DEFAULT_OUTPUT_DIR = Path("runs/detect/phase11_hotkey_runner")
DEFAULT_MODEL = Path("runs/detect/phase3_yolo11n_baseline/weights/best.pt")
DEFAULT_PHASE10_OUTPUT_DIR = Path("runs/detect/phase11_hotkey_runner/phase10_child_runs")
EVENTS_FILE = "runner_events.jsonl"
SUMMARY_FILE = "runner_summary.json"
COMMAND_PREVIEW_FILE = "command_preview.txt"
STOP_FILE = "stop_requested.json"
STATE_IDLE = "IDLE"
STATE_ARMED = "ARMED"
STATE_RUNNING = "RUNNING"
STATE_STOPPING = "STOPPING"
STATE_DONE = "DONE"

DEFAULT_SAFETY_CAPS = {
    "max_iterations": 600,
    "max_duration_sec": 120,
    "max_loop_iterations": 2000,
    "max_retries_per_target": 2,
    "max_retries": 100,
    "max_no_detection_timeouts": 200,
    "max_consecutive_no_detection_timeouts": 30,
}

DEFAULT_PHASE10_ARGS = {
    "conf": 0.10,
    "max_det": 20,
    "max_iterations": 600,
    "max_duration_sec": 120,
    "max_loop_iterations": 2000,
    "post_click_wait_sec": 0.03,
    "after_validation_mode": "hybrid",
    "after_fast_mode": "roi_only",
    "click_guard_mode": "strict",
    "strict_center_roi_click_threshold_px": 6,
    "retry_policy": "bounded",
    "max_retries_per_target": 2,
    "max_retries": 50,
    "max_no_detection_timeouts": 200,
    "max_consecutive_no_detection_timeouts": 30,
    "capture_backend": "mss",
    "evidence_mode": "minimal",
    "execute_move": True,
    "allow_click": True,
    "confirm_local_aimlab_only": True,
    "latency_compensation_sec": 0.075,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def default_run_id() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def append_event(path: Path, event_type: str, **payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": now_iso(), "event_type": event_type, **payload}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 11 console hotkey runner for finite Phase 10 runs. Visible console only; no GUI, no tray, no background service.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id")
    parser.add_argument("--python-exe", default=sys.executable)
    parser.add_argument("--arm-timeout-sec", type=float, default=None)
    parser.add_argument("--poll-interval-sec", type=float, default=0.10)
    parser.add_argument("--child-exit-timeout-sec", type=float, default=5.0)
    parser.add_argument("--title-keyword", action="append", dest="title_keywords")
    return parser.parse_args()


def default_config() -> dict[str, Any]:
    return {
        "phase": "phase11_hotkey_runner",
        "arm_timeout_sec": 5,
        "hotkeys": {"arm": "ctrl+alt+f8", "start": "ctrl+alt+f9", "stop": "ctrl+alt+f10"},
        "title_keywords": ["aimlab", "aim lab"],
        "safety_caps": dict(DEFAULT_SAFETY_CAPS),
        "phase10": {
            "script": "scripts/live_finite_repeat_aim_click.py",
            "model": str(DEFAULT_MODEL),
            "output_dir": str(DEFAULT_PHASE10_OUTPUT_DIR),
            **DEFAULT_PHASE10_ARGS,
        },
    }


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return default_config()
    with path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    cfg = default_config()
    cfg.update({k: v for k, v in loaded.items() if k != "phase10"})
    phase10 = dict(cfg["phase10"])
    phase10.update(loaded.get("phase10", {}))
    cfg["phase10"] = phase10
    return cfg


def hotkey_display(config: dict[str, Any]) -> dict[str, str]:
    hotkeys = config.get("hotkeys", {})
    return {
        "arm": str(hotkeys.get("arm", "ctrl+alt+f8")),
        "start": str(hotkeys.get("start", "ctrl+alt+f9")),
        "stop": str(hotkeys.get("stop", "ctrl+alt+f10")),
    }


def pynput_hotkey_spec(display: str) -> str:
    return "+".join(f"<{part}>" if part in {"ctrl", "alt", "shift", "cmd"} or part.startswith("f") else part for part in display.lower().split("+"))


def validate_safety_caps(phase10: dict[str, Any], caps: dict[str, Any]) -> tuple[bool, str | None]:
    for key, cap in caps.items():
        if key not in phase10:
            return False, f"missing_required_phase10_arg:{key}"
        try:
            value = float(phase10[key])
            cap_value = float(cap)
        except (TypeError, ValueError):
            return False, f"invalid_safety_cap_value:{key}"
        if value > cap_value:
            return False, f"safety_cap_exceeded:{key}"
    required_flags = ("execute_move", "allow_click", "confirm_local_aimlab_only")
    for flag in required_flags:
        if not bool(phase10.get(flag)):
            return False, f"missing_required_action_flag:{flag}"
    return True, None


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def add_cli_arg(command: list[str], name: str, value: Any) -> None:
    flag = "--" + name.replace("_", "-")
    if isinstance(value, bool):
        if value:
            command.append(flag)
        return
    if value is None:
        return
    command.extend([flag, str(value)])


def build_phase10_command(config: dict[str, Any], *, runner_run_dir: Path, python_exe: str) -> tuple[list[str], Path, Path]:
    phase10 = dict(config.get("phase10", {}))
    script = resolve_project_path(phase10.pop("script", "scripts/live_finite_repeat_aim_click.py"))
    child_output_base = resolve_project_path(phase10.pop("output_dir", str(DEFAULT_PHASE10_OUTPUT_DIR)))
    child_run_id = str(phase10.pop("run_id", f"phase10_{runner_run_dir.name}"))
    child_run_dir = child_output_base / child_run_id
    stop_file = runner_run_dir / STOP_FILE
    command = [python_exe, str(script)]
    model = resolve_project_path(phase10.pop("model", str(DEFAULT_MODEL)))
    command.extend(["--model", str(model)])
    command.extend(["--output-dir", str(child_output_base)])
    command.extend(["--run-id", child_run_id])
    command.extend(["--stop-file", str(stop_file)])
    skip = {"save_evidence_on_fallback_click"}
    for key, value in phase10.items():
        if key in skip:
            continue
        add_cli_arg(command, key, value)
    return command, stop_file, child_run_dir


def command_preview(command: list[str]) -> str:
    return "\n".join(command) + "\n"


def aimlab_foreground_passed(title_keywords: tuple[str, ...]) -> tuple[bool, str | None]:
    gate = phase81.get_gate_state(title_keywords)
    if gate.get("blocked"):
        return False, str(gate.get("blocked_reason") or "aimlab_foreground_blocked")
    return True, None


@dataclass
class Phase11Runner:
    config: dict[str, Any]
    run_dir: Path
    python_exe: str = sys.executable
    title_keywords: tuple[str, ...] = ("aimlab", "aim lab")
    popen_factory: Callable[..., Any] = subprocess.Popen
    foreground_check: Callable[[tuple[str, ...]], tuple[bool, str | None]] = aimlab_foreground_passed
    state: str = STATE_IDLE
    arm_deadline: float | None = None
    child: Any | None = None
    child_command: list[str] = field(default_factory=list)
    stop_file: Path | None = None
    child_output_dir: Path | None = None
    started_at: str = field(default_factory=now_iso)
    blocked: bool = False
    blocked_reason: str | None = None
    stop_requested_by_user: bool = False
    runner_stop_reason: str | None = None
    phase10_child_return_code: int | None = None

    @property
    def events_path(self) -> Path:
        return self.run_dir / EVENTS_FILE

    def event(self, event_type: str, **payload: Any) -> None:
        append_event(self.events_path, event_type, state=self.state, **payload)

    def arm(self, now: float | None = None) -> bool:
        if self.state == STATE_RUNNING:
            self.event("arm_ignored_running")
            return False
        now = time.monotonic() if now is None else now
        timeout = float(self.config.get("arm_timeout_sec", 5))
        self.arm_deadline = now + timeout
        self.state = STATE_ARMED
        self.event("armed", arm_timeout_sec=timeout)
        print("State: ARMED")
        return True

    def expire_arm_if_needed(self, now: float | None = None) -> bool:
        if self.state != STATE_ARMED or self.arm_deadline is None:
            return False
        now = time.monotonic() if now is None else now
        if now <= self.arm_deadline:
            return False
        self.state = STATE_IDLE
        self.arm_deadline = None
        self.event("arm_expired")
        print("State: ARM_EXPIRED")
        return True

    def start(self, now: float | None = None) -> bool:
        self.event("start_requested")
        now = time.monotonic() if now is None else now
        if self.state == STATE_RUNNING and self.child is not None and self.child.poll() is None:
            self.event("duplicate_start_ignored")
            print("BLOCKED: child already running")
            return False
        if self.state != STATE_ARMED or self.arm_deadline is None or now > self.arm_deadline:
            self.state = STATE_IDLE
            self.event("start_blocked", blocked_reason="not_armed_or_arm_expired")
            print("BLOCKED: not_armed_or_arm_expired")
            return False
        phase10 = self.config.get("phase10", {})
        ok, reason = validate_safety_caps(phase10, self.config.get("safety_caps", DEFAULT_SAFETY_CAPS))
        if not ok:
            self.blocked = True
            self.blocked_reason = reason
            self.state = STATE_IDLE
            self.event("start_blocked", blocked_reason=reason)
            print(f"BLOCKED: {reason}")
            return False
        fg_ok, fg_reason = self.foreground_check(self.title_keywords)
        if not fg_ok:
            self.blocked = True
            self.blocked_reason = fg_reason
            self.state = STATE_IDLE
            self.event("start_blocked", blocked_reason=fg_reason)
            print(f"BLOCKED: {fg_reason}")
            return False
        self.event("aimlab_foreground_passed")
        self.child_command, self.stop_file, self.child_output_dir = build_phase10_command(self.config, runner_run_dir=self.run_dir, python_exe=self.python_exe)
        (self.run_dir / COMMAND_PREVIEW_FILE).write_text(command_preview(self.child_command), encoding="utf-8")
        self.child = self.popen_factory(self.child_command, cwd=str(PROJECT_ROOT))
        self.state = STATE_RUNNING
        self.runner_stop_reason = None
        self.event("phase10_child_started", pid=getattr(self.child, "pid", None), command_preview=str(self.run_dir / COMMAND_PREVIEW_FILE))
        print("State: RUNNING")
        return True

    def stop(self) -> bool:
        if self.child is None or self.child.poll() is not None:
            self.event("stop_ignored_no_child")
            print("STOP ignored: no running child")
            return False
        if self.stop_file is None:
            self.stop_file = self.run_dir / STOP_FILE
        write_json(self.stop_file, {"requested_at": now_iso(), "reason": "user_hotkey_stop"})
        self.stop_requested_by_user = True
        self.state = STATE_STOPPING
        self.runner_stop_reason = "user_stop_requested"
        self.event("stop_requested", stop_file=str(self.stop_file))
        print("State: STOPPING")
        return True

    def poll_child(self) -> bool:
        if self.child is None:
            return False
        code = self.child.poll()
        if code is None:
            return False
        self.phase10_child_return_code = int(code)
        self.state = STATE_DONE
        self.runner_stop_reason = "phase10_completed" if code == 0 else "phase10_child_failed"
        self.event("phase10_child_exited", return_code=code)
        print("State: DONE")
        return True

    def request_exit(self, timeout_sec: float = 5.0) -> None:
        if self.child is not None and self.child.poll() is None:
            self.stop()
            deadline = time.monotonic() + max(0.0, timeout_sec)
            while time.monotonic() < deadline:
                if self.poll_child():
                    return
                time.sleep(0.05)
            self.event("phase10_child_soft_stop_timeout")
        self.runner_stop_reason = self.runner_stop_reason or "runner_exit"

    def summary(self) -> dict[str, Any]:
        hotkeys = hotkey_display(self.config)
        return {
            "phase": PHASE,
            "mode": MODE,
            "hotkeys": hotkeys,
            "arm_required": True,
            "arm_timeout_sec": float(self.config.get("arm_timeout_sec", 5)),
            "blocked": bool(self.blocked),
            "blocked_reason": self.blocked_reason,
            "phase10_child_started": self.child is not None,
            "phase10_child_return_code": self.phase10_child_return_code,
            "phase10_run_dir": str(self.child_output_dir) if self.child_output_dir else None,
            "stop_requested_by_user": bool(self.stop_requested_by_user),
            "runner_stop_reason": self.runner_stop_reason or self.state.lower(),
            "safety_caps_enforced": self.config.get("safety_caps", DEFAULT_SAFETY_CAPS),
            "runner_run_dir": str(self.run_dir),
            "started_at": self.started_at,
            "ended_at": now_iso(),
        }

    def write_summary(self) -> None:
        write_json(self.run_dir / SUMMARY_FILE, self.summary())


def print_banner(config: dict[str, Any]) -> None:
    hotkeys = hotkey_display(config)
    print("Phase 11 Hotkey Runner")
    print(f"Project: {PROJECT_ROOT}")
    print("State: IDLE")
    print("\nHotkeys:")
    print(f"{hotkeys['arm']}  = Arm")
    print(f"{hotkeys['start']}  = Start finite Phase 10 run")
    print(f"{hotkeys['stop']} = Request stop")
    print("Ctrl+C       = Exit runner")
    print("\nSafety:")
    print("- finite run only")
    print("- AIMLAB foreground required")
    print("- no background service")
    print("- no infinite loop")
    print("- Phase 10 gates preserved")


def register_hotkeys(runner: Phase11Runner):
    try:
        from pynput import keyboard
    except Exception as exc:
        raise RuntimeError(f"pynput is required for Phase 11 hotkeys: {type(exc).__name__}: {exc}") from exc
    hotkeys = hotkey_display(runner.config)
    mappings = {
        pynput_hotkey_spec(hotkeys["arm"]): runner.arm,
        pynput_hotkey_spec(hotkeys["start"]): runner.start,
        pynput_hotkey_spec(hotkeys["stop"]): runner.stop,
    }
    listener = keyboard.GlobalHotKeys(mappings)
    listener.start()
    runner.event("hotkeys_registered", hotkeys=hotkeys)
    return listener


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    if args.arm_timeout_sec is not None:
        config["arm_timeout_sec"] = args.arm_timeout_sec
    run_id = args.run_id or default_run_id()
    run_dir = (args.output_dir / run_id).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    title_keywords = tuple(args.title_keywords or config.get("title_keywords") or ("aimlab", "aim lab"))
    runner = Phase11Runner(config=config, run_dir=run_dir, python_exe=args.python_exe, title_keywords=title_keywords)
    runner.event("runner_started", config=str(args.config))
    runner.event("config_loaded", config_exists=args.config.exists())
    write_json(run_dir / "runner_config.json", config)
    print_banner(config)
    listener = None
    try:
        listener = register_hotkeys(runner)
        while True:
            runner.expire_arm_if_needed()
            runner.poll_child()
            if runner.state == STATE_DONE:
                runner.state = STATE_IDLE
            time.sleep(max(0.01, float(args.poll_interval_sec)))
    except KeyboardInterrupt:
        runner.event("runner_keyboard_interrupt")
        runner.request_exit(timeout_sec=float(args.child_exit_timeout_sec))
    except Exception as exc:
        runner.blocked = True
        runner.blocked_reason = f"runner_error:{type(exc).__name__}:{exc}"
        runner.runner_stop_reason = "runner_error"
        runner.event("runner_error", error=runner.blocked_reason)
        print(f"BLOCKED: {runner.blocked_reason}")
        return_code = 1
    else:
        return_code = 0
    finally:
        if listener is not None:
            try:
                listener.stop()
            except Exception:
                pass
        runner.write_summary()
        runner.event("runner_finished", runner_stop_reason=runner.runner_stop_reason)
    return locals().get("return_code", 0)


if __name__ == "__main__":
    raise SystemExit(main())
