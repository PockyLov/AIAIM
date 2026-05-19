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

    def update(self, x: float, y: float, timestamp: Optional[float] = None) -> None:
        if timestamp is None:
            timestamp = time.perf_counter()
        self.history.append((x, y, timestamp))

    def predict(self, current_time: Optional[float] = None) -> Tuple[float, float]:
        if not self.history:
            return 0.0, 0.0
        if len(self.history) < 2:
            return self.history[-1][0], self.history[-1][1]

        if current_time is None:
            current_time = time.perf_counter()

        # Simple linear velocity using first and last in history
        p1 = self.history[0]
        p2 = self.history[-1]
        
        dt = p2[2] - p1[2]
        if dt <= 0.001:
            return p2[0], p2[1]

        vx = (p2[0] - p1[0]) / dt
        vy = (p2[1] - p1[1]) / dt

        import math
        VELOCITY_DEADZONE = 50.0
        if math.hypot(vx, vy) < VELOCITY_DEADZONE:
            vx = 0.0
            vy = 0.0

        self.ema_vx = self.EMA_ALPHA * vx + (1.0 - self.EMA_ALPHA) * self.ema_vx
        self.ema_vy = self.EMA_ALPHA * vy + (1.0 - self.EMA_ALPHA) * self.ema_vy

        future_time = current_time + self.latency_compensation_sec
        delta_t = future_time - p2[2]

        predicted_x = p2[0] + self.ema_vx * delta_t
        predicted_y = p2[1] + self.ema_vy * delta_t

        return predicted_x, predicted_y

    def reset(self) -> None:
        self.history.clear()
        self.ema_vx = 0.0
        self.ema_vy = 0.0
