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
        available_components = []
        available_component_names = []
        unavailable_component_names = []

        # 1. Stroke Symmetry
        sym_weight = self.weights.get("symmetry_weight", 0.20)
        if report.stroke_symmetry and report.stroke_symmetry.valid and report.stroke_symmetry.value is not None:
            sym_score = float(report.stroke_symmetry.value)
            available_components.append((sym_score, sym_weight))
            available_component_names.append("Stroke Symmetry")
            if sym_score < SYMMETRY_SCORE_PENALTY_THRESHOLD:
                errors.append(MovementError(-1, 0, "Asymmetrical Pull", "Left and right arms have significantly different mechanics.", "High", confidence=report.stroke_symmetry.confidence))
        else:
            # P0-7: Do NOT default to MAX_SCORE. Skip this component and note unavailability.
            unavailable_component_names.append("Stroke Symmetry")
            logger.debug("Symmetry metric unavailable; component omitted from scoring.")

        # 2. Elbow Angle during Pull
        elb_weight = self.weights.get("elbow_weight", 0.25)
        pull_elbows = []
        for f in analysis_result.frames:
            if f.is_valid and f.stroke_phase == "Pull":
                if f.angles.left_elbow and f.angles.left_elbow.valid: pull_elbows.append((f.angles.left_elbow.value, f.timestamp_ms))
                if f.angles.right_elbow and f.angles.right_elbow.valid: pull_elbows.append((f.angles.right_elbow.value, f.timestamp_ms))
        
        if pull_elbows:
            vals = [v[0] for v in pull_elbows]
            ts = pull_elbows[0][1]
            avg_val = float(np.mean(vals))
            # Optimal high-elbow catch / mid-pull flexion is 90° to 120° (Maglischo, 2003)
            if PULL_ELBOW_MIN_ANGLE <= avg_val <= PULL_ELBOW_MAX_ANGLE:
                elb_score = float(MAX_SCORE)
            else:
                elb_score = float(DEFAULT_PENALTY_SCORE)
                errors.append(MovementError(-1, ts, "Dropped Elbow", f"Average elbow angle during pull is outside optimal range (90°-120°) (Measured: {avg_val:.1f}).", "Medium"))
            available_components.append((elb_score, elb_weight))
            available_component_names.append("Pull Elbow Angle")
        else:
            unavailable_component_names.append("Pull Elbow Angle")
            logger.debug("Pull elbow angles unavailable; component omitted from scoring.")

        # 3. Shoulder Angle (Recovery/Reach)
        shoulder_weight = self.weights.get("shoulder_weight", 0.20)
        reach_shoulders = []
        for f in analysis_result.frames:
            if f.is_valid and f.stroke_phase == "Recovery":
                if f.angles.left_shoulder and f.angles.left_shoulder.valid: reach_shoulders.append((f.angles.left_shoulder.value, f.timestamp_ms))
                if f.angles.right_shoulder and f.angles.right_shoulder.valid: reach_shoulders.append((f.angles.right_shoulder.value, f.timestamp_ms))
                
        if reach_shoulders:
            vals = [v[0] for v in reach_shoulders]
            ts = reach_shoulders[0][1]
            avg_val = float(np.mean(vals))
            if RECOVERY_SHOULDER_MIN_ANGLE <= avg_val <= RECOVERY_SHOULDER_MAX_ANGLE:
                sh_score = float(MAX_SCORE)
            else:
                sh_score = float(DEFAULT_PENALTY_SCORE)
                errors.append(MovementError(-1, ts, "Limited Shoulder Extension", f"Shoulder extension during recovery is restricted (Measured: {avg_val:.1f}).", "Medium"))
            available_components.append((sh_score, shoulder_weight))
            available_component_names.append("Recovery Shoulder Angle")
        else:
            unavailable_component_names.append("Recovery Shoulder Angle")
            logger.debug("Recovery shoulder angles unavailable; component omitted from scoring.")

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
        
        if knees:
            vals = [v[0] for v in knees]
            ts = knees[0][1]
            avg_val = float(np.mean(vals))
            if KNEE_BEND_MIN_ANGLE <= avg_val <= KNEE_BEND_MAX_ANGLE:
                kn_score = float(MAX_SCORE)
            else:
                kn_score = float(DEFAULT_PENALTY_SCORE)
                errors.append(MovementError(-1, ts, "Excessive Knee Bend", f"Knees are bending too much during kicking (Measured: {avg_val:.1f}).", "Medium"))
            available_components.append((kn_score, knee_weight))
            available_component_names.append("Knee Angle")
        else:
            unavailable_component_names.append("Knee Angle")
            logger.debug("Knee angles unavailable; component omitted from scoring.")

        report.available_components = available_component_names
        report.unavailable_components = unavailable_component_names
        report.total_components_count = len(available_component_names) + len(unavailable_component_names)

        # Downstream propagation — score is only valid when upstream dependencies are met
        cycles = analysis_result.stroke_statistics.completed_cycles if analysis_result.stroke_statistics else 0
        reliability_score = analysis_result.reliability.analysis_reliability_score if analysis_result.reliability else 0.0

        if cycles == 0:
            # P0-7: No complete stroke cycle → no valid score
            report.overall_score = None
            report.evidence_sufficiency = "INSUFFICIENT"
            report.technique_assessment = "INSUFFICIENT EVIDENCE"
            report.status = "insufficient_evidence"
            report.feedback_summary = "INSUFFICIENT_EVIDENCE: No complete stroke cycle detected. Scoring requires at least one full cycle."
            report.errors = errors
            return report

        if reliability_score < RELIABILITY_MIN_ACCEPTABLE_SCORE:
            # P0-7: Reliability too low → no valid score
            report.overall_score = None
            report.evidence_sufficiency = "INSUFFICIENT"
            report.technique_assessment = "INSUFFICIENT EVIDENCE"
            report.status = "insufficient_evidence"
            report.feedback_summary = f"INSUFFICIENT_EVIDENCE: Reliability score {reliability_score:.0f} below minimum threshold ({RELIABILITY_MIN_ACCEPTABLE_SCORE}). Biomechanical data is insufficient for scoring."
            report.errors = errors
            return report

        total_weight = sum(w for _, w in available_components)
        if total_weight <= 0.0 or len(available_components) == 0:
            report.overall_score = None
            report.evidence_sufficiency = "INSUFFICIENT"
            report.technique_assessment = "INSUFFICIENT EVIDENCE"
            report.status = "metric_unavailable"
            report.feedback_summary = "METRIC_UNAVAILABLE: No scoreable metrics available. Ensure pose detection is working correctly."
            report.errors = errors
            return report

        weighted_sum = sum(score * weight for score, weight in available_components)
        final_score = weighted_sum / total_weight
        report.overall_score = float(round(max(0.0, min(MAX_SCORE, final_score)), 1))
        report.status = "available"
        report.errors = errors

        # Determine evidence sufficiency and technique assessment (P0-1, P0-2, P0-3)
        if len(available_components) <= 1:
            report.evidence_sufficiency = "INSUFFICIENT"
            report.technique_assessment = "INSUFFICIENT EVIDENCE"
        elif len(available_components) == 2:
            report.evidence_sufficiency = "LIMITED"
            report.technique_assessment = "LIMITED EVIDENCE"
        else:
            report.evidence_sufficiency = "SUFFICIENT"
            if report.overall_score >= SCORE_THRESHOLD_EXCELLENT:
                report.technique_assessment = "Excellent"
            elif report.overall_score >= SCORE_THRESHOLD_GOOD:
                report.technique_assessment = "Good"
            elif report.overall_score >= SCORE_THRESHOLD_FAIR:
                report.technique_assessment = "Fair"
            else:
                report.technique_assessment = "Needs Improvement"

        report.feedback_summary = self._generate_feedback_summary(
            report.overall_score, 
            len(errors), 
            report.evidence_sufficiency,
            len(available_components),
            report.total_components_count
        )
        
        return report

    def _generate_feedback_summary(
        self, 
        score: float, 
        error_count: int,
        evidence_sufficiency: str = "SUFFICIENT",
        available_count: int = 4,
        total_count: int = 4
    ) -> str:
        if evidence_sufficiency == "INSUFFICIENT":
            return f"Technique score {score:.1f}/100 is based only on {available_count} of {total_count} measurable components. Evidence is insufficient for overall technique evaluation."
        elif evidence_sufficiency == "LIMITED":
            return f"Limited evidence ({available_count} of {total_count} components available). Available technique score is {score:.1f}/100 with {error_count} detected flaw(s)."
        else:
            if score >= SCORE_THRESHOLD_EXCELLENT:
                return "Solid technique across all evaluated components! Keep up the great form."
            elif score >= SCORE_THRESHOLD_GOOD:
                return f"Good solid swim. We found {error_count} areas to focus on."
            elif score >= SCORE_THRESHOLD_FAIR:
                return f"Fair technique. Working on these {error_count} errors will improve efficiency."
            else:
                return "Significant adjustments are recommended. Focus on core mechanics."
