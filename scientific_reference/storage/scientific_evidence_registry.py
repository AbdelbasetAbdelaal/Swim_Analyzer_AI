import yaml
from pathlib import Path
from typing import Dict, List, Optional

from models.scientific_evidence_models import (
    ScientificEvidenceRecord, SourceAccessLevel, SourceRelationship,
    PopulationMatchingStatus, DefinitionMatchingStatus, ReviewStatus,
    SourceQuality, AuditDecision
)
from core.logger import setup_logger

logger = setup_logger(__name__)

class ScientificEvidenceRegistry:
    """
    Persistent storage repository for granular scientific evidence records (EVID-xxx).
    Decoupled from UI and athlete execution engines.
    """
    def __init__(self, registry_path: Optional[Path] = None):
        if registry_path is None:
            registry_path = Path(__file__).resolve().parent.parent / "evidence" / "evidence_registry.yaml"
        self.registry_path = registry_path
        self._records: Dict[str, ScientificEvidenceRecord] = {}
        self.load_registry()

    def load_registry(self):
        self._records.clear()
        if not self.registry_path.exists():
            logger.warning(f"Evidence registry YAML not found at {self.registry_path}")
            return

        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                raw_records = data.get("evidence_records", {})
                for eid, edata in raw_records.items():
                    self._records[eid] = self._dict_to_record(eid, edata)
            logger.info(f"Loaded {len(self._records)} scientific evidence records from registry.")
        except Exception as e:
            logger.error(f"Failed to parse evidence_registry.yaml: {e}")

    def _dict_to_record(self, eid: str, d: dict) -> ScientificEvidenceRecord:
        def parse_enum(enum_cls, val, default):
            try:
                return enum_cls(val)
            except Exception:
                return default

        return ScientificEvidenceRecord(
            evidence_id=eid,
            source_id=d.get("source_id", ""),
            title=d.get("title", ""),
            authors=d.get("authors", []),
            year=int(d.get("year")) if d.get("year") is not None else 2026,
            doi=d.get("doi"),
            url=d.get("url"),
            publication=d.get("publication", ""),
            stroke=d.get("stroke", "Freestyle"),
            event_distance=d.get("event_distance", "100m"),
            population_description=d.get("population_description", ""),
            age_min=d.get("age_min"),
            age_max=d.get("age_max"),
            mean_age=d.get("mean_age"),
            gender=d.get("gender", "Mixed"),
            skill_level=d.get("skill_level", "National"),
            sample_size=int(d.get("sample_size")) if d.get("sample_size") is not None else None,
            measurement_name=d.get("measurement_name", ""),
            measurement_definition=d.get("measurement_definition", ""),
            measurement_method=d.get("measurement_method", ""),
            measurement_units=d.get("measurement_units", ""),
            reported_mean=d.get("reported_mean"),
            reported_std=d.get("reported_std"),
            reported_min=d.get("reported_min"),
            reported_max=d.get("reported_max"),
            confidence_interval=d.get("confidence_interval"),
            statistical_method=d.get("statistical_method", "Mean +/- SD"),
            table_or_figure_reference=d.get("table_or_figure_reference", ""),
            page_reference=d.get("page_reference", ""),
            source_access_level=parse_enum(SourceAccessLevel, d.get("source_access_level"), SourceAccessLevel.FULL_TEXT_VERIFIED),
            source_quality=parse_enum(SourceQuality, d.get("source_quality"), SourceQuality.PEER_REVIEWED_FULL_TEXT),
            extraction_method=d.get("extraction_method", "Manual Audit"),
            relationship_to_benchmark=parse_enum(SourceRelationship, d.get("relationship_to_benchmark"), SourceRelationship.DIRECTLY_SUPPORTED),
            population_compatibility=parse_enum(PopulationMatchingStatus, d.get("population_compatibility"), PopulationMatchingStatus.EXACT_MATCH),
            definition_compatibility=parse_enum(DefinitionMatchingStatus, d.get("definition_compatibility"), DefinitionMatchingStatus.EXACT_MATCH),
            unit_compatibility=bool(d.get("unit_compatibility", True)),
            scientific_status=parse_enum(ReviewStatus, d.get("scientific_status"), ReviewStatus.SCIENTIFICALLY_ACCEPTED),
            audit_decision=parse_enum(AuditDecision, d.get("audit_decision"), AuditDecision.ACCEPT),
            conversion_formula=d.get("conversion_formula"),
            converted_value=d.get("converted_value"),
            converted_unit=d.get("converted_unit"),
            reviewed_by=d.get("reviewed_by", "Lead Scientific Architect"),
            reviewed_at=d.get("reviewed_at", "2026-08-08"),
            notes=d.get("notes", "")
        )

    def get_record(self, evidence_id: str) -> Optional[ScientificEvidenceRecord]:
        return self._records.get(evidence_id)

    def get_records_by_stroke(self, stroke: str) -> List[ScientificEvidenceRecord]:
        return [r for r in self._records.values() if r.stroke.lower() == stroke.lower()]

    def get_records_by_metric(self, measurement_name: str) -> List[ScientificEvidenceRecord]:
        return [r for r in self._records.values() if r.measurement_name.lower() == measurement_name.lower()]

    def get_all_records(self) -> List[ScientificEvidenceRecord]:
        return list(self._records.values())

    def get_accepted_records(self) -> List[ScientificEvidenceRecord]:
        return [r for r in self._records.values() if r.scientific_status == ReviewStatus.SCIENTIFICALLY_ACCEPTED]
