# Scientific Validation Protocol for SwimAnalyzer AI

**Document Version:** 1.0.0  
**Effective Date:** 2026-09-05  
**Pose Estimation Engine:** MediaPipe Tasks API (`PoseLandmarker`) — Single Backend Invariant  
**Document Purpose:** Define a rigorous, reproducible scientific validation protocol for prioritized swimming biomechanics metrics.

---

## 1. Scientific Principles & Safety Policy

1. **Distinction of Correctness Layers:**
   - **Layer A (Mathematical Correctness):** Formulas are derived from standard vector algebra, geometry, and kinematic principles without numerical or algebraic errors.
   - **Layer B (Implementation Correctness):** Code executes predictably, handles nulls and NaN edge-cases safely, clamps invalid physical domains, and matches the mathematical derivation.
   - **Layer C (Empirical Scientific Validation):** Metrics are quantitatively compared against independent, gold-standard Physical Ground Truth (e.g., underwater optoelectronic 3D motion capture, synchronized multi-sensor IMU arrays, or certified multi-expert manual digitization) on representative swimming cohorts.

2. **Ground Truth Integrity Gate:**
   - Ground Truth **must never be manufactured or simulated**.
   - Synthetic unit-test fixtures (e.g., `validation/test_data/test_video_labels.json`) test algorithmic execution, **not** empirical validity.
   - Population normative registries (e.g., `data/reference/swimming_reference_data_v2_scientific_registry.csv`) provide macro-level race statistics (e.g., Born et al., 2022), **not** video-paired kinematic ground truth.
   - When empirical ground truth is unavailable, the metric **must** be classified as:
     $$\textbf{NOT\_VALIDATED — INSUFFICIENT GROUND TRUTH}$$
   - No metric may be described as "scientifically validated" in the absence of peer-reviewed empirical validation data.

3. **Threshold Definition Policy:**
   - Numerical acceptance thresholds (e.g., acceptable error margins or repeatability coefficients) must **not** be invented.
   - If peer-reviewed literature and empirical validation datasets within the repository do not provide an established benchmark, the criterion must be explicitly recorded as:
     $$\textbf{THRESHOLD NOT YET ESTABLISHED}$$

---

## 2. Priority Metrics Validation Protocols

The following 8 priority metrics represent the core kinematic, temporal, and angular indicators of the SwimAnalyzer AI engine.

---

### Protocol 1: Stroke Rate (SR)

- **Implementation Location:** `analysis/strategies/*_stroke_analyzer.py`, `calculate_global_metrics`
- **Mathematical Definition:**
  $$\text{SR} = \frac{N_{\text{cycles}}}{\Delta t / 60} = \frac{60 \times N_{\text{cycles}}}{\sum_{i=1}^{N_{\text{cycles}}} T_{\text{cycle}, i}}$$
  where $N_{\text{cycles}}$ is the count of completed stroke cycles across active swimming duration $\Delta t$ (seconds).
- **Required MediaPipe Landmarks:**
  - Freestyle / Backstroke: Wrists (15, 16), Shoulders (11, 12)
  - Breaststroke: Wrists (15, 16), Ankles (27, 28)
  - Butterfly: Wrists (15, 16), Shoulders (11, 12)
- **Coordinate System:** Temporal domain derived from frame indices and video timestamps ($t_k = k / \text{FPS}$). Landmark spatial extrema in normalized $[0, 1]^2$ plane.
- **Units:** Strokes per minute (`spm`).
- **Required FPS / Timestamp Assumptions:**
  - Video FPS $\ge 30\text{ fps}$ (preferably $\ge 60\text{ fps}$ to reduce peak-detection temporal quantization to $< 16.7\text{ ms}$).
  - Strictly uniform frame rate (CFR) or frame-accurate hardware timestamps.
- **Required Camera / View Conditions:**
  - Lateral sagittal view (side-on) or stationary elevated diagonal view with unobstructed view of hand entries and exits.
