"""
Kinematic Feature Extractor for Swimming Stroke Classification.
Extracts temporal biomechanical features over landmark frame sequences.
"""
from dataclasses import dataclass
from typing import List, Optional, Any
import numpy as np
import math

from core.logger import setup_logger

logger = setup_logger(__name__)

# MediaPipe Pose Landmark Indices
NOSE = 0
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_ANKLE = 27
RIGHT_ANKLE = 28

@dataclass
class ExtractedFeatureValue:
    """Stores a single kinematic feature with validity, raw value, and missing-data conditions."""
    feature_name: str
    raw_value: Optional[float]
    valid: bool
    missing_data_condition: Optional[str] = None
    window_frame_count: int = 0
    valid_frame_count: int = 0

@dataclass
class KinematicFeatureSet:
    """Holds all extracted kinematic features for a given frame window."""
    arm_phase_correlation: ExtractedFeatureValue
    mean_body_roll: ExtractedFeatureValue
    body_roll_amplitude: ExtractedFeatureValue
    wrist_vertical_range_ratio: ExtractedFeatureValue
    leg_kick_symmetry: ExtractedFeatureValue
    wrist_recovery_height_ratio: ExtractedFeatureValue
    total_frames_in_window: int
    valid_frames_in_window: int
    window_start_frame: int
    window_end_frame: int
    head_supine_ratio: Optional[ExtractedFeatureValue] = None


