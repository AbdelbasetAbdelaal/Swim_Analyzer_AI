"""
Ground Truth Validation Runner.
Executes an immutable Swim Analyzer AI pipeline version against a standardized Ground Truth cohort manifest.
"""
from typing import List, Dict, Optional, Any, Tuple
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
import jsonschema

from core.logger import setup_logger
from core.config import config
from services.analysis_service import AnalysisService
from models.data_models import StrokeSelection, StrokeType
from .ground_truth_models import (
    GroundTruthManifest,
    GroundTruthSample,
    ManifestRecord,
    ValidationRunMetadata,
    ValidationCohortResult,
    InclusionStatus,
    AnnotationStatus,
    QualityStatus,
)
from .ground_truth_comparator import GroundTruthComparator
from .ground_truth_policy import ValidationStatus
from .data_leakage_validator import DataLeakageValidator
from .provenance_contract import ProvenanceValidator

logger = setup_logger(__name__)


def get_git_commit_sha() -> str:
    """Safely queries git for the current HEAD commit hash."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=5,
        )
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN_COMMIT_SHA"


class GroundTruthValidationRunner:
    """
    Orchestrates the scientific validation experiment.
    Loads manifest, enforces inclusion gates, executes analysis pipeline, pairs metrics,
    computes comparison statistics, and outputs a reproducible evaluation report.
    """

    def __init__(
        self,
        schema_path: Optional[Path] = None,
        manifest_schema_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ):
        self.repo_root = Path(__file__).resolve().parent.parent.parent
        self.schema_path = schema_path or (self.repo_root / "schemas" / "ground_truth_schema.json")
        self.manifest_schema_path = manifest_schema_path or (self.repo_root / "schemas" / "ground_truth_manifest_schema.json")
        self.output_dir = output_dir or (self.repo_root / "data" / "ground_truth" / "validation_runs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._load_schemas()

    def _load_schemas(self):
        with open(self.schema_path, "r", encoding="utf-8") as f:
            self.gt_schema = json.load(f)
        with open(self.manifest_schema_path, "r", encoding="utf-8") as f:
            self.manifest_schema = json.load(f)

    def validate_manifest_schema(self, manifest_dict: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Verifies manifest against schemas/ground_truth_manifest_schema.json."""
        try:
            jsonschema.validate(instance=manifest_dict, schema=self.manifest_schema)
            return True, None
        except jsonschema.ValidationError as e:
            return False, f"Manifest schema violation at '{'.'.join([str(p) for p in e.path])}': {e.message}"

    def validate_sample_schema(self, sample_dict: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Verifies sample against schemas/ground_truth_schema.json and provenance contracts."""
        try:
            jsonschema.validate(instance=sample_dict, schema=self.gt_schema)
        except jsonschema.ValidationError as e:
            return False, f"Sample schema violation at '{'.'.join([str(p) for p in e.path])}': {e.message}"

        # Provenance contract validation
        prov_valid, prov_errs = ProvenanceValidator.validate_sample_metrics(sample_dict)
        if not prov_valid:
            return False, f"Provenance contract violation: {'; '.join(prov_errs)}"

        return True, None

    def load_manifest(self, manifest_path: Path) -> GroundTruthManifest:
        """Loads and schema-validates a manifest file."""
        with open(manifest_path, "r", encoding="utf-8") as f:
            raw_manifest = json.load(f)

        is_valid, err = self.validate_manifest_schema(raw_manifest)
        if not is_valid:
            raise ValueError(f"Invalid Ground Truth manifest ({manifest_path}): {err}")

        return GroundTruthManifest.from_dict(raw_manifest)

    def load_and_validate_sample(self, sample_path: Path) -> GroundTruthSample:
        """Loads and schema-validates an individual Ground Truth sample file."""
        with open(sample_path, "r", encoding="utf-8") as f:
            raw_sample = json.load(f)

        is_valid, err = self.validate_sample_schema(raw_sample)
        if not is_valid:
            raise ValueError(f"Invalid Ground Truth sample ({sample_path}): {err}")

        return GroundTruthSample.from_dict(raw_sample)

    def run_validation_experiment(
        self,
        manifest_path: Path,
        allow_synthetic: bool = False,
        analysis_service_override: Optional[Any] = None,
    ) -> ValidationCohortResult:
        """
        Executes the validation experiment against the specified manifest.
        
        Args:
            manifest_path: Path to ground_truth_manifest.json.
            allow_synthetic: If True, allows running synthetic test fixtures.
            analysis_service_override: Optional custom analysis callable or mock for testing.
        """
        manifest = self.load_manifest(manifest_path)
        warnings: List[str] = []

        # Synthetic fixture gating
        if manifest.is_synthetic_manifest and not allow_synthetic:
            raise ValueError(
                "SYNTHETIC FIXTURE ISOLATION GATE: Manifest is marked as synthetic. "
                "Synthetic fixtures cannot be used for official scientific validation."
            )

        # Data leakage check
        is_leak_free, leak_errors = DataLeakageValidator.validate_manifest_splits(
            [r.to_dict() for r in manifest.records]
        )
        if not is_leak_free:
            raise ValueError(f"Data leakage detected in manifest:\n" + "\n".join(leak_errors))

        # Eligibility filtering
        total_records = len(manifest.records)
        eligible_records: List[ManifestRecord] = []
        excluded_records_count = 0
        ambiguous_records_count = 0

        for r in manifest.records:
            if r.inclusion_status == InclusionStatus.EXCLUDED.value:
                excluded_records_count += 1
            elif r.inclusion_status == InclusionStatus.AMBIGUOUS.value:
                ambiguous_records_count += 1
            elif r.annotation_status != AnnotationStatus.COMPLETE.value:
                warnings.append(f"Sample {r.sample_id} excluded: Incomplete annotation ({r.annotation_status}).")
                excluded_records_count += 1
            elif r.quality_status == QualityStatus.FAILED.value:
                warnings.append(f"Sample {r.sample_id} excluded: Failed quality control.")
                excluded_records_count += 1
            else:
                eligible_records.append(r)

        # Build run metadata
        now_utc = datetime.now(timezone.utc)
        metadata = ValidationRunMetadata(
            run_id=f"VAL-RUN-{now_utc.strftime('%Y%m%d-%H%M%S')}",
            git_commit_sha=get_git_commit_sha(),
            protocol_version=manifest.protocol_version,
            schema_version="1.0.0",
            config_version="PRODUCTION",
            app_version="SwimAnalyzer-1.0.0",
            run_timestamp=now_utc.isoformat(),
            is_synthetic_run=manifest.is_synthetic_manifest,
        )

        ai_extracted_results: List[Dict[str, Any]] = []
        gt_extracted_samples: List[Dict[str, Any]] = []

        analysis_service = analysis_service_override or AnalysisService()

        # Execute AI analysis for each eligible record
        for record in eligible_records:
            sample_file_path = Path(record.annotation_file)
            if not sample_file_path.is_absolute():
                sample_file_path = self.repo_root / sample_file_path

            if not sample_file_path.exists():
                warnings.append(f"Annotation file not found for sample {record.sample_id}: {sample_file_path}")
                continue

            sample = self.load_and_validate_sample(sample_file_path)

            if sample.is_synthetic_fixture and not allow_synthetic:
                warnings.append(f"Skipping synthetic sample {sample.sample_id} in official run.")
                continue

            # Run production analysis pipeline
            video_file_path = Path(record.video_path)
            if not video_file_path.is_absolute():
                video_file_path = self.repo_root / video_file_path

            ai_metrics: Dict[str, Any] = {}
            if video_file_path.exists() or analysis_service_override is not None:
                try:
                    stroke_type_enum = StrokeType(record.stroke)
                except Exception:
                    stroke_type_enum = StrokeType.FREESTYLE

                stroke_selection = StrokeSelection(
                    selected_stroke=stroke_type_enum,
                    selection_source="USER"
                )

                try:
                    if callable(analysis_service):
                        ai_metrics = analysis_service(str(video_file_path), stroke_selection)
                    else:
                        _, _, _, analysis_result = analysis_service.analyze_video(
                            input_video_path=str(video_file_path),
                            stroke_detection=stroke_selection
                        )
                        # Extract metrics from analysis_result
                        if analysis_result:
                            if analysis_result.stroke_metrics:
                                for k, v in analysis_result.stroke_metrics.items():
                                    val = getattr(v, "value", v)
                                    ai_metrics[k] = val
                            if analysis_result.report and analysis_result.report.metrics:
                                for k, v in analysis_result.report.metrics.items():
                                    val = getattr(v, "value", v)
                                    ai_metrics[k] = val
                except Exception as e:
                    warnings.append(f"Error running pipeline on {record.sample_id}: {e}")
                    ai_metrics = {}
            else:
                warnings.append(f"Video file missing for {record.sample_id}: {video_file_path}")

            ai_extracted_results.append(ai_metrics)
            gt_extracted_samples.append(sample.to_dict())

        # Compare using GroundTruthComparator
        metric_comparisons = GroundTruthComparator.compare_cohort(
            ai_results=ai_extracted_results,
            gt_samples=gt_extracted_samples,
        )

        overall_status = ValidationStatus.NOT_VALIDATED_INSUFFICIENT_GROUND_TRUTH.value
        if manifest.is_synthetic_manifest:
            overall_status = "TEST FIXTURE — NOT SCIENTIFIC GROUND TRUTH"
        elif len(eligible_records) == 0:
            overall_status = ValidationStatus.NOT_VALIDATED_INSUFFICIENT_GROUND_TRUTH.value

        result = ValidationCohortResult(
            metadata=metadata,
            overall_status=overall_status,
            cohort_name=manifest.cohort_name,
            total_manifest_records=total_records,
            eligible_records_count=len(eligible_records),
            excluded_records_count=excluded_records_count,
            ambiguous_records_count=ambiguous_records_count,
            metric_comparisons=metric_comparisons,
            warnings=warnings,
        )

        # Save machine-readable run report
        report_path = self.output_dir / f"{metadata.run_id}_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2)

        return result