- **Applicable Strokes:** Freestyle, Backstroke, Breaststroke, Butterfly.
- **Expected Measurement Range (Literature):**
  - $20.0\text{ to }75.0\text{ spm}$ across all competitive swimming strokes (Craig & Pendergast, 1979; Maglischo, 2003; Born et al., 2022).
- **Ground Truth Reference Required:**
  - Frame-by-frame event logging from high-speed reference video ($\ge 100\text{ fps}$) or synchronized base-of-stroke timing systems operated by two independent certified biomechanists.
- **Ground Truth Acquisition Method:**
  - Two independent raters identify the exact video frame of hand entry (or initial outsweep) for every completed cycle. Discrepancies $> 2\text{ frames}$ adjudicated by consensus. Ground truth cycle duration $T_i = (F_{\text{entry}, i+1} - F_{\text{entry}, i}) / \text{FPS}_{\text{ref}}$.
- **Error Metric:**
  - Mean Absolute Error (MAE in spm), Root Mean Squared Error (RMSE in spm), Mean Absolute Percentage Error (MAPE), Bland-Altman 95% Limits of Agreement.
- **Acceptance Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Repeatability Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Conditions Under Which Marked NOT VALIDATED:**
  - Paired ground truth video timing labels are absent.
  - Video duration contains fewer than 2 complete consecutive stroke cycles.
  - Landmark visibility score $< 0.40$ for wrists or shoulders across $\ge 20\%$ of cycle frames.
  - Swimmer is executing turns, push-offs, or underwater dolphin kicks rather than clean surface swimming.

---

### Protocol 2: Average Cycle Duration

- **Implementation Location:** `analysis/strategies/*_stroke_analyzer.py` (`avg_cycle_duration_ms`)
- **Mathematical Definition:**
  $$\bar{T}_{\text{cycle}} = \frac{1}{N_{\text{cycles}}} \sum_{i=1}^{N_{\text{cycles}}} T_{\text{cycle}, i} = \frac{60}{\text{SR}} \times 1000\text{ ms}$$
- **Required MediaPipe Landmarks:** Same as Stroke Rate (Wrists 15, 16; Shoulders 11, 12).
- **Coordinate System:** Temporal sequence based on frame timestamps.
- **Units:** Milliseconds (`ms`).
- **Required FPS / Timestamp Assumptions:** $\ge 30\text{ fps}$, constant frame rate.
- **Required Camera / View Conditions:** Continuous lateral visibility of hand entry and exit boundaries.
- **Applicable Strokes:** Freestyle, Backstroke, Breaststroke, Butterfly.
- **Expected Measurement Range (Literature):**
  - $800\text{ to }3000\text{ ms}$ (0.80 s to 3.00 s per cycle) depending on stroke, race distance, and sex (Craig & Pendergast, 1979; Seifert et al., 2007).
- **Ground Truth Reference Required:**
  - Synchronized high-speed video timecodes (SMPTE) or swimming touchpad cycle chronometry.
- **Ground Truth Acquisition Method:**
  - Frame-accurate rater marking of stroke transition boundaries on reference video footage.
- **Error Metric:**
  - MAE ($\text{ms}$), RMSE ($\text{ms}$), Pearson correlation coefficient ($r$).
- **Acceptance Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Repeatability Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Conditions Under Which Marked NOT VALIDATED:**
  - Paired ground truth cycle timecodes are absent.
  - Fewer than 2 completed cycles detected.
  - Temporal jitter $> 0.10\text{ s}$ due to severe frame dropping in recording.

---

### Protocol 3: Stroke Length / DPS Proxy

