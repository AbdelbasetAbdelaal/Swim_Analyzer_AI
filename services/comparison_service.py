import json
from pathlib import Path
from typing import Dict, Any, Optional
from models.comparison_models import ComparisonReport, MetricDelta

class ComparisonService:
    """
    Service responsible for comparing two analysis sessions and generating
    a structured, AI-ready ComparisonReport.
    """

    def _load_json(self, path: str) -> Dict[str, Any]:
        if not path or not Path(path).exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _calc_delta(self, name: str, val_a: Optional[float], val_b: Optional[float], higher_is_better: bool = True, unit: str = "") -> MetricDelta:
        if val_a is None or val_b is None:
            return MetricDelta(
                metric_name=name,
                old_value=val_a,
                new_value=val_b,
                delta=None,
                is_improvement=False,
                unit=unit
            )
        delta = val_b - val_a
        is_improvement = (delta > 0) if higher_is_better else (delta < 0)
        
        # If there's no actual change, we don't strictly call it an improvement
        if abs(delta) < 0.01:
            is_improvement = False 
            
        return MetricDelta(
            metric_name=name,
            old_value=val_a,
            new_value=val_b,
            delta=delta,
            is_improvement=is_improvement,
            unit=unit
        )

    def _get_metric_val(self, data: Dict[str, Any], key: str) -> Optional[float]:
        """Return a measured numeric value, or None when that metric is unavailable."""
        report = data.get("report", {})
        metric = report.get(key, {})
        if isinstance(metric, dict):
            value = metric.get("value")
        else:
            value = metric
        return float(value) if value is not None else None

    def compare_sessions(self, session_a: Any, session_b: Any) -> ComparisonReport:
        """
        Compare Session A (older) and Session B (newer).
        Returns a structured ComparisonReport.
        """
        data_a = self._load_json(session_a.report_json_path)
        data_b = self._load_json(session_b.report_json_path)

        report = ComparisonReport(
            athlete_id=session_a.athlete_id,
            session_a_id=session_a.session_id,
            session_b_id=session_b.session_id,
            video_path_a=session_a.processed_video_filename,
            video_path_b=session_b.processed_video_filename
        )

        # 1. Overall Performance
        # P0-8: None score = INSUFFICIENT_EVIDENCE — skip delta if either session lacks a score
        score_a = session_a.performance_score
        score_b = session_b.performance_score
        if score_a is not None and score_b is not None:
            report.overall_score_delta = self._calc_delta("Overall Score", score_a, score_b)
        # else: overall_score_delta remains None — no valid comparison possible


        # 2. Technique Metrics (Stroke-agnostic)
        sr_a = self._get_metric_val(data_a, "stroke_rate")
        sr_b = self._get_metric_val(data_b, "stroke_rate")
        if sr_a is not None and sr_b is not None:
            report.technique_deltas.append(self._calc_delta("Stroke Rate", sr_a, sr_b, higher_is_better=True, unit="strokes/min"))
        
        # Future-proof: we can iterate dynamically over other keys in data["report"] if they are valid metrics.
        sl_a = self._get_metric_val(data_a, "stroke_length")
        sl_b = self._get_metric_val(data_b, "stroke_length")
        if sl_a is not None and sl_b is not None:
            report.technique_deltas.append(self._calc_delta("Stroke Length", sl_a, sl_b, higher_is_better=True))
            
        kf_a = self._get_metric_val(data_a, "kick_frequency")
        kf_b = self._get_metric_val(data_b, "kick_frequency")
        if kf_a is not None and kf_b is not None:
            report.technique_deltas.append(self._calc_delta("Kick Frequency", kf_a, kf_b, higher_is_better=True))
            
        ss_a = self._get_metric_val(data_a, "stroke_symmetry")
        ss_b = self._get_metric_val(data_b, "stroke_symmetry")
        if ss_a is not None and ss_b is not None:
            report.technique_deltas.append(self._calc_delta("Stroke Symmetry", ss_a, ss_b, higher_is_better=True, unit="%"))

        # 3. Scientific Confidence (Qualitative)
        conf_a = session_a.scientific_confidence
        conf_b = session_b.scientific_confidence
        # Qualitative delta mapping (Low=1, Medium=2, High=3)
        cm = {"Low": 1, "Medium": 2, "High": 3, "Inconclusive": 0}
        report.confidence_delta = MetricDelta(
            metric_name="Scientific Confidence",
            old_value=cm.get(conf_a, 0),
            new_value=cm.get(conf_b, 0),
            delta=cm.get(conf_b, 0) - cm.get(conf_a, 0),
            is_improvement=(cm.get(conf_b, 0) > cm.get(conf_a, 0)),
            old_label=conf_a,
            new_label=conf_b
        )

        # 4. Movement Errors
        errors_a = {e.get("error_type", "") for e in data_a.get("report", {}).get("errors", [])}
        errors_b = {e.get("error_type", "") for e in data_b.get("report", {}).get("errors", [])}
        
        report.resolved_errors = list(errors_a - errors_b)
        report.new_errors = list(errors_b - errors_a)
        report.persistent_errors = list(errors_a.intersection(errors_b))

        # 5. Stroke Statistics
        report.cycles_delta = self._calc_delta("Completed Cycles", session_a.completed_cycles, session_b.completed_cycles)
        
        stat_a = data_a.get("stroke_statistics", {})
        stat_b = data_b.get("stroke_statistics", {})
        dur_a = float(stat_a.get("average_cycle_duration_ms", 0.0))
        dur_b = float(stat_b.get("average_cycle_duration_ms", 0.0))
        report.cycle_duration_delta = self._calc_delta("Cycle Duration", dur_a, dur_b, higher_is_better=False, unit="ms")
        
        # 6. Basic Coach Summary Rule-based Gen
        if report.overall_score_delta is None:
            report.coach_summary = "Score comparison unavailable (one or both sessions lack sufficient evidence). "
        elif report.overall_score_delta.is_improvement:
            report.coach_summary = f"Athlete has improved overall score by {report.overall_score_delta.delta:.1f} points. "
        elif report.overall_score_delta.delta < 0:
            report.coach_summary = f"Athlete performance dropped by {abs(report.overall_score_delta.delta):.1f} points. "
        else:
            report.coach_summary = "Athlete performance is stable. "

            
        if report.resolved_errors:
            report.coach_summary += f"Excellent work resolving {len(report.resolved_errors)} previous movement error(s)."
        if report.new_errors:
            report.coach_summary += f" Attention needed on {len(report.new_errors)} newly developed error(s)."

        return report
