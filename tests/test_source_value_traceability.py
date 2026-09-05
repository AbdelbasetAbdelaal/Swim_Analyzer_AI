import yaml
from pathlib import Path

from analysis.benchmarks.benchmark_engine import BenchmarkEngine
from models.scientific_evidence_models import (
    SourceRelationship,
    PopulationCompatibility
)

def test_benchmark_source_relationship_tags():
    """Verify all benchmark datasets contain explicit source relationship and compatibility metadata."""
    benchmark_dir = Path(__file__).resolve().parent.parent / "config" / "benchmarks"
    yaml_files = list(benchmark_dir.glob("*.yaml"))
    assert len(yaml_files) >= 4

    for yfile in yaml_files:
        with open(yfile, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        pops = data.get("populations", {})
        default_pop = pops.get("default", {})

        for gender, gcfg in default_pop.items():
            if gender == "status": continue
            for m_name, mcfg in gcfg.items():
                if m_name == "status": continue
                ev = mcfg.get("evidence", {})
                assert "source_relationship" in ev or "relationship" in ev, f"Metric {m_name} in {yfile.name} missing source_relationship"
                assert "population_status" in ev or "population_compatibility" in ev, f"Metric {m_name} in {yfile.name} missing population status"
                assert "definition_status" in ev or "definition_compatibility" in ev, f"Metric {m_name} in {yfile.name} missing definition status"

def test_validated_metrics_must_be_directly_or_derived_supported():
    """
    CRITICAL SCIENTIFIC RULE:
    Any metric tagged as VALIDATED must have source_relationship DIRECTLY_SUPPORTED or DERIVED_FROM_SOURCE.
    It CANNOT be APPROXIMATED or UNVERIFIED, nor have POPULATION_MISMATCH.
    """
    benchmark_dir = Path(__file__).resolve().parent.parent / "config" / "benchmarks"
    yaml_files = list(benchmark_dir.glob("*.yaml"))

    for yfile in yaml_files:
        with open(yfile, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        pops = data.get("populations", {})
        default_pop = pops.get("default", {})

        for gender, gcfg in default_pop.items():
            if gender == "status": continue
            for m_name, mcfg in gcfg.items():
                if m_name == "status": continue
                ev = mcfg.get("evidence", {})
                val_stat = ev.get("validation_status")
                src_rel = ev.get("source_relationship") or ev.get("relationship")
                pop_comp = ev.get("population_status") or ev.get("population_compatibility")

                if val_stat == "VALIDATED":
                    assert src_rel in ["DIRECTLY_SUPPORTED", "DERIVED_FROM_SOURCE"], \
                        f"CRITICAL RULE FAILURE: Metric {m_name} in {yfile.name} is VALIDATED but relationship is {src_rel}!"
                    assert pop_comp in ["COMPATIBLE", "EXACT_MATCH"], \
                        f"CRITICAL RULE FAILURE: Metric {m_name} in {yfile.name} is VALIDATED but has POPULATION_MISMATCH!"

def test_benchmark_engine_populates_traceability_metadata():
    """Verify the explicitly labelled YAML cohort preserves its provenance metadata."""
    engine = BenchmarkEngine()
    stats = engine._get_population_stats("Freestyle", "Mixed", "Male", "stroke_rate")

    assert stats.evidence.source_relationship == SourceRelationship.DIRECTLY_SUPPORTED
    assert stats.evidence.population_compatibility == PopulationCompatibility.COMPATIBLE
    assert stats.evidence.source_ids == ["SRC-FREE-001"]
