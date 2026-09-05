from typing import List, Optional
from models.athlete_profile import AthleteProfile
from database import SessionLocal, AthleteRepository
import logging

logger = logging.getLogger(__name__)

class AthleteService:
    def __init__(self, db_session=None):
        self._owns_session = False
        if db_session is None:
            self.db = SessionLocal()
            self._owns_session = True
        else:
            self.db = db_session
        self.repository = AthleteRepository(self.db)

    def close(self):
        """Explicitly closes the database session if owned by this service."""
        if getattr(self, '_owns_session', False) and getattr(self, 'db', None):
            try:
                self.db.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def validate_profile(self, profile: AthleteProfile) -> List[str]:
        """Validate athlete profile fields. Returns a list of error messages."""
        errors = []
        if not profile.full_name or not profile.full_name.strip():
            errors.append("Full name is required.")
        if profile.age < 0 or profile.age > 150:
            errors.append("Age must be between 0 and 150.")
        if profile.height_cm <= 0:
            errors.append("Height must be greater than 0.")
        if profile.weight_kg <= 0:
            errors.append("Weight must be greater than 0.")
        if profile.shoulder_width_cm is not None and profile.shoulder_width_cm <= 0:
            errors.append("Shoulder width must be greater than 0 if provided.")
        if not profile.swimming_level:
            errors.append("Swimming level is required.")
        if not profile.preferred_stroke:
            errors.append("Preferred stroke is required.")
        return errors

    def create_profile(self, coach_id: str, **kwargs) -> AthleteProfile:
        """Create and save a new athlete profile."""
        if not coach_id:
            raise ValueError("coach_id is required to create a profile")
            
        profile = AthleteProfile(coach_id=coach_id, **kwargs)
        profile.coach_id = coach_id
        
        errors = self.validate_profile(profile)
        if errors:
            error_msg = "; ".join(errors)
            logger.error(f"Failed to save athlete profile {profile.athlete_id}: {error_msg}")
            raise ValueError(f"Invalid athlete profile: {error_msg}")
            
        success = self.repository.create(profile, coach_id)
        if success:
            logger.info(f"Created athlete profile: {profile.athlete_id} for coach {coach_id}")
        else:
            logger.error(f"Error saving athlete profile {profile.athlete_id} to database.")
            
        return profile

    def load_profile(self, athlete_id: str, coach_id: str) -> Optional[AthleteProfile]:
        """Load an athlete profile from the database, enforcing coach ownership strictly."""
        if not coach_id:
            logger.warning(f"Security: Missing coach_id for athlete profile access {athlete_id}")
            raise ValueError("coach_id is required")
            
        profile = self.repository.get_by_id_and_coach_id(athlete_id, coach_id)
        if not profile:
            logger.warning(f"Athlete profile not found or access denied: {athlete_id}")
            return None
                
        return profile

    def get_all_profiles(self, coach_id: str) -> List[AthleteProfile]:
        """Load all athlete profiles strictly for a specific coach."""
        if not coach_id:
            raise ValueError("coach_id is required to fetch profiles")
        return self.repository.get_all_by_coach_id(coach_id=coach_id)

    def update_profile(self, profile: AthleteProfile, coach_id: str) -> bool:
        """Update an existing athlete profile with ownership validation."""
        errors = self.validate_profile(profile)
        if errors:
            error_msg = "; ".join(errors)
            logger.error(f"Failed to update athlete profile {profile.athlete_id}: {error_msg}")
            raise ValueError(f"Invalid athlete profile: {error_msg}")
            
        success = self.repository.update_by_id_and_coach_id(profile, coach_id)
        if success:
            logger.info(f"Updated athlete profile: {profile.athlete_id} by coach {coach_id}")
        else:
            logger.error(f"Error updating athlete profile {profile.athlete_id} by coach {coach_id}")
        return success

    def delete_profile(self, athlete_id: str, coach_id: str) -> bool:
        """Delete an athlete profile by ID, enforcing strict coach ownership."""
        if not coach_id:
            logger.warning(f"Security: Missing coach_id for delete operation on {athlete_id}")
            raise ValueError("coach_id is required")
            
        success = self.repository.delete_by_id_and_coach_id(athlete_id, coach_id)
        if success:
            logger.info(f"Deleted athlete profile: {athlete_id}")
        else:
            logger.error(f"Error deleting athlete profile {athlete_id}")
        return success

