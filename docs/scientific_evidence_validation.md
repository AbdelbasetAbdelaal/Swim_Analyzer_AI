# Scientific Evidence Validation

## Overview
The `ScientificEvidenceValidator` enforces deterministic correctness for any extracted literature data. AI is used solely for extraction and text processing (Candidate Evidence), and all results must pass stringent validation rules before entering the active knowledge base.

## Rule Checks
The validator performs the following rule checks when promoting Candidate Evidence to Validated Evidence:

1. **Source Verifiability (`test_source_verifiability`)**
   *   Candidate must link to a valid source in `ScientificSourceRegistry`.
   *   The source must have `verification_status` of `VERIFIED_CORRECT` or `PEER_REVIEWED_ABSTRACT_ONLY`.

2. **Metric Definition Consistency (`test_metric_definition_consistency`)**
   *   The metric name must be in the approved taxonomy (e.g., `stroke_rate`, `stroke_length`, `kick_frequency`).
   *   The unit must match strictly. Conversions are allowed (e.g., sec/cycle to spm) provided they use exact formulas.
   *   Fuzzy/unknown definitions are flagged as `DEFINITION_MISMATCH`.

3. **Demographic Constraints (`test_demographic_constraints`)**
   *   Age ranges, sex, and stroke type must not "leak."
   *   e.g., Cannot use data from a study of adult males and apply it to female youths.

4. **Sample Size Requirements (`test_sample_size_requirements`)**
   *   Any candidate with a sample size `< 8` is rejected (`INSUFFICIENT_SAMPLE_SIZE`).

5. **Value Reasonability (`test_value_reasonability`)**
   *   Values must fall within physically possible bounds for human swimming (e.g., `stroke_rate` cannot be 200 spm).

## Quality Categories
*   **LEVEL A**: Directly supported, large sample size, exact metric definition.
*   **LEVEL B**: Acceptable sample size, minor derivations, robust definitions.
*   **LEVEL C**: Marginally acceptable, older data, small samples.
*   **LEVEL D**: Conflicting or insufficient data.
*   **LEVEL E**: Unverified/Placeholder.

Any record marked `LEVEL_D` or `LEVEL_E` will NOT be allowed to generate a Z-score or Percentile ranking for a user in the Benchmark Engine.
