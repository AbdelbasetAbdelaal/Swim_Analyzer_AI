"""
Handles video frame annotation based on visualization modes.
"""
import cv2
import numpy as np
from typing import Any, Optional
from core.constants import COLOR_RED, COLOR_GREEN, COLOR_WHITE, THICKNESS_LANDMARK, THICKNESS_CONNECTION
from models.data_models import JointAngles

POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32), (27, 31), (28, 32)
]

class VideoAnnotator:
    """
    Draws information onto a video frame based on the visualization mode.
    Modes:
    - User Mode: Clean video + minimal coaching
    - Coach Mode: Skeleton + joint angles + phase + coaching
    - Developer Mode: Everything above + deep debugging info
    """
    
    def __init__(self, mode: str = "Developer Mode", trajectory_frames: int = 60):
        self.mode = mode
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.trajectory_frames = trajectory_frames
        self.hand_history = [] # list of (x, y) tuples
        self.last_transition = None # string describing last transition
        self.transition_timer = 0
        
    def annotate(self, frame: np.ndarray, landmarks: Any, angles: Optional[JointAngles], 
                 frame_idx: int, timestamp: int, confidence: float, phase: str, fps: float, 
                 score: Optional[float] = None, errors: int = 0, new_transitions: list = None,
                 technique_assessment: Optional[str] = None,
                 evidence_sufficiency: Optional[str] = None) -> np.ndarray:
        """Annotates a single frame with evidence-aware technique score and assessment."""
        annotated = frame.copy()
        height, width, _ = annotated.shape
        
        pixel_landmarks = []
        wrist_pos = None
        if landmarks:
            for i, lm in enumerate(landmarks):
                x = int(lm.x * width)
                y = int(lm.y * height)
                pixel_landmarks.append((x, y))
                if i == 16: # Right wrist
                    wrist_pos = (x, y)
                    
        if wrist_pos:
            self.hand_history.append(wrist_pos)
            if len(self.hand_history) > self.trajectory_frames:
                self.hand_history.pop(0)
                
        if new_transitions:
            # Just take the latest one
            t = new_transitions[-1]
            self.last_transition = f"{t.from_phase} -> {t.to_phase} ({t.reason})"
            self.transition_timer = int(fps * 1.5) # show for 1.5 seconds
            
        if self.transition_timer > 0:
            self.transition_timer -= 1
        else:
            self.last_transition = None

        # Build evidence-aware technique score text and color
        if score is not None:
            score_text = f"Available Technique Score: {score:.1f}/100"
            if technique_assessment and technique_assessment.upper() not in ("N/A", "UNKNOWN", "NONE"):
                score_text += f" ({technique_assessment})"
            score_color = (0, 255, 0) if score >= 80 else (0, 215, 255) if score >= 60 else (0, 165, 255)
        else:
            score_text = "Available Technique Score: INSUFFICIENT EVIDENCE"
            score_color = (0, 165, 255) # Warning Amber/Orange
                
        # User Mode (Minimal)
        if self.mode == "User Mode":
            if landmarks:
                self._draw_skeleton(annotated, pixel_landmarks)
            self._draw_text_with_background(annotated, score_text, (20, 35), self.font, 0.65, score_color, 2)
            if errors > 0:
                self._draw_text_with_background(annotated, f"Errors Detected: {errors}", (20, 70), self.font, 0.65, (0, 0, 255), 2)
            return annotated
            
        # Coach Mode
        if self.mode == "Coach Mode":
            if landmarks:
                self._draw_skeleton(annotated, pixel_landmarks)
                self._draw_angles(annotated, pixel_landmarks, angles)
            self._draw_text_with_background(annotated, f"Phase: {phase}", (20, 35), self.font, 0.75, (255, 255, 0), 2)
            self._draw_text_with_background(annotated, score_text, (20, 70), self.font, 0.65, score_color, 2)
            return annotated
            
        # Developer Mode (Full)
        if self.mode == "Developer Mode":
            self._draw_trajectory(annotated)
            
            if landmarks:
                self._draw_skeleton(annotated, pixel_landmarks)
                self._draw_angles(annotated, pixel_landmarks, angles)
                
            self._draw_debug_panel(annotated, frame_idx, timestamp, confidence, phase, fps, score, errors, len(pixel_landmarks), technique_assessment)
            
            if self.last_transition:
                self._draw_text_with_background(annotated, f"TRANSITION: {self.last_transition}", (20, height - 30), self.font, 0.7, (0, 255, 255), 2)
                
        return annotated
        
    def _draw_trajectory(self, frame):
        if len(self.hand_history) < 2:
            return
            
        # Draw with fading alpha. Since OpenCV doesn't support alpha line drawing directly easily,
        # we draw on an overlay and blend.
        overlay = frame.copy()
        
        for i in range(1, len(self.hand_history)):
            pt1 = self.hand_history[i-1]
            pt2 = self.hand_history[i]
            
            # Calculate intensity based on position in history
            intensity = int((i / len(self.hand_history)) * 255)
            color = (0, intensity, 255) # Red to Yellowish
            thickness = max(1, int((i / len(self.hand_history)) * 4))
            
            cv2.line(overlay, pt1, pt2, color, thickness)
            
        # Blend it in
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    def _draw_skeleton(self, frame, pixel_landmarks):
        for connection in POSE_CONNECTIONS:
            start_idx, end_idx = connection
            if start_idx < len(pixel_landmarks) and end_idx < len(pixel_landmarks):
                cv2.line(frame, pixel_landmarks[start_idx], pixel_landmarks[end_idx], COLOR_GREEN, THICKNESS_CONNECTION)
        for x, y in pixel_landmarks:
            cv2.circle(frame, (x, y), THICKNESS_LANDMARK, COLOR_RED, -1)
            
    def _draw_angles(self, frame, pixel_landmarks, angles):
        if not angles: return
        def draw_text(angle_val, idx):
            if angle_val and idx < len(pixel_landmarks):
                x, y = pixel_landmarks[idx]
                text = f"{int(angle_val.value)}d" if angle_val.valid else "N/A"
                color = COLOR_WHITE if angle_val.valid else (128, 128, 128)
                cv2.putText(frame, text, (x + 10, y + 10), self.font, 0.5, color, 1)
        
        draw_text(angles.left_elbow, 13)
        draw_text(angles.right_elbow, 14)
        draw_text(angles.left_knee, 25)
        draw_text(angles.right_knee, 26)
        
    def _draw_debug_panel(self, frame, frame_idx, timestamp, conf, phase, fps, score, errors, lm_count, technique_assessment=None):
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (430, 280), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        score_val_str = f"{score:.1f}/100" if score is not None else "INSUFFICIENT"
        assessment_str = technique_assessment if technique_assessment else "N/A"

        texts = [
            "DEV DEBUG MODE",
            f"Frame: {frame_idx} | TS: {timestamp}ms",
            f"Effective FPS: {fps:.2f}",
            f"Confidence: {conf:.2f}",
            f"Stroke Phase: {phase}",
            f"Landmarks: {lm_count}/33",
            f"Available Technique Score: {score_val_str}",
            f"Technique Assessment: {assessment_str}",
            f"Active Errors: {errors}"
        ]
        
        y = 35
        for t in texts:
            color = (0, 255, 0) if "Score" in t and score is not None else (0, 165, 255) if "Score" in t else (0, 0, 255) if "Error" in t else (255, 255, 255)
            cv2.putText(frame, t, (20, y), self.font, 0.55, color, 1, cv2.LINE_AA)
            y += 26

    def _draw_text_with_background(self, frame, text, pos, font, scale, color, thickness=2, bg_color=(0, 0, 0)):
        """Draws text with a dark rectangular background pill for maximum contrast and legibility."""
        (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
        x, y = pos
        cv2.rectangle(frame, (x - 4, y - th - 4), (x + tw + 4, y + baseline + 4), bg_color, -1)
        cv2.putText(frame, text, (x, y), font, scale, color, thickness, cv2.LINE_AA)

