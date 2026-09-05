"""
Calibration engines for converting pixel measurements into physical or relative measurements.
Implements explicit measurement domain classification and prevents relative metrics from being presented as meters.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional
import numpy as np
from models.data_models import ValidatedMetric

class MeasurementDomain(str, Enum):
    CALIBRATED_PHYSICAL = "calibrated_physical"
    RELATIVE_BODY_NORMALIZED = "relative_body_normalized"
    POSE_RELATIVE_3D = "pose_relative_3d"
    IMAGE_SPACE = "image_space"
    UNAVAILABLE = "unavailable"

class CalibrationEngine(ABC):
    """
    Abstract base class for measurement calibration.
    """
    @property
    @abstractmethod
    def mode_name(self) -> str:
        pass

    @property
    @abstractmethod
    def is_physical_calibration(self) -> bool:
        """Returns True if the engine produces physical meters, False otherwise."""
        pass

    @property
    @abstractmethod
    def measurement_domain(self) -> str:
        """Returns the measurement domain string."""
        pass

    @property
    @abstractmethod
    def unit_name(self) -> str:
        """Returns the unit name string (e.g., 'meters', 'body_length', 'pixels')."""
        pass

    @abstractmethod
    def calibrate_distance(self, p1: Any, p2: Any, frame_width: int, frame_height: int, reference_landmarks: Any = None) -> float:
        """
        Converts distance between two points into a calibrated measurement.
        """
        pass

    def create_metric(self, name: str, value: Optional[float], valid: bool = True, reason: str = "") -> ValidatedMetric:
        """
        Creates a ValidatedMetric strictly attached to this engine's measurement domain.
        """
        if not self.is_physical_calibration and self.unit_name == "meters":
            # Safety guard: Never allow uncalibrated metric to claim 'meters'
            return ValidatedMetric(
                name=name,
                value=None,
                unit="meters",
                measurement_domain=MeasurementDomain.UNAVAILABLE.value,
                status="unavailable",
                valid=False,
                calibration_required=True,
                calibration_status="missing",
                reason_if_invalid="Physical meter calibration missing"
            )

        if not valid or value is None or value <= 0:
            return ValidatedMetric(
                name=name,
                value=None,
                unit=self.unit_name,
                measurement_domain=self.measurement_domain,
                status="unavailable",
                valid=False,
                calibration_required=True if self.is_physical_calibration else False,
                calibration_status="calibrated" if self.is_physical_calibration else "uncalibrated",
                reason_if_invalid=reason or "Invalid distance calculation"
            )

        return ValidatedMetric(
            name=name,
            value=float(value),
            unit=self.unit_name,
            measurement_domain=self.measurement_domain,
            status="available",
            valid=True,
            confidence=1.0,
            calibration_required=False,
            calibration_status="calibrated" if self.is_physical_calibration else "uncalibrated",
            reason_if_invalid=""
        )


class RelativeCalibration(CalibrationEngine):
    """
    Normalizes distance based on the swimmer's estimated body height in the frame.
    Returns measurements in "body_length" under RELATIVE_BODY_NORMALIZED domain.
    """
    
    @property
    def mode_name(self) -> str:
        return "Relative (Body Height)"

    @property
    def is_physical_calibration(self) -> bool:
        return False

    @property
    def measurement_domain(self) -> str:
        return MeasurementDomain.RELATIVE_BODY_NORMALIZED.value

    @property
    def unit_name(self) -> str:
        return "body_length"

    def calibrate_distance(self, p1: Any, p2: Any, frame_width: int, frame_height: int, reference_landmarks: Any = None) -> float:
        if not reference_landmarks or len(reference_landmarks) < 29:
            return 0.0
            
        # Calculate raw pixel distance between p1 and p2
        pixel_dist = np.sqrt(
            ((p1.x - p2.x) * frame_width)**2 + 
            ((p1.y - p2.y) * frame_height)**2
        )
        
        # Estimate body height using Shoulder to Ankle distance (average of left/right)
        l_shoulder, r_shoulder = reference_landmarks[11], reference_landmarks[12]
        l_ankle, r_ankle = reference_landmarks[27], reference_landmarks[28]
        
        shoulder_mid_x = (l_shoulder.x + r_shoulder.x) / 2
        shoulder_mid_y = (l_shoulder.y + r_shoulder.y) / 2
        ankle_mid_x = (l_ankle.x + r_ankle.x) / 2
        ankle_mid_y = (l_ankle.y + r_ankle.y) / 2
        
        body_height_pixels = np.sqrt(
            ((shoulder_mid_x - ankle_mid_x) * frame_width)**2 + 
            ((shoulder_mid_y - ankle_mid_y) * frame_height)**2
        )
        
        if body_height_pixels <= 0:
            return 0.0
            
        return float(pixel_dist / body_height_pixels)


class PhysicalPoolCalibration(CalibrationEngine):
    """
    Calibrates distance to physical meters using a known pool scale (pixels per meter).
    """
    def __init__(self, pixels_per_meter: float, reference_name: str = "Pool Lane Line"):
        self.pixels_per_meter = float(pixels_per_meter)
        self.reference_name = reference_name

    @property
    def mode_name(self) -> str:
        return f"Physical ({self.reference_name})"

    @property
    def is_physical_calibration(self) -> bool:
        return self.pixels_per_meter > 0

    @property
    def measurement_domain(self) -> str:
        return MeasurementDomain.CALIBRATED_PHYSICAL.value if self.is_physical_calibration else MeasurementDomain.UNAVAILABLE.value

    @property
    def unit_name(self) -> str:
        return "meters"

    def calibrate_distance(self, p1: Any, p2: Any, frame_width: int, frame_height: int, reference_landmarks: Any = None) -> float:
        if self.pixels_per_meter <= 0:
            return 0.0
            
        pixel_dist = np.sqrt(
            ((p1.x - p2.x) * frame_width)**2 + 
            ((p1.y - p2.y) * frame_height)**2
        )
        return float(pixel_dist / self.pixels_per_meter)


class UncalibratedEngine(CalibrationEngine):
    """
    Engine representing an uncalibrated setup where physical calibration is unavailable.
    """
    @property
    def mode_name(self) -> str:
        return "Uncalibrated"

    @property
    def is_physical_calibration(self) -> bool:
        return False

    @property
    def measurement_domain(self) -> str:
        return MeasurementDomain.UNAVAILABLE.value

    @property
    def unit_name(self) -> str:
        return "unavailable"

    def calibrate_distance(self, p1: Any, p2: Any, frame_width: int, frame_height: int, reference_landmarks: Any = None) -> float:
        return 0.0
