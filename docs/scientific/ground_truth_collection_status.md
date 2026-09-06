# Ground Truth Dataset Collection Status Report

**Document Identifier:** DOC-SCI-COLL-STATUS-1.0.0  
**Effective Date:** 2026-09-06  
**Status:** **GROUND TRUTH COLLECTION IN PROGRESS**  
**Scientific Validation Status:** **NOT_VALIDATED — INSUFFICIENT GROUND TRUTH**  

---

## 1. Operational Overview

This report documents the current status of the physical Ground Truth data collection and double-blind annotation phase for Swim Analyzer AI.

In accordance with scientific protocol rules:
- The production AI algorithm remains **strictly frozen** at commit `db33130abb4af653ccacc4bec872be25233b59e4`.
- No model predictions have been evaluated against Ground Truth (the AI-vs-GT firewall is active).
- Pre-populated/simulated pilot annotations were permanently purged from the official cohort.
- The official manifest (`data/ground_truth/manifests/ground_truth_manifest.json`) currently contains **0 approved trials** pending certified human dual-rater manual annotation.

> [!IMPORTANT]
> **SCIENTIFIC INTEGRITY GATE**  
> Empirical scientific validation status remains **`NOT_VALIDATED — INSUFFICIENT GROUND TRUTH`**.  
> The system requires actual, certified human dual-rater manual annotation on real physical videos before any trial can be marked `INCLUDED` in the official validation cohort.

---

## 2. Real Ground Truth Assets Detected Locally

A total of **8 candidate physical video assets** are currently detected in local storage (`data/ground_truth/raw/`), representing steady-state mid-pool swimming across all four strokes:

| Video Path | Stroke | Frame Count | FPS | Duration (s) | SHA-256 (Local Byte Computed) | Physical Video Status |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: |
| `data/ground_truth/raw/freestyle/GT-FREE-001.mp4` | Freestyle | 668 | 30.0 | 22.27 | `916b168bc666...` | **Present Locally** |
| `data/ground_truth/raw/freestyle/GT-FREE-002.mp4` | Freestyle | 643 | 30.0 | 21.43 | `5a6f8f56fc78...` | **Present Locally** |
| `data/ground_truth/raw/backstroke/GT-BACK-001.mp4` | Backstroke | 898 | 29.97 | 29.96 | `2cdedfd1aa19...` | **Present Locally** |
| `data/ground_truth/raw/backstroke/GT-BACK-002.mp4` | Backstroke | 378 | 30.0 | 12.60 | `9d06708aa0f9...` | **Present Locally** |
| `data/ground_truth/raw/breaststroke/GT-BRST-001.mp4` | Breaststroke | 420 | 30.0 | 14.00 | `62e30e6b5340...` | **Present Locally** |
| `data/ground_truth/raw/breaststroke/GT-BRST-002.mp4` | Breaststroke | 182 | 30.0 | 6.07 | `753ca95e5136...` | **Present Locally** |
| `data/ground_truth/raw/butterfly/GT-FLY-001.mp4` | Butterfly | 909 | 30.0 | 30.30 | `59e85c045939...` | **Present Locally** |
| `data/ground_truth/raw/butterfly/GT-FLY-002.mp4` | Butterfly | 417 | 30.0 | 13.90 | `18174f3508f4...` | **Present Locally** |

---

## 3. Official Cohort & Annotation Progress

| Metric | Target | Actual Currently Included | Notes |
| :--- | :---: | :---: | :--- |
| **Total Approved Trials** | 24 | **0** | Empty pending certified human manual annotation |
| **Freestyle Approved** | 6 | **0** | 2 candidate raw videos detected |
| **Backstroke Approved** | 6 | **0** | 2 candidate raw videos detected |
| **Breaststroke Approved** | 6 | **0** | 2 candidate raw videos detected |
| **Butterfly Approved** | 6 | **0** | 2 candidate raw videos detected |
| **Independent Participants Approved** | $\ge 12$ | **0** | Awaiting certified annotation linkage |
| **Candidate Physical Videos Detected** | — | **8** | Real files verified on local disk |
| **Certified Human Dual-Rater Annotations** | 100% | **0%** | Annotation process in progress |
| **Data Leakage Violations** | 0 | **0** | Clean |
| **Synthetic Fixtures in Official Manifest** | 0 | **0** | Strictly blocked by isolation gate |

---

## 4. Corrected ICC & Reliability Architecture

The inter-rater reliability engine (`analysis/validation/ground_truth_qc.py`) has been restructured to enforce scientific validity:

1. **Per-Metric Cohort ICC:**
   - Two-way random absolute agreement $ICC(2,1)$ is computed strictly **per metric across independent trials** (items).
   - Pooling heterogeneous metrics (e.g. stroke rate in spm, cycle duration in ms, joint angles in degrees) into a single trial ICC is strictly prohibited.
2. **Single-Trial Gating via Discrepancies:**
   - Single trials are evaluated using operational discrepancy gates:
     - Temporal cycle transitions: $\le 2$ frames.
     - Metric divergences: within defined operational review thresholds.
   - Single-trial calculations never produce or report an "overall ICC".
3. **Small-Sample Rule:**
   - Single trials ($n = 1$) return status `INSUFFICIENT_SAMPLE`.
   - Cohorts with $n < 24$ are labeled strictly as `PILOT INTER-RATER RELIABILITY` evidence only, and cannot be converted into claims of formal scientific validation.
4. **Content-Level Blinding Verification:**
   - Automated scans confirm the syntactic absence of model prediction fields in annotation files (`verify_content_level_blinding`).
   - The protocol explicitly notes that content-level scans do not substitute for organizational human procedural blinding.

---

## 5. Ingestion Gates for Official Cohort Inclusion

A trial can only be ingested as `INCLUDED` in `data/ground_truth/manifests/ground_truth_manifest.json` when:
1. Real raw video file physically exists on local disk.
2. SHA-256 checksum is computed directly from actual local bytes at ingestion time.
3. Timestamp integrity passes (no future-dated annotations).
4. Minimum 3 complete clean swimming cycles are annotated.
5. Distinct independent dual annotators are verified (`annotator_id != secondary_annotator_id`).
6. Inter-rater discrepancies pass operational tolerances or are formally adjudicated.
7. Provenance contract passes (`true_dps_meters` strictly null without 3D physical reference).
8. Sample is non-synthetic (`is_synthetic_fixture == False`).
9. Data leakage checks confirm no participant overlap with development/tuning splits.

---

## 6. Next Steps

1. Conduct certified manual dual-rater annotation on the 8 candidate raw video assets.
2. Ingest approved pilot trials through `GroundTruthIngestionService`.
3. Evaluate preliminary per-metric $ICC(2,1)$ across the pilot cohort.
4. Acquire remaining 16 trials to reach full 24-trial cohort target.
5. Lock the completed manifest and execute formal AI-vs-GT validation in the subsequent phase.
