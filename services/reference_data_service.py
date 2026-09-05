"""
High-level service layer for the Reference Data Manager.
Coordinates database access, validation, audit trail logging, and duplicate detection.
"""

from typing import List, Optional, Tuple, Any
from database import SessionLocal
from database.reference_repository import ReferenceDataRepository
from models.reference_data_models import (
    ReferenceDataset, ReferenceValidationStatus, ReferenceBenchmarkEligibility, ReferenceSourceType
)
from services.reference_data_validator import ReferenceDataValidator, ScientificValidationResult
from services.reference_resolver import ReferenceDataResolver, ResolvedReferenceMatch

class ReferenceDataService:
    def __init__(self, db_session=None, principal: Optional[Any] = None):
        self._owns_session = False
        if db_session is None:
            self.db = SessionLocal()
            self._owns_session = True
        else:
            self.db = db_session
        self.principal = principal
        self.repo = ReferenceDataRepository(self.db)

    def _check_admin(self, principal: Optional[Any] = None) -> str:
        active_principal = principal if principal is not None else self.principal
        if not active_principal or getattr(active_principal, "role", None) != "admin":
            raise PermissionError("Global write access denied. Administrator privileges required to modify reference data.")
        return getattr(active_principal, "username", None) or getattr(active_principal, "full_name", None) or "admin"

    def __del__(self):
        if hasattr(self, '_owns_session') and self._owns_session and self.db:
            try:
                self.db.close()
            except Exception:
                pass

    def get_all_datasets(self, include_archived: bool = False) -> List[ReferenceDataset]:
        """Fetch all datasets."""
        return self.repo.get_all_datasets(include_archived=include_archived)

    def get_dataset(self, dataset_id: str) -> Optional[ReferenceDataset]:
        """Fetch single dataset by ID."""
        return self.repo.get_dataset(dataset_id)

    def save_dataset(self, dataset: ReferenceDataset, user: Optional[str] = None, principal: Optional[Any] = None) -> Tuple[bool, ScientificValidationResult]:
        """Validate and save a reference dataset with mandatory admin authorization."""
        admin_user = self._check_admin(principal)
        effective_user = user or admin_user

        val_res = ReferenceDataValidator.validate_dataset(dataset)
        if not val_res.is_valid:
            return False, val_res

        # Apply suggested eligibility if present
        if val_res.suggested_eligibility:
            dataset.benchmark_eligibility = val_res.suggested_eligibility

        success = self.repo.save_dataset(dataset, user=effective_user)
        return success, val_res

    def validate_and_update_status(self, dataset_id: str, new_status: str, notes: str, user: Optional[str] = None, principal: Optional[Any] = None) -> bool:
        """Update validation status (e.g., DRAFT -> SCIENTIFICALLY_VALIDATED) with audit logging and mandatory admin authorization."""
        admin_user = self._check_admin(principal)
        effective_user = user or admin_user

        ds = self.repo.get_dataset(dataset_id)
        if not ds:
            return False

        old_status = ds.validation_status
        # Rule 1 check: COACH_DEFINED cannot automatically become BENCHMARK unless validated
        if new_status == ReferenceValidationStatus.SCIENTIFICALLY_VALIDATED.value:
            if ds.source_type in [ReferenceSourceType.PEER_REVIEWED_PRIMARY_STUDY.value, ReferenceSourceType.PEER_REVIEWED_SYSTEMATIC_REVIEW.value, ReferenceSourceType.PEER_REVIEWED_META_ANALYSIS.value]:
                ds.benchmark_eligibility = ReferenceBenchmarkEligibility.BENCHMARK.value
            else:
                ds.benchmark_eligibility = ReferenceBenchmarkEligibility.CONTEXT_ONLY.value
        elif new_status == ReferenceValidationStatus.REJECTED.value:
            ds.benchmark_eligibility = ReferenceBenchmarkEligibility.NOT_ELIGIBLE.value

        return self.repo.add_validation_event(dataset_id, "VALIDATE", old_status, new_status, notes, user=effective_user)

    def archive_dataset(self, dataset_id: str, is_archived: bool = True, user: Optional[str] = None, principal: Optional[Any] = None) -> bool:
        """Archive or unarchive a dataset with mandatory admin authorization."""
        admin_user = self._check_admin(principal)
        effective_user = user or admin_user
        return self.repo.archive_dataset(dataset_id, is_archived=is_archived, user=effective_user)

    def delete_dataset(self, dataset_id: str, user: Optional[str] = None, principal: Optional[Any] = None) -> bool:
        """Hard delete a dataset with mandatory admin authorization."""
        admin_user = self._check_admin(principal)
        effective_user = user or admin_user
        return self.repo.delete_dataset(dataset_id, user=effective_user)

    def check_duplicates(self, dataset: ReferenceDataset) -> List[ReferenceDataset]:
        """Detect potential duplicate datasets."""
        doi = dataset.sources[0].doi if dataset.sources else ""
        pmid = dataset.sources[0].pmid if dataset.sources else ""
        title = dataset.sources[0].source_title if dataset.sources else ""

        return self.repo.find_potential_duplicates(
            stroke=dataset.stroke,
            age_min=dataset.age_min,
            age_max=dataset.age_max,
            sex=dataset.sex,
            skill_level=dataset.skill_level,
            title=title,
            doi=doi,
            pmid=pmid,
            dataset_id_to_ignore=dataset.dataset_id
        )

    def resolve_reference(
        self, metric_name: str, stroke: str, age: int, sex: str, skill_level: str = "Unknown", test_protocol: Optional[str] = None
    ) -> ResolvedReferenceMatch:
        """Resolve top reference dataset for a given metric and athlete profile."""
        all_ds = self.repo.get_all_datasets(include_archived=False)
        return ReferenceDataResolver.resolve_metric_reference(
            datasets=all_ds,
            metric_name=metric_name,
            stroke=stroke,
            athlete_age=age,
            athlete_sex=sex,
            athlete_skill=skill_level,
            test_protocol=test_protocol
        )

    def get_dataset_versions(self):
        """Fetch all registered dataset versions."""
        return self.repo.get_dataset_versions()

    def activate_dataset_version(self, version_name: str, principal: Optional[Any] = None) -> bool:
        """Activate a dataset version with mandatory admin authorization."""
        self._check_admin(principal)
        return self.repo.set_version_active(version_name, is_active=True)

    def deactivate_dataset_version(self, version_name: str, principal: Optional[Any] = None) -> bool:
        """Deactivate a dataset version with mandatory admin authorization."""
        self._check_admin(principal)
        return self.repo.set_version_active(version_name, is_active=False)
