"""
Weighted scoring engine for evaluating swimming performance.
"""
import yaml
import numpy as np
from core.config import config
from core.constants import (
    MAX_SCORE, DEFAULT_PENALTY_SCORE, PULL_ELBOW_MIN_ANGLE, PULL_ELBOW_MAX_ANGLE,
    RECOVERY_SHOULDER_MIN_ANGLE, RECOVERY_SHOULDER_MAX_ANGLE,
    KNEE_BEND_MIN_ANGLE, KNEE_BEND_MAX_ANGLE, SYMMETRY_SCORE_PENALTY_THRESHOLD,
    SCORE_THRESHOLD_EXCELLENT, SCORE_THRESHOLD_GOOD, SCORE_THRESHOLD_FAIR,
    RELIABILITY_MIN_ACCEPTABLE_SCORE
)
from models.data_models import AnalysisResult, MovementError, PerformanceReport
from core.logger import setup_logger
from analysis.strategies.base_strategy import BaseScoringEngine

logger = setup_logger(__name__)

class FreestyleScoringEngine(BaseScoringEngine):
    """
    Evaluates biomechanical data using a configurable weighted scoring model.
    """
    
    def __init__(self):
        self.weights = self._load_weights()
        
    def _load_weights(self) -> dict:
        try:
            with open(config.app_config_path, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('scoring', {})
        except Exception as e:
            logger.error(f"Could not load scoring weights: {e}")
            return {}

    def generate_report(self, analysis_result: AnalysisResult, global_metrics: dict) -> PerformanceReport:
        """
        Generates the performance report and calculates the final score based on weights.
        """
        report = PerformanceReport()
        report.stroke_rate = global_metrics.get("stroke_rate")
        report.stroke_length = global_metrics.get("stroke_length")
        report.kick_frequency = global_metrics.get("kick_frequency")
        report.stroke_symmetry = global_metrics.get("stroke_symmetry")
        
        errors = []
        score_components = []
        
        # Helper to get score out of 100
        def calculate_component_score(value_list, ideal_min, ideal_max, error_name, error_desc):
            if not value_list:
                return 0, None
            avg_val = np.mean(value_list)
            if ideal_min <= avg_val <= ideal_max:
                return MAX_SCORE, None
            else:
                err = MovementError(-1, 0, error_name, f"{error_desc} (Measured: {avg_val:.1f})", "Medium")
                return DEFAULT_PENALTY_SCORE, err

        # 1. Stroke Symmetry
        sym_weight = self.weights.get("symmetry_weight", 0.20)
        sym_score = None
        if report.stroke_symmetry and report.stroke_symmetry.valid and report.stroke_symmetry.value is not None:
            sym_score = report.stroke_symmetry.value
            score_components.append(sym_score * sym_weight)
            if sym_score < SYMMETRY_SCORE_PENALTY_THRESHOLD:
                errors.append(MovementError(-1, 0, "Asymmetrical Pull", "Left and right arms have significantly different mechanics.", "High", confidence=report.stroke_symmetry.confidence))
        else:
            # P0-7: Do NOT default to MAX_SCORE. Skip this component and note unavailability.
            logger.debug("Symmetry metric unavailable; component omitted from scoring.")


        # 2. Elbow Angle during Pull
        elb_weight = self.weights.get("elbow_weight", 0.25)
        pull_elbows = []
        for f in analysis_result.frames:
            if f.is_valid and f.stroke_phase == "Pull":
                if f.angles.left_elbow and f.angles.left_elbow.valid: pull_elbows.append((f.angles.left_elbow.value, f.timestamp_ms))
                if f.angles.right_elbow and f.angles.right_elbow.valid: pull_elbows.append((f.angles.right_elbow.value, f.timestamp_ms))
        
        vals = [v[0] for v in pull_elbows]
        ts = pull_elbows[0][1] if pull_elbows else 0
        # Optimal high-elbow catch / mid-pull flexion is 90° to 120° (Maglischo, 2003)
        elb_score, elb_err = calculate_component_score(vals, PULL_ELBOW_MIN_ANGLE, PULL_ELBOW_MAX_ANGLE, "Dropped Elbow", "Average elbow angle during pull is outside optimal range (90°-120°).")
        score_components.append(elb_score * elb_weight)
        if elb_err: 
            elb_err.timestamp_ms = ts
            errors.append(elb_err)
        
        # 3. Shoulder Angle (Recovery/Reach)
        shoulder_weight = self.weights.get("shoulder_weight", 0.20)
        reach_shoulders = []
        for f in analysis_result.frames:
            if f.is_valid and f.stroke_phase == "Recovery":
                if f.angles.left_shoulder and f.angles.left_shoulder.valid: reach_shoulders.append((f.angles.left_shoulder.value, f.timestamp_ms))
                if f.angles.right_shoulder and f.angles.right_shoulder.valid: reach_shoulders.append((f.angles.right_shoulder.value, f.timestamp_ms))
                
        vals = [v[0] for v in reach_shoulders]
        ts = reach_shoulders[0][1] if reach_shoulders else 0
        sh_score, sh_err = calculate_component_score(vals, RECOVERY_SHOULDER_MIN_ANGLE, RECOVERY_SHOULDER_MAX_ANGLE, "Limited Shoulder Extension", "Shoulder extension during recovery is restricted.")
        score_components.append(sh_score * shoulder_weight)
        if sh_err: 
            sh_err.timestamp_ms = ts
            errors.append(sh_err)
        
        # 4. Hip Angle
        # P0-7: Hip angle not yet calculated; do NOT inject MAX_SCORE as a placeholder.
        # This component is explicitly omitted until hip angle is added to JointAngles.
        logger.debug("Hip angle not yet available; component omitted from scoring (P0-7).")
        
        # 5. Knee Angle
        knee_weight = self.weights.get("knee_weight", 0.15)
        knees = []
        for f in analysis_result.frames:
            if f.is_valid:
                if f.angles.left_knee and f.angles.left_knee.valid: knees.append((f.angles.left_knee.value, f.timestamp_ms))
                if f.angles.right_knee and f.angles.right_knee.valid: knees.append((f.angles.right_knee.value, f.timestamp_ms))
        
        vals = [v[0] for v in knees]
        ts = knees[0][1] if knees else 0
        kn_score, kn_err = calculate_component_score(vals, KNEE_BEND_MIN_ANGLE, KNEE_BEND_MAX_ANGLE, "Excessive Knee Bend", "Knees are bending too much during kicking.")
        score_components.append(kn_score * knee_weight)
        if kn_err: 
            kn_err.timestamp_ms = ts
            errors.append(kn_err)

        # P0-8: Downstream propagation — score is only valid when upstream dependencies are met
        cycles = analysis_result.stroke_statistics.completed_cycles if analysis_result.stroke_statistics else 0
        reliability_score = analysis_result.reliability.analysis_reliability_score if analysis_result.reliability else 0.0

        if cycles == 0:
            # P0-7: No complete stroke cycle → no valid score
            report.overall_score = None
            report.feedback_summary = "INSUFFICIENT_EVIDENCE: No complete stroke cycle detected. Scoring requires at least one full cycle."
            report.errors = errors
            return report

        if reliability_score < RELIABILITY_MIN_ACCEPTABLE_SCORE:
            # P0-7: Reliability too low → no valid score
            report.overall_score = None
            report.feedback_summary = f"INSUFFICIENT_EVIDENCE: Reliability score {reliability_score:.0f} below minimum threshold ({RELIABILITY_MIN_ACCEPTABLE_SCORE}). Biomechanical data is insufficient for scoring."
            report.errors = errors
            return report

        if not score_components:
            report.overall_score = None
            report.feedback_summary = "METRIC_UNAVAILABLE: No scoreable metrics available. Ensure pose detection is working correctly."
            report.errors = errors
            return report

        raw_score = sum(score_components)
        # Normalize to available components (not total weight which may have missing items)
        report.overall_score = max(0.0, min(MAX_SCORE, raw_score))
        report.errors = errors
        report.feedback_summary = self._generate_feedback_summary(report.overall_score, len(errors))
        
        return report

    def _generate_feedback_summary(self, score: float, error_count: int) -> str:
        if score >= SCORE_THRESHOLD_EXCELLENT:
            return "Excellent technique! Keep up the great form."
        elif score >= SCORE_THRESHOLD_GOOD:
            return f"Good solid swim. We found {error_count} areas to focus on."
        elif score >= SCORE_THRESHOLD_FAIR:
            return f"Fair technique. Working on these {error_count} errors will improve efficiency."
        else:
            return "Significant adjustments are recommended. Focus on core mechanics."
