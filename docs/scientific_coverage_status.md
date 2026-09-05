# Scientific Coverage Status

## Overview
This document tracks the completeness of our literature database across demographics, strokes, and metrics. Due to the strict Scientific Evidence Engine rules, demographic groups that lack peer-reviewed literature cannot be given performance percentiles or z-scores.

## Stroke Coverage
*   **Freestyle**: Very High Coverage (Adult Males, Adult Females, Elite, National). Youth coverage requires expansion.
*   **Backstroke**: Moderate Coverage. Needs more specific data for female athletes and amateur competitive levels.
*   **Breaststroke**: Low Coverage. Requires additional literature searches.
*   **Butterfly**: Moderate Coverage (Adult Mixed).

## Demographic Gaps
The following demographics currently trigger `INSUFFICIENT_EVIDENCE` in the UI due to lack of peer-reviewed sources:
*   Youth (Under 10, 11-13) for all strokes except Freestyle (partially).
*   Masters (35+, 55+) for all strokes.
*   Adult Females for Breaststroke.

## Resolution Plan
*   Run the `ScientificUpdaterSystem` periodically with targeted keyword queries (e.g., `"youth backstroke kinematics"`) to discover and ingest papers.
*   Allow the AI to parse Candidate Evidence and have the `ScientificEvidenceValidator` promote it.
*   Ensure that any new papers are fully reviewed for population constraints before being promoted into `evidence_registry.yaml`.
