# Scientific Validation Experiment Design & Execution Report

**Document Version:** 1.0.0  
**Effective Date:** 2026-09-05  
**Pose Estimation Engine:** MediaPipe Tasks API (`PoseLandmarker`) — Single Backend Invariant  
**Experiment Execution Status:** **BLOCKED — GROUND TRUTH DATASET REQUIRED**

---

## 1. Executive Summary & Repository Evidence Audit

An exhaustive investigation across all directories in the `Swim_Analyzer_AI` repository was conducted to determine whether real physical ground truth data exists to execute the validation experiment.

### Evidence Inventory Results:
1. **`data/validation_dataset/`**:
   - Subdirectories (`freestyle/`, `backstroke/`, `breaststroke/`, `butterfly/`, `unknown_noise/`) contain **only `.gitkeep` placeholder files**.
   - Zero annotated videos or measurement ground-truth files are present.
2. **`data/input_videos/`**:
   - Contains 9 raw user/athlete uploads in MP4 format.
   - None of these videos possess paired manual landmark annotations, 3D optoelectronic motion capture trajectories, or synchronized IMU telemetry.
3. **`validation/test_data/test_video_labels.json`**:
   - A 17-line synthetic mock fixture containing 5 fabricated numbers (SR=40, SL=1.5, BR=35, KF=2.0, SC=10) and 8 toy events used exclusively for checking arithmetic formulas in `tests/test_validation_math.py`. It is **not** an empirical ground truth dataset.
4. **`data/reference/swimming_reference_data_v2_scientific_registry.csv`**:
   - Contains published macro-level cohort statistics from peer-reviewed literature (e.g., Born et al., 2022 for European Championship finalists). These are population norms, not paired video frame-by-frame ground truth.
5. **`data/reports/rtmpose_vs_mediapipe_benchmark.json`**:
   - Explicitly documents on line 7: `"note": "Engineering proxy metrics without ground-truth manual annotations"`.

### Scientific Safety Enforcement:
Under the project's strict Scientific Safety Policy:
> **No results may be fabricated.**  
> In the absence of real Physical Ground Truth, the validation experiment **cannot be executed**.  
> The mandatory verdict for this step is:  
> $$\textbf{BLOCKED — GROUND TRUTH DATASET REQUIRED}$$

---

## 2. Priority Metrics Validation Status Table

In accordance with STEP 66 mandates, every priority metric is audited for Ground Truth availability, execution feasibility, and resulting empirical status.

| Metric | Ground Truth Available | Experiment Executed | Result | Status |
|---|---|---|---|---|
| **Stroke Rate** | NO | NO | INSUFFICIENT GROUND TRUTH | **NOT_VALIDATED** |
| **Average Cycle Duration** | NO | NO | INSUFFICIENT GROUND TRUTH | **NOT_VALIDATED** |
| **Stroke Length / DPS proxy** | NO | NO | INSUFFICIENT GROUND TRUTH | **NOT_VALIDATED** |
| **Elbow Angle** | NO | NO | INSUFFICIENT GROUND TRUTH | **NOT_VALIDATED** |
| **Knee Angle** | NO | NO | INSUFFICIENT GROUND TRUTH | **NOT_VALIDATED** |
| **Shoulder Angle** | NO | NO | INSUFFICIENT GROUND TRUTH | **NOT_VALIDATED** |
| **Body Roll** | NO | NO | INSUFFICIENT GROUND TRUTH | **NOT_VALIDATED** |
| **Stroke Phase Timing** | NO | NO | INSUFFICIENT GROUND TRUTH | **NOT_VALIDATED** |

---

## 3. Validation Experiment Design

This section establishes the exact statistical and experimental design that will execute as soon as the Ground Truth dataset matching `docs/ground_truth_dataset_specification.md` is populated.

---

### Experiment 1: Stroke Rate (SR)

- **A. Ground Truth Value ($y_i$):**
  Mean stroke rate across completed cycles $i = 1 \dots N$, derived from double-blind frame timestamps:
  $$y_i = \frac{60 \times \text{FPS}_{\text{actual}}}{F_{\text{entry}, i+1} - F_{\text{entry}, i}} \quad [\text{spm}]$$
  where $\text{FPS}_{\text{actual}}$ is the hardware-verified timebase, not assumed nominal FPS.
