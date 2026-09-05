# Biomechanics Validation Framework

This framework provides CLI validation tooling for comparing computed biomechanical metrics against labeled ground truth data.

> [!IMPORTANT]
> **Scientific Validation Protocol & Ground Truth Specification (Steps 65 & 66)**:  
> - For the formal scientific validation protocol governing priority metrics, see [`docs/scientific_validation_protocol.md`](../docs/scientific_validation_protocol.md).
> - For the empirical Ground Truth dataset requirements and 24-trial specification, see [`docs/ground_truth_dataset_specification.md`](../docs/ground_truth_dataset_specification.md).
> - For the formal machine-readable annotation schema, see [`data/reference/ground_truth_dataset_schema.json`](../data/reference/ground_truth_dataset_schema.json).
> - For experiment design and empirical status, see [`docs/scientific_validation_results.md`](../docs/scientific_validation_results.md).
> 
> *Note:* The local `test_data/test_video_labels.json` fixture in this directory is a 17-line synthetic mock used exclusively for unit testing arithmetic calculations (`tests/test_validation_math.py`). It is not an empirical swimming dataset.

## Workflow

1. Create a manually labeled JSON file for each benchmark video (e.g., `video01_labels.json`).
2. Run the pipeline to generate a prediction JSON file (e.g., `video01_predictions.json`).
3. Run the CLI validator:

```bash
python validate.py --labels video01_labels.json --predictions video01_predictions.json
```

## Report Generation

The CLI tool automatically generates two reports in the current working directory:
- `validation_report.txt`: A human-readable breakdown of metrics, passing status, True/False positives, and F1 scores.
- `validation_report.json`: A machine-readable dump for integration into CI/CD pipelines.

## Dataset & Label Schema

Both the Ground Truth labels and the Predictions use the exact same schema. 

```json
{
    "stroke_rate": 40.0,
    "stroke_length": 1.5,
    "body_roll": 35.0,
    "kick_frequency": 2.0,
    "stroke_cycles": 10,
    "events": [
        {"frame": 10, "phase": "Entry"},
        {"frame": 20, "phase": "Catch"},
        {"frame": 30, "phase": "Pull"}
    ]
}
```

### Supported Metrics & Tolerances

To account for minor human error in manual labeling, the validation engine allows the following deterministic tolerances before marking a metric as a `FAIL` or `False Negative`.

| Metric | Tolerance | Description |
|---|---|---|
| **Stroke Rate** | ± 2.0 spm | Absolute difference in strokes per minute. |
| **Stroke Length** | ± 0.15 | Absolute difference in relative units. |
| **Kick Frequency** | ± 0.3 Hz | Absolute difference in Hertz. |
| **Body Roll** | ± 5.0 deg | Absolute difference in maximum roll angle. |
| **Stroke Cycles** | ± 1.0 | Allowed cycle count variance. |
| **Phase Events** | ± 5 frames | Maximum temporal distance between predicted phase transition and ground truth. |

## Metric Definitions

### Continuous Data
- **Absolute Error:** `abs(Prediction - Ground Truth)`
- **Mean Absolute Error (MAE):** The average absolute error across all global continuous metrics (Rate, Length, Roll, Kick, Cycles).
- **RMSE:** Root Mean Square Error across continuous metrics.

### Phase Detection (Categorical)
- **True Positive (TP):** Predicted phase transition occurs within 5 frames of a Ground Truth phase transition.
- **False Negative (FN):** Ground truth phase transition was completely missed, or detected outside the 5 frame window.
- **False Positive (FP):** A phase transition was predicted, but no matching ground truth event exists within the 5 frame window.
- **Accuracy:** `TP / Total Expected Ground Truth Events`.
- **F1 Score:** Harmonic mean of Precision and Recall (`2 * (P * R) / (P + R)`).
