"""
Analyzes stroke phases based on motion tracking over time using a deterministic state machine.
"""
from typing import Any, List
import numpy as np
from core.logger import setup_logger
from models.data_models import PhaseTransition
from analysis.strategies.base_strategy import BaseStrokeStateMachine

logger = setup_logger(__name__)

class FreestyleStrokeStateMachine(BaseStrokeStateMachine):
    """
    Deterministic state machine with temporal filtering and history buffer
    for robust stroke phase detection.
    """
    
    STATES = ["Unknown", "Entry", "Catch", "Pull", "Push", "Recovery"]
    
    def __init__(self, fps: float = 30.0):
        self.fps = fps
        self.current_phase = "Unknown"
        self.phase_confidence = 0.0
        
        # History buffer for hand tracking (right wrist index 16)
        self.history_size = 5
        self.wrist_x_history: List[float] = []
        self.wrist_y_history: List[float] = []
        self.timestamp_history: List[int] = []
        
        # Temporal filtering
        self.pending_phase = None
        self.frames_in_pending = 0
        self.temporal_threshold = max(2, int(self.fps * 0.1)) # e.g., 3 frames at 30fps
        
        # Logging & Stats
        self.transitions: List[PhaseTransition] = []
        self.time_in_phases = {state: 0.0 for state in self.STATES}
        self.completed_cycles = 0
        self.frame_count = 0
        
    def _calculate_velocity(self) -> float:
        """Calculates rough X-axis velocity of the wrist."""
        if len(self.wrist_x_history) < 2:
            return 0.0
            
        dx = self.wrist_x_history[-1] - self.wrist_x_history[0]
        dt = (self.timestamp_history[-1] - self.timestamp_history[0]) / 1000.0
        if dt == 0:
            return 0.0
        return dx / dt
        
    def analyze_frame(self, landmarks: Any, frame_idx: int, timestamp_ms: int) -> tuple[str, float]:
        """
        Determines the current stroke phase.
        Returns: (phase_name, confidence)
        """
        self.frame_count += 1
        
        if not landmarks or len(landmarks) < 25:
            self._update_stats("Unknown", timestamp_ms)
            return "Unknown", 0.0
            
        try:
            wrist_x = landmarks[16].x
            wrist_y = landmarks[16].y
            shoulder_x = landmarks[12].x
            shoulder_y = landmarks[12].y
            hip_x = landmarks[24].x
            
            # Update history
            self.wrist_x_history.append(wrist_x)
            self.wrist_y_history.append(wrist_y)
            self.timestamp_history.append(timestamp_ms)
            
            if len(self.wrist_x_history) > self.history_size:
                self.wrist_x_history.pop(0)
                self.wrist_y_history.pop(0)
                self.timestamp_history.pop(0)
                
            velocity_x = self._calculate_velocity()
            
            # Determine base state using robust relative positioning
            s_left, s_right = landmarks[11], landmarks[12]
            h_left, h_right = landmarks[23], landmarks[24]
            shoulder_width = abs(s_left.x - s_right.x)
            
            mid_shoulder_x = (s_left.x + s_right.x) / 2
            mid_shoulder_y = (s_left.y + s_right.y) / 2
            mid_hip_x = (h_left.x + h_right.x) / 2
            mid_hip_y = (h_left.y + h_right.y) / 2
            
            torso_len = np.sqrt((mid_shoulder_x - mid_hip_x)**2 + (mid_shoulder_y - mid_hip_y)**2)
            
            is_front_facing = False
            if torso_len > 0 and (shoulder_width / torso_len) > 0.6: # Front facing shoulders are much wider relative to torso in 2D
                # Still check if we're moving purely horizontally
                if abs(mid_shoulder_x - mid_hip_x) < abs(mid_shoulder_y - mid_hip_y):
                    is_front_facing = True
                
            is_swimming_left = shoulder_x < hip_x
            target_phase = "Unknown"
            reason = ""
            confidence = 1.0
            
            if is_front_facing:
                # Calculate Y velocity (negative means moving UP in image space)
                dy = self.wrist_y_history[-1] - self.wrist_y_history[0] if len(self.wrist_y_history) > 1 else 0
                dt = (self.timestamp_history[-1] - self.timestamp_history[0]) / 1000.0 if len(self.timestamp_history) > 1 else 0.1
                velocity_y = dy / dt if dt > 0 else 0
                
                hip_y = landmarks[24].y
                
                if wrist_y < shoulder_y and velocity_y < -0.02:
                    target_phase = "Recovery"
                    reason = "Wrist is high and moving upwards"
                elif velocity_y < -0.1:
                    target_phase = "Recovery"
                    reason = "Wrist is moving upwards rapidly"
                elif wrist_y < shoulder_y + 0.15:
                    target_phase = "Entry" if wrist_y < shoulder_y + 0.05 else "Catch"
                    reason = "Wrist is near shoulder level"
                elif wrist_y < hip_y - 0.1:
                    target_phase = "Pull"
                    reason = "Wrist is pulling down between shoulder and hip"
                else:
                    target_phase = "Push"
                    reason = "Wrist is pushing near or past hip"
                    
            elif is_swimming_left:
                # Swimming left: smaller X is forward.
                # Recovery: wrist is moving forward and is above or at shoulder level
                if wrist_y <= shoulder_y and velocity_x < -0.01:
                    target_phase = "Recovery"
                    reason = "Wrist is high and moving forward"
                elif wrist_y < shoulder_y - 0.05:
                    target_phase = "Recovery"
                    reason = "Wrist is significantly above shoulder"
                elif wrist_x < shoulder_x - 0.02:
                    if wrist_y < shoulder_y + 0.1:
                        target_phase = "Entry"
                        reason = "Wrist entered water in front of shoulder"
                    else:
                        target_phase = "Catch"
                        reason = "Wrist catching water in front of shoulder"
                elif shoulder_x - 0.02 <= wrist_x <= hip_x + 0.05:
                    target_phase = "Pull"
                    reason = "Wrist is under body between shoulder and hip"
                    if velocity_x < -0.05 and self.current_phase == "Pull": 
                        confidence = 0.5
                else:
                    target_phase = "Push"
                    reason = "Wrist is pushing past hip"
            else:
                # Swimming right: larger X is forward.
                if wrist_y <= shoulder_y and velocity_x > 0.01:
                    target_phase = "Recovery"
                    reason = "Wrist is high and moving forward"
                elif wrist_y < shoulder_y - 0.05:
                    target_phase = "Recovery"
                    reason = "Wrist is significantly above shoulder"
                elif wrist_x > shoulder_x + 0.02:
                    if wrist_y < shoulder_y + 0.1:
                        target_phase = "Entry"
                        reason = "Wrist entered water in front of shoulder"
                    else:
                        target_phase = "Catch"
                        reason = "Wrist catching water in front of shoulder"
                elif hip_x - 0.05 <= wrist_x <= shoulder_x + 0.02:
                    target_phase = "Pull"
                    reason = "Wrist is under body between shoulder and hip"
                    if velocity_x > 0.05 and self.current_phase == "Pull":
                        confidence = 0.5
                else:
                    target_phase = "Push"
                    reason = "Wrist is pushing past hip"
                    
            if not is_front_facing and confidence < 0.4:
                target_phase = "Unknown"
                reason = "Confidence too low based on velocity mismatch"
                
            # Enforce Sequential State Machine Constraints
            valid_transitions = {
                "Unknown": ["Entry", "Catch", "Pull", "Push", "Recovery"],
                "Entry": ["Catch", "Pull", "Unknown"],
                "Catch": ["Pull", "Push", "Unknown"],
                "Pull": ["Push", "Recovery", "Entry", "Unknown"],
                "Push": ["Recovery", "Entry", "Pull", "Unknown"],
                "Recovery": ["Entry", "Catch", "Pull", "Unknown"]
            }
            
            if target_phase != self.current_phase and self.current_phase in valid_transitions and target_phase not in valid_transitions[self.current_phase]:
                if target_phase != "Unknown":
                    # Reduce confidence significantly if we jump completely out of sequence
                    confidence = 0.2
                    reason += f" (Violates sequential transition from {self.current_phase})"
                    # We still allow the transition if the signal is strong for temporal threshold frames, 
                    # but the low confidence will penalize the score via the reliability engine.
                
            # Temporal Filtering
            if target_phase != self.current_phase:
                if target_phase == self.pending_phase:
                    self.frames_in_pending += 1
                    if self.frames_in_pending >= self.temporal_threshold:
                        # Log transition
                        transition = PhaseTransition(
                            frame_index=frame_idx,
                            timestamp_ms=timestamp_ms,
                            from_phase=self.current_phase,
                            to_phase=target_phase,
                            reason=reason,
                            confidence=confidence
                        )
                        self.transitions.append(transition)
                        
                        logger.debug_log(f"\nFrame {frame_idx}\nTimestamp {timestamp_ms}ms\n{self.current_phase} -> {target_phase}\nConfidence: {confidence:.2f}\nReason:\n{reason}\n")
                        # Cycle counting logic
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
            logger.debug(f"Error analyzing stroke phase: {e}")
            return self.current_phase, self.phase_confidence
            
    def _update_stats(self, phase: str, timestamp_ms: int):
        """Accumulates time spent in current phase."""
        # We approximate time per frame as 1000/fps ms
        time_ms = 1000.0 / self.fps if self.fps > 0 else 33.3
        self.time_in_phases[phase] += time_ms
