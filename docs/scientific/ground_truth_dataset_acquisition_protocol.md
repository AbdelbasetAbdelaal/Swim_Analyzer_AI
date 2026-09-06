# Ground Truth Dataset Acquisition & Human Annotation Operational Protocol

**Document Identifier:** DOC-SCI-ACQ-PROTO-1.0.0  
**Version:** 1.0.0  
**Effective Date:** 2026-09-06  
**Status:** **GROUND TRUTH DATASET PROTOCOL READY — REAL DATA REQUIRED**  
**Scientific Validation Status:** **NOT_VALIDATED — INSUFFICIENT GROUND TRUTH**

---

## 1. Executive Summary & Purpose

The purpose of this operational protocol is to govern the physical acquisition, standardized recording, and double-blind human expert annotation of empirical Ground Truth datasets for the **Swim Analyzer AI** platform.

The acquired dataset is collected strictly to **evaluate the empirical accuracy, systematic bias, and repeatability** of the frozen Swim Analyzer AI pipeline against external gold-standard truth. 

> [!IMPORTANT]
> **SCIENTIFIC INDEPENDENCE & NON-TUNING INVARIANT**  
> 1. **Zero Development Contamination:** Ground Truth validation data must be completely independent from algorithm development. Data collected under this protocol must **never** be used to tune heuristic thresholds, adjust scoring weights, or alter pipeline logic.
> 2. **Blinded Annotation:** Annotators must remain completely blinded to all AI model outputs and internal predictions throughout the entire annotation process.
> 3. **No Synthetic Data:** Synthetic test fixtures, simulated values, and population reference tables from literature are strictly barred from official validation cohorts.
> 4. **Current Status Invariant:** The scientific status remains strictly **`NOT_VALIDATED — INSUFFICIENT GROUND TRUTH`** until a real physical cohort is collected, annotated, adjudicated, and evaluated.

---

## 2. Target Dataset Cohort Design

The empirical validation process is divided into two distinct scientific milestones:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VALIDATION MILESTONES                             │
│                                                                             │
│   Phase 1: PRELIMINARY VALIDATION (n = 24 Trials)                           │
│   • 6 Freestyle  • 6 Backstroke  • 6 Breaststroke  • 6 Butterfly            │
│   • Independent Swimmers (No single-swimmer repetitions)                    │
│   • Purpose: Validate pipeline functionality against real physical truth    │
│                                                                             │
│                                      ↓                                      │
│                                                                             │
│   Phase 2: FULL EXTERNAL VALIDATION (n ≥ 100 Trials)                        │
│   • Multicenter data collection across 3+ swimming facilities               │
│   • Balanced demographic cohorts (Sex, Junior, Senior, Masters, Elite)      │
│   • Purpose: Establish definitive commercial & clinical accuracy boundaries │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Preliminary Cohort Requirements (Round 1: 24 Trials)
- **Freestyle:** 6 independent trials
- **Backstroke:** 6 independent trials
- **Breaststroke:** 6 independent trials
- **Butterfly:** 6 independent trials
- **Participant Rule:** Each of the 24 trials must feature an independent trial session. A single swimmer executing 24 consecutive repetitions is strictly prohibited from constituting the preliminary cohort.

---

## 3. Participant Design & Privacy Protection

### Required Metadata Scope
Only scientific metadata essential to biomechanical stratification and body-length normalization is collected:
- `participant_id`: Pseudonymized code (format: `PARTICIPANT-XXX` or `SWIMMER-XXX`).
- `sex`: Biological sex (`Male`, `Female`).
- `age_group`: Category (`Junior`, `Senior`, `Masters`).
- `competition_level`: Competitive tier (`Club`, `National`, `International_Elite`, `Recreational`).
- `height_cm` / `arm_span_cm`: Optional anthropometrics for metric body-length calibration.

