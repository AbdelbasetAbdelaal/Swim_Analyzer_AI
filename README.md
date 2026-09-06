# 🏊 SwimAnalyzer AI — Professional Sports Analytics & Scientific Biomechanics Platform

**SwimAnalyzer AI** is a commercial-grade, peer-reviewed sports analytics and biomechanics platform built for competitive swimming coaches, biomechanists, and elite sports institutes.

It transforms raw video of swimming technique into auditable kinematic measurements (including pose-relative 3D estimates with explicit uncalibrated monocular depth caveats), reliability scores, consistency validations, population benchmark comparisons, and longitudinal progression tracking across all four competitive stroke styles (**Freestyle, Backstroke, Breaststroke, Butterfly**).

---

## 🌟 Key Features Overview

### 1. 🏊 Mandatory User Stroke Selection & Biomechanical Kinematics
- **Single Source of Truth (`selected_stroke`)**: The user MUST explicitly select the swimming stroke style (**Freestyle**, **Backstroke**, **Breaststroke**, or **Butterfly**) before starting analysis. The system default `-- Select Swimming Stroke --` blocks execution until a valid stroke is selected.
- **Zero Inferencing / Overrides**: The system never overrides, infers, or recalculates the user-selected stroke.
- **100% Full Natural Native FPS Processing**: Operates at native video resolution and 100% FPS (`selected_stride = 1`), analyzing every single frame.
- **Pose-Relative 3D Kinematics**: Calculates pose-relative 3D body roll rotation, core torsion, joint angles (elbow, knee, shoulder), stroke cycle phase segmentation, and time-in-phase breakdown. Note: MediaPipe monocular depth ($z$-axis) represents an uncalibrated relative estimate, not physical 3D metric coordinate measurements.
- **Key Metrics**:
  - **Stroke Rate (tempo)**: Cycles per minute (spm) and Hz.
  - **Stroke Length (distance per stroke)**: Distance traveled per arm cycle. Represented in physical meters (m) if calibration is available, otherwise strictly demarcated as `relative_body_normalized` (uncalibrated) to prevent domain-mismatch comparisons against metric literature.
  - **Kick Frequency**: Kick cycles per second / minute.
  - **Stroke Symmetry**: Bilateral force and velocity symmetry index (%).
  - **Pose-Relative 3D Body Roll & Core Torsion**: Rotation angles relative to water plane derived from pose landmarks.

### 2. 🔬 Transparent Video Analysis Reliability Engine
- **Decoupled Quality Model**: "Confidence" refers exclusively to empirical **Video Analysis Reliability** (pose tracking coverage, landmark visibility, temporal stability, cycle quality, measurement stability), and NEVER to stroke classification probability or physical truth.
- **Reliability Formula**:
  $$\text{Reliability} = 0.30 \cdot \text{PoseTrackingCoverage} + 0.25 \cdot \text{LandmarkVisibility} + 0.20 \cdot \text{TemporalStability} + 0.15 \cdot \text{CycleQuality} + 0.10 \cdot \text{MeasurementStability}$$
- **Decoupled Validation Boundary**: Video tracking reliability reflects algorithmic signal stability; it explicitly does NOT claim scientific validation (`scientific_validation_status = "NOT_VALIDATED — INSUFFICIENT GROUND TRUTH"`).
- **Data Quality Warnings**: Automatically detects low-quality footage (insufficient valid frames, low landmark visibility, swimmer leaving frame) and logs explicit quality warnings.

### 3. 🛡️ Video Quality Assessment (VQA) & Safety Engine
- **VQA Pre-check**: Evaluates resolution, frame rate, lighting, occlusion, and camera stability.
- **Scientific Consistency Validator**: Enforces 7 mathematical rules to ensure scientific trustworthiness.

### 4. 👥 Multi-Tenant Isolation & Roster Management
- **Strict Tenant Isolation**: Enforces strict domain invariants (`AthleteProfile.coach_id` required, `AnalysisSession.account_id` required).
- **Authenticated Access Control**: All session and roster queries require authenticated principal context with deny-by-default cross-tenant protection.
- **Longitudinal Progression Tracking**: Tracks scores, metrics, and technical flaw resolution over time per athlete.
- **Session-to-Session Comparison**: Side-by-side comparison of baseline vs recent sessions.

### 5. 🔒 Path Traversal & File Export Security
- **Sanitized Paths**: All uploads and export endpoints (JSON, PDF, Video) use `sanitize_and_resolve_path` with UUID-based filenames and containment checks.
- **Zero Hardcoded Secrets**: Production secrets and bootstrap admin credentials are parameterized via `.env`.

### 6. 🔬 Literature Provenance & Scientific Benchmarks
- **100% Traceable Literature**: Population benchmark values link directly to peer-reviewed studies (Craig & Pendergast 1979, Psycharakis & Sanders 2008/2010, Gonjo et al. 2020, Leblanc et al. 2005).
- **Demographic Compatibility Guard**: Suppresses percentile math for non-compatible cohorts (Youth, Female, Masters) with clear warning banners.

