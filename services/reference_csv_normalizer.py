"""
Deterministic Schema Normalizer for Reference Data CSV Pipeline.
Normalizes raw CSV rows into canonical dataset-level and metric-level records,
applies explicit source_type mappings, constructs canonical metric identity keys,
and preserves missing scientific values as None/null.
"""

from typing import Dict, Optional, List
from models.reference_data_models import (
    CANONICAL_SOURCE_TYPE_MAPPING
)

class NormalizedCSVRow:
    def __init__(self, row_index: int, raw_data: Dict[str, str]):
        self.row_index = row_index
        self.raw_data = raw_data
        
        # Dataset-level metadata fields
        self.record_type: str = "METRIC"
        self.dataset_name: str = ""
        self.stroke: str = "FREESTYLE"
        self.event_distance: str = ""
        self.course: str = ""
        self.sex: str = "Mixed"
        self.age_min: Optional[int] = None
        self.age_max: Optional[int] = None
        self.age_group: str = ""
        self.skill_level: str = "Unknown"
        self.cohort: str = "Adult"
        self.source_type: str = "IMPORTED_REFERENCE"
        self.raw_source_type: str = ""
        self.source_title: str = ""
        self.authors: str = ""
        self.publication_year: Optional[int] = None
        self.doi: str = ""
        self.pmid: str = ""
        self.population_description: str = ""
        
        # Metric-level fields
        self.metric_name: str = ""
        self.display_name: str = ""
        self.unit: str = ""
        self.value_typical: Optional[float] = None
        self.uncertainty_sd: Optional[float] = None
        self.value_min: Optional[float] = None
        self.value_median: Optional[float] = None
        self.value_max: Optional[float] = None
        self.measurement_domain: str = "CALIBRATED_PHYSICAL"
        self.status: str = "available"
        self.benchmark_priority: str = "P2"
        self.benchmark_eligibility: str = "CONTEXT_ONLY"
        self.method: str = ""
        self.notes: str = ""
        self.evidence_grade: str = ""
        self.context_only_reason: str = ""
        self.population_match_required: str = ""
        
        # Validation & Identity flags
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.canonical_identity: str = ""

