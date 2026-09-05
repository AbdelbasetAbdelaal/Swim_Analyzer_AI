import pytest
from models.analysis_session import AnalysisSession
from services.analysis_history_service import AnalysisHistoryService
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

def test_analysis_session_serialization():
    session = AnalysisSession(account_id="test_account",
        athlete_id="user_123",
        analysis_timestamp="2026-08-01T12:00:00.000000",
        original_video_filename="swim_vid.mp4",
        processed_video_filename="processed_swim_vid.mp4",
        metadata_json_path="meta.json",
        report_json_path="report.json",
        performance_score=85.5,
        scientific_confidence="High",
        completed_cycles=12,
        stroke_type="Freestyle",
        processing_time_seconds=45.2
    )

    data = session.to_dict()
    assert data["athlete_id"] == "user_123"
    assert data["performance_score"] == 85.5
    assert "session_id" in data

    loaded_session = AnalysisSession.from_dict(data)
    assert loaded_session.session_id == session.session_id
    assert loaded_session.athlete_id == session.athlete_id
    assert loaded_session.processing_time_seconds == 45.2

def test_analysis_history_service_crud(db_session):
    service = AnalysisHistoryService(db_session=db_session)

    session = AnalysisSession(account_id="test_account",
        athlete_id="athlete_1",
        analysis_timestamp="2026-08-01T12:00:00.000000",
        original_video_filename="vid1.mp4",
        processed_video_filename="vid1_out.mp4",
        metadata_json_path="meta1.json",
        report_json_path="report1.json",
        performance_score=90.0,
        scientific_confidence="High",
        completed_cycles=10,
        stroke_type="Freestyle",
        processing_time_seconds=30.0
    )

    # Test Save
    assert service.create_session(session, "test_account") is True

    # Test Load
    loaded = service.load_session(session.session_id, "test_account")
    assert loaded is not None
    assert loaded.session_id == session.session_id

    # Test Get by Athlete
    # Note: Athlete needs to exist in the database for the join to work in get_sessions_by_athlete_and_account_id
    from database.repository import AthleteRepository
    from models.athlete_profile import AthleteProfile
    AthleteRepository(db_session).create(AthleteProfile(coach_id="test_account", athlete_id="athlete_1", full_name="A1", age=20, gender="Male", height_cm=180, weight_kg=75, swimming_level="Pro", preferred_stroke="Free"), "test_account")

    sessions = service.get_sessions_by_athlete("athlete_1", "test_account")
    assert len(sessions) == 1
    assert sessions[0].athlete_id == "athlete_1"

    # Test Delete
    assert service.delete_session(session.session_id, "test_account") is True
    assert service.load_session(session.session_id, "test_account") is None

def test_get_sessions_by_athlete_ordering(db_session):
    service = AnalysisHistoryService(db_session=db_session)

    s1 = AnalysisSession(account_id="test_account",
        athlete_id="athlete_2",
        analysis_timestamp="2026-08-01T10:00:00.000000", # Older
        original_video_filename="old.mp4",
        processed_video_filename="old_out.mp4",
        metadata_json_path="", report_json_path="",
        performance_score=80.0, scientific_confidence="High",
        completed_cycles=5, stroke_type="Freestyle", processing_time_seconds=10.0
    )
    s2 = AnalysisSession(account_id="test_account",
        athlete_id="athlete_2",
        analysis_timestamp="2026-08-01T12:00:00.000000", # Newer
        original_video_filename="new.mp4",
        processed_video_filename="new_out.mp4",
        metadata_json_path="", report_json_path="",
        performance_score=85.0, scientific_confidence="High",
        completed_cycles=6, stroke_type="Freestyle", processing_time_seconds=12.0
    )

    from database.repository import AthleteRepository
    from models.athlete_profile import AthleteProfile
    AthleteRepository(db_session).create(AthleteProfile(coach_id="coach_1", athlete_id="athlete_2", full_name="A2", age=20, gender="Male", height_cm=180, weight_kg=75, swimming_level="Pro", preferred_stroke="Free"), "coach_1")

    service.create_session(s1, "coach_1")
    service.create_session(s2, "coach_1")

    sessions = service.get_sessions_by_athlete("athlete_2", "coach_1")
    assert len(sessions) == 2
    # Should be sorted newest first
    assert sessions[0].session_id == s2.session_id
    assert sessions[1].session_id == s1.session_id


def test_get_sessions_by_account_filtering(db_session):
    service = AnalysisHistoryService(db_session=db_session)

    user_session = AnalysisSession(athlete_id=None,
        account_id="user_abc",
        analysis_timestamp="2026-08-01T09:00:00.000000",
        original_video_filename="user.mp4",
        processed_video_filename="user_out.mp4",
        metadata_json_path="meta_user.json",
        report_json_path="report_user.json",
        performance_score=75.0,
        scientific_confidence="Medium",
        completed_cycles=8,
        stroke_type="Backstroke",
        processing_time_seconds=22.0
    )
    coach_session = AnalysisSession(athlete_id="athlete_3",
        account_id="coach_xyz",
        analysis_timestamp="2026-08-01T11:00:00.000000",
        original_video_filename="coach.mp4",
        processed_video_filename="coach_out.mp4",
        metadata_json_path="meta_coach.json",
        report_json_path="report_coach.json",
        performance_score=88.0,
        scientific_confidence="High",
        completed_cycles=14,
        stroke_type="Freestyle",
        processing_time_seconds=35.0
    )

    service.create_session(user_session, "user_abc")
    service.create_session(coach_session, "coach_xyz")

    user_sessions = service.get_sessions_by_account("user_abc")
    coach_sessions = service.get_sessions_by_account("coach_xyz")

    assert len(user_sessions) == 1
    assert user_sessions[0].account_id == "user_abc"
    assert user_sessions[0].original_video_filename == "user.mp4"

    assert len(coach_sessions) == 1
    assert coach_sessions[0].account_id == "coach_xyz"
    assert coach_sessions[0].original_video_filename == "coach.mp4"
