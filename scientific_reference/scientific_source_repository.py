import yaml
from pathlib import Path
from typing import Dict, List, Optional

from models.scientific_evidence_models import ScientificSource, EvidenceLevel
from core.logger import setup_logger

logger = setup_logger(__name__)

class ScientificSourceRepository:
    """
    Repository layer for scientific literature sources and citation provenance.
    Decoupled from UI and business logic to allow future SQLite/PostgreSQL migration.
    """
    _sources_cache: Optional[Dict[str, ScientificSource]] = None

    def __init__(self, registry_path: Optional[Path] = None):
        if registry_path is None:
            registry_path = Path(__file__).resolve().parent / "sources" / "source_registry.yaml"
        self.registry_path = registry_path
        self._sources: Dict[str, ScientificSource] = {}
        self.load_registry()

    def load_registry(self, force_reload: bool = False):
        if not force_reload and ScientificSourceRepository._sources_cache is not None:
            self._sources = dict(ScientificSourceRepository._sources_cache)
            return

        self._sources.clear()
        if not self.registry_path.exists():
            logger.warning(f"Scientific source registry not found at {self.registry_path}")
            return

        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                raw_sources = data.get("sources", {})
                for sid, sdata in raw_sources.items():
                    elev = sdata.get("evidence_quality", "LEVEL_A")
                    try:
                        elev_enum = EvidenceLevel(elev)
                    except ValueError:
                        elev_enum = EvidenceLevel.LEVEL_A

                    self._sources[sid] = ScientificSource(
                        source_id=sid,
                        title=sdata.get("title", ""),
                        authors=sdata.get("authors", []),
                        publication_year=int(sdata.get("publication_year")) if sdata.get("publication_year") is not None else 2026,
                        journal_or_organization=sdata.get("journal_or_organization", ""),
                        doi=sdata.get("doi"),
                        pmid=sdata.get("pmid"),
                        url=sdata.get("url"),
                        stroke=sdata.get("stroke", "Freestyle"),
                        population=sdata.get("population", "Competitive Swimmers"),
                        sample_size=int(sdata.get("sample_size")) if sdata.get("sample_size") is not None else None,
                        age_range=sdata.get("age_range", "18-25"),
                        gender=sdata.get("gender", "Mixed"),
                        competitive_level=sdata.get("competitive_level", "National"),
                        measured_metrics=sdata.get("measured_metrics", []),
                        evidence_quality=elev_enum,
                        access_level=sdata.get("access_level", "FULL_TEXT_VERIFIED"),
                        verification_status=sdata.get("verification_status", "VERIFIED_CORRECT"),
                        notes=sdata.get("notes", "")
                    )
            ScientificSourceRepository._sources_cache = dict(self._sources)
            logger.info(f"Loaded {len(self._sources)} scientific literature sources from registry.")
        except Exception as e:
            logger.error(f"Failed to parse scientific source registry YAML: {e}")

    def get_source(self, source_id: str) -> Optional[ScientificSource]:
        return self._sources.get(source_id)

    def get_sources(self, source_ids: List[str]) -> List[ScientificSource]:
        return [self._sources[sid] for sid in source_ids if sid in self._sources]

    def get_all_sources(self) -> List[ScientificSource]:
        return list(self._sources.values())

    def validate_provenance(self, source_ids: List[str]) -> bool:
        """Returns True if all cited source_ids exist in the registered repository."""
        return all(sid in self._sources for sid in source_ids)
