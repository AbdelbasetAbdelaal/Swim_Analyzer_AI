"""
AI Stroke Verification Agent for SwimAnalyzer AI.
Consumes compact structured analysis results from the existing video pipeline and verifies stroke type without accessing video,
frames, MediaPipe, or raw landmark processing.
"""

import math
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from models.data_models import StrokeType, StrokeDetectionResult
from core.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class StrokeVerificationInput:
    """Compact structured input for the AI Stroke Verification Agent."""
    kinematic_features: Dict[str, Optional[float]] = field(default_factory=dict)
    biomechanics: Dict[str, Optional[float]] = field(default_factory=dict)
    rule_classifier: Dict[str, Any] = field(default_factory=dict)
    video_quality: Dict[str, Any] = field(default_factory=dict)

class AIStrokeAgent:
    """
    Lightweight AI Stroke Verification Agent.
    Verifies stroke type from already-extracted kinematic and rule evidence only.
    """

    def __init__(self, confidence_threshold: float = 0.40):
        self.confidence_threshold = confidence_threshold
        self.version = "2.0.0-AI-Stroke-Verification"

    def analyze_structured_input(
        self,
        structured_input: StrokeVerificationInput,
        selected_stroke_input: StrokeType = StrokeType.AUTO_DETECT
    ) -> StrokeDetectionResult:
        """Analyzes structured features and returns a stroke verification result without video access."""
        missing_evidence: List[str] = []
        evidence: List[str] = []

        kinematic = structured_input.kinematic_features or {}
        biomechanics = structured_input.biomechanics or {}
        rule_info = structured_input.rule_classifier or {}
        quality = structured_input.video_quality or {}

        arm_phase_corr = kinematic.get("arm_phase_correlation")
        body_roll_amp = kinematic.get("body_roll_amplitude")
        wrist_range = kinematic.get("wrist_vertical_range_ratio")
        kick_symmetry = kinematic.get("leg_kick_symmetry")
        wrist_recovery_height = kinematic.get("wrist_recovery_height_ratio")
        head_supine = kinematic.get("head_supine_ratio")
        recovery_pattern = biomechanics.get("recovery_pattern")
        body_roll = biomechanics.get("body_roll")
        camera_view = quality.get("camera_view")
        visibility_ratio = quality.get("visibility_ratio")

        if arm_phase_corr is None:
            missing_evidence.append("arm_phase_correlation")

        if body_roll_amp is None:
            missing_evidence.append("body_roll_amplitude")

        if wrist_range is None:
            missing_evidence.append("wrist_vertical_range_ratio")

        if kick_symmetry is None:
            missing_evidence.append("leg_kick_symmetry")

        rule_prediction = rule_info.get("prediction")
        rule_decision_score = rule_info.get("decision_score")
        rule_evidence = rule_info.get("evidence") or []
        if rule_prediction:
            evidence.append(f"Rule engine predicted {rule_prediction}")
        if rule_decision_score is not None:
            evidence.append(f"Rule decision score {rule_decision_score}")
        evidence.extend([f"Rule evidence: {item}" for item in rule_evidence if isinstance(item, str)])

        if arm_phase_corr is None or abs(arm_phase_corr) <= 0.15:
            reason = "Insufficient or ambiguous arm phase evidence." if arm_phase_corr is not None else "Arm phase evidence is missing."
            result = self._build_insufficient_evidence_result(selected_stroke_input, reason, missing_evidence)
            self._log_no_video_access(result, structured_input)
            return result

        scores: Dict[StrokeType, float] = {
            StrokeType.FREESTYLE: 0.0,
            StrokeType.BACKSTROKE: 0.0,
            StrokeType.BREASTSTROKE: 0.0,
            StrokeType.BUTTERFLY: 0.0
        }

        reasoning_parts: List[str] = []

        if arm_phase_corr < -0.15:
            reasoning_parts.append(f"Alternating arm rhythm ({arm_phase_corr:.2f})")
            if head_supine is not None and head_supine > 0.50:
                scores[StrokeType.BACKSTROKE] += 0.85
                scores[StrokeType.FREESTYLE] += 0.15
                evidence.append(f"Supine face-up posture ratio {head_supine:.2f} supports Backstroke.")
            elif head_supine is not None and head_supine <= 0.20:
                scores[StrokeType.FREESTYLE] += 0.85
                scores[StrokeType.BACKSTROKE] += 0.15
                evidence.append(f"Prone face-down posture ratio {head_supine:.2f} supports Freestyle.")
            elif camera_view and "back" in str(camera_view).lower():
                scores[StrokeType.BACKSTROKE] += 0.75
                scores[StrokeType.FREESTYLE] += 0.25
                evidence.append("Camera view supports backstroke.")
            elif body_roll_amp is not None and body_roll_amp > 10.0:
                scores[StrokeType.FREESTYLE] += 0.65
                scores[StrokeType.BACKSTROKE] += 0.35
                evidence.append(f"Measured body roll amplitude {body_roll_amp:.2f} degrees")
            else:
                scores[StrokeType.FREESTYLE] += 0.55
                scores[StrokeType.BACKSTROKE] += 0.45
                evidence.append("Alternating arm phase favors Freestyle/Backstroke.")

            if body_roll is not None and body_roll > 10.0:
                evidence.append(f"High body roll {body_roll:.2f}")


        else:
            reasoning_parts.append(f"Simultaneous arm rhythm ({arm_phase_corr:.2f})")
            if wrist_range is not None and wrist_range > 0.08:
                scores[StrokeType.BUTTERFLY] += 0.75
                scores[StrokeType.BREASTSTROKE] += 0.25
                evidence.append("Large wrist recovery range supports Butterfly.")
            else:
                scores[StrokeType.BREASTSTROKE] += 0.75
                scores[StrokeType.BUTTERFLY] += 0.25
                evidence.append("Simultaneous arm motion supports Breaststroke/Butterfly.")

            if wrist_recovery_height is not None and wrist_recovery_height < 0.0:
                scores[StrokeType.BUTTERFLY] += 0.10
                evidence.append("Wrist recovery above shoulder line supports Butterfly.")
            if kick_symmetry is not None and kick_symmetry > 0.30:
                scores[StrokeType.BREASTSTROKE] += 0.10
                evidence.append(f"Symmetrical kick signature ({kick_symmetry:.2f})")

        if recovery_pattern and isinstance(recovery_pattern, str):
            evidence.append(f"Recovery pattern: {recovery_pattern}")
            if "dolphin" in recovery_pattern.lower():
                scores[StrokeType.BUTTERFLY] += 0.10
            elif "frog" in recovery_pattern.lower():
                scores[StrokeType.BREASTSTROKE] += 0.10

        total_score = sum(scores.values())
        if total_score <= 0.0:
            result = self._build_insufficient_evidence_result(selected_stroke_input, "No stroke candidate scored sufficient structured evidence.", missing_evidence)
            self._log_no_video_access(result, structured_input)
            return result

        predictions = {st.value: round(score / total_score, 4) for st, score in scores.items() if score > 0.0}
        top_stroke = max(predictions, key=predictions.get)
        top_confidence = predictions[top_stroke]
        predicted_stroke = StrokeType(top_stroke)

        classification_status = "ACCEPTED" if top_confidence >= self.confidence_threshold else "MODERATE_CONFIDENCE"
        reasoning = "; ".join(reasoning_parts + evidence)
        result = StrokeDetectionResult(
            predicted_stroke=predicted_stroke,
            confidence=top_confidence,
            predictions=predictions,
            selected_stroke=selected_stroke_input,
            manual_override=False,
            is_inconsistent=False,
            classification_status=classification_status,
            classification_reason=reasoning,
            feature_values=kinematic,
            feature_contributions={"ai_stroke_verification_score": top_confidence},
            missing_evidence=missing_evidence,
            classifier_version=self.version,
            threshold_version="AI_STROKE_VERIFICATION_v1.0",
            confidence_type="UNCALIBRATED_DECISION_SCORE",
            evidence={"ai_evidence": evidence},
            method="AI_STROKE_VERIFICATION_AGENT",
            ai_prediction=predicted_stroke
        )
        self._log_no_video_access(result, structured_input)
        return result

    def _log_no_video_access(self, result: StrokeDetectionResult, structured_input: StrokeVerificationInput) -> None:
        logger.info(
            "[AI_STROKE_AGENT] Input source: STRUCTURED_ANALYSIS | Video access: NONE | Pose extraction: NONE | Frames analyzed: 0 | "
            "Decision: %s | Decision score: %s | Missing evidence: %s",
            result.predicted_stroke.value,
            result.confidence if result.confidence is not None else "None",
            result.missing_evidence
        )

    def _build_insufficient_evidence_result(self, selected_stroke: StrokeType, reason: str, missing: List[str]) -> StrokeDetectionResult:
        result = StrokeDetectionResult(
            predicted_stroke=StrokeType.UNKNOWN,
            confidence=None,
            predictions={},
            selected_stroke=selected_stroke,
            manual_override=False,
            is_inconsistent=False,
            classification_status="INSUFFICIENT_EVIDENCE",
            classification_reason=f"AI Stroke Verification Agent: {reason}",
            feature_values={},
            feature_contributions={},
            missing_evidence=missing,
            classifier_version=self.version,
            threshold_version="AI_STROKE_VERIFICATION_v1.0",
            confidence_type="UNCALIBRATED_DECISION_SCORE",
            evidence={"ai_evidence": [reason]},
            method="AI_STROKE_VERIFICATION_AGENT",
            ai_prediction=None
        )
        return result

    @staticmethod
    def build_structured_input(
        kinematic_features: Dict[str, Optional[float]],
        rule_classifier: Dict[str, Any],
        video_quality: Dict[str, Any],
        biomechanics: Optional[Dict[str, Optional[float]]] = None
    ) -> StrokeVerificationInput:
        return StrokeVerificationInput(
            kinematic_features=kinematic_features,
            biomechanics=biomechanics or {},
            rule_classifier=rule_classifier,
            video_quality=video_quality
        )
