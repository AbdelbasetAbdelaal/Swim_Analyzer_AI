"""
Ground Truth Source and Metric Provenance Contract.
Enforces that every Ground Truth measurement explicitly declares its origin modality,
and validates that modalities are scientifically compatible with measured quantities.
"""
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass


class SourceModality(str, Enum):
    HUMAN_VIDEO_ANNOTATION = "HUMAN_VIDEO_ANNOTATION"
    PHYSICAL_MOCAP = "PHYSICAL_MOCAP"
    IMU = "IMU"
    CALIBRATED_OPTICAL = "CALIBRATED_OPTICAL"
    SYNTHETIC_TEST_FIXTURE = "SYNTHETIC_TEST_FIXTURE"


class AngleDimension(str, Enum):
    TWO_D_PLANAR = "2D_PLANAR"
    THREE_D_SPATIAL = "3D_SPATIAL"


# Formal mapping of which metrics may be accepted from which source modalities
ALLOWED_METRIC_MODALITIES: Dict[str, List[SourceModality]] = {
    "stroke_rate_spm": [
        SourceModality.HUMAN_VIDEO_ANNOTATION,
        SourceModality.PHYSICAL_MOCAP,
        SourceModality.IMU,
        SourceModality.CALIBRATED_OPTICAL,
        SourceModality.SYNTHETIC_TEST_FIXTURE,
    ],
    "cycle_duration_ms": [
        SourceModality.HUMAN_VIDEO_ANNOTATION,
        SourceModality.PHYSICAL_MOCAP,
        SourceModality.IMU,
        SourceModality.CALIBRATED_OPTICAL,
        SourceModality.SYNTHETIC_TEST_FIXTURE,
    ],
    "true_dps_meters": [
        # STRICT CONSTRAINT: Only calibrated physical systems capable of measuring true whole-body CoM translation
        SourceModality.PHYSICAL_MOCAP,
        SourceModality.CALIBRATED_OPTICAL,
        SourceModality.SYNTHETIC_TEST_FIXTURE,
    ],
    "hand_excursion_proxy_bl": [
        # Proxy measure: Human video annotation or calibrated optical
        SourceModality.HUMAN_VIDEO_ANNOTATION,
        SourceModality.CALIBRATED_OPTICAL,
        SourceModality.PHYSICAL_MOCAP,
        SourceModality.SYNTHETIC_TEST_FIXTURE,
    ],
    "mean_elbow_angle_deg": [
        SourceModality.HUMAN_VIDEO_ANNOTATION,
        SourceModality.PHYSICAL_MOCAP,
        SourceModality.CALIBRATED_OPTICAL,
        SourceModality.SYNTHETIC_TEST_FIXTURE,
    ],
    "mean_knee_angle_deg": [
        SourceModality.HUMAN_VIDEO_ANNOTATION,
        SourceModality.PHYSICAL_MOCAP,
        SourceModality.CALIBRATED_OPTICAL,
        SourceModality.SYNTHETIC_TEST_FIXTURE,
    ],
    "body_roll_amplitude_deg": [
        SourceModality.HUMAN_VIDEO_ANNOTATION,
        SourceModality.PHYSICAL_MOCAP,
        SourceModality.IMU,
        SourceModality.CALIBRATED_OPTICAL,
        SourceModality.SYNTHETIC_TEST_FIXTURE,
    ],
    "stroke_symmetry_percent": [
        SourceModality.HUMAN_VIDEO_ANNOTATION,
        SourceModality.PHYSICAL_MOCAP,
        SourceModality.IMU,
        SourceModality.CALIBRATED_OPTICAL,
        SourceModality.SYNTHETIC_TEST_FIXTURE,
    ],
}


@dataclass
class MetricProvenanceRecord:
    value: Optional[float]
    source_modality: SourceModality
    angle_dimension: Optional[AngleDimension] = None
    operational_definition: Optional[str] = None
    temporal_reference: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "value": self.value,
            "source_modality": self.source_modality.value,
        }
        if self.angle_dimension is not None:
            d["angle_dimension"] = self.angle_dimension.value
        if self.operational_definition is not None:
            d["operational_definition"] = self.operational_definition
        if self.temporal_reference is not None:
            d["temporal_reference"] = self.temporal_reference
        if self.notes:
            d["notes"] = self.notes
        return d


