# Scientific Database Status

**Date:** 2026-08-08

## 1. Scientific Evidence Coverage
* **Verified Cohorts:** Primarily Adult Male/Female Freestyle (e.g. `18-25`, `Elite`).
* **Insufficient-Evidence Cohorts:** Primarily Youth (`8-10`, `11-13`) across Backstroke, Breaststroke, and Butterfly where peer-reviewed literature lacks exact kinematic kinematic tables.
* **Accepted Evidence:** Records extracted from PubMed/PMC via verifiable DOIs/PMIDs, maintaining exact value integrity without silent cross-stroke interpolation.
* **Rejected Evidence:** Abstract-only metrics lacking full-text provenance, and non-peer-reviewed or loosely categorized sources, are strictly kept off production endpoints.
* **Reference-Only Evidence:** Kept fully isolated and prohibited from converting into mathematical comparison vectors (Z-scores, percentiles).

## 2. Integrity Guards
* **Population Guard:** Copying Male metrics to Female or Adult benchmarks to Youth profiles is fully barred. If evidence does not exist, the metric comparison accurately yields `None` (Null) and notifies the UI.
* **Provenance Validator:** Every `Benchmark` resolves back to an `Evidence record` which resolves to a `Source ID` (PubMed/PMC context). If a link vanishes, the benchmark is deemed invalid.

## 3. Current Verification
The scientific database represents a highly structured, scientifically immutable graph. It successfully prevents arbitrary demographic leakage.
**Status:** BLOCKED_BY_MISSING_REAL_WORLD_DATA (for clinical heuristic comparison), but the database extraction layer is fully IMPLEMENTED and TESTED.
