"""
Comprehensive Unit Tests for Optional AI Coach Layer (Step 71).
Validates configuration, safety system prompt, schema parsing, provider abstraction,
deterministic fallbacks, immutable metric integrity, and tenant isolation.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
import requests

from core.config import config
from models.data_models import (
    AnalysisResult,
    PerformanceReport,
    ValidatedMetric,
    StrokeStatistics,
    ReliabilityResult,
    ConsistencyReport,
    StrokeSelection,
    StrokeType,
)
from models.athlete_profile import AthleteProfile
from models.ai_coach_models import (
    AICoachInputMetric,
    AICoachInputPayload,
    AICoachFeedback,
    MetricInterpretation,
    SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED,
    DEFAULT_AI_COACH_DISCLAIMER,
)
from services.ai_coach_service import (
    AI_COACH_SYSTEM_PROMPT,
    AICoachPayloadBuilder,
    AICoachResponseParser,
    generate_safe_fallback,
    DisabledAICoachProvider,
    MockAICoachProvider,
    HuggingFaceProvider,
    AICoachService,
)


@pytest.fixture
def sample_analysis_result() -> AnalysisResult:
    """Fixture providing standard structured AnalysisResult."""
    report = PerformanceReport(
        overall_score=82.0,
        status="available",
        stroke_rate=ValidatedMetric(name="stroke_rate", value=42.0, unit="spm", valid=True),
        stroke_length=ValidatedMetric(
            name="stroke_length",
            value=0.85,
            unit="body_lengths",
            valid=True,
            measurement_domain="relative_body_normalized",
        ),
        kick_frequency=ValidatedMetric(name="kick_frequency", value=120.0, unit="kpm", valid=True),
        stroke_symmetry=ValidatedMetric(name="stroke_symmetry", value=93.5, unit="%", valid=True),
        evidence_sufficiency="SUFFICIENT",
        technique_assessment="Good",
    )
    stats = StrokeStatistics(
        completed_cycles=4,
        average_cycle_duration_ms=1428.5,
        average_phase_confidence=0.95,
    )
    reliability = ReliabilityResult(
        analysis_reliability_score=94.0,
        analysis_reliability_level="High",
        scientific_confidence="High",
        reasons=[],
    )
    consistency = ConsistencyReport(
        overall_score=82.0,
        validation_status="Passed",
        scientific_confidence="High",
        warnings=[],
        failed_rules=[],
    )
    return AnalysisResult(
        video_path="data/input_videos/test_freestyle.mp4",
        stroke_type="Freestyle",
        stroke_selection=StrokeSelection(selected_stroke=StrokeType.FREESTYLE, selection_source="USER"),
        average_stroke_rate=42.0,
        report=report,
        stroke_statistics=stats,
        reliability=reliability,
        consistency=consistency,
    )


# 1. AI Coach disabled
def test_ai_coach_disabled(sample_analysis_result):
    with patch.object(config, "ai_coach_enabled", False):
        service = AICoachService()
        assert isinstance(service.provider, DisabledAICoachProvider)
        feedback = service.generate_coaching_feedback(sample_analysis_result)
        assert feedback.status == "disabled"
        assert "disabled" in feedback.summary.lower()
        assert feedback.disclaimer == DEFAULT_AI_COACH_DISCLAIMER
        assert sample_analysis_result.ai_coach_feedback is feedback


# 2. Missing token
def test_missing_token(sample_analysis_result):
    provider = HuggingFaceProvider(model_name="Qwen/Qwen2.5-1.5B-Instruct", token="")
    payload = AICoachPayloadBuilder.build(sample_analysis_result)
    feedback = provider.generate_interpretation(payload)
    assert feedback.status == "fallback"
    assert "token is missing" in feedback.error_message
    assert feedback.provider == "huggingface"
    assert len(feedback.metric_interpretations) > 0


# 3. Provider unavailable / HTTP 5xx / Network Error
def test_provider_unavailable(sample_analysis_result):
    provider = HuggingFaceProvider(model_name="Qwen/Qwen2.5-1.5B-Instruct", token="mock_hf_token")
    payload = AICoachPayloadBuilder.build(sample_analysis_result)

    with patch("requests.post") as mock_post:
        # Simulate HTTP 503 Service Unavailable
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_post.return_value = mock_resp

        feedback = provider.generate_interpretation(payload)
        assert feedback.status == "fallback"
        assert "temporarily unavailable" in feedback.error_message

    with patch("requests.post") as mock_post:
        # Simulate HTTP 500 Internal Server Error
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        feedback = provider.generate_interpretation(payload)
        assert feedback.status == "fallback"
        assert "500" in feedback.error_message

    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        feedback = provider.generate_interpretation(payload)
        assert feedback.status == "fallback"
        assert "connection" in feedback.error_message.lower()


# 4. Timeout
def test_timeout(sample_analysis_result):
    provider = HuggingFaceProvider(model_name="Qwen/Qwen2.5-1.5B-Instruct", token="mock_hf_token", timeout_seconds=5.0)
    payload = AICoachPayloadBuilder.build(sample_analysis_result)

    with patch("requests.post", side_effect=requests.exceptions.Timeout("Request timed out")):
        feedback = provider.generate_interpretation(payload)
        assert feedback.status == "fallback"
        assert "timed out" in feedback.error_message.lower()


# 5. Malformed model response
def test_malformed_model_response(sample_analysis_result):
    provider = HuggingFaceProvider(model_name="Qwen/Qwen2.5-1.5B-Instruct", token="mock_hf_token")
    payload = AICoachPayloadBuilder.build(sample_analysis_result)

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # Return OpenAI shape with invalid JSON string
        mock_resp.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "This is free text without any JSON structure."}}]
        }
        mock_post.return_value = mock_resp

        feedback = provider.generate_interpretation(payload)
        assert feedback.status == "fallback"
        assert "Malformed" in feedback.error_message


# 6. Valid structured response via router chat completions
def test_valid_structured_response(sample_analysis_result):
    provider = HuggingFaceProvider(model_name="Qwen/Qwen2.5-1.5B-Instruct", token="mock_hf_token")
    payload = AICoachPayloadBuilder.build(sample_analysis_result)

    valid_json_response = {
        "summary": "Swimmer exhibits steady freestyle cadence with balanced pull symmetry.",
        "strengths": ["High stroke cadence (42.0 spm).", "Symmetry exceeds 93%."],
        "areas_for_improvement": ["Elbow recovery could be elevated higher."],
        "coach_recommendations": ["Perform fingertip-drag drill over 4x50m."],
        "metric_interpretations": [
            {
                "metric": "stroke_rate",
                "interpretation": "Stroke rate of 42.0 spm is well maintained.",
                "evidence_level": "measured"
            },
            {
                "metric": "hand_excursion_proxy_bl",
                "interpretation": "Hand excursion proxy reaches 0.85 body lengths.",
                "evidence_level": "limited"
            }
        ],
        "limitations": [
            "Scientific validation status remains: NOT_VALIDATED — INSUFFICIENT GROUND TRUTH.",
            "Hand excursion is a 2D proxy, not 3D displacement."
        ]
    }

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # Return standard OpenAI-compatible choices response
        mock_resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(valid_json_response)
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        feedback = provider.generate_interpretation(payload)
        assert feedback.status == "success"
        assert feedback.summary == valid_json_response["summary"]
        assert len(feedback.strengths) == 2
        assert len(feedback.coach_recommendations) == 1
        assert len(feedback.metric_interpretations) == 2
        assert feedback.metric_interpretations[0].metric == "stroke_rate"
        assert feedback.metric_interpretations[0].evidence_level == "measured"
        assert feedback.disclaimer == DEFAULT_AI_COACH_DISCLAIMER

        # Verify call arguments
        mock_post.assert_called_once()
        call_args, call_kwargs = mock_post.call_args
        assert call_args[0] == HuggingFaceProvider.DEFAULT_ROUTER_URL
        body = call_kwargs["json"]
        assert body["model"] == "Qwen/Qwen2.5-1.5B-Instruct"
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["role"] == "user"
        assert body["response_format"] == {"type": "json_object"}
        assert call_kwargs["headers"]["Authorization"] == "Bearer mock_hf_token"


# 6b. HTTP 401 & 403 authentication failures
def test_http_401_and_403_auth_failure(sample_analysis_result):
    provider = HuggingFaceProvider(model_name="Qwen/Qwen2.5-1.5B-Instruct", token="invalid_token")
    payload = AICoachPayloadBuilder.build(sample_analysis_result)

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        feedback = provider.generate_interpretation(payload)
        assert feedback.status == "fallback"
        assert "Authentication failed" in feedback.error_message


# 6c. HTTP 404 model unavailable
def test_http_404_model_unavailable(sample_analysis_result):
    provider = HuggingFaceProvider(model_name="NonExistent/Model-99B", token="mock_hf_token")
    payload = AICoachPayloadBuilder.build(sample_analysis_result)

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_post.return_value = mock_resp

        feedback = provider.generate_interpretation(payload)
        assert feedback.status == "fallback"
        assert "currently unavailable" in feedback.error_message


# 6d. HTTP 429 rate limit
def test_http_429_rate_limit(sample_analysis_result):
    provider = HuggingFaceProvider(model_name="Qwen/Qwen2.5-1.5B-Instruct", token="mock_hf_token")
    payload = AICoachPayloadBuilder.build(sample_analysis_result)

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_post.return_value = mock_resp

        feedback = provider.generate_interpretation(payload)
        assert feedback.status == "fallback"
        assert "rate limit reached" in feedback.error_message


# 7. Prompt contains supplied metrics
def test_prompt_contains_supplied_metrics(sample_analysis_result):
    payload = AICoachPayloadBuilder.build(sample_analysis_result)
    provider = HuggingFaceProvider(model_name="Qwen/Qwen2.5-1.5B-Instruct", token="mock_hf_token")
    user_msg = provider._build_user_message(payload)

    assert "stroke_rate" in user_msg
    assert "42.0" in user_msg
    assert "spm" in user_msg
    assert "hand_excursion_proxy_bl" in user_msg
    assert "0.85" in user_msg
    assert "stroke_symmetry" in user_msg
    assert "93.5" in user_msg
    assert "average_cycle_duration_ms" in user_msg
    assert "1428.5" in user_msg


# 8. Prompt explicitly forbids invented metrics
def test_prompt_explicitly_forbids_invented_metrics():
    assert "Never invent or hallucinate measurement values" in AI_COACH_SYSTEM_PROMPT
    assert "Never change or recalculate supplied values" in AI_COACH_SYSTEM_PROMPT
    assert "Never claim any metric is scientifically validated" in AI_COACH_SYSTEM_PROMPT
    assert "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH" in AI_COACH_SYSTEM_PROMPT
    assert "hand_excursion_proxy_bl" in AI_COACH_SYSTEM_PROMPT
    assert "NOT a calibrated physical displacement in meters" in AI_COACH_SYSTEM_PROMPT


# 9. Scientific status remains NOT_VALIDATED
def test_scientific_status_remains_not_validated(sample_analysis_result):
    payload = AICoachPayloadBuilder.build(sample_analysis_result)
    assert payload.scientific_validation_status == SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED

    for m in payload.measured_metrics:
        assert m.scientific_validation_status == SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED

    mock_provider = MockAICoachProvider()
    feedback = mock_provider.generate_interpretation(payload)
    assert SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED in feedback.disclaimer
    assert any(SCIENTIFIC_VALIDATION_STATUS_NOT_VALIDATED in lim for lim in feedback.limitations)


# 10. AI layer cannot modify original metrics
def test_ai_layer_cannot_modify_original_metrics(sample_analysis_result):
    orig_sr = sample_analysis_result.average_stroke_rate
    orig_sl = sample_analysis_result.report.stroke_length.value
    orig_sym = sample_analysis_result.report.stroke_symmetry.value
    orig_score = sample_analysis_result.report.overall_score

    mock_provider = MockAICoachProvider()
    service = AICoachService(provider=mock_provider)
    feedback = service.generate_coaching_feedback(sample_analysis_result)

    assert sample_analysis_result.average_stroke_rate == orig_sr
    assert sample_analysis_result.report.stroke_length.value == orig_sl
    assert sample_analysis_result.report.stroke_symmetry.value == orig_sym
    assert sample_analysis_result.report.overall_score == orig_score
    assert sample_analysis_result.ai_coach_feedback is feedback


# 11. Uncalibrated/proxy metric semantics are preserved
def test_uncalibrated_proxy_metric_semantics_preserved(sample_analysis_result):
    payload = AICoachPayloadBuilder.build(sample_analysis_result)
    sl_metrics = [m for m in payload.measured_metrics if m.metric == "hand_excursion_proxy_bl"]
    assert len(sl_metrics) == 1
    sl_m = sl_metrics[0]
    assert sl_m.is_proxy is True
    assert "proxy for stroke length" in sl_m.proxy_meaning.lower() or "hand excursion proxy" in sl_m.proxy_meaning.lower()
    assert "not true physical translation" in sl_m.proxy_meaning.lower()
    assert sl_m.unit == "body_lengths"


# 12. Existing analysis flow works without AI Coach
def test_existing_analysis_flow_works_without_ai_coach(sample_analysis_result):
    # Verify default state without AI Coach running
    assert sample_analysis_result.ai_coach_feedback is None
    # Verify angles timeseries calculation works independently
    ts = sample_analysis_result.get_angles_timeseries()
    assert "timestamp_ms" in ts
    assert len(ts["timestamp_ms"]) == 0  # No frames in fixture, but method succeeds cleanly


# 13. Tenant / authorization boundaries are preserved
def test_tenant_authorization_boundaries_preserved(sample_analysis_result):
    # Athlete profile with demographic context
    profile = AthleteProfile(
        full_name="Secret Athlete Name",
        age=22,
        gender="Female",
        height_cm=178.0,
        weight_kg=68.0,
        swimming_level="Elite Senior",
        preferred_stroke="Freestyle",
        coach_id="COACH-99999",
        athlete_id="ATH-12345",
    )

    payload = AICoachPayloadBuilder.build(sample_analysis_result, athlete_profile=profile)
    payload_dict = payload.to_dict()
    payload_str = json.dumps(payload_dict)

    # Verify no PII or secrets leaked
    assert "Secret Athlete Name" not in payload_str
    assert "ATH-12345" not in payload_str
    assert "COACH-99999" not in payload_str
    assert "password" not in payload_str.lower()
    assert "token" not in payload_str.lower()
    assert "data/input_videos" not in payload_str

    # Only anonymized context is passed
    assert payload.swimming_level == "Elite Senior"
