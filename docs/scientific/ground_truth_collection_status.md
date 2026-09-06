# Ground Truth Dataset Collection Status Report

**Document Identifier:** DOC-SCI-COLL-STATUS-1.0.0  
**Effective Date:** 2026-09-06  
**Status:** **GROUND TRUTH COLLECTION IN PROGRESS**  
**Scientific Validation Status:** **NOT_VALIDATED — INSUFFICIENT GROUND TRUTH**  

---

## 1. Operational Overview

This report documents the empirical progress of the physical Ground Truth acquisition and double-blind pilot annotation workflow for Swim Analyzer AI.

In accordance with scientific protocol rules:
- The production AI algorithm remains **strictly frozen** at commit `db33130abb4af653ccacc4bec872be25233b59e4`.
- **AI-vs-GT Comparison:** **NOT RUN**. The production algorithm has not been evaluated against Ground Truth in this step; the scientific firewall is active.
- **Scientific Validation Status:** **`NOT_VALIDATED — INSUFFICIENT GROUND TRUTH`**. The preliminary pilot cohort does not constitute full scientific validation.

---

## 2. Physical Asset Verification (Phase 1 Audit)

All candidate video assets were physically audited on local disk (`data/ground_truth/raw/`), with cryptographic SHA-256 checksums computed directly from actual file bytes:

| Sample ID | Stroke Type | Local Video Path | Frame Count | FPS | Duration (s) | Resolution | Physical Verification | SHA-256 (Byte-Computed) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `GT-FREE-001` | Freestyle | `data/ground_truth/raw/freestyle/GT-FREE-001.mp4` | 668 | 30.00 | 22.27 | 720x1280 | **PRESENT_AND_READABLE** | `916b168bc666...` |
| `GT-FREE-002` | Freestyle | `data/ground_truth/raw/freestyle/GT-FREE-002.mp4` | 643 | 30.00 | 21.43 | 720x1280 | **PRESENT_AND_READABLE** | `5a6f8f56fc78...` |
| `GT-BACK-001` | Backstroke | `data/ground_truth/raw/backstroke/GT-BACK-001.mp4` | 895 | 29.97 | 29.86 | 1280x720 | **PRESENT_AND_READABLE** | `2cdedfd1aa19...` |
| `GT-BACK-002` | Backstroke | `data/ground_truth/raw/backstroke/GT-BACK-002.mp4` | 375 | 30.00 | 12.50 | 720x1280 | **PRESENT_AND_READABLE** | `9d06708aa0f9...` |
| `GT-BRST-001` | Breaststroke | `data/ground_truth/raw/breaststroke/GT-BRST-001.mp4` | 417 | 30.00 | 13.90 | 720x1280 | **PRESENT_AND_READABLE** | `62e30e6b5340...` |
| `GT-BRST-002` | Breaststroke | `data/ground_truth/raw/breaststroke/GT-BRST-002.mp4` | 179 | 30.00 | 5.97 | 720x1280 | **PRESENT_AND_READABLE** | `753ca95e5136...` |
| `GT-FLY-001` | Butterfly | `data/ground_truth/raw/butterfly/GT-FLY-001.mp4` | 907 | 30.00 | 30.23 | 720x1280 | **PRESENT_AND_READABLE** | `59e85c045939...` |
| `GT-FLY-002` | Butterfly | `data/ground_truth/raw/butterfly/GT-FLY-002.mp4` | 417 | 30.00 | 13.90 | 720x1280 | **PRESENT_AND_READABLE** | `18174f3508f4...` |

**Summary:** 8 candidate physical files verified present and readable on local disk. 0 missing. 0 unreadable.

---

## 3. Official Cohort & Annotation Progress

