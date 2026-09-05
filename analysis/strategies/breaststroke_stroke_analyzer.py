"""
Analyzes stroke phases for Breaststroke based on motion tracking.
"""
from typing import Any, List
from core.logger import setup_logger
from models.data_models import PhaseTransition
from analysis.strategies.base_strategy import BaseStrokeStateMachine

logger = setup_logger(__name__)

class BreaststrokeStateMachine(BaseStrokeStateMachine):
    """
    State machine for Breaststroke phase detection.
    Breaststroke phases: Outsweep, Catch, Insweep, Recovery/Shoot, Glide.
    """
    
    STATES = ["Unknown", "Outsweep", "Catch", "Insweep", "Recovery", "Glide"]
    
    def __init__(self, fps: float = 30.0):
        self.fps = fps
        self.current_phase = "Unknown"
        self.phase_confidence = 0.0
        
        # History buffers
        self.history_size = 5
        self.wrist_y_history: List[float] = []
        self.wrist_x_history: List[float] = []
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
            # For breaststroke, we look at both wrists and shoulders since it's symmetric
            left_wrist = landmarks[15]
            right_wrist = landmarks[16]
            left_shoulder = landmarks[11]
            right_shoulder = landmarks[12]
            
            # Using right wrist for primary heuristic (assuming symmetry for now)
            wrist_y = right_wrist.y
            wrist_x = right_wrist.x
            shoulder_y = right_shoulder.y
            shoulder_x = right_shoulder.x
            
            self.wrist_y_history.append(wrist_y)
            self.wrist_x_history.append(wrist_x)
            self.timestamp_history.append(timestamp_ms)
            
            if len(self.wrist_y_history) > self.history_size:
                self.wrist_y_history.pop(0)
                self.wrist_x_history.pop(0)
                self.timestamp_history.pop(0)
                
            # Heuristics based on lateral spread (X) and depth (Y) relative to shoulders
            wrist_spread = abs(right_wrist.x - left_wrist.x)
            shoulder_width = abs(right_shoulder.x - left_shoulder.x)
            
            target_phase = "Unknown"
            reason = ""
            confidence = 1.0

            # Breaststroke heuristics (ordered from most specific to least):
            # Glide: hands together, close to shoulder level, minimal spread
            if wrist_spread < shoulder_width * 0.6 and abs(wrist_y - shoulder_y) < 0.12:
                target_phase = "Glide"
                reason = "Hands together, extended in front — glide phase"

            # Recovery/Shoot: wrists moving forward, above or at shoulder level
            elif wrist_y <= shoulder_y + 0.05 and wrist_spread < shoulder_width:
                target_phase = "Recovery"
                reason = "Hands shooting forward above water surface"

            # Insweep: wrists coming together below shoulder, spread narrowing
            elif wrist_spread < shoulder_width and wrist_y > shoulder_y + 0.1:
                target_phase = "Insweep"
                reason = "Wrists sweeping inward under chest"

            # Catch: maximum lateral extension — widest spread
            elif wrist_spread > shoulder_width * 1.6:
                target_phase = "Catch"
                reason = "Maximum lateral extension — catch position"

            # Outsweep: spreading wider than shoulders but not yet at max
            elif wrist_spread > shoulder_width:
                target_phase = "Outsweep"
                reason = "Wrists sweeping wider than shoulders"

            else:
                target_phase = "Unknown"
                confidence = 0.5
                reason = "No strong breaststroke pattern detected"
                
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
                        if last_phase == "Glide" and target_phase == "Outsweep":
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
            logger.debug_log(f"Error analyzing breaststroke phase: {e}")
            return self.current_phase, self.phase_confidence
            
    def _update_stats(self, phase: str, timestamp_ms: int):
        time_ms = 1000.0 / self.fps if self.fps > 0 else 33.3
        if phase in self.time_in_phases:
            self.time_in_phases[phase] += time_ms
