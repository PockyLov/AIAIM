from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path("scripts").resolve()))

import phase11_hotkey_runner as phase11
import live_finite_repeat_aim_click as phase10


class FakeChild:
    def __init__(self):
        self.pid = 1234
        self.returncode = None

    def poll(self):
        return self.returncode


class FakePopen:
    calls = []

    def __new__(cls, command, cwd=None):
        cls.calls.append((command, cwd))
        return FakeChild()


def cfg(**phase10_overrides):
    config = phase11.default_config()
    config["phase10"].update(phase10_overrides)
    return config


def test_arm_then_start_within_timeout_allowed(tmp_path):
    FakePopen.calls.clear()
    runner = phase11.Phase11Runner(
        config=cfg(),
        run_dir=tmp_path,
        python_exe="python",
        popen_factory=FakePopen,
        foreground_check=lambda _kw: (True, None),
    )
    assert runner.arm(now=10.0) is True
    assert runner.start(now=12.0) is True
    assert runner.state == phase11.STATE_RUNNING
    assert len(FakePopen.calls) == 1
    assert "--stop-file" in FakePopen.calls[0][0]


def test_start_without_arm_is_rejected(tmp_path):
    runner = phase11.Phase11Runner(config=cfg(), run_dir=tmp_path, foreground_check=lambda _kw: (True, None))
    assert runner.start(now=10.0) is False
    assert runner.state == phase11.STATE_IDLE


def test_arm_expired_start_is_rejected(tmp_path):
    runner = phase11.Phase11Runner(config=cfg(), run_dir=tmp_path, foreground_check=lambda _kw: (True, None))
    runner.arm(now=10.0)
    assert runner.start(now=20.0) is False
    assert runner.state == phase11.STATE_IDLE


def test_running_duplicate_start_does_not_spawn_second_child(tmp_path):
    FakePopen.calls.clear()
    runner = phase11.Phase11Runner(config=cfg(), run_dir=tmp_path, python_exe="python", popen_factory=FakePopen, foreground_check=lambda _kw: (True, None))
    runner.arm(now=1.0)
    assert runner.start(now=2.0) is True
    assert runner.start(now=3.0) is False
    assert len(FakePopen.calls) == 1


def test_stop_creates_stop_file(tmp_path):
    runner = phase11.Phase11Runner(config=cfg(), run_dir=tmp_path, foreground_check=lambda _kw: (True, None))
    runner.child = FakeChild()
    runner.stop_file = tmp_path / phase11.STOP_FILE
    assert runner.stop() is True
    assert runner.stop_file.exists()


def test_stop_without_child_is_ignored(tmp_path):
    runner = phase11.Phase11Runner(config=cfg(), run_dir=tmp_path)
    assert runner.stop() is False


def test_safety_cap_exceeded_blocks_start(tmp_path):
    runner = phase11.Phase11Runner(config=cfg(max_iterations=301), run_dir=tmp_path, foreground_check=lambda _kw: (True, None))
    runner.arm(now=1.0)
    assert runner.start(now=2.0) is False
    assert runner.blocked_reason == "safety_cap_exceeded:max_iterations"


def test_foreground_gate_failure_blocks_start(tmp_path):
    runner = phase11.Phase11Runner(config=cfg(), run_dir=tmp_path, foreground_check=lambda _kw: (False, "aimlab_not_foreground"))
    runner.arm(now=1.0)
    assert runner.start(now=2.0) is False
    assert runner.blocked_reason == "aimlab_not_foreground"


def test_phase10_stop_file_default_false(tmp_path):
    args = SimpleNamespace(stop_file=None)
    assert phase10.stop_file_requested(args) is False


def test_phase10_stop_file_detected(tmp_path):
    stop_file = tmp_path / "stop_requested.json"
    stop_file.write_text("{}", encoding="utf-8")
    args = SimpleNamespace(stop_file=stop_file)
    assert phase10.stop_file_requested(args) is True
