"""
AI Coach Service for SwimAnalyzer AI (Step 71).
Provides an optional, non-blocking coaching interpretation layer operating strictly
on structured analysis results produced by the frozen MediaPipe pipeline.

Invariants:
- The AI Coach does not perform pose detection, measurements, or threshold tuning.
- The AI Coach cannot alter or overwrite measured metrics.
- The scientific status remains strictly NOT_VALIDATED — INSUFFICIENT GROUND TRUTH.
- Video analysis functions normally when the AI Coach is disabled, offline, or unavailable.
- Zero secrets or tokens are stored in source code.
"""
from abc import ABC, abstractmethod
import json
import re
from typing import Dict, Any, Optional, List
import requests

from core.logger import setup_logger
from core.config import config
from models.data_models import AnalysisResult, PerformanceReport
from models.ai_coach_models import (
    AICoachInputMetric,
    AICoachInputPayload,
    MetricInterpretation,
    AICoachFeedback,
    SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED,
    DEFAULT_AI_COACH_DISCLAIMER,
)

logger = setup_logger(__name__)

AI_COACH_SYSTEM_PROMPT = f"""You are an AI coaching interpretation assistant for Swim Analyzer AI, a swimming biomechanics analysis application.
You do not perform pose estimation.
You do not perform measurements.
You do not validate scientific claims.
You only explain and interpret measurements supplied by the application.

Strict Rules:
1. Never invent or hallucinate measurement values. Only discuss metrics present in the supplied payload.
2. Never change or recalculate supplied values.
3. Never claim any metric is scientifically validated. The scientific validation status is strictly: {SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED}.
4. Respect reliability warnings and consistency alerts. If reliability is low or evidence is insufficient, explicitly state so.
5. Respect metric provenance:
   - Hand excursion proxy ('hand_excursion_proxy_bl') is a 2D stroke-length proxy normalized to body lengths, NOT a calibrated physical displacement in meters. Never convert or describe it as physical center-of-mass translation.
   - Monocular depth (z) is an uncalibrated relative estimate.
6. Distinguish measured values from proxies and derived values.
7. If evidence is insufficient, explicitly state that conclusive coaching feedback cannot be provided.
8. Provide practical, coach-friendly suggestions and technical drills ONLY when supported by the supplied measurements.
9. Do not diagnose injuries, physical impairments, or medical conditions.
10. Do not expose secrets, tokens, or internal application data.

Output Format:
You MUST respond with valid, parseable JSON matching this exact structure:
{{
  "summary": "Brief executive coaching summary.",
  "strengths": ["Identified technical strength 1", ...],
  "areas_for_improvement": ["Identified technical flaw 1", ...],
  "coach_recommendations": ["Actionable coaching drill or technique recommendation 1", ...],
  "metric_interpretations": [
    {{
      "metric": "metric_name",
      "interpretation": "Interpretation of the metric value.",
      "evidence_level": "measured|limited|insufficient"
    }}
  ],
  "limitations": ["Biomechanics limitation or caveat 1", ...]
}}
"""


