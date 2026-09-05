"""
Temporal smoothing for pose landmarks to reduce jitter.
Includes Exponential Moving Average (EMA) and Adaptive One-Euro Filtering.
"""
import copy
import math
from typing import Any, Optional, List
from core.logger import setup_logger

logger = setup_logger(__name__)

class OneEuroFilter1D:
    """
    1D One-Euro Filter implementation for adaptive noise reduction.
    Low cutoff at low velocity (eliminates jitter), high cutoff at high velocity (low latency).
    """
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev: Optional[float] = None
        self.dx_prev: float = 0.0

    def _alpha(self, cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x: float, dt: float = 1.0 / 30.0) -> float:
        if self.x_prev is None:
            self.x_prev = x
            self.dx_prev = 0.0
            return x

        dx = (x - self.x_prev) / dt if dt > 0 else 0.0
        a_d = self._alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, dt)
        x_hat = a * x + (1.0 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        return x_hat


class LandmarkSmoother:
    """
    Applies Exponential Moving Average (EMA) or One-Euro smoothing to landmark coordinates.
    """
    
    def __init__(self, alpha: float = 0.5, method: str = "ema", min_cutoff: float = 1.0, beta: float = 0.007):
        """
        Args:
            alpha: Smoothing factor between 0 and 1 for EMA method.
            method: 'ema' or 'one_euro'.
            min_cutoff: Minimum cutoff frequency for One-Euro filter.
            beta: Speed coefficient for One-Euro filter.
        """
        self.alpha = alpha
        self.method = method
        self.previous_landmarks = None
        self.one_euro_filters: Optional[List[dict]] = None
        self.min_cutoff = min_cutoff
        self.beta = beta
        
    def smooth(self, current_landmarks: Any, dt: float = 1.0 / 30.0) -> Any:
        """
        Applies smoothing to current landmarks.
        """
        if not current_landmarks:
            self.previous_landmarks = None
            self.one_euro_filters = None
            return current_landmarks
            
        if self.method == "one_euro":
            return self._smooth_one_euro(current_landmarks, dt)
        else:
            return self._smooth_ema(current_landmarks)

    def _smooth_ema(self, current_landmarks: Any) -> Any:
        if self.previous_landmarks is None:
            self.previous_landmarks = copy.deepcopy(current_landmarks)
            return current_landmarks
            
        smoothed_landmarks = copy.deepcopy(current_landmarks)
        
        try:
            for i in range(len(smoothed_landmarks)):
                prev = self.previous_landmarks[i]
                curr = smoothed_landmarks[i]
                
                curr.x = (self.alpha * curr.x) + ((1 - self.alpha) * prev.x)
                curr.y = (self.alpha * curr.y) + ((1 - self.alpha) * prev.y)
                curr.z = (self.alpha * curr.z) + ((1 - self.alpha) * prev.z)
                
            self.previous_landmarks = copy.deepcopy(smoothed_landmarks)
        except Exception as e:
            logger.warning(f"Error during EMA landmark smoothing: {e}")
            return current_landmarks
            
        return smoothed_landmarks

    def _smooth_one_euro(self, current_landmarks: Any, dt: float) -> Any:
        n = len(current_landmarks)
        if self.one_euro_filters is None or len(self.one_euro_filters) != n:
            self.one_euro_filters = [
                {
                    "x": OneEuroFilter1D(self.min_cutoff, self.beta),
                    "y": OneEuroFilter1D(self.min_cutoff, self.beta),
                    "z": OneEuroFilter1D(self.min_cutoff, self.beta)
                }
                for _ in range(n)
            ]

        smoothed_landmarks = copy.deepcopy(current_landmarks)
        try:
            for i in range(n):
                curr = smoothed_landmarks[i]
                f = self.one_euro_filters[i]
                curr.x = f["x"].filter(curr.x, dt)
                curr.y = f["y"].filter(curr.y, dt)
                curr.z = f["z"].filter(curr.z, dt)
        except Exception as e:
            logger.warning(f"Error during One-Euro landmark smoothing: {e}")
            return current_landmarks

        return smoothed_landmarks