- **Implementation Location:** `analysis/strategies/freestyle_biomechanics_calculator.py` (`calculate_global_metrics`)
- **Mathematical Definition:**
  - **Uncalibrated Hand Excursion Proxy:**
    $$D_{\text{excursion}} = \frac{1}{N_{\text{cycles}}} \sum_{i=1}^{N} \left| x_{\text{wrist}}(t_{\text{finish}}) - x_{\text{wrist}}(t_{\text{catch}}) \right| \quad [\text{body lengths or normalized}]$$
  - **Calibrated Distance Per Stroke (True Physical DPS):**
    $$\text{DPS} = \frac{v_{\text{clean\_swim}}}{\text{SR} / 60} = \frac{\Delta x_{\text{COM}}}{\text{cycle}} \quad [\text{meters}]$$
- **Required MediaPipe Landmarks:**
  - Wrists (15, 16), Shoulders (11, 12), Hips (23, 24).
- **Coordinate System:**
  - Normalized image coordinates $[0, 1]$ if uncalibrated (`relative_body_normalized`).
  - Metric world coordinates ($x, y$ in meters) if lane markers / pool floor grid are calibrated.
- **Units:** Meters per cycle (`m`) or body length units per cycle (`BL`).
- **Required FPS / Timestamp Assumptions:** $\ge 30\text{ fps}$.
- **Required Camera / View Conditions:**
  - Fixed stationary camera orthogonal to swimming lane with calibrated physical distance markers (lane line floats or pool tiles).
  - Panning cameras are strictly prohibited unless compensated by calibrated 2D planar homography or background optical flow tracking.
- **Applicable Strokes:** Freestyle, Backstroke, Breaststroke, Butterfly.
- **Expected Measurement Range (Literature):**
  - $1.40\text{ to }2.60\text{ m/stroke}$ for calibrated competitive swimmers (Smith et al., 2002; Born et al., 2022).
  - $0.80\text{ to }1.50\text{ body lengths}$ for hand reach excursion proxy.
- **Ground Truth Reference Required:**
  - Submerged or aerial calibrated motion capture tracking anatomical Center of Mass (COM), or laser/tachometer speed-cable displacement system.
- **Ground Truth Acquisition Method:**
  - Whole-body segment model tracking the displacement of the body center of mass across consecutive complete stroke cycles against metric lane markers.
- **Error Metric:**
  - MAE (meters or body lengths), RMSE, percentage deviation from true COM translation.
- **Acceptance Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Repeatability Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Conditions Under Which Marked NOT VALIDATED:**
  - Absence of metric pool calibration or paired COM ground truth data.
  - Camera is panning or tilting without geometric ego-motion compensation.
  - Presenting hand reach excursion as equivalent to whole-body center of mass displacement.

---

### Protocol 4: Elbow Angle

- **Implementation Location:** `analysis/strategies/freestyle_biomechanics_calculator.py` (`_calculate_joint_angles`, `calculate_angle`)
- **Mathematical Definition:**
  $$\vec{u} = P_{\text{shoulder}} - P_{\text{elbow}}, \quad \vec{v} = P_{\text{wrist}} - P_{\text{elbow}}$$
  $$\theta_{\text{elbow}} = \arccos\left(\frac{\vec{u} \cdot \vec{v}}{\|\vec{u}\| \|\vec{v}\|}\right) \times \frac{180}{\pi}$$
  clamped to $[0^\circ, 180^\circ]$.
- **Required MediaPipe Landmarks:**
  - Left: Shoulder (11), Elbow (13), Wrist (15)
  - Right: Shoulder (12), Elbow (14), Wrist (16)
- **Coordinate System:** 2D normalized image space $[0, 1]^2$ on camera sensor plane.
- **Units:** Degrees ($^\circ$).
- **Required FPS / Timestamp Assumptions:** $\ge 30\text{ fps}$.
- **Required Camera / View Conditions:**
  - True lateral sagittal camera orthogonal to the swimmer's stroke plane ($< 15^\circ$ out-of-plane deviation).
  - Clean underwater viewing window or underwater submersible enclosure.
