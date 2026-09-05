"""
Reference Data Manager Service.
Central business logic for importing CSV datasets, managing reference datasets,
executing versioning, priority resolution, duplicate detection, and exports.
"""

from typing import List, Optional, Tuple
from database import SessionLocal
from database.reference_repository import ReferenceDataRepository
from services.reference_data_validator import ReferenceDataValidator
from services.reference_resolver import ReferenceDataResolver
from services.reference_export_service import ReferenceExportService
from services.csv_registry_importer import CSVRegistryImporter
from models.reference_data_models import (
    ReferenceDataset, ReferenceMetric, ReferenceDatasetVersion, ReferenceBenchmarkEligibility
)

class ReferenceDataManager:
    """
    Service managing reference datasets, versioning, priorities, and scientific integrity.
    Does NOT contain Streamlit UI code.
    """
    def __init__(self):
        self._db = SessionLocal()
        self._repo = ReferenceDataRepository(self._db)

    def close(self):
        if self._db:
            self._db.close()

    def import_csv(
        self,
        principal,
        filepath: str,
        version_name: str = "manual_reference_v1",
        importer: str = "System/Coach"
    ) -> Tuple[int, int, List[str]]:
        """Imports a reference CSV file into database with specified version name."""
        if not principal or getattr(principal, "role", "coach") != "admin":
            raise PermissionError("Global write access denied. Administrator privileges required to import reference data.")
            
        valid, rejected, errs = CSVRegistryImporter.import_scientific_registry_csv(
            csv_path=filepath,
            version_name=version_name,
            importer_name=importer
        )
        return valid, rejected, errs

    def get_records(
        self,
        stroke: Optional[str] = None,
        metric_name: Optional[str] = None,
        age: Optional[int] = None,
        sex: Optional[str] = None,
        priority: Optional[str] = None,
        eligibility: Optional[str] = None,
        include_inactive: bool = False,
        include_archived: bool = False
    ) -> List[ReferenceDataset]:
        """Fetch reference datasets with optional filters."""
        all_ds = self._repo.get_all_datasets(include_archived=include_archived)

        filtered = []
        for ds in all_ds:
            if not include_inactive and not ds.is_active:
                continue
            if stroke and stroke.upper() != "ALL" and ds.stroke.upper() != stroke.upper():
                continue
            if sex and sex.lower() != "all" and ds.sex.lower() != "mixed" and ds.sex.lower() != sex.lower():
                continue
            if age is not None:
                if ds.age_min is not None and age < ds.age_min:
                    continue
                if ds.age_max is not None and age > ds.age_max:
                    continue
            if priority and ds.benchmark_priority != priority:
                continue
            if eligibility and ds.benchmark_eligibility != eligibility:
                continue
            if metric_name:
                _norm = ReferenceDataResolver._normalize_metric_name
                has_m = any(
                    _norm(m.metric_name) == _norm(metric_name)
                    or _norm(m.display_name) == _norm(metric_name)
                    for m in ds.metrics
                )
                if not has_m:
                    continue

            filtered.append(ds)

        return filtered

    def get_benchmark_candidates(
        self,
        stroke: str,
        metric_name: str,
        age: int = 20,
        sex: str = "Male"
    ) -> List[ReferenceDataset]:
        """Returns candidate datasets compatible with the demographic profile."""
        all_active = self.get_records(stroke=stroke, metric_name=metric_name, include_inactive=False)
        candidates = []
        for ds in all_active:
            score, _ = ReferenceDataResolver.calculate_compatibility(ds, stroke=stroke, age=age, sex=sex)
            if score > 0:
                candidates.append(ds)
        return candidates

    def get_benchmark_for_metric(
        self,
        stroke: str,
        metric_name: str,
        age: int = 20,
        sex: str = "Male"
    ) -> Optional[ReferenceMetric]:
        """Resolves the top benchmark metric value according to P0 > P1 priority and scientific eligibility."""
        candidates = self.get_records(stroke=stroke, metric_name=metric_name, include_inactive=False)
        eligible = [ds for ds in candidates if ds.benchmark_eligibility == ReferenceBenchmarkEligibility.BENCHMARK.value and ds.benchmark_priority in ["P0", "P1"]]

        if not eligible:
            return None

        resolved = ReferenceDataResolver.resolve_metric_reference(
            datasets=eligible,
            metric_name=metric_name,
            stroke=stroke,
            athlete_age=age,
            athlete_sex=sex
        )
        return resolved.reference_metric

    def validate_record(self, dataset: ReferenceDataset):
        """Runs 8 Scientific Integrity Rules validation on dataset."""
        return ReferenceDataValidator.validate_dataset(dataset)

    def create_record(self, principal, dataset: ReferenceDataset, user: str = "Coach/Admin") -> bool:
        """Validates and saves a new dataset record."""
        if not principal or getattr(principal, "role", "coach") != "admin":
            raise PermissionError("Global write access denied. Administrator privileges required.")
        return self._repo.save_dataset(dataset, user=user)

    def update_record(self, principal, dataset: ReferenceDataset, user: str = "Coach/Admin") -> bool:
        """Updates an existing dataset record."""
        if not principal or getattr(principal, "role", "coach") != "admin":
            raise PermissionError("Global write access denied. Administrator privileges required.")
        return self._repo.save_dataset(dataset, user=user)

    def delete_record(self, principal, dataset_id: str, confirm: bool = False, user: str = "Coach/Admin") -> bool:
        """Deletes a dataset record ONLY when confirm=True."""
        if not principal or getattr(principal, "role", "coach") != "admin":
            raise PermissionError("Global write access denied. Administrator privileges required.")
        if not confirm:
            raise ValueError("Deletion requires explicit confirmation (confirm=True).")
        return self._repo.delete_dataset(dataset_id, user=user)

    def get_dataset_versions(self) -> List[ReferenceDatasetVersion]:
        """Fetch list of all imported dataset versions."""
        return self._repo.get_dataset_versions()

    def activate_dataset_version(self, principal, version_name: str) -> bool:
        """Activates a dataset version."""
        if not principal or getattr(principal, "role", "coach") != "admin":
            raise PermissionError("Global write access denied. Administrator privileges required.")
        return self._repo.set_version_active(version_name, is_active=True)

    def deactivate_dataset_version(self, principal, version_name: str) -> bool:
        """Deactivates a dataset version."""
        if not principal or getattr(principal, "role", "coach") != "admin":
            raise PermissionError("Global write access denied. Administrator privileges required.")
        return self._repo.set_version_active(version_name, is_active=False)

    def export_csv(self, stroke: Optional[str] = None, eligible_only: bool = False) -> str:
        """Exports dataset records to CSV string."""
        datasets = self.get_records(stroke=stroke)
        if eligible_only:
            datasets = [d for d in datasets if d.benchmark_eligibility == "BENCHMARK"]
        return ReferenceExportService.export_to_csv(datasets)