class ProvenanceValidator:
    """
    Validates that metric annotations satisfy provenance contracts.
    """

    @classmethod
    def validate_metric(
        cls,
        metric_name: str,
        metric_payload: Any,
        is_synthetic_sample: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        Validates a single metric payload against provenance rules.
        Returns (is_valid, error_messages).
        """
        errors: List[str] = []

        if not isinstance(metric_payload, dict):
            return False, [f"Metric '{metric_name}' must be an object declaring 'value' and 'source_modality'."]

        value = metric_payload.get("value")
        raw_modality = metric_payload.get("source_modality")

        if not raw_modality:
            errors.append(f"Metric '{metric_name}' missing required 'source_modality'.")
            return False, errors

        try:
            modality = SourceModality(raw_modality)
        except ValueError:
            errors.append(
                f"Metric '{metric_name}' specifies invalid source_modality '{raw_modality}'. "
                f"Allowed: {[m.value for m in SourceModality]}"
            )
            return False, errors

        # Rule: Synthetic fixture modality only permitted on synthetic fixtures
        if modality == SourceModality.SYNTHETIC_TEST_FIXTURE and not is_synthetic_sample:
            errors.append(
                f"Metric '{metric_name}' claims SYNTHETIC_TEST_FIXTURE, but sample is not flagged as is_synthetic_fixture=true."
            )

        # Rule: Modality must be valid for the specific metric
        allowed = ALLOWED_METRIC_MODALITIES.get(metric_name)
        if allowed is not None and modality not in allowed:
            errors.append(
                f"INCOMPATIBLE PROVENANCE: Metric '{metric_name}' cannot be derived from source modality '{modality.value}'. "
                f"Allowed modalities: {[m.value for m in allowed]}."
            )

        # Skip remaining detailed checks if value is null
        if value is None:
            return len(errors) == 0, errors

        # Rule: true_dps_meters MUST NOT be accepted from HUMAN_VIDEO_ANNOTATION or IMU
        if metric_name == "true_dps_meters":
            if modality in [SourceModality.HUMAN_VIDEO_ANNOTATION, SourceModality.IMU]:
                errors.append(
                    f"PROVENANCE VIOLATION: 'true_dps_meters' cannot be measured via '{modality.value}'. "
                    f"A calibrated physical reference (PHYSICAL_MOCAP or CALIBRATED_OPTICAL) capable of "
                    f"tracking true whole-body center-of-mass translation is mandatory."
                )

        # Rule: Angle metrics must declare angle_dimension (2D_PLANAR vs 3D_SPATIAL) and cannot mix definitions
        if "angle" in metric_name or "roll" in metric_name:
            dim = metric_payload.get("angle_dimension")
            if not dim:
                errors.append(
                    f"PROVENANCE VIOLATION: Angle metric '{metric_name}' must explicitly declare 'angle_dimension' "
                    f"('2D_PLANAR' or '3D_SPATIAL')."
                )
            elif dim not in [AngleDimension.TWO_D_PLANAR.value, AngleDimension.THREE_D_SPATIAL.value]:
                errors.append(
                    f"Angle metric '{metric_name}' has invalid angle_dimension '{dim}'. "
                    f"Must be '2D_PLANAR' or '3D_SPATIAL'."
                )
            elif modality == SourceModality.HUMAN_VIDEO_ANNOTATION and dim == AngleDimension.THREE_D_SPATIAL.value:
                errors.append(
                    f"PROVENANCE VIOLATION: Human video annotation from monocular camera cannot claim "
                    f"'3D_SPATIAL' for '{metric_name}'. Must be '2D_PLANAR'."
                )

        # Rule: Symmetry must record operational definition
        if "symmetry" in metric_name:
            op_def = metric_payload.get("operational_definition")
            if not op_def or not isinstance(op_def, str) or len(op_def.strip()) < 3:
                errors.append(
                    f"PROVENANCE VIOLATION: Symmetry metric '{metric_name}' must record its exact "
                    f"'operational_definition' (e.g. 'MIN_MAX_PULL_DURATION_RATIO')."
                )

        return len(errors) == 0, errors

    @classmethod
    def validate_sample_metrics(
        cls,
        sample_dict: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validates all metrics in sample_dict['metric_annotations'].
        """
        all_errors: List[str] = []
        metrics = sample_dict.get("metric_annotations", {})
        is_synthetic = sample_dict.get("is_synthetic_fixture", False)

        if not isinstance(metrics, dict):
            return False, ["Field 'metric_annotations' must be a dictionary."]

        for metric_name, payload in metrics.items():
            is_valid, errs = cls.validate_metric(metric_name, payload, is_synthetic_sample=is_synthetic)
            if not is_valid:
                all_errors.extend(errs)

        return len(all_errors) == 0, all_errors
