# Ground Truth Dataset Specification for SwimAnalyzer AI

**Document Version:** 1.0.0  
**Effective Date:** 2026-09-05  
**Current Status:** **GROUND TRUTH DATASET: NOT AVAILABLE**  
**Purpose:** Define the rigorous, minimum dataset and annotation specifications required to conduct an empirical scientific validation of SwimAnalyzer AI's priority biomechanics metrics.

---

## 1. Executive Status & Scientific Disclaimer

> [!WARNING]
> **GROUND TRUTH DATASET: NOT AVAILABLE**  
> An exhaustive audit of the repository confirms that **no paired physical ground truth datasets** (underwater optoelectronic 3D motion capture, synchronized IMU sensor logs, or expert frame-by-frame manual annotations) currently exist.  
> - `data/validation_dataset/` contains only `.gitkeep` placeholders.
> - `data/input_videos/` contains unannotated raw MP4 video files.
> - `validation/test_data/test_video_labels.json` is a synthetic 17-line unit-test mock fixture.
> - `data/reference/swimming_reference_data_v2_scientific_registry.csv` contains macro-level cohort distributions from published literature (e.g., Born et al., 2022), not video-paired kinematic ground truth.
> 
> Under the project's strict Scientific Safety Policy, **no empirical validation may be claimed until a real Ground Truth dataset matching this specification is acquired and evaluated.**

---

## 2. Dataset Architecture & Collection Requirements

To empirically validate the 8 prioritized metrics, an empirical dataset comprising a minimum of **24 distinct video trials** (6 per stroke: Freestyle, Backstroke, Breaststroke, Butterfly) across male and female competitive swimmers must be acquired under calibrated conditions.

### Global Recording Standards
- **Video Container & Codec:** High-bitrate MP4 / MOV, uncompressed or visually lossless (H.264 / ProRes 422, bitrate $\ge 50\text{ Mbps}$).
- **Resolution:** Minimum $1920 \times 1080$ (Full HD) at 16:9, or $1280 \times 720$ high-speed.
- **Frame Rate:** Minimum $60\text{ fps}$ (recommended $100\text{--}120\text{ fps}$ for propulsive hand sweep and dolphin kick analysis). Must be strictly Constant Frame Rate (CFR) with zero frame drops.
- **Recording Duration:** $10\text{ to }20\text{ seconds}$ per trial.
- **Swimmer Phase:** Clean mid-pool surface swimming (free-swimming phase between 10 m and 20 m in a 25 m or 50 m pool). Starts, wall pushoffs, and flip/open turns must be excluded from kinematic evaluation.
- **Consecutive Cycles Required:** Minimum $3\text{ to }5\text{ consecutive clean stroke cycles}$ per trial.
- **Optical Environment:** Clear pool water with underwater visibility $> 10\text{ m}$; submerged window or stationary underwater housing aligned with the lane; minimal water surface foam and aeration.

---

## 3. Metric-Specific Ground Truth Specifications

---

### 1. Stroke Rate (SR)
- **Required Video Type:** High-speed lateral or elevated side-view video, CFR $\ge 60\text{ fps}$.
- **Required Swimming Stroke:** Freestyle, Backstroke, Breaststroke, Butterfly.
- **Required Camera View:** Lateral sagittal view (perpendicular to swim lane).
- **Required Camera Position:** Stationary poolside at water level ($10\text{--}15\text{ m}$ from start wall, $5\text{ m}$ lateral distance from swimmer).
- **Required Frame Rate:** $\ge 60\text{ fps}$ (temporal resolution $\le 16.7\text{ ms}$).
- **Required Video Duration:** $\ge 12\text{ seconds}$.
- **Required Number of Cycles:** Minimum 4 complete consecutive cycles.
- **Required Reference Annotation:** Frame timestamp of hand water entry (or initial outsweep in Breaststroke) for each completed cycle: $F_{\text{entry}, 1}, F_{\text{entry}, 2}, \dots, F_{\text{entry}, N+1}$.
- **Required Measurement Method:** Dual-rater video chronometry using kinematic analysis software (Kinovea / Dartfish / SkillSpector). Cycle duration $T_i = (F_{i+1} - F_i) / \text{FPS}$. True $\text{SR}_i = 60 / T_i$.
- **Required Units:** Strokes per minute (`spm`).
- **Required Annotator Expertise:** Certified Sports Biomechanist (ISBS/BASES accredited) or FINA/World Aquatics Level 3 Coach with motion analysis certification.
- **Number of Human Annotators:** 2 independent raters.
- **Inter-Rater Agreement Measurement:** Two-way random effects Intraclass Correlation Coefficient for single measures ($ICC(2, 1) \ge 0.95$) and Mean Absolute Difference $< 1.0\text{ spm}$.

