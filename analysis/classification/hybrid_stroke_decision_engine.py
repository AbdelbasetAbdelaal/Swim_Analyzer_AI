"""
Hybrid Stroke Decision Engine for SwimAnalyzer AI.
Combines outputs from:
1. Video / Pose Detector
2. Quality / Visibility Gate
3. Existing Rule-Based Classifier (StrokeHeuristicClassifier)
4. AI Stroke Classifier (AIStrokeAgent)

Outputs the unified 6-part decision structure for the Coach UI:
- Stroke Type
- Confidence
- Evidence
- Rule Contributions
- AI Contributions
- Uncertainty
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

from models.data_models import StrokeType, StrokeDetectionResult
from analysis.classification.visibility_gate import VisibilityGateResult
from core.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class HybridStrokeDecision:
    """Structured decision output produced by the Hybrid Decision Engine."""
    stroke_type: StrokeType
    confidence: Optional[float]
    evidence: Dict[str, Any]
    rule_contributions: Dict[str, float]
    ai_contributions: Dict[str, float]
    uncertainty: Optional[float]
    raw_detection_result: StrokeDetectionResult

class HybridStrokeDecisionEngine:
    """
    Fuses Evidence from Rule-Based Heuristics and AI Stroke Classifier
    to produce a unified, explainable decision for the Coach UI.
    """

    def __init__(self, rule_weight: float = 0.50, ai_weight: float = 0.50):
        self.rule_weight = rule_weight
        self.ai_weight = ai_weight

    def evaluate_hybrid_decision(
        self,
        rule_result: StrokeDetectionResult,
        ai_result: Optional[StrokeDetectionResult],
        visibility_result: VisibilityGateResult,
        selected_stroke_input: StrokeType = StrokeType.AUTO_DETECT
    ) -> HybridStrokeDecision:
        """
        Fuses predictions and feature evidence into a single HybridStrokeDecision object.
        Enforces strict scientific rules:
        - Python Primary Strong (AI skipped or None) -> ACCEPTED
        - Both valid + agree -> ACCEPTED / MODERATE_CONFIDENCE
        - Rule/AI disagreement -> UNKNOWN, REVIEW_REQUIRED, confidence=None
        - Insufficient visibility or evidence -> UNKNOWN, INSUFFICIENT_EVIDENCE/VISIBILITY, confidence=None
        """
        ai_missing = (ai_result.missing_evidence if ai_result else [])
        ai_conflicts = (ai_result.conflicts if ai_result else [])
        ai_feature_vals = (ai_result.feature_values if ai_result else {})
        ai_feature_contribs = (ai_result.feature_contributions if ai_result else {})

        missing_evidence = list(set(
            (rule_result.missing_evidence or []) + 
            ai_missing + 
            (visibility_result.missing_landmarks or [])
        ))
        conflicts = list(set((rule_result.conflicts or []) + ai_conflicts))

        rule_valid = rule_result.classification_status not in ["INSUFFICIENT_EVIDENCE", "INSUFFICIENT_VISIBILITY", "FALLBACK_DEFAULT"] and rule_result.predicted_stroke != StrokeType.UNKNOWN
        ai_valid = ai_result is not None and ai_result.classification_status not in ["INSUFFICIENT_EVIDENCE", "INSUFFICIENT_VISIBILITY", "FALLBACK_DEFAULT"] and ai_result.predicted_stroke != StrokeType.UNKNOWN

        # Case A / Python Primary Accepted (AI verifier disabled or not invoked)
        if ai_result is None:
            if rule_result.predicted_stroke != StrokeType.UNKNOWN and rule_result.confidence is not None:
                res = StrokeDetectionResult(
                    predicted_stroke=rule_result.predicted_stroke,
                    confidence=rule_result.confidence,
                    predictions=rule_result.predictions or {},
                    selected_stroke=selected_stroke_input,
                    manual_override=False,
                    is_inconsistent=False,
                    classification_status=rule_result.classification_status,
                    classification_reason=f"Primary Python Kinematic Classifier: {rule_result.classification_reason}",
                    feature_values=rule_result.feature_values or {},
                    feature_contributions=rule_result.feature_contributions or {},
                    confidence_type="UNCALIBRATED_DECISION_SCORE",
                    uncertainty=round(1.0 - (rule_result.confidence or 0.0), 4),
                    rule_prediction=rule_result.predicted_stroke,
                    ai_prediction=None,
                    agreement=None,
                    evidence=rule_result.evidence or {"reason": "Python Kinematic Engine Primary Accepted"},
                    missing_evidence=missing_evidence,
                    conflicts=conflicts,
                    method="PYTHON_PRIMARY_ACCEPTED"
                )
                return HybridStrokeDecision(
                    stroke_type=rule_result.predicted_stroke,
                    confidence=rule_result.confidence,
                    evidence=res.evidence,
                    rule_contributions=rule_result.feature_contributions or {},
                    ai_contributions={},
                    uncertainty=res.uncertainty,
                    raw_detection_result=res
                )


        # Rule 1: Visibility Gate Enforcement (for hybrid AI mode)
        if not visibility_result.is_sufficient:
            conflicts.append(f"Visibility Gate failed: {visibility_result.gate_reason}")
            res = StrokeDetectionResult(
                predicted_stroke=StrokeType.UNKNOWN,
                confidence=None,
                predictions={},
                selected_stroke=selected_stroke_input,
                manual_override=False,
                is_inconsistent=False,
                classification_status="INSUFFICIENT_VISIBILITY",
                classification_reason=f"Visibility Gate Rejected: {visibility_result.gate_reason}",
                feature_values=ai_feature_vals or rule_result.feature_values or {},
                feature_contributions={},
                confidence_type="UNCALIBRATED_DECISION_SCORE",
                uncertainty=1.0,
                rule_prediction=rule_result.predicted_stroke if rule_result.predicted_stroke != StrokeType.UNKNOWN else None,
                ai_prediction=ai_result.predicted_stroke if (ai_result and ai_result.predicted_stroke != StrokeType.UNKNOWN) else None,
                agreement=False,
                evidence={"visibility_gate": visibility_result.gate_reason},
                missing_evidence=missing_evidence,
                conflicts=conflicts,
                method="HYBRID_FUSION"
            )
            return HybridStrokeDecision(
                stroke_type=StrokeType.UNKNOWN, confidence=None, evidence=res.evidence,
                rule_contributions={}, ai_contributions={}, uncertainty=1.0, raw_detection_result=res
            )

        # Rule 2: Insufficient Python Kinematic Evidence
        if rule_result.predicted_stroke == StrokeType.UNKNOWN or rule_result.confidence is None:
            res = StrokeDetectionResult(
                predicted_stroke=StrokeType.UNKNOWN,
                confidence=None,
                predictions={},
                selected_stroke=selected_stroke_input,
                manual_override=False,
                is_inconsistent=False,
                classification_status="INSUFFICIENT_EVIDENCE",
                classification_reason="Primary Python Kinematic Classifier reported insufficient evidence.",
                feature_values=rule_result.feature_values or {},
                feature_contributions={},
                confidence_type="UNCALIBRATED_DECISION_SCORE",
                uncertainty=1.0,
                rule_prediction=None,
                ai_prediction=None,
                agreement=None,
                evidence={},
                missing_evidence=missing_evidence,
                conflicts=conflicts,
                method="PYTHON_PRIMARY"
            )
            return HybridStrokeDecision(
                stroke_type=StrokeType.UNKNOWN, confidence=None, evidence=res.evidence,
                rule_contributions={}, ai_contributions={}, uncertainty=1.0, raw_detection_result=res
            )



        # Rule 2: Both Engines Unavailable
        if not rule_valid and not ai_valid:
            res = StrokeDetectionResult(
                predicted_stroke=StrokeType.UNKNOWN,
                confidence=None,
                predictions={},
                selected_stroke=selected_stroke_input,
                manual_override=False,
                is_inconsistent=False,
                classification_status="INSUFFICIENT_EVIDENCE",
                classification_reason="Both Rule Classifier and AI Agent reported insufficient evidence.",
                feature_values=ai_result.feature_values or rule_result.feature_values or {},
                feature_contributions={},
                confidence_type="UNCALIBRATED_DECISION_SCORE",
                uncertainty=1.0,
                rule_prediction=None,
                ai_prediction=None,
                agreement=None,
                evidence={},
                missing_evidence=missing_evidence,
                conflicts=conflicts,
                method="HYBRID_FUSION"
            )
            return HybridStrokeDecision(
                stroke_type=StrokeType.UNKNOWN, confidence=None, evidence=res.evidence,
                rule_contributions={}, ai_contributions={}, uncertainty=1.0, raw_detection_result=res
            )

        # Rule 3: Single Engine Valid (Rule Only or AI Only) -> Flag REVIEW_REQUIRED, confidence=None
        if rule_valid and not ai_valid:
            conflict_msg = f"Rule Classifier predicted {rule_result.predicted_stroke.value}, but AI Agent had insufficient evidence."
            conflicts.append(conflict_msg)
            res = StrokeDetectionResult(
                predicted_stroke=StrokeType.UNKNOWN,
                confidence=None,
                predictions=rule_result.predictions or {},
                selected_stroke=selected_stroke_input,
                manual_override=False,
                is_inconsistent=False,
                classification_status="REVIEW_REQUIRED",
                classification_reason=conflict_msg,
                feature_values=rule_result.feature_values or {},
                feature_contributions=rule_result.feature_contributions or {},
                confidence_type="UNCALIBRATED_DECISION_SCORE",
                uncertainty=1.0,
                rule_prediction=rule_result.predicted_stroke,
                ai_prediction=None,
                agreement=None,
                evidence={"rule_only_reason": rule_result.classification_reason},
                missing_evidence=missing_evidence,
                conflicts=conflicts,
                method="RULE_ONLY"
            )
            return HybridStrokeDecision(
                stroke_type=StrokeType.UNKNOWN, confidence=None, evidence=res.evidence,
                rule_contributions=rule_result.feature_contributions or {}, ai_contributions={},
                uncertainty=1.0, raw_detection_result=res
            )

        if ai_valid and not rule_valid:
            conflict_msg = f"AI Agent predicted {ai_result.predicted_stroke.value}, but Rule Classifier had insufficient evidence."
            conflicts.append(conflict_msg)
            res = StrokeDetectionResult(
                predicted_stroke=StrokeType.UNKNOWN,
                confidence=None,
                predictions=ai_result.predictions or {},
                selected_stroke=selected_stroke_input,
                manual_override=False,
                is_inconsistent=False,
                classification_status="REVIEW_REQUIRED",
                classification_reason=conflict_msg,
                feature_values=ai_result.feature_values or {},
                feature_contributions=ai_result.feature_contributions or {},
                confidence_type="UNCALIBRATED_DECISION_SCORE",
                uncertainty=1.0,
                rule_prediction=None,
                ai_prediction=ai_result.predicted_stroke,
                agreement=None,
                evidence={"ai_only_reason": ai_result.classification_reason},
                missing_evidence=missing_evidence,
                conflicts=conflicts,
                method="AI_ONLY"
            )
            return HybridStrokeDecision(
                stroke_type=StrokeType.UNKNOWN, confidence=None, evidence=res.evidence,
                rule_contributions={}, ai_contributions=ai_result.feature_contributions or {},
                uncertainty=1.0, raw_detection_result=res
            )

        # Rule 4: Both Engines Valid -> Check Agreement
        rule_pred = rule_result.predicted_stroke
        ai_pred = ai_result.predicted_stroke

        if rule_pred != ai_pred:
            # DISAGREEMENT: Return UNKNOWN, REVIEW_REQUIRED, confidence=None
            conflict_msg = f"Disagreement between Rule Classifier ({rule_pred.value}) and AI Agent ({ai_pred.value})."
            conflicts.append(conflict_msg)
            
            res = StrokeDetectionResult(
                predicted_stroke=StrokeType.UNKNOWN,
                confidence=None,
                predictions={},
                selected_stroke=selected_stroke_input,
                manual_override=False,
                is_inconsistent=True,
                classification_status="REVIEW_REQUIRED",
                classification_reason=conflict_msg,
                feature_values={**(rule_result.feature_values or {}), **(ai_result.feature_values or {})},
                feature_contributions={**(rule_result.feature_contributions or {}), **(ai_result.feature_contributions or {})},
                confidence_type="UNCALIBRATED_DECISION_SCORE",
                uncertainty=1.0,
                rule_prediction=rule_pred,
                ai_prediction=ai_pred,
                agreement=False,
                evidence={
                    "rule_prediction": rule_pred.value,
                    "rule_confidence": f"{rule_result.confidence*100:.1f}%" if rule_result.confidence else "N/A",
                    "ai_prediction": ai_pred.value,
                    "ai_confidence": f"{ai_result.confidence*100:.1f}%" if ai_result.confidence else "N/A"
                },
                missing_evidence=missing_evidence,
                conflicts=conflicts,
                method="HYBRID_DISAGREEMENT"
            )
            return HybridStrokeDecision(
                stroke_type=StrokeType.UNKNOWN, confidence=None, evidence=res.evidence,
                rule_contributions=rule_result.feature_contributions, ai_contributions=ai_result.feature_contributions,
                uncertainty=1.0, raw_detection_result=res
            )

        # Rule 5: AGREEMENT -> Fuse scores
        strokes = [StrokeType.FREESTYLE, StrokeType.BACKSTROKE, StrokeType.BREASTSTROKE, StrokeType.BUTTERFLY]
        rule_preds = rule_result.predictions or {}
        ai_preds = ai_result.predictions or {}

        # Visibility dynamically adjusts weights
        w_rule = self.rule_weight * visibility_result.visibility_ratio
        w_ai = self.ai_weight * visibility_result.wrist_visibility
        tot_w = w_rule + w_ai if (w_rule + w_ai) > 0 else 1.0
        w_rule, w_ai = w_rule / tot_w, w_ai / tot_w

        fused_probs: Dict[str, float] = {}
        for s in strokes:
            sv = s.value
            pr = rule_preds.get(sv, 0.0)
            pa = ai_preds.get(sv, 0.0)
            fused_probs[sv] = round(w_rule * pr + w_ai * pa, 4)

        tot_p = sum(fused_probs.values()) or 1.0
        for sv in fused_probs:
            fused_probs[sv] = round(fused_probs[sv] / tot_p, 4)

        top_stroke_str = max(fused_probs, key=fused_probs.get)
        top_confidence = fused_probs[top_stroke_str]
        chosen_stroke = StrokeType(top_stroke_str)

        # Uncertainty = 1.0 - (top1 - top2 margin)
        sorted_probs = sorted(fused_probs.values(), reverse=True)
        top1 = sorted_probs[0]
        top2 = sorted_probs[1] if len(sorted_probs) > 1 else 0.0
        margin = top1 - top2
        uncertainty = round(max(0.0, min(1.0, 1.0 - margin)), 4)

        res = StrokeDetectionResult(
            predicted_stroke=chosen_stroke,
            confidence=top_confidence,
            predictions=fused_probs,
            selected_stroke=selected_stroke_input,
            manual_override=False,
            is_inconsistent=False,
            classification_status="ACCEPTED" if top_confidence >= 0.40 else "MODERATE_CONFIDENCE",
            classification_reason=f"Hybrid Fusion Agreement on {chosen_stroke.value} (Rule + AI).",
            feature_values={**(rule_result.feature_values or {}), **(ai_result.feature_values or {})},
            feature_contributions={**(rule_result.feature_contributions or {}), **(ai_result.feature_contributions or {})},
            confidence_type="UNCALIBRATED_DECISION_SCORE",
            uncertainty=uncertainty,
            rule_prediction=rule_pred,
            ai_prediction=ai_pred,
            agreement=True,
            evidence={
                "visibility_ratio": f"{visibility_result.visibility_ratio*100:.1f}%",
                "rule_confidence": f"{rule_result.confidence*100:.1f}%" if rule_result.confidence else "N/A",
                "ai_confidence": f"{ai_result.confidence*100:.1f}%" if ai_result.confidence else "N/A"
            },
            missing_evidence=missing_evidence,
            conflicts=conflicts,
            method="HYBRID_FUSION"
        )

        return HybridStrokeDecision(
            stroke_type=chosen_stroke,
            confidence=top_confidence,
            evidence=res.evidence,
            rule_contributions=rule_result.feature_contributions,
            ai_contributions=ai_result.feature_contributions,
            uncertainty=uncertainty,
            raw_detection_result=res
        )