class AICoachPayloadBuilder:
    """Builds a strictly structured, privacy-preserving payload for the AI coach."""

    @staticmethod
    def build(analysis_result: AnalysisResult, athlete_profile: Optional[Any] = None) -> AICoachInputPayload:
        """Converts AnalysisResult into AICoachInputPayload without leaking private data or raw video."""
        selected_stroke = "Unknown"
        if analysis_result.stroke_selection:
            st_val = analysis_result.stroke_selection.selected_stroke
            selected_stroke = st_val.value if hasattr(st_val, "value") else str(st_val)
        elif analysis_result.stroke_type:
            selected_stroke = str(analysis_result.stroke_type)

        measured_metrics: List[AICoachInputMetric] = []
        report = getattr(analysis_result, "report", None)

        # 1. Stroke Rate
        sr_val = getattr(analysis_result, "average_stroke_rate", 0.0)
        if report and getattr(report, "stroke_rate", None) and report.stroke_rate.valid and report.stroke_rate.value is not None:
            sr_val = report.stroke_rate.value
        if sr_val and sr_val > 0:
            measured_metrics.append(AICoachInputMetric(
                metric="stroke_rate",
                value=round(float(sr_val), 1),
                unit="spm",
                source="measured_by_existing_analysis_pipeline",
                is_proxy=False,
                proxy_meaning=None,
                scientific_validation_status=SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED,
                evidence_sufficiency="SUFFICIENT" if sr_val > 0 else "INSUFFICIENT",
            ))

        # 2. Hand Excursion Proxy / Stroke Length
        if report and getattr(report, "stroke_length", None):
            sl = report.stroke_length
            if sl.valid and sl.value is not None:
                measured_metrics.append(AICoachInputMetric(
                    metric="hand_excursion_proxy_bl",
                    value=round(float(sl.value), 2),
                    unit="body_lengths",
                    source="measured_by_existing_analysis_pipeline",
                    is_proxy=True,
                    proxy_meaning="Hand excursion proxy normalized by swimmer body length; not true physical translation",
                    scientific_validation_status=SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED,
                    evidence_sufficiency=getattr(sl, "evidence_sufficiency", "LIMITED"),
                ))

        # 3. Stroke Symmetry
        if report and getattr(report, "stroke_symmetry", None):
            sym = report.stroke_symmetry
            if sym.valid and sym.value is not None:
                measured_metrics.append(AICoachInputMetric(
                    metric="stroke_symmetry",
                    value=round(float(sym.value), 1),
                    unit="%",
                    source="measured_by_existing_analysis_pipeline",
                    is_proxy=False,
                    proxy_meaning=None,
                    scientific_validation_status=SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED,
                    evidence_sufficiency=getattr(sym, "evidence_sufficiency", "LIMITED"),
                ))

        # 4. Kick Frequency
        if report and getattr(report, "kick_frequency", None):
            kf = report.kick_frequency
            if kf.valid and kf.value is not None:
                measured_metrics.append(AICoachInputMetric(
                    metric="kick_frequency",
                    value=round(float(kf.value), 1),
                    unit="kpm",
                    source="measured_by_existing_analysis_pipeline",
                    is_proxy=False,
                    proxy_meaning=None,
                    scientific_validation_status=SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED,
                    evidence_sufficiency=getattr(kf, "evidence_sufficiency", "LIMITED"),
                ))

        # 5. Cycle Duration
        stats = getattr(analysis_result, "stroke_statistics", None)
        if stats and stats.average_cycle_duration_ms > 0:
            measured_metrics.append(AICoachInputMetric(
                metric="average_cycle_duration_ms",
                value=round(float(stats.average_cycle_duration_ms), 1),
                unit="ms",
                source="measured_by_existing_analysis_pipeline",
                is_proxy=False,
                proxy_meaning=None,
                scientific_validation_status=SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED,
                evidence_sufficiency="SUFFICIENT",
            ))

        # Reliability info
        reliability = getattr(analysis_result, "reliability", None)
        rel_score = reliability.analysis_reliability_score if reliability else 100.0
        rel_level = reliability.analysis_reliability_level if reliability else "High"
        rel_reasons = list(reliability.reasons) if reliability and reliability.reasons else []

        # Consistency info
        consistency = getattr(analysis_result, "consistency", None)
        cons_warnings = list(consistency.warnings) if consistency and consistency.warnings else []
        cons_failed = list(consistency.failed_rules) if consistency and consistency.failed_rules else []

        # Benchmark info (only authorized summary comparisons if present)
        benchmark_comparisons = None
        bm = getattr(analysis_result, "benchmark_result", None)
        if bm and getattr(bm, "comparisons", None):
            benchmark_comparisons = {}
            for k, comp in bm.comparisons.items():
                if hasattr(comp, "percentile"):
                    benchmark_comparisons[k] = {
                        "percentile": round(float(comp.percentile), 1),
                        "classification": getattr(comp, "tier", "Average"),
                    }

        # Demographic level (anonymous context only)
        swimming_level = None
        if athlete_profile and getattr(athlete_profile, "swimming_level", None):
            swimming_level = str(athlete_profile.swimming_level)

        return AICoachInputPayload(
            selected_stroke=selected_stroke,
            measured_metrics=measured_metrics,
            reliability_score=round(float(rel_score), 1),
            reliability_level=rel_level,
            reliability_reasons=rel_reasons,
            consistency_warnings=cons_warnings,
            consistency_failed_rules=cons_failed,
            benchmark_comparisons=benchmark_comparisons,
            swimming_level=swimming_level,
            scientific_validation_status=SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED,
        )