### Strict Privacy & PII Invariant
- **Direct PII Prohibited:** Swimmer full names, personal phone numbers, email addresses, residential addresses, and club affiliations must **never** be entered into metadata files, annotation JSONs, or file paths.
- **Ethics & Consent:** All participant data must be collected in full compliance with applicable institutional ethics boards, minor participant protections, and signed informed consent protocols.

---

## 4. Video Acquisition Specifications & Viewpoint Rules

### Optical & Recording Standards

| Parameter | Minimum Requirement | Recommended Specification | Rationale |
|---|---|---|---|
| **Frame Rate** | $\ge 30.0\text{ fps}$ (Strict CFR) | $\ge 60.0\text{ fps}$ ($100\text{--}120\text{ fps}$ for Butterfly/Sprint) | Limits temporal quantization jitter to $< 16.7\text{ ms}$. |
| **Resolution** | $1280 \times 720$ (HD) | $1920 \times 1080$ (Full HD) | Ensures sharp landmark boundaries under high water turbulence. |
| **Shutter Speed** | $\le 1/500\text{ s}$ | $\le 1/1000\text{ s}$ | Eliminates optical motion blur on fast hand pull and kick whip. |
| **Video Codec** | H.264 / ProRes 422 | Visually lossless / Constant Bitrate (CBR) | Prevents inter-frame compression artifacts from shifting joint centers. |

### Viewpoint Taxonomy & Truth Boundaries

> [!WARNING]
> **CRITICAL SCIENTIFIC DISTINCTION: MONOCULAR 2D vs. CALIBRATED PHYSICAL 3D**  
> - **Monocular Lateral Sagittal View:** Suitable for temporal cycle chronometry, 2D planar joint angles, body roll timing, and hand excursion proxy. **Monocular video CANNOT provide calibrated physical whole-body 3D translation.**
> - **Calibrated Multi-View / Physical Reference:** Required for true physical spatial measurements (e.g. true Distance Per Stroke in meters, whole-body Center of Mass displacement). MediaPipe monocular z-axis outputs must **never** be claimed as calibrated 3D ground truth.

---

## 5. Standardized Recording Procedure

### Trial Execution Rules
1. **Camera Placement:** Fixed tripod mount poolside ($10\text{--}15\text{ m}$ from start wall, $5\text{ m}$ lateral distance from swimming lane) or stationary submerged viewing window orthogonal to swimmer trajectory.
2. **Camera Stability:** Zero camera panning, tilting, or zooming. The optical axis must remain strictly stationary and perpendicular to the swimming lane.
3. **Clean Mid-Pool Window:** Swimmers must be recorded exclusively in the steady-state free-swimming zone (between $10\text{ m}$ and $20\text{ m}$ in a $25\text{ m}$ pool; $15\text{ m}$ and $35\text{ m}$ in a $50\text{ m}$ pool).
4. **Exclusion of Non-Free-Swimming:** Dive starts, underwater wall push-offs, breakout transitions, and flip/open turns are strictly excluded from the analyzed cycle sequence.
5. **Cycle Count:** Minimum 3 to 5 continuous, clean, unobstructed stroke cycles per video trial.
6. **Optical Environment:** Clear pool water, unobstructed lane lines, adequate surface lighting ($\ge 500\text{ lux}$), and minimal air bubble curtains.

### Asset Registration & Checksum
For every trial captured:
1. Assign a unique `sample_id` (e.g. `GT-FREE-001`).
2. Assign a unique `video_id` (e.g. `VID-FREE-001`).
3. Compute the cryptographic SHA-256 checksum:
   ```bash
   sha256sum trial_video.mp4
   ```
4. Record checksum in `data/ground_truth/metadata/` and the trial annotation JSON.

---

## 6. Metric-to-Ground-Truth Source Provenance Matrix

Every Ground Truth measurement must adhere to the provenance contract established in Step 68.1:

