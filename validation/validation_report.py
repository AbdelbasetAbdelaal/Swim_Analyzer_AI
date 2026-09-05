import json
from validation.metrics_validator import ValidationSetResult

class ValidationReportGenerator:
    
    @staticmethod
    def generate_text_report(result: ValidationSetResult) -> str:
        lines = []
        lines.append("====================================================")
        lines.append("GROUND TRUTH VALIDATION REPORT")
        lines.append("====================================================")
        lines.append("")
        
        # Continuous Metrics
        for metric in result.continuous_metrics:
            lines.append(metric.name)
            lines.append("-" * len(metric.name))
            lines.append(f"Ground Truth: {metric.ground_truth}")
            lines.append(f"Prediction:   {metric.prediction}")
            lines.append(f"Abs Error:    {metric.absolute_error:.2f}")
            status = "PASS" if metric.passed else "FAIL"
            lines.append(f"Status:       {status}")
            lines.append("")
            
        lines.append("====================================================")
        lines.append("STROKE PHASE DETECTION")
        lines.append("====================================================")
        lines.append(f"True Positives:  {result.phase_metrics.true_positives}")
        lines.append(f"False Positives: {result.phase_metrics.false_positives}")
        lines.append(f"False Negatives: {result.phase_metrics.false_negatives}")
        lines.append("")
        lines.append(f"Accuracy:  {result.phase_metrics.accuracy * 100:.1f}%")
        lines.append(f"Precision: {result.phase_metrics.precision * 100:.1f}%")
        lines.append(f"Recall:    {result.phase_metrics.recall * 100:.1f}%")
        lines.append(f"F1 Score:  {result.phase_metrics.f1 * 100:.1f}%")
        lines.append("")
        
        lines.append("====================================================")
        lines.append("OVERALL AGGREGATES")
        lines.append("====================================================")
        lines.append(f"Global MAE:  {result.overall_mae:.3f}")
        lines.append(f"Global RMSE: {result.overall_rmse:.3f}")
        
        return "\n".join(lines)
        
    @staticmethod
    def generate_json_report(result: ValidationSetResult) -> str:
        continuous = {}
        for m in result.continuous_metrics:
            continuous[m.name] = {
                "ground_truth": m.ground_truth,
                "prediction": m.prediction,
                "absolute_error": m.absolute_error,
                "passed": m.passed
            }
            
        data = {
            "continuous_metrics": continuous,
            "phase_metrics": {
                "true_positives": result.phase_metrics.true_positives,
                "false_positives": result.phase_metrics.false_positives,
                "false_negatives": result.phase_metrics.false_negatives,
                "precision": result.phase_metrics.precision,
                "recall": result.phase_metrics.recall,
                "f1": result.phase_metrics.f1,
                "accuracy": result.phase_metrics.accuracy
            },
            "overall_mae": result.overall_mae,
            "overall_rmse": result.overall_rmse
        }
        
        return json.dumps(data, indent=4)
