# SwimAnalyzer AI — Complete User Guide & Feature Manual

Welcome to **SwimAnalyzer AI**, an advanced sports analytics platform designed to provide evidence-based, scientifically validated swimming technique analysis.

---

## 📌 Table of Contents
1. [Getting Started & Login](#1-getting-started--login)
2. [Video Analysis Workflow](#2-video-analysis-workflow)
3. [Interpreting Analysis Results](#3-interpreting-analysis-results)
4. [Video Data Reliability Breakdown](#4-video-data-reliability-breakdown)
5. [Population Benchmarks & Evidence Cards](#5-population-benchmarks--evidence-cards)
6. [Managing Athlete Rosters](#6-managing-athlete-rosters)
7. [Session-to-Session Comparison](#7-session-to-session-comparison)
8. [Downloading PDF Reports & Data](#8-downloading-pdf-reports--data)
9. [Scientific Trustworthiness & Safety Rules](#9-scientific-trustworthiness--safety-rules)

---

## 1. Getting Started & Login

### Launching the Web App
Execute the following command in your terminal:
```bash
streamlit run app/streamlit_app.py
```
Open `http://localhost:8501` in your browser.

### Coach Authentication
- Log in using your registered coach credentials.
- **Login Instructions**: The system requires a secure bootstrap configuration via the `.env` file. Copy `.env.example` to `.env` and set `SWIM_ANALYZER_BOOTSTRAP_COACH_USERNAME` and `SWIM_ANALYZER_BOOTSTRAP_COACH_PASSWORD` with secure values to use for your initial login.
- Logging in isolates your athlete roster and session logs from other coaching staff.

---

## 2. Video Analysis Workflow

1. **Select Navigation**: Click **🏊‍♂️ Video Analysis** from the sidebar menu.
2. **Assign Athlete**: Select an athlete from your roster dropdown or choose **Guest Swimmer**.
3. **Upload Video**: Click **Browse Files** and upload a video file (`.mp4`, `.mov`, `.avi`).
4. **Mandatory Swimming Stroke Selection**:
   - In the sidebar dropdown **`Select Swimming Stroke *`**, choose the exact stroke style performed in the video:
     - 🏊 **`Freestyle`**
     - 🏊 **`Backstroke`**
     - 🏊 **`Breaststroke`**
     - 🏊 **`Butterfly`**
   - *Note*: You must explicitly select a stroke style. Leaving the option on `-- Select Swimming Stroke --` will display an error banner (`❌ Please select the swimming stroke before starting the analysis.`) and block processing.
5. **Adjust Settings** (Sidebar):
   - **Effective FPS**: Verified frame rate.
   - **Visualization Mode**: `User Mode` (clean overlay), `Coach Mode` (detailed metrics overlay), or `Developer Mode` (raw landmark debug metrics).
6. **Analyze**: Click **Analyze Swimming Technique**.
   - Processing executes at 100% full natural native video FPS (`selected_stride = 1`), analyzing every single frame.

---

## 3. Interpreting Analysis Results

Analysis results are presented across 6 full-width tabs:

### 📋 Overview Tab
- **Annotated Video**: High-definition video with pose skeleton tracking rendered via native Streamlit player (`st.video`).
- **Swimming Stroke Badge**: Displays the exact user-selected stroke title and icon.
- **Overall Technique Score**: Composite 0–100 technique score.
- **Video Quality Score**: Evaluates resolution, frame rate, camera stability, and lighting.
- **Analysis Reliability**: Displays overall data quality rating (`High`, `Medium`, `Low`).
- **Scientific Confidence**: Shows evidence confidence rating (`High`, `Medium`, `Low`).

---

## 4. Video Data Reliability Breakdown

Expand the **🔬 Analysis Data Reliability & Pose Tracking Quality Breakdown** drawer to inspect video quality criteria:

- **Frame Coverage**: Percentage of total frames with valid tracking data.
- **Pose Validity**: Ratio of frames meeting minimum landmark confidence thresholds.
- **Landmark Visibility**: Average visibility score across body keypoints.
- **Temporal Stability**: Smoothness and continuity of phase detection.
- **Cycle Quality**: Rating based on total detected complete stroke cycles.
- **Data Quality Notes**: Displays specific warnings (e.g., *"Insufficient valid pose frames"*, *"Swimmer leaving frame or excessive occlusion detected"*).

---

## 5. Population Benchmarks & Evidence Cards

Navigate to the **📊 Population Benchmarks** tab to view population reference comparisons:

### Demographic Compatibility Guard
- **Valid Population**: Adult Competitive Male Swimmers (Age 18–25).
- **Non-Compatible Athletes** (Female, Youth U10/U13/U17, Masters >35):
  - Displays a warning banner: `"⚠️ No validated reference population is currently available for this athlete's demographic group."`

---

## 6. Managing Athlete Rosters

Click **👥 Athlete Profiles** in the sidebar:
- Add, edit, or search athlete profiles.
- View training history, preferred stroke, age group, and notes.

---

## 7. Session-to-Session Comparison

Click **📊 Session Comparison** in the sidebar:
- Select two sessions for an athlete (e.g., Baseline vs Recent).
- Side-by-side metric comparison chart and flaw resolution report.

---

## 8. Downloading PDF Reports & Data

In the **📥 Downloads** tab:
- Download full session PDF report via `PDFReportService` displaying `Swimming Stroke: <User Selected>` and `Analysis Reliability`.
- Export JSON analysis report and metadata.

---

## 9. Scientific Trustworthiness & Safety Rules

- **Deterministic Pipeline**: 100% local Python execution. No LLM hallucinations or uncalibrated scores.
- **Single Source of Truth**: User selected stroke is preserved throughout the entire processing pipeline.
- **No Fabricated Fallbacks**: Values remain `INSUFFICIENT_EVIDENCE` when data is missing or low quality.
