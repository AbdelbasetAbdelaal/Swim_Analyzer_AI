# Ground Truth Validation Protocol for Swim Analyzer AI

**Document Identifier:** DOC-SCI-VAL-PROTO-1.0.0  
**Version:** 1.0.0  
**Effective Date:** 2026-09-06  
**Status:** **INFRASTRUCTURE READY — DATASET REQUIRED**  
**Scientific Validation Status:** **NOT_VALIDATED — INSUFFICIENT GROUND TRUTH**

---

## 1. Executive Summary & Core Principles

This protocol defines the formal, reproducible methodology for evaluating the accuracy, bias, and repeatability of the Swim Analyzer AI biomechanics engine against gold-standard human-annotated and physical sensor Ground Truth.

> [!IMPORTANT]
> **CRITICAL SCIENTIFIC SAFETY GATE & CURRENT STATUS**  
> 1. **Current Status:** `NOT_VALIDATED — INSUFFICIENT GROUND TRUTH`. No metric in Swim Analyzer AI may be advertised or reported as "scientifically validated" until this protocol is executed against an approved, independent empirical Ground Truth dataset.
> 2. **MediaPipe Tasks API:** MediaPipe is the single authorized pose estimation backend. No alternative pose estimation architectures (RTMPose, MMPose, YOLO-Pose, OpenPose) are permitted.
> 3. **Mathematical Correctness $\ne$ Empirical Scientific Validation:** Pure algebraic correctness and unit-test execution do not constitute scientific validation.
> 4. **Analysis Reliability / Consistency $\ne$ Scientific Validation:** High internal algorithmic confidence does not demonstrate physical accuracy against external truth.
> 5. **Synthetic Fixtures $\ne$ Ground Truth:** Mocks and synthetic fixtures are strictly software unit-testing tools and must never enter official validation cohorts.

---

## 2. Protocol Sections (A through L)

### A. Dataset Requirements
- **Target Size:** Minimum 24 independent trials (6 trials per stroke: Freestyle, Backstroke, Breaststroke, Butterfly) for preliminary cohort validation; 100+ trials across diverse populations for full external validation.
- **Participant Diversity:** Balanced representation across biological sex (Male / Female) and competitive tiers (Club, National, Elite).
- **Trial Completeness:** Every trial must capture a minimum of 3 to 5 consecutive, uninterrupted clean swimming cycles during mid-pool free-swimming.
- **Independence:** Data used for official validation must never have been used for heuristic threshold tuning or algorithm development.

### B. Participant Metadata
- **Pseudonymization:** Swimmer identities must be strictly pseudonymized using codes such as `PARTICIPANT-XXX`. Direct personally identifiable information (PII) is strictly prohibited.
- **Demographic Scope:**
  - Biological Sex (`Male`, `Female`)
  - Age Category (`Junior`, `Senior`, `Masters`)
  - Competitive Standard (`Club`, `National`, `International_Elite`, `Recreational`)
  - Height & Arm Span (normalized metric where available for body-length scaling)

### C. Video Acquisition Requirements
- **Video Standard:** Constant Frame Rate (CFR), minimum 30.0 fps (recommended $\ge 60.0$ fps to limit temporal quantization error to $< 16.7$ ms).
- **Resolution:** Minimum $1280 \times 720$ (HD), recommended $1920 \times 1080$ (Full HD).
- **Optics & Viewpoints:**
  - *Lateral Sagittal View:* Fixed tripod mount poolside or underwater viewing window perpendicular to lane trajectory.
  - *Frontal / Overhead:* Permitted only for auxiliary roll/symmetry analysis when explicitly calibrated.
- **Clarity & Water Condition:** Clear water, minimal aeration/bubble curtains; swimmer body fully visible throughout active stroke cycles.