- **Applicable Strokes:** Freestyle, Backstroke, Breaststroke, Butterfly.
- **Expected Measurement Range (Literature):**
  - $40^\circ\text{ to }180^\circ$ (Maglischo, 2003; Psycharakis & Sanders, 2008). High-elbow catch typically reaches $90^\circ\text{ to }120^\circ$.
- **Ground Truth Reference Required:**
  - Calibrated underwater multi-camera 3D optoelectronic motion capture (e.g., Qualisys / Vicon underwater systems) or frame-by-frame manual goniometric digitization by expert biomechanists.
- **Ground Truth Acquisition Method:**
  - Manual digitization of lateral epicondyle of humerus, acromion process, and ulnar styloid across 3 repeated trials, or 3D retroreflective underwater marker trajectories reconstructed in calibrated 3D space.
- **Error Metric:**
  - MAE ($^\circ$), RMSE ($^\circ$), Bland-Altman 95% Limits of Agreement, Intraclass Correlation Coefficient $ICC(2, 1)$.
- **Acceptance Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Repeatability Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Conditions Under Which Marked NOT VALIDATED:**
  - Paired 3D mocap or manual goniometric annotations are absent.
  - Swimmer is viewed from front/diagonal angle ($> 20^\circ$ non-orthogonal), causing severe 2D perspective foreshortening.
  - Optical refraction distortion at water-air interface is uncorrected.
  - MediaPipe landmark visibility $< 0.50$ for elbow or wrist.

---

### Protocol 5: Knee Angle

- **Implementation Location:** `analysis/strategies/freestyle_biomechanics_calculator.py` (`_calculate_joint_angles`, `calculate_angle`)
- **Mathematical Definition:**
  $$\vec{u} = P_{\text{hip}} - P_{\text{knee}}, \quad \vec{v} = P_{\text{ankle}} - P_{\text{knee}}$$
  $$\theta_{\text{knee}} = \arccos\left(\frac{\vec{u} \cdot \vec{v}}{\|\vec{u}\| \|\vec{v}\|}\right) \times \frac{180}{\pi}$$
  clamped to $[0^\circ, 180^\circ]$.
- **Required MediaPipe Landmarks:**
  - Left: Hip (23), Knee (25), Ankle (27)
  - Right: Hip (24), Knee (26), Ankle (28)
- **Coordinate System:** 2D normalized image space $[0, 1]^2$.
- **Units:** Degrees ($^\circ$).
- **Required FPS / Timestamp Assumptions:** $\ge 30\text{ fps}$.
- **Required Camera / View Conditions:** Lateral underwater sagittal view with clear view of lower extremities beneath surface turbulence.
- **Applicable Strokes:** Freestyle, Backstroke, Breaststroke, Butterfly.
- **Expected Measurement Range (Literature):**
  - $30^\circ\text{ to }180^\circ$ (Maglischo, 2003). Freestyle flutter kick flexion typically maintains $130^\circ\text{ to }175^\circ$; Breaststroke recovery flexion reaches $40^\circ\text{ to }60^\circ$.
- **Ground Truth Reference Required:**
  - Underwater optoelectronic 3D motion capture or expert manual digitization of knee joint center.
- **Ground Truth Acquisition Method:**
  - Synchronized underwater camera array tracking greater trochanter, lateral femoral epicondyle, and lateral malleolus.
- **Error Metric:**
  - MAE ($^\circ$), RMSE ($^\circ$), $ICC(2, 1)$.
- **Acceptance Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Repeatability Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Conditions Under Which Marked NOT VALIDATED:**
  - Absence of paired underwater motion capture or manual labels.
  - Heavy aeration / bubble curtain from kick completely occludes knees or ankles.
  - MediaPipe landmark visibility $< 0.40$ for knee or ankle joints.

---

### Protocol 6: Shoulder Angle

