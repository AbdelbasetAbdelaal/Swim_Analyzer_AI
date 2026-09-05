import pytest
from models.data_models import (
    AnalysisResult, PerformanceReport, ReliabilityResult, 
    VQAResult, StrokeStatistics, ValidatedMetric, FrameData
)
from analysis.consistency_validator import AnalysisConsistencyValidator

@pytest.fixture
def base_result():
    report = PerformanceReport(
        overall_score=90.0,
        stroke_rate=ValidatedMetric(value=40.0),
        stroke_length=ValidatedMetric(value=1.5),
        kick_frequency=ValidatedMetric(value=4.0),
        stroke_symmetry=ValidatedMetric(value=85.0),
        feedback_summary="Excellent technique"
    )
    vqa = VQAResult(overall_score=95, quality_class="Excellent")
    stats = StrokeStatistics(completed_cycles=5, average_phase_confidence=0.90)
    reliability = ReliabilityResult(analysis_confidence_score=95.0, analysis_reliability_score=90.0)
    
    frames = [
        FrameData(frame_index=i, timestamp_ms=i*33, raw_landmarks=None, is_valid=True, stroke_phase="Pull")
        for i in range(10)
    ]
    
    return AnalysisResult(
        report=report,
        vqa_result=vqa,
        stroke_statistics=stats,
        reliability=reliability,
        frames=frames
    )

def test_rule_1_low_phase_confidence(base_result):
    base_result.stroke_statistics.average_phase_confidence = 0.30
    consistency = AnalysisConsistencyValidator.validate(base_result)
    
    assert consistency.overall_score <= 75.0
    assert "Rule_1_Low_Phase_Confidence" in consistency.failed_rules
    assert consistency.scientific_confidence == "Low"
    assert consistency.validation_status == "Warning"

def test_rule_2_poor_video_quality(base_result):
    base_result.vqa_result.quality_class = "Poor"
    base_result.vqa_result.overall_score = 40
    consistency = AnalysisConsistencyValidator.validate(base_result)
    
    assert base_result.reliability.analysis_reliability_score <= 66.0
    assert base_result.reliability.analysis_reliability_level == "Medium"
    assert "Rule_2_Poor_VQA_Reliability" in consistency.failed_rules
    assert consistency.scientific_confidence == "Medium"

def test_rule_3_critical_video_quality(base_result):
    base_result.vqa_result.quality_class = "Critical"
    consistency = AnalysisConsistencyValidator.validate(base_result)
    
    assert consistency.overall_score == 0.0
    assert consistency.validation_status == "Critical"
    assert "Rule_3_Critical_VQA" in consistency.failed_rules

def test_rule_4_insufficient_cycles(base_result):
    base_result.stroke_statistics.completed_cycles = 1
    consistency = AnalysisConsistencyValidator.validate(base_result)
    
    assert base_result.report.stroke_rate.is_insufficient_data is True
    assert base_result.report.stroke_length.is_insufficient_data is True
    assert "Rule_4_Insufficient_Cycles" in consistency.failed_rules
    assert consistency.scientific_confidence == "Medium"

def test_rule_5_low_reliability(base_result):
    base_result.reliability.analysis_reliability_score = 30.0
    consistency = AnalysisConsistencyValidator.validate(base_result)
    
    assert "Inconclusive" in base_result.report.feedback_summary
    assert len(base_result.report.errors) == 0
    assert "Rule_5_Low_Reliability" in consistency.failed_rules
    assert consistency.scientific_confidence == "Low"

def test_rule_6_estimated_angles(base_result):
    for f in base_result.frames[:4]:
        f.is_valid = False
    
    consistency = AnalysisConsistencyValidator.validate(base_result)
    
    assert "Rule_6_Estimated_Angles" in consistency.failed_rules
    assert consistency.validation_status == "Warning"
    assert base_result.reliability.analysis_reliability_score < 90.0

def test_rule_7_unstable_pose(base_result):
    base_result.reliability.analysis_confidence_score = 40.0
    consistency = AnalysisConsistencyValidator.validate(base_result)
    
    assert "Rule_7_Unstable_Pose" in consistency.failed_rules
    assert consistency.scientific_confidence == "Low"

def test_contradiction_detection(base_result):
    base_result.vqa_result.quality_class = "Poor"
    base_result.vqa_result.overall_score = 30
    
    consistency = AnalysisConsistencyValidator.validate(base_result)
    
    # Swimmer's technique score (90) is preserved, while scientific_confidence drops to reflect poor camera data
    assert consistency.overall_score == 90.0
    assert consistency.scientific_confidence in ["Medium", "Low"]

