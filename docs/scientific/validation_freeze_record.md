# Validation AI Freeze Record

**Document Identifier:** DOC-SCI-FREEZE-1.0.0  
**Effective Date:** 2026-09-06  
**Status:** **ACTIVE — FROZEN**  

---

## 1. Declarative Statement of AI Freeze

> [!IMPORTANT]
> **MANDATORY SCIENTIFIC FIREWALL STATEMENT**  
> "The AI implementation used for the official validation cohort is frozen before Ground Truth annotation and validation."

To maintain strict scientific integrity and avoid post-hoc heuristic tuning, data leakage, or overfitting to Ground Truth trials, the algorithmic pipeline of Swim Analyzer AI is permanently frozen at the commit specified below. Each future official validation run must reference this immutable commit SHA.

---

## 2. Immutable Version Specifications

| Component | Identifier / Version | Description / Verification |
| :--- | :--- | :--- |
| **Git Commit SHA** | `db33130abb4af653ccacc4bec872be25233b59e4` | Baseline commit on `origin/main` passing 100% test suite (408 tests) |
| **Application Version** | `SwimAnalyzer-1.0.0` | Release package identifier |
| **Scientific Protocol Version** | `1.0.0` (`DOC-SCI-VAL-PROTO-1.0.0`) | Ground Truth Validation Protocol |
| **Dataset Acquisition Protocol** | `1.0.0` (`DOC-SCI-ACQ-PROTO-1.0.0`) | Field Acquisition and Annotation Protocol |
| **Ground Truth Schema Version** | `1.0.0` (`ground_truth_schema.json`) | Machine-readable trial specification |
| **Manifest Schema Version** | `1.0.0` (`ground_truth_manifest_schema.json`) | Cohort registry specification |
| **Provenance Contract Version** | `1.0.0` (`provenance_contract.py`) | Source modality & physical measurement rules |
| **Benchmark Reference Version** | `1.0.0` (`docs/scientific/scientific_benchmarks.md`) | Normative physiological reference standards |
| **Configuration Profile** | `PRODUCTION` | Default algorithmic hyperparameters and weights |

---

## 3. Algorithmic Baseline Constraints

1. **Pose Backend Invariant:** MediaPipe Tasks API (`pose_landmarker.task`, Heavy/Full model) is the sole authorized pose detection backend. No alternative pose estimation frameworks (RTMPose, MMPose, YOLO-Pose, OpenPose) are permitted.
2. **Deterministic Processing:** Heuristics, phase detection rules, joint angle formulas, and reliability scoring models must not be modified during or following Ground Truth data collection.
3. **Double-Blind Isolation:** Human annotators and clinical reviewers must have zero visibility into AI predictions, scores, confidence metrics, or error logs for any Ground Truth trial.
4. **Validation Separation:** This frozen AI pipeline will only be evaluated against Ground Truth trials once the collection and annotation phase is complete and the Ground Truth manifest is formally locked.