- **B. Swim Analyzer Value ($\hat{y}_i$):**
  Predicted stroke rate output by `analysis/strategies/*_stroke_analyzer.py` via cycle state machine.
- **C. Absolute Error:**
  $$e_i = |\hat{y}_i - y_i| \quad [\text{spm}]$$
- **D. Relative Error:**
  $$\text{RE}_i = \frac{|\hat{y}_i - y_i|}{y_i} \times 100\%$$
- **E. Agreement Analysis:**
  - **Mean Bias:** $\bar{d} = \frac{1}{N}\sum (\hat{y}_i - y_i)$
  - **Standard Deviation of Error:** $s_d = \sqrt{\frac{1}{N-1}\sum ((\hat{y}_i - y_i) - \bar{d})^2}$
  - **Bland-Altman 95% Limits of Agreement (LoA):** $[\bar{d} - 1.96 s_d, \bar{d} + 1.96 s_d]$
  - **Statistical Justification:** Bland-Altman analysis reveals systematic over- or under-estimation across varying stroke tempos without assuming uniform variance.
- **F. Repeatability Analysis:**
  - **Intraclass Correlation Coefficient ($ICC(3, 1)$):** Evaluates algorithmic test-retest consistency across 3 repeated runs on identical video.
  - **Swimmer Consistency:** Within-subject coefficient of variation across consecutive trials.
- **G. Failure / Insufficient Evidence Handling:**
  - If video contains $< 2$ valid completed cycles or wrist visibility $< 0.40$ on $> 20\%$ of frames, report `valid=False`, `status="insufficient_data"`.

---

### Experiment 2: Average Cycle Duration

- **A. Ground Truth Value ($y_i$):**
  Cycle duration in milliseconds from synchronized timecodes:
  $$y_i = \frac{F_{\text{end}} - F_{\text{start}}}{\text{FPS}_{\text{actual}}} \times 1000\text{ ms}$$
- **B. Swim Analyzer Value ($\hat{y}_i$):**
  `avg_cycle_duration_ms` from `*_stroke_analyzer.py`.
- **C. Absolute Error:**
  $$e_i = |\hat{y}_i - y_i| \quad [\text{ms}]$$
- **D. Relative Error:**
  $$\text{RE}_i = \frac{|\hat{y}_i - y_i|}{y_i} \times 100\%$$
- **E. Agreement Analysis:**
  - Mean Absolute Error (MAE in ms) and Root Mean Squared Error (RMSE in ms).
  - Pearson correlation coefficient ($r$) to evaluate linear tracking across fast and slow strokes.
- **F. Repeatability Analysis:**
  - $ICC(3, 1)$ across repeated runs; algorithmic determinism verified if $\text{MAE}_{\text{repeat}} = 0.0\text{ ms}$.
- **G. Failure Handling:**
  - Dropped frames or timestamp discontinuities $> 100\text{ ms}$ abort cycle calculation.

---

### Experiment 3: Stroke Length / DPS Proxy

- **A. Ground Truth Value ($y_i$):**
  - **Hand-Excursion Proxy Ground Truth:** Distal wrist horizontal displacement from catch to finish measured in relative torso length units.
  - **Physical Whole-Body DPS Ground Truth:** Horizontal translation of body Center of Mass (COM) per cycle measured against calibrated pool floor markers:
    $$\text{DPS}_{\text{true}} = \Delta X_{\text{COM}} \quad [\text{meters}]$$
- **B. Swim Analyzer Value ($\hat{y}_i$):**
  `stroke_length` output by `FreestyleBiomechanicsCalculator` (uncalibrated: normalized to body units; calibrated: multiplied by pool calibration scale).
- **C. Absolute Error:**
  $$e_i = |\hat{y}_i - y_i| \quad [\text{body units or meters}]$$
- **D. Relative Error:**
  $$\text{RE}_i = \frac{|\hat{y}_i - y_i|}{y_i} \times 100\%$$
- **E. Agreement Analysis:**
  - **CRITICAL SCIENTIFIC SAFETY CONSTRAINT:** The existing SwimAnalyzer AI implementation calculates a **hand reach-to-finish excursion proxy**, NOT whole-body center-of-mass translation.
  - If Ground Truth tracks whole-body COM displacement while SwimAnalyzer measures wrist excursion, direct numerical comparison is methodologically invalid.
  - Therefore, if only whole-body COM Ground Truth is available without calibrated hand-excursion reference, mark:
    $$\textbf{NOT VALIDATABLE WITH CURRENT GROUND TRUTH}$$
