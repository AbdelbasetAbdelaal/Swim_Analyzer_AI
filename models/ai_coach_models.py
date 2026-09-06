"""
Data models for the optional AI Coach Layer.
Preserves strict scientific provenance, immutable original metric integrity,
and strongly-typed structured responses.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED = "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"
DEFAULT_AI_COACH_DISCLAIMER = (
    "AI-generated coaching interpretation. Measurements are produced by the SwimAnalyzer analysis pipeline. "
    f"Scientific validation status remains: {SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED}."
)


@dataclass
class AICoachInputMetric:
    """Individual metric packaged for LLM consumption with strict semantic context."""
    metric: str
    value: Optional[float]
    unit: str
    source: str = "measured_by_existing_analysis_pipeline"
    is_proxy: bool = False
    proxy_meaning: Optional[str] = None
    scientific_validation_status: str = SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED
    evidence_sufficiency: str = "INSUFFICIENT"  # "SUFFICIENT", "LIMITED", "INSUFFICIENT"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "is_proxy": self.is_proxy,
            "proxy_meaning": self.proxy_meaning,
            "scientific_validation_status": self.scientific_validation_status,
            "evidence_sufficiency": self.evidence_sufficiency,
        }


@dataclass
class AICoachInputPayload:
    """Strict structured input contract supplied to the AI coaching provider."""
    selected_stroke: str
    measured_metrics: List[AICoachInputMetric] = field(default_factory=list)
    reliability_score: float = 100.0
    reliability_level: str = "High"
    reliability_reasons: List[str] = field(default_factory=list)
    consistency_warnings: List[str] = field(default_factory=list)
    consistency_failed_rules: List[str] = field(default_factory=list)
    benchmark_comparisons: Optional[Dict[str, Any]] = None
    swimming_level: Optional[str] = None
    scientific_validation_status: str = SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_stroke": self.selected_stroke,
            "measured_metrics": [m.to_dict() for m in self.measured_metrics],
            "reliability_score": self.reliability_score,
            "reliability_level": self.reliability_level,
            "reliability_reasons": self.reliability_reasons,
            "consistency_warnings": self.consistency_warnings,
            "consistency_failed_rules": self.consistency_failed_rules,
            "benchmark_comparisons": self.benchmark_comparisons,
            "swimming_level": self.swimming_level,
            "scientific_validation_status": self.scientific_validation_status,
        }


@dataclass
class MetricInterpretation:
    """Interpretation of an individual metric with explicit evidence qualification."""
    metric: str
    interpretation: str
    evidence_level: str  # "measured", "limited", "insufficient"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "interpretation": self.interpretation,
            "evidence_level": self.evidence_level,
        }


@dataclass
class AICoachFeedback:
    """Validated structured output produced by the AI coaching interpretation layer."""
    summary: str
    strengths: List[str] = field(default_factory=list)
    areas_for_improvement: List[str] = field(default_factory=list)
    coach_recommendations: List[str] = field(default_factory=list)
    metric_interpretations: List[MetricInterpretation] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    disclaimer: str = DEFAULT_AI_COACH_DISCLAIMER
    provider: str = "none"
    model: str = ""
    status: str = "success"  # "success", "disabled", "fallback", "error"
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "strengths": self.strengths,
            "areas_for_improvement": self.areas_for_improvement,
            "coach_recommendations": self.coach_recommendations,
            "metric_interpretations": [m.to_dict() for m in self.metric_interpretations],
            "limitations": self.limitations,
            "disclaimer": self.disclaimer,
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AICoachFeedback":
        raw_interps = data.get("metric_interpretations", [])
        interps = []
        for item in raw_interps:
            if isinstance(item, dict):
                interps.append(MetricInterpretation(
                    metric=str(item.get("metric", "")),
                    interpretation=str(item.get("interpretation", "")),
                    evidence_level=str(item.get("evidence_level", "insufficient")),
                ))
            elif isinstance(item, MetricInterpretation):
                interps.append(item)

        return cls(
            summary=str(data.get("summary", "")),
            strengths=[str(s) for s in data.get("strengths", [])],
            areas_for_improvement=[str(a) for a in data.get("areas_for_improvement", [])],
            coach_recommendations=[str(r) for r in data.get("coach_recommendations", [])],
            metric_interpretations=interps,
            limitations=[str(l) for l in data.get("limitations", [])],
            disclaimer=str(data.get("disclaimer", DEFAULT_AI_COACH_DISCLAIMER)),
            provider=str(data.get("provider", "none")),
            model=str(data.get("model", "")),
            status=str(data.get("status", "success")),
            error_message=data.get("error_message"),
            created_at=str(data.get("created_at", datetime.now().isoformat())),
        )
