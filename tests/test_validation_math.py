import os
import unittest
import math
import subprocess
from validation.reference_loader import ReferenceLoader
from validation.metrics_validator import MetricsValidator

class TestValidationMath(unittest.TestCase):
    
    def setUp(self):
        self.gt_path = "validation/test_data/test_video_labels.json"
        self.pred_path = "validation/test_data/test_video_predictions.json"
        self.gt = ReferenceLoader.load(self.gt_path)
        self.pred = ReferenceLoader.load(self.pred_path)
        self.validator = MetricsValidator(phase_tolerance_frames=5)
        
    def test_continuous_metrics(self):
        result = self.validator.validate(self.gt, self.pred)
        
        # Expected Absolute Errors:
        # SR: abs(40-42) = 2.0
        # SL: abs(1.5-1.4) = 0.1
        # BR: abs(35-34) = 1.0
        # KF: abs(2.0-1.8) = 0.2
        # SC: abs(10-10) = 0.0
        
        errors = {m.name: m.absolute_error for m in result.continuous_metrics}
        self.assertAlmostEqual(errors["Stroke Rate"], 2.0)
        self.assertAlmostEqual(errors["Stroke Length"], 0.1)
        self.assertAlmostEqual(errors["Body Roll"], 1.0)
        self.assertAlmostEqual(errors["Kick Frequency"], 0.2)
        self.assertAlmostEqual(errors["Stroke Cycles"], 0.0)
        
        # Expected MAE = 3.3 / 5 = 0.66
        self.assertAlmostEqual(result.overall_mae, 0.66)
        
        # Expected RMSE = sqrt(5.05 / 5) = sqrt(1.01)
        self.assertAlmostEqual(result.overall_rmse, math.sqrt(1.01))
        
    def test_phase_metrics(self):
        result = self.validator.validate(self.gt, self.pred)
        p = result.phase_metrics
        
        # TP = 5
        # FN = 3 (Push 40, Recovery 50, Catch 70)
        # FP = 2 (Push 55, Catch 78)
        self.assertEqual(p.true_positives, 5)
        self.assertEqual(p.false_negatives, 3)
        self.assertEqual(p.false_positives, 2)
        
        # Accuracy = TP / Total Expected (8)
        self.assertEqual(p.accuracy, 5/8)
        
        # Precision = 5 / 7
        self.assertAlmostEqual(p.precision, 5/7)
        
        # Recall = 5 / 8
        self.assertEqual(p.recall, 5/8)
        
        # F1 = 2/3
        self.assertAlmostEqual(p.f1, 2/3)
        
    def test_determinism_and_regression(self):
        # Run CLI validation 5 times to check determinism
        
        reports = []
        for i in range(5):
            subprocess.run(["python", "validate.py", "--labels", self.gt_path, "--predictions", self.pred_path], check=True)
            with open("validation_report.json", "r") as f:
                reports.append(f.read())
                
        # All 5 runs must be byte-for-byte identical
        for i in range(1, 5):
            self.assertEqual(reports[0], reports[i], "Determinism failed! Generated reports differ across runs.")
            
        # Check against golden regression reference
        golden_file = "validation/test_data/golden_report.json"
        
        # If golden doesn't exist, this is the first run, so create it
        if not os.path.exists(golden_file):
            with open(golden_file, "w") as f:
                f.write(reports[0])
                
        with open(golden_file, "r") as f:
            golden_content = f.read()
            
        self.assertEqual(reports[0], golden_content, "Regression failed! New report differs from golden reference.")


from models.data_models import (
    AnalysisResult, PerformanceReport, ReliabilityResult, 
    VQAResult, StrokeStatistics, ValidatedMetric, FrameData, JointAngles
)
from analysis.consistency_validator import AnalysisConsistencyValidator

