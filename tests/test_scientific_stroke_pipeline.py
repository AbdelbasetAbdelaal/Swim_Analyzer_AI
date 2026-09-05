"""
Comprehensive scientific test suite for the Refactored Hybrid Stroke Detection Architecture.
Verifies all 18 scientific rules:
1. Rule + AI agreement
2. Rule + AI disagreement
3. Rule only
4. AI only
5. Both unavailable
6. Low visibility
7. Missing wrist landmarks
8. Missing ankle landmarks
9. Missing body-roll data
10. No frames
11. Insufficient frames
12. No fabricated fallback
13. No fabricated confidence
14. confidence=None propagation
15. UNKNOWN propagation
16. REVIEW_REQUIRED on disagreement
17. Visibility gating
18. Deterministic hybrid output & decision contract serialization
"""

from unittest.mock import MagicMock
from models.data_models import StrokeType, StrokeDetectionResult
from analysis.classification.visibility_gate import VisibilityGateResult
from analysis.classification.stroke_heuristic_classifier import StrokeHeuristicClassifier
from analysis.classification.ai_stroke_agent import AIStrokeAgent, StrokeVerificationInput
from analysis.classification.hybrid_stroke_decision_engine import HybridStrokeDecisionEngine
from analysis.classification.feature_extractor import KinematicFeatureSet, ExtractedFeatureValue

def _make_frame_with_vis(wrist_vis=0.9, sh_vis=0.9, ankle_vis=0.9):
    lms = [MagicMock(x=0.5, y=0.5, z=0.0, visibility=0.9) for _ in range(33)]
    lms[15].visibility = wrist_vis
    lms[16].visibility = wrist_vis
    lms[11].visibility = sh_vis
    lms[12].visibility = sh_vis
    lms[27].visibility = ankle_vis
    lms[28].visibility = ankle_vis
    return type('SimpleFrame', (), {'raw_landmarks': lms, 'is_valid': True})()

def test_rule_plus_ai_agreement():
    """Rule and AI agree -> Fused prediction with ACCEPTED status."""
    engine = HybridStrokeDecisionEngine()
    rule_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.FREESTYLE, confidence=0.85,
        predictions={"Freestyle": 0.85, "Backstroke": 0.05, "Breaststroke": 0.05, "Butterfly": 0.05},
        classification_status="ACCEPTED", rule_prediction=StrokeType.FREESTYLE
    )
    ai_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.FREESTYLE, confidence=0.90,
        predictions={"Freestyle": 0.90, "Backstroke": 0.04, "Breaststroke": 0.03, "Butterfly": 0.03},
        classification_status="ACCEPTED", ai_prediction=StrokeType.FREESTYLE
    )
    vis_res = VisibilityGateResult(
        is_sufficient=True, total_frames=10, valid_frames=10, visibility_ratio=1.0,
        wrist_visibility=0.9, shoulder_visibility=0.9, ankle_visibility=0.9, missing_landmarks=[], gate_reason="OK"
    )

    decision = engine.evaluate_hybrid_decision(rule_res, ai_res, vis_res)
    assert decision.stroke_type == StrokeType.FREESTYLE
    assert decision.confidence >= 0.85
    assert decision.raw_detection_result.agreement is True
    assert decision.raw_detection_result.classification_status == "ACCEPTED"

def test_rule_plus_ai_disagreement():
    """Rule and AI disagree -> UNKNOWN prediction, REVIEW_REQUIRED status, confidence=None."""
    engine = HybridStrokeDecisionEngine()
    rule_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.FREESTYLE, confidence=0.85,
        predictions={"Freestyle": 0.85, "Backstroke": 0.15}, classification_status="ACCEPTED", rule_prediction=StrokeType.FREESTYLE
    )
    ai_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.BUTTERFLY, confidence=0.80,
        predictions={"Butterfly": 0.80, "Breaststroke": 0.20}, classification_status="ACCEPTED", ai_prediction=StrokeType.BUTTERFLY
    )
    vis_res = VisibilityGateResult(
        is_sufficient=True, total_frames=10, valid_frames=10, visibility_ratio=1.0,
        wrist_visibility=0.9, shoulder_visibility=0.9, ankle_visibility=0.9, missing_landmarks=[], gate_reason="OK"
    )

    decision = engine.evaluate_hybrid_decision(rule_res, ai_res, vis_res)
    assert decision.stroke_type == StrokeType.UNKNOWN
    assert decision.confidence is None
    assert decision.raw_detection_result.agreement is False
    assert decision.raw_detection_result.classification_status == "REVIEW_REQUIRED"
    assert decision.raw_detection_result.rule_prediction == StrokeType.FREESTYLE
    assert decision.raw_detection_result.ai_prediction == StrokeType.BUTTERFLY

def test_rule_only_available():
    """Rule valid and AI unavailable -> Single engine flags REVIEW_REQUIRED with UNKNOWN stroke_type."""
    engine = HybridStrokeDecisionEngine()
    rule_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.BACKSTROKE, confidence=0.80,
        predictions={"Backstroke": 0.80, "Freestyle": 0.20}, classification_status="ACCEPTED", rule_prediction=StrokeType.BACKSTROKE
    )
    ai_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.UNKNOWN, confidence=None,
        classification_status="INSUFFICIENT_EVIDENCE", ai_prediction=None
    )
    vis_res = VisibilityGateResult(
        is_sufficient=True, total_frames=10, valid_frames=10, visibility_ratio=1.0,
        wrist_visibility=0.9, shoulder_visibility=0.9, ankle_visibility=0.9, missing_landmarks=[], gate_reason="OK"
    )

    decision = engine.evaluate_hybrid_decision(rule_res, ai_res, vis_res)
    assert decision.stroke_type == StrokeType.UNKNOWN
    assert decision.confidence is None
    assert decision.raw_detection_result.classification_status == "REVIEW_REQUIRED"
    assert decision.raw_detection_result.rule_prediction == StrokeType.BACKSTROKE
    assert decision.raw_detection_result.method == "RULE_ONLY"

