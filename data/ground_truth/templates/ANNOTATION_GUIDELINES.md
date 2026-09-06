# Human Ground Truth Double-Blind Annotation Protocol

## Scientific Principles

To ensure complete empirical validity and eliminate bias, all Ground Truth annotations must adhere to this double-blind manual protocol:

1. **Physical Video Asset:**
   - Annotators must watch the verified raw swimming video from data/ground_truth/raw/<stroke>/GT-*.mp4.
   - Video checksum must match data/ground_truth/metadata/asset_verification_audit.json.

2. **Rater Independence:**
   - Rater A and Rater B are distinct, qualified biomechanics experts (nnotator_id != secondary_annotator_id).
   - Rater A annotates independently without observing or discussing with Rater B.
   - Rater B annotates independently without observing or discussing with Rater A.

3. **Complete Blinding to AI Output:**
   - Neither Rater A nor Rater B has access to Swim Analyzer AI model outputs, predictions, keypoint coordinates, technique scores, or analysis reports.
   - The annotation files must not contain any AI model fields (erify_content_level_blinding).

4. **Timestamp & Setup Recording:**
   - Both annotators must record their local/UTC timestamp when the annotation session takes place.
   - Future-dated timestamps are automatically rejected by ingestion gates.

5. **Cycle Boundary Criteria:**
   - Annotate at least 3 clean, complete, continuous swimming cycles.
   - Mark start_frame and end_frame for each cycle.
   - Mark phase transitions (catch, pull, ecovery) within each cycle.

6. **Preservation of Raw Audit Files:**
   - Once completed, the raw rater files are saved to:
     - data/ground_truth/quality_control/<sample_id>/rater_A.json
     - data/ground_truth/quality_control/<sample_id>/rater_B.json
   - These raw audit files remain immutable.

7. **Quality Control & Ingestion:**
   - Execute python tools/import_human_annotations.py.
   - Discrepancies between raters must satisfy:
     - Temporal boundary discrepancy: $\le 2$ frames.
     - Continuous metric discrepancies: within operational thresholds.
   - If discrepancies exceed thresholds, an independent referee conducts formal adjudication (djudication.json).
   - If QC passes, a consensus record is created and ingested into data/ground_truth/manifests/ground_truth_manifest.json.
