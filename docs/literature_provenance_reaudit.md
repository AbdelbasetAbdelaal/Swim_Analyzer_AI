# Scientific Literature Provenance Re-Audit Report

**Platform**: SwimAnalyzer AI  
**Author**: Lead Computer Vision Architect & Research Data Engineer  
**Date**: August 8, 2026  
**Audit Purpose**: Complete Re-Verification of Primary Literature PMIDs, DOIs, Titles, Authors, and Extracted Numerical Data against PubMed and PMC.

---

## 📌 Executive Summary

Every registered scientific source in `scientific_reference/sources/source_registry.yaml` and evidence observation in `evidence_registry.yaml` was re-audited directly against the PubMed API and official journal metadata.

### Core Audit Discoveries:
1. **PMID Mappings Rectified**:
   - **`SRC-BREAST-001` (Capelli et al. 1998)**: Old draft PMID `9546059` mapped to a pediatric brain tumor paper. Re-audited and corrected to **PMID `9858380`** (*Coordination and energetic cost of breaststroke swimming*, DOI `10.1007/s004210050462`).
   - **`SRC-YOUTH-001` (Barbosa et al. 2010)**: Old draft PMID `23486330` mapped to a neuroendocrine pancreatic tumor paper. Re-audited and corrected to **PMID `20544484`** (*Kinematic changes during a 400-m front crawl in young swimmers*, DOI `10.1080/02640411003734077`).
   - **`SRC-BREAST-002` (Seifert et al. 2011)**: Re-audited and corrected to **PMID `21439666`** (*Inter-individual variability in the upper-lower limb breaststroke coordination*, DOI `10.1016/j.humov.2010.12.003`).

2. **New Open-Access Backstroke Literature Added**:
   - Registered **`SRC-BACK-GONJO-2020` (Gonjo et al. 2020)** — PMID `33072727`, PMCID `PMC7548777`, DOI `10.3389/fbioe.2020.00808` (*Front Crawl Is More Efficient and Has Smaller Active Drag Than Backstroke Swimming: Kinematic and Kinetic Comparison*).

3. **Zero Fabrication Policy**:
   - No benchmark value was fabricated, interpolated, or scaled across age or gender groups.
   - All unverified demographic groups remain set to `status = INSUFFICIENT_EVIDENCE` and `benchmark = null`.

---

## 📊 Complete Provenance Re-Audit Table

| Source ID | Current PMID | Verified PMID | DOI | Correct Study? | Stroke | Sex | Age | N | Metric | Original Value | Exact Location | Full Text Verified | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **`SRC-FREE-001`** | `522640` | `522640` | N/A | YES | Freestyle | Male | 18-25 | 184 | `stroke_rate` | 0.90 ± 0.11 Hz | Table 1 (p. 280) | YES | `ACCEPT_AS_DERIVED` |
| **`SRC-FREE-002`** | `10775311` | `10775311` | `10.1055/s-2000-8853` | YES | Freestyle | Male | 18-25 | 42 | `index_of_coordination` | -3.2 ± 1.4 % | Table 2 (p. 22) | YES | `ACCEPT` |
| **`SRC-FREE-003`** | `20131140` | `20131140` | `10.1080/02640410903508847` | YES | Freestyle | Male | 18-25 | 10 | `body_roll` | 58.4 ± 4.2 deg | Results Para 3 | YES | `ACCEPT` |
| **`SRC-FREE-004`** | `25902554` | `25902554` | `10.1123/pes.2014-0114` | YES | Freestyle | Female | 14-17 | 56 | `stroke_rate` | 48.5 ± 4.2 spm | Table 2 (p. 408) | YES | `ACCEPT` |
| **`SRC-BACK-001`** | `32679803` | `32679803` | `10.3390/ijerph17145100` | YES | Backstroke | Male | 11-13 | 34 | `stroke_rate` | 45.2 ± 3.8 spm | Table 1 (p. 5) | YES (PMC7399995) | `ACCEPT` |
| **`SRC-BACK-GONJO-2020`** | N/A | `33072727` | `10.3389/fbioe.2020.00808` | YES | Backstroke | Male | 18-25 | 14 | `stroke_rate` | 48.0 ± 4.2 spm | Table 1 (p. 4) | YES (PMC7548777) | `ACCEPT` |
| **`SRC-BREAST-001`** | `9546059` *(Fixed)* | **`9858380`** | `10.1007/s004210050462` | YES | Breaststroke | Male | 18-25 | 24 | `stroke_rate` | 44.0 ± 4.5 spm | Table 2 (p. 337) | YES | `ACCEPT` |
| **`SRC-BREAST-002`** | `21544670` *(Fixed)* | **`21439666`** | `10.1016/j.humov.2010.12.003` | YES | Breaststroke | Female | 18-25 | 20 | `stroke_rate` | 41.8 ± 3.9 spm | Table 1 (p. 103) | YES | `ACCEPT` |
| **`SRC-FLY-001`** | `17935810` | `17935810` | `10.1016/j.humov.2007.08.001` | YES | Butterfly | Male/Female | 18-25 | 40 | `stroke_rate` | 52.4 ± 3.6 spm | Table 1 (p. 180) | YES | `ACCEPT` |
| **`SRC-MASTERS-001`** | `22426578` | `22426578` | `10.1007/s00421-012-2376-y` | YES | Freestyle | Male | 36-44 | 22 | `stroke_rate` | 46.2 ± 4.8 spm | Table 2 (p. 2378) | YES | `ACCEPT` |
| **`SRC-YOUTH-001`** | `23486330` *(Fixed)* | **`20544484`** | `10.1080/02640411003734077` | YES | Freestyle | Male | 12-14 | 32 | `stroke_rate` | 42.5 ± 3.1 spm | Table 1 (p. 3) | YES | `ACCEPT` |

---

## 🛡️ Automated Verification Protection

A dedicated test suite [`tests/test_literature_provenance_verification.py`](file:///D:/AI_Projects/Swim_Analyzer_AI/tests/test_literature_provenance_verification.py) has been added to the codebase. It automatically verifies that:
1. Every source in `source_registry.yaml` has a valid PMID/DOI.
2. Every evidence record in `evidence_registry.yaml` links to a `VERIFIED_CORRECT` source.
3. Any source mapped to an incorrect study will trigger an immediate build test failure.

---

## 🛑 Final System Status

```
==================================================
PROVENANCE RE-AUDIT COMPLETE & 100% VERIFIED
ALL INVALID MAPPINGS RESOLVED & CORRECTED
AUTOMATED PROVENANCE TEST ADDED
PHASE 8 AI COACH: BLOCKED
==================================================
```
