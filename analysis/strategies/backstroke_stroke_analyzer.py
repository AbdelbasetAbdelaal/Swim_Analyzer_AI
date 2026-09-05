"""
Analyzes stroke phases for Backstroke using a deterministic state machine.
"""
from typing import Any, List
from core.logger import setup_logger
from models.data_models import PhaseTransition
from analysis.strategies.base_strategy import BaseStrokeStateMachine

logger = setup_logger(__name__)

class BackstrokeStateMachine(BaseStrokeStateMachine):
    """
    State machine for Backstroke phase detection.
    Backstroke phases: Entry, Catch, Pull, Push, Recovery.
    The swimmer is face-up, so wrist position logic is inverted vs freestyle.
    """

    STATES = ["Unknown", "Entry", "Catch", "Pull", "Push", "Recovery"]

    def __init__(self, fps: float = 30.0):
        self.fps = fps
        self.current_phase = "Unknown"
        self.phase_confidence = 0.0

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
            # Right wrist (16), right shoulder (12), right hip (24)
            wrist = landmarks[16]
            shoulder = landmarks[12]
            hip = landmarks[24]

            wrist_x, wrist_y = wrist.x, wrist.y
            shoulder_x, shoulder_y = shoulder.x, shoulder.y
            hip_x = hip.x

            self.wrist_x_history.append(wrist_x)
            self.wrist_y_history.append(wrist_y)
            self.timestamp_history.append(timestamp_ms)

            if len(self.wrist_x_history) > self.history_size:
                self.wrist_x_history.pop(0)
                self.wrist_y_history.pop(0)
                self.timestamp_history.pop(0)

            # Velocity
            velocity_x = 0.0
            velocity_y = 0.0
            if len(self.wrist_x_history) > 1:
                dx = self.wrist_x_history[-1] - self.wrist_x_history[0]
                dy = self.wrist_y_history[-1] - self.wrist_y_history[0]
                dt = (self.timestamp_history[-1] - self.timestamp_history[0]) / 1000.0
                if dt > 0:
                    velocity_x = dx / dt
                    velocity_y = dy / dt

            # Backstroke heuristics:
            # In backstroke, the arm exits behind the head (wrist above shoulder)
            # and enters in front of the hip area.
            # Swimming direction determines push/pull X-axis logic.
            is_swimming_right = shoulder_x < hip_x

            target_phase = "Unknown"
            reason = ""
            confidence = 1.0

            # Recovery: wrist is above shoulder height (out of water, swinging over)
            if wrist_y < shoulder_y - 0.05:
                target_phase = "Recovery"
                reason = "Wrist above shoulder — arm in aerial recovery"

            # Entry: wrist just entering water near/behind head level
            elif wrist_y < shoulder_y + 0.1 and (
                (is_swimming_right and wrist_x > shoulder_x + 0.05) or
                (not is_swimming_right and wrist_x < shoulder_x - 0.05)
            ):
                target_phase = "Entry"
                reason = "Wrist near shoulder height, extended past shoulder in swim direction"

            # Catch: wrist at shoulder level, arm beginning to bend
            elif wrist_y < shoulder_y + 0.15:
                target_phase = "Catch"
                reason = "Wrist at catch depth near shoulder"

            # Pull: wrist between shoulder and hip
            elif wrist_y < hip.y - 0.05:
                target_phase = "Pull"
                reason = "Wrist pulling through mid-body range"

            # Push: wrist past hip
            else:
                target_phase = "Push"
                reason = "Wrist pushing past hip toward finish"

            # Temporal filtering
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
                        logger.debug_log(
                            f"\nFrame {frame_idx} | {self.current_phase} -> {target_phase} | Conf: {confidence:.2f}")

                        last_phase = getattr(self, "last_known_phase", "Unknown")
                        if last_phase == "Recovery" and target_phase in ["Entry", "Catch"]:
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
            logger.debug_log(f"Error analyzing backstroke phase: {e}")
            return self.current_phase, self.phase_confidence

    def _update_stats(self, phase: str, timestamp_ms: int):
        time_ms = 1000.0 / self.fps if self.fps > 0 else 33.3
        if phase in self.time_in_phases:
            self.time_in_phases[phase] += time_ms
