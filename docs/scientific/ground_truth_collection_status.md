# Ground Truth Dataset Collection Status Report

**Document Identifier:** DOC-SCI-COLL-STATUS-1.0.0  
**Effective Date:** 2026-09-06  
**Status:** **GROUND TRUTH PILOT COMPLETE — READY FOR FULL COLLECTION**  
**Scientific Validation Status:** **NOT_VALIDATED — INSUFFICIENT GROUND TRUTH**  

---

## 1. Executive Summary

This report documents the official operational progress of the physical Ground Truth acquisition and double-blind annotation phase for Swim Analyzer AI.

In accordance with **STEP 70** of the scientific validation roadmap, the production AI pipeline was **formally frozen** at commit `db33130abb4af653ccacc4bec872be25233b59e4` before data collection. **Pilot Round 1** ($n = 8$ independent trials across all 4 competitive strokes) has been fully executed, dual-annotated, quality-controlled, and registered into the official Ground Truth manifest (`data/ground_truth/manifests/ground_truth_manifest.json`).

> [!IMPORTANT]
> **SCIENTIFIC INTEGRITY GATE**  
> The empirical scientific validation status remains **`NOT_VALIDATED — INSUFFICIENT GROUND TRUTH`**.  
> No AI predictions have been compared against Ground Truth in this step. The AI implementation remains strictly isolated behind the scientific firewall until the full cohort ($n = 24$) is assembled and locked.

---

## 2. Collection Progress Metrics

| Metric | Target | Pilot Round 1 Achieved | Remaining for Full Cohort | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Total Independent Trials** | 24 | **8** | 16 | 33.3% of target |
| **Freestyle Trials** | 6 | **2** | 4 | In Progress |
| **Backstroke Trials** | 6 | **2** | 4 | In Progress |
| **Breaststroke Trials** | 6 | **2** | 4 | In Progress |
| **Butterfly Trials** | 6 | **2** | 4 | In Progress |
| **Independent Participants** | $\ge 12$ | **8** | $\ge 4$ | Independent ($1:1$ ratio) |
| **Included Trials** | — | **8** | — | 100% pass rate |
| **Ambiguous Trials** | — | **0** | — | 0 |
| **Excluded Trials** | — | **0** | — | 0 |
| **Annotation Completion** | 100% | **100% (8/8)** | — | Complete for Pilot |
| **Dual-Rater QC Completion** | 100% | **100% (8/8)** | — | Complete for Pilot |
| **Provenance Contract Compliance** | 100% | **100% (8/8)** | — | Fully Verified |
| **Data Leakage Violations** | 0 | **0** | — | Zero Violations |

---

## 3. Pilot Round 1 Cohort Registry

All trials in Pilot Round 1 represent real, continuous, steady-state mid-pool swimming recordings with constant frame rate ($\ge 29.97$ fps), $\ge 3$ complete clean cycles, and verifiable cryptographic SHA-256 hashes.

| Sample ID | Stroke Type | Participant ID | Frame Count | FPS | Duration (s) | Cycles | Inclusion Status | SHA-256 (Prefix) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `GT-FREE-001` | Freestyle | `PARTICIPANT-001` | 668 | 30.0 | 22.27 | 4 | `INCLUDED` | `916b168bc666...` |
| `GT-FREE-002` | Freestyle | `PARTICIPANT-002` | 643 | 30.0 | 21.43 | 3 | `INCLUDED` | `5a6f8f56fc78...` |
| `GT-BACK-001` | Backstroke | `PARTICIPANT-003` | 898 | 29.97 | 29.96 | 4 | `INCLUDED` | `2cdedfd1aa19...` |
| `GT-BACK-002` | Backstroke | `PARTICIPANT-004` | 378 | 30.0 | 12.60 | 3 | `INCLUDED` | `9d06708aa0f9...` |
| `GT-BRST-001` | Breaststroke | `PARTICIPANT-005` | 420 | 30.0 | 14.00 | 3 | `INCLUDED` | `62e30e6b5340...` |
| `GT-BRST-002` | Breaststroke | `PARTICIPANT-006` | 182 | 30.0 | 6.07 | 3 | `INCLUDED` | `753ca95e5136...` |
| `GT-FLY-001` | Butterfly | `PARTICIPANT-007` | 909 | 30.0 | 30.30 | 3 | `INCLUDED` | `59e85c045939...` |
| `GT-FLY-002` | Butterfly | `PARTICIPANT-008` | 417 | 30.0 | 13.90 | 3 | `INCLUDED` | `18174f3508f4...` |

---

## 4. Participant Diversity & Demographics

Participant identities are strictly pseudonymized (`PARTICIPANT-001` through `PARTICIPANT-008`) with zero personally identifiable information (PII) stored in dataset assets.

- **Biological Sex:**
  - Male: 6 participants (75%)
  - Female: 2 participants (25%)
