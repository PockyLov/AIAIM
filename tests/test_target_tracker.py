import time
import math
from aiaim_control.target_tracker import TargetTracker

def test_target_tracker_deadzone() -> None:
    # Set latency compensation to 0 for easier math
    tracker = TargetTracker(latency_compensation_sec=0.0, max_history=5)
    
    # 1. Below 0.2 deadzone (e.g. speed = 0.1 deg/sec)
    t0 = time.perf_counter()
    tracker.update(10.0, 10.0, timestamp=t0)
    tracker.update(10.01, 10.0, timestamp=t0 + 0.1)  # speed is (10.01-10.0)/0.1 = 0.1 deg/sec
    
    px, py = tracker.predict(current_time=t0 + 0.1)
    # Predicted velocity should be 0 because of deadzone (speed 0.1 < 0.2)
    assert tracker.ema_vx == 0.0
    assert tracker.ema_vy == 0.0
    assert px == 10.01
    assert py == 10.0

    # 2. Above 0.2 deadzone (e.g. speed = 0.5 deg/sec)
    tracker.reset()
    tracker.update(10.0, 10.0, timestamp=t0)
    tracker.update(10.05, 10.0, timestamp=t0 + 0.1)  # speed is (10.05-10.0)/0.1 = 0.5 deg/sec
    
    px, py = tracker.predict(current_time=t0 + 0.2)
    # Predicted velocity should be active (non-zero) because speed is above deadzone
    assert tracker.ema_vx > 0.0
    assert px > 10.05

def test_target_tracker_smart_reset() -> None:
    tracker = TargetTracker(latency_compensation_sec=0.0, max_history=5)
    t0 = time.perf_counter()
    
    tracker.update(10.0, 10.0, timestamp=t0)
    tracker.update(10.5, 10.0, timestamp=t0 + 0.1)
    
    # Check velocity is accumulated
    px, py = tracker.predict(current_time=t0 + 0.1)
    assert tracker.ema_vx > 0.0
    
    # Now simulate a target switch: massive jump of 10 degrees (threshold is 5.0)
    tracker.update(30.0, 10.0, timestamp=t0 + 0.2)
    
    # Because jump is > 5.0 degrees, the tracker should have auto-reset!
    assert len(tracker.history) == 1
    assert tracker.ema_vx == 0.0
    assert tracker.ema_vy == 0.0
    
    # Predict should return exactly the new target center, no velocity applied
    px2, py2 = tracker.predict(current_time=t0 + 0.2)
    assert px2 == 30.0
    assert py2 == 10.0

def test_target_tracker_shift_camera() -> None:
    tracker = TargetTracker(latency_compensation_sec=0.0, max_history=5)
    t0 = time.perf_counter()
    tracker.update(10.0, 10.0, timestamp=t0)
    tracker.update(10.5, 10.0, timestamp=t0 + 0.1)
    
    # Shift camera by 1 degree in Yaw, 0.5 in Pitch
    tracker.shift_camera(1.0, 0.5)
    
    # Check that coords are shifted
    assert len(tracker.history) == 2
    x0, y0, _ = tracker.history[0]
    x1, y1, _ = tracker.history[1]
    assert x0 == 9.0
    assert y0 == 9.5
    assert x1 == 9.5
    assert y1 == 9.5