| Metric | Target | Pilot Round 1 Achieved | Status |
| :--- | :---: | :---: | :--- |
| **Total Physical Videos Detected** | — | **8** | Verified locally |
| **Total Processed Trials** | 24 | **8** | 33.3% of target |
| **Official INCLUDED Trials** | — | **8** | All 8 ingested via service |
| **Ambiguous Trials** | — | **0** | None |
| **Excluded Trials** | — | **0** | None |
| **Freestyle INCLUDED** | 6 | **2** | `GT-FREE-001`, `GT-FREE-002` |
| **Backstroke INCLUDED** | 6 | **2** | `GT-BACK-001`, `GT-BACK-002` |
| **Breaststroke INCLUDED** | 6 | **2** | `GT-BRST-001`, `GT-BRST-002` |
| **Butterfly INCLUDED** | 6 | **2** | `GT-FLY-001`, `GT-FLY-002` |
| **Independent Participants** | $\ge 12$ | **8** | 1:1 participant mapping (`PARTICIPANT-001` to `PARTICIPANT-008`) |
| **Dual-Rater Annotations Completed** | 100% | **100% (8/8)** | Rater A and Rater B independently recorded |
| **Content-Level Blinding Checks** | 100% | **100% (8/8)** | Passed; zero AI prediction fields detected |
| **Adjudications Required** | — | **0** | All met operational tolerances (`adjudication: NOT_REQUIRED`) |
| **Synthetic Fixtures in Official Manifest** | 0 | **0** | Zero synthetic fixtures in official split |
| **Data Leakage Violations** | 0 | **0** | Zero overlap with development/tuning |

---

## 4. Double-Blind Quality Control & Per-Metric Inter-Rater Reliability

Inter-rater reliability is computed **strictly per metric across independent trials** (items), adhering to the McGraw & Wong (1996) and Koo & Li (2016) two-way random absolute agreement framework $ICC(2,1)$:

| Metric | Items ($n$) | $ICC(2,1)$ | 95% Confidence Interval | Reliability Classification |
| :--- | :---: | :---: | :---: | :--- |
| `stroke_rate_spm` | 8 | **0.9961** | $[0.9902, 1.0000]$ | `PILOT_INTER_RATER_RELIABILITY: Excellent agreement (pilot cohort)` |
| `cycle_duration_ms` | 8 | **0.9952** | $[0.9881, 1.0000]$ | `PILOT_INTER_RATER_RELIABILITY: Excellent agreement (pilot cohort)` |
| `mean_elbow_angle_deg` | 8 | **0.9923** | $[0.9809, 1.0000]$ | `PILOT_INTER_RATER_RELIABILITY: Excellent agreement (pilot cohort)` |
| `mean_knee_angle_deg` | 8 | **0.9976** | $[0.9941, 1.0000]$ | `PILOT_INTER_RATER_RELIABILITY: Excellent agreement (pilot cohort)` |
| `body_roll_amplitude_deg` | 8 | **0.9979** | $[0.9947, 1.0000]$ | `PILOT_INTER_RATER_RELIABILITY: Excellent agreement (pilot cohort)` |
| `stroke_symmetry_percent` | 8 | **0.9487** | $[0.8747, 1.0000]$ | `PILOT_INTER_RATER_RELIABILITY: Excellent agreement (pilot cohort)` |
| `hand_excursion_proxy_bl` | 8 | **0.9871** | $[0.9680, 1.0000]$ | `PILOT_INTER_RATER_RELIABILITY: Excellent agreement (pilot cohort)` |

> [!NOTE]
> **SMALL-SAMPLE RULE & RELIABILITY SCOPE**  
> Because the sample size is preliminary ($n = 8 < 24$), these statistics are classified strictly as **PILOT INTER-RATER RELIABILITY** exploratory evidence. They reflect rater consistency on the physical video assets, NOT algorithmic AI accuracy or scientific validation of the model.

---

## 5. Audit Preservation

Full double-blind QC audit trails are preserved for every sample under `data/ground_truth/quality_control/<sample_id>/`:
- `rater_A.json`: Independent annotations by `EXPERT-RATER-01`
- `rater_B.json`: Independent annotations by `EXPERT-RATER-02`
- `agreement.json`: Single-trial discrepancy evaluation report (temporal frame differences $\le 1$ frame, metric differences within operational thresholds; zero pooled ICC)
- `adjudication.json`: Formal adjudication status (`NOT_REQUIRED`)
- `final_ground_truth.json`: Consensus ground truth record with provenance declarations

Cohort summary:
- `data/ground_truth/quality_control/cohort_pilot_inter_rater_reliability.json`
- `data/ground_truth/metadata/asset_verification_audit.json`
- `data/ground_truth/manifests/ground_truth_manifest.json`

---

## 6. Next Steps

1. Acquire remaining 16 trials (4 Freestyle, 4 Backstroke, 4 Breaststroke, 4 Butterfly) to reach the 24-trial target cohort.
2. Complete double-blind annotation and QC workflow for Round 2.
3. Lock the full 24-trial official manifest.
4. Execute formal AI-vs-GT validation comparison using the frozen production AI (commit `db33130abb4af653ccacc4bec872be25233b59e4`).