| Metric Name | Canonical Unit | Permitted Modalities | Provenance & Measurement Contract |
|---|---|---|---|
| **Stroke Rate** | `spm` | `HUMAN_VIDEO_ANNOTATION`, `PHYSICAL_MOCAP`, `IMU`, `CALIBRATED_OPTICAL` | Hand entry-to-entry frame chronometry by dual raters ($ICC \ge 0.90$). |
| **Cycle Duration** | `ms` | `HUMAN_VIDEO_ANNOTATION`, `PHYSICAL_MOCAP`, `IMU`, `CALIBRATED_OPTICAL` | Exact millisecond elapsed duration between consecutive cycle boundaries. |
| **Elbow Angle** | `deg` | `HUMAN_VIDEO_ANNOTATION`, `PHYSICAL_MOCAP`, `CALIBRATED_OPTICAL` | Must declare `angle_dimension`. Monocular human annotation **must be `2D_PLANAR`**; claiming `3D_SPATIAL` is strictly prohibited. |
| **Knee Angle** | `deg` | `HUMAN_VIDEO_ANNOTATION`, `PHYSICAL_MOCAP`, `CALIBRATED_OPTICAL` | Must declare `angle_dimension` (`2D_PLANAR` for monocular video). |
| **Body Roll Angle** | `deg` | `HUMAN_VIDEO_ANNOTATION`, `PHYSICAL_MOCAP`, `IMU`, `CALIBRATED_OPTICAL` | Planar shoulder/hip excursion angle relative to horizontal. |
| **Stroke Symmetry** | `%` | `HUMAN_VIDEO_ANNOTATION`, `PHYSICAL_MOCAP`, `IMU`, `CALIBRATED_OPTICAL` | Must declare `operational_definition` (e.g. `MIN_MAX_PULL_DURATION_RATIO`). |
| **Stroke Length Proxy** | `BL` | `HUMAN_VIDEO_ANNOTATION`, `CALIBRATED_OPTICAL`, `PHYSICAL_MOCAP` | Normalized hand excursion relative to torso length. **Explicitly classified as a proxy measure.** |
| **True DPS / CoM Translation** | `m` | `PHYSICAL_MOCAP`, `CALIBRATED_OPTICAL` ONLY | **STRICT PROVENANCE GATE:** MUST NOT be accepted from `HUMAN_VIDEO_ANNOTATION` or `IMU`. Requires calibrated physical spatial measurement of whole-body center-of-mass translation. |

---

## 7. Double-Blind Human Annotation Protocol

### Rater Qualification
- Minimum two independent raters per trial.
- Raters must be accredited sports biomechanists (ISBS / BASES) or certified high-performance swim coaches with motion analysis certification.
- Raters are completely blinded to AI predictions.

### Stroke-Specific Event & Boundary Definitions

#### 1. Freestyle
- **Cycle Boundary:** First frame of visible reference hand entry into the water surface to the subsequent entry of the same hand.
- **Key Events:** Entry ($F_{\text{entry}}$), Catch inflection ($F_{\text{catch}}$), Pull mid-point ($F_{\text{pull}}$), Release / Exit ($F_{\text{exit}}$).
- **Elbow Angle:** Minimum angle measured during underwater pull phase between shoulder, elbow, and wrist joint centers.

#### 2. Backstroke
- **Cycle Boundary:** Hand entry in supine position with little finger leading to subsequent identical hand entry.
- **Key Events:** Entry, First Downsweep, Catch, Upsweep, Release, Over-water Recovery.
- **Body Roll:** Peak bilateral shoulder rotation angle from horizontal plane.

#### 3. Breaststroke
- **Cycle Boundary:** Initial outward hand separation (outsweep initiation) to the subsequent outsweep initiation.
- **Key Events:** Outsweep start, Inwards sweep finish, Arm recovery drive, Kick propulsive finish, Glide phase.
- **Knee Angle:** Minimum knee flexion angle during propulsive kick preparation.

