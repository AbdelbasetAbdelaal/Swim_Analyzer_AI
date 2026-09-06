# Ground Truth Trial Collection & Ingestion Field Checklist

**Document Identifier:** CHK-SCI-GT-1.0.0  
**Version:** 1.0.0  
**Effective Date:** 2026-09-06  
**Audience:** Field Technicians, Research Biomechanists, and Annotation Supervisors

---

## Instructions for Field Operators
Every video recording candidate must pass this checklist before being registered into the official Ground Truth validation dataset. If any mandatory item fails, the trial must be marked **`EXCLUDED`** or re-recorded.

---

## Pre-Recording Setup Checklist

| Check | Item | Specification | Status |
|---|---|---|---|
| ☐ | **Participant Pseudonymization** | Participant assigned an anonymous ID (`PARTICIPANT-XXX`). Zero PII (name, email, club) collected. | Mandatory |
| ☐ | **Informed Consent Verified** | Signed ethics consent form on file with institutional supervisor. | Mandatory |
| ☐ | **Camera Rig Stability** | Fixed tripod mount or submerged window rig locked in place. Zero panning/tilting permitted. | Mandatory |
| ☐ | **Camera Orientation** | Optical axis strictly perpendicular (orthogonal) to swimmer lane trajectory. | Mandatory |
| ☐ | **Frame Rate Standard** | Camera configured to Constant Frame Rate (CFR) $\ge 30.0\text{ fps}$ (recommended $\ge 60.0\text{ fps}$). Variable Frame Rate (VFR) is strictly prohibited. | Mandatory |
| ☐ | **Optical Resolution** | Camera configured to minimum $1280 \times 720$ (recommended $1920 \times 1080$). | Mandatory |
| ☐ | **Shutter Speed** | Shutter configured to $\le 1/500\text{ s}$ to eliminate limb motion blur. | Recommended |
| ☐ | **Pool Optical Quality** | Pool water visibility clear to at least $10\text{ m}$. Lane line clearly distinguishable. | Mandatory |

---

## Trial Execution & Video Capture Checklist

| Check | Item | Specification | Status |
|---|---|---|---|
| ☐ | **Target Stroke Verification** | Swimmer executed the intended target stroke (Freestyle, Backstroke, Breaststroke, Butterfly). | Mandatory |
| ☐ | **Mid-Pool Free-Swimming** | Recording captures only the steady-state mid-pool swimming zone ($10\text{--}20\text{ m}$ for $25\text{ m}$ pool; $15\text{--}35\text{ m}$ for $50\text{ m}$ pool). | Mandatory |
| ☐ | **Zero Start / Turn Contamination** | Dive start, breakout kick, flip turn, or open turn are completely absent from analyzed sequence. | Mandatory |
| ☐ | **Clean Continuous Cycles** | At least 3 to 5 continuous, clean, completed stroke cycles captured without interruption. | Mandatory |
| ☐ | **Swimmer In-Frame Continuity** | Swimmer torso and limbs remain fully within frame throughout the evaluated cycles. | Mandatory |
| ☐ | **Occlusion Tolerance** | Joint landmark occlusions from air bubbles, surface foam, or lane ropes do not exceed 20% of cycle duration. | Mandatory |

---

## Post-Recording Ingestion Checklist

| Check | Item | Specification | Status |
|---|---|---|---|
| ☐ | **File Integrity & Format** | Video playable, uncorrupted MP4/MOV container. | Mandatory |
| ☐ | **Checksum Generation** | Cryptographic SHA-256 computed on raw file: `sha256sum trial.mp4`. | Mandatory |
| ☐ | **Local Secure Storage** | Video moved to `data/ground_truth/raw/<stroke>/`. File confirmed untracked in Git. | Mandatory |
| ☐ | **Metadata File Generated** | Demographics, pool calibration, camera parameters recorded in `data/ground_truth/metadata/`. | Mandatory |

---

## Annotation & Quality Gate Checklist

| Check | Item | Specification | Status |
|---|---|---|---|
| ☐ | **Dual-Rater Blinding** | Annotators assigned and verified blinded to all Swim Analyzer AI outputs. | Mandatory |
| ☐ | **Independent Annotation** | Both raters completed independent cycle boundary and event logging. | Mandatory |
| ☐ | **Inter-Rater Agreement Check** | Boundary discrepancy $\le 2\text{ frames}$; angle differences $\le 5.0^\circ$. Disagreements adjudicated. | Mandatory |
| ☐ | **Provenance Contract Compliance** | Modalities declared per Step 68.1 rules (`true_dps` uses physical/optical calibration; angles declare 2D/3D; symmetry declares definition). | Mandatory |
| ☐ | **Schema Validation** | Annotation JSON passes `schemas/ground_truth_schema.json` via ingestion tool. | Mandatory |
| ☐ | **Manifest Registration** | Trial registered into `data/ground_truth/manifests/ground_truth_manifest.json` with status `INCLUDED`. | Mandatory |

---

## Trial Sign-off

- **Trial Sample ID:** `_______________________`
- **Video Checksum (SHA-256):** `________________________________________________________________`
- **Field Operator Name / Signature:** `_______________________`  **Date:** `______________`
- **Annotation Supervisor Signature:** `_______________________`  **Date:** `______________`
- **Final Trial Status:** `[ ] INCLUDED     [ ] AMBIGUOUS     [ ] EXCLUDED`
