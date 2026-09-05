# Scientific Database Update Manual

## 1. What does the "Update Scientific Database" button do?
When a user clicks the "Update Scientific Database" button in the sidebar, the Swim Analyzer AI initiates an atomic transaction to pull the latest peer-reviewed literature from NCBI (PubMed/PMC).

## 2. The Atomic Transaction Cycle
1. **Snapshotting**: The system creates a full backup of the `scientific_reference` folder and `config/benchmarks`.
2. **Staging**: An isolated environment is built.
3. **Fetching**: E-Utilities pulls new abstracts and XML full-texts.
4. **LLM Extraction**: `ScientificSemanticExtractor` is invoked to map XML body text to evidence JSON.
5. **Deterministic Validation**: Strict validation ensures the LLM did not hallucinate any values.
6. **Benchmark Compilation**: Validated evidence is grouped by stroke/age/sex to build the final benchmarking datasets.
7. **Testing**: The system runs `_run_scientific_safety_tests()`.
8. **Commit**: If all tests pass, the staging data overwrites the production folders. If any failure occurs, or if no new data was found, the system rolls back instantly and reports the state to the user.

## 3. Idempotency
Running the updater 50 times without new literature appearing on PubMed will result in exactly 0 changes to the database. The system calculates cryptographic hashes of extracted values and prevents duplicate evidence instantiation.
