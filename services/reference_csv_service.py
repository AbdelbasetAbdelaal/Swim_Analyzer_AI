"""
CSV Import & Validation Preview Service for Reference Data Manager.
Parses CSV files, validates rows against scientific integrity rules,
previews errors/warnings, generates sample & normalized CSV templates, and imports validated rows.
"""

import io
import csv
from typing import List, Dict, Any
from models.reference_data_models import (
    ReferenceDataset, ReferenceMetric, ReferenceSource,
    ReferenceBenchmarkEligibility
)
from services.reference_csv_normalizer import ReferenceCSVNormalizer, NormalizedCSVRow

class CSVRowValidationResult:
    def __init__(self, row_index: int, norm_row: NormalizedCSVRow):
        self.row_index = row_index
        self.raw_data = norm_row.raw_data
        self.is_valid: bool = norm_row.is_valid
        self.errors: List[str] = list(norm_row.errors)
        self.warnings: List[str] = list(norm_row.warnings)
        
        # Dataset & Metric Metadata
        self.dataset_name: str = norm_row.dataset_name
        self.stroke: str = norm_row.stroke
        self.metric_name: str = norm_row.metric_name
        self.canonical_identity: str = norm_row.canonical_identity
        
        # Transformation Stages
        self.raw_csv_row: Dict[str, str] = norm_row.raw_data
        self.normalized_dataset: Dict[str, Any] = {
            "name": norm_row.dataset_name,
            "stroke": norm_row.stroke,
            "event_distance": norm_row.event_distance,
            "course": norm_row.course,
            "sex": norm_row.sex,
            "age_range": f"[{norm_row.age_min}–{norm_row.age_max}]",
            "cohort": norm_row.cohort,
            "skill_level": norm_row.skill_level,
            "source_type": norm_row.source_type,
            "doi": norm_row.doi,
            "pmid": norm_row.pmid
        }
        self.normalized_metric: Dict[str, Any] = {
            "metric_name": norm_row.metric_name,
            "display_name": norm_row.display_name,
            "value_typical": norm_row.value_typical,
            "uncertainty_sd": norm_row.uncertainty_sd,
            "value_min": norm_row.value_min,
            "value_median": norm_row.value_median,
            "value_max": norm_row.value_max,
            "unit": norm_row.unit,
            "measurement_domain": norm_row.measurement_domain,
            "status": norm_row.status
        }
        self.validation_result: str = "PASSED" if norm_row.is_valid else "FAILED"
        self.benchmark_eligibility: str = norm_row.benchmark_eligibility
        self.norm_row: NormalizedCSVRow = norm_row

class CSVValidationPreview:
    def __init__(self):
        self.total_rows: int = 0
        self.valid_rows: int = 0
        self.invalid_rows: int = 0
        self.warnings_count: int = 0
        self.duplicate_rows: int = 0
        self.schema_errors: List[str] = []
        self.metadata_errors: List[str] = []
        self.metric_errors: List[str] = []
        self.duplicate_errors: List[str] = []
        self.provenance_warnings: List[str] = []
        self.eligibility_warnings: List[str] = []
        self.row_results: List[CSVRowValidationResult] = []