- **F. Repeatability Analysis:**
  - Test-retest CV across repeated swimming passes under identical pool calibration.
- **G. Failure Handling:**
  - Uncalibrated videos must enforce `relative_body_normalized` domain. Mobile panning cameras without planar homography compensation must abort calculation.

---

### Experiment 4: Elbow Angle

- **A. Ground Truth Value ($y_f$):**
  Submerged anatomical goniometric digitization of Acromion-Epicondyle-Styloid angle on frame $f$ by consensus of two independent biomechanists ($^\circ$).
- **B. Swim Analyzer Value ($\hat{y}_f$):**
  2D planar interior angle computed via `calculate_angle(Shoulder, Elbow, Wrist)` on frame $f$.
- **C. Absolute Error:**
  $$e_f = |\hat{y}_f - y_f| \quad [^\circ]$$
- **D. Relative Error:**
  Not scientifically recommended for bounded circular joint angles (a $5^\circ$ error at $50^\circ$ is $10\%$, but at $150^\circ$ is $3.3\%$ despite identical biomechanical severity). Absolute error in degrees ($^\circ$) is the primary metric.
- **E. Agreement Analysis:**
  - **MAE ($^\circ$) & RMSE ($^\circ$)** across all analyzed pull-phase frames.
  - **Bland-Altman 95% LoA** to assess angular systematic bias (e.g., MediaPipe consistently under-estimating flexion due to surface refraction).
  - **Intraclass Correlation Coefficient ($ICC(2, 1)$)** for continuous agreement.
- **F. Repeatability Analysis:**
  - Frame-to-frame angular jitter $\sigma_{\Delta \theta}$ across static posture frames.
- **G. Failure Handling:**
  - Landmark visibility $< 0.50$ on shoulder, elbow, or wrist flags angle as invalid. Angles outside $[0^\circ, 180^\circ]$ are rejected.

---

### Experiment 5: Knee Angle

- **A. Ground Truth Value ($y_f$):**
  Digitized anatomical Hip-Knee-Ankle interior angle ($^\circ$).
- **B. Swim Analyzer Value ($\hat{y}_f$):**
  `calculate_angle(Hip, Knee, Ankle)` ($^\circ$).
- **C. Absolute Error:**
  $$e_f = |\hat{y}_f - y_f| \quad [^\circ]$$
- **D. Agreement Analysis:**
  - MAE ($^\circ$), RMSE ($^\circ$), $ICC(2, 1)$.
  - Projection limitation analysis: Planar error evaluated as a function of swimmer distance and roll angle.
- **E. Repeatability Analysis:**
  - Peak kick flexion angle repeatability across consecutive kick oscillations.
- **F. Failure Handling:**
  - Landmark visibility $< 0.40$ or aeration bubble occlusion flags metric as invalid.

---

### Experiment 6: Shoulder Angle

- **A. Ground Truth Value ($y_f$):**
  Digitized trunk-to-humerus angle ($^\circ$).
- **B. Swim Analyzer Value ($\hat{y}_f$):**
  `calculate_angle(Hip, Shoulder, Elbow)` ($^\circ$).
- **C. Absolute Error:**
  $$e_f = |\hat{y}_f - y_f| \quad [^\circ]$$
- **D. Agreement Analysis:**
  - MAE ($^\circ$) and Bland-Altman Limits of Agreement.
  - Explicit documentation: Out-of-plane arm abduction during recovery projected onto a 2D sagittal sensor will show non-linear foreshortening error.
- **E. Failure Handling:**
  - Visibility $< 0.40$ on hip or shoulder sets `valid=False`.

---

### Experiment 7: Body Roll

- **A. Ground Truth Value ($y_f$):**
  - **2D Image-Plane Tilt Ground Truth:** Bilateral shoulder tilt relative to water surface horizontal ($^\circ$).
  - **True 3D Anatomical Trunk Rotation Ground Truth:** Calibrated waterproof 9-DOF IMU continuous roll orientation ($^\circ$).
