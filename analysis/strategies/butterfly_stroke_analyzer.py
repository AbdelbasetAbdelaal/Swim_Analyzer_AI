"""
Analyzes stroke phases for Butterfly based on motion tracking.
"""
from typing import Any, List
from core.logger import setup_logger
from models.data_models import PhaseTransition
from analysis.strategies.base_strategy import BaseStrokeStateMachine

logger = setup_logger(__name__)

class ButterflyStateMachine(BaseStrokeStateMachine):
    """
    State machine for Butterfly phase detection.
    Butterfly phases: Entry, Catch, Pull, Push, Recovery.
    """
    
    STATES = ["Unknown", "Entry", "Catch", "Pull", "Push", "Recovery"]
    
    def __init__(self, fps: float = 30.0):
        self.fps = fps
        self.current_phase = "Unknown"
        self.phase_confidence = 0.0
        
        # History buffers
        self.history_size = 5
        self.wrist_y_history: List[float] = []
        self.timestamp_history: List[int] = []
        
        self.pending_phase = None
        self.frames_in_pending = 0
        self.temporal_threshold = max(2, int(self.fps * 0.1))
        
        self.transitions: List[PhaseTransition] = []
        self.time_in_phases = {state: 0.0 for state in self.STATES}
        self.completed_cycles = 0
        self.frame_count = 0

    def analyze_frame(self, landmarks: Any, frame_idx: int, timestamp_ms: int) -> tuple[str, float]:
        self.frame_count += 1
        
        if not landmarks or len(landmarks) < 25:
            self._update_stats("Unknown", timestamp_ms)
            return "Unknown", 0.0
            
        try:
            # For butterfly, arms move simultaneously. We can average or pick one.
            left_wrist = landmarks[15]
            right_wrist = landmarks[16]
            shoulder_y = (landmarks[11].y + landmarks[12].y) / 2
            hip_y = (landmarks[23].y + landmarks[24].y) / 2
            
            # Using average wrist Y
            avg_wrist_y = (left_wrist.y + right_wrist.y) / 2
            
            self.wrist_y_history.append(avg_wrist_y)
            self.timestamp_history.append(timestamp_ms)
            
            if len(self.wrist_y_history) > self.history_size:
                self.wrist_y_history.pop(0)
                self.timestamp_history.pop(0)
                
            velocity_y = 0.0
            if len(self.wrist_y_history) > 1:
                dy = self.wrist_y_history[-1] - self.wrist_y_history[0]
                dt = (self.timestamp_history[-1] - self.timestamp_history[0]) / 1000.0
                if dt > 0:
                    velocity_y = dy / dt
            
            target_phase = "Unknown"
            reason = ""
            confidence = 1.0
            
            # Basic Butterfly heuristics (similar to freestyle but symmetric)
            if avg_wrist_y < shoulder_y and velocity_y < -0.05:
                target_phase = "Recovery"
                reason = "Both wrists high and moving upwards over water"
            elif avg_wrist_y < shoulder_y + 0.15:
                target_phase = "Entry" if avg_wrist_y < shoulder_y + 0.05 else "Catch"
                reason = "Wrists entering or catching at shoulder level"
            elif avg_wrist_y < hip_y - 0.1:
                target_phase = "Pull"
                reason = "Wrists pulling down under body"
            else:
                target_phase = "Push"
                reason = "Wrists pushing past hips"
                
            # Temporal Filtering
            if target_phase != self.current_phase:
                if target_phase == self.pending_phase:
                    self.frames_in_pending += 1
                    if self.frames_in_pending >= self.temporal_threshold:
                        transition = PhaseTransition(
                            frame_index=frame_idx,
                            timestamp_ms=timestamp_ms,
                            from_phase=self.current_phase,
                            to_phase=target_phase,
                            reason=reason,
                            confidence=confidence
                        )
                        self.transitions.append(transition)
                        
                        logger.debug_log(f"\nFrame {frame_idx} | {self.current_phase} -> {target_phase} | Conf: {confidence:.2f}")
                        
                        last_phase = getattr(self, "last_known_phase", "Unknown")
                        if last_phase == "Recovery" and target_phase in ["Entry", "Catch", "Pull"]:
                            self.completed_cycles += 1
                            
                        self.current_phase = target_phase
                        if target_phase != "Unknown":
                            self.last_known_phase = target_phase
                        self.phase_confidence = confidence
                        self.pending_phase = None
                        self.frames_in_pending = 0
                else:
                    self.pending_phase = target_phase
                    self.frames_in_pending = 1
            else:
                self.pending_phase = None
                self.frames_in_pending = 0
                self.phase_confidence = confidence
                
            self._update_stats(self.current_phase, timestamp_ms)
            return self.current_phase, self.phase_confidence
            
        except Exception as e:
            logger.debug_log(f"Error analyzing butterfly phase: {e}")
            return self.current_phase, self.phase_confidence
            
    def _update_stats(self, phase: str, timestamp_ms: int):
        time_ms = 1000.0 / self.fps if self.fps > 0 else 33.3
        if phase in self.time_in_phases:
            self.time_in_phases[phase] += time_ms