class ReferenceCSVService:
    EXPECTED_COLUMNS = [
        "record_type", "dataset_name", "stroke", "event_distance", "sex", "age_min", "age_max", "skill_level",
        "athlete_category", "metric_name", "unit", "value_min", "value_typical", "uncertainty_sd",
        "value_median", "value_max", "measurement_domain", "status", "benchmark_priority", "method",
        "source_type", "source_title", "authors", "publication_year", "doi", "pmid", "url", "sample_size",
        "population_description", "age_group", "course", "evidence_grade", "benchmark_eligibility",
        "population_match_required", "context_only_reason", "notes"
    ]

    @classmethod
    def generate_sample_csv_template(cls) -> str:
        """Returns CSV template string matching canonical columns with both METRIC and SOURCE examples."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(cls.EXPECTED_COLUMNS)
        # Sample 1: METRIC row
        writer.writerow([
            "METRIC", "EUROPEAN_FINALISTS_2021_MALE", "BUTTERFLY", "100m", "Male", "18", "35", "Elite",
            "Adult", "Start Time", "s", "", "5.53", "0.19", "", "", "CALIBRATED_PHYSICAL",
            "VALIDATED_REFERENCE", "P0", "Race video kinematic analysis", "PEER_REVIEWED_PRIMARY_STUDY",
            "Performance Development of European Swimmers", "Born DP et al.", "2022", "10.3389/fspor.2022.894066",
            "35755613", "", "24", "2021 European Championships finalists", "ADULT", "LCM", "A",
            "BENCHMARK", "sex + adult + elite", "", "Long-course pool mean ± SD"
        ])
        # Sample 2: SOURCE / PROVENANCE row (no metric_name required)
        writer.writerow([
            "SOURCE", "SOURCE_REGISTRY_BACKSTROKE_2025", "BACKSTROKE", "", "Mixed", "", "", "Elite",
            "Adult", "", "", "", "", "", "", "", "UNAVAILABLE",
            "CONTEXT_ONLY", "P2", "Systematic Literature Review", "PEER_REVIEWED_SYSTEMATIC_REVIEW",
            "Biomechanical and Anthropometric Characteristics of Backstroke Swimmers", "Smith et al.", "2025", "10.1016/j.jbiomech.2025.100999",
            "39123456", "https://doi.org/10.1016/j.jbiomech.2025.100999", "120", "Comprehensive meta-review of backstroke kinematics", "ADULT", "LCM", "B",
            "CONTEXT_ONLY", "", "Systematic review evidence for backstroke reference context", "Provenance registry record"
        ])
        return output.getvalue()

    @classmethod
    def parse_and_validate_csv(
        cls,
        csv_content: str,
        strict_scientific_mode: bool = True
    ) -> CSVValidationPreview:
        """Parses CSV content and applies deterministic normalization and validation pipeline."""
        preview = CSVValidationPreview()
        if csv_content.startswith("\ufeff"):
            csv_content = csv_content[1:]

        lines = csv_content.splitlines()
        if not lines:
            return preview

        first_line = lines[0].lower()
        is_policy_csv = "eligibility_class" in first_line or "eligibility_rule" in first_line

        reader = csv.DictReader(io.StringIO(csv_content))
        seen_identities = set()

        for idx, raw_row in enumerate(reader, start=1):
            preview.total_rows += 1

            if is_policy_csv:
                # Handle swimming_benchmark_eligibility_policy.csv
                elig_class = str(raw_row.get("eligibility_class", "")).strip().upper()
                rule = str(raw_row.get("eligibility_rule", "")).strip()
                allowed_use = str(raw_row.get("allowed_use", "")).strip()
                example = str(raw_row.get("example", "")).strip()

                norm_r = NormalizedCSVRow(idx, raw_row)
                norm_r.dataset_name = f"Policy Rule: {elig_class}"
                norm_r.stroke = "ALL"
                norm_r.metric_name = f"Rule: {elig_class}"
                norm_r.display_name = f"Rule: {elig_class}"
                norm_r.benchmark_eligibility = elig_class if elig_class in ReferenceBenchmarkEligibility.__members__ else "CONTEXT_ONLY"

                row_res = CSVRowValidationResult(idx, norm_r)
                valid_classes = ["PRIMARY_BENCHMARK", "CONTEXT_ONLY", "TEST_SPECIFIC", "AGE_LAYER_ONLY", "INSUFFICIENT_EVIDENCE"]
                if elig_class not in valid_classes:
                    row_res.is_valid = False
                    row_res.errors.append(f"Invalid eligibility_class '{elig_class}'.")
                    preview.metadata_errors.append(f"Row {idx}: Invalid eligibility_class '{elig_class}'.")
                else:
                    row_res.is_valid = True

                row_res.warnings.append(f"Eligibility Policy Rule parsed: {allowed_use}")
                preview.eligibility_warnings.append(f"Row {idx}: Policy Rule {elig_class} -> {allowed_use}")

                if row_res.is_valid:
                    preview.valid_rows += 1
                else:
                    preview.invalid_rows += 1

                preview.warnings_count += len(row_res.warnings)
                preview.row_results.append(row_res)
                continue

            # 1. Normalize Row via ReferenceCSVNormalizer
            norm_r = ReferenceCSVNormalizer.normalize_row(idx, raw_row)
            row_res = CSVRowValidationResult(idx, norm_r)

            # Categorize normalization errors
            if norm_r.errors:
                for err in norm_r.errors:
                    if "dataset_name" in err or "metric_name" in err:
                        preview.schema_errors.append(f"Row {idx}: {err}")
                    elif "Range Error" in err or "non-numeric" in err:
                        preview.metric_errors.append(f"Row {idx}: {err}")
                    else:
                        preview.metadata_errors.append(f"Row {idx}: {err}")

            # 2. Canonical Identity Duplicate Validation
            # Distinguishes 50m vs 100m vs 200m Butterfly cleanly!
            ident = norm_r.canonical_identity
            if ident in seen_identities:
                row_res.warnings.append(f"Duplicate metric identity: dataset '{norm_r.dataset_name}', stroke '{norm_r.stroke}', distance '{norm_r.event_distance}', metric '{norm_r.metric_name}'.")
                preview.duplicate_errors.append(f"Row {idx}: Duplicate identity '{ident}'")
                preview.duplicate_rows += 1
            else:
                seen_identities.add(ident)

            # 3. Scientific Provenance Warnings
            if norm_r.source_type == "PEER_REVIEWED_PRIMARY_STUDY" and not norm_r.doi and not norm_r.pmid and not norm_r.source_title:
                row_res.warnings.append("Peer-reviewed study record lacks explicit DOI, PMID, or citation title.")
                preview.provenance_warnings.append(f"Row {idx}: Incomplete citation for peer-reviewed record.")

            # 4. Strict Scientific Mode Policy Checks
            if strict_scientific_mode:
                if norm_r.source_type == "COACH_DEFINED" and norm_r.benchmark_eligibility == "BENCHMARK":
                    norm_r.benchmark_eligibility = "CONTEXT_ONLY"
                    row_res.benchmark_eligibility = "CONTEXT_ONLY"
                    row_res.warnings.append("Strict Scientific Mode: Coach-defined record reset to CONTEXT_ONLY eligibility.")
                    preview.eligibility_warnings.append(f"Row {idx}: Coach data restricted to CONTEXT_ONLY eligibility.")

            if row_res.is_valid:
                preview.valid_rows += 1
            else:
                preview.invalid_rows += 1

            if row_res.warnings:
                preview.warnings_count += len(row_res.warnings)

            preview.row_results.append(row_res)

        return preview

    @classmethod
    def generate_normalized_csv(cls, preview: CSVValidationPreview) -> str:
        """Generates canonical normalized CSV text matching EXPECTED_COLUMNS."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(cls.EXPECTED_COLUMNS)

        for r in preview.row_results:
            n = r.norm_row
            writer.writerow([
                n.record_type, n.dataset_name, n.stroke, n.event_distance, n.sex,
                n.age_min if n.age_min is not None else "",
                n.age_max if n.age_max is not None else "",
                n.skill_level, n.cohort, n.metric_name if n.record_type == "METRIC" else "", n.unit,
                n.value_min if n.value_min is not None else "",
                n.value_typical if n.value_typical is not None else "",
                n.uncertainty_sd if n.uncertainty_sd is not None else "",
                n.value_median if n.value_median is not None else "",
                n.value_max if n.value_max is not None else "",
                n.measurement_domain, n.status, n.benchmark_priority, n.method,
                n.source_type, n.source_title, n.authors,
                n.publication_year if n.publication_year is not None else "",
                n.doi, n.pmid, "", "", n.population_description,
                n.age_group, n.course, n.evidence_grade, n.benchmark_eligibility,
                n.population_match_required, n.context_only_reason, n.notes
            ])

        return output.getvalue()

    @classmethod
    def convert_csv_to_datasets(cls, preview: CSVValidationPreview) -> List[ReferenceDataset]:
        """Converts validated CSV rows into domain ReferenceDataset instances."""
        dataset_map: Dict[str, ReferenceDataset] = {}

        for r in preview.row_results:
            if not r.is_valid:
                continue

            n = r.norm_row
            ds_key = f"{n.dataset_name.lower()}_{n.stroke}"

            if ds_key not in dataset_map:
                ds = ReferenceDataset(
                    dataset_id=f"ds_{n.dataset_name.lower().replace(' ', '_')[:24]}",
                    name=n.dataset_name,
                    description=n.notes or n.population_description,
                    stroke=n.stroke,
                    age_min=n.age_min if n.age_min is not None else 0,
                    age_max=n.age_max if n.age_max is not None else 100,
                    sex=n.sex,
                    skill_level=n.skill_level,
                    athlete_category=n.cohort,
                    source_type=n.source_type,
                    evidence_status="AVAILABLE" if n.benchmark_eligibility == "BENCHMARK" else "INSUFFICIENT_EVIDENCE",
                    benchmark_eligibility=n.benchmark_eligibility,
                    benchmark_priority=n.benchmark_priority,
                    validation_status="VALIDATED_REFERENCE" if n.benchmark_eligibility == "BENCHMARK" else "DRAFT",
                    is_archived=False,
                    is_active=True
                )

                if n.source_title or n.authors or n.doi:
                    src = ReferenceSource(
                        source_type=n.source_type,
                        source_title=n.source_title,
                        authors=n.authors,
                        publication_year=n.publication_year,
                        doi=n.doi,
                        pmid=n.pmid,
                        population_description=n.population_description
                    )
                    ds.sources.append(src)

                dataset_map[ds_key] = ds

            if n.record_type == "METRIC":
                m = ReferenceMetric(
                    metric_name=n.metric_name,
                    display_name=n.display_name,
                    value_min=n.value_min,
                    value_typical=n.value_typical,
                    value_median=n.value_median,
                    value_max=n.value_max,
                    uncertainty_sd=n.uncertainty_sd,
                    unit=n.unit,
                    measurement_domain=n.measurement_domain,
                    status=n.status,
                    method=n.method,
                    notes=n.notes,
                    event_distance=n.event_distance,
                    course=n.course,
                    evidence_grade=n.evidence_grade,
                    context_only_reason=n.context_only_reason,
                    population_match_required=n.population_match_required
                )
                dataset_map[ds_key].metrics.append(m)

        return list(dataset_map.values())
