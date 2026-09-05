# SwimAnalyzer AI — Scientific Reference & Literature Pipeline Architecture

The `scientific_reference/` package forms the scientific evidence extraction, literature discovery, and provenance compilation layer for SwimAnalyzer AI.

It is completely decoupled from the athlete analysis runtime and Streamlit UI execution, providing auditable scientific evidence for population benchmarks.

---

## 🏗️ Architecture & Component Overview

```
scientific_reference/
├── discovery/
│   └── scientific_source_discovery.py   # NCBI E-utilities & Europe PMC legal API discovery
├── retrieval/
│   └── scientific_document_retriever.py # Open-access XML & PubMed summary retriever
├── extraction/
│   └── scientific_evidence_extractor.py # Parses structured scientific observations
├── validation/
│   └── scientific_evidence_validator.py # Unit conversion layer & definition/population matching
├── storage/
│   └── scientific_evidence_registry.py  # Repository for evidence_registry.yaml
├── evidence/
│   └── evidence_registry.yaml           # YAML database of 37-field evidence records
└── scientific_benchmark_builder.py      # Compiles provenance-enriched config/benchmarks/*.yaml
```

---

## 🔬 Core Components

### 1. Legal Scientific Source Discovery (`discovery/`)
- `ScientificSourceDiscovery`: Queries NCBI E-utilities (`esearch.fcgi`) and Europe PMC REST APIs for open-access literature matching queries (e.g. *"swimming stroke rate kinematic"*).
- Does NOT scrape paywalled publisher sites or violate copyright terms.

### 2. Document Retriever (`retrieval/`)
- `ScientificDocumentRetriever`: Fetches metadata and PMC XML text legally.
- Classifies access levels:
  - `FULL_TEXT_VERIFIED`: Full text accessed legally via PMC XML or Open Access PDF.
  - `ABSTRACT_VERIFIED`: Abstract metadata retrieved via PubMed API.
  - `METADATA_ONLY`: Citation metadata only.
  - `UNVERIFIED`: Unverified source.

### 3. Scientific Evidence Validator (`validation/`)
- `ScientificEvidenceValidator`:
  - **Unit Conversion Layer**: Converts units (e.g. $0.90 \text{ Hz} \times 60 = 54.0 \text{ spm}$) while preserving original values, original units, and explicit conversion formulas.
  - **Definition Matching Guard**: Compares literature definitions against SwimAnalyzer definitions (`EXACT_MATCH`, `COMPATIBLE_DEFINITION`, `DEFINITION_MISMATCH`, `UNKNOWN_DEFINITION`).
  - **Population Compatibility Guard**: Compares study demographic cohorts against target benchmark populations (`EXACT_MATCH`, `COMPATIBLE`, `PARTIAL_MATCH`, `POPULATION_MISMATCH`).

### 4. Evidence Storage Repository (`storage/` & `evidence/`)
- `ScientificEvidenceRegistry`: Persistent repository reading `evidence/evidence_registry.yaml`.
- Manages 37-field evidence records (`EVID-xxx`) storing exact table/figure references, page numbers, sample sizes, DOI, conversion formulas, and audit decision tags (`ACCEPT`, `ACCEPT_AS_DERIVED`, `REFERENCE_ONLY`, `REJECT`).

### 5. Benchmark Dataset Compiler (`scientific_benchmark_builder.py`)
- `ScientificBenchmarkBuilder`: Compiles versioned YAML files (`config/benchmarks/freestyle.yaml`, `backstroke.yaml`, `breaststroke.yaml`, `butterfly.yaml`).
- Enforces that ONLY records with `scientific_status == SCIENTIFICALLY_ACCEPTED` and `audit_decision in [ACCEPT, ACCEPT_AS_DERIVED]` are compiled into production benchmark means. Non-adult cohorts are assigned `status: INSUFFICIENT_EVIDENCE`.

---

## 🧪 Verification & Usage
Run the scientific extraction pipeline tests:
```bash
pytest tests/test_scientific_extraction_pipeline.py -v
pytest tests/test_final_scientific_audit.py -v
```