- **Implementation Location:** `analysis/strategies/freestyle_biomechanics_calculator.py` (`_calculate_joint_angles`)
- **Mathematical Definition:**
  $$\vec{u} = P_{\text{hip}} - P_{\text{shoulder}}, \quad \vec{v} = P_{\text{elbow}} - P_{\text{shoulder}}$$
  $$\theta_{\text{shoulder}} = \arccos\left(\frac{\vec{u} \cdot \vec{v}}{\|\vec{u}\| \|\vec{v}\|}\right) \times \frac{180}{\pi}$$
  clamped to $[0^\circ, 180^\circ]$.
- **Required MediaPipe Landmarks:**
  - Left: Hip (23), Shoulder (11), Elbow (13)
  - Right: Hip (24), Shoulder (12), Elbow (14)
- **Coordinate System:** 2D normalized image plane.
- **Units:** Degrees ($^\circ$).
- **Required FPS / Timestamp Assumptions:** $\ge 30\text{ fps}$.
- **Required Camera / View Conditions:** Lateral sagittal view.
- **Applicable Strokes:** Freestyle, Backstroke, Breaststroke, Butterfly.
- **Expected Measurement Range (Literature):**
  - $30^\circ\text{ to }180^\circ$ (Maglischo, 2003). Near $180^\circ$ during forward reach / entry extension; drops to $60^\circ\text{ to }90^\circ$ during catch/pull.
- **Ground Truth Reference Required:**
  - Calibrated 3D motion capture or manual frame-by-frame joint digitization.
- **Ground Truth Acquisition Method:**
  - 3D tracking of trunk longitudinal vector vs. humerus segment vector.
- **Error Metric:**
  - MAE ($^\circ$), RMSE ($^\circ$), Bland-Altman Limits of Agreement.
- **Acceptance Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Repeatability Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Conditions Under Which Marked NOT VALIDATED:**
  - Ground truth motion capture data absent.
  - Arm abduction/adduction outside sagittal plane is projected as false 2D flexion/extension.
  - Landmark visibility $< 0.40$.

---

### Protocol 7: Body Roll

- **Implementation Location:**
  - 2D Proxy: `analysis/strategies/freestyle_biomechanics_calculator.py` (`body_roll`)
  - 3D Vector: `analysis/strategies/freestyle_biomechanics_calculator.py` (`body_roll_3d`)
- **Mathematical Definition:**
  - **2D Shoulder Line Tilt:**
    $$\theta_{\text{roll, 2D}} = \left| \arctan2(\Delta y_{\text{shoulders}}, \Delta x_{\text{shoulders}}) \times \frac{180}{\pi} \right|$$
  - **3D Torso Normal Roll:**
    $$\vec{s} = P_{\text{R\_shoulder}} - P_{\text{L\_shoulder}}, \quad \vec{v}_{\text{spine}} = P_{\text{mid\_hip}} - P_{\text{mid\_shoulder}}$$
    $$\vec{n}_{\text{torso}} = \frac{\vec{s} \times \vec{v}_{\text{spine}}}{\|\vec{s} \times \vec{v}_{\text{spine}}\|}, \quad \theta_{\text{roll, 3D}} = \arcsin\left(\frac{n_x}{\sqrt{n_x^2 + n_y^2}}\right)$$
- **Required MediaPipe Landmarks:**
  - Left Shoulder (11), Right Shoulder (12), Left Hip (23), Right Hip (24).
- **Coordinate System:**
  - 2D: Camera sensor image plane.
  - 3D: Camera-relative 3D coordinate space with monocular pseudo-depth $Z$.
- **Units:** Degrees ($^\circ$).
- **Required FPS / Timestamp Assumptions:** $\ge 30\text{ fps}$.
- **Required Camera / View Conditions:**
  - Frontal (head-on) or longitudinal tracking camera provides ideal orientation. Lateral view depends critically on $Z$ coordinate accuracy.