class AICoachResponseParser:
    """Parses and strictly validates the JSON response from the LLM."""

    @staticmethod
    def parse_and_validate(raw_text: str, model_name: str = "", provider_name: str = "huggingface") -> AICoachFeedback:
        """Extracts JSON block, parses, and validates schema compliance."""
        if not raw_text or not raw_text.strip():
            raise ValueError("Empty response received from model.")

        text = raw_text.strip()

        # Strip markdown fences if present
        json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(json_pattern, text)
        if match:
            text = match.group(1).strip()
        else:
            # Look for outermost JSON object brackets
            start_idx = text.find("{")
            end_idx = text.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                text = text[start_idx:end_idx + 1]

        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Parsed JSON root is not an object/dict.")

        # Validate required fields
        required_fields = ["summary", "strengths", "areas_for_improvement", "coach_recommendations", "metric_interpretations", "limitations"]
        for field_name in required_fields:
            if field_name not in data:
                raise ValueError(f"Missing required field in AI Coach response: '{field_name}'.")

        data["provider"] = provider_name
        data["model"] = model_name
        data["status"] = "success"
        data["disclaimer"] = DEFAULT_AI_COACH_DISCLAIMER

        return AICoachFeedback.from_dict(data)


def generate_safe_fallback(payload: AICoachInputPayload, error_reason: str, provider_name: str = "fallback") -> AICoachFeedback:
    """
    Generates a deterministic rule-based coaching interpretation fallback.
    Guarantees analysis results are never lost and measurements are never corrupted.
    """
    stroke = payload.selected_stroke
    summary = f"Rule-based coaching observation for {stroke} technique. Automated LLM interpretation is currently unavailable ({error_reason})."

    strengths = []
    areas_for_improvement = []
    coach_recommendations = []
    interpretations = []

    # Derive safe, factual observations strictly from measured metrics
    for m in payload.measured_metrics:
        val_str = f"{m.value} {m.unit}" if m.value is not None else "N/A"
        evidence = "measured" if m.value is not None and not m.is_proxy else "limited"

        if m.metric == "stroke_rate" and m.value:
            if m.value >= 30 and m.value <= 55:
                strengths.append(f"Stroke cadence ({val_str}) is within typical operational swimming ranges.")
            interpretations.append(MetricInterpretation(
                metric="stroke_rate",
                interpretation=f"Cadence measured at {val_str}.",
                evidence_level=evidence,
            ))
        elif m.metric == "hand_excursion_proxy_bl" and m.value:
            interpretations.append(MetricInterpretation(
                metric="hand_excursion_proxy_bl",
                interpretation=f"Normalized hand excursion proxy measured at {val_str} (proxy for stroke length; not physical translation).",
                evidence_level="limited",
            ))
        elif m.metric == "stroke_symmetry" and m.value:
            if m.value >= 90:
                strengths.append(f"Bilateral stroke symmetry ({val_str}) demonstrates balanced propulsion.")
            else:
                areas_for_improvement.append(f"Stroke symmetry ({val_str}) indicates minor bilateral asymmetry between left and right arm strokes.")
                coach_recommendations.append("Focus on single-arm isolate drills to balance stroke pulling depth and tempo.")
            interpretations.append(MetricInterpretation(
                metric="stroke_symmetry",
                interpretation=f"Symmetry measured at {val_str}.",
                evidence_level=evidence,
            ))

    if not coach_recommendations:
        coach_recommendations.append("Maintain consistent catch mechanics and perform distance-per-stroke drill sets.")

    limitations = [
        f"Scientific validation status remains: {SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED}.",
        "Measurements derived from 2D monocular video via MediaPipe Tasks API.",
        "Hand excursion proxy does not represent true center-of-mass physical distance.",
    ]
    if payload.reliability_level != "High":
        limitations.append(f"Analysis reliability is flagged as {payload.reliability_level}: {', '.join(payload.reliability_reasons)}.")

    return AICoachFeedback(
        summary=summary,
        strengths=strengths if strengths else ["Steady stroke execution detected across analyzed cycles."],
        areas_for_improvement=areas_for_improvement if areas_for_improvement else ["Continue monitoring cycle consistency."],
        coach_recommendations=coach_recommendations,
        metric_interpretations=interpretations,
        limitations=limitations,
        disclaimer=DEFAULT_AI_COACH_DISCLAIMER,
        provider=provider_name,
        status="fallback",
        error_message=error_reason,
    )


class AICoachProvider(ABC):
    """Abstract interface for AI coaching interpretation providers."""

    @abstractmethod
    def generate_interpretation(self, payload: AICoachInputPayload) -> AICoachFeedback:
        """Generate structured coaching feedback from the input payload."""
        pass


