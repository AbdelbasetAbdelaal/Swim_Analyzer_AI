import pytest
import yaml
from pathlib import Path

from models.scientific_evidence_models import (
    CandidateEvidence, ReviewStatus, AuditDecision, ValidationStatus
)
from scientific_reference.validation.benchmark_eligibility_validator import BenchmarkEligibilityValidator
from scientific_reference.validation.evidence_validator import EvidenceValidator
from scientific_reference.storage.scientific_evidence_registry import ScientificEvidenceRegistry
from analysis.benchmarks.benchmark_engine import BenchmarkEngine


@pytest.fixture
def eligibility_validator():
    return BenchmarkEligibilityValidator()


@pytest.fixture
def benchmark_engine():
    return BenchmarkEngine()


# TEST 1: Systematic review alone cannot create a benchmark.
def test_1_systematic_review_alone_cannot_create_benchmark(eligibility_validator):
    candidate = CandidateEvidence(
        source_id="SR_BACKSTROKE_2025",
        pmid="40483624",
        pmcid=None,
        doi="10.1186/s40798-025-00868-z",
        title="Backstroke 2025 systematic review",
        stroke="Backstroke",
        population_sex="Male",
        population_age="18-25",
        competitive_level="Elite",
        metric="stroke_rate",
        mean=42.5,
        sd=3.1,
        unit="spm",
        sample_size=507,
        table_or_figure="Table 2",
        source_quote="Mean stroke rate across backstroke studies was 42.5 spm.",
        xml_block_type="table",
        study_type="systematic_review",
        primary_study_identifier=None # Missing primary study trace!
    )
    status, decision, rationale = eligibility_validator.evaluate_eligibility(candidate)
    assert status != ReviewStatus.SCIENTIFICALLY_ACCEPTED
    assert status in [ReviewStatus.PENDING_REVIEW, ReviewStatus.REJECTED]
    assert decision == AuditDecision.REFERENCE_ONLY or decision == AuditDecision.REJECT
    assert "primary study trace" in rationale.lower()


# TEST 2: Systematic review + verified primary study can create a benchmark candidate.
def test_2_systematic_review_with_primary_study_trace_valid(eligibility_validator):
    candidate = CandidateEvidence(
        source_id="SR_BACKSTROKE_2025",
        pmid="40483624",
        pmcid=None,
        doi="10.1186/s40798-025-00868-z",
        title="Backstroke 2025 systematic review",
        stroke="Backstroke",
        population_sex="Male",
        population_age="18-25",
        competitive_level="Elite",
        metric="stroke_rate",
        mean=42.5,
        sd=3.1,
        unit="spm",
        sample_size=35,
        table_or_figure="Table 2",
        source_quote="Gonjo et al. (2020) reported mean stroke rate of 42.5 spm.",
        xml_block_type="table",
        study_type="systematic_review",
        primary_study_identifier="SRC-BACK-GONJO-2020" # Primary study trace present!
    )
    status, decision, rationale = eligibility_validator.evaluate_eligibility(candidate)
    assert status == ReviewStatus.SCIENTIFICALLY_ACCEPTED
    assert decision == AuditDecision.ACCEPT


# TEST 3: Male evidence cannot populate female benchmark.
def test_3_male_evidence_cannot_populate_female_benchmark(eligibility_validator):
    candidate = CandidateEvidence(
        source_id="SRC-FREE-001",
        pmid="522640",
        pmcid=None,
        doi=None,
        title="Relationships of stroke rate",
        stroke="Freestyle",
        population_sex="Male",
        population_age="18-25",
        competitive_level="National",
        metric="stroke_rate",
        mean=54.0,
        sd=4.0,
        unit="spm",
        sample_size=184,
        table_or_figure="Table 1",
        source_quote="Male swimmers exhibited stroke rate of 54.0 spm.",
        xml_block_type="results"
    )
    status, decision, rationale = eligibility_validator.evaluate_eligibility(candidate, target_sex="Female")
    assert status == ReviewStatus.REJECTED
    assert decision == AuditDecision.REJECT
    assert "demographic leakage" in rationale.lower() or "sex" in rationale.lower()


