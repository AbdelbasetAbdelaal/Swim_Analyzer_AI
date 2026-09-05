"""
Unit tests for AIStrokeAgent stroke detection engine.
"""

from models.data_models import StrokeType
from analysis.classification.ai_stroke_agent import AIStrokeAgent, StrokeVerificationInput


def _build_structured_input(
    arm_phase_corr: float,
    body_roll_amp: float,
    wrist_range: float,
    kick_symmetry: float,
    wrist_recovery_height: float,
    prediction: StrokeType = StrokeType.AUTO_DETECT,
    rule_score: float = 0.90,
    visibility_ratio: float = 0.95
) -> StrokeVerificationInput:
    return StrokeVerificationInput(
        kinematic_features={
            "arm_phase_correlation": arm_phase_corr,
            "body_roll_amplitude": body_roll_amp,
            "wrist_vertical_range_ratio": wrist_range,
            "leg_kick_symmetry": kick_symmetry,
            "wrist_recovery_height_ratio": wrist_recovery_height
        },
        biomechanics={
            "body_roll": body_roll_amp,
            "recovery_pattern": "dolphin" if arm_phase_corr > 0.3 else "frog"
        },
        rule_classifier={
            "prediction": prediction.value,
            "decision_score": rule_score,
            "evidence": [f"Mock rule predicted {prediction.value}"]
        },
        video_quality={
            "status": "PASS",
            "camera_view": None,
            "visibility_ratio": visibility_ratio
        }
    )


def test_ai_stroke_agent_freestyle_detection():
    """Verify AIStrokeAgent detects Freestyle for alternating arm rhythm."""
    agent = AIStrokeAgent()
    structured_input = _build_structured_input(
        arm_phase_corr=-0.75,
        body_roll_amp=18.0,
        wrist_range=0.18,
        kick_symmetry=0.1,
        wrist_recovery_height=0.05,
        prediction=StrokeType.FREESTYLE
    )

    res = agent.analyze_structured_input(structured_input)
    assert res.predicted_stroke in [StrokeType.FREESTYLE, StrokeType.BACKSTROKE]
    assert res.confidence >= 0.40
    assert "Alternating arm rhythm" in res.classification_reason


def test_ai_stroke_agent_butterfly_detection():
    """Verify AIStrokeAgent detects Butterfly for simultaneous arm motion with high recovery."""
    agent = AIStrokeAgent()
    structured_input = _build_structured_input(
        arm_phase_corr=0.80,
        body_roll_amp=12.0,
        wrist_range=0.20,
        kick_symmetry=0.05,
        wrist_recovery_height=-0.05,
        prediction=StrokeType.BUTTERFLY
    )

    res = agent.analyze_structured_input(structured_input)
    assert res.predicted_stroke == StrokeType.BUTTERFLY
    assert res.confidence >= 0.50


def test_ai_stroke_agent_breaststroke_detection():
    """Verify AIStrokeAgent detects Breaststroke for simultaneous underwater arm motion."""
    agent = AIStrokeAgent()
    structured_input = _build_structured_input(
        arm_phase_corr=0.70,
        body_roll_amp=6.0,
        wrist_range=0.04,
        kick_symmetry=0.55,
        wrist_recovery_height=0.10,
        prediction=StrokeType.BREASTSTROKE
    )

    res = agent.analyze_structured_input(structured_input)
    assert res.predicted_stroke == StrokeType.BREASTSTROKE
    assert res.confidence >= 0.50


def test_ai_stroke_agent_fallback_missing_evidence():
    """Verify AIStrokeAgent returns insufficient evidence with missing arm phase data."""
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