class KinematicFeatureExtractor:
    """
    Extracts temporal biomechanical features across landmark frame sequences.
    Strictly enforces missing-data handling without silent zero substitutions.
    """

    def __init__(self, min_valid_frames: int = 2, visibility_threshold: float = 0.1):
        self.min_valid_frames = min_valid_frames
        self.visibility_threshold = visibility_threshold

    def extract_features(self, frames: List[Any], window_start: int = 0, window_end: Optional[int] = None) -> KinematicFeatureSet:
        """
        Extracts temporal kinematic feature set over a frame sequence slice [window_start:window_end].
        """
        if not frames:
            return self._build_empty_feature_set(0, 0, "NO_FRAMES")

        if window_end is None:
            window_end = len(frames)

        frame_slice = frames[window_start:window_end]
        total_frames = len(frame_slice)

        # Filter valid frames containing raw landmarks (regardless of pose confidence thresholds)
        valid_frames = [f for f in frame_slice if getattr(f, 'raw_landmarks', None) and len(f.raw_landmarks) > 0]
        valid_count = len(valid_frames)

        if valid_count < self.min_valid_frames:
            return self._build_empty_feature_set(window_start, window_end, f"INSUFFICIENT_VALID_FRAMES (Got {valid_count}, required {self.min_valid_frames})", total_frames, valid_count)

        # 1. Extract Trajectory Time-series
        lw_y, rw_y = [], []
        la_y, ra_y = [], []
        body_rolls = []
        lw_max_h, rw_max_h = [], []

        for f in valid_frames:
            lms = f.raw_landmarks
            # Verify required landmarks exist
            if len(lms) > max(LEFT_WRIST, RIGHT_WRIST, LEFT_ANKLE, RIGHT_ANKLE, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP):
                l_wrist = lms[LEFT_WRIST]
                r_wrist = lms[RIGHT_WRIST]
                l_ankle = lms[LEFT_ANKLE]
                r_ankle = lms[RIGHT_ANKLE]
                l_sh = lms[LEFT_SHOULDER]
                r_sh = lms[RIGHT_SHOULDER]
                l_hip = lms[LEFT_HIP]
                r_hip = lms[RIGHT_HIP]

                # Extract wrist Y coordinates (shoulder-relative if shoulders present to normalize translation)
                if l_wrist and r_wrist:
                    if l_sh and r_sh:
                        sh_avg_y = (l_sh.y + r_sh.y) / 2.0
                        lw_y.append(l_wrist.y - sh_avg_y)
                        rw_y.append(r_wrist.y - sh_avg_y)
                    else:
                        lw_y.append(l_wrist.y)
                        rw_y.append(r_wrist.y)

                # Extract ankle Y coordinates
                if l_ankle and r_ankle:
                    if l_hip and r_hip:
                        hip_avg_y = (l_hip.y + r_hip.y) / 2.0
                        la_y.append(l_ankle.y - hip_avg_y)
                        ra_y.append(r_ankle.y - hip_avg_y)
                    else:
                        la_y.append(l_ankle.y)
                        ra_y.append(r_ankle.y)

                # Body roll angle calculation
                if hasattr(f, 'angles') and f.angles and hasattr(f.angles, 'body_roll') and f.angles.body_roll and f.angles.body_roll.valid:
                    body_rolls.append(f.angles.body_roll.value)
                elif l_sh and r_sh:
                    dx = r_sh.x - l_sh.x
                    dy = r_sh.y - l_sh.y
                    roll_deg = abs(math.degrees(math.atan2(dy, dx)))
                    body_rolls.append(roll_deg)

        # Fallback if strict visibility filtered out submerged wrists
        if len(lw_y) < self.min_valid_frames:
            lw_y = [f.raw_landmarks[LEFT_WRIST].y for f in valid_frames if len(f.raw_landmarks) > LEFT_WRIST]
            rw_y = [f.raw_landmarks[RIGHT_WRIST].y for f in valid_frames if len(f.raw_landmarks) > RIGHT_WRIST]

        if len(la_y) < self.min_valid_frames:
            la_y = [f.raw_landmarks[LEFT_ANKLE].y for f in valid_frames if len(f.raw_landmarks) > LEFT_ANKLE]
            ra_y = [f.raw_landmarks[RIGHT_ANKLE].y for f in valid_frames if len(f.raw_landmarks) > RIGHT_ANKLE]


        # Feature 1: Arm Phase Correlation
        feat_arm_phase = self._calculate_correlation("arm_phase_correlation", lw_y, rw_y, total_frames, valid_count)

        # Feature 2: Mean Body Roll
        feat_mean_roll = self._calculate_mean("mean_body_roll", body_rolls, total_frames, valid_count)

        # Feature 3: Body Roll Amplitude
        feat_roll_amp = self._calculate_amplitude("body_roll_amplitude", body_rolls, total_frames, valid_count)

        # Feature 4: Wrist Vertical Range Ratio
        feat_wrist_range = self._calculate_range_ratio("wrist_vertical_range_ratio", lw_y, rw_y, total_frames, valid_count)

        # Feature 5: Leg Kick Symmetry
        feat_leg_sym = self._calculate_correlation("leg_kick_symmetry", la_y, ra_y, total_frames, valid_count)

        # Feature 6: Wrist Recovery Height Ratio
        feat_wrist_height_ratio = self._calculate_height_ratio("wrist_recovery_height_ratio", lw_y, rw_y, total_frames, valid_count)

        # Feature 7: Head Supine Ratio (Face-Up Backstroke Indicator)
        supine_count = 0
        supine_valid_count = 0
        for f in valid_frames:
            lms = f.raw_landmarks
            if len(lms) > max(NOSE, LEFT_SHOULDER, RIGHT_SHOULDER):
                nose_lm = lms[NOSE]
                l_sh = lms[LEFT_SHOULDER]
                r_sh = lms[RIGHT_SHOULDER]
                if nose_lm and l_sh and r_sh:
                    sh_avg_y = (l_sh.y + r_sh.y) / 2.0
                    supine_valid_count += 1
                    if nose_lm.y < sh_avg_y:
                        supine_count += 1

        if supine_valid_count >= self.min_valid_frames:
            supine_ratio = float(supine_count / supine_valid_count)
            feat_head_supine = ExtractedFeatureValue("head_supine_ratio", supine_ratio, True, None, total_frames, valid_count)
        else:
            feat_head_supine = ExtractedFeatureValue("head_supine_ratio", None, False, "INSUFFICIENT_LANDMARKS", total_frames, valid_count)

        return KinematicFeatureSet(
            arm_phase_correlation=feat_arm_phase,
            mean_body_roll=feat_mean_roll,
            body_roll_amplitude=feat_roll_amp,
            wrist_vertical_range_ratio=feat_wrist_range,
            leg_kick_symmetry=feat_leg_sym,
            wrist_recovery_height_ratio=feat_wrist_height_ratio,
            total_frames_in_window=total_frames,
            valid_frames_in_window=valid_count,
            window_start_frame=window_start,
            window_end_frame=window_end,
            head_supine_ratio=feat_head_supine
        )


    def _calculate_correlation(self, name: str, s1: List[float], s2: List[float], total_cnt: int, valid_cnt: int) -> ExtractedFeatureValue:
        if len(s1) < self.min_valid_frames or len(s2) < self.min_valid_frames:
            return ExtractedFeatureValue(name, None, False, "INSUFFICIENT_VISIBILITY_SERIES", total_cnt, valid_cnt)

        arr1 = np.array(s1)
        arr2 = np.array(s2)
        std1 = np.std(arr1)
        std2 = np.std(arr2)

        if std1 < 1e-5 or std2 < 1e-5:
            # Low variance series (glide phase) -> return neutral 0.0 correlation with valid=True
            return ExtractedFeatureValue(name, 0.0, True, "LOW_VARIANCE_SERIES", total_cnt, valid_cnt)

        corr = float(np.corrcoef(arr1, arr2)[0, 1])
        if math.isnan(corr):
            return ExtractedFeatureValue(name, 0.0, True, "NAN_CORRELATION", total_cnt, valid_cnt)

        return ExtractedFeatureValue(name, corr, True, None, total_cnt, valid_cnt)


    def _calculate_mean(self, name: str, vals: List[float], total_cnt: int, valid_cnt: int) -> ExtractedFeatureValue:
        if len(vals) < self.min_valid_frames:
            return ExtractedFeatureValue(name, None, False, "INSUFFICIENT_BODY_ROLL_DATA", total_cnt, valid_cnt)

        mean_val = float(np.mean(vals))
        return ExtractedFeatureValue(name, mean_val, True, None, total_cnt, valid_cnt)

    def _calculate_amplitude(self, name: str, vals: List[float], total_cnt: int, valid_cnt: int) -> ExtractedFeatureValue:
        if len(vals) < self.min_valid_frames:
            return ExtractedFeatureValue(name, None, False, "INSUFFICIENT_BODY_ROLL_DATA", total_cnt, valid_cnt)

        amp = float(np.max(vals) - np.min(vals))
        return ExtractedFeatureValue(name, amp, True, None, total_cnt, valid_cnt)

    def _calculate_range_ratio(self, name: str, s1: List[float], s2: List[float], total_cnt: int, valid_cnt: int) -> ExtractedFeatureValue:
        if len(s1) < self.min_valid_frames or len(s2) < self.min_valid_frames:
            return ExtractedFeatureValue(name, None, False, "INSUFFICIENT_WRIST_DATA", total_cnt, valid_cnt)

        r1 = np.max(s1) - np.min(s1)
        r2 = np.max(s2) - np.min(s2)
        avg_range = float((r1 + r2) / 2.0)
        return ExtractedFeatureValue(name, avg_range, True, None, total_cnt, valid_cnt)

    def _calculate_height_ratio(self, name: str, s1: List[float], s2: List[float], total_cnt: int, valid_cnt: int) -> ExtractedFeatureValue:
        if len(s1) < self.min_valid_frames or len(s2) < self.min_valid_frames:
            return ExtractedFeatureValue(name, None, False, "INSUFFICIENT_WRIST_DATA", total_cnt, valid_cnt)

        # Minimum Y corresponds to highest point in MediaPipe normalized image coordinates
        h1 = np.min(s1)
        h2 = np.min(s2)
        ratio = float(abs(h1 - h2))
        return ExtractedFeatureValue(name, ratio, True, None, total_cnt, valid_cnt)

    def _build_empty_feature_set(self, start: int, end: int, reason: str, total_cnt: int = 0, valid_cnt: int = 0) -> KinematicFeatureSet:
        return KinematicFeatureSet(
            arm_phase_correlation=ExtractedFeatureValue("arm_phase_correlation", None, False, reason, total_cnt, valid_cnt),
            mean_body_roll=ExtractedFeatureValue("mean_body_roll", None, False, reason, total_cnt, valid_cnt),
            body_roll_amplitude=ExtractedFeatureValue("body_roll_amplitude", None, False, reason, total_cnt, valid_cnt),
            wrist_vertical_range_ratio=ExtractedFeatureValue("wrist_vertical_range_ratio", None, False, reason, total_cnt, valid_cnt),
            leg_kick_symmetry=ExtractedFeatureValue("leg_kick_symmetry", None, False, reason, total_cnt, valid_cnt),
            wrist_recovery_height_ratio=ExtractedFeatureValue("wrist_recovery_height_ratio", None, False, reason, total_cnt, valid_cnt),
            total_frames_in_window=total_cnt,
            valid_frames_in_window=valid_cnt,
            window_start_frame=start,
            window_end_frame=end
        )
