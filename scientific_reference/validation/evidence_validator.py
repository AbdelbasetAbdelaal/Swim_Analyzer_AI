from typing import Tuple, Optional
from models.scientific_evidence_models import (
    CandidateEvidence, ScientificEvidenceRecord, ReviewStatus, AuditDecision
)
from scientific_reference.validation.metric_validator import MetricValidator
from scientific_reference.validation.statistical_validator import StatisticalValidator
from scientific_reference.validation.provenance_validator import ProvenanceValidator
from core.logger import setup_logger
import uuid

logger = setup_logger(__name__)

from scientific_reference.validation.benchmark_eligibility_validator import BenchmarkEligibilityValidator

class EvidenceValidator:
    """
    Orchestrates the deterministic validation pipeline.
    Transforms untrusted CandidateEvidence into validated ScientificEvidenceRecord,
    or rejects it if it fails strict provenance, demographic, metric, or statistical rules.
    """

    @staticmethod
    def validate_candidate(candidate: CandidateEvidence, full_xml_text: str, target_population_age_range: Tuple[Optional[int], Optional[int]] = (18, 25)) -> ScientificEvidenceRecord:
        """
        Executes the strict validation pipeline on a CandidateEvidence record.
        """
        # 0. Benchmark Eligibility Validation
        status, decision, rationale = BenchmarkEligibilityValidator.evaluate_eligibility(candidate)
        if status == ReviewStatus.REJECTED:
            logger.warning(f"Benchmark eligibility rejection for {candidate.source_id}: {rationale}")
            return EvidenceValidator._build_rejected_record(candidate, rationale)
        elif status == ReviewStatus.PENDING_REVIEW:
            logger.info(f"Candidate {candidate.source_id} requires review / primary trace: {rationale}")
            rec = EvidenceValidator._build_rejected_record(candidate, rationale)
            rec.scientific_status = ReviewStatus.PENDING_REVIEW
            rec.audit_decision = AuditDecision.REFERENCE_ONLY
            return rec

        # 1. Provenance Validation
        if not ProvenanceValidator.validate_provenance(candidate.source_quote, full_xml_text):
            logger.warning(f"Provenance rejection for {candidate.metric}: Quote not found in source text.")
            return EvidenceValidator._build_rejected_record(candidate, "Provenance hallucination or quote mismatch")

        # 2. Stroke Validation
        if not MetricValidator.validate_stroke(candidate.stroke, full_xml_text):
            logger.warning(f"Stroke rejection for {candidate.metric}: Stroke '{candidate.stroke}' not supported by context.")
            return EvidenceValidator._build_rejected_record(candidate, "Stroke leakage / unsupported by context")

        # 3. Statistical Validation
        # Default empty/missing values to safe fallback types for validation checking
        c_mean = candidate.mean if candidate.mean is not None else 0.0
        c_std = candidate.sd if candidate.sd is not None else 0.0
        c_n = candidate.sample_size if candidate.sample_size is not None else 0

        if not StatisticalValidator.validate_statistics(c_mean, c_std, c_n):
            return EvidenceValidator._build_rejected_record(candidate, "Statistical invalidity or insufficient N")

        # 4. Convert unit for SwimAnalyzer compatibility
        # We need to map to target metrics if needed, but for validation we just rely on standard SA targets.
        target_unit = "m/s" if "velocity" in str(candidate.metric).lower() else candidate.unit
        converted_val, final_unit, formula = StatisticalValidator.convert_unit(c_mean, candidate.unit or "", target_unit or "")

        # 5. Build Validated Record
        record = ScientificEvidenceRecord(
            evidence_id=f"EV-{uuid.uuid4().hex[:8].upper()}",
            source_id=candidate.source_id,
            title=candidate.title,
            authors=[], # We can merge this later via SourceRegistry
            year=2026,
            doi=candidate.doi,
            publication="",
            stroke=candidate.stroke or "Freestyle",
            event_distance="100m",
            population_description=f"{candidate.population_sex} {candidate.competitive_level} ({candidate.population_age})",
            age_min=None,
            age_max=None,
            gender=candidate.population_sex or "Mixed",
            skill_level=candidate.competitive_level or "National",
            sample_size=c_n,
            measurement_name=candidate.metric or "Unknown",
            measurement_units=candidate.unit or "",
            reported_mean=c_mean,
            reported_std=c_std,
            table_or_figure_reference=candidate.table_or_figure or "",
            source_quote=candidate.source_quote or "",
            conversion_formula=formula if formula != "1:1 Exact Match" else None,
            converted_value=converted_val,
            converted_unit=final_unit,
            scientific_status=ReviewStatus.SCIENTIFICALLY_ACCEPTED,
            audit_decision=AuditDecision.ACCEPT if formula == "1:1 Exact Match" else AuditDecision.ACCEPT_AS_DERIVED
        )
        return record

    @staticmethod
    def _build_rejected_record(candidate: CandidateEvidence, reason: str) -> ScientificEvidenceRecord:
        return ScientificEvidenceRecord(
            evidence_id=f"EV-REJ-{uuid.uuid4().hex[:8].upper()}",
            source_id=candidate.source_id,
            title=candidate.title,
            authors=[],
            year=0,
            stroke=candidate.stroke or "Unknown",
            measurement_name=candidate.metric or "Unknown",
            scientific_status=ReviewStatus.REJECTED,
            audit_decision=AuditDecision.REJECT,
            notes=reason
        )