### 7. 📄 Export & Reporting System
- **PDF Report Exporter**: Generates detailed single-session and athlete summary PDF reports displaying `Swimming Stroke: <User Selected>` and `Analysis Reliability`.
- **JSON Data Exports**: Exports structured JSON report, metadata, and frame-by-frame timelines with guaranteed serialization.

### 8. 🧹 Storage Retention & Automated Disk Cleanup
- **Real-Time Storage Telemetry**: Tracks disk space usage across upload and export directories (`input_videos/`, `output_videos/`, `reports/`, `pdf_reports/`).
- **Configurable TTL Cleanup**: Automatically or manually prunes user-generated runtime files older than a chosen retention window (default 7 days) while strictly protecting machine learning models, reference benchmarks, and databases.

### 9. ⚡ Asynchronous Video Processing Engine
- **Non-Blocking Background Worker**: Runs long-duration video processing jobs in independent background threads with real-time status and progress callbacks.

### 10. 🎯 Single-Source MediaPipe Pose Architecture (Step 63)
- **Single Source of Pose Truth**: The production pipeline exclusively employs the **MediaPipe Tasks API (`vision.PoseLandmarker`)** with `pose_landmarker_full.task`.
- **Zero Incompatible Multi-Backends**: Secondary pose backends (RTMPose, MMPose, YOLO Pose) have been eliminated to ensure predictable deterministic execution, native contiguous memory alignment, and zero multi-backend drift.

### 11. 📐 Audited Biomechanics Metric Engine & Baseline (Step 64)
- **41 Inventoried Biomechanical Metrics**: Complete audit across all 4 competitive strokes (Freestyle, Backstroke, Breaststroke, Butterfly), joint angles (elbow, knee, shoulder, hip), 3D spatial roll/torsion, and state-machine phase timing.
- **Machine-Readable Baseline**: Standardized catalog recorded in [`data/reference/biomechanics_metric_baseline.json`](data/reference/biomechanics_metric_baseline.json) and detailed in [`docs/biomechanics_metric_audit.md`](docs/biomechanics_metric_audit.md).
- **0 Broken Formulas**: All mathematical vector operations, state machines, and angle derivations verified with zero crashes or NaN edge-cases.

### 12. 🛡️ Scientific Validation Protocol & Safety Gate (Steps 65 & 66)
- **Mandatory Safety Rule**: Clear separation between *Mathematical Correctness*, *Implementation Correctness*, and *Empirical Scientific Validation*. No metric is claimed as "scientifically validated" without paired physical ground truth.
- **Unestablished Thresholds Policy**: Whenever empirical literature or dataset evidence is missing, acceptance criteria are strictly marked `THRESHOLD NOT YET ESTABLISHED`.
- **Ground Truth Specification**: Standardized specifications for collecting 24 calibrated high-speed video trials ($\ge 60\text{ fps}$) paired with double-blind manual landmark annotations and IMU telemetry ([`docs/ground_truth_dataset_specification.md`](docs/ground_truth_dataset_specification.md) and [`data/reference/ground_truth_dataset_schema.json`](data/reference/ground_truth_dataset_schema.json)).
- **Current Empirical Status**: Rigorously held at **`NOT_VALIDATED — INSUFFICIENT GROUND TRUTH`** until physical reference data is acquired ([`docs/scientific_validation_results.md`](docs/scientific_validation_results.md)). MediaPipe monocular depth ($z$) remains an uncalibrated relative estimate and is not accepted as physical 3D ground truth.

### 13. 🔒 Ground Truth Acquisition & Double-Blind Protocol (Steps 68–70)
- **Permanent AI Freeze**: Algorithmic pipeline permanently frozen at commit `db33130abb4af653ccacc4bec872be25233b59e4` (`docs/scientific/validation_freeze_record.md`).
- **Physical Asset Auditing**: `tools/verify_physical_assets.py` cryptographically audits physical video assets directly from local file bytes (`data/ground_truth/metadata/asset_verification_audit.json`).
- **Zero Automated Annotations**: Code strictly barred from synthesizing or programmatically populating human ground truth.
- **Blank Rater Sheets**: `tools/generate_blank_rater_sheets.py` generates empty skeleton files (`rater_A_blank.json`, `rater_B_blank.json`) with null values for human experts.
- **Independent Human Importer & QC**: `tools/import_human_annotations.py` ingests trials ONLY when independent, blinded human files are supplied, enforcing content-level blinding, non-future timestamps, $\ge 3$ cycles, and strict provenance contracts.
- **Official Manifest Purity**: `data/ground_truth/manifests/ground_truth_manifest.json` contains 0 records pending receipt of certified human annotations.

---

## 🛠️ System Architecture

