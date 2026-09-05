# Real-World Stroke Classification Validation Protocol

**Platform**: SwimAnalyzer AI  
**Author**: Lead Computer Vision Architect & Sports Biomechanics Engineer  
**Date**: August 8, 2026  
**Status**: VALIDATION PROTOCOL SPECIFICATION  

---

## 📌 1. Purpose & Scope

This protocol establishes the rigorous, reproducible validation standard for evaluating the **Stroke Classifier** on real-world swimming videos.

The objective is to measure empirical classification accuracy, confusion matrices, and safety gating effectiveness across all four competitive swimming stroke styles (**Freestyle, Backstroke, Breaststroke, Butterfly**) and ambiguous/unsupported clips (**UNKNOWN**).

> [!CAUTION]
> **SCIENTIFIC INTEGRITY RULE**: Synthetic unit tests (e.g. `tests/test_stroke_classifier.py`) verify code logic determinism, but **DO NOT** constitute real-world scientific validation. Real-world validation requires an independent, ground-truth annotated video dataset with diverse camera angles, swimmer demographics, lighting conditions, and occlusion scenarios.

---

## 2. Dataset Composition & Ground-Truth Manifest Standard

### 2.1 Minimum Dataset Diversity Requirements

A scientifically valid evaluation dataset must contain at least **120 independent video clips** (30 clips per stroke style) satisfying the following diversity matrix:

1. **Stroke Representation**:
   - 30 Freestyle clips
   - 30 Backstroke clips
   - 30 Breaststroke clips
   - 30 Butterfly clips
   - 10 Ambiguous / Non-swimming / Drill clips (Negative Control Set)

2. **Camera Angle Variations**:
   - **Side-Pool View** (orthogonal to swimmer trajectory): Min 40%
   - **Front-Pool / Head-On View**: Min 20%
   - **Elevated Pool-Deck View**: Min 20%
   - **Underwater / Water-Surface Split View**: Min 20%

3. **Video Quality & Occlusion Levels**:
   - Clear lighting, high FPS ($\ge 30$ FPS): 50%
   - Low lighting / Water splash occlusion: 30%
   - Partial body occlusion / Low resolution ($< 720p$): 20%

### 2.2 Dataset Manifest Schema

Every validation clip must be registered in `data/validation_dataset_manifest.json` with the following schema:

```json
{
  "video_id": "VAL-FREE-001",
  "filename": "freestyle_side_01.mp4",
  "ground_truth_stroke": "Freestyle",
  "camera_angle": "Side-Pool",
  "resolution": "1920x1080",
  "fps": 60.0,
  "duration_seconds": 4.5,
  "quality_class": "Excellent",
  "has_occlusion": false,
  "swimmer_demographic": "Adult Male",
  "annotator_id": "BIOMECH_EXPERT_1"
}
```

---

## 3. Evaluation Metrics & Confusion Matrix Formulation

### 3.1 Confusion Matrix Structure ($5 \times 5$)

The classifier output is mapped into a $5 \times 5$ confusion matrix including the `UNKNOWN` class:

$$\mathbf{C} = \begin{bmatrix}
c_{FF} & c_{FB} & c_{FBr} & c_{FFly} & c_{FU} \\
c_{BF} & c_{BB} & c_{BBr} & c_{BFly} & c_{BU} \\
c_{BrF} & c_{BrB} & c_{BrBr} & c_{BrFly} & c_{BrU} \\
c_{FlyF} & c_{FlyB} & c_{FlyBr} & c_{FlyFly} & c_{FlyU} \\
c_{UF} & c_{UB} & c_{UBr} & c_{UFly} & c_{UU}
\end{bmatrix}$$

### 3.2 Performance Metrics

For each stroke class $k \in \{\text{Freestyle}, \text{Backstroke}, \text{Breaststroke}, \text{Butterfly}\}$:

1. **Precision ($P_k$)**:
   $$P_k = \frac{TP_k}{TP_k + FP_k}$$

2. **Recall ($R_k$)**:
   $$R_k = \frac{TP_k}{TP_k + FN_k}$$

3. **F1-Score ($F1_k$)**:
   $$F1_k = 2 \cdot \frac{P_k \cdot R_k}{P_k + R_k}$$

4. **Macro-F1 Score**:
   $$\text{Macro-F1} = \frac{1}{4} \sum_{k=1}^{4} F1_k$$

5. **UNKNOWN Rate ($R_{\text{UNKNOWN}}$)**:
   $$R_{\text{UNKNOWN}} = \frac{N_{\text{UNKNOWN}}}{N_{\text{Total}}}$$

6. **High-Confidence Error Rate ($E_{\text{HighConf}}$)**:
   $$E_{\text{HighConf}} = \frac{N(\text{Predicted} \neq \text{GroundTruth} \text{ and } \text{confidence} \ge 0.75)}{N_{\text{Total}}}$$

---

## 4. Target Acceptance Criteria for Real-World Certification

To declare the classifier **Scientifically Validated for Production**, the real-world evaluation must satisfy:

- **Overall Accuracy**: $\ge 90.0\%$
- **Macro-F1 Score**: $\ge 0.88$
- **High-Confidence Error Rate**: $\le 3.0\%$ (Safety Invariant)
- **UNKNOWN Rate on Noise Clips**: $\ge 90.0\%$ (Negative control safety)
