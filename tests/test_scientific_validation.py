import yaml
from pathlib import Path

from scientific_reference.scientific_source_repository import ScientificSourceRepository
from services.scientific_evidence_service import ScientificEvidenceService
from analysis.benchmarks.benchmark_engine import BenchmarkEngine
from models.scientific_evidence_models import ValidationStatus, EvidenceLevel
from models.data_models import AnalysisResult, PerformanceReport, ValidatedMetric
from models.athlete_profile import AthleteProfile

def test_source_registry_loading():
    """Verify ScientificSourceRepository loads registered Level A/B publications."""
    repo = ScientificSourceRepository()
    sources = repo.get_all_sources()
    assert len(sources) >= 5, f"Expected at least 5 scientific literature sources, got {len(sources)}"
    
    src1 = repo.get_source("SRC-FREE-001")
    assert src1 is not None, "SRC-FREE-001 missing from registry"
    assert src1.publication_year == 1979
    assert src1.evidence_quality == EvidenceLevel.LEVEL_A
    assert src1.sample_size == 184

def test_citation_formatting():
    """Verify ScientificEvidenceService formats APA citations correctly."""
    service = ScientificEvidenceService()
    src = service.repo.get_source("SRC-FREE-001")
    citation = service.format_citation(src)
    assert "Craig, AB, Pendergast, DR" in citation
    assert "1979" in citation
    assert "medicine and science in sports" in citation.lower()

def test_benchmark_datasets_have_evidence_metadata():
    """
    CRITICAL RULE TEST:
    Fails if any production benchmark dataset metric has numerical mean/std
    WITHOUT explicit evidence metadata.
    """
    benchmark_dir = Path(__file__).resolve().parent.parent / "config" / "benchmarks"
    yaml_files = list(benchmark_dir.glob("*.yaml"))
    assert len(yaml_files) >= 4, "Expected at least 4 benchmark YAML files"

    repo = ScientificSourceRepository()

    for yfile in yaml_files:
        with open(yfile, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "dataset_id" in data, f"dataset_id missing in {yfile.name}"
        assert "version" in data, f"version missing in {yfile.name}"
        assert "scientific_revision" in data, f"scientific_revision missing in {yfile.name}"

        pops = data.get("populations", {})
        default_pop = pops.get("default", {})
        
        for gender, gcfg in default_pop.items():
            if gender == "status": continue
            for metric_name, mcfg in gcfg.items():
                if metric_name == "status": continue
                assert "mean" in mcfg and "std" in mcfg, f"Metric {metric_name} missing mean/std in {yfile.name}"
                assert "evidence" in mcfg, f"CRITICAL AUDIT FAILURE: Metric {metric_name} in {yfile.name} has numerical mean/std but NO evidence metadata block!"
                
                ev = mcfg["evidence"]
                assert "validation_status" in ev, f"Metric {metric_name} in {yfile.name} missing validation_status"
                assert "evidence_level" in ev, f"Metric {metric_name} in {yfile.name} missing evidence_level"
                
                # Verify cited source_ids exist in registry if status is VALIDATED or PARTIALLY_VALIDATED
                sids = ev.get("source_ids", [])
                if ev["validation_status"] in ["VALIDATED", "PARTIALLY_VALIDATED"] and sids:
                    for sid in sids:
                        assert repo.get_source(sid) is not None, f"Metric {metric_name} in {yfile.name} cites non-existent source_id {sid}"

def test_benchmark_engine_unmatched_age_cohort_is_insufficient_evidence():
    """Adult profiles must not consume the YAML dataset's age-unspecified Mixed cohort."""
    engine = BenchmarkEngine()
    ar = AnalysisResult()
    ar.report = PerformanceReport(
        overall_score=82.0,
        stroke_rate=ValidatedMetric(value=54.0, valid=True),
        stroke_length=ValidatedMetric(value=1.90, valid=True)
    )
    prof = AthleteProfile(coach_id="test_coach", full_name="John Doe", age=22, gender="Male", height_cm=180.0, weight_kg=75.0, swimming_level="Advanced", preferred_stroke="Freestyle")
    
    res = engine.evaluate_analysis(ar, prof)
    assert res.dataset_id != "", "dataset_id missing from BenchmarkResult"
    assert "stroke_rate" in res.comparisons
    
    sr_comp = res.comparisons["stroke_rate"]
    assert sr_comp.evidence is not None
    assert sr_comp.evidence.validation_status == ValidationStatus.INSUFFICIENT_EVIDENCE
    assert sr_comp.population_mean is None
    assert sr_comp.percentile is None

def test_derived_placeholder_performance_score_is_not_invented_without_statistics():
    """A composite score without an explicit benchmark remains insufficient evidence."""
    engine = BenchmarkEngine()
    ar = AnalysisResult()
    ar.report = PerformanceReport(overall_score=85.0)
    res = engine.evaluate_analysis(ar)
    
    score_comp = res.comparisons.get("performance_score")
    assert score_comp is not None
    assert score_comp.evidence.validation_status == ValidationStatus.INSUFFICIENT_EVIDENCE
    assert score_comp.evidence.evidence_level == EvidenceLevel.LEVEL_E