### D. Annotation Requirements
- **Rater Qualification:** Annotations must be performed by certified sports biomechanists or accredited swim coaches with formal video analysis training.
- **Dual-Rater Protocol:** Minimum 2 independent raters annotating temporal cycle boundaries and landmark angles.
- **Inter-Rater Agreement Gate:**
  - Continuous metrics: Two-way random Intraclass Correlation Coefficient $ICC(2, 1) \ge 0.90$.
  - Temporal event marking: Discrepancy $\le 2$ frames (at 60 fps).
  - Adjudication: If raters diverge beyond tolerance, an expert consensus review is required.

### E. Metric Definitions & Measurement Classification

The protocol enforces a strict distinction between **MEASURED PHYSICAL QUANTITIES** and **PROXIES / ESTIMATES**:

| Metric | Scientific Classification | Unit | Temporal / Spatial Reference | Operational Definition |
|---|---|---|---|---|
| **Stroke Rate (SR)** | Measured Physical Quantity | `spm` | Entry-to-entry timestamps | $60 / T_{\text{cycle}}$ computed from consecutive cycle durations. |
| **Cycle Duration** | Measured Physical Quantity | `ms` | Start-to-end cycle frame time | Duration in milliseconds between consecutive identical cycle events. |
| **Elbow Angle** | Measured Physical Quantity | `deg` | Shoulder-Elbow-Wrist 3D vector | Instantaneous planar angle formed by shoulder, elbow, and wrist joint centers. |
| **Knee Angle** | Measured Physical Quantity | `deg` | Hip-Knee-Ankle 3D vector | Planar angle formed by hip, knee, and lateral malleolus joint centers. |
| **Body Roll Angle** | Measured Physical Quantity | `deg` | Bi-acromial / Bi-trochanteric line | Angular excursion of the shoulder or hip line relative to horizontal. |
| **Stroke Symmetry** | Normalized Measure | `%` | Left vs. Right half-cycle kinematics | Ratio of left-to-right arm pull duration or excursion: $\min(L, R)/\max(L, R) \times 100$. |
| **Stroke Length (Proxy)** | **PROXY / ESTIMATE / NORMALIZED** | `BL` or `m` | Distal wrist trajectory relative to torso | **CRITICAL:** In uncalibrated monocular video, this measures hand excursion relative to body landmarks, **NOT literal whole-body Center of Mass (CoM) translation**. Must never be labeled as true CoM DPS without physical pool calibration. |

### F. Stroke-Specific Rules

#### 1. Freestyle
- **Cycle Boundaries:** Hand entry of the reference arm to the subsequent hand entry of the same arm.
- **Phases:** Entry, Catch, Pull, Push, Recovery.
- **Symmetry:** Evaluated by comparing left and right single-arm pull durations and peak depths.
- **Exclusions:** Breathing cycle head-lift distortion must be flagged in quality notes.

#### 2. Backstroke
- **Cycle Boundaries:** Hand entry in supine position to subsequent hand entry of the same arm.
- **Phases:** Entry, First Downsweep, Catch, Upsweep, Release, Recovery.
- **Body Roll:** Continuous alternating bilateral roll around longitudinal axis ($30^\circ\text{--}50^\circ$).

#### 3. Breaststroke
- **Cycle Boundaries:** Initiation of arm outsweep to subsequent outsweep initiation.
- **Phases:** Outsweep, Catch, Inoutsweep, Arm Recovery, Kick Propulsive Drive, Gliding Phase.
- **Coordination:** Explicit separation between arm pull completion and kick initiation (glide phase).

#### 4. Butterfly
- **Cycle Boundaries:** Simultaneous bilateral hand entry to subsequent simultaneous entry.
- **Phases:** Entry/Catch, Insweep, Upsweep/Finish, Recovery (simultaneous over-water).
- **Undulation / Kicking:** Two distinct dolphin kicks per arm stroke cycle (first at entry, second at finish).

### G. Inclusion & Exclusion Criteria

#### Inclusion Criteria:
1. Video format CFR $\ge 30.0$ fps with complete frame metadata.
2. Minimum 3 complete, unobstructed stroke cycles captured in free-swimming phase.
3. Swimmer fully within camera frame during the analyzed cycle window.
4. Paired dual-rater consensus annotation file adhering to `schemas/ground_truth_schema.json`.