---

### 2. Average Cycle Duration
- **Required Video Type:** Same as Stroke Rate (CFR $\ge 60\text{ fps}$).
- **Required Swimming Stroke:** All 4 strokes.
- **Required Camera View:** Lateral sagittal view.
- **Required Camera Position:** Stationary poolside at water level.
- **Required Frame Rate:** $\ge 60\text{ fps}$.
- **Required Video Duration:** $\ge 12\text{ seconds}$.
- **Required Number of Cycles:** Minimum 4 complete consecutive cycles.
- **Required Reference Annotation:** Individual cycle elapsed durations $\Delta t_i$ in milliseconds.
- **Required Measurement Method:** Synchronized timecode markers (SMPTE) placed at cycle initiation inflection points.
- **Required Units:** Milliseconds (`ms`).
- **Required Annotator Expertise:** Certified Sports Biomechanist.
- **Number of Human Annotators:** 2 independent raters.
- **Inter-Rater Agreement Measurement:** $ICC(2, 1) \ge 0.95$; Bland-Altman Mean Difference $< 20\text{ ms}$.

---

### 3. Stroke Length / DPS Proxy
- **Required Video Type:** Calibrated lateral side-view video with stationary camera and physical pool metric markers.
- **Required Swimming Stroke:** All 4 strokes.
- **Required Camera View:** Lateral view perpendicular to swimming direction.
- **Required Camera Position:** Fixed tripod mount orthogonal to lane center; camera optical axis perpendicular to lane line.
- **Required Frame Rate:** $\ge 60\text{ fps}$.
- **Required Video Duration:** $\ge 15\text{ seconds}$.
- **Required Number of Cycles:** Minimum 3 complete cycles.
- **Required Reference Annotation:**
  - *For Physical DPS:* Horizontal displacement of swimmer's anatomical Center of Mass (COM) from cycle entry to subsequent entry: $\Delta X_{\text{COM}}$.
  - *For Hand-Excursion Proxy:* Horizontal trajectory length of distal wrist joint center from catch point to finish release point relative to torso length.
- **Required Measurement Method:**
  - Physical 2D/3D calibrated spatial reconstruction using calibrated pool lane floats (known $1.0\text{ m}$ spacing) or submerged optical calibration wand.
- **Required Units:** Meters (`m`) for true DPS; body length units (`BL`) for hand excursion proxy.
- **Required Annotator Expertise:** Research Biomechanist experienced in planar 2D/3D DLT (Direct Linear Transformation) camera calibration.
- **Number of Human Annotators:** 2 independent raters.
- **Inter-Rater Agreement Measurement:** $ICC(2, 1) \ge 0.90$; Mean absolute difference $< 0.05\text{ m}$ (or $< 0.05\text{ BL}$).
- **Critical Proxy Constraint:** If true COM displacement cannot be tracked due to lack of submerged full-body calibration, the metric must be explicitly cataloged as `NOT VALIDATABLE WITH CURRENT GROUND TRUTH` rather than misrepresenting hand excursion as true whole-body DPS.

---