class ReferenceCSVNormalizer:
    """
    Normalizes raw CSV rows into standardized dataset & metric models.
    """

    @classmethod
    def normalize_row(
        cls,
        row_index: int,
        raw_row: Dict[str, str],
        dataset_metadata_context: Optional[Dict[str, str]] = None
    ) -> NormalizedCSVRow:
        """Applies deterministic normalization pipeline on a single raw CSV row."""
        # 1. Clean dict keys (strip BOM, quotes, whitespace, lowercase)
        norm_dict = {}
        for k, v in raw_row.items():
            if k is not None:
                clean_k = str(k).strip('\ufeff "\'\t\r\n').lower().strip()
                clean_v = str(v).strip() if v is not None else ""
                norm_dict[clean_k] = clean_v

        row_res = NormalizedCSVRow(row_index, raw_dict_data(norm_dict))

        # Helper for parsing optional float without silent fallbacks
        def parse_optional_float(key_name: str) -> Optional[float]:
            val_str = norm_dict.get(key_name, "")
            if not val_str or val_str.lower() in ["none", "null", "n/a", "nan", ""]:
                return None
            try:
                return float(val_str)
            except ValueError:
                row_res.is_valid = False
                row_res.errors.append(f"Field '{key_name}' contains invalid non-numeric string '{val_str}'.")
                return None

        # Helper for parsing optional int
        def parse_optional_int(key_name: str) -> Optional[int]:
            val_str = norm_dict.get(key_name, "")
            if not val_str or val_str.lower() in ["none", "null", "n/a", "nan", ""]:
                return None
            try:
                return int(float(val_str))
            except ValueError:
                row_res.is_valid = False
                row_res.errors.append(f"Field '{key_name}' contains invalid integer string '{val_str}'.")
                return None

        # 2. Extract & Normalize Dataset Name
        ds_name = norm_dict.get("dataset_name") or norm_dict.get("dataset") or norm_dict.get("dataset_title")
        if not ds_name and dataset_metadata_context:
            ds_name = dataset_metadata_context.get("dataset_name") or dataset_metadata_context.get("dataset_title")

        if not ds_name:
            # Check source_title or population_description as fallback if deterministically available
            ds_name = norm_dict.get("source_title") or norm_dict.get("population_description")

        if not ds_name:
            row_res.is_valid = False
            row_res.errors.append("Missing required field 'dataset_name'.")
            ds_name = "UNNAMED_DATASET"

        row_res.dataset_name = ds_name

        # 3. Extract & Normalize Stroke
        raw_stroke = norm_dict.get("stroke", "FREESTYLE").upper()
        if raw_stroke in ["FREESTYLE", "FRONT CRAWL", "CRAWL"]:
            row_res.stroke = "FREESTYLE"
        elif raw_stroke in ["BACKSTROKE", "BACK CRAWL"]:
            row_res.stroke = "BACKSTROKE"
        elif raw_stroke in ["BREASTSTROKE"]:
            row_res.stroke = "BREASTSTROKE"
        elif raw_stroke in ["BUTTERFLY", "FLY"]:
            row_res.stroke = "BUTTERFLY"
        elif raw_stroke in ["ALL", "ALL_FOUR", "COMBINED"]:
            row_res.stroke = "ALL"
        else:
            row_res.stroke = raw_stroke

        # 4. Extract Event Distance & Course Context
        row_res.event_distance = norm_dict.get("event_distance", "")
        row_res.course = norm_dict.get("course", "").upper()

        # 5. Extract Demographics & Cohort Context
        row_res.sex = norm_dict.get("sex", "Mixed") or "Mixed"
        row_res.age_min = parse_optional_int("age_min")
        row_res.age_max = parse_optional_int("age_max")
        row_res.age_group = norm_dict.get("age_group", "").upper()
        row_res.skill_level = norm_dict.get("skill_level") or norm_dict.get("population_level") or "Unknown"
        row_res.cohort = norm_dict.get("athlete_category") or norm_dict.get("cohort") or norm_dict.get("age_group") or "Adult"

        # Safe default bounds if age_min/age_max empty
        if row_res.age_min is None:
            row_res.age_min = 18 if row_res.age_group == "ADULT" else 0
        if row_res.age_max is None:
            row_res.age_max = 35 if row_res.age_group == "ADULT" else 100

        # 6. Extract Source Type & Explicit Mapping
        raw_st = norm_dict.get("source_type", "IMPORTED_REFERENCE").upper()
        row_res.raw_source_type = raw_st
        if raw_st in CANONICAL_SOURCE_TYPE_MAPPING:
            row_res.source_type = CANONICAL_SOURCE_TYPE_MAPPING[raw_st]
        else:
            row_res.source_type = "IMPORTED_REFERENCE"
            row_res.warnings.append(f"Unrecognized source_type '{raw_st}'. Mapped strictly to IMPORTED_REFERENCE.")

        # 7. Extract Provenance Details
        row_res.source_title = norm_dict.get("source_title", "")
        row_res.authors = norm_dict.get("authors", "")
        row_res.publication_year = parse_optional_int("publication_year")
        row_res.doi = norm_dict.get("doi", "")
        row_res.pmid = norm_dict.get("pmid", "")
        row_res.population_description = norm_dict.get("population_description", "")

        # Record Type Detection
        raw_rec_type = norm_dict.get("record_type", "").upper()
        if raw_rec_type in ["SOURCE", "PROVENANCE", "CONTEXT", "SOURCE_REGISTRY"]:
            record_type = "SOURCE"
        elif raw_rec_type in ["METRIC", "OBSERVATION", "MEASUREMENT"]:
            record_type = "METRIC"
        else:
            # Infer record_type if unpopulated
            ds_name_upper = (norm_dict.get("dataset_name") or norm_dict.get("dataset") or "").upper()
            st_upper = (norm_dict.get("source_type") or "").upper()
            m_name = norm_dict.get("metric_name") or norm_dict.get("metric") or ""

            if ds_name_upper.startswith("SOURCE_REGISTRY_") or st_upper in ["SOURCE_REGISTRY", "SCIENTIFIC_POLICY"] or (not m_name and (norm_dict.get("source_title") or norm_dict.get("doi") or norm_dict.get("population_description"))):
                record_type = "SOURCE"
            else:
                record_type = "METRIC"

        row_res.record_type = record_type

        # 8. Metric / Source Validation by Record Type
        if record_type == "SOURCE":
            # SOURCE records do NOT require metric_name or metric values!
            row_res.metric_name = norm_dict.get("metric_name") or norm_dict.get("metric") or f"Provenance Record: {row_res.dataset_name}"
            row_res.display_name = f"Source Provenance ({row_res.dataset_name})"
            row_res.status = "CONTEXT_ONLY"
            row_res.benchmark_eligibility = "CONTEXT_ONLY"
            row_res.benchmark_priority = "P2"
            row_res.warnings.append("Source/provenance record — no metric_name required.")
        else:
            # METRIC records REQUIRE metric_name
            row_res.metric_name = norm_dict.get("metric_name") or norm_dict.get("metric") or ""
            if not row_res.metric_name:
                row_res.is_valid = False
                row_res.errors.append("Missing required field 'metric_name'.")

            row_res.display_name = row_res.metric_name.replace("_", " ").title()
            row_res.unit = norm_dict.get("unit", "")
            row_res.value_typical = parse_optional_float("value_typical")
            row_res.uncertainty_sd = parse_optional_float("uncertainty_sd")
            row_res.value_min = parse_optional_float("value_min")
            row_res.value_median = parse_optional_float("value_median")
            row_res.value_max = parse_optional_float("value_max")

            # Range Order Validation for METRIC records
            if row_res.value_min is not None and row_res.value_max is not None and row_res.value_min > row_res.value_max:
                row_res.is_valid = False
                row_res.errors.append(f"Range Error: value_min ({row_res.value_min}) > value_max ({row_res.value_max}).")

            if row_res.value_min is not None and row_res.value_typical is not None and row_res.value_min > row_res.value_typical:
                row_res.is_valid = False
                row_res.errors.append(f"Range Error: value_min ({row_res.value_min}) > value_typical ({row_res.value_typical}).")

            if row_res.value_typical is not None and row_res.value_max is not None and row_res.value_typical > row_res.value_max:
                row_res.is_valid = False
                row_res.errors.append(f"Range Error: value_typical ({row_res.value_typical}) > value_max ({row_res.value_max}).")

            # Benchmark Priority & Eligibility for METRIC records
            raw_elig = norm_dict.get("benchmark_eligibility", "CONTEXT_ONLY").upper()
            if raw_elig in ["BENCHMARK", "PRIMARY_BENCHMARK"]:
                row_res.benchmark_eligibility = "BENCHMARK"
            elif raw_elig in ["CONTEXT_ONLY", "TEST_SPECIFIC", "AGE_LAYER_ONLY"]:
                row_res.benchmark_eligibility = "CONTEXT_ONLY"
            else:
                row_res.benchmark_eligibility = "INSUFFICIENT_EVIDENCE"

            raw_prio = norm_dict.get("benchmark_priority", "P2").upper()
            if raw_prio in ["PRIMARY_BENCHMARK", "P0", "0"]:
                row_res.benchmark_priority = "P0"
            elif raw_prio in ["SUPPORTING_BENCHMARK", "P1", "1"]:
                row_res.benchmark_priority = "P1"
            elif raw_prio in ["CONTEXT_ONLY", "P2", "2"]:
                row_res.benchmark_priority = "P2"
            else:
                row_res.benchmark_priority = "P3"

        # Measurement Domain
        raw_dom = norm_dict.get("measurement_domain", "CALIBRATED_PHYSICAL").upper()
        row_res.measurement_domain = raw_dom if raw_dom in ["CALIBRATED_PHYSICAL", "RELATIVE_BODY_NORMALIZED", "POSE_RELATIVE_3D", "IMAGE_SPACE", "UNAVAILABLE"] else "CALIBRATED_PHYSICAL"

        # Method & Notes
        row_res.method = norm_dict.get("method", "")
        row_res.notes = norm_dict.get("notes", "")
        row_res.evidence_grade = norm_dict.get("evidence_grade", "")
        row_res.context_only_reason = norm_dict.get("context_only_reason", "")
        row_res.population_match_required = norm_dict.get("population_match_required", "")

        # 9. Construct Canonical Identity (Key for Duplicate Detection)
        if record_type == "SOURCE":
            row_res.canonical_identity = (
                f"SOURCE|"
                f"{row_res.dataset_name.lower().strip()}|"
                f"{row_res.stroke.upper()}|"
                f"{row_res.source_title.lower().strip()}|"
                f"{row_res.doi.lower().strip()}"
            )
        else:
            row_res.canonical_identity = (
                f"METRIC|"
                f"{row_res.dataset_name.lower().strip()}|"
                f"{row_res.stroke.upper()}|"
                f"{row_res.event_distance.lower().strip()}|"
                f"{row_res.course.upper().strip()}|"
                f"{row_res.cohort.lower().strip()}|"
                f"{row_res.sex.lower().strip()}|"
                f"{row_res.metric_name.lower().strip()}|"
                f"{row_res.unit.lower().strip()}|"
                f"{row_res.measurement_domain.upper()}"
            )

        return row_res

def raw_dict_data(d: Dict[str, str]) -> Dict[str, str]:
    return d