#### Exclusion Criteria:
1. Dive starts, underwater wall push-offs, breakout transitions, and flip/open turns.
2. Landmark occlusion exceeding 20% of cycle duration for critical joints.
3. Severe aerated water foam obscuring wrist or shoulder trajectories.
4. Any sample flagged as `AMBIGUOUS` or `EXCLUDED` during annotation QA.

### H. Ground Truth Quality Control
Samples must be categorized into exactly one of three states:
- `INCLUDED` (or `ANNOTATED`): Fully validated, dual-annotator consensus achieved, all quality gates passed.
- `AMBIGUOUS`: Divergent annotator interpretation, visual distortion, or borderline cycle boundaries. **Forbidden from official validation cohort.**
- `EXCLUDED`: Critical occlusion, insufficient cycles, severe frame drop, or turn inclusion. **Forbidden from official validation cohort.**

### I. AI vs. Ground Truth Comparison Methodology
1. **Sample Pairing:** AI analysis is executed on the identical raw video asset specified in the manifest.
2. **Cycle Alignment:** Temporal cycle alignment is verified using frame index synchronization or relative timeline normalization.
3. **Metric Extraction:** Comparable metrics are paired using standard metric keys.
4. **Missing Values:** If AI or Ground Truth fails to produce a valid measurement, it is recorded as a missing comparison rather than silently imputed as zero.

### J. Statistical Evaluation

For each continuous numerical metric, the comparator must compute:
1. **Sample Count ($N$):** Total samples in cohort.
2. **Valid Comparison Count ($n$):** Samples with both valid AI and valid Ground Truth values.
3. **Mean Absolute Error (MAE):**
   $$\text{MAE} = \frac{1}{n} \sum_{i=1}^n |y_{\text{AI}, i} - y_{\text{GT}, i}|$$
4. **Root Mean Squared Error (RMSE):**
   $$\text{RMSE} = \sqrt{\frac{1}{n} \sum_{i=1}^n (y_{\text{AI}, i} - y_{\text{GT}, i})^2}$$
5. **Mean Signed Error (Bias):**
   $$\text{Bias} = \frac{1}{n} \sum_{i=1}^n (y_{\text{AI}, i} - y_{\text{GT}, i})$$
6. **Mean Absolute Percentage Error (MAPE):**
   $$\text{MAPE} = \frac{100}{n} \sum_{i=1}^n \left| \frac{y_{\text{AI}, i} - y_{\text{GT}, i}}{y_{\text{GT}, i}} \right| \quad (\text{only when } y_{\text{GT}, i} \ne 0)$$
7. **Pearson Correlation ($r$):** Supplementary descriptive statistic only; **never** the sole acceptance criterion.

### K. Pass / Fail Interpretation & Threshold Policy
> [!WARNING]
> **THRESHOLD POLICY: NO INVENTED BENCHMARKS**  
> In accordance with project scientific integrity rules, numerical acceptance thresholds (e.g. acceptable MAE in degrees or SPM) must **NOT** be fabricated.  
> All thresholds are classified as:  
> $$\textbf{TBD — REQUIRES DOMAIN JUSTIFICATION}$$  
> Thresholds will be codified only upon approval by an accredited sports biomechanics board with reference to empirical literature.

### L. Validation Status Rules

Every metric evaluated will be assigned one of the following official statuses:
- `VALIDATED`: Empirical Ground Truth cohort evaluated; error statistics meet domain-justified criteria; sample size adequate ($n \ge 30$).
- `VALIDATED_WITH_LIMITATIONS`: Meets criteria under specific constrained viewpoints or swimming conditions.
- `NOT_VALIDATED`: Error statistics exceed domain thresholds.
- `INSUFFICIENT_SAMPLE`: Too few valid samples ($n < 10$) to compute reliable statistics.
- `INCONCLUSIVE`: High measurement variance or contradictory statistical indicators.
- `NOT_VALIDATED — INSUFFICIENT GROUND TRUTH`: **Default status for all metrics prior to empirical dataset execution.**