#### 4. Butterfly
- **Cycle Boundary:** Simultaneous entry of both hands in front of shoulders to subsequent simultaneous entry.
- **Key Events:** Hand entry, Catch/Insweep, Upsweep/Release, Simultaneous over-water recovery, First dolphin kick downbeat, Second dolphin kick downbeat.

---

## 8. Inter-Rater Quality Control & Adjudication

```
┌─────────────────────────┐     ┌─────────────────────────┐
│     RATER 1 (BLIND)     │     │     RATER 2 (BLIND)     │
│   Independent Marking   │     │   Independent Marking   │
└────────────┬────────────┘     └────────────┬────────────┘
             │                               │
             └───────────────┬───────────────┘
                             ▼
              ┌─────────────────────────────┐
              │    AGREEMENT AUDIT (QA)     │
              │   • Temporal Discrepancy    │
              │   • Angle ICC(2, 1)         │
              └──────────────┬──────────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   Discrepancy ≤ Tolerance           Discrepancy > Tolerance
   [PASS: DIRECT CONSENSUS]          [REQUIRES ADJUDICATION]
            │                                 │
            │                        ┌────────┴────────┐
            │                        ▼                 ▼
            │               Consensus Reached     Unresolvable
            │               [ADJUDICATED PASS]    [AMBIGUOUS/EXCLUDED]
            │                        │                 │
            └────────────────────────┼─────────────────┘
                                     ▼
                      ┌─────────────────────────────┐
                      │    OFFICIAL GROUND TRUTH    │
                      │   Recorded in Manifest      │
                      └─────────────────────────────┘
```

### Disagreement Tolerances
- **Temporal Boundaries:** Frame difference $\le 2\text{ frames}$ (at $60\text{ fps}$, $\le 33.3\text{ ms}$).
- **Kinematic Angles:** Absolute rater difference $\le 5.0^\circ$.
- **Adjudication:** If raters diverge beyond tolerance, an expert consensus panel adjudicates the discrepancy. If unresolvable, the sample is tagged `AMBIGUOUS` and barred from official cohorts.
- **Audit Preservation:** Raw independent sheets from both raters must be preserved in `data/ground_truth/quality_control/` for permanent provenance auditability.

---

## 9. Sample Status Gating Rules

Each sample is assigned exactly one status:
- **`INCLUDED`:** Complete dual-annotator consensus achieved; all quality flags passed; valid provenance; zero data leakage. Eligible for official validation cohorts.
- **`AMBIGUOUS`:** Disagreement beyond tolerance; visual refraction ambiguity; uncertain landmark identification. **Barred from official validation cohorts.**
- **`EXCLUDED`:** Contaminated by turns, starts, wall push-offs; $> 20\%$ landmark occlusion; severe aeration; missing video. **Barred from official validation cohorts.**

---

## 10. Validation Readiness Gate Checklist

Official validation execution against `analysis/validation/ground_truth_runner.py` is permitted **only** when all of the following conditions are verified:

- [ ] Real video assets placed in secure local storage (`data/ground_truth/raw/`).
- [ ] Cryptographic SHA-256 checksums generated and verified.
- [ ] Dual-rater independent annotations completed without exposure to AI outputs.
- [ ] Inter-rater agreement calculated and all discrepancies adjudicated.
- [ ] Metric provenance strictly adheres to `analysis/validation/provenance_contract.py`.
- [ ] Trial annotation JSON passes schema validation (`schemas/ground_truth_schema.json`).
- [ ] Cohort manifest verified (`schemas/ground_truth_manifest_schema.json`).
- [ ] Data leakage check confirms zero participant overlap across splits (`DataLeakageValidator`).
- [ ] All cohort samples hold `inclusion_status == "INCLUDED"`.
- [ ] Git commit SHA and protocol version recorded.
- [ ] Validation cohort is frozen and archived before running comparison.
