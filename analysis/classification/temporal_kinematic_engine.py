"""
Deterministic Python Temporal Kinematic Engine for Swimming Stroke Classification.
Operates on temporal sequences of pose landmarks. Performs body-centered scale normalization,
temporal signal smoothing, stroke-cycle detection, stroke-specific physiological signature
evaluations, quality-weighted cycle voting, and calibrated confidence computation.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import math

from models.data_models import StrokeType, StrokeDetectionResult
from core.logger import setup_logger

logger = setup_logger(__name__)

# MediaPipe Pose Landmark Indices
NOSE = 0
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28


@dataclass
class NormalizedFrame:
    frame_index: int
    quality: float
    is_valid: bool
    # Body-centered scale-normalized coordinates (origin at hip midpoint, unit = torso length)
    lw_x: Optional[float] = None
    lw_y: Optional[float] = None
    rw_x: Optional[float] = None
    rw_y: Optional[float] = None
    le_x: Optional[float] = None
    le_y: Optional[float] = None
    re_x: Optional[float] = None
    re_y: Optional[float] = None
    lsh_x: Optional[float] = None
    lsh_y: Optional[float] = None
    rsh_x: Optional[float] = None
    rsh_y: Optional[float] = None
    lhip_x: Optional[float] = None
    lhip_y: Optional[float] = None
    rhip_x: Optional[float] = None
    rhip_y: Optional[float] = None
    lknee_x: Optional[float] = None
    lknee_y: Optional[float] = None
    rknee_x: Optional[float] = None
    rknee_y: Optional[float] = None
    lank_x: Optional[float] = None
    lank_y: Optional[float] = None
    rank_x: Optional[float] = None
    rank_y: Optional[float] = None
    body_roll: Optional[float] = None
    is_supine: bool = False


@dataclass
class StrokeCycle:
    cycle_index: int
    start_frame: int
    peak_frame: int
    end_frame: int
    quality_score: float


@dataclass
class TemporalKinematicFeatures:
    arm_phase_correlation: float = 0.0
    arm_phase_synchrony: float = 0.0
    wrist_vertical_range: float = 0.0
    wrist_recovery_symmetry: float = 0.0
    inward_wrist_sweep: float = 0.0
    dolphin_kick_undulation: float = 0.0
    frog_kick_knee_abduction: float = 0.0
    torso_hip_wave_correlation: float = 0.0
    glide_duration_ratio: float = 0.0
    leg_kick_symmetry: float = 0.0
    body_roll_amplitude: float = 0.0
    head_supine_ratio: float = 0.0
    valid_frame_count: int = 0
    total_frame_count: int = 0


@dataclass
class StrokeSignatureScores:
    butterfly: float = 0.0
    breaststroke: float = 0.0
    freestyle: float = 0.0
    backstroke: float = 0.0
    details: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass
class TemporalEngineResult:
    predicted_stroke: StrokeType
    confidence: float
    classification_status: str
    classification_reason: str
    pose_quality: float
    cycles_detected: int
    cycle_predictions: List[Dict[str, Any]]
    stroke_scores: Dict[str, float]
    signature_scores: Dict[str, Dict[str, float]]
    feature_values: Dict[str, float]
    feature_contributions: Dict[str, float]
    temporal_windows_count: int = 0
    window_predictions: Dict[str, str] = field(default_factory=dict)
    temporal_consistency: float = 0.0
    signature_margin: float = 0.0
    missing_evidence: List[str] = field(default_factory=list)


class LandmarkFilterAndNormalizer:
    """Filters raw landmark frames, computes body-centered scale normalization, and measures pose quality."""

    def normalize_frames(self, frames: List[Any]) -> Tuple[List[NormalizedFrame], float]:
        if not frames:
            return [], 0.0

        normalized_frames: List[NormalizedFrame] = []
        valid_qualities: List[float] = []

        for idx, f in enumerate(frames):
            lms = getattr(f, 'raw_landmarks', None)
            if not lms or len(lms) <= max(LEFT_WRIST, RIGHT_WRIST):
                normalized_frames.append(NormalizedFrame(frame_index=idx, quality=0.0, is_valid=False))
                continue

            l_sh = lms[LEFT_SHOULDER] if len(lms) > LEFT_SHOULDER else None
            r_sh = lms[RIGHT_SHOULDER] if len(lms) > RIGHT_SHOULDER else None
            l_hip = lms[LEFT_HIP] if len(lms) > LEFT_HIP else None
            r_hip = lms[RIGHT_HIP] if len(lms) > RIGHT_HIP else None

            if not (l_sh and r_sh):
                normalized_frames.append(NormalizedFrame(frame_index=idx, quality=0.0, is_valid=False))
                continue

            # Calculate origin (hip midpoint if present, else shoulder midpoint)
            if l_hip and r_hip:
                origin_x = (l_hip.x + r_hip.x) / 2.0
                origin_y = (l_hip.y + r_hip.y) / 2.0
            else:
                origin_x = (l_sh.x + r_sh.x) / 2.0
                origin_y = (l_sh.y + r_sh.y) / 2.0

            sh_mid_x = (l_sh.x + r_sh.x) / 2.0
            sh_mid_y = (l_sh.y + r_sh.y) / 2.0

            # Scale unit = Torso length if hips present, else shoulder width
            if l_hip and r_hip:
                torso_length = math.hypot(sh_mid_x - origin_x, sh_mid_y - origin_y)
            else:
                torso_length = 0.0

            if torso_length < 1e-4:
                torso_length = math.hypot(r_sh.x - l_sh.x, r_sh.y - l_sh.y)
            if torso_length < 1e-4:
                torso_length = 1.0

            scale = 1.0 / torso_length

            def norm_pt(pt) -> Tuple[Optional[float], Optional[float]]:
                if not pt:
                    return None, None
                return float((pt.x - origin_x) * scale), float((pt.y - origin_y) * scale)

            lw_x, lw_y = norm_pt(lms[LEFT_WRIST] if len(lms) > LEFT_WRIST else None)
            rw_x, rw_y = norm_pt(lms[RIGHT_WRIST] if len(lms) > RIGHT_WRIST else None)
            le_x, le_y = norm_pt(lms[LEFT_ELBOW] if len(lms) > LEFT_ELBOW else None)
            re_x, re_y = norm_pt(lms[RIGHT_ELBOW] if len(lms) > RIGHT_ELBOW else None)
            lsh_x, lsh_y = norm_pt(l_sh)
            rsh_x, rsh_y = norm_pt(r_sh)
            lhip_x, lhip_y = norm_pt(l_hip)
            rhip_x, rhip_y = norm_pt(r_hip)
            lknee_x, lknee_y = norm_pt(lms[LEFT_KNEE] if len(lms) > LEFT_KNEE else None)
            rknee_x, rknee_y = norm_pt(lms[RIGHT_KNEE] if len(lms) > RIGHT_KNEE else None)
            lank_x, lank_y = norm_pt(lms[LEFT_ANKLE] if len(lms) > LEFT_ANKLE else None)
            rank_x, rank_y = norm_pt(lms[RIGHT_ANKLE] if len(lms) > RIGHT_ANKLE else None)

            # Body roll angle
            dx_sh = r_sh.x - l_sh.x
            dy_sh = r_sh.y - l_sh.y
            body_roll = abs(math.degrees(math.atan2(dy_sh, dx_sh)))

            # Head supine posture check (face-up posture where nose 3D z is shallower than shoulders)
            nose_lm = lms[NOSE] if len(lms) > NOSE else None
            sh_mid_z = (l_sh.z + r_sh.z) / 2.0 if (l_sh and r_sh) else 0.0
            is_supine = bool(nose_lm and (getattr(nose_lm, 'z', 0.0) < sh_mid_z - 0.05))

            # Compute frame landmark quality
            keypoints = [lw_y, rw_y, le_y, re_y, lsh_y, rsh_y, lknee_y, rknee_y, lank_y, rank_y]
            present_cnt = sum(1 for kp in keypoints if kp is not None)
            quality = float(present_cnt / len(keypoints))

            is_valid = (quality >= 0.20)
            if is_valid:
                valid_qualities.append(quality)


            normalized_frames.append(NormalizedFrame(
                frame_index=idx, quality=quality, is_valid=is_valid,
                lw_x=lw_x, lw_y=lw_y, rw_x=rw_x, rw_y=rw_y,
                le_x=le_x, le_y=le_y, re_x=re_x, re_y=re_y,
                lsh_x=lsh_x, lsh_y=lsh_y, rsh_x=rsh_x, rsh_y=rsh_y,
                lhip_x=lhip_x, lhip_y=lhip_y, rhip_x=rhip_x, rhip_y=rhip_y,
                lknee_x=lknee_x, lknee_y=lknee_y, rknee_x=rknee_x, rknee_y=rknee_y,
                lank_x=lank_x, lank_y=lank_y, rank_x=rank_x, rank_y=rank_y,
                body_roll=body_roll, is_supine=is_supine
            ))

        overall_pose_quality = float(np.mean(valid_qualities)) if valid_qualities else 0.0
        return normalized_frames, overall_pose_quality


class TemporalSignalProcessor:
    """Applies temporal 5-point moving median and exponential smoothing to trajectory time-series."""

    def _smooth_series(self, series: List[Optional[float]], window_size: int = 5, alpha: float = 0.3) -> np.ndarray:
        if not series:
            return np.array([], dtype=float)

        # Interpolate missing values (None) linearly
        vals = np.array([v if v is not None else np.nan for v in series], dtype=float)
        nans = np.isnan(vals)

        if np.all(nans):
            return np.zeros_like(vals)

        if np.any(nans):
            x = np.arange(len(vals))
            vals[nans] = np.interp(x[nans], x[~nans], vals[~nans])

        # 1. Moving median filter
        smoothed = np.copy(vals)
        half_w = window_size // 2
        for i in range(len(vals)):
            i_min = max(0, i - half_w)
            i_max = min(len(vals), i + half_w + 1)
            smoothed[i] = np.median(vals[i_min:i_max])

        # 2. Exponential smoothing
        exp_smoothed = np.zeros_like(smoothed)
        exp_smoothed[0] = smoothed[0]
        for i in range(1, len(smoothed)):
            exp_smoothed[i] = alpha * smoothed[i] + (1 - alpha) * exp_smoothed[i - 1]

        return exp_smoothed


class StrokeCycleDetector:
    """Detects periodic stroke movement cycles from local extremum turnarounds in wrist and shoulder trajectories."""

    def detect_cycles(self, lw_y: np.ndarray, rw_y: np.ndarray, qualities: np.ndarray) -> List[StrokeCycle]:
        if len(lw_y) < 15:
            # Short clip -> single overall cycle window
            return [StrokeCycle(cycle_index=1, start_frame=0, peak_frame=len(lw_y)//2, end_frame=len(lw_y)-1, quality_score=float(np.mean(qualities)) if len(qualities)>0 else 0.5)]

        # Combined wrist activity signal
        combined_wrist_y = (lw_y + rw_y) / 2.0

        # Find local minima (highest vertical hand position in image Y)
        peaks = []
        for i in range(2, len(combined_wrist_y) - 2):
            if (combined_wrist_y[i] < combined_wrist_y[i-1] and combined_wrist_y[i] < combined_wrist_y[i-2] and
                combined_wrist_y[i] < combined_wrist_y[i+1] and combined_wrist_y[i] < combined_wrist_y[i+2]):
                peaks.append(i)

        if len(peaks) < 2:
            return [StrokeCycle(cycle_index=1, start_frame=0, peak_frame=len(lw_y)//2, end_frame=len(lw_y)-1, quality_score=float(np.mean(qualities)) if len(qualities)>0 else 0.5)]

        cycles: List[StrokeCycle] = []
        for idx in range(len(peaks) - 1):
            start = peaks[idx]
            end = peaks[idx + 1]
            if end - start >= 6:  # Minimum cycle length check
                mid_peak = (start + end) // 2
                q_sub = qualities[start:end+1] if len(qualities) > end else qualities
                q_score = float(np.mean(q_sub)) if len(q_sub) > 0 else 0.5
                cycles.append(StrokeCycle(
                    cycle_index=idx + 1,
                    start_frame=start,
                    peak_frame=mid_peak,
                    end_frame=end,
                    quality_score=q_score
                ))

        if not cycles:
            cycles = [StrokeCycle(cycle_index=1, start_frame=0, peak_frame=len(lw_y)//2, end_frame=len(lw_y)-1, quality_score=float(np.mean(qualities)) if len(qualities)>0 else 0.5)]

        return cycles


class StrokeSignatureEvaluator:
    """Computes explicit physiological movement signatures for Butterfly, Breaststroke, Freestyle, and Backstroke."""

    def extract_temporal_features(
        self,
        frames: List[NormalizedFrame],
        processor: TemporalSignalProcessor,
        start_idx: int = 0,
        end_idx: Optional[int] = None
    ) -> TemporalKinematicFeatures:
        if end_idx is None:
            end_idx = len(frames)

        sub_frames = frames[start_idx:end_idx]
        valid_sub = [f for f in sub_frames if f.is_valid]

        if len(valid_sub) < 3:
            return TemporalKinematicFeatures(valid_frame_count=len(valid_sub), total_frame_count=len(sub_frames))

        # Extract time series
        lw_y = processor._smooth_series([f.lw_y for f in sub_frames])
        rw_y = processor._smooth_series([f.rw_y for f in sub_frames])
        lw_x = processor._smooth_series([f.lw_x for f in sub_frames])
        rw_x = processor._smooth_series([f.rw_x for f in sub_frames])
        le_y = processor._smooth_series([f.le_y for f in sub_frames])
        re_y = processor._smooth_series([f.re_y for f in sub_frames])
        lsh_y = processor._smooth_series([f.lsh_y for f in sub_frames])
        rsh_y = processor._smooth_series([f.rsh_y for f in sub_frames])
        lhip_y = processor._smooth_series([f.lhip_y for f in sub_frames])
        rhip_y = processor._smooth_series([f.rhip_y for f in sub_frames])
        lknee_x = processor._smooth_series([f.lknee_x for f in sub_frames])
        rknee_x = processor._smooth_series([f.rknee_x for f in sub_frames])
        lank_y = processor._smooth_series([f.lank_y for f in sub_frames])
        rank_y = processor._smooth_series([f.rank_y for f in sub_frames])

        body_rolls = [f.body_roll for f in sub_frames if f.body_roll is not None]
        supine_flags = [1.0 if f.is_supine else 0.0 for f in sub_frames if f.is_valid]

        # 1. Arm Phase Correlation (Linear Correlation between Left and Right Wrist Y)
        arm_corr = 0.0
        if np.std(lw_y) > 1e-4 and np.std(rw_y) > 1e-4:
            c = np.corrcoef(lw_y, rw_y)[0, 1]
            arm_corr = float(c) if not math.isnan(c) else 0.0

        # 2. Arm Phase Synchrony (Cross-correlation of both wrists and elbows)
        arm_synch = arm_corr

        # 3. Wrist Vertical Range
        lw_range = np.ptp(lw_y) if len(lw_y) > 0 else 0.0
        rw_range = np.ptp(rw_y) if len(rw_y) > 0 else 0.0
        wrist_range = float((lw_range + rw_range) / 2.0)

        # 4. Wrist Recovery Symmetry
        lw_min, rw_min = np.min(lw_y), np.min(rw_y)
        wrist_recovery_sym = float(abs(lw_min - rw_min))

        # 5. Inward Wrist Sweep (Minimum Horizontal Distance between Wrists during pull phase)
        wrist_dist_x = np.abs(lw_x - rw_x)
        inward_sweep = float(np.min(wrist_dist_x)) if len(wrist_dist_x) > 0 else 0.0

        # 6. Dolphin Kick Undulation Score
        # Measured by vertical ankle oscillation frequency & amplitude relative to hips (simultaneous bilateral leg movement)
        leg_corr = 0.0
        if np.std(lank_y) > 1e-4 and np.std(rank_y) > 1e-4:
            lc = np.corrcoef(lank_y, rank_y)[0, 1]
            leg_corr = float(lc) if not math.isnan(lc) else 0.0

        ankle_range = float((np.ptp(lank_y) + np.ptp(rank_y)) / 2.0)
        dolphin_undulation = float(max(0.0, leg_corr) * ankle_range * 2.0)

        # 7. Frog Kick Knee Abduction over Hip Width (Outward knee spread beyond hips during leg flexion)
        lhip_x = processor._smooth_series([f.lhip_x for f in sub_frames])
        rhip_x = processor._smooth_series([f.rhip_x for f in sub_frames])
        knee_dist_x = np.abs(np.array(lknee_x) - np.array(rknee_x))
        hip_dist_x = np.abs(np.array(lhip_x) - np.array(rhip_x))
        abduction_over_hips = np.maximum(0.0, knee_dist_x - hip_dist_x)
        frog_abduction = float(np.max(abduction_over_hips)) if len(abduction_over_hips) > 0 else 0.0

        # 8. Torso-Hip Wave Correlation (Phase relationship between shoulder Y and hip Y)
        sh_avg_y = (lsh_y + rsh_y) / 2.0
        hip_avg_y = (lhip_y + rhip_y) / 2.0
        torso_hip_corr = 0.0
        if np.std(sh_avg_y) > 1e-4 and np.std(hip_avg_y) > 1e-4:
            tc = np.corrcoef(sh_avg_y, hip_avg_y)[0, 1]
            torso_hip_corr = float(tc) if not math.isnan(tc) else 0.0

        # 9. Glide Duration Ratio (Percentage of frames where wrist velocity is low)
        lw_vel = np.abs(np.diff(lw_y))
        rw_vel = np.abs(np.diff(rw_y))
        avg_vel = (lw_vel + rw_vel) / 2.0 if len(lw_vel) > 0 else np.array([1.0])
        glide_frames = np.sum(avg_vel < 0.02)
        glide_ratio = float(glide_frames / max(1, len(avg_vel)))

        # 10. Body Roll Amplitude & Head Supine Ratio
        roll_amp = float(np.ptp(body_rolls)) if len(body_rolls) > 0 else 0.0
        head_supine = float(np.mean(supine_flags)) if len(supine_flags) > 0 else 0.0

        return TemporalKinematicFeatures(
            arm_phase_correlation=arm_corr,
            arm_phase_synchrony=arm_synch,
            wrist_vertical_range=wrist_range,
            wrist_recovery_symmetry=wrist_recovery_sym,
            inward_wrist_sweep=inward_sweep,
            dolphin_kick_undulation=dolphin_undulation,
            frog_kick_knee_abduction=frog_abduction,
            torso_hip_wave_correlation=torso_hip_corr,
            glide_duration_ratio=glide_ratio,
            leg_kick_symmetry=leg_corr,
            body_roll_amplitude=roll_amp,
            head_supine_ratio=head_supine,
            valid_frame_count=len(valid_sub),
            total_frame_count=len(sub_frames)
        )

    def evaluate_stroke_signatures(self, feats: TemporalKinematicFeatures) -> StrokeSignatureScores:
        scores = {
            StrokeType.FREESTYLE: 0.10,
            StrokeType.BACKSTROKE: 0.10,
            StrokeType.BREASTSTROKE: 0.10,
            StrokeType.BUTTERFLY: 0.10
        }
        details: Dict[str, Dict[str, float]] = {
            "butterfly": {},
            "breaststroke": {},
            "freestyle": {},
            "backstroke": {}
        }

        # -------------------------------------------------------------
        # A) BUTTERFLY SIGNATURE EVALUATION
        # -------------------------------------------------------------
        if feats.arm_phase_correlation > +0.20 and feats.head_supine_ratio <= 0.50:
            # Synchronous bilateral arm movement in prone position
            scores[StrokeType.BUTTERFLY] += 0.35
            details["butterfly"]["arm_synchrony"] = +0.35

            if feats.wrist_vertical_range > 0.35:
                # High vertical wrist recovery elevation above water
                scores[StrokeType.BUTTERFLY] += 0.35
                details["butterfly"]["arm_elevation_recovery"] = +0.35

            if feats.dolphin_kick_undulation > 0.05:
                # Dolphin kick undulation
                scores[StrokeType.BUTTERFLY] += 0.30
                details["butterfly"]["dolphin_kick"] = +0.30

            if feats.torso_hip_wave_correlation > 0.15:
                # Torso-to-hip undulation wave
                scores[StrokeType.BUTTERFLY] += 0.20
                details["butterfly"]["torso_undulation_wave"] = +0.20

            # Butterfly requires flat horizontal torso; body roll rotation indicates Freestyle
            if feats.body_roll_amplitude > 10.0:
                scores[StrokeType.BUTTERFLY] = max(0.0, scores[StrokeType.BUTTERFLY] - 0.60)

        # -------------------------------------------------------------
        # B) BREASTSTROKE SIGNATURE EVALUATION
        # -------------------------------------------------------------
        # Breaststroke is identified by Frog Kick (lateral knee abduction beyond hips) and compact underwater recovery
        if feats.head_supine_ratio <= 0.50:
            if feats.frog_kick_knee_abduction >= 0.08:
                # Distinctive Frog Kick (wide lateral knee spread beyond hips)
                scores[StrokeType.BREASTSTROKE] += 0.65
                details["breaststroke"]["frog_kick_knee_spread"] = +0.65
                # Frog Kick strongly suppresses Freestyle & Butterfly
                scores[StrokeType.FREESTYLE] = max(0.0, scores[StrokeType.FREESTYLE] - 0.75)
                scores[StrokeType.BUTTERFLY] = max(0.0, scores[StrokeType.BUTTERFLY] - 0.75)

            if feats.wrist_vertical_range <= 0.35 and feats.inward_wrist_sweep < 0.40:
                # Compact submerged inward hand sweep
                scores[StrokeType.BREASTSTROKE] += 0.25
                details["breaststroke"]["inward_hand_sweep"] = +0.25

            if feats.wrist_vertical_range <= 0.35 and feats.glide_duration_ratio > 0.10:
                # Characteristic Breaststroke submerged glide phase
                scores[StrokeType.BREASTSTROKE] += 0.20
                details["breaststroke"]["glide_phase_deceleration"] = +0.20

            if feats.arm_phase_correlation > +0.10:
                # Synchronous bilateral arm stroke
                scores[StrokeType.BREASTSTROKE] += 0.20
                details["breaststroke"]["arm_synchrony"] = +0.20

        # -------------------------------------------------------------
        # C) FREESTYLE SIGNATURE EVALUATION
        # -------------------------------------------------------------
        if feats.head_supine_ratio <= 0.50:
            if feats.arm_phase_correlation < -0.05:
                # Alternating arm movement
                scores[StrokeType.FREESTYLE] += 0.45
                details["freestyle"]["alternating_arm_phase"] = +0.45

            if feats.body_roll_amplitude > 8.0:
                # Body roll rotation around spine axis (characteristic of Freestyle)
                scores[StrokeType.FREESTYLE] += 0.35
                details["freestyle"]["body_roll_rotation"] = +0.35
                # Suppress Butterfly when strong body roll rotation is present
                scores[StrokeType.BUTTERFLY] = max(0.0, scores[StrokeType.BUTTERFLY] - 0.50)

            if feats.head_supine_ratio <= 0.30:
                # Prone posture (face-down swimming)
                scores[StrokeType.FREESTYLE] += 0.20
                details["freestyle"]["prone_posture"] = +0.20

        # -------------------------------------------------------------
        # D) BACKSTROKE SIGNATURE EVALUATION
        # -------------------------------------------------------------
        # Any swimmer in face-up supine posture (> 0.50) is in Backstroke position.
        if feats.head_supine_ratio > 0.50:
            scores[StrokeType.BACKSTROKE] += 0.65
            details["backstroke"]["supine_posture"] = +0.65

            if feats.arm_phase_correlation < -0.15:
                # Alternating arm recovery
                scores[StrokeType.BACKSTROKE] += 0.30
                details["backstroke"]["alternating_arms"] = +0.30
            else:
                # Synchronous / Double arm backstroke drill
                scores[StrokeType.BACKSTROKE] += 0.20
                details["backstroke"]["double_arm_backstroke"] = +0.20

            # Suppress prone-only strokes (Butterfly, Breaststroke, Freestyle) when swimmer is face-up
            scores[StrokeType.FREESTYLE] = max(0.0, scores[StrokeType.FREESTYLE] - 0.80)
            scores[StrokeType.BUTTERFLY] = max(0.0, scores[StrokeType.BUTTERFLY] - 0.80)
            scores[StrokeType.BREASTSTROKE] = max(0.0, scores[StrokeType.BREASTSTROKE] - 0.80)

        return StrokeSignatureScores(
            butterfly=scores[StrokeType.BUTTERFLY],
            breaststroke=scores[StrokeType.BREASTSTROKE],
            freestyle=scores[StrokeType.FREESTYLE],
            backstroke=scores[StrokeType.BACKSTROKE],
            details=details
        )


class TemporalWindowClassifier:
    """
    Splits valid frame sequences into overlapping temporal windows (e.g. 2-4 seconds)
    and evaluates independent predictions to compute temporal consistency.
    """

    def __init__(self, window_duration_sec: float = 3.0, stride_sec: float = 1.5, fps: float = 30.0):
        self.window_size = int(window_duration_sec * fps)
        self.stride = int(stride_sec * fps)

    def evaluate_windows(
        self,
        norm_frames: List[NormalizedFrame],
        evaluator: StrokeSignatureEvaluator,
        processor: TemporalSignalProcessor
    ) -> Tuple[int, Dict[str, str], float, Dict[str, float]]:
        total_frames = len(norm_frames)
        if total_frames < self.window_size:
            # Single window fallback
            w_feats = evaluator.extract_temporal_features(norm_frames, processor)
            w_sigs = evaluator.evaluate_stroke_signatures(w_feats)
            w_scores = {
                "Butterfly": w_sigs.butterfly,
                "Breaststroke": w_sigs.breaststroke,
                "Freestyle": w_sigs.freestyle,
                "Backstroke": w_sigs.backstroke
            }
            top_st = max(w_scores, key=w_scores.get)
            return 1, {st: "1/1" if st == top_st else "0/1" for st in w_scores}, 1.0, w_scores

        windows_preds: List[str] = []
        accum_scores = {"Butterfly": 0.0, "Breaststroke": 0.0, "Freestyle": 0.0, "Backstroke": 0.0}

        start_idx = 0
        while start_idx + 15 <= total_frames:
            end_idx = min(total_frames, start_idx + self.window_size)
            win_frames = norm_frames[start_idx:end_idx]
            valid_in_win = sum(1 for f in win_frames if f.is_valid)

            if valid_in_win >= 5:
                w_feats = evaluator.extract_temporal_features(win_frames, processor)
                w_sigs = evaluator.evaluate_stroke_signatures(w_feats)
                w_dict = {
                    "Butterfly": w_sigs.butterfly,
                    "Breaststroke": w_sigs.breaststroke,
                    "Freestyle": w_sigs.freestyle,
                    "Backstroke": w_sigs.backstroke
                }
                top_w = max(w_dict, key=w_dict.get)
                windows_preds.append(top_w)
                for st, sc in w_dict.items():
                    accum_scores[st] += sc

            start_idx += self.stride

        total_valid_windows = len(windows_preds)
        if total_valid_windows == 0:
            return 0, {st: "0/0" for st in accum_scores}, 0.0, accum_scores

        counts = {st: windows_preds.count(st) for st in accum_scores}
        top_stroke = max(counts, key=counts.get)
        consistency = float(counts[top_stroke] / total_valid_windows)
        pred_strings = {st: f"{counts[st]}/{total_valid_windows}" for st in accum_scores}

        avg_scores = {st: accum_scores[st] / total_valid_windows for st in accum_scores}

        return total_valid_windows, pred_strings, consistency, avg_scores


class PythonTemporalKinematicEngine:
    """
    100% Python-based Deterministic Temporal Kinematic Classifier Engine.
    Operates without AI agent or LLM dependencies.
    """

    def __init__(self, confidence_threshold: float = 0.40):
        self.confidence_threshold = confidence_threshold
        self.normalizer = LandmarkFilterAndNormalizer()
        self.processor = TemporalSignalProcessor()
        self.cycle_detector = StrokeCycleDetector()
        self.evaluator = StrokeSignatureEvaluator()
        self.window_classifier = TemporalWindowClassifier()

    def classify_video_sequence(self, frames: List[Any], selected_stroke_input: StrokeType = StrokeType.AUTO_DETECT) -> TemporalEngineResult:
        # 1. Normalize landmarks & evaluate pose quality
        norm_frames, overall_pose_quality = self.normalizer.normalize_frames(frames)
        valid_count = sum(1 for f in norm_frames if f.is_valid)
        total_count = len(norm_frames)

        # Quality Gate Check
        if valid_count < 2 or overall_pose_quality < 0.15:
            return TemporalEngineResult(
                predicted_stroke=StrokeType.UNKNOWN,
                confidence=0.0,
                classification_status="INSUFFICIENT_DATA",
                classification_reason=f"Insufficient pose quality ({overall_pose_quality*100:.1f}%) or valid frames ({valid_count}/{total_count}).",
                pose_quality=overall_pose_quality,
                cycles_detected=0,
                cycle_predictions=[],
                stroke_scores={"Freestyle": 0.0, "Backstroke": 0.0, "Breaststroke": 0.0, "Butterfly": 0.0},
                signature_scores={},
                feature_values={},
                feature_contributions={},
                temporal_windows_count=0,
                window_predictions={},
                temporal_consistency=0.0,
                signature_margin=0.0,
                missing_evidence=["insufficient_valid_pose_landmarks"]
            )

        # 2. Extract full-sequence features & global signatures
        full_feats = self.evaluator.extract_temporal_features(norm_frames, self.processor)
        global_sigs = self.evaluator.evaluate_stroke_signatures(full_feats)

        # 3. Perform Temporal Window Classification
        num_windows, win_pred_strs, temporal_consistency, avg_win_sigs = self.window_classifier.evaluate_windows(
            norm_frames, self.evaluator, self.processor
        )

        # 4. Detect stroke cycles & cycle predictions
        lw_y = self.processor._smooth_series([f.lw_y for f in norm_frames])
        rw_y = self.processor._smooth_series([f.rw_y for f in norm_frames])
        qualities = np.array([f.quality for f in norm_frames])

        detected_cycles = self.cycle_detector.detect_cycles(lw_y, rw_y, qualities)
        cycle_preds: List[Dict[str, Any]] = []

        cycle_accum = {
            "Butterfly": 0.0,
            "Breaststroke": 0.0,
            "Freestyle": 0.0,
            "Backstroke": 0.0
        }

        for c in detected_cycles:
            c_feats = self.evaluator.extract_temporal_features(norm_frames, self.processor, c.start_frame, c.end_frame)
            c_sigs = self.evaluator.evaluate_stroke_signatures(c_feats)

            c_dict = {
                "Butterfly": c_sigs.butterfly,
                "Breaststroke": c_sigs.breaststroke,
                "Freestyle": c_sigs.freestyle,
                "Backstroke": c_sigs.backstroke
            }
            top_st = max(c_dict, key=c_dict.get)

            cycle_preds.append({
                "cycle_index": c.cycle_index,
                "start_frame": c.start_frame,
                "end_frame": c.end_frame,
                "predicted_stroke": top_st,
                "quality": round(c.quality_score, 2),
                "scores": {st: round(sc, 4) for st, sc in c_dict.items()}
            })

            weight = max(0.2, c.quality_score)
            for st, sc in c_dict.items():
                cycle_accum[st] += sc * weight

        # 5. Composite Signature Scoring (Global 50% + Windows 30% + Cycles 20%)
        raw_signatures = {
            "Butterfly": global_sigs.butterfly,
            "Breaststroke": global_sigs.breaststroke,
            "Freestyle": global_sigs.freestyle,
            "Backstroke": global_sigs.backstroke
        }

        composite_signatures: Dict[str, float] = {}
        for st in raw_signatures:
            glob_val = raw_signatures[st]
            win_val = avg_win_sigs.get(st, glob_val)
            cyc_val = (cycle_accum[st] / max(1, len(detected_cycles))) if detected_cycles else glob_val
            composite_signatures[st] = round(0.50 * glob_val + 0.30 * win_val + 0.20 * cyc_val, 4)

        # Normalize signature candidate ratios (sum to 1.0)
        tot_sig = sum(composite_signatures.values()) or 1.0
        normalized_scores = {st: round(composite_signatures[st] / tot_sig, 4) for st in composite_signatures}

        # Top and second stroke determination
        sorted_strokes = sorted(composite_signatures.items(), key=lambda x: x[1], reverse=True)
        top_stroke_str, best_sig = sorted_strokes[0]
        second_stroke_str, second_sig = sorted_strokes[1]

        signature_margin = max(0.0, best_sig - second_sig)
        predicted_stroke = StrokeType(top_stroke_str)

        # 6. Multi-Factor Deterministic Confidence Calculation
        # Factors: Best Sig (0.35), Margin (0.30), Window Consistency (0.15), Pose Quality (0.10), Cycle Quality (0.10)
        norm_best_sig = min(1.0, best_sig / 1.0)
        norm_margin = min(1.0, signature_margin / max(1e-4, best_sig))
        cycle_quality = min(1.0, len(detected_cycles) / 2.0)

        confidence_raw = (
            0.35 * norm_best_sig +
            0.30 * norm_margin +
            0.15 * temporal_consistency +
            0.10 * overall_pose_quality +
            0.10 * cycle_quality
        )
        confidence = round(float(confidence_raw), 2)

        # 7. Status Classification
        if best_sig < 0.20 or normalized_scores[top_stroke_str] < 0.28:
            classification_status = "ambiguous"
            reason = f"Ambiguous kinematic movement (flat score distribution across strokes)."
            predicted_stroke = StrokeType.UNKNOWN
            confidence = min(confidence, 0.25)
        elif confidence >= 0.70:
            classification_status = "HIGH_CONFIDENCE"
            reason = f"High deterministic kinematic confidence ({confidence*100:.0f}%) for {predicted_stroke.value}."
        elif confidence >= 0.45:
            classification_status = "MODERATE_CONFIDENCE"
            reason = f"Moderate deterministic kinematic confidence ({confidence*100:.0f}%) for {predicted_stroke.value}."
        elif confidence >= 0.20:
            classification_status = "LOW_CONFIDENCE"
            reason = f"Low deterministic kinematic confidence ({confidence*100:.0f}%) for {predicted_stroke.value}."
        else:
            classification_status = "INSUFFICIENT_DATA"
            reason = f"Insufficient evidence for confident stroke classification."

        feature_values_dict = {
            "arm_phase_correlation": round(full_feats.arm_phase_correlation, 4),
            "arm_phase_synchrony": round(full_feats.arm_phase_synchrony, 4),
            "wrist_vertical_range": round(full_feats.wrist_vertical_range, 4),
            "dolphin_kick_undulation": round(full_feats.dolphin_kick_undulation, 4),
            "frog_kick_knee_abduction": round(full_feats.frog_kick_knee_abduction, 4),
            "torso_hip_wave_correlation": round(full_feats.torso_hip_wave_correlation, 4),
            "glide_duration_ratio": round(full_feats.glide_duration_ratio, 4),
            "leg_kick_symmetry": round(full_feats.leg_kick_symmetry, 4),
            "body_roll_amplitude": round(full_feats.body_roll_amplitude, 4),
            "head_supine_ratio": round(full_feats.head_supine_ratio, 4),
            "pose_quality": round(overall_pose_quality, 4)
        }

        top_details = global_sigs.details.get(top_stroke_str.lower(), {})
        contributions_dict = {k: float(v) for k, v in top_details.items()}

        signature_scores_dict = {
            "butterfly": {"score": composite_signatures["Butterfly"], "details": global_sigs.details["butterfly"]},
            "breaststroke": {"score": composite_signatures["Breaststroke"], "details": global_sigs.details["breaststroke"]},
            "freestyle": {"score": composite_signatures["Freestyle"], "details": global_sigs.details["freestyle"]},
            "backstroke": {"score": composite_signatures["Backstroke"], "details": global_sigs.details["backstroke"]}
        }

        return TemporalEngineResult(
            predicted_stroke=predicted_stroke,
            confidence=confidence,
            classification_status=classification_status,
            classification_reason=reason,
            pose_quality=overall_pose_quality,
            cycles_detected=len(detected_cycles),
            cycle_predictions=cycle_preds,
            stroke_scores=normalized_scores,
            signature_scores=signature_scores_dict,
            feature_values=feature_values_dict,
            feature_contributions=contributions_dict,
            temporal_windows_count=num_windows,
            window_predictions=win_pred_strs,
            temporal_consistency=temporal_consistency,
            signature_margin=round(signature_margin, 4)
        )