### 4. Elbow Angle
- **Required Video Type:** Submerged underwater camera video or high-clarity viewing window video, free of bubble curtains.
- **Required Swimming Stroke:** Freestyle, Backstroke, Breaststroke, Butterfly.
- **Required Camera View:** True lateral sagittal view ($< 15^\circ$ out-of-plane deviation).
- **Required Camera Position:** Submerged waterproof housing at depth $0.5\text{ m}$ below water surface, lateral distance $4\text{ m}$.
- **Required Frame Rate:** $\ge 60\text{ fps}$ (to resolve maximum elbow flexion at catch without motion blur).
- **Required Video Duration:** $10\text{ to }15\text{ seconds}$.
- **Required Number of Cycles:** Minimum 3 complete pull-push cycles.
- **Required Reference Annotation:** Frame-by-frame 2D coordinates of Acromion (shoulder), Lateral Epicondyle of Humerus (elbow), and Ulnar Styloid (wrist).
- **Required Measurement Method:** Manual frame-by-frame anatomical landmark digitization across the underwater pull phase ($30\text{ to }60\text{ frames per cycle}$) using calibrated software.
- **Required Units:** Degrees ($^\circ$).
- **Required Annotator Expertise:** Anatomically trained Sports Biomechanist or Physical Therapist.
- **Number of Human Annotators:** 2 independent raters (double-blind digitization).
- **Inter-Rater Agreement Measurement:** $ICC(2, 1) \ge 0.90$; Mean Absolute Difference $< 4.0^\circ$ across digitized frames; Bland-Altman 95% Limits of Agreement within $\pm 8.0^\circ$.

---

### 5. Knee Angle
- **Required Video Type:** Submerged underwater lateral video.
- **Required Swimming Stroke:** All 4 strokes (crucial for Breaststroke kick recovery and Freestyle flutter kick).
- **Required Camera View:** Lateral sagittal view.
- **Required Camera Position:** Submerged housing at depth $0.7\text{ m}$, aligned with lower extremity trajectory.
- **Required Frame Rate:** $\ge 60\text{ fps}$ (preferably $100\text{ fps}$ for flutter kick oscillations).
- **Required Video Duration:** $10\text{ to }15\text{ seconds}$.
- **Required Number of Cycles:** Minimum 3 kick cycles.
- **Required Reference Annotation:** Frame-by-frame coordinates of Greater Trochanter (hip), Lateral Femoral Condyle (knee), and Lateral Malleolus (ankle).
- **Required Measurement Method:** Frame-by-frame manual digitization or underwater retroreflective marker tracking.
- **Required Units:** Degrees ($^\circ$).
- **Required Annotator Expertise:** Certified Sports Biomechanist.
- **Number of Human Annotators:** 2 independent raters.
- **Inter-Rater Agreement Measurement:** $ICC(2, 1) \ge 0.90$; Mean Absolute Difference $< 4.0^\circ$.

---

### 6. Shoulder Angle
- **Required Video Type:** Lateral sagittal video capturing torso and upper arm excursion.
- **Required Swimming Stroke:** All 4 strokes.
- **Required Camera View:** Lateral view orthogonal to swimming line.
- **Required Camera Position:** Submerged/surface boundary position.
- **Required Frame Rate:** $\ge 60\text{ fps}$.
- **Required Video Duration:** $10\text{ to }15\text{ seconds}$.
- **Required Number of Cycles:** Minimum 3 cycles.
- **Required Reference Annotation:** Coordinates of Greater Trochanter (hip), Acromion (shoulder), and Lateral Epicondyle (elbow).
- **Required Measurement Method:** Planar anatomical goniometric digitization of trunk-to-humerus angle.
- **Required Units:** Degrees ($^\circ$).
- **Required Annotator Expertise:** Certified Sports Biomechanist.
- **Number of Human Annotators:** 2 independent raters.
- **Inter-Rater Agreement Measurement:** $ICC(2, 1) \ge 0.90$; Mean Absolute Difference $< 5.0^\circ$.

---