```
Swim_Analyzer_AI/
├── analysis/                        # Biomechanical Analysis Engines
│   ├── benchmarks/                  # BenchmarkEngine & percentile math
│   ├── strategies/                  # Stroke-specific strategies (Freestyle, Backstroke, Breaststroke, Butterfly)
│   ├── validation/                  # Ground Truth QC, Ingestion & Runner
│   ├── consistency_validator.py     # Scientific consistency rules
│   ├── pose_detector.py             # MediaPipe PoseLandmarker (Contiguous C-Memory)
│   ├── reliability_engine.py       # Transparent Video Analysis Reliability Engine
│   └── vqa_engine.py                # Video Quality Assessment engine
├── app/                             # Web Application & UI Components
│   ├── streamlit_app.py             # Main Streamlit router & orchestrator
│   └── ui/                          # Modular Presentation Layer
│       ├── tabs/                    # Summary, Charts, Downloads presenters
│       ├── pages/                   # Athlete Manager, Admin Console presenters
│       └── charts.py                # Plotly kinematic & progression charts
├── config/                          # Benchmark YAML files & application config
├── database/                        # Database Layer
│   ├── database.py                  # SQLAlchemy engine with SQLite WAL mode
│   ├── models.py                    # Database models (Coaches, Athletes, Sessions)
│   └── repository.py                # Authenticated tenant-isolated repositories
├── models/                          # Dataclasses & Domain Schemas
│   ├── athlete_profile.py           # Athlete Profile schema
│   ├── benchmark_models.py          # Benchmark result schemas
│   └── data_models.py               # StrokeSelection, AnalysisResult, ReliabilityResult
├── services/                        # Service Layer
│   ├── analysis_service.py          # Video analysis orchestrator (User selected stroke)
│   ├── athlete_service.py           # Athlete roster service (with Context Manager)
│   ├── analysis_history_service.py  # Session history service (with Context Manager)
│   ├── auth_service.py              # Argon2id authentication & RBAC
│   ├── background_analysis_worker.py# Async video processing worker
│   ├── storage_service.py           # Storage retention & TTL cleanup
│   ├── export_service.py            # JSON report exporter
│   ├── pdf_report_service.py        # FPDF report generator
│   └── scientific_evidence_service.py# Citation formatter
├── tools/                           # Operational Ground Truth Tools
│   ├── verify_physical_assets.py    # Local video asset byte audit
│   ├── generate_blank_rater_sheets.py # Blank template generator
│   └── import_human_annotations.py  # Human annotation QC and ingestion
├── data/ground_truth/               # Ground Truth Dataset Storage
│   ├── raw/                         # Local swimming videos (untracked)
│   ├── templates/                   # Guidelines & blank rater sheets
│   ├── quality_control/             # Double-blind audit trail (rater A/B)
│   ├── manifests/                   # Official validation manifest
│   └── metadata/                    # Cryptographic asset verification audit
└── tests/                           # Automated Pytest Suite (423 Passed, 1 Skipped / 100% Green)
```

---

## 🚀 Quickstart & Installation

### 1. Environment Setup
```bash
# Clone repository
git clone https://github.com/AbdelbasetAbdelaal/Swim_Analyzer_AI.git
cd Swim_Analyzer_AI

# Create virtual environment
python -m venv venv
venv\Scripts\activate   # On Windows
# source venv/bin/activate  # On Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### 2. Launching Web App
```bash
streamlit run app/streamlit_app.py
```

### 3. Running Automated Tests
```bash
python -m pytest tests/ -v
# 423 passed, 1 skipped, 0 failed (100% Pass Rate)
```

```bash
venv\Scripts\streamlit run app/streamlit_app.py
```
Open `http://localhost:8501`. 

**Initial Setup & Login:**
The application does not use hardcoded default passwords. To access the platform, you must configure the initial bootstrap credentials in your `.env` file (see `.env.example`):
```env
SWIM_ANALYZER_BOOTSTRAP_COACH_USERNAME=your_secure_username
SWIM_ANALYZER_BOOTSTRAP_COACH_PASSWORD=your_secure_password
```
Use these credentials to log in for the first time.
---

## 🧪 Automated Testing

Run the full test suite:
```bash
venv\Scripts\python -m pytest tests/ -v
```
Run ground truth collection & double-blind human protocol tests:
```bash
venv\Scripts\python -m pytest tests/test_ground_truth_collection.py -v
```
Run ground truth dataset & validation infrastructure tests:
```bash
venv\Scripts\python -m pytest tests/test_ground_truth_validation_infrastructure.py -v
```
Run scientific validation protocol & safety gate tests:
```bash
venv\Scripts\python -m pytest tests/test_scientific_validation_protocol.py -v
```
Run biomechanics baseline tests:
```bash
venv\Scripts\python -m pytest tests/test_biomechanics_baseline.py -v
```
Run user stroke selection and reliability tests:
```bash
venv\Scripts\python -m pytest tests/test_user_stroke_selection_and_reliability.py -v
```