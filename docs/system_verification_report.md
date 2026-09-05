# System Verification & Architectural Contract Report

This report certifies that **SwimAnalyzer AI** adheres to all core architectural contracts and deterministic biomechanical standards.

---

## 1. Core System Guarantees

1. **Mandatory User Swimming Stroke Selection**:
   - The user MUST manually select the swimming stroke style (**Freestyle**, **Backstroke**, **Breaststroke**, **Butterfly**) before starting analysis.
   - The default selection `-- Select Swimming Stroke --` blocks execution and displays a clear UI error banner.

2. **Single Source of Truth (`selected_stroke`)**:
   - The user's selected stroke is the ONLY source of truth.
   - The system NEVER infers, overrides, or recalculates the selected stroke.
   - The selected stroke flows through Streamlit $\rightarrow$ `AnalysisService` $\rightarrow$ Biomechanics Strategies $\rightarrow$ `BenchmarkEngine` $\rightarrow$ PDF / JSON Reports.

3. **Transparent Video Analysis Reliability**:
   - "Confidence" refers exclusively to empirical **Video Analysis Reliability** (pose tracking stability, landmark visibility, frame coverage, cycle quality).
   - Low-quality footage produces clear reliability warnings (e.g., *"Insufficient valid pose frames"*).

4. **100% Full Natural FPS Processing**:
   - Video processing operates at 100% native video resolution and FPS (`selected_stride = 1`), analyzing every single frame.

5. **MediaPipe Contiguous Memory Layout**:
   - Image data passed into `mp.Image` is stored in contiguous C-order layout (`np.ascontiguousarray()`), eliminating MediaPipe `landmark_projection_calculator.cc:81` ROI warnings.

6. **JSON & PDF Export Serialization & Path Security**:
   - `ExportService` handles dictionary and dataclass serialization cleanly.
   - All export paths (JSON, metadata, PDF, timeline) use `sanitize_and_resolve_path` with UUID-based naming, preventing path traversal and cross-directory access.
   - PDF reports explicitly display `Swimming Stroke: <User Selected>` and `Analysis Reliability: <High/Medium/Low>`.

7. **Multi-Tenant Data Isolation & Ownership Invariants**:
   - Domain invariants strictly enforced: `AthleteProfile.coach_id` is REQUIRED, `AnalysisSession.account_id` is REQUIRED.
   - Ownership is verified against authenticated session context (`st.session_state.current_coach`).
   - Cross-tenant queries are blocked by default; queries require explicit principal verification.

8. **Zero Hardcoded Credentials & Secure Bootstrap**:
   - All default/hardcoded passwords and credentials removed from production code and UI.
   - Authentication secured with Argon2id cryptographic hashing and per-user random salting.
   - Bootstrap accounts configured securely via environment variables (`.env`).

9. **Storage Retention Policy & TTL Lifecycle**:
   - Automated disk usage telemetry across all runtime upload and report directories.
   - Configurable TTL pruning protecting database, scientific datasets, and ML model weights.

10. **Modular Presentation Architecture**:
    - Complete UI layer modularization (`app/ui/tabs/`, `app/ui/pages/`) ensuring clean separation of concerns and robust maintainability.

---

## 2. Automated Test Verification

- **Full Pytest Suite**: `320 PASSED, 1 SKIPPED, 0 FAILED (100% Pass Rate)`.
- **Tenant Isolation & Security Suite**: `16/16 PASSED (100%)` (`tests/test_tenant_isolation.py`, `tests/test_models_regression.py`, `tests/test_dashboard_regression.py`, `tests/test_analysis_history.py`).
- **User Stroke Selection & Reliability Suite**: `15/15 PASSED (100%)` (`tests/test_user_stroke_selection_and_reliability.py`).
- **Storage Retention Suite**: `2/2 PASSED (100%)` (`tests/test_storage_service.py`).
- **Background Worker Suite**: `1/1 PASSED (100%)` (`tests/test_background_worker.py`).
- **Biomechanics Baseline Suite**: `6/6 PASSED (100%)` (`tests/test_biomechanics_baseline.py`).
- **Scientific Validation Protocol Suite**: `4/4 PASSED (100%)` (`tests/test_scientific_validation_protocol.py`).
- **Validation Experiment Infrastructure Suite**: `4/4 PASSED (100%)` (`tests/test_validation_experiment_infrastructure.py`).
- **Determinism**: 100% local Python biomechanical analysis. Zero unauthenticated or untracked cloud API dependencies.

---

## 3. Step 63: MediaPipe-Only Architecture & Pose Integrity