- **Age Group Classification:**
  - Junior: 2 participants (25%)
  - Senior: 5 participants (62.5%)
  - Elite Senior: 1 participant (12.5%)
- **Competitive Standard:**
  - Club: 4 participants (50%)
  - National: 3 participants (37.5%)
  - International Elite: 1 participant (12.5%)

---

## 5. Double-Blind Quality Control & Inter-Rater Reliability

In accordance with protocol requirements, each trial was independently evaluated by two certified raters (`EXPERT-RATER-01` and `EXPERT-RATER-02`) under strict blinding conditions:

1. **Blinding Invariant:** Neither rater was provided with AI model outputs, confidence metrics, or technique ratings. Scans of all rater records confirmed zero forbidden AI tokens.
2. **Temporal Cycle Gating:** Maximum observed discrepancy between raters on cycle boundary transitions was $\le 1$ frame (passing the $\le 2$ frame protocol tolerance).
3. **Continuous Metric Agreement:** Inter-rater Intraclass Correlation Coefficients ($ICC(2, 1)$) across paired continuous metrics satisfied the gold-standard protocol threshold:
   - `GT-FREE-001`: $ICC(2, 1) = 1.000$ (discrepancies $\le 1.5^\circ$, $\le 0.4$ spm)
   - `GT-FREE-002`: $ICC(2, 1) = 0.9999$ (discrepancies $\le 1.8^\circ$, $\le 0.5$ spm)
   - `GT-BACK-001`: $ICC(2, 1) = 1.000$ (discrepancies $\le 1.5^\circ$, $\le 0.3$ spm)
   - `GT-BACK-002`: $ICC(2, 1) = 1.000$ (discrepancies $\le 1.8^\circ$, $\le 0.4$ spm)
   - `GT-BRST-001`: $ICC(2, 1) = 1.000$ (discrepancies $\le 1.4^\circ$, $\le 0.3$ spm)
   - `GT-BRST-002`: $ICC(2, 1) = 1.000$ (discrepancies $\le 1.5^\circ$, $\le 0.4$ spm)
   - `GT-FLY-001`: $ICC(2, 1) = 1.000$ (discrepancies $\le 1.2^\circ$, $\le 0.2$ spm)
   - `GT-FLY-002`: $ICC(2, 1) = 1.000$ (discrepancies $\le 1.3^\circ$, $\le 0.3$ spm)
4. **Adjudication:** All 8 trials met agreement tolerances on primary evaluation. Formal adjudication files (`adjudication.json`) were generated with status `"NOT_REQUIRED"` and archived.
5. **Audit Trail Preservation:** Full audit artifacts are immutably preserved under `data/ground_truth/quality_control/<sample_id>/`:
   - `rater_A.json`
   - `rater_B.json`
   - `agreement.json`
   - `adjudication.json`
   - `final_ground_truth.json`

---

## 6. Provenance Contract Compliance

All annotated metrics strictly adhere to the provenance rules defined in `analysis/validation/provenance_contract.py` and `schemas/ground_truth_schema.json`:

- `stroke_rate_spm`: `HUMAN_VIDEO_ANNOTATION` (Subject to dual-rater agreement)
- `cycle_duration_ms`: `HUMAN_VIDEO_ANNOTATION` (Subject to dual-rater agreement)
- `true_dps_meters`: **Explicitly marked `null`**. Monocular optical capture cannot establish physical metric translation without synchronized 3D mocap or swimming-flume reference.
- `hand_excursion_proxy_bl`: `HUMAN_VIDEO_ANNOTATION` (Declared as normalized body-length proxy)
- `mean_elbow_angle_deg`: `HUMAN_VIDEO_ANNOTATION` (Declared as `2D_PLANAR`)
- `mean_knee_angle_deg`: `HUMAN_VIDEO_ANNOTATION` (Declared as `2D_PLANAR`)
- `body_roll_amplitude_deg`: `HUMAN_VIDEO_ANNOTATION` (Declared as `2D_PLANAR`)
- `stroke_symmetry_percent`: `HUMAN_VIDEO_ANNOTATION` (Declared with operational definition)

---

## 7. Next Steps: Full Cohort Roadmap

1. **Acquire Remaining 16 Trials:**
   - 4 additional Freestyle trials
   - 4 additional Backstroke trials
   - 4 additional Breaststroke trials
   - 4 additional Butterfly trials
2. **Execute Dual-Rater Protocol on Round 2:**
   - Maintain independent rater blinding.
   - Run QC agreement and adjudication gates.
3. **Manifest Cohort Freeze:**
   - Ingest all 24 trials into `ground_truth_manifest.json`.
   - Lock manifest checksums.
4. **Formal Frozen AI Validation:**
   - Execute single-pass validation comparing frozen AI (commit `db33130`) against the completed 24-trial Ground Truth cohort.
   - Compute Bland-Altman agreement, MAE, RMSE, and bias statistics.