class TestScientificConsistencyValidation(unittest.TestCase):
    """
    Validates scientific accuracy, technique score independence, and 
    non-contradiction rules across pipeline edge cases.
    """
    
    def _create_mock_analysis(self, tech_score=90.0, vqa_class="Excellent", vqa_score=95, 
                             cycles=5, phase_conf=0.95, tracking_conf=95.0, reliability_score=90.0):
        report = PerformanceReport(
            overall_score=tech_score,
            stroke_rate=ValidatedMetric(value=40.0, valid=True),
            stroke_length=ValidatedMetric(value=1.5, valid=True),
            kick_frequency=ValidatedMetric(value=4.0, valid=True),
            stroke_symmetry=ValidatedMetric(value=85.0, valid=True),
            feedback_summary="Technique analyzed."
        )
        vqa = VQAResult(overall_score=vqa_score, quality_class=vqa_class)
        stats = StrokeStatistics(completed_cycles=cycles, average_phase_confidence=phase_conf)
        reliability = ReliabilityResult(
            analysis_confidence_score=tracking_conf, 
            analysis_reliability_score=reliability_score
        )
        
        frames = []
        for i in range(20):
            ja = JointAngles()
            ja.left_elbow = ValidatedMetric(value=110.0, valid=True) # Optimal 90-120
            ja.right_elbow = ValidatedMetric(value=110.0, valid=True)
            ja.left_knee = ValidatedMetric(value=165.0, valid=True) # Optimal 130-175
            ja.right_knee = ValidatedMetric(value=165.0, valid=True)
            ja.left_shoulder = ValidatedMetric(value=160.0, valid=True) # Optimal 140-180
            ja.right_shoulder = ValidatedMetric(value=160.0, valid=True)
            frames.append(FrameData(
                frame_index=i, timestamp_ms=i*33, raw_landmarks=None, 
                is_valid=True, stroke_phase="Pull", angles=ja
            ))
            
        return AnalysisResult(
            report=report, vqa_result=vqa, stroke_statistics=stats,
            reliability=reliability, frames=frames
        )

    def test_high_technique_high_video_quality(self):
        """High technique + High video quality -> High score + High confidence."""
        analysis = self._create_mock_analysis(tech_score=90.0, vqa_class="Excellent", vqa_score=95, cycles=5)
        report = AnalysisConsistencyValidator.validate(analysis)
        self.assertEqual(report.overall_score, 90.0)
        self.assertEqual(report.scientific_confidence, "High")
        self.assertEqual(report.validation_status, "Passed")

    def test_high_technique_low_video_quality(self):
        """High technique + Low video quality -> High score + Medium/Low confidence."""
        analysis = self._create_mock_analysis(tech_score=90.0, vqa_class="Poor", vqa_score=45, cycles=5)
        report = AnalysisConsistencyValidator.validate(analysis)
        # Performance Score MUST reflect swimmer technique only (90.0), not drop to 30
        self.assertEqual(report.overall_score, 90.0)
        self.assertIn(report.scientific_confidence, ["Medium", "Low"])

    def test_poor_technique_high_video_quality(self):
        """Poor technique + High video quality -> Low score + High confidence."""
        analysis = self._create_mock_analysis(tech_score=45.0, vqa_class="Excellent", vqa_score=95, cycles=5)
        report = AnalysisConsistencyValidator.validate(analysis)
        self.assertEqual(report.overall_score, 45.0)
        self.assertEqual(report.scientific_confidence, "High")

    def test_poor_technique_low_video_quality(self):
        """Poor technique + Low video quality -> Low score + Medium/Low confidence."""
        analysis = self._create_mock_analysis(tech_score=40.0, vqa_class="Poor", vqa_score=40, cycles=5)
        report = AnalysisConsistencyValidator.validate(analysis)
        self.assertEqual(report.overall_score, 40.0)
        self.assertIn(report.scientific_confidence, ["Medium", "Low"])

    def test_zero_completed_stroke_cycles(self):
        """Zero completed stroke cycles -> Score is 0.0, insufficient data flags set."""
        analysis = self._create_mock_analysis(tech_score=85.0, cycles=0)
        report = AnalysisConsistencyValidator.validate(analysis)
        self.assertIsNone(report.overall_score)
        self.assertTrue(analysis.report.stroke_rate.is_insufficient_data)
        self.assertIn("Rule_4_Insufficient_Cycles", report.failed_rules)

    def test_partial_stroke_cycles(self):
        """Partial stroke cycles (<2) -> Validated metrics flagged, confidence lowered."""
        analysis = self._create_mock_analysis(tech_score=85.0, cycles=1)
        report = AnalysisConsistencyValidator.validate(analysis)
        self.assertTrue(analysis.report.stroke_rate.is_insufficient_data)
        self.assertIn(report.scientific_confidence, ["Medium", "Low"])

    def test_inconsistent_biomechanical_metrics(self):
        """Unstable tracking / low reliability clears specific error lists to avoid false feedback."""
        analysis = self._create_mock_analysis(tech_score=85.0, reliability_score=30.0)
        report = AnalysisConsistencyValidator.validate(analysis)
        self.assertEqual(len(analysis.report.errors), 0)
        self.assertIn("Rule_5_Low_Reliability", report.failed_rules)

    def test_critical_vqa_contradiction_safety(self):
        """Critical VQA results in Critical validation status and 0 score without contradictory Passed state."""
        analysis = self._create_mock_analysis(tech_score=95.0, vqa_class="Critical", vqa_score=20)
        report = AnalysisConsistencyValidator.validate(analysis)
        self.assertEqual(report.overall_score, 0.0)
        self.assertEqual(report.validation_status, "Critical")
        self.assertEqual(report.scientific_confidence, "Inconclusive")


if __name__ == "__main__":
    unittest.main()

