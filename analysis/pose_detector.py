"""
Pose detection utilizing MediaPipe Tasks API.
"""
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from typing import Optional, Tuple, Any
from core.logger import setup_logger
from core.config import config
from core.constants import COLOR_RED, COLOR_GREEN, COLOR_WHITE, THICKNESS_LANDMARK, THICKNESS_CONNECTION
from models.data_models import JointAngles
from analysis.landmark_smoother import LandmarkSmoother

logger = setup_logger(__name__)

# Standard 33 landmarks connections for MediaPipe Pose
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32), (27, 31), (28, 32)
]

class PoseDetector:
    """
    Purpose: Wrapper for MediaPipe Pose Landmarker using the Tasks API to detect, smooth, and draw poses.
    Inputs: Uses config.pose_model_path for initialization. Takes BGR image frames for detection.
    Outputs: Smoothed landmark coordinates and temporal validity metrics.
    Exceptions: Raises RuntimeError if MediaPipe initialization fails or model file is missing.
    Example:
        detector = PoseDetector()
        landmarks, is_valid = detector.detect_pose(frame)
        annotated_frame = detector.draw_pose(frame, landmarks)
        detector.close()
    """
    def __init__(self):
        logger.info(f"Initializing PoseDetector with model: {config.pose_model_path}")
        
        base_options = python.BaseOptions(model_asset_path=str(config.pose_model_path))
        self._options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            min_pose_detection_confidence=config.pose_min_detection_confidence,
            min_pose_presence_confidence=config.pose_min_tracking_confidence,
            output_segmentation_masks=False
        )
        self.detector = vision.PoseLandmarker.create_from_options(self._options)
        self.smoother = LandmarkSmoother(alpha=0.4)
        self._frame_timestamp_ms = 0
        self._last_timestamp_ms = -1

    def reset(self):
        """
        Resets internal timestamp tracker, smoothing state, and recreates
        the MediaPipe PoseLandmarker graph to safely start a new video stream.
        """
        self._frame_timestamp_ms = 0
        self._last_timestamp_ms = -1
        self.smoother = LandmarkSmoother(alpha=0.4)
        if self.detector:
            try:
                self.detector.close()
            except Exception:
                pass
        self.detector = vision.PoseLandmarker.create_from_options(self._options)
        logger.info("PoseDetector reset: timestamp tracker and graph reinitialized.")
        
    def detect_pose(self, frame: np.ndarray, timestamp_ms: Optional[int] = None) -> Tuple[Any, bool]:
        """
        Detects poses in a single BGR frame using VIDEO running mode.
        
        Args:
            frame: A numpy array representing a BGR image.
            timestamp_ms: Optional timestamp in milliseconds for sequential video tracking.
            
        Returns:
            Tuple[Any, bool]: The smoothed landmarks, and a boolean indicating if confidence is high enough.
        """
        # Convert BGR (OpenCV) to RGB (MediaPipe) with contiguous memory layout
        rgb_frame = np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        if timestamp_ms is not None:
            raw_ts = int(timestamp_ms)
        else:
            raw_ts = self._frame_timestamp_ms
            self._frame_timestamp_ms += 33  # ~30 FPS default step

        # Strict monotonic timestamp enforcement: ts must be > _last_timestamp_ms
        if raw_ts <= self._last_timestamp_ms:
            ts = self._last_timestamp_ms + 1
        else:
            ts = raw_ts
        self._last_timestamp_ms = ts
            
        try:
            result = self.detector.detect_for_video(mp_image, ts)
        except Exception as exc:
            err_msg = str(exc)
            if "timestamp" in err_msg.lower():
                logger.error(f"MediaPipe Tasks timestamp lifecycle error at {ts}ms: {exc}")
                raise RuntimeError(f"MediaPipe timestamp violation: {exc}") from exc
            logger.warning(f"Pose detection failed on frame: {exc}")
            return None, False
        
        is_valid = False
        smoothed_landmarks = None
        
        if result.pose_landmarks and len(result.pose_landmarks) > 0:
            raw_landmarks = result.pose_landmarks[0]
            
            # Check average confidence and visible landmark count
            visible_count = sum(1 for lm in raw_landmarks if getattr(lm, 'visibility', 0.0) > 0.4)
            avg_confidence = sum(getattr(lm, 'visibility', 0.0) for lm in raw_landmarks) / len(raw_landmarks)
            is_valid = avg_confidence >= config.landmark_confidence_threshold and visible_count >= 18
            
            # Smooth the landmarks for downstream processing even if low confidence
            smoothed_landmarks = self.smoother.smooth(raw_landmarks)
            
        return smoothed_landmarks, is_valid
        
    def draw_pose(self, frame: np.ndarray, landmarks: Any, angles: Optional[JointAngles] = None) -> np.ndarray:
        """
        Draw the skeleton and optional angles onto a frame.
        
        Args:
            frame: A numpy array representing a BGR image.
            landmarks: The pose landmarks detected previously.
            angles: Optional JointAngles to display on the frame.
            
        Returns:
            The annotated frame.
        """
        annotated_frame = frame.copy()
        
        if landmarks:
            height, width, _ = annotated_frame.shape
            
            # Map normalized coordinates to pixel coordinates
            pixel_landmarks = []
            for lm in landmarks:
                x = int(lm.x * width)
                y = int(lm.y * height)
                pixel_landmarks.append((x, y))
                
            # Draw connections (bones)
            for connection in POSE_CONNECTIONS:
                start_idx, end_idx = connection
                # Check if we have enough landmarks
                if start_idx < len(pixel_landmarks) and end_idx < len(pixel_landmarks):
                    start_point = pixel_landmarks[start_idx]
                    end_point = pixel_landmarks[end_idx]
                    cv2.line(annotated_frame, start_point, end_point, COLOR_GREEN, THICKNESS_CONNECTION)
            
            # Draw landmarks (joints)
            for x, y in pixel_landmarks:
                cv2.circle(annotated_frame, (x, y), THICKNESS_LANDMARK, COLOR_RED, -1)
                
            # Draw angles if provided
            if angles:
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.5
                thickness = 1
                
                # Helper to draw text
                def draw_angle_text(angle_val, landmark_idx):
                    if angle_val is not None and landmark_idx < len(pixel_landmarks):
                        x, y = pixel_landmarks[landmark_idx]
                        text = f"{int(angle_val)}d"
                        cv2.putText(annotated_frame, text, (x + 10, y + 10), font, font_scale, COLOR_WHITE, thickness)
                
                draw_angle_text(angles.left_elbow, 13)
                draw_angle_text(angles.right_elbow, 14)
                draw_angle_text(angles.left_knee, 25)
                draw_angle_text(angles.right_knee, 26)
            
        return annotated_frame
        
    def close(self):
        """Releases the underlying MediaPipe resources."""
        self.detector.close()
        logger.info("PoseDetector resources released.")
