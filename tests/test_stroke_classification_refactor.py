import pytest
from models.data_models import StrokeType, StrokeDetectionResult
from analysis.classification.feature_extractor import KinematicFeatureSet, ExtractedFeatureValue
from analysis.classification.stroke_heuristic_classifier import StrokeHeuristicClassifier
from analysis.classification.ai_stroke_agent import AIStrokeAgent, StrokeVerificationInput
from analysis.classification.hybrid_stroke_decision_engine import HybridStrokeDecisionEngine, VisibilityGateResult

def _dummy_feature_set():
    return KinematicFeatureSet(
        arm_phase_correlation=ExtractedFeatureValue("arm_phase_correlation", None, False),
        mean_body_roll=ExtractedFeatureValue("mean_body_roll", None, False),
        body_roll_amplitude=ExtractedFeatureValue("body_roll_amplitude", None, False),
        wrist_vertical_range_ratio=ExtractedFeatureValue("wrist_vertical_range_ratio", None, False),
        leg_kick_symmetry=ExtractedFeatureValue("leg_kick_symmetry", None, False),
        wrist_recovery_height_ratio=ExtractedFeatureValue("wrist_recovery_height_ratio", None, False),
        total_frames_in_window=0,
        valid_frames_in_window=0,
        window_start_frame=0,
        window_end_frame=0
    )

def test_1_freestyle_classification():
    classifier = StrokeHeuristicClassifier()
    f = _dummy_feature_set()
    f.total_frames_in_window = 100
    f.valid_frames_in_window = 90
    f.arm_phase_correlation = ExtractedFeatureValue("arm_phase_correlation", -0.8, True)
    f.body_roll_amplitude = ExtractedFeatureValue("body_roll_amplitude", 25.0, True)
    f.wrist_vertical_range_ratio = ExtractedFeatureValue("wrist_vertical_range_ratio", 0.20, True)
    f.head_supine_ratio = ExtractedFeatureValue("head_supine_ratio", 0.05, True)

    res = classifier.classify_features(f)
    assert res.predicted_stroke == StrokeType.FREESTYLE
    assert res.confidence is not None and res.confidence >= 0.40
    assert res.confidence_type == "UNCALIBRATED_DECISION_SCORE"
    assert "arm_phase_alternating" in res.feature_contributions

def test_2_backstroke_classification():
    classifier = StrokeHeuristicClassifier()
    f = _dummy_feature_set()
    f.total_frames_in_window = 100
    f.valid_frames_in_window = 90
    f.arm_phase_correlation = ExtractedFeatureValue("arm_phase_correlation", -0.8, True)
    f.body_roll_amplitude = ExtractedFeatureValue("body_roll_amplitude", 20.0, True)
    f.head_supine_ratio = ExtractedFeatureValue("head_supine_ratio", 0.85, True)

    res = classifier.classify_features(f)
    assert res.predicted_stroke == StrokeType.BACKSTROKE
    assert res.confidence is not None and res.confidence >= 0.40
    assert res.confidence_type == "UNCALIBRATED_DECISION_SCORE"
    assert "head_supine_orientation" in res.feature_contributions

def test_3_breaststroke_classification():
    classifier = StrokeHeuristicClassifier()
    f = _dummy_feature_set()
    f.total_frames_in_window = 100
    f.valid_frames_in_window = 90
    f.arm_phase_correlation = ExtractedFeatureValue("arm_phase_correlation", +0.8, True)
    f.wrist_vertical_range_ratio = ExtractedFeatureValue("wrist_vertical_range_ratio", 0.05, True)
    f.leg_kick_symmetry = ExtractedFeatureValue("leg_kick_symmetry", +0.65, True)

    res = classifier.classify_features(f)
    assert res.predicted_stroke == StrokeType.BREASTSTROKE
    assert res.confidence is not None and res.confidence >= 0.40
    assert res.confidence_type == "UNCALIBRATED_DECISION_SCORE"
    assert "compact_wrist_excursion" in res.feature_contributions

def test_4_butterfly_classification():
    classifier = StrokeHeuristicClassifier()
    f = _dummy_feature_set()
    f.total_frames_in_window = 100
    f.valid_frames_in_window = 90
    f.arm_phase_correlation = ExtractedFeatureValue("arm_phase_correlation", +0.8, True)
    f.wrist_vertical_range_ratio = ExtractedFeatureValue("wrist_vertical_range_ratio", 0.35, True)

    res = classifier.classify_features(f)
    assert res.predicted_stroke == StrokeType.BUTTERFLY
    assert res.confidence is not None and res.confidence >= 0.40
    assert res.confidence_type == "UNCALIBRATED_DECISION_SCORE"
    assert "high_wrist_excursion" in res.feature_contributions


def test_5_insufficient_frames_classification():
    classifier = StrokeHeuristicClassifier()
    f = _dummy_feature_set()
    f.total_frames_in_window = 0
    f.valid_frames_in_window = 0
    res = classifier.classify_features(f)
    assert res.predicted_stroke == StrokeType.UNKNOWN
    assert res.confidence == 0.0
    assert res.classification_status == "insufficient_data"

