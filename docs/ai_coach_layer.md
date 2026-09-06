# Optional Hugging Face AI Coach Layer (Step 71)

**Document Identifier:** DOC-AI-COACH-1.0.0  
**Effective Date:** 2026-09-06  
**Status:** **EXPERIMENTAL BETA**  
**Scientific Validation Status:** **NOT_VALIDATED — INSUFFICIENT GROUND TRUTH**  
**Preferred Model:** `Qwen/Qwen2.5-1.5B-Instruct` (via Hugging Face Inference Providers Router: `https://router.huggingface.co/v1/chat/completions`)

---

## 1. Executive Summary & Core Invariants

The **AI Coach Layer** is an **optional, non-blocking interpretation subsystem** for Swim Analyzer AI. It is designed strictly to generate coach-friendly explanations, identify technique strengths, highlight technical flaws, and suggest actionable drills based upon **already-computed, structured analysis results**.

> [!IMPORTANT]
> **MANDATORY SYSTEM INVARIANTS**  
> 1. **Zero Pose / Measurement Authority:** The AI Coach does **not** perform pose estimation, computer vision, frame tracking, or kinematic calculations. MediaPipe Tasks API remains the **sole authorized pose backend**.
> 2. **Immutability of Measured Biomechanics:** The LLM cannot calculate, overwrite, correct, infer, or alter numerical metrics produced by the frozen pipeline (`db33130abb4af653ccacc4bec872be25233b59e4`).
> 3. **Non-Blocking / Zero Core Dependency:** Video analysis runs to 100% completion regardless of whether the AI Coach is enabled, disabled, unauthenticated, rate-limited, timed out, or offline.
> 4. **Scientific Safety Firewall:** The AI Coach cannot claim scientific validation. The scientific status remains strictly:  
>    $$\textbf{NOT\_VALIDATED — INSUFFICIENT GROUND TRUTH}$$
> 5. **Zero Video / Secret Ingestion:** The LLM never receives raw video bytes, database internals, authentication credentials, or cross-tenant records.

---

## 2. Architecture & Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                       INPUT VIDEO                           │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│       FROZEN MEDIAPIPE MEASUREMENT PIPELINE (db33130)       │
│  - MediaPipe Tasks API (PoseLandmarker)                     │
│  - Cycle segmentation & phase state machines                │
│  - Joint angle calculations & temporal smoothing            │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│          RELIABILITY & CONSISTENCY SAFETY GATES             │
│  - Video Quality Assessment (VQA)                           │
│  - Video Analysis Reliability Engine                        │
│  - 7-Rule Scientific Consistency Validator                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│             STRUCTURED ANALYSIS RESULT                      │
│  - stroke_rate, hand_excursion_proxy_bl, cycle_duration     │
│  - stroke_symmetry, kick_frequency, joint angles            │
│  - reliability_score, consistency_warnings                  │
└───────────────┬──────────────────────────────┬──────────────┘
                │                              │
                │ (Normal Direct Flow)         │ (Optional Interpretation Flow)
                │                              ▼
                │               ┌─────────────────────────────┐
                │               │    AI COACH ADAPTER LAYER   │
                │               │   (AICoachPayloadBuilder)   │
                │               └──────────────┬──────────────┘
                │                              │
                │                              ▼
                │               ┌─────────────────────────────┐
                │               │    HUGGING FACE PROVIDER    │
                │               │ (Qwen/Qwen2.5-1.5B-Instruct)│
                │               │  * Safe Fallback on Timeout │
                │               └──────────────┬──────────────┘
                │                              │
                ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 STREAMLIT PRESENTATION LAYER                │
│  - Original Measured Metrics (Tabs: Biomech, 3D, Charts)    │
│  - AI Coaching Feedback Tab ("🤖 AI Coach")                 │
│  - Mandatory Scientific Disclaimer                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Configuration & Environment Variables

The AI Coach layer is configured strictly via environment variables (or `.env` file):

| Variable | Default Value | Allowed Values | Description |
| :--- | :--- | :--- | :--- |
| `SWIM_ANALYZER_AI_COACH_ENABLED` | `false` | `true`, `false` | Master switch. When `false`, no external requests are made. |
| `SWIM_ANALYZER_AI_PROVIDER` | `huggingface` | `huggingface`, `disabled`, `mock` | Active provider implementation. |
| `SWIM_ANALYZER_HF_MODEL` | `Qwen/Qwen2.5-1.5B-Instruct` | Valid HF model ID | Target instruction model on Hugging Face. |
| `SWIM_ANALYZER_HF_TOKEN` | `""` | User Token (`hf_...`) | Read token for Hugging Face Inference API. Never commit. |
| `SWIM_ANALYZER_HF_TIMEOUT_SECONDS`| `20.0` | Positive float ($\ge 5.0$) | HTTP timeout for inference requests. |
| `SWIM_ANALYZER_HF_API_URL` | `https://router.huggingface.co/v1/chat/completions` | Valid URL | Hugging Face Inference Providers router endpoint or custom endpoint. |

