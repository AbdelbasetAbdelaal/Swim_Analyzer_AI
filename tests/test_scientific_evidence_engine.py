from models.scientific_evidence_models import (
    CandidateEvidence, PopulationMatchingStatus, DefinitionMatchingStatus,
    ScientificEvidenceRecord
)
from scientific_reference.validation.population_validator import PopulationValidator
from scientific_reference.validation.metric_validator import MetricValidator
from scientific_reference.validation.statistical_validator import StatisticalValidator
from scientific_reference.validation.provenance_validator import ProvenanceValidator
from scientific_reference.validation.evidence_validator import EvidenceValidator
from scientific_reference.evidence_aggregator import EvidenceAggregator

def test_demographic_leakage():
    # Adult to youth leakage must be rejected
    status = PopulationValidator.evaluate_population_match("Adult", "Youth", (18, 25), (8, 12))
    assert status == PopulationMatchingStatus.POPULATION_MISMATCH

def test_stroke_leakage():
    # Freestyle candidate inside Backstroke text should be rejected
    assert not MetricValidator.validate_stroke("Freestyle", "The swimmers performed 100m backstroke trials.")
    assert MetricValidator.validate_stroke("Backstroke", "The swimmers performed 100m backstroke trials.")

def test_metric_mismatch():
    # Shoulder roll should not match torso normal vector
    status = MetricValidator.evaluate_definition_match("shoulder roll", "torso normal vector")
    assert status == DefinitionMatchingStatus.DEFINITION_MISMATCH
    
    # Stroke rate should match cycle frequency
    status2 = MetricValidator.evaluate_definition_match("cycle frequency", "stroke rate")
    assert status2 == DefinitionMatchingStatus.EXACT_MATCH

def test_insufficient_sample_size():
    # N < 5 is statistically unreliable
    assert not StatisticalValidator.validate_statistics(50.0, 5.0, 4)
    assert StatisticalValidator.validate_statistics(50.0, 5.0, 15)

def test_provenance_hallucination():
    # Quote must exactly match part of the XML
    xml_text = "The mean velocity was 1.6 m/s for elite males."
    assert ProvenanceValidator.validate_provenance("mean velocity was 1.6", xml_text)
    # Hallucinated value not in text
    assert not ProvenanceValidator.validate_provenance("mean velocity was 1.8", xml_text)

def test_evidence_validator_integration():
    # End-to-end validation of a candidate
    cand = CandidateEvidence(
        source_id="SRC-1", pmid="123", pmcid=None, doi=None, title="Test",
        stroke="Freestyle", population_sex="Male", population_age="18-25", competitive_level="Elite",
        metric="swimming velocity", mean=1.8, sd=0.1, unit="m/s", sample_size=20,
        table_or_figure="Table 1", source_quote="velocity was 1.8 m/s", xml_block_type="text"
    )
    xml = "The velocity was 1.8 m/s in the freestyle trial."
    
    record = EvidenceValidator.validate_candidate(cand, xml)
    assert record.scientific_status == "SCIENTIFICALLY_ACCEPTED"
    assert record.converted_value == 1.8

    # Fail provenance
    bad_cand = CandidateEvidence(
        source_id="SRC-1", pmid="123", pmcid=None, doi=None, title="Test",
        stroke="Freestyle", population_sex="Male", population_age="18-25", competitive_level="Elite",
        metric="swimming velocity", mean=2.0, sd=0.1, unit="m/s", sample_size=20,
        table_or_figure="Table 1", source_quote="velocity was 2.0 m/s", xml_block_type="text"
    )
    bad_record = EvidenceValidator.validate_candidate(bad_cand, xml)
    assert bad_record.scientific_status == "REJECTED"
    assert "Provenance" in bad_record.notes

def test_evidence_aggregation_valid():
    r1 = ScientificEvidenceRecord(
        evidence_id="1", source_id="s1", title="t", authors=[], year=2020,
        stroke="Freestyle", gender="Male", sample_size=20, measurement_name="stroke_rate",
        reported_mean=40.0, reported_std=2.0, converted_value=40.0, converted_unit="spm",
        scientific_status="SCIENTIFICALLY_ACCEPTED"
    )
    r2 = ScientificEvidenceRecord(
        evidence_id="2", source_id="s2", title="t", authors=[], year=2021,
        stroke="Freestyle", gender="Male", sample_size=30, measurement_name="stroke_rate",
        reported_mean=42.0, reported_std=3.0, converted_value=42.0, converted_unit="spm",
        scientific_status="SCIENTIFICALLY_ACCEPTED"
    )
    
    agg = EvidenceAggregator.aggregate_evidence([r1, r2], "Freestyle", "Male", "18-25", "stroke_rate")
    assert agg is not None
    assert agg.total_sample_size == 50
    # Weighted mean: (40*20 + 42*30) / 50 = (800 + 1260) / 50 = 2060 / 50 = 41.2
    assert agg.aggregated_mean == 41.2
    assert not agg.is_conflicting

def test_evidence_aggregation_conflicting():
    r1 = ScientificEvidenceRecord(
        evidence_id="1", source_id="s1", title="t", authors=[], year=2020,
        stroke="Freestyle", gender="Male", sample_size=20, measurement_name="stroke_rate",
        reported_mean=40.0, reported_std=1.0, converted_value=40.0, converted_unit="spm",
        scientific_status="SCIENTIFICALLY_ACCEPTED"
    )
    r2 = ScientificEvidenceRecord(
        evidence_id="2", source_id="s2", title="t", authors=[], year=2021,
        stroke="Freestyle", gender="Male", sample_size=30, measurement_name="stroke_rate",
        reported_mean=60.0, reported_std=1.0, converted_value=60.0, converted_unit="spm",
        scientific_status="SCIENTIFICALLY_ACCEPTED"
    )
    
    agg = EvidenceAggregator.aggregate_evidence([r1, r2], "Freestyle", "Male", "18-25", "stroke_rate")
    assert agg is not None
    assert agg.is_conflicting == True
