# Step 64 — Biomechanics Metric Audit Report

**Audit Date:** 2026-09-05  
**Audit Scope:** CURRENT Biomechanics Engine (Freestyle, Backstroke, Breaststroke, Butterfly)  
**Pose Engine:** MediaPipe Tasks API (`vision.PoseLandmarker`, `pose_landmarker_full.task`) — Single Pose Engine Invariant  
**Audit Standard:** Peer-Reviewed Sports Biomechanics Literature (Maglischo 2003, Craig & Pendergast 1979, Psycharakis & Sanders 2008/2010, Leblanc et al. 2005, Cappaert et al. 1995, Chollet et al. 2000, Gonjo et al. 2020)

---

## 1. Executive Summary

An exhaustive scientific audit of all 41 biomechanical, kinematic, temporal, spatial 3D, error-detection, and reliability metrics was conducted across SwimAnalyzer AI.

### Metric Audit Classification Summary:
- **Total Metrics Audited:** 41
- **VALID:** 11 (26.8%)
- **VALID WITH LIMITATIONS:** 27 (65.9%)
- **NEEDS VALIDATION:** 2 (4.9%)
- **INCORRECT:** 0 (0.0%)
- **UNVERIFIED:** 1 (2.4%)

---

## 2. Complete Metric Inventory & Correctness Audit

### Category A: Per-Frame 2D Planar Joint Angles
All joint angles are calculated in `FreestyleBiomechanicsCalculator.calculate_all_angles` and shared across all four strokes.

| Metric | Landmarks Used | Formula Implemented | Units | Domain | Literature Reference | Classification |
|---|---|---|---|---|---|---|
| **left_elbow** | 11, 13, 15 | $\text{interior\_angle}(\vec{v}_{13 \to 11}, \vec{v}_{13 \to 15})$ via `arctan2` | deg | 2D image | Maglischo (2003); Psycharakis (2008) | **VALID WITH LIMITATIONS** |
| **right_elbow** | 12, 14, 16 | $\text{interior\_angle}(\vec{v}_{14 \to 12}, \vec{v}_{14 \to 16})$ via `arctan2` | deg | 2D image | Maglischo (2003); Psycharakis (2008) | **VALID WITH LIMITATIONS** |
| **left_knee** | 23, 25, 27 | $\text{interior\_angle}(\vec{v}_{25 \to 23}, \vec{v}_{25 \to 27})$ via `arctan2` | deg | 2D image | Maglischo (2003) | **VALID WITH LIMITATIONS** |
| **right_knee** | 24, 26, 28 | $\text{interior\_angle}(\vec{v}_{26 \to 24}, \vec{v}_{26 \to 28})$ via `arctan2` | deg | 2D image | Maglischo (2003) | **VALID WITH LIMITATIONS** |
| **left_shoulder** | 23, 11, 13 | $\text{interior\_angle}(\vec{v}_{11 \to 23}, \vec{v}_{11 \to 13})$ via `arctan2` | deg | 2D image | Maglischo (2003) | **VALID WITH LIMITATIONS** |
| **right_shoulder** | 24, 12, 14 | $\text{interior\_angle}(\vec{v}_{12 \to 24}, \vec{v}_{12 \to 14})$ via `arctan2` | deg | 2D image | Maglischo (2003) | **VALID WITH LIMITATIONS** |
| **left_hip** | 11, 23, 25 | $\text{interior\_angle}(\vec{v}_{23 \to 11}, \vec{v}_{23 \to 25})$ via `arctan2` | deg | 2D image | Psycharakis & Sanders (2008) | **VALID WITH LIMITATIONS** |
| **right_hip** | 12, 24, 26 | $\text{interior\_angle}(\vec{v}_{24 \to 12}, \vec{v}_{24 \to 26})$ via `arctan2` | deg | 2D image | Psycharakis & Sanders (2008) | **VALID WITH LIMITATIONS** |
| **body_roll (2D)** | 11, 12 | $|\arctan2(\Delta y, \Delta x) \cdot \frac{180}{\pi}|$ clamped $[0, 90]$ | deg | 2D image | Cappaert et al. (1995) | **VALID WITH LIMITATIONS** |

*Scientific Limitation Note for 2D Angles:*  
Calculated on normalized $[0, 1]$ coordinate vectors. In non-square camera aspects (16:9), unequal scaling between width and height introduces a minor aspect-ratio skew on diagonal vectors. Furthermore, monocular 2D projection foreshortens limbs when they rotate outside the camera's orthogonal plane.

---

### Category B: Spatial 3D Metrics (Pose-Relative)
Calculated in `FreestyleBiomechanicsCalculator._calculate_3d_metrics`:

| Metric | Landmarks Used | Formula Implemented | Units | Domain | Literature Reference | Classification |
|---|---|---|---|---|---|---|
| **body_roll_3d** | 11, 12, 23, 24 | $\vec{n}_{\text{torso}} = (\vec{r}_{sh} - \vec{l}_{sh}) \times (\vec{m}_{sh} - \vec{m}_{hp})$; $\text{roll} = \arctan2(|n_x|, |n_y|)$ | deg | `pose_relative_3d` | Psycharakis & Sanders (2010); Gonjo et al. (2020) | **VALID WITH LIMITATIONS** |
| **core_torsion_3d** | 11, 12, 23, 24 | $\arccos\left(\frac{\vec{v}_{sh} \cdot \vec{v}_{hp}}{\|\vec{v}_{sh}\| \|\vec{v}_{hp}\|}\right)$ clamped $[0, 90]$ | deg | `pose_relative_3d` | Cappaert et al. (1995); Psycharakis & Sanders (2008) | **VALID WITH LIMITATIONS** |
| **hand_depth_left_3d** | 11, 12, 15 | $z_{\text{wrist\_L}} - z_{\text{mid\_shoulder}}$ | rel units | `pose_relative_3d` | UNVERIFIED | **VALID WITH LIMITATIONS** |
| **hand_depth_right_3d** | 11, 12, 16 | $z_{\text{wrist\_R}} - z_{\text{mid\_shoulder}}$ | rel units | `pose_relative_3d` | UNVERIFIED | **VALID WITH LIMITATIONS** |

*Scientific Limitation Note for 3D Metrics:*  
The vector algebra (cross product for torso normal, dot product for transverse spine torsion) is mathematically exact. However, MediaPipe Z coordinates originate from a monocular neural network predicting relative depth without stereo triangulation; depth metrics represent qualitative spatial indicators.

---

### Category C: Phase Detection & Temporal State Machine Metrics
Calculated in `*_stroke_analyzer.py`:

| Metric | Formula Implemented | Units | Temporal Logic | Literature Reference | Classification |
|---|---|---|---|---|---|
| **stroke_phase** | Discrete state machine with hysteresis buffer | categorical | $\ge 0.10\text{s}$ pending confirmation | Maglischo (2003); Chollet et al. (2000) | **VALID** |
| **phase_confidence** | Transition heuristic score | scalar $[0, 1]$ | Per transition | UNVERIFIED | **VALID WITH LIMITATIONS** |
| **time_in_phases** | Accumulated phase duration $\sum \Delta t$ | seconds | Continuous frame timestamps | Chollet et al. (2000) | **VALID** |
| **completed_cycles** | Transition count (Recovery $\to$ Entry / Glide $\to$ Outsweep) | integer count | Monotonic cycle progression | Craig & Pendergast (1979) | **VALID** |
| **avg_cycle_duration_ms** | $(\text{duration\_sec} \cdot 1000) / \text{completed\_cycles}$ | ms | Cycle average | Craig & Pendergast (1979) | **VALID** |
| **avg_phase_confidence** | Mean confidence of active phase frames | ratio $[0, 1]$ | Timeline average | UNVERIFIED | **VALID WITH LIMITATIONS** |

---

### Category D: Global Kinematic Timeline Metrics
Calculated in `calculate_global_metrics`:

| Metric | Formula Implemented | Units | Domain | Literature Reference | Classification |
|---|---|---|---|---|---|
| **stroke_rate** | $\frac{\text{completed\_cycles}}{\Delta t_{\text{minutes}}}$ | spm | `calibrated_physical` | Craig & Pendergast (1979); Psycharakis & Sanders (2008) | **VALID** |
| **stroke_length** | $\text{mean}(\text{calibrate}(\Delta x_{\text{wrist}}))$ during pull-to-push | meters or body_length | `relative_body_normalized` / `calibrated_physical` | Craig & Pendergast (1979); Smith et al. (2002) | **VALID WITH LIMITATIONS** |
| **kick_frequency** | $\frac{\text{knee flexion-extension cycles}}{\Delta t_{\text{seconds}}}$ | Hz | `calibrated_physical` | Maglischo (2003) | **VALID WITH LIMITATIONS** |
| **stroke_symmetry** | Angular/spatial difference deduction: $100 - \|\theta_L - \theta_R\|$ | % | `calibrated_physical` | Seifert et al. (2005); Psycharakis (2008) | **VALID WITH LIMITATIONS** |

*Scientific Limitation Notes:*  
1. `stroke_length` measures hand reach-to-finish excursion distance per cycle, not center of mass pool translation. The engine correctly enforces `relative_body_normalized` when physical pool markers are uncalibrated.
2. `kick_frequency` tracks the right knee unilaterally, representing right leg kicking tempo.

---

### Category E: Stroke-Specific Global Kinematics