# TEST 4: Adult evidence cannot populate adolescent benchmark.
def test_4_adult_evidence_cannot_populate_adolescent_benchmark(eligibility_validator):
    candidate = CandidateEvidence(
        source_id="SRC-FREE-001",
        pmid="522640",
        pmcid=None,
        doi=None,
        title="Relationships of stroke rate",
        stroke="Freestyle",
        population_sex="Male",
        population_age="18-25",
        competitive_level="National",
        metric="stroke_rate",
        mean=54.0,
        sd=4.0,
        unit="spm",
        sample_size=184,
        table_or_figure="Table 1",
        source_quote="Adult male swimmers 18-25 years old.",
        xml_block_type="results"
    )
    status, decision, rationale = eligibility_validator.evaluate_eligibility(candidate, target_age_group="8-10")
    assert status == ReviewStatus.REJECTED
    assert decision == AuditDecision.REJECT
    assert "adult evidence cannot populate adolescent" in rationale.lower() or "demographic" in rationale.lower()


# TEST 5: Freestyle evidence cannot populate backstroke benchmark.
def test_5_freestyle_evidence_cannot_populate_backstroke_benchmark(eligibility_validator):
    candidate = CandidateEvidence(
        source_id="SRC-FREE-001",
        pmid="522640",
        pmcid=None,
        doi=None,
        title="Relationships of stroke rate",
        stroke="Freestyle",
        population_sex="Male",
        population_age="18-25",
        competitive_level="National",
        metric="stroke_rate",
        mean=54.0,
        sd=4.0,
        unit="spm",
        sample_size=184,
        table_or_figure="Table 1",
        source_quote="Freestyle stroke rate was 54.0 spm.",
        xml_block_type="results"
    )
    status, decision, rationale = eligibility_validator.evaluate_eligibility(candidate, target_stroke="Backstroke")
    assert status == ReviewStatus.REJECTED
    assert decision == AuditDecision.REJECT
    assert "stroke leakage" in rationale.lower()


# TEST 6: 400m freestyle evidence cannot populate generic freestyle benchmark.
def test_6_400m_freestyle_evidence_cannot_populate_generic_freestyle(eligibility_validator):
    candidate = CandidateEvidence(
        source_id="MA_400M_FRONT_CRAWL",
        pmid="36778096",
        pmcid="PMC9909090",
        doi="10.3389/fspor.2023.977739",
        title="400m Front Crawl meta-analysis",
        stroke="Freestyle",
        population_sex="Male",
        population_age="18-25",
        competitive_level="Elite",
        metric="stroke_rate",
        mean=38.2,
        sd=2.4,
        unit="spm",
        sample_size=320,
        table_or_figure="Figure 3",
        source_quote="During the 400m front crawl test, mean stroke rate was 38.2 spm.",
        xml_block_type="results",
        study_type="meta_analysis",
        test_distance_m=400
    )
    status, decision, rationale = eligibility_validator.evaluate_eligibility(candidate, target_distance_m=100)
    assert status == ReviewStatus.REJECTED
    assert decision == AuditDecision.REJECT
    assert "400m" in rationale


# TEST 7: Missing population -> REVIEW_REQUIRED or INSUFFICIENT_EVIDENCE.
def test_7_missing_population_returns_insufficient_evidence(benchmark_engine):
    stats = benchmark_engine._get_population_stats("breaststroke", "8-10", "Female", "stroke_rate")
    assert stats.mean is None, "Missing demographic cohort 8-10 Female Breaststroke must return None mean"
    assert stats.evidence.validation_status in [ValidationStatus.INSUFFICIENT_EVIDENCE, ValidationStatus.CONFLICTING_EVIDENCE]


# TEST 8: Missing provenance -> rejection.
def test_8_missing_provenance_quote_rejected():
    candidate = CandidateEvidence(
        source_id="SRC-FREE-001",
        pmid="522640",
        pmcid=None,
        doi=None,
        title="Relationships of stroke rate",
        stroke="Freestyle",
        population_sex="Male",
        population_age="18-25",
        competitive_level="National",
        metric="stroke_rate",
        mean=54.0,
        sd=4.0,
        unit="spm",
        sample_size=184,
        table_or_figure="Table 1",
        source_quote="This quote does not exist anywhere in the paper text.",
        xml_block_type="results"
    )
    full_text = "The actual paper text contains different sentences about swimming velocity and stroke length."
    rec = EvidenceValidator.validate_candidate(candidate, full_text)
    assert rec.scientific_status == ReviewStatus.REJECTED
    assert rec.audit_decision == AuditDecision.REJECT
    assert "provenance" in rec.notes.lower() or "quote" in rec.notes.lower()


