import yaml
from pathlib import Path

from scientific_reference.storage.scientific_evidence_registry import ScientificEvidenceRegistry
from scientific_reference.validation.population_validator import PopulationValidator
from scientific_reference.validation.metric_validator import MetricValidator
from scientific_reference.validation.statistical_validator import StatisticalValidator
from models.scientific_evidence_models import (
    DefinitionMatchingStatus, PopulationMatchingStatus
)

def test_evidence_registry_records():
    """Verify evidence registry stores valid structured scientific records (EVID-xxx)."""
    registry = ScientificEvidenceRegistry()
    records = registry.get_all_records()
    assert len(records) >= 5, f"Expected at least 5 evidence records, got {len(records)}"

    for r in records:
        assert r.evidence_id.startswith("EVID-"), f"Invalid evidence_id {r.evidence_id}"
        assert r.source_id != "", f"Missing source_id for {r.evidence_id}"
        assert r.title != "", f"Missing publication title for {r.evidence_id}"
        assert r.authors, f"Missing authors for {r.evidence_id}"
        assert r.table_or_figure_reference != "", f"Missing table/figure location for {r.evidence_id}"
        assert r.page_reference != "", f"Missing page reference for {r.evidence_id}"

def test_unit_conversion_layer():
    """Verify unit conversion layer produces traceable conversion formulas."""
    val, unit, formula = StatisticalValidator.convert_unit(0.90, "Hz", "spm")
    assert val == 54.0
    assert unit == "spm"
    assert "0.9" in formula and "60" in formula and "54" in formula

def test_definition_matching():
    """Verify definition matching flags definition mismatches."""
    status1 = MetricValidator.evaluate_definition_match("Stroke rate in Hz", "stroke_rate")
    assert status1 == DefinitionMatchingStatus.EXACT_MATCH

    status2 = MetricValidator.evaluate_definition_match("Shoulder roll angle", "torso normal vector roll")
    assert status2 == DefinitionMatchingStatus.DEFINITION_MISMATCH

def test_population_matching_adult_to_youth_guard():
    """CRITICAL RULE: Adult data extrapolated to youth MUST return POPULATION_MISMATCH."""
    status = PopulationValidator.evaluate_population_match(
        study_pop="Elite adult males",
        target_pop="U10 Junior Swimmers",
        study_age_range=(18, 25),
        target_age_range=(8, 10)
    )
    assert status == PopulationMatchingStatus.POPULATION_MISMATCH

def test_yaml_benchmark_provenance_integrity():
    """
    CRITICAL PIPELINE RULE TESTS 1-11:
    Verify production benchmark YAML datasets contain full provenance blocks
    and violate zero scientific rules.
    """
    benchmark_dir = Path(__file__).resolve().parent.parent / "config" / "benchmarks"
    yaml_files = list(benchmark_dir.glob("*.yaml"))
    assert len(yaml_files) >= 4

    for yfile in yaml_files:
        with open(yfile, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        pops = data.get("populations", {})
        def_pop = pops.get("default", {})

        for m_name, mcfg in def_pop.items():
            ev = mcfg.get("evidence", {})
            val_stat = ev.get("validation_status")

            if val_stat == "VALIDATED":
                # Rule 1 & 3: Validated benchmark must have source & evidence record
                assert ev.get("evidence_id") is not None, f"Metric {m_name} in {yfile.name} missing evidence_id"
                assert "source_ids" in ev, f"Metric {m_name} in {yfile.name} missing source_ids"
                
                # Rule 4: Validated benchmark cannot have UNKNOWN_DEFINITION
                assert ev.get("definition_status") != "UNKNOWN_DEFINITION", f"Metric {m_name} has unknown definition"
                
                # Rule 5: Validated benchmark cannot have POPULATION_MISMATCH
                assert ev.get("population_status") != "POPULATION_MISMATCH", f"Metric {m_name} has population mismatch"
                
                # Rule 11: Validated benchmark cannot have UNVERIFIED evidence status
                assert ev.get("scientific_status") == "SCIENTIFICALLY_ACCEPTED", f"Metric {m_name} is not accepted"

        # Rule 10: Youth cohorts must have status INSUFFICIENT_EVIDENCE rather than scaled adult data
        u10 = pops.get("8-10", {})
        status = u10.get("status", "INSUFFICIENT_EVIDENCE")
        assert status == "INSUFFICIENT_EVIDENCE", f"Youth cohort in {yfile.name} must be INSUFFICIENT_EVIDENCE"