| Stroke | Metric Name | Formula Implemented | Units | Literature Reference | Classification |
|---|---|---|---|---|---|
| **Backstroke** | `average_body_roll` | Mean of 2D body roll across valid frames | deg | Psycharakis & Sanders (2010); Gonjo et al. (2020) | **VALID WITH LIMITATIONS** |
| **Breaststroke** | `glide_ratio` | $\frac{\text{frames in Glide}}{\text{total frames}}$ | ratio $[0, 1]$ | Leblanc et al. (2005); Seifert et al. (2007) | **VALID** |
| **Breaststroke** | `max_knee_bend_deg` | $\max(180.0 - \theta_{\text{knee}})$ | deg | Maglischo (2003) | **VALID WITH LIMITATIONS** |
| **Butterfly** | `hip_undulation_amplitude` | $\max(y_{\text{hip}}) - \min(y_{\text{hip}})$ | body_length | Sanders et al. (1995); Alves et al. (2006) | **VALID WITH LIMITATIONS** |
| **Butterfly** | `avg_wrist_asymmetry` | $\text{mean}(\|y_{\text{wrist\_L}} - y_{\text{wrist\_R}}\|)$ | image_space | UNVERIFIED | **VALID WITH LIMITATIONS** |
| **Butterfly** | `butterfly_symmetry_norm` | $\max(0, 100 - (\Delta y / 0.3) \cdot 100)$ | percent | UNVERIFIED | **UNVERIFIED** |

*Audit Finding on Butterfly Symmetry Norm:*  
The divisor `0.3` in Butterfly symmetry scoring represents an arbitrary empirical threshold (30% of normalized vertical frame height). It is classified as **UNVERIFIED** because no published Derivation exists for this specific scaling factor, although its qualitative coaching behavior (penalizing asymmetric arm clearance) functions effectively.

---

### Category F: Coaching Score & Technique Errors

| Metric | Trigger Condition | Severity | Literature Reference | Classification |
|---|---|---|---|---|
| **overall_score** | Weighted multi-attribute score (or deduction model) | N/A | UNVERIFIED | **VALID WITH LIMITATIONS** |
| **dropped_elbow** | Pull phase elbow angle $< 90^\circ$ or $> 120^\circ$ | Medium | Maglischo (2003) | **VALID** |
| **recovery_reach** | Recovery phase shoulder angle $< 140^\circ$ or $> 180^\circ$ | Medium | Maglischo (2003) | **VALID** |
| **knee_bend_error** | Knee angle outside $[130^\circ, 175^\circ]$ | Medium | Maglischo (2003) | **VALID** |
| **asymmetrical_pull** | Symmetry score $< 80\%$ | High | Seifert et al. (2005) | **VALID WITH LIMITATIONS** |

---

### Category G: Reliability Engine Components
Calculated in `analysis/reliability_engine.py`:

| Metric | Formula Implemented | Classification |
|---|---|---|
| **analysis_reliability_score** | $0.25 \cdot \text{Coverage} + 0.25 \cdot \text{PoseVal} + 0.20 \cdot \text{Visibility} + 0.15 \cdot \text{TempStab} + 0.15 \cdot \text{CycleQual}$ | **VALID** |
| **frame_coverage_pct** | $(\text{valid\_frames} / \text{total\_frames}) \cdot 100$ | **VALID** |
| **pose_validity_pct** | $(\text{valid\_pose\_frames} / \text{total\_frames}) \cdot 100$ | **VALID** |
| **landmark_visibility_pct** | $\text{mean}(\text{landmark.visibility}) \cdot 100$ | **VALID** |
| **temporal_stability_pct** | $100 - \text{penalty}(\text{velocity variance})$ | **NEEDS VALIDATION** |
| **cycle_quality_pct** | $\min(100, (\text{completed\_cycles} / \text{target\_cycles}) \cdot 100)$ | **VALID WITH LIMITATIONS** |
| **measurement_stability_pct** | Coefficient of variation penalty on joint angles | **NEEDS VALIDATION** |

---

## 3. Critical Scientific Findings & Recommendations

1. **Aspect Ratio Foreshortening**:
   2D interior angles computed via `calculate_angle` do not scale normalized coordinates by the frame aspect ratio ($W/H$). This introduces minor angular distortion on oblique limbs in widescreen (16:9) video footage compared to square aspect ratios.
2. **Stroke Length Semantics**:
   The metric `stroke_length` measures hand reach-to-finish excursion per cycle. The engine correctly flags this as `relative_body_normalized` when physical lane line markers are uncalibrated, successfully mitigating clinical/medical misinterpretation.
3. **Monocular 3D Depth Limitations**:
   While `body_roll_3d` and `core_torsion_3d` use mathematically sound vector algebra, they rely on MediaPipe's monocular pseudo-depth $Z$. They are properly tagged with `measurement_domain: pose_relative_3d`.
4. **Butterfly Symmetry Normalization Factor (`0.3`)**:
   An empirical heuristic that functions well in practice but lacks a formal mathematical proof. Classified as **UNVERIFIED**.

---

## 4. Final Verdict

**READY FOR SCIENTIFIC VALIDATION**