# TEST 9: Gemini-generated unsupported value cannot bypass validators.
def test_9_gemini_unsupported_value_cannot_bypass_validators():
    candidate = CandidateEvidence(
        source_id="SRC-FREE-001",
        pmid="522640",
        pmcid=None,
        doi=None,
        title="Relationships of stroke rate",
        stroke="Freestyle",
        population_sex="Male",
        population_age="18-25",
        competitive_level="National",
        metric="stroke_rate",
        mean=54.0,
        sd=-1.5, # Invalid negative SD!
        unit="spm",
        sample_size=3, # N < 8!
        table_or_figure="Table 1",
        source_quote="Sample size was 3.",
        xml_block_type="results",
        confidence="0.99" # High LLM confidence cannot bypass validation
    )
    full_text = "Sample size was 3."
    rec = EvidenceValidator.validate_candidate(candidate, full_text)
    assert rec.scientific_status == ReviewStatus.REJECTED
    assert rec.audit_decision == AuditDecision.REJECT


# TEST 10: No interpolation.
def test_10_no_interpolation(benchmark_engine):
    stats = benchmark_engine._get_population_stats("butterfly", "11-13", "Male", "stroke_rate")
    assert stats.mean is None, "No interpolation allowed for unrepresented youth age group"


# TEST 11: No extrapolation.
def test_11_no_extrapolation(benchmark_engine):
    stats = benchmark_engine._get_population_stats("freestyle", "Masters", "Male", "stroke_rate")
    assert stats.mean is None, "No extrapolation of adult 18-25 values to Masters 35+ allowed"


# TEST 12: No fabricated DOI/PMID/PMCID.
def test_12_no_fabricated_doi_pmid(eligibility_validator):
    candidate = CandidateEvidence(
        source_id="SRC-FAKE-001",
        pmid="FABRICATED",
        pmcid=None,
        doi="10.0000/fake",
        title="Fake Swimming Study",
        stroke="Freestyle",
        population_sex="Male",
        population_age="18-25",
        competitive_level="National",
        metric="stroke_rate",
        mean=50.0,
        sd=3.0,
        unit="spm",
        sample_size=30,
        table_or_figure="Table 1",
        source_quote="Fake quote text.",
        xml_block_type="results"
    )
    status, decision, rationale = eligibility_validator.evaluate_eligibility(candidate)
    assert status == ReviewStatus.REJECTED
    assert decision == AuditDecision.REJECT
    assert "fabricated" in rationale.lower()


# TEST 13: Accepted records contain complete provenance.
def test_13_accepted_records_contain_complete_provenance():
    registry = ScientificEvidenceRegistry()
    for rec in registry.get_all_records():
        if rec.scientific_status == ReviewStatus.SCIENTIFICALLY_ACCEPTED:
            assert rec.source_id is not None and len(rec.source_id) > 0
            assert rec.title is not None and len(rec.title) > 0
            assert rec.stroke in ["Freestyle", "Backstroke", "Breaststroke", "Butterfly"]
            assert rec.measurement_name is not None and len(rec.measurement_name) > 0
            assert rec.sample_size > 0
            assert rec.reported_mean is not None


# TEST 14: Benchmark YAML contains only scientifically accepted evidence.
def test_14_benchmark_yaml_contains_only_scientifically_accepted():
    benchmark_dir = Path(__file__).resolve().parent.parent / "config" / "benchmarks"
    yaml_files = list(benchmark_dir.glob("*.yaml"))
    assert len(yaml_files) >= 4, "Must find at least 4 stroke benchmark YAML files"

    for yfile in yaml_files:
        with open(yfile, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        pops = data.get("populations", {})
        default_pop = pops.get("default", {})
        for m_name, m_cfg in default_pop.items():
            if isinstance(m_cfg, dict) and "evidence" in m_cfg:
                ev = m_cfg["evidence"]
                val_status = ev.get("validation_status")
                if val_status == "VALIDATED":
                    assert ev.get("scientific_status") == "SCIENTIFICALLY_ACCEPTED"
                    assert len(ev.get("source_ids", [])) > 0
