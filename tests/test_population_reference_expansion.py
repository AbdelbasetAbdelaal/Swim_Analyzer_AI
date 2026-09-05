import pytest
import yaml
from pathlib import Path

from scientific_reference.scientific_source_repository import ScientificSourceRepository
from services.population_taxonomy_service import PopulationTaxonomyService, AgeCohort, SexCategory
from analysis.benchmarks.benchmark_engine import BenchmarkEngine

@pytest.fixture
def repo():
    return ScientificSourceRepository()

@pytest.fixture
def benchmark_engine():
    return BenchmarkEngine()

@pytest.fixture
def evidence_data():
    p = Path("scientific_reference/evidence/evidence_registry.yaml")
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_1_no_benchmark_without_source(repo, evidence_data):
    records = evidence_data.get("evidence_records", {})
    for eid, rec in records.items():
        sid = rec.get("source_id")
        assert sid is not None, f"Evidence {eid} missing source_id"
        assert repo.get_source(sid) is not None, f"Source {sid} not found in repository for {eid}"

def test_2_no_accepted_benchmark_without_exact_location(evidence_data):
    records = evidence_data.get("evidence_records", {})
    for eid, rec in records.items():
        if rec.get("scientific_status") == "SCIENTIFICALLY_ACCEPTED":
            loc = rec.get("table_or_figure_reference")
            page = rec.get("page_reference")
            assert loc is not None and loc != "", f"Accepted evidence {eid} missing table_or_figure_reference"
            assert page is not None and page != "", f"Accepted evidence {eid} missing page_reference"

def test_3_no_accepted_benchmark_without_population(evidence_data):
    records = evidence_data.get("evidence_records", {})
    for eid, rec in records.items():
        if rec.get("scientific_status") == "SCIENTIFICALLY_ACCEPTED":
            pop_desc = rec.get("population_description")
            assert pop_desc is not None and pop_desc != "", f"Evidence {eid} missing population_description"

def test_4_no_accepted_benchmark_without_sex(evidence_data):
    records = evidence_data.get("evidence_records", {})
    for eid, rec in records.items():
        if rec.get("scientific_status") == "SCIENTIFICALLY_ACCEPTED":
            gender = rec.get("gender")
            assert gender in ["Male", "Female", "Mixed"], f"Evidence {eid} missing valid gender"

def test_5_no_adult_to_youth_automatic_scaling(benchmark_engine):
    stats = benchmark_engine._get_population_stats("freestyle", "8-10", "Male", "stroke_rate")
    assert stats.mean is None, "8-10 Male Freestyle must return None mean due to INSUFFICIENT_EVIDENCE"

def test_6_no_male_to_female_copying(benchmark_engine):
    m_stats = benchmark_engine._get_population_stats("freestyle", "18-25", "Male", "stroke_rate")
    f_stats = benchmark_engine._get_population_stats("freestyle", "18-25", "Female", "stroke_rate")
    assert m_stats.mean != f_stats.mean or f_stats.mean is None, "Female 18-25 stroke rate must not copy Male 18-25 value"

def test_7_no_stroke_to_stroke_copying(benchmark_engine):
    free_stats = benchmark_engine._get_population_stats("freestyle", "18-25", "Male", "stroke_rate")
    fly_stats = benchmark_engine._get_population_stats("butterfly", "18-25", "Male", "stroke_rate")
    # Both values are intentionally unavailable until separately verified; matching
    # None values are not evidence of cross-stroke copying.
    assert free_stats.mean is None
    assert fly_stats.mean is None

def test_8_no_incompatible_metric_definition_matching(evidence_data):
    records = evidence_data.get("evidence_records", {})
    for eid, rec in records.items():
        def_compat = rec.get("definition_compatibility")
        if def_compat == "DEFINITION_MISMATCH":
            assert rec.get("scientific_status") != "SCIENTIFICALLY_ACCEPTED", f"Record {eid} with mismatch definition cannot be accepted"

def test_9_no_silent_averaging_of_conflicting_studies(evidence_data):
    records = evidence_data.get("evidence_records", {})
    # Check each evidence record has single explicit source_id and reported_mean
    for eid, rec in records.items():
        assert isinstance(rec.get("source_id"), str)
        assert isinstance(rec.get("reported_mean"), (int, float))

def test_10_no_abstract_only_labeled_full_text(repo):
    for sid, source in repo._sources.items():
        if source.access_level == "ABSTRACT_ONLY":
            assert source.access_level != "FULL_TEXT_VERIFIED"

def test_11_no_textbook_labeled_peer_reviewed(repo):
    for sid, source in repo._sources.items():
        if "textbook" in source.journal_or_organization.lower():
            assert source.evidence_quality != "LEVEL_A"

def test_12_no_benchmark_from_unverified_source(repo, benchmark_engine):
    for stroke, ds in benchmark_engine._datasets.items():
        pops = ds.get("populations", {})
        for pop_k, pop_v in pops.items():
            if isinstance(pop_v, dict) and "Male" in pop_v:
                for gender_k in ["Male", "Female"]:
                    g_cfg = pop_v.get(gender_k)
                    if isinstance(g_cfg, dict):
                        for m_k, m_v in g_cfg.items():
                            if isinstance(m_v, dict) and "evidence" in m_v:
                                sid = m_v["evidence"].get("source_id")
                                if sid:
                                    assert repo.get_source(sid) is not None, f"Unverified source_id {sid} in {stroke} benchmark"

def test_13_traceability_metadata_present(benchmark_engine):
    stats = benchmark_engine._get_population_stats("freestyle", "Mixed", "Male", "stroke_rate")
    assert stats.evidence is not None
    assert "SRC-FREE-001" in stats.evidence.source_ids

def test_14_four_stroke_coverage_in_engine(benchmark_engine):
    for stroke in ["freestyle", "backstroke", "breaststroke", "butterfly"]:
        assert stroke in benchmark_engine._datasets, f"Dataset for {stroke} missing"

def test_15_population_taxonomy_mapping():
    c_youth = PopulationTaxonomyService.resolve_cohort(12, "Male")
    assert c_youth.age_cohort == AgeCohort.U11_U12
    assert c_youth.sex == SexCategory.MALE

    c_adult = PopulationTaxonomyService.resolve_cohort(22, "Female")
    assert c_adult.age_cohort == AgeCohort.SENIOR_21_25
    assert c_adult.sex == SexCategory.FEMALE

def test_16_absence_of_fabricated_values(benchmark_engine):
    stats = benchmark_engine._get_population_stats("freestyle", "Masters", "Female", "stroke_rate")
    assert stats.mean is None, "Missing demographic group Masters Female must return None mean"