- **B. Swim Analyzer Value ($\hat{y}_f$):**
  - 2D: `body_roll` ($\arctan2(\Delta y, \Delta x)$ of shoulders).
  - 3D: `body_roll_3d` (torso normal vector cross-product).
- **C. Absolute Error:**
  $$e_f = |\hat{y}_f - y_f| \quad [^\circ]$$
- **D. Agreement Analysis:**
  - **CRITICAL DISTINCTION:** 2D image-plane shoulder tilt must **never** be conflated with true 3D anatomical trunk rotation.
  - SwimAnalyzer's monocular 3D body roll relies on MediaPipe pseudo-depth $Z$. The experiment will separately evaluate:
    1. Agreement between predicted 2D roll and video image-plane shoulder tilt.
    2. Agreement between predicted 3D roll and IMU physical trunk rotation.
- **E. Failure Handling:**
  - Missing either shoulder or either hip collapses the torso plane and invalidates 3D body roll.

---

### Experiment 8: Stroke Phase Timing

- **A. Ground Truth Value ($y_k$):**
  Expert consensus transition frame index $F_{\text{trans}, k}$ and phase percentage $\% \text{Phase}_k$.
- **B. Swim Analyzer Value ($\hat{y}_k$):**
  Predicted transition frame and accumulated phase duration percentage.
- **C. Absolute Error:**
  $$e_{\text{frame}} = |\hat{F}_{\text{trans}} - F_{\text{trans}}| \quad [\text{frames}]$$
  $$e_{\text{pct}} = |\hat{\%}_{\text{phase}} - \%_{\text{phase}}| \quad [\%]$$
- **D. Agreement Analysis:**
  - Event Matching within a $\pm 3\text{ frame}$ tolerance window ($\approx 50\text{ ms}$ at $60\text{ fps}$).
  - Classification metrics:
    $$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}, \quad \text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}, \quad F_1 = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
  - Phase duration MAE in milliseconds.
- **E. Failure Handling:**
  - Phase transitions occurring during frames with low landmark confidence ($< 0.40$) are flagged with low phase confidence.

---

## 4. Scientific Audit of Dataset Limitations & Blocker Analysis

| Factor | Limitation Description | Impact on Validation |
|---|---|---|
| **1. Dataset Availability** | Zero physical ground truth files exist in repository. | Validation experiment blocked. |
| **2. Number of Videos** | 9 raw videos present, but none have reference annotations. | Sample size = 0 for empirical testing. |
| **3. Number of Annotated Cycles** | 0 annotated cycles. | Cannot calculate statistical agreement. |
| **4. Number of Measurements** | 0 paired physical measurements. | Error statistics cannot be computed. |
| **5. Human Annotation Method** | No double-blind digitization protocol has been executed on the video assets. | Inter-rater consensus unavailable. |
| **6. Inter-Rater Agreement** | Unmeasured. | Benchmark human baseline unknown. |
| **7. Metric Errors** | Cannot be reported without ground truth. | Unreported to prevent data fabrication. |
| **8. Failure Cases** | Optical refraction, surface aeration, bubble curtains, and limb self-occlusion cause MediaPipe landmark dropouts. | System safely falls back to `insufficient_data` or `report=None`. |
| **9. Camera Limitations** | Monocular single-view cameras suffer from planar foreshortening; 2D projection collapses 3D kinematics. | Lateral angles cannot measure transverse abduction without distortion. |
| **10. FPS Limitations** | Videos recorded at $30\text{ fps}$ exhibit up to $\pm 33.3\text{ ms}$ temporal quantization error. | Requires minimum $60\text{ fps}$ for reliable phase transition validation. |
| **11. Occlusion Limitations** | Submerged arms and flutter-kicking legs are frequently occluded by air bubbles and swimmer's torso. | Requires temporal smoothing and visibility gating. |
| **12. Smoothing Limitations** | OneEuroFilter reduces landmark jitter, but excessive cutoff frequencies induce phase lag ($> 50\text{ ms}$) on fast turnaround strokes. | Filter parameters must be tuned against reference data. |

---

## 5. Final Conclusion

SwimAnalyzer AI has established a complete, mathematically verified kinematic engine and a formal validation experiment design. However, empirical scientific validation cannot proceed until the physical ground truth dataset specified in `docs/ground_truth_dataset_specification.md` is collected.