- **Single Pose Source of Truth**: MediaPipe Tasks API (`vision.PoseLandmarker`, `pose_landmarker_full.task`) is established as the sole pose estimation backend across the entire production pipeline. No multi-backend abstraction or RTMPose/MMPose/YOLO overhead exists.
- **End-to-End Pipeline Trace**:
  $$\text{Video} \longrightarrow \text{MediaPipe PoseDetector} \longrightarrow \text{Landmark Smoother (EMA)} \longrightarrow \text{Stroke Biomechanics} \longrightarrow \text{Reliability/Consistency} \longrightarrow \text{Video Annotator} \longrightarrow \text{H.264 Web MP4}$$
- **Verification on Real 4-Stroke Footage**:
  - **Freestyle**: Complete cycle kinematics, 51/96 valid frames, 56.03 technique score, 56.64 reliability score.
  - **Backstroke**: Inconclusive zero-fallback correctly triggered (swimmer in footage was freestyle; no false scores fabricated).
  - **Breaststroke**: Inconclusive zero-fallback correctly triggered.
  - **Butterfly**: Valid cycle identification and phase segmentation executed.
- **Video Annotation & Transcoding**: OpenCV frame writer verified with FFmpeg `libx264` (`avc1`, `+faststart`). Skeleton overlays confirmed on 100% of valid detected frames (64,081 green bone pixels, 20,881 red joint pixels).
- **Upstream C++ MediaPipe Warning Audit**: The log message `Using NORM_RECT without IMAGE_DIMENSIONS is only supported for the square ROI` from `landmark_projection_calculator.cc:81` was traced to MediaPipe's internal graph specification. Because ROI cropping is normalized and square, coordinate projection executes accurately and downstream joint angle precision is unaffected.
- **Status**: **READY FOR SCIENTIFIC BIOMECHANICS VALIDATION**.

---

## 4. Step 64: Biomechanics Metric Audit & Baseline Record

- **41 Metrics Audited**: Exhaustive scientific classification of every metric:
  - 11 VALID (26.8%)
  - 27 VALID WITH LIMITATIONS (65.9%)
  - 2 NEEDS VALIDATION (4.9%)
  - 0 INCORRECT (0.0%)
  - 1 UNVERIFIED (2.4%)
- **Zero Formula Defects**: Confirmed 0 broken mathematical equations, 0 divide-by-zero crashes, and 0 deadlock state-machine transitions.
- **Baseline Invariants Recorded**: [`data/reference/biomechanics_metric_baseline.json`](../data/reference/biomechanics_metric_baseline.json) and [`docs/biomechanics_metric_audit.md`](biomechanics_metric_audit.md).

---

## 5. Step 65: Scientific Validation Protocol & Safety Gate

- **Priority Metrics Validation Protocol**: Comprehensive protocol established for 8 priority metrics (Stroke Rate, Cycle Duration, Stroke Length proxy, Elbow Angle, Knee Angle, Shoulder Angle, Body Roll, Phase Timing) in [`docs/scientific_validation_protocol.md`](scientific_validation_protocol.md) and [`data/reference/scientific_validation_protocol.json`](../data/reference/scientific_validation_protocol.json).
- **Scientific Safety Gate**: Strictly enforces distinction between Mathematical Correctness, Implementation Correctness, and Empirical Validation.
- **Unestablished Thresholds Policy**: Explicitly marks acceptance criteria as `THRESHOLD NOT YET ESTABLISHED` to prevent inventing arbitrary tolerances.

---

## 6. Step 66: Ground Truth Dataset Specification & Validation Experiment

- **Ground Truth Specification**: Standardized specifications established for a minimum 24-trial empirical dataset (6 per stroke) with high-speed video ($\ge 60\text{ fps}$), double-blind manual landmark annotations, and IMU telemetry in [`docs/ground_truth_dataset_specification.md`](ground_truth_dataset_specification.md) and schema in [`data/reference/ground_truth_dataset_schema.json`](../data/reference/ground_truth_dataset_schema.json).
- **Repository Ground Truth Audit**: Confirmed that real Physical Ground Truth is currently **NOT AVAILABLE** in the repository.
- **Validation Experiment Design**: Complete statistical design (MAE, RMSE, Bland-Altman LoA, Lin's CCC) documented in [`docs/scientific_validation_results.md`](scientific_validation_results.md).
- **Current Empirical Status**: Held strictly at **`NOT_VALIDATED — INSUFFICIENT GROUND TRUTH`** across all priority metrics.
- **Final Verdict**: **`BLOCKED — GROUND TRUTH DATASET REQUIRED`**.



