import yaml
from pathlib import Path

from scientific_reference.storage.scientific_evidence_registry import ScientificEvidenceRegistry
from models.scientific_evidence_models import (
    ReviewStatus, AuditDecision, DefinitionMatchingStatus, SourceAccessLevel
)

def test_final_audit_safety_rule_1_exact_source_location():
    """SAFETY RULE: Accepted benchmarks MUST have non-empty exact table/figure and page references."""
    registry = ScientificEvidenceRegistry()
    accepted = [
        r for r in registry.get_all_records()
        if r.audit_decision in [AuditDecision.ACCEPT, AuditDecision.ACCEPT_AS_DERIVED]
    ]
    assert len(accepted) >= 5, "Expected at least 5 accepted benchmark evidence records"

    for r in accepted:
        assert r.table_or_figure_reference != "", f"Record {r.evidence_id} missing table/figure reference"
        assert r.page_reference != "", f"Record {r.evidence_id} missing page reference"
        assert r.sample_size > 0, f"Record {r.evidence_id} has invalid sample size N={r.sample_size}"

def test_final_audit_safety_rule_2_definition_mismatch_guard():
    """SAFETY RULE: Records with DEFINITION_MISMATCH cannot be marked ACCEPT or SCIENTIFICALLY_ACCEPTED."""
    registry = ScientificEvidenceRegistry()
    mismatched = [
        r for r in registry.get_all_records()
        if r.definition_compatibility == DefinitionMatchingStatus.DEFINITION_MISMATCH
    ]
    
    for r in mismatched:
        assert r.audit_decision not in [AuditDecision.ACCEPT, AuditDecision.ACCEPT_AS_DERIVED], \
            f"Record {r.evidence_id} has DEFINITION_MISMATCH but was decision {r.audit_decision}"
        assert r.scientific_status != ReviewStatus.SCIENTIFICALLY_ACCEPTED, \
            f"Record {r.evidence_id} has DEFINITION_MISMATCH but was status {r.scientific_status}"

def test_final_audit_safety_rule_3_derived_conversion_formula():
    """SAFETY RULE: Any ACCEPT_AS_DERIVED benchmark MUST contain an explicit non-empty conversion formula."""
    registry = ScientificEvidenceRegistry()
    derived = [
        r for r in registry.get_all_records()
        if r.audit_decision == AuditDecision.ACCEPT_AS_DERIVED
    ]
    assert len(derived) >= 1

    for r in derived:
        assert r.conversion_formula is not None and r.conversion_formula != "", \
            f"Derived record {r.evidence_id} missing conversion formula"
        assert r.converted_value is not None, f"Derived record {r.evidence_id} missing converted_value"

def test_final_audit_safety_rule_4_youth_masters_scaling_suppression():
    """SAFETY RULE: Non-adult cohorts MUST NOT use adult scaling heuristics as validated benchmarks."""
    benchmark_dir = Path(__file__).resolve().parent.parent / "config" / "benchmarks"
    for yfile in benchmark_dir.glob("*.yaml"):
        with open(yfile, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        pops = data.get("populations", {})
        for cohort in ["8-10", "11-13", "Masters"]:
            cohort_data = pops.get(cohort, {})
            status = cohort_data.get("status", "INSUFFICIENT_EVIDENCE") if isinstance(cohort_data, dict) else "INSUFFICIENT_EVIDENCE"
            assert status == "INSUFFICIENT_EVIDENCE", \
                f"Cohort {cohort} in {yfile.name} must be INSUFFICIENT_EVIDENCE"

def test_final_audit_safety_rule_5_unverified_access_level_guard():
    """SAFETY RULE: Unverified or metadata-only sources CANNOT be marked ACCEPT or SCIENTIFICALLY_ACCEPTED."""
    registry = ScientificEvidenceRegistry()
    unverified = [
        r for r in registry.get_all_records()
        if r.source_access_level in [SourceAccessLevel.METADATA_ONLY, SourceAccessLevel.UNVERIFIED]
    ]

    for r in unverified:
        assert r.audit_decision not in [AuditDecision.ACCEPT, AuditDecision.ACCEPT_AS_DERIVED]
        assert r.scientific_status != ReviewStatus.SCIENTIFICALLY_ACCEPTED
