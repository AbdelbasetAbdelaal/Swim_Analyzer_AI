from typing import Any, List, Optional

from scientific_reference.scientific_source_repository import ScientificSourceRepository
from models.scientific_evidence_models import ScientificSource, ValidationStatus, EvidenceLevel
from core.logger import setup_logger

logger = setup_logger(__name__)

class ScientificEvidenceService:
    """
    Service layer orchestrating scientific evidence validation and citation lookup.
    Keeps UI and reporting completely decoupled from citation data stores.
    """
    def __init__(self, repo: Optional[ScientificSourceRepository] = None):
        if repo is None:
            repo = ScientificSourceRepository()
        self.repo = repo

    def get_sources_for_ids(self, source_ids: List[str]) -> List[ScientificSource]:
        return self.repo.get_sources(source_ids)

    def format_citation(self, source: ScientificSource) -> str:
        """Formats source into APA-style scientific citation string."""
        authors_str = ", ".join(source.authors) if source.authors else "Unknown Authors"
        doi_str = f" DOI: {source.doi}" if source.doi else ""
        return f"{authors_str} ({source.publication_year}). {source.title}. {source.journal_or_organization}.{doi_str}"

    def evaluate_evidence_confidence(self, validation_status: ValidationStatus,
                                    evidence_level: EvidenceLevel) -> str:
        """Returns qualitative Scientific Evidence Confidence string (High, Medium, Low)."""
        if validation_status == ValidationStatus.VALIDATED and evidence_level in [EvidenceLevel.LEVEL_A, EvidenceLevel.LEVEL_B]:
            return "High"
        elif validation_status == ValidationStatus.PARTIALLY_VALIDATED or evidence_level == EvidenceLevel.LEVEL_C:
            return "Medium"
        else:
            return "Low"

    def get_evidence_record(self, evidence_id: str) -> Optional[Any]:
        """Resolves an evidence record by evidence_id (e.g. EVID-FREE-001)."""
        from scientific_reference.storage.scientific_evidence_registry import ScientificEvidenceRegistry
        return ScientificEvidenceRegistry().get_record(evidence_id)

    def get_evidence_for_source(self, source_id: str, measurement_name: Optional[str] = None) -> Optional[Any]:
        """Resolves an evidence record by source_id (e.g. SRC-BACK-GONJO-2020) and optional metric name."""
        from scientific_reference.storage.scientific_evidence_registry import ScientificEvidenceRegistry
        reg = ScientificEvidenceRegistry()
        candidates = [r for r in reg.get_all_records() if r.source_id == source_id]
        if not candidates:
            return None
        if measurement_name:
            for r in candidates:
                if r.measurement_name.lower() == measurement_name.lower():
                    return r
        return candidates[0]