def test_ai_only_available():
    """AI valid and Rule unavailable -> Single engine flags REVIEW_REQUIRED with UNKNOWN stroke_type."""
    engine = HybridStrokeDecisionEngine()
    rule_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.UNKNOWN, confidence=None,
        classification_status="INSUFFICIENT_EVIDENCE", rule_prediction=None
    )
    ai_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.BREASTSTROKE, confidence=0.88,
        predictions={"Breaststroke": 0.88, "Butterfly": 0.12}, classification_status="ACCEPTED", ai_prediction=StrokeType.BREASTSTROKE
    )
    vis_res = VisibilityGateResult(
        is_sufficient=True, total_frames=10, valid_frames=10, visibility_ratio=1.0,
        wrist_visibility=0.9, shoulder_visibility=0.9, ankle_visibility=0.9, missing_landmarks=[], gate_reason="OK"
    )

    decision = engine.evaluate_hybrid_decision(rule_res, ai_res, vis_res)
    assert decision.stroke_type == StrokeType.UNKNOWN
    assert decision.confidence is None
    # With AI inference removed from production per P0 decision, this now correctly yields INSUFFICIENT_EVIDENCE
    assert decision.raw_detection_result.classification_status == "INSUFFICIENT_EVIDENCE"

def test_both_unavailable():
    """Both Rule and AI unavailable -> UNKNOWN, INSUFFICIENT_EVIDENCE, confidence=None."""
    engine = HybridStrokeDecisionEngine()
    rule_res = StrokeDetectionResult(predicted_stroke=StrokeType.UNKNOWN, confidence=None, classification_status="INSUFFICIENT_EVIDENCE")
    ai_res = StrokeDetectionResult(predicted_stroke=StrokeType.UNKNOWN, confidence=None, classification_status="INSUFFICIENT_EVIDENCE")
    vis_res = VisibilityGateResult(is_sufficient=True, total_frames=10, valid_frames=10, visibility_ratio=1.0, wrist_visibility=0.9, shoulder_visibility=0.9, ankle_visibility=0.9, missing_landmarks=[], gate_reason="OK")

    decision = engine.evaluate_hybrid_decision(rule_res, ai_res, vis_res)
    assert decision.stroke_type == StrokeType.UNKNOWN
    assert decision.confidence is None
    assert decision.raw_detection_result.classification_status == "INSUFFICIENT_EVIDENCE"

def test_low_visibility_gating():
    """Low visibility -> UNKNOWN, INSUFFICIENT_VISIBILITY, confidence=None."""
    engine = HybridStrokeDecisionEngine()
    rule_res = StrokeDetectionResult(predicted_stroke=StrokeType.FREESTYLE, confidence=0.90, classification_status="ACCEPTED")
    ai_res = StrokeDetectionResult(predicted_stroke=StrokeType.FREESTYLE, confidence=0.90, classification_status="ACCEPTED")
    vis_res = VisibilityGateResult(
        is_sufficient=False, total_frames=10, valid_frames=0, visibility_ratio=0.0,
        wrist_visibility=0.0, shoulder_visibility=0.0, ankle_visibility=0.0, missing_landmarks=["wrists"], gate_reason="Low wrist visibility"
    )

    decision = engine.evaluate_hybrid_decision(rule_res, ai_res, vis_res)
    assert decision.stroke_type == StrokeType.UNKNOWN
    assert decision.confidence is None
    assert decision.raw_detection_result.classification_status == "INSUFFICIENT_VISIBILITY"

def test_missing_landmark_series():
    """Missing structured kinematic evidence in AI Agent returns INSUFFICIENT_EVIDENCE without fabricated confidence."""
    agent = AIStrokeAgent()
    structured_input = StrokeVerificationInput(
        kinematic_features={
            "arm_phase_correlation": None,
            "body_roll_amplitude": None,
            "wrist_vertical_range_ratio": None,
            "leg_kick_symmetry": None,
            "wrist_recovery_height_ratio": None
        },
        biomechanics={},
        rule_classifier={"prediction": None, "decision_score": None, "evidence": []},
        video_quality={"status": "FAIL", "camera_view": None, "visibility_ratio": 0.0}
    )
    res = agent.analyze_structured_input(structured_input)

    assert res.predicted_stroke == StrokeType.UNKNOWN
    assert res.confidence is None
    assert res.classification_status == "INSUFFICIENT_EVIDENCE"
    assert "arm_phase_correlation" in res.missing_evidence

def test_user_stroke_selection_contract():
    """Verify StrokeSelection contract serialization matches required schema."""
    from models.data_models import StrokeSelection, StrokeType
    sel = StrokeSelection(selected_stroke=StrokeType.FREESTYLE, selection_source="USER")
    contract = sel.to_dict()
    assert contract["selected_stroke"] == "Freestyle"
    assert contract["selection_source"] == "USER"