- **Applicable Strokes:** Freestyle and Backstroke.
- **Expected Measurement Range (Literature):**
  - Peak body roll $25^\circ\text{ to }65^\circ$ to each side (Cappaert et al., 1995; Psycharakis & Sanders, 2010; Gonjo et al., 2020).
- **Ground Truth Reference Required:**
  - Calibrated, synchronized waterproof 9-DOF Inertial Measurement Units (IMU: triaxial accelerometer + gyroscope + magnetometer) affixed to thoracic spine/sacrum, or 3D underwater motion capture.
- **Ground Truth Acquisition Method:**
  - Fused orientation quaternion from calibrated IMUs sampled at $\ge 100\text{ Hz}$, aligned with swimmer's anatomical axes.
- **Error Metric:**
  - Peak Roll Angle Error ($^\circ$), Waveform Root Mean Square Difference (RMSD), Waveform Cross-Correlation Coefficient.
- **Acceptance Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Repeatability Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Conditions Under Which Marked NOT VALIDATED:**
  - Synchronized IMU or 3D mocap data absent.
  - Monocular MediaPipe $Z$ depth exhibits scale compression or inversion due to water turbidity/reflection.
  - Swimmer yaw (turning off track) is conflated with roll.

---

### Protocol 8: Stroke Phase Timing

- **Implementation Location:** `analysis/strategies/*_stroke_analyzer.py` (`stroke_phase`, `time_in_phases`)
- **Mathematical Definition:**
  $$\Delta t_{\text{phase } k} = \sum_{f \in \text{Phase}_k} \Delta t_f, \quad \% \text{Phase}_k = \frac{\Delta t_{\text{phase } k}}{T_{\text{cycle}}} \times 100\%$$
- **Required MediaPipe Landmarks:** Wrists (15, 16), Shoulders (11, 12), Hips (23, 24).
- **Coordinate System:** Discrete categorical phase state machine over frame sequence.
- **Units:** Seconds (`s`), frames, and cycle duration percentage (`%`).
- **Required FPS / Timestamp Assumptions:** $\ge 30\text{ fps}$ (preferably $\ge 50\text{ fps}$ per Chollet et al., 2000).
- **Required Camera / View Conditions:** Lateral sagittal underwater and surface view capturing hand entry, transition to backward propulsion, and hand exit.
- **Applicable Strokes:** Freestyle, Backstroke, Breaststroke, Butterfly.
- **Expected Measurement Range (Literature):**
  - Freestyle: Entry/Catch $20\text{--}35\%$, Pull/Push $40\text{--}55\%$, Recovery $15\text{--}25\%$ (Chollet et al., 2000).
  - Breaststroke: Glide $20\text{--}40\%$, Kick $25\text{--}35\%$ (Leblanc et al., 2005).
- **Ground Truth Reference Required:**
  - Independent frame-by-frame manual phase labeling by at least two certified swimming biomechanists.
- **Ground Truth Acquisition Method:**
  - Double-blind annotation of phase transition frames according to standardized biomechanical landmarks (e.g., first backward motion of wrist = Catch start; maximum hand depth = Pull-to-Push transition; hand exit from water = Recovery start). Inter-rater agreement evaluated via Cohen's Kappa ($\kappa \ge 0.85$).
- **Error Metric:**
  - Transition Frame Absolute Error ($|\Delta F|$), Phase Duration MAE (ms), Precision, Recall, F1-Score at tolerance window $\pm 3\text{ frames}$.
- **Acceptance Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Repeatability Criterion:** **THRESHOLD NOT YET ESTABLISHED**
- **Conditions Under Which Marked NOT VALIDATED:**
  - Paired manual event ground truth labels absent.
  - Water surface splash prevents unambiguous identification of hand entry/exit.
  - Frame rate $< 30\text{ fps}$, introducing temporal quantization ambiguity $> 66\text{ ms}$.

---

## 3. Machine-Readable Protocol Companion

A machine-readable specification conforming strictly to this protocol is recorded at:  
`data/reference/scientific_validation_protocol.json`
