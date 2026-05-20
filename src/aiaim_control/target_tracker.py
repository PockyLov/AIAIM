import time
from collections import deque
from typing import Tuple, Optional

class TargetTracker:
    EMA_ALPHA = 0.8

    def __init__(self, latency_compensation_sec: float = 0.05, max_history: int = 5):
        self.latency_compensation_sec = latency_compensation_sec
        self.history = deque(maxlen=max_history)
        self.ema_vx = 0.0
        self.ema_vy = 0.0

    def update(self, yaw_deg: float, pitch_deg: float, timestamp: Optional[float] = None) -> Tuple[float, float]:
        if timestamp is None:
            timestamp = time.perf_counter()
        
        if self.history:
            import math
            last_yaw, last_pitch, _ = self.history[-1]
            dyaw = yaw_deg - last_yaw
            dpitch = pitch_deg - last_pitch
            if math.hypot(dyaw, dpitch) > 5.0:
                self.reset()

        self.history.append((yaw_deg, pitch_deg, timestamp))

        # Calculate angular velocity
        if len(self.history) < 2:
            return self.ema_vx, self.ema_vy

        p1 = self.history[0]
        p2 = self.history[-1]
        
        dt = p2[2] - p1[2]
        if dt <= 0.001:
            return self.ema_vx, self.ema_vy

        vx = (p2[0] - p1[0]) / dt
        vy = (p2[1] - p1[1]) / dt

        import math
        VELOCITY_DEADZONE = 0.2
        if math.hypot(vx, vy) < VELOCITY_DEADZONE:
            vx = 0.0
            vy = 0.0

        self.ema_vx = self.EMA_ALPHA * vx + (1.0 - self.EMA_ALPHA) * self.ema_vx
        self.ema_vy = self.EMA_ALPHA * vy + (1.0 - self.EMA_ALPHA) * self.ema_vy

        return self.ema_vx, self.ema_vy

    def predict(self, current_time: Optional[float] = None) -> Tuple[float, float]:
        if not self.history:
            return 0.0, 0.0
        if len(self.history) < 2:
            return self.history[-1][0], self.history[-1][1]

        if current_time is None:
            current_time = time.perf_counter()

        p2 = self.history[-1]
        future_time = current_time + self.latency_compensation_sec
        delta_t = future_time - p2[2]

        predicted_yaw = p2[0] + self.ema_vx * delta_t
        predicted_pitch = p2[1] + self.ema_vy * delta_t

        return predicted_yaw, predicted_pitch

    def reset(self) -> None:
        self.history.clear()
        self.ema_vx = 0.0
        self.ema_vy = 0.0

    def shift_camera(self, moved_yaw_deg: float, moved_pitch_deg: float) -> None:
        self.history = deque(
            [(hx - moved_yaw_deg, hy - moved_pitch_deg, t) for hx, hy, t in self.history],
            maxlen=self.history.maxlen
        )
