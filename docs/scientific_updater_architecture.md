# Scientific Updater Architecture

## 1. Overview
The Scientific Updater System is a highly deterministic, zero-fabrication engine designed to ingest peer-reviewed biomechanics literature from external academic APIs (PubMed, PMC), extract statistically valid kinematic metrics (e.g., stroke rate, body roll), and rebuild the application's core performance benchmarks.

## 2. Core Constraints
- **Atomic Transactions:** Updates run in an isolated staging environment. If any safety check fails, or if the update crashes, the database is perfectly rolled back to its previous verified state.
- **Strict Provenance:** No benchmarks can be updated or generated without mathematically rigorous empirical data extracted directly from a verifiable scientific source.
- **Zero Fabrication:** The system will never hallucinate, infer, or "default" to synthetic benchmarks to cover gaps in data. If there is no data, the coverage matrix displays "INSUFFICIENT EVIDENCE".

## 3. Data Flow
1. **Literature Discovery (`_search_literature`)**: Queries PubMed via E-Utilities for target strokes and demographics.
2. **Structural Extraction (`_try_retrieve_and_parse_pmc_fulltext`)**: Fetches XML full text from PMC. Uses `xml.etree.ElementTree` to deterministically traverse Abstract, Body Paragraphs, and Tables to locate metrics.
3. **Semantic Extraction (`ScientificSemanticExtractor`)**: Passes targeted text blocks to Gemini via the `google-genai` SDK using a strict JSON schema.
4. **Deterministic Validation (`_process_candidates_with_llm`)**: Candidates are mathematically verified against the literal source text. If a mean/SD was hallucinated or altered by the LLM, the candidate is instantly rejected.
5. **Benchmark Compilation (`_rebuild_benchmarks_from_evidence`)**: Accepted evidence is mathematically aggregated into isolated demographic cohorts (e.g., U10 Female Freestyle).
6. **Commit & Rollback**: Updates are moved from staging to production only if 100% of data passes relationship mapping and provenance checks.

## 4. Sub-Systems
- `ScientificUpdaterService`: The primary coordinator for transactions, API calls, and validation.
- `ScientificSemanticExtractor`: The LLM interface utilizing `gemini-2.5-flash` with structured JSON output enforcing demographic boundaries and exact quote references.
- `BenchmarkEngine`: Consumes the resulting YAML benchmarks to power UI stroke classification and athlete technique comparisons.
