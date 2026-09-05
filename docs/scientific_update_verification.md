# Scientific Update Verification

## Overview
The pipeline that dynamically fetches and registers new scientific literature runs on an automated schedule (or manual trigger). It is crucial that this process does not corrupt the `ScientificSourceRegistry` or `ScientificEvidenceRegistry`.

## Verification Steps
When the `ScientificUpdaterService` runs:
1. **Deduplication Check**: Ensures a paper (by DOI or PMID) does not already exist in the registry.
2. **PMC Fetching**: Attempts to retrieve full-text open-access papers from EuropePMC/PubMed Central.
3. **Extraction**: A Gemini extraction process generates candidate evidence blocks from the text.
4. **Validation Check**: The candidate is passed into the `ScientificEvidenceValidator`. If the extraction fails the strict domain rules, it is rejected and logged.
5. **Promotion**: If it passes, the new Source is added to `source_registry.yaml` and the Evidence is added to `evidence_registry.yaml`.
6. **Re-aggregation**: `ScientificBenchmarkBuilder` recompiles all `yaml` benchmarks using the newly updated evidence base.

## Audit Commands
To manually run safety audits against the current knowledge base, use pytest:

```bash
# Verify the entire provenance linkage (no dangling source IDs, no missing metadata)
python -m pytest tests/test_literature_provenance_verification.py -v

# Verify the evidence extraction and aggregation logic
python -m pytest tests/test_scientific_extraction_pipeline.py -v

# Verify that UI constraints and safety rules hold under the current registry state
python -m pytest tests/test_phase7_5_ui_safety.py -v
python -m pytest tests/test_population_reference_expansion.py -v
```

If these tests pass, the updated `benchmarks/*.yaml` datasets are safe for production deployment.
