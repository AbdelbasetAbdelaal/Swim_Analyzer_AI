"""
Ground Truth Ingestion & Registration Service.
Provides a strict, safe utility for validating and registering physical Ground Truth trials into manifests.
Enforces that no unverified, incomplete, or synthetic samples enter official validation cohorts.
"""
from typing import Dict, List, Optional, Any, Tuple
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

from core.logger import setup_logger
from .ground_truth_models import (
    GroundTruthSample,
    GroundTruthManifest,
    ManifestRecord,
    InclusionStatus,
    AnnotationStatus,
    QualityStatus,
)
from .ground_truth_runner import GroundTruthValidationRunner
from .provenance_contract import ProvenanceValidator

logger = setup_logger(__name__)


def compute_file_sha256(file_path: Path) -> str:
    """Computes SHA-256 hash of a file using buffered streaming."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class GroundTruthIngestionService:
    """
    Ingests and registers new Ground Truth trial candidates into a manifest.
    Guarantees that files exist, checksums match, schemas pass, and provenance contracts hold.
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        runner: Optional[GroundTruthValidationRunner] = None,
    ):
        self.repo_root = repo_root or Path(__file__).resolve().parent.parent.parent
        self.runner = runner or GroundTruthValidationRunner()

    def register_trial(
        self,
        manifest_path: Path,
        video_path: Path,
        annotation_path: Path,
        split: str = "VALIDATION_OFFICIAL",
        allow_synthetic: bool = False,
        save: bool = True,
    ) -> Tuple[bool, Optional[ManifestRecord], List[str]]:
        """
        Validates a candidate trial asset and registers it into the target manifest.
        
        Returns:
            (success: bool, record: Optional[ManifestRecord], errors: List[str])
        """
        errors: List[str] = []

        # 1. Resolve paths
        v_path = video_path if video_path.is_absolute() else self.repo_root / video_path
        a_path = annotation_path if annotation_path.is_absolute() else self.repo_root / annotation_path
        m_path = manifest_path if manifest_path.is_absolute() else self.repo_root / manifest_path

        # 2. Check physical raw video file existence
        if not v_path.exists() or not v_path.is_file():
            errors.append(
                f"PHYSICAL ASSET ERROR: Target raw video file does not exist locally: {v_path}. "
                "Unverified trials without real local video files cannot enter the validation cohort."
            )
            return False, None, errors

        # 3. Check annotation file existence
        if not a_path.exists() or not a_path.is_file():
            errors.append(f"Annotation file does not exist: {a_path}")
            return False, None, errors

        # 4. Check manifest existence
        if not m_path.exists() or not m_path.is_file():
            errors.append(f"Manifest file does not exist: {m_path}")
            return False, None, errors

        # 5. Load and validate annotation schema & provenance
        try:
            with open(a_path, "r", encoding="utf-8") as f:
                raw_sample = json.load(f)
        except Exception as e:
            errors.append(f"Failed to parse annotation JSON ({a_path}): {e}")
            return False, None, errors

        is_schema_valid, schema_err = self.runner.validate_sample_schema(raw_sample)
        if not is_schema_valid:
            errors.append(f"Sample schema/provenance validation failed: {schema_err}")
            return False, None, errors

        # 6. Timestamp Integrity Validation (reject future-dated annotations)
        ann_ts_str = raw_sample.get("annotation_timestamp")
        if ann_ts_str:
            try:
                ts_clean = ann_ts_str.replace("Z", "+00:00")
                ann_dt = datetime.fromisoformat(ts_clean)
                from datetime import timedelta
                now_utc = datetime.now(timezone.utc)
                if ann_dt > (now_utc + timedelta(seconds=60)):
                    errors.append(
                        f"TIMESTAMP INTEGRITY ERROR: annotation_timestamp '{ann_ts_str}' is in the future. "
                        "Future-dated annotations are strictly forbidden."
                    )
                    return False, None, errors
            except Exception as e:
                errors.append(f"TIMESTAMP PARSING ERROR: Invalid annotation_timestamp '{ann_ts_str}': {e}")
                return False, None, errors

        # 7. Verify checksum from actual local file bytes
        actual_sha256 = compute_file_sha256(v_path)
        recorded_sha256 = raw_sample.get("video_sha256")
        if recorded_sha256:
            if actual_sha256.lower() != recorded_sha256.lower():
                errors.append(
                    f"CHECKSUM MISMATCH: Computed SHA-256 ({actual_sha256}) does not match "
                    f"recorded video_sha256 in annotation ({recorded_sha256})."
                )
                return False, None, errors
        else:
            # Auto-populate computed checksum
            raw_sample["video_sha256"] = actual_sha256

        # 8. Check synthetic isolation gate
        is_synth_sample = raw_sample.get("is_synthetic_fixture", False)
        manifest = self.runner.load_manifest(m_path)

        if is_synth_sample and not manifest.is_synthetic_manifest and not allow_synthetic:
            errors.append(
                "SYNTHETIC ISOLATION VIOLATION: Cannot register synthetic fixture into "
                "an official (non-synthetic) validation manifest."
            )
            return False, None, errors

        # 9. Check duplicate sample_id and duplicate video in manifest
        sample_id = raw_sample["sample_id"]
        rel_video_str = str(video_path).replace("\\", "/")

        for existing_rec in manifest.records:
            if existing_rec.sample_id == sample_id:
                errors.append(f"DUPLICATE ERROR: Sample ID '{sample_id}' already registered in manifest.")
                return False, None, errors
            if existing_rec.video_path.replace("\\", "/") == rel_video_str:
                errors.append(f"DUPLICATE ERROR: Video '{rel_video_str}' already registered under sample '{existing_rec.sample_id}'.")
                return False, None, errors

        # 10. Determine quality, annotation, and inclusion status
        exclusion_status = raw_sample.get("exclusion_status", InclusionStatus.INCLUDED.value)
        exclusion_reason = raw_sample.get("exclusion_reason")
        
        # Check completeness (Ground Truth protocol requires minimum 3 complete cycles)
        has_cycles = len(raw_sample.get("cycle_annotations", [])) >= 3
        has_metrics = len(raw_sample.get("metric_annotations", {})) > 0
        
        if has_cycles and has_metrics:
            annotation_status = AnnotationStatus.COMPLETE.value
        else:
            annotation_status = AnnotationStatus.INCOMPLETE.value

        # Check quality flags
        q_flags = raw_sample.get("quality_flags", {})
        if q_flags.get("water_turbulence") == "SEVERE" or q_flags.get("occlusion_level") == "HIGH":
            quality_status = QualityStatus.FAILED.value
        elif q_flags.get("requires_adjudication", False):
            quality_status = QualityStatus.SUSPECT.value
        else:
            quality_status = QualityStatus.PASSED.value

        # Check dual-rater independence for official validation split
        if split == "VALIDATION_OFFICIAL":
            r_a = raw_sample.get("annotator_id")
            r_b = raw_sample.get("secondary_annotator_id")
            if not r_a or not r_b:
                if exclusion_status == InclusionStatus.INCLUDED.value:
                    exclusion_status = InclusionStatus.EXCLUDED.value
                    exclusion_reason = "Official validation trials require two distinct independent annotators."
            elif str(r_a).strip() == str(r_b).strip():
                if exclusion_status == InclusionStatus.INCLUDED.value:
                    exclusion_status = InclusionStatus.EXCLUDED.value
                    exclusion_reason = f"Dual-rater independence violation: annotators are identical ('{r_a}')."

        # CRITICAL SAFETY: Cannot mark INCLUDED if incomplete, failed quality, or explicitly excluded
        if exclusion_status == InclusionStatus.INCLUDED.value:
            if annotation_status != AnnotationStatus.COMPLETE.value:
                exclusion_status = InclusionStatus.EXCLUDED.value
                exclusion_reason = "Incomplete annotation cannot be marked INCLUDED."
            elif quality_status == QualityStatus.FAILED.value:
                exclusion_status = InclusionStatus.EXCLUDED.value
                exclusion_reason = "Failed quality control criteria cannot be marked INCLUDED."

        # 10. Construct ManifestRecord
        new_record = ManifestRecord(
            sample_id=sample_id,
            video_path=rel_video_str,
            stroke=raw_sample["stroke_type"],
            participant_id=raw_sample["participant_id"],
            annotation_file=str(annotation_path).replace("\\", "/"),
            annotation_status=annotation_status,
            quality_status=quality_status,
            inclusion_status=exclusion_status,
            validator_version=raw_sample.get("annotation_version", "1.0.0"),
            video_sha256=actual_sha256,
            session_id=raw_sample.get("session_id"),
            exclusion_reason=exclusion_reason,
            split=split,
        )

        # 11. Append and validate updated manifest
        manifest.records.append(new_record)
        updated_manifest_dict = manifest.to_dict()

        is_manifest_valid, m_err = self.runner.validate_manifest_schema(updated_manifest_dict)
        if not is_manifest_valid:
            errors.append(f"Updated manifest schema validation failed: {m_err}")
            return False, None, errors

        # 12. Save if requested
        if save:
            with open(m_path, "w", encoding="utf-8") as f:
                json.dump(updated_manifest_dict, f, indent=2)
            logger.info(f"Successfully registered sample {sample_id} into manifest {m_path}")

        return True, new_record, []
