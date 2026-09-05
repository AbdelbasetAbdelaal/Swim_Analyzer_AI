import pytest
from models.athlete_profile import AthleteProfile
from services.athlete_service import AthleteService
from database.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_session():
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()

def test_athlete_profile_creation():
    profile = AthleteProfile(coach_id="test_coach", full_name="Michael Phelps",
        age=38,
        gender="Male",
        height_cm=193.0,
        weight_kg=90.0,
        swimming_level="Elite",
        preferred_stroke="Butterfly"
    )
    assert profile.full_name == "Michael Phelps"
    assert profile.athlete_id is not None
    assert len(profile.athlete_id) > 0
    assert profile.coach_id == "test_coach"

def test_athlete_profile_serialization():
    profile = AthleteProfile(coach_id="test_coach", full_name="Katie Ledecky",
        age=27,
        gender="Female",
        height_cm=183.0,
        weight_kg=73.0,
        swimming_level="Elite",
        preferred_stroke="Freestyle"
    )
    data = profile.to_dict()
    assert data["full_name"] == "Katie Ledecky"
    
    new_profile = AthleteProfile.from_dict(data)
    assert new_profile.athlete_id == profile.athlete_id
    assert new_profile.height_cm == 183.0
    assert new_profile.coach_id == "test_coach"

def test_athlete_service_create(db_session):
    service = AthleteService(db_session=db_session)
    profile = service.create_profile(
        coach_id="test_coach",
        full_name="Sarah Sjostrom",
        age=30,
        gender="Female",
        height_cm=183.0,
        weight_kg=68.0,
        swimming_level="Elite",
        preferred_stroke="Butterfly"
    )
    assert profile.athlete_id is not None
    loaded_profile = service.load_profile(profile.athlete_id, "test_coach")
    assert loaded_profile is not None
    assert loaded_profile.full_name == "Sarah Sjostrom"

def test_athlete_service_update_and_delete(db_session):
    service = AthleteService(db_session=db_session)
    profile = service.create_profile(
        coach_id="test_coach",
        full_name="Adam Peaty",
        age=29,
        gender="Male",
        height_cm=191.0,
        weight_kg=86.0,
        swimming_level="Elite",
        preferred_stroke="Breaststroke"
    )
    
    # Update
    profile.swimming_level = "Professional"
    assert service.update_profile(profile, "test_coach") is True
    loaded = service.load_profile(profile.athlete_id, "test_coach")
    assert loaded.swimming_level == "Professional"
    
    # Delete
    assert service.delete_profile(profile.athlete_id, "test_coach") is True
    assert service.load_profile(profile.athlete_id, "test_coach") is None

def test_athlete_service_validation_errors(db_session):
    service = AthleteService(db_session=db_session)
    
    with pytest.raises(ValueError):
        service.create_profile(
            coach_id="test_coach",
            full_name="", # Invalid
            age=-5, # Invalid
            gender="Male",
            height_cm=0, # Invalid
            weight_kg=86.0,
            swimming_level="", # Invalid
            preferred_stroke="Breaststroke"
        )

def test_athlete_service_get_all_profiles(db_session):
    service = AthleteService(db_session=db_session)
    service.create_profile(coach_id="coach1", full_name="A", age=20, gender="M", height_cm=180, weight_kg=80, swimming_level="Pro", preferred_stroke="Free")
    service.create_profile(coach_id="coach1", full_name="B", age=22, gender="F", height_cm=170, weight_kg=60, swimming_level="Amateur", preferred_stroke="Back")
    
    profiles = service.get_all_profiles("coach1")
    assert len(profiles) == 2
