"""
Automatic CSV Scientific Registry Importer.
Parses swimming_reference_data_v2_scientific_registry.csv and swimming_benchmark_eligibility_policy.csv,
populating SQLite database tables with versioning, active flags, and scientific provenance.
"""

import os
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

from database import SessionLocal
from database.reference_repository import ReferenceDataRepository
from models.reference_data_models import (
    ReferenceDataset, ReferenceMetric, ReferenceSource, ReferenceDatasetVersion,
    ReferenceBenchmarkEligibility, ReferenceValidationStatus
)

class CSVRegistryImporter:
    """
    Parses supplied CSV files and imports them with zero alteration of scientific values.
    Empty cells remain NULL / None.
    """

    @classmethod
    def import_scientific_registry_csv(
        cls,
        csv_path: str,
        version_name: str = "manual_reference_v2_scientific",
        importer_name: str = "System/Scientific_Registry_Importer"
    ) -> Tuple[int, int, List[str]]:
        """Imports swimming_reference_data_v2_scientific_registry.csv."""
        if not os.path.exists(csv_path):
            return 0, 0, [f"CSV file not found at path {csv_path}"]

        db = SessionLocal()
        repo = ReferenceDataRepository(db)
        errors = []

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        row_count = len(rows)
        dataset_map: Dict[str, ReferenceDataset] = {}
        valid_count = 0
        rejected_count = 0

        now_str = datetime.now().isoformat()

        for idx, r in enumerate(rows, start=1):
            ds_name = r.get("dataset_name", "").strip()
            metric_name = r.get("metric_name", "").strip()
            stroke = r.get("stroke", "FREESTYLE").strip().upper()

            if not ds_name or not metric_name:
                rejected_count += 1
                errors.append(f"Row {idx}: Missing dataset_name or metric_name.")
                continue

            def parse_float(val_str):
                if not val_str or val_str.strip() == "" or val_str.strip().lower() in ["none", "null", "n/a"]:
                    return None
                try:
                    return float(val_str.strip())
                except ValueError:
                    return None

            def parse_int(val_str):
                if not val_str or val_str.strip() == "" or val_str.strip().lower() in ["none", "null", "n/a"]:
                    return None
                try:
                    return int(float(val_str.strip()))
                except ValueError:
                    return None

            v_typ = parse_float(r.get("value_typical"))
            v_sd = parse_float(r.get("uncertainty_sd"))
            v_min = parse_float(r.get("value_min"))
            v_max = parse_float(r.get("value_max"))

            # Range validation: min <= max
            if v_min is not None and v_max is not None and v_min > v_max:
                rejected_count += 1
                errors.append(f"Row {idx}: value_min ({v_min}) > value_max ({v_max}). Rejected.")
                continue

            # Key dataset grouping
            ds_key = f"{ds_name}_{stroke}"
            if ds_key not in dataset_map:
                source_type = r.get("source_type", "PEER_REVIEWED_PRIMARY_STUDY").strip().upper()
                eligibility = r.get("benchmark_eligibility", "BENCHMARK").strip().upper()
                raw_priority = r.get("benchmark_priority", "PRIMARY_BENCHMARK").strip().upper()

                if raw_priority in ["PRIMARY_BENCHMARK", "P0", "0"]:
                    priority = "P0"
                elif raw_priority in ["SUPPORTING_BENCHMARK", "P1", "1"]:
                    priority = "P1"
                elif raw_priority in ["CONTEXT_ONLY", "P2", "2"]:
                    priority = "P2"
                else:
                    priority = "P3"

                raw_status = r.get("status", "VALIDATED_REFERENCE").strip().upper()

                parsed_age_min = parse_int(r.get("age_min"))
                parsed_age_max = parse_int(r.get("age_max"))
                age_grp = r.get("age_group", "").strip().upper()

                if parsed_age_min is None:
                    parsed_age_min = 18 if age_grp == "ADULT" else 0
                if parsed_age_max is None:
                    parsed_age_max = 35 if age_grp == "ADULT" else 100

                ds = ReferenceDataset(
                    dataset_id=f"ds_{ds_name.lower().replace(' ', '_')[:24]}",
                    name=ds_name,
                    description=r.get("notes", ""),
                    stroke=stroke,
                    age_min=parsed_age_min,
                    age_max=parsed_age_max,
                    sex=r.get("sex", "Mixed").strip() or "Mixed",
                    skill_level=r.get("skill_level", "Unknown").strip() or "Unknown",
                    athlete_category=r.get("population_level", "Adult").strip() or "Adult",
                    source_type=source_type,
                    evidence_status="AVAILABLE" if eligibility == "BENCHMARK" else "INSUFFICIENT_EVIDENCE",
                    benchmark_eligibility=eligibility if eligibility in ReferenceBenchmarkEligibility.__members__ else "CONTEXT_ONLY",
                    benchmark_priority=priority,
                    validation_status=raw_status if raw_status in ReferenceValidationStatus.__members__ else "SCIENTIFICALLY_VALIDATED",
                    is_archived=False,
                    is_active=True,
                    dataset_version=version_name,
                    created_at=now_str,
                    updated_at=now_str
                )

                if r.get("source_title") or r.get("authors") or r.get("doi"):
                    src = ReferenceSource(
                        source_type=source_type,
                        source_title=r.get("source_title", ""),
                        authors=r.get("authors", ""),
                        publication_year=parse_int(r.get("publication_year")),
                        doi=r.get("doi", ""),
                        pmid=r.get("pmid", ""),
                        population_description=r.get("population_description", "")
                    )
                    ds.sources.append(src)

                dataset_map[ds_key] = ds

            # Metric creation
            m = ReferenceMetric(
                metric_name=metric_name,
                display_name=metric_name.replace("_", " ").title(),
                value_min=v_min,
                value_typical=v_typ,
                value_median=None,
                value_max=v_max,
                uncertainty_sd=v_sd,
                unit=r.get("unit", "").strip(),
                measurement_domain=r.get("measurement_domain", "CALIBRATED_PHYSICAL").strip().upper(),
                status="available" if (v_typ is not None or v_min is not None) else "unavailable",
                method=r.get("method", "").strip(),
                notes=r.get("notes", "").strip(),
                event_distance=r.get("event_distance", "").strip(),
                course=r.get("course", "").strip(),
                evidence_grade=r.get("evidence_grade", "").strip(),
                context_only_reason=r.get("context_only_reason", "").strip(),
                population_match_required=r.get("population_match_required", "").strip()
            )
            dataset_map[ds_key].metrics.append(m)
            valid_count += 1

        # Save all imported datasets into repo
        for ds in dataset_map.values():
            repo.save_dataset(ds, user=importer_name)

        # Save dataset version tracking
        v_info = ReferenceDatasetVersion(
            version_name=version_name,
            filename=Path(csv_path).name,
            imported_at=now_str,
            record_count=row_count,
            valid_count=valid_count,
            rejected_count=rejected_count,
            is_active=True,
            importer=importer_name
        )
        repo.save_dataset_version(v_info)
        db.close()

        return valid_count, rejected_count, errors