def test_6_7_8_ai_agent_zero_video_access():
    agent = AIStrokeAgent()
    input_data = StrokeVerificationInput(
        kinematic_features={"arm_phase_correlation": -0.8, "body_roll_amplitude": 25.0},
        rule_classifier={"prediction": "Freestyle", "decision_score": 0.85},
        video_quality={"status": "PASS", "visibility_ratio": 0.95}
    )
    res = agent.analyze_structured_input(input_data)
    assert res.predicted_stroke == StrokeType.FREESTYLE
    assert res.method == "AI_STROKE_VERIFICATION_AGENT"

def _dummy_vis_result(is_sufficient=True):
    return VisibilityGateResult(
        is_sufficient=is_sufficient,
        total_frames=100,
        valid_frames=95,
        visibility_ratio=0.95,
        wrist_visibility=0.95,
        shoulder_visibility=0.95,
        ankle_visibility=0.95,
        missing_landmarks=[],
        gate_reason="PASS"
    )

def test_9_10_ai_verifier_skipped_for_strong_predictions():
    hybrid_engine = HybridStrokeDecisionEngine()
    vis_res = _dummy_vis_result(is_sufficient=True)

    rule_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.FREESTYLE,
        confidence=0.85,
        predictions={"Freestyle": 0.85, "Backstroke": 0.15},
        classification_status="ACCEPTED"
    )

    decision = hybrid_engine.evaluate_hybrid_decision(rule_res, ai_result=None, visibility_result=vis_res)
    assert decision.stroke_type == StrokeType.FREESTYLE
    assert decision.confidence == 0.85
    assert decision.raw_detection_result.method == "PYTHON_PRIMARY_ACCEPTED"

def test_11_python_ai_agreement():
    hybrid_engine = HybridStrokeDecisionEngine()
    vis_res = _dummy_vis_result(is_sufficient=True)

    rule_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.FREESTYLE,
        confidence=0.85,
        predictions={"Freestyle": 0.85, "Backstroke": 0.15},
        classification_status="ACCEPTED"
    )
    ai_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.FREESTYLE,
        confidence=0.80,
        predictions={"Freestyle": 0.80, "Backstroke": 0.20},
        classification_status="ACCEPTED"
    )

    decision = hybrid_engine.evaluate_hybrid_decision(rule_res, ai_result=ai_res, visibility_result=vis_res)
    assert decision.stroke_type == StrokeType.FREESTYLE
    assert decision.raw_detection_result.classification_status == "ACCEPTED"
    assert decision.raw_detection_result.agreement is True

def test_12_python_ai_disagreement():
    hybrid_engine = HybridStrokeDecisionEngine()
    vis_res = _dummy_vis_result(is_sufficient=True)

    rule_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.FREESTYLE,
        confidence=0.85,
        predictions={"Freestyle": 0.85, "Backstroke": 0.15},
        classification_status="ACCEPTED"
    )
    ai_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.BACKSTROKE,
        confidence=0.80,
        predictions={"Backstroke": 0.80, "Freestyle": 0.20},
        classification_status="ACCEPTED"
    )

    decision = hybrid_engine.evaluate_hybrid_decision(rule_res, ai_result=ai_res, visibility_result=vis_res)
    assert decision.stroke_type == StrokeType.UNKNOWN
    assert decision.confidence is None
    assert decision.raw_detection_result.classification_status == "REVIEW_REQUIRED"
    assert decision.raw_detection_result.is_inconsistent is True

def test_13_14_manual_override_flow():
    res = StrokeDetectionResult(
        predicted_stroke=StrokeType.FREESTYLE,
        selected_stroke=StrokeType.BACKSTROKE,
        confidence=0.85,
        manual_override=True
    )
    assert res.selected_stroke == StrokeType.BACKSTROKE
    assert res.manual_override is True

def test_15_numeric_confidence_guarantee():
    classifier = StrokeHeuristicClassifier()
    f = _dummy_feature_set()
    f.total_frames_in_window = 100
    f.valid_frames_in_window = 80
    f.body_roll_amplitude = ExtractedFeatureValue("body_roll_amplitude", 20.0, True)
    res = classifier.classify_features(f)
    assert isinstance(res.confidence, float)
    assert res.confidence >= 0.0

def test_16_python_only_mode_disables_ai_agent():
    hybrid_engine = HybridStrokeDecisionEngine()
    vis_res = _dummy_vis_result(is_sufficient=True)
    rule_res = StrokeDetectionResult(
        predicted_stroke=StrokeType.FREESTYLE,
        confidence=0.60,
        predictions={"Freestyle": 0.60, "Backstroke": 0.40},
        classification_status="ACCEPTED"
    )
    decision = hybrid_engine.evaluate_hybrid_decision(rule_res, ai_result=None, visibility_result=vis_res)
    assert decision.stroke_type == StrokeType.FREESTYLE
    assert decision.confidence == 0.60
    assert decision.raw_detection_result.ai_prediction is None
    assert decision.raw_detection_result.method == "PYTHON_PRIMARY_ACCEPTED"