### 7. Body Roll
- **Required Video Type:** Frontal (head-on) submerged/surface camera video OR synchronized multi-sensor IMU telemetry.
- **Required Swimming Stroke:** Freestyle and Backstroke (longitudinal rotation strokes).
- **Required Camera View:** Frontal head-on view looking down the lane, OR longitudinal tracking trolley.
- **Required Camera Position:** Pool end-wall mount facing swimmer approaching head-on ($15\text{ m}$ to $5\text{ m}$ distance).
- **Required Frame Rate:** $\ge 60\text{ fps}$.
- **Required Video Duration:** 1 length ($15\text{ m}$ clean swim).
- **Required Number of Cycles:** Minimum 4 complete bilateral roll cycles.
- **Required Reference Annotation:**
  - *2D Image Tilt Ground Truth:* Angle of bilateral biacromial shoulder line relative to horizontal water surface.
  - *3D Anatomical Roll Ground Truth:* Continuous longitudinal axis angular velocity and Euler/quaternion orientation from a calibrated 9-DOF waterproof IMU affixed to thoracic spine (T1–T4 level).
- **Required Measurement Method:** Fused IMU orientation sampled at $\ge 100\text{ Hz}$, or multi-camera calibrated 3D torso normal tracking.
- **Required Units:** Degrees ($^\circ$).
- **Required Annotator Expertise:** Biomechanics research team with validated IMU validation protocols (e.g., Psycharakis & Sanders, 2010).
- **Number of Human Annotators:** Automated IMU gold standard + 1 biomechanist for video timecode synchronization.
- **Inter-Rater Agreement Measurement:** Sensor-to-video cross-correlation coefficient $r > 0.90$; Peak roll angle difference $< 5.0^\circ$.

---

### 8. Stroke Phase Timing
- **Required Video Type:** High-resolution lateral submerged side-view video capturing clean hand entry, underwater pull-push path, and surface exit.
- **Required Swimming Stroke:** Freestyle, Backstroke, Breaststroke, Butterfly.
- **Required Camera View:** Lateral sagittal view.
- **Required Camera Position:** Stationary underwater window or housing.
- **Required Frame Rate:** $\ge 60\text{ fps}$ (preferably $100\text{ fps}$).
- **Required Video Duration:** $\ge 15\text{ seconds}$.
- **Required Number of Cycles:** Minimum 3 complete cycles.
- **Required Reference Annotation:** Frame numbers marking transitions according to standardized definitions (Chollet et al., 2000; Leblanc et al., 2005):
  - *Freestyle:* Entry, Catch (first backward wrist translation), Pull-to-Push (hand at maximum vertical depth), Finish/Release (hand breaks surface), Recovery.
  - *Breaststroke:* Glide start, Outsweep/Catch, Inward Propulsion, Recovery.
- **Required Measurement Method:** Double-blind frame tagging with adjudication of discrepancies $> 2\text{ frames}$.
- **Required Units:** Frame numbers, seconds (`s`), and cycle percentage (`%`).
- **Required Annotator Expertise:** Two independent certified swim biomechanists.
- **Number of Human Annotators:** 2 independent raters.
- **Inter-Rater Agreement Measurement:** Cohen's Kappa $\kappa \ge 0.85$ for phase identification; Absolute frame difference $\le 2\text{ frames}$ on $\ge 90\%$ of transitions.

---

## 4. Human Annotation Protocol & Quality Assurance

1. **Rater Qualification:** Annotators must possess an accredited degree in Kinesiology, Sports Biomechanics, or Physical Education, with demonstrated competence in 2D video landmark digitization.
2. **Double-Blind Procedure:** Annotator A and Annotator B perform digitization independently without access to SwimAnalyzer AI predictions or each other's annotations.
3. **Consensus Adjudication:** Discrepancies exceeding the specified tolerance window ($\pm 2\text{ frames}$ for events, $\pm 5^\circ$ for angles) are jointly reviewed frame-by-frame with a Senior Biomechanist to establish the consensus Ground Truth.
4. **Data Verification File:** All consensus ground truth must be packaged in a standardized, machine-readable JSON schema (see `data/reference/ground_truth_dataset_schema.json`).