---

## 4. Input Payload Specification (`AICoachInputPayload`)

The payload builder (`AICoachPayloadBuilder.build`) compiles an immutable JSON object containing only safe, measured data:

```json
{
  "selected_stroke": "Freestyle",
  "measured_metrics": [
    {
      "metric": "stroke_rate",
      "value": 41.5,
      "unit": "spm",
      "source": "measured_by_existing_analysis_pipeline",
      "is_proxy": false,
      "proxy_meaning": null,
      "scientific_validation_status": "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH",
      "evidence_sufficiency": "SUFFICIENT"
    },
    {
      "metric": "hand_excursion_proxy_bl",
      "value": 0.88,
      "unit": "body_lengths",
      "source": "measured_by_existing_analysis_pipeline",
      "is_proxy": true,
      "proxy_meaning": "Hand excursion proxy normalized by swimmer body length; not true physical translation",
      "scientific_validation_status": "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH",
      "evidence_sufficiency": "LIMITED"
    }
  ],
  "reliability_score": 92.5,
  "reliability_level": "High",
  "reliability_reasons": [],
  "consistency_warnings": [],
  "consistency_failed_rules": [],
  "benchmark_comparisons": {
    "stroke_rate": {"percentile": 68.4, "classification": "Above Average"}
  },
  "swimming_level": "Senior Club",
  "scientific_validation_status": "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"
}
```

---

## 5. Output Format Specification (`AICoachFeedback`)

The LLM is prompted to respond strictly in valid JSON matching this schema:

```json
{
  "summary": "Swimmer exhibits steady freestyle cadence with balanced pull symmetry.",
  "strengths": [
    "High stroke cadence within competitive range (41.5 spm).",
    "Bilateral arm pull symmetry exceeds 94%."
  ],
  "areas_for_improvement": [
    "Normalized hand excursion proxy indicates shortened pull-through phase."
  ],
  "coach_recommendations": [
    "Execute 6x50m catch-up drill focusing on full extension past the hip.",
    "Fingertip drag drill to encourage high-elbow recovery."
  ],
  "metric_interpretations": [
    {
      "metric": "stroke_rate",
      "interpretation": "Stroke rate of 41.5 spm represents a strong race tempo.",
      "evidence_level": "measured"
    },
    {
      "metric": "hand_excursion_proxy_bl",
      "interpretation": "Proxy indicates hand trajectory reaches 0.88 body lengths.",
      "evidence_level": "limited"
    }
  ],
  "limitations": [
    "Scientific validation status: NOT_VALIDATED — INSUFFICIENT GROUND TRUTH.",
    "Monocular camera setup restricts 3D depth measurements."
  ]
}
```

---

## 6. Provider Abstraction & Fallback Architecture

To ensure zero downtime, the provider architecture implements graceful degradation:

```
┌─────────────────────────────────────────────────────────────┐
│                     AICoachProvider (ABC)                   │
└───────┬───────────────────────────────┬─────────────────────┘
        │                               │
┌───────▼───────────────┐       ┌───────▼─────────────────────┐
│  HuggingFaceProvider  │       │   DisabledAICoachProvider   │
└───────┬───────────────┘       └─────────────────────────────┘
        │ (Failure / Timeout / No Token)
        ▼
┌─────────────────────────────────────────────────────────────┐
│               generate_safe_fallback()                      │
│  - Deterministic rule-based observations from metrics       │
│  - Preserves 100% of underlying video analysis data         │
│  - Flags status="fallback" with clear explanation           │
└─────────────────────────────────────────────────────────────┘
```

### Failure Modes Handled:
1. **Disabled in config:** Returns clean `status="disabled"` without network call.
2. **Missing token:** Logs info, immediately yields rule-based fallback.
3. **HTTP 401/403 (Invalid Token):** Trapped cleanly; logs warning without leaking token.
4. **HTTP 404 (Model Unavailable):** Trapped cleanly; yields fallback explaining model is unavailable.
5. **HTTP 429 (Rate Limit):** Yields fallback with rate-limit notice.
6. **HTTP 5xx (Provider Server Error):** Trapped cleanly; yields fallback explaining temporary provider error.
7. **Network Timeout / Connection Error:** Times out after `timeout_seconds`, yields fallback.
8. **Malformed JSON / Schema Mismatch:** Trapped by `AICoachResponseParser`, yields safe fallback.

---

## 7. Tenant Isolation & Privacy

1. **Zero Database Querying:** The AI Coach layer has no direct access to the database or repository layer. It accepts only the explicit in-memory `AnalysisResult` and optional profile passed to it.
2. **Zero PII Transmission:** Real names, email addresses, coach IDs, and video file system paths are stripped. Only anonymous athletic context (`selected_stroke`, `swimming_level`) and measured values are sent.
3. **Zero Secret Logging:** Tokens and authorization headers are never written to log files.
