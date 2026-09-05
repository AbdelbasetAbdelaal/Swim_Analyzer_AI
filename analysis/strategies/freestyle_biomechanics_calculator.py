"""
Calculates advanced biomechanical metrics from pose landmarks.
"""
import numpy as np
from typing import Any, List
from models.data_models import JointAngles, FrameData, ValidatedMetric
from analysis.strategies.base_strategy import BaseBiomechanicsCalculator
from core.logger import setup_logger

logger = setup_logger(__name__)

class FreestyleBiomechanicsCalculator(BaseBiomechanicsCalculator):
    """
    Utility class for calculating angles and advanced biomechanics 
    using vector mathematics and frame history.
    """
    
    # MediaPipe landmark indices
    NOSE = 0
    L_SHOULDER, L_ELBOW, L_WRIST = 11, 13, 15
    R_SHOULDER, R_ELBOW, R_WRIST = 12, 14, 16
    L_HIP, L_KNEE, L_ANKLE = 23, 25, 27
    R_HIP, R_KNEE, R_ANKLE = 24, 26, 28

    @staticmethod
    def _create_angle_metric(angle: float, name: str) -> ValidatedMetric:
        """Validates an angle and returns a ValidatedMetric."""
        valid = True
        reason = ""
        # For body roll, acceptable range is 0-90
        # For joint angles, acceptable range is 0-180
        if name == "body_roll":
            if not (0 <= angle <= 90):
                valid = False
                reason = f"Body roll {angle:.1f} is outside 0-90 range."
        else:
            if not (0 <= angle <= 180):
                valid = False
                reason = f"{name} {angle:.1f} is outside 0-180 range."
                
        if not valid:
            logger.debug(reason)
            
        return ValidatedMetric(value=angle, confidence=1.0, valid=valid, reason_if_invalid=reason)

    @staticmethod
    def calculate_angle(a: Any, b: Any, c: Any) -> float:
        """Calculate the interior angle between three points."""
        a_coords = np.array([a.x, a.y])
        b_coords = np.array([b.x, b.y])
        c_coords = np.array([c.x, c.y])
        
        radians = np.arctan2(c_coords[1] - b_coords[1], c_coords[0] - b_coords[0]) - \
                  np.arctan2(a_coords[1] - b_coords[1], a_coords[0] - b_coords[0])
        angle = np.abs(radians * 180.0 / np.pi)
        
        if angle > 180.0:
            angle = 360 - angle
            
        return float(angle)

    @classmethod
    def _calculate_joint_angles(cls, landmarks: Any, angles: JointAngles):
        """Calculates internal joint angles (elbows, knees, shoulders, hips)."""
        # Elbows
        angles.left_elbow = cls._create_angle_metric(
            cls.calculate_angle(landmarks[cls.L_SHOULDER], landmarks[cls.L_ELBOW], landmarks[cls.L_WRIST]),
            "left_elbow"
        )
        angles.right_elbow = cls._create_angle_metric(
            cls.calculate_angle(landmarks[cls.R_SHOULDER], landmarks[cls.R_ELBOW], landmarks[cls.R_WRIST]),
            "right_elbow"
        )
        
        # Knees
        angles.left_knee = cls._create_angle_metric(
            cls.calculate_angle(landmarks[cls.L_HIP], landmarks[cls.L_KNEE], landmarks[cls.L_ANKLE]),
            "left_knee"
        )
        angles.right_knee = cls._create_angle_metric(
            cls.calculate_angle(landmarks[cls.R_HIP], landmarks[cls.R_KNEE], landmarks[cls.R_ANKLE]),
            "right_knee"
        )
        
        # Shoulders
        angles.left_shoulder = cls._create_angle_metric(
            cls.calculate_angle(landmarks[cls.L_HIP], landmarks[cls.L_SHOULDER], landmarks[cls.L_ELBOW]),
            "left_shoulder"
        )
        angles.right_shoulder = cls._create_angle_metric(
            cls.calculate_angle(landmarks[cls.R_HIP], landmarks[cls.R_SHOULDER], landmarks[cls.R_ELBOW]),
            "right_shoulder"
        )
        
        # Hips
        angles.left_hip = cls._create_angle_metric(
            cls.calculate_angle(landmarks[cls.L_SHOULDER], landmarks[cls.L_HIP], landmarks[cls.L_KNEE]),
            "left_hip"
        )
        angles.right_hip = cls._create_angle_metric(
            cls.calculate_angle(landmarks[cls.R_SHOULDER], landmarks[cls.R_HIP], landmarks[cls.R_KNEE]),
            "right_hip"
        )

    @classmethod
    def _estimate_body_roll(cls, landmarks: Any, angles: JointAngles):
        """Estimates 2D body roll based on shoulder horizontal displacement."""
        dx = landmarks[cls.R_SHOULDER].x - landmarks[cls.L_SHOULDER].x
        dy = landmarks[cls.R_SHOULDER].y - landmarks[cls.L_SHOULDER].y
        roll = np.abs(np.arctan2(dy, dx) * 180.0 / np.pi)
        if roll > 90:
            roll = 180 - roll
        angles.body_roll = cls._create_angle_metric(float(roll), "body_roll")

    @classmethod
    def _calculate_3d_metrics(cls, landmarks: Any, angles: JointAngles):
        """Calculates 3D spatial metrics (True 3D Body Roll, Core Torsion, and 3D Hand Depths)."""
        try:
            l_sh, r_sh = landmarks[cls.L_SHOULDER], landmarks[cls.R_SHOULDER]
            l_hp, r_hp = landmarks[cls.L_HIP], landmarks[cls.R_HIP]
            l_wr, r_wr = landmarks[cls.L_WRIST], landmarks[cls.R_WRIST]

            # 3D Shoulder vector
            sh_v = np.array([r_sh.x - l_sh.x, r_sh.y - l_sh.y, getattr(r_sh, 'z', 0.0) - getattr(l_sh, 'z', 0.0)])
            # 3D Hip vector
            hp_v = np.array([r_hp.x - l_hp.x, r_hp.y - l_hp.y, getattr(r_hp, 'z', 0.0) - getattr(l_hp, 'z', 0.0)])
            # 3D Spine vector (mid hips to mid shoulders)
            mid_sh = np.array([(l_sh.x + r_sh.x)/2, (l_sh.y + r_sh.y)/2, (getattr(l_sh, 'z', 0.0) + getattr(r_sh, 'z', 0.0))/2])
            mid_hp = np.array([(l_hp.x + r_hp.x)/2, (l_hp.y + r_hp.y)/2, (getattr(l_hp, 'z', 0.0) + getattr(r_hp, 'z', 0.0))/2])
            sp_v = mid_sh - mid_hp

            # Torso Normal Vector = Shoulder x Spine
            torso_normal = np.cross(sh_v, sp_v)
            norm_mag = np.linalg.norm(torso_normal)
            
            if norm_mag > 0:
                torso_normal = torso_normal / norm_mag
                # 3D Roll Angle relative to vertical
                roll_3d = float(np.degrees(np.arctan2(abs(torso_normal[0]), abs(torso_normal[1]))))
            else:
                roll_3d = 0.0
                
            angles.body_roll_3d = ValidatedMetric(
                name="body_roll_3d", value=min(90.0, max(0.0, roll_3d)), unit="deg",
                measurement_domain="pose_relative_3d", status="available", valid=True
            )

            # Core Torsion: 3D angle difference between shoulder line and hip line
            sh_mag = np.linalg.norm(sh_v)
            hp_mag = np.linalg.norm(hp_v)
            if sh_mag > 0 and hp_mag > 0:
                dot_prod = np.clip(np.dot(sh_v, hp_v) / (sh_mag * hp_mag), -1.0, 1.0)
                torsion = float(np.degrees(np.arccos(dot_prod)))
            else:
                torsion = 0.0
            angles.core_torsion_3d = ValidatedMetric(
                name="core_torsion_3d", value=min(90.0, max(0.0, torsion)), unit="deg",
                measurement_domain="pose_relative_3d", status="available", valid=True
            )

            # 3D Hand Depth (Z offset from chest plane midpoint in pose-relative units)
            chest_z = mid_sh[2]
            l_depth = float(getattr(l_wr, 'z', 0.0) - chest_z)
            r_depth = float(getattr(r_wr, 'z', 0.0) - chest_z)
            angles.hand_depth_left_3d = ValidatedMetric(
                name="hand_depth_left_3d", value=l_depth, unit="pose_relative_units",
                measurement_domain="pose_relative_3d", status="available", valid=True
            )
            angles.hand_depth_right_3d = ValidatedMetric(
                name="hand_depth_right_3d", value=r_depth, unit="pose_relative_units",
                measurement_domain="pose_relative_3d", status="available", valid=True
            )

        except Exception as e:
            logger.debug(f"Error calculating 3D metrics: {e}")

    @classmethod
    def calculate_all_angles(cls, landmarks: Any) -> JointAngles:
        """Calculate predefined key joint angles and 3D spatial metrics."""
        angles = JointAngles()
        
        try:
            if len(landmarks) > max(cls.L_ANKLE, cls.R_ANKLE):
                cls._calculate_joint_angles(landmarks, angles)
                cls._estimate_body_roll(landmarks, angles)
                cls._calculate_3d_metrics(landmarks, angles)
        except Exception as e:
            logger.warning(f"Error calculating angles: {e}")
            
        return angles

    @classmethod
    def _calculate_stroke_rate(cls, frames: List[FrameData], effective_fps: float) -> ValidatedMetric:
        catch_count = 0
        prev_phase = None
        for f in frames:
            if f.is_valid:
                curr_phase = f.stroke_phase
                if prev_phase == "Recovery" and curr_phase in ["Entry", "Catch", "Pull"]:
                    catch_count += 1
                if curr_phase != "Unknown":
                    prev_phase = curr_phase
                    
        duration_minutes = (len(frames) / effective_fps) / 60.0 if effective_fps > 0 else 0.0
        if duration_minutes > 0:
            sr = float(catch_count / duration_minutes)
            if sr == 0.0 and catch_count == 0:
                return ValidatedMetric(
                    name="stroke_rate", value=None, unit="spm", measurement_domain="calibrated_physical",
                    status="unavailable", valid=False, is_estimated=False, reason_if_invalid="No complete stroke cycle detected."
                )
            
            valid = 15 <= sr <= 120
            reason = "" if valid else f"Stroke rate {sr:.1f} spm is outside valid range (15-120)."
            is_estimated = catch_count < 3
            if not valid: logger.debug(reason)
            return ValidatedMetric(
                name="stroke_rate", value=sr, unit="spm", measurement_domain="calibrated_physical",
                status="available" if valid else "unavailable", valid=valid, is_estimated=is_estimated, reason_if_invalid=reason
            )
        return ValidatedMetric(name="stroke_rate", value=None, unit="spm", status="unavailable", valid=False)

    @classmethod
    def _calculate_stroke_length(cls, frames: List[FrameData], calibration_engine: Any, frame_width: int, frame_height: int) -> ValidatedMetric:
        if not calibration_engine or frame_width <= 0 or frame_height <= 0:
            return ValidatedMetric(
                name="stroke_length", value=None, unit="unavailable", measurement_domain="unavailable",
                status="unavailable", valid=False, calibration_required=True, calibration_status="missing",
                reason_if_invalid="Physical pool calibration missing"
            )


        stroke_lengths = []
        current_cycle_min_x = 999.0
        current_cycle_max_x = -999.0
        prev_phase = None
        
        class Point:
            def __init__(self, x, y):
                self.x, self.y = x, y
        
        for f in frames:
            if not f.is_valid or not f.raw_landmarks:
                continue
                
            wrist_x = f.raw_landmarks[cls.R_WRIST].x
            current_cycle_min_x = min(current_cycle_min_x, wrist_x)
            current_cycle_max_x = max(current_cycle_max_x, wrist_x)
            
            if f.stroke_phase == "Push" and prev_phase == "Pull":
                if current_cycle_max_x > -999.0 and current_cycle_min_x < 999.0:
                    p1, p2 = Point(current_cycle_min_x, 0.5), Point(current_cycle_max_x, 0.5)
                    dist = calibration_engine.calibrate_distance(p1, p2, frame_width, frame_height, f.raw_landmarks)
                    if dist > 0:
                        stroke_lengths.append(dist)
                current_cycle_min_x, current_cycle_max_x = 999.0, -999.0
                
            if f.stroke_phase != "Unknown":
                prev_phase = f.stroke_phase
                
        sl = 0.0
        is_est = False
        if stroke_lengths:
            sl = float(np.mean(stroke_lengths))
        elif current_cycle_max_x > -999.0 and current_cycle_min_x < 999.0:
            p1, p2 = Point(current_cycle_min_x, 0.5), Point(current_cycle_max_x, 0.5)
            sl = float(calibration_engine.calibrate_distance(p1, p2, frame_width, frame_height, frames[0].raw_landmarks))
            is_est = True
        
        valid = sl > 0 
        is_physical = getattr(calibration_engine, 'is_physical_calibration', False)
        return ValidatedMetric(
            name="stroke_length", value=sl if valid else None, 
            unit=calibration_engine.unit_name,
            measurement_domain=calibration_engine.measurement_domain, 
            status="available" if valid else "unavailable",
            valid=valid, is_estimated=is_est, calibration_required=True, 
            calibration_status="calibrated" if is_physical else "uncalibrated",
            reason_if_invalid="" if valid else "Insufficient tracking to calculate length."
        )

    @classmethod
    def _evaluate_symmetry(cls, frames: List[FrameData]) -> ValidatedMetric:
        l_pull = [f.angles.left_elbow.value for f in frames if f.is_valid and f.stroke_phase == "Pull" and f.angles.left_elbow and f.angles.left_elbow.valid]
        r_pull = [f.angles.right_elbow.value for f in frames if f.is_valid and f.stroke_phase == "Pull" and f.angles.right_elbow and f.angles.right_elbow.valid]
        
        if l_pull and r_pull:
            diff = abs(np.mean(l_pull) - np.mean(r_pull))
            sym = max(0.0, 100.0 - diff)
            return ValidatedMetric(value=sym, valid=True)
        return ValidatedMetric(value=100.0, valid=False, reason_if_invalid="Missing arms data for symmetry comparison.")

    @classmethod
    def _calculate_kick_frequency(cls, frames: List[FrameData], effective_fps: float) -> ValidatedMetric:
        kicks = 0
        is_bending = False
        for f in frames:
            if f.is_valid and f.angles.right_knee and f.angles.right_knee.valid:
                ang = f.angles.right_knee.value
                if ang < 150:
                    is_bending = True
                elif is_bending and ang > 160:
                    kicks += 1
                    is_bending = False
        
        duration_seconds = len(frames) / effective_fps if effective_fps > 0 else 1.0
        kf = float(kicks / duration_seconds)
        valid = 0.2 <= kf <= 8.0 or kf == 0.0
        reason = "" if valid else f"Kick frequency {kf:.1f} Hz is outside valid range (0.2-8.0)."
        if not valid: logger.debug(reason)
        return ValidatedMetric(value=kf, valid=valid, reason_if_invalid=reason)

    @classmethod
    def calculate_global_metrics(cls, frames: List[FrameData], effective_fps: float, calibration_engine: Any = None, frame_width: int = 0, frame_height: int = 0) -> dict:
        """
        Calculate metrics that require the full video timeline.
        Returns a dict of ValidatedMetric for the PerformanceReport.
        """
        metrics = {
            "stroke_rate": ValidatedMetric(),
            "stroke_length": ValidatedMetric(),
            "kick_frequency": ValidatedMetric(),
            "stroke_symmetry": ValidatedMetric(),
            "body_roll_3d": ValidatedMetric(),
            "core_torsion_3d": ValidatedMetric(),
        }
        
        if not frames or effective_fps <= 0:
            return metrics
            
        try:
            metrics["stroke_rate"] = cls._calculate_stroke_rate(frames, effective_fps)
            metrics["stroke_length"] = cls._calculate_stroke_length(frames, calibration_engine, frame_width, frame_height)
            metrics["stroke_symmetry"] = cls._evaluate_symmetry(frames)
            metrics["kick_frequency"] = cls._calculate_kick_frequency(frames, effective_fps)

            # 3D Aggregation
            rolls_3d = [f.angles.body_roll_3d.value for f in frames if f.is_valid and f.angles and f.angles.body_roll_3d and f.angles.body_roll_3d.valid]
            torsions = [f.angles.core_torsion_3d.value for f in frames if f.is_valid and f.angles and f.angles.core_torsion_3d and f.angles.core_torsion_3d.valid]

            if rolls_3d:
                metrics["body_roll_3d"] = ValidatedMetric(value=float(np.mean(rolls_3d)), valid=True)
            if torsions:
                metrics["core_torsion_3d"] = ValidatedMetric(value=float(np.mean(torsions)), valid=True)
        except Exception as e:
            logger.error(f"Error calculating global metrics: {e}")
            
        return metrics
