"""
Repository for Reference Datasets, Metrics, Sources, and Audit Validation Events.
Handles CRUD and queries on SQLite via SQLAlchemy Session.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from database.models import (
    ReferenceDatasetModel, ReferenceMetricModel,
    ReferenceSourceModel, ReferenceValidationEventModel,
    ReferenceDatasetVersionModel
)
from models.reference_data_models import (
    ReferenceDataset, ReferenceMetric, ReferenceSource, ReferenceValidationEvent,
    ReferenceDatasetVersion
)

class ReferenceDataRepository:
    def __init__(self, db: Session):
        self.db = db

    def _model_to_domain(self, model: ReferenceDatasetModel) -> ReferenceDataset:
        metrics = [
            ReferenceMetric(
                metric_id=m.metric_id,
                dataset_id=m.dataset_id,
                metric_name=m.metric_name,
                display_name=m.display_name,
                value_min=m.value_min,
                value_typical=m.value_typical,
                value_median=m.value_median,
                value_max=m.value_max,
                uncertainty_sd=m.uncertainty_sd,
                unit=m.unit or "",
                measurement_domain=m.measurement_domain,
                status=m.status,
                method=m.method or "",
                notes=m.notes or "",
                event_distance=m.event_distance or "",
                course=m.course or "",
                evidence_grade=m.evidence_grade or "",
                context_only_reason=m.context_only_reason or "",
                population_match_required=m.population_match_required or ""
            ) for m in model.metrics
        ]

        sources = [
            ReferenceSource(
                source_id=s.source_id,
                dataset_id=s.dataset_id,
                source_type=s.source_type,
                source_title=s.source_title or "",
                authors=s.authors or "",
                publication_year=s.publication_year,
                doi=s.doi or "",
                pmid=s.pmid or "",
                url=s.url or "",
                sample_size=s.sample_size,
                population_description=s.population_description or ""
            ) for s in model.sources
        ]

        events = [
            ReferenceValidationEvent(
                event_id=e.event_id,
                dataset_id=e.dataset_id,
                timestamp=e.timestamp,
                user=e.user,
                action=e.action,
                old_status=e.old_status or "",
                new_status=e.new_status or "",
                notes=e.notes or ""
            ) for e in model.validation_events
        ]
        # Sort validation events chronologically
        events.sort(key=lambda x: x.timestamp)

        return ReferenceDataset(
            dataset_id=model.dataset_id,
            name=model.name,
            description=model.description or "",
            stroke=model.stroke,
            age_min=model.age_min,
            age_max=model.age_max,
            sex=model.sex,
            skill_level=model.skill_level,
            athlete_category=model.athlete_category,
            training_level=model.training_level or "",
            source_type=model.source_type,
            evidence_status=model.evidence_status,
            benchmark_eligibility=model.benchmark_eligibility,
            benchmark_priority=getattr(model, 'benchmark_priority', 'P2') or 'P2',
            validation_status=model.validation_status,
            is_archived=bool(model.is_archived),
            is_active=bool(getattr(model, 'is_active', 1)),
            dataset_version=getattr(model, 'dataset_version', 'manual_reference_v1') or 'manual_reference_v1',
            created_at=model.created_at,
            updated_at=model.updated_at,
            metrics=metrics,
            sources=sources,
            validation_events=events
        )

    def save_dataset(self, dataset: ReferenceDataset, user: str = "Coach/Admin") -> bool:
        """Create or update a reference dataset with its metrics, sources, and log an audit event."""
        now_str = datetime.now().isoformat()
        if not dataset.dataset_id:
            dataset.dataset_id = f"ds_{uuid.uuid4().hex[:8]}"
            dataset.created_at = now_str
            is_new = True
        else:
            is_new = False

        dataset.updated_at = now_str

        existing = self.db.query(ReferenceDatasetModel).filter_by(dataset_id=dataset.dataset_id).first()

        if existing:
            old_status = existing.validation_status
            existing.name = dataset.name
            existing.description = dataset.description
            existing.stroke = dataset.stroke
            existing.age_min = dataset.age_min
            existing.age_max = dataset.age_max
            existing.sex = dataset.sex
            existing.skill_level = dataset.skill_level
            existing.athlete_category = dataset.athlete_category
            existing.training_level = dataset.training_level
            existing.source_type = dataset.source_type
            existing.evidence_status = dataset.evidence_status
            existing.benchmark_eligibility = dataset.benchmark_eligibility
            existing.benchmark_priority = dataset.benchmark_priority
            existing.validation_status = dataset.validation_status
            existing.is_archived = 1 if dataset.is_archived else 0
            existing.is_active = 1 if dataset.is_active else 0
            existing.dataset_version = dataset.dataset_version
            existing.updated_at = dataset.updated_at

            # Delete old metrics and sources for clean overwrite
            self.db.query(ReferenceMetricModel).filter_by(dataset_id=dataset.dataset_id).delete()
            self.db.query(ReferenceSourceModel).filter_by(dataset_id=dataset.dataset_id).delete()
            dataset_model = existing
            action = "EDIT"
        else:
            old_status = ""
            dataset_model = ReferenceDatasetModel(
                dataset_id=dataset.dataset_id,
                name=dataset.name,
                description=dataset.description,
                stroke=dataset.stroke,
                age_min=dataset.age_min,
                age_max=dataset.age_max,
                sex=dataset.sex,
                skill_level=dataset.skill_level,
                athlete_category=dataset.athlete_category,
                training_level=dataset.training_level,
                source_type=dataset.source_type,
                evidence_status=dataset.evidence_status,
                benchmark_eligibility=dataset.benchmark_eligibility,
                benchmark_priority=dataset.benchmark_priority,
                validation_status=dataset.validation_status,
                is_archived=1 if dataset.is_archived else 0,
                is_active=1 if dataset.is_active else 0,
                dataset_version=dataset.dataset_version,
                created_at=dataset.created_at,
                updated_at=dataset.updated_at
            )
            self.db.add(dataset_model)
            action = "CREATE"

        # Add metrics
        for m in dataset.metrics:
            m_id = m.metric_id if m.metric_id else f"m_{uuid.uuid4().hex[:8]}"
            m_model = ReferenceMetricModel(
                metric_id=m_id,
                dataset_id=dataset.dataset_id,
                metric_name=m.metric_name,
                display_name=m.display_name or m.metric_name.replace("_", " ").title(),
                value_min=m.value_min,
                value_typical=m.value_typical,
                value_median=m.value_median,
                value_max=m.value_max,
                uncertainty_sd=m.uncertainty_sd,
                unit=m.unit,
                measurement_domain=m.measurement_domain,
                status=m.status,
                method=m.method,
                notes=m.notes,
                event_distance=m.event_distance,
                course=m.course,
                evidence_grade=m.evidence_grade,
                context_only_reason=m.context_only_reason,
                population_match_required=m.population_match_required
            )
            self.db.add(m_model)

        # Add sources
        for s in dataset.sources:
            s_id = s.source_id if s.source_id else f"src_{uuid.uuid4().hex[:8]}"
            s_model = ReferenceSourceModel(
                source_id=s_id,
                dataset_id=dataset.dataset_id,
                source_type=s.source_type,
                source_title=s.source_title,
                authors=s.authors,
                publication_year=s.publication_year,
                doi=s.doi,
                pmid=s.pmid,
                url=s.url,
                sample_size=s.sample_size,
                population_description=s.population_description
            )
            self.db.add(s_model)

        # Add validation audit event
        ev_model = ReferenceValidationEventModel(
            event_id=f"ev_{uuid.uuid4().hex[:8]}",
            dataset_id=dataset.dataset_id,
            timestamp=now_str,
            user=user,
            action=action,
            old_status=old_status,
            new_status=dataset.validation_status,
            notes=f"Dataset {action.lower()}d via Reference Data Manager"
        )
        self.db.add(ev_model)

        try:
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def get_dataset(self, dataset_id: str) -> Optional[ReferenceDataset]:
        """Fetch a dataset by ID with all metrics, sources, and validation events."""
        model = self.db.query(ReferenceDatasetModel).options(
            joinedload(ReferenceDatasetModel.metrics),
            joinedload(ReferenceDatasetModel.sources),
            joinedload(ReferenceDatasetModel.validation_events)
        ).filter_by(dataset_id=dataset_id).first()

        if not model:
            return None
        return self._model_to_domain(model)

    def get_all_datasets(self, include_archived: bool = False) -> List[ReferenceDataset]:
        """Fetch all datasets."""
        query = self.db.query(ReferenceDatasetModel).options(
            joinedload(ReferenceDatasetModel.metrics),
            joinedload(ReferenceDatasetModel.sources),
            joinedload(ReferenceDatasetModel.validation_events)
        )
        if not include_archived:
            query = query.filter(ReferenceDatasetModel.is_archived == 0)

        models = query.all()
        return [self._model_to_domain(m) for m in models]

    def archive_dataset(self, dataset_id: str, is_archived: bool = True, user: str = "Coach/Admin") -> bool:
        """Soft-delete/archive or unarchive a dataset."""
        model = self.db.query(ReferenceDatasetModel).filter_by(dataset_id=dataset_id).first()
        if not model:
            return False

        old_status = model.validation_status
        model.is_archived = 1 if is_archived else 0
        model.updated_at = datetime.now().isoformat()

        action = "ARCHIVE" if is_archived else "UNARCHIVE"
        ev_model = ReferenceValidationEventModel(
            event_id=f"ev_{uuid.uuid4().hex[:8]}",
            dataset_id=dataset_id,
            timestamp=model.updated_at,
            user=user,
            action=action,
            old_status=old_status,
            new_status=model.validation_status,
            notes=f"Dataset {action.lower()}d"
        )
        self.db.add(ev_model)

        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

    def delete_dataset(self, dataset_id: str, user: str = "Coach/Admin") -> bool:
        """Hard delete a dataset (requires explicit confirmation)."""
        model = self.db.query(ReferenceDatasetModel).filter_by(dataset_id=dataset_id).first()
        if not model:
            return False
        try:
            self.db.delete(model)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

    def add_validation_event(self, dataset_id: str, action: str, old_status: str, new_status: str, notes: str, user: str = "Coach/Admin") -> bool:
        """Record an explicit validation event."""
        model = self.db.query(ReferenceDatasetModel).filter_by(dataset_id=dataset_id).first()
        if not model:
            return False

        now_str = datetime.now().isoformat()
        if new_status:
            model.validation_status = new_status
            model.updated_at = now_str

        ev_model = ReferenceValidationEventModel(
            event_id=f"ev_{uuid.uuid4().hex[:8]}",
            dataset_id=dataset_id,
            timestamp=now_str,
            user=user,
            action=action,
            old_status=old_status,
            new_status=new_status,
            notes=notes
        )
        self.db.add(ev_model)

        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

    def find_potential_duplicates(
        self, stroke: str, age_min: int, age_max: int, sex: str, skill_level: str,
        title: str = "", doi: str = "", pmid: str = "", dataset_id_to_ignore: str = ""
    ) -> List[ReferenceDataset]:
        """Detect likely duplicates based on stroke, age range, sex, skill level, or DOI/PMID/title."""
        all_ds = self.get_all_datasets(include_archived=True)
        duplicates = []

        for ds in all_ds:
            if dataset_id_to_ignore and ds.dataset_id == dataset_id_to_ignore:
                continue

            match_demographics = (
                ds.stroke.upper() == stroke.upper() and
                ds.sex.lower() == sex.lower() and
                ds.skill_level.lower() == skill_level.lower() and
                abs(ds.age_min - age_min) <= 2 and
                abs(ds.age_max - age_max) <= 2
            )

            match_doi_pmid = False
            match_title = False
            for src in ds.sources:
                if doi and src.doi and src.doi.strip().lower() == doi.strip().lower():
                    match_doi_pmid = True
                if pmid and src.pmid and src.pmid.strip().lower() == pmid.strip().lower():
                    match_doi_pmid = True
                if title and src.source_title and title.strip().lower() in src.source_title.strip().lower():
                    match_title = True

            if match_demographics or match_doi_pmid or match_title:
                duplicates.append(ds)

        return duplicates

    def save_dataset_version(self, version: ReferenceDatasetVersion) -> bool:
        """Saves a dataset version record."""
        existing = self.db.query(ReferenceDatasetVersionModel).filter_by(version_name=version.version_name).first()
        if existing:
            existing.filename = version.filename
            existing.imported_at = version.imported_at
            existing.record_count = version.record_count
            existing.valid_count = version.valid_count
            existing.rejected_count = version.rejected_count
            existing.is_active = 1 if version.is_active else 0
            existing.importer = version.importer
        else:
            v_model = ReferenceDatasetVersionModel(
                version_id=version.version_id or f"ver_{uuid.uuid4().hex[:8]}",
                version_name=version.version_name,
                filename=version.filename,
                imported_at=version.imported_at,
                record_count=version.record_count,
                valid_count=version.valid_count,
                rejected_count=version.rejected_count,
                is_active=1 if version.is_active else 0,
                importer=version.importer
            )
            self.db.add(v_model)

        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

    def get_dataset_versions(self) -> List[ReferenceDatasetVersion]:
        """Fetch all registered dataset versions."""
        models = self.db.query(ReferenceDatasetVersionModel).all()
        return [
            ReferenceDatasetVersion(
                version_id=m.version_id,
                version_name=m.version_name,
                filename=m.filename,
                imported_at=m.imported_at,
                record_count=m.record_count,
                valid_count=m.valid_count,
                rejected_count=m.rejected_count,
                is_active=bool(m.is_active),
                importer=m.importer
            ) for m in models
        ]

    def set_version_active(self, version_name: str, is_active: bool) -> bool:
        """Activate or deactivate all dataset records belonging to a version."""
        v_model = self.db.query(ReferenceDatasetVersionModel).filter_by(version_name=version_name).first()
        if v_model:
            v_model.is_active = 1 if is_active else 0

        self.db.query(ReferenceDatasetModel).filter_by(dataset_version=version_name).update(
            {"is_active": 1 if is_active else 0}
        )
        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