class DisabledAICoachProvider(AICoachProvider):
    """Provider used when AI Coach is disabled in configuration."""

    def generate_interpretation(self, payload: AICoachInputPayload) -> AICoachFeedback:
        return AICoachFeedback(
            summary="AI Coach interpretation is disabled. Enable in configuration (SWIM_ANALYZER_AI_COACH_ENABLED=true) to activate.",
            strengths=[],
            areas_for_improvement=[],
            coach_recommendations=[],
            metric_interpretations=[],
            limitations=[f"Scientific validation status: {SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED}."],
            disclaimer=DEFAULT_AI_COACH_DISCLAIMER,
            provider="disabled",
            status="disabled",
            error_message="AI Coach disabled via configuration.",
        )


class MockAICoachProvider(AICoachProvider):
    """Deterministic provider for testing and offline development."""

    def __init__(self, model_name: str = "mock-qwen-2.5"):
        self.model_name = model_name

    def generate_interpretation(self, payload: AICoachInputPayload) -> AICoachFeedback:
        interpretations = []
        for m in payload.measured_metrics:
            interpretations.append(MetricInterpretation(
                metric=m.metric,
                interpretation=f"Standard test interpretation for {m.metric} with measured value {m.value} {m.unit}.",
                evidence_level="measured" if not m.is_proxy else "limited",
            ))

        return AICoachFeedback(
            summary=f"Mock AI coaching assessment for {payload.selected_stroke}. Effective cadence and stroke mechanics observed.",
            strengths=["Consistent catch-phase initiation", "Stable torso alignment"],
            areas_for_improvement=["Optimize elbow recovery elevation", "Enhance kick timing synchronization"],
            coach_recommendations=[
                "High-elbow catch drill with swimmer focus on fingertip water entry.",
                "Bilateral kick-timing sets with kickboard.",
            ],
            metric_interpretations=interpretations,
            limitations=[
                f"Scientific validation status: {SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED}.",
                "Monocular 2D pose detection bounds accuracy; proxy metrics reflect planar hand excursions.",
            ],
            disclaimer=DEFAULT_AI_COACH_DISCLAIMER,
            provider="mock",
            model=self.model_name,
            status="success",
        )


