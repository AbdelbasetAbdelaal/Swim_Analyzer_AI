# Scientific Provenance Policy

## 1. The Core Rule: Zero Fabrication
Under no circumstances may the Swim Analyzer AI synthesize, guess, interpolate, or fabricate kinematic benchmarks. Every number driving athlete classification must be mathematically derived from peer-reviewed scientific literature.

## 2. Demographic Isolation
- **Age Cohorts**: Literature citing "youth" or "adult" without specific ranges will NOT be mapped to specific U10, 11-12, etc. cohorts. Exact ages must be verified, otherwise they fall into "Mixed" which does NOT contaminate specific competitive cohorts.
- **Gender Splits**: If a study aggregates male and female swimmers without separate statistics, the benchmark remains "Mixed" and cannot be applied specifically to "Male" or "Female" categories.
- **Stroke Specificity**: A stroke rate for Freestyle will absolutely never be applied to Butterfly. 

## 3. Provenance Chain
1. **Source Level (Level A/B)**: The original PubMed/PMC paper containing the data. 
2. **Evidence Level (EVID-XXX)**: A single measurement (e.g. Stroke Rate: 45 strokes/min) pulled from the source. The system tracks the exact source quote, table, or paragraph where the LLM found this data.
3. **Benchmark Level**: The final YAML configuration used by the `BenchmarkEngine`. Benchmarks compile multiple evidence records together into a validated mean and standard deviation.

## 4. Fallback Handling
If a population demographic lacks sufficient evidence, the system correctly reports **INSUFFICIENT EVIDENCE**. It will not fallback to adult statistics for children, or use dummy values like `70.0 LEVEL_E`. The system degrades gracefully to `UNKNOWN` classification rather than lie.
