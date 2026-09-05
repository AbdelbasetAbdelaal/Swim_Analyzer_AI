from dataclasses import dataclass
from typing import List
from validation.reference_loader import Labels, PhaseEvent
import math

@dataclass
class ContinuousMetricResult:
    name: str
    ground_truth: float
    prediction: float
    absolute_error: float
    passed: bool

@dataclass
class PhaseValidationResult:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    accuracy: float # Simplified accuracy

@dataclass
class ValidationSetResult:
    continuous_metrics: List[ContinuousMetricResult]
    phase_metrics: PhaseValidationResult
    overall_mae: float
    overall_rmse: float

class MetricsValidator:
    
    def __init__(self, phase_tolerance_frames: int = 5):
        self.phase_tolerance = phase_tolerance_frames
        self.tolerances = {
            "stroke_rate": 2.0,
            "stroke_length": 0.15,
            "kick_frequency": 0.3,
            "body_roll": 5.0,
            "stroke_cycles": 1.0 # 1 cycle tolerance
        }
        
    def validate(self, ground_truth: Labels, prediction: Labels) -> ValidationSetResult:
        continuous_results = []
        
        metrics = [
            ("Stroke Rate", ground_truth.stroke_rate, prediction.stroke_rate, self.tolerances["stroke_rate"]),
            ("Stroke Length", ground_truth.stroke_length, prediction.stroke_length, self.tolerances["stroke_length"]),
            ("Kick Frequency", ground_truth.kick_frequency, prediction.kick_frequency, self.tolerances["kick_frequency"]),
            ("Body Roll", ground_truth.body_roll, prediction.body_roll, self.tolerances["body_roll"]),
            ("Stroke Cycles", float(ground_truth.stroke_cycles), float(prediction.stroke_cycles), self.tolerances["stroke_cycles"]),
        ]
        
        sum_error = 0.0
        sum_squared_error = 0.0
        
        for name, gt_val, pred_val, tol in metrics:
            abs_err = abs(gt_val - pred_val)
            sum_error += abs_err
            sum_squared_error += abs_err ** 2
            
            continuous_results.append(ContinuousMetricResult(
                name=name,
                ground_truth=gt_val,
                prediction=pred_val,
                absolute_error=abs_err,
                passed=abs_err <= tol
            ))
            
        overall_mae = sum_error / len(metrics) if metrics else 0.0
        overall_rmse = math.sqrt(sum_squared_error / len(metrics)) if metrics else 0.0
        
        phase_metrics = self._validate_phases(ground_truth.events, prediction.events)
        
        return ValidationSetResult(
            continuous_metrics=continuous_results,
            phase_metrics=phase_metrics,
            overall_mae=overall_mae,
            overall_rmse=overall_rmse
        )
        
    def _validate_phases(self, gt_events: List[PhaseEvent], pred_events: List[PhaseEvent]) -> PhaseValidationResult:
        # A simple matching algorithm:
        # For each GT event, find the closest Pred event of the same phase.
        # If distance <= tolerance, TP. Remove from Pred list to avoid double counting.
        # If no match, FN.
        # Any remaining Pred events are FP.
        
        tp = 0
        fn = 0
        
        # Clone pred events so we can consume them
        unmatched_preds = list(pred_events)
        
        for gt in gt_events:
            # Find matching phase candidates
            candidates = [p for p in unmatched_preds if p.phase == gt.phase]
            
            if not candidates:
                fn += 1
                continue
                
            # Find closest candidate
            closest = min(candidates, key=lambda p: abs(p.frame - gt.frame))
            
            if abs(closest.frame - gt.frame) <= self.phase_tolerance:
                tp += 1
                unmatched_preds.remove(closest)
            else:
                fn += 1
                
        fp = len(unmatched_preds)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # Accuracy: (TP) / (Total Events) -> Simplified
        total_expected = len(gt_events)
        accuracy = tp / total_expected if total_expected > 0 else 0.0
        
        return PhaseValidationResult(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=precision,
            recall=recall,
            f1=f1,
            accuracy=accuracy
        )