class HuggingFaceProvider(AICoachProvider):
    """
    Hugging Face Inference Provider.
    Queries Hugging Face Serverless / Inference API using lightweight HTTP requests.
    Supports Qwen/Qwen2.5-1.5B-Instruct and compatible instruction models.
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-1.5B-Instruct",
        token: str = "",
        timeout_seconds: float = 20.0,
        api_url: str = "",
    ):
        self.model_name = model_name
        self.token = token.strip() if token else ""
        self.timeout_seconds = max(5.0, float(timeout_seconds))
        # Support custom API URL or standard HF router / model inference endpoint
        if api_url and api_url.strip():
            self.api_url = api_url.strip()
        else:
            self.api_url = f"https://api-inference.huggingface.co/models/{self.model_name}"

    def _build_user_message(self, payload: AICoachInputPayload) -> str:
        """Constructs the user message string containing structured JSON input."""
        payload_json = json.dumps(payload.to_dict(), indent=2)
        return (
            "Analyze the following swimming performance payload and provide structured coaching interpretation in valid JSON:\n\n"
            f"{payload_json}\n\n"
            "Ensure output is valid JSON strictly matching the specified schema."
        )

    def generate_interpretation(self, payload: AICoachInputPayload) -> AICoachFeedback:
        """Executes the request against Hugging Face with robust failure handling."""
        if not self.token:
            logger.info("Hugging Face token not configured. Falling back to deterministic rule-based interpretation.")
            return generate_safe_fallback(payload, "Hugging Face token is missing or not configured.", provider_name="huggingface")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        user_content = self._build_user_message(payload)

        # Standard Hugging Face text generation / chat payload
        # For instruction-tuned models on api-inference
        request_body = {
            "inputs": f"<|im_start|>system\n{AI_COACH_SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n{user_content}<|im_end|>\n<|im_start|>assistant\n",
            "parameters": {
                "max_new_tokens": 1024,
                "temperature": 0.2,
                "return_full_text": False,
            },
        }

        try:
            logger.info(f"Sending coaching interpretation request to Hugging Face model: {self.model_name}")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=request_body,
                timeout=self.timeout_seconds,
            )

            # Handle status codes safely without exposing token
            if response.status_code == 401 or response.status_code == 403:
                logger.warning("Hugging Face authentication failed (invalid or expired token).")
                return generate_safe_fallback(payload, "Authentication failed (invalid Hugging Face token).", provider_name="huggingface")
            elif response.status_code == 429:
                logger.warning("Hugging Face API rate limit reached.")
                return generate_safe_fallback(payload, "Hugging Face rate limit reached.", provider_name="huggingface")
            elif response.status_code == 503:
                logger.warning("Hugging Face model is loading or temporarily unavailable.")
                return generate_safe_fallback(payload, "Hugging Face model is loading or temporarily unavailable.", provider_name="huggingface")
            elif response.status_code != 200:
                logger.warning(f"Hugging Face API returned HTTP status {response.status_code}.")
                return generate_safe_fallback(payload, f"Hugging Face API error (HTTP {response.status_code}).", provider_name="huggingface")

            resp_json = response.json()
            raw_text = ""
            if isinstance(resp_json, list) and len(resp_json) > 0 and isinstance(resp_json[0], dict):
                raw_text = resp_json[0].get("generated_text", "")
            elif isinstance(resp_json, dict):
                # Chat completions format
                if "choices" in resp_json and len(resp_json["choices"]) > 0:
                    raw_text = resp_json["choices"][0].get("message", {}).get("content", "")
                else:
                    raw_text = resp_json.get("generated_text", "")

            # Parse and validate structured output
            try:
                feedback = AICoachResponseParser.parse_and_validate(raw_text, model_name=self.model_name, provider_name="huggingface")
                return feedback
            except (ValueError, json.JSONDecodeError) as parse_err:
                logger.warning(f"Failed to parse Hugging Face response as JSON schema: {parse_err}")
                return generate_safe_fallback(payload, f"Malformed model response ({parse_err}).", provider_name="huggingface")

        except requests.exceptions.Timeout:
            logger.warning(f"Hugging Face request timed out after {self.timeout_seconds} seconds.")
            return generate_safe_fallback(payload, f"Request timed out after {self.timeout_seconds}s.", provider_name="huggingface")
        except requests.exceptions.RequestException as req_err:
            logger.warning(f"Hugging Face connection or network error: {req_err}")
            return generate_safe_fallback(payload, "Network connection error.", provider_name="huggingface")
        except Exception as e:
            logger.error(f"Unexpected error in Hugging Face provider: {e}")
            return generate_safe_fallback(payload, "Unexpected provider error.", provider_name="huggingface")


class AICoachService:
    """
    High-level orchestrator service for the AI Coach layer.
    Manages active provider, payload transformation, and execution.
    """

    def __init__(self, provider: Optional[AICoachProvider] = None):
        if provider is not None:
            self.provider = provider
        else:
            self.provider = self._create_provider_from_config()

    def _create_provider_from_config(self) -> AICoachProvider:
        """Instantiates the appropriate provider according to current configuration."""
        if not config.ai_coach_enabled:
            return DisabledAICoachProvider()

        prov_type = config.ai_coach_provider.lower().strip()
        if prov_type == "mock":
            return MockAICoachProvider(model_name=config.ai_coach_hf_model)
        elif prov_type == "disabled":
            return DisabledAICoachProvider()
        else:
            # Default to Hugging Face
            return HuggingFaceProvider(
                model_name=config.ai_coach_hf_model,
                token=config.ai_coach_hf_token,
                timeout_seconds=config.ai_coach_hf_timeout_seconds,
                api_url=config.ai_coach_hf_api_url,
            )

    def build_payload(self, analysis_result: AnalysisResult, athlete_profile: Optional[Any] = None) -> AICoachInputPayload:
        """Constructs input payload for the AI Coach."""
        return AICoachPayloadBuilder.build(analysis_result, athlete_profile=athlete_profile)

    def generate_coaching_feedback(
        self,
        analysis_result: AnalysisResult,
        athlete_profile: Optional[Any] = None,
    ) -> AICoachFeedback:
        """
        Generates structured coaching feedback and attaches it to analysis_result.
        Original analysis results and measured metrics are never altered.
        """
        payload = self.build_payload(analysis_result, athlete_profile=athlete_profile)
        feedback = self.provider.generate_interpretation(payload)
        
        # Attach to analysis_result for UI access and export
        analysis_result.ai_coach_feedback = feedback
        return feedback
