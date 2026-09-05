import pytest
import uuid
from database.database import SessionLocal, init_db
from database.repository import AthleteRepository, AnalysisHistoryRepository
from models.athlete_profile import AthleteProfile
from models.analysis_session import AnalysisSession

@pytest.fixture(scope="module")
def setup_db():
    init_db()
    yield

def test_orphaned_athlete_deny_by_default(setup_db):
    db = SessionLocal()
    repo = AthleteRepository(db)
    
    ath_id = str(uuid.uuid4())
    athlete = AthleteProfile(coach_id="test_coach", athlete_id=ath_id, full_name="Orphaned Athlete", age=25, gender="Male", height_cm=180, weight_kg=75, swimming_level="Pro", preferred_stroke="Freestyle")
    
    with pytest.raises(ValueError):
        repo.create(athlete, None) # Coach ID required
        
    repo.create(athlete, "orphan_coach")
    
    with pytest.raises(ValueError):
        repo.get_by_id_and_coach_id(ath_id, None)
        
    assert repo.get_by_id_and_coach_id(ath_id, "coach_x") is None
    
    db.close()

def test_orphaned_session_deny_by_default(setup_db):
    db = SessionLocal()
    repo = AnalysisHistoryRepository(db)
    
    sess_id = str(uuid.uuid4())
    session = AnalysisSession(account_id="test_account", session_id=sess_id, athlete_id="ath_x", stroke_type="Freestyle", 
        analysis_timestamp="2026-01-01T00:00:00Z",
        original_video_filename="dummy.mp4",
        processed_video_filename="dummy.mp4",
        metadata_json_path="dummy.json",
        report_json_path="dummy.json",
        performance_score=0.0,
        scientific_confidence="Low",
        completed_cycles=0,
        processing_time_seconds=0.0
    )
    
    with pytest.raises(ValueError):
        repo.create(session, None)
        
    repo.create(session, "orphan_coach")
        
    with pytest.raises(ValueError):
        repo.get_by_id_and_account_id(sess_id, None)
        
    assert repo.get_by_id_and_account_id(sess_id, "coach_x") is None
    db.close()

def test_cross_tenant_attacks(setup_db):
    db = SessionLocal()
    ath_repo = AthleteRepository(db)
    sess_repo = AnalysisHistoryRepository(db)
    
    coach_a = "coach_A"
    coach_b = "coach_B"
    
    ath_b_id = str(uuid.uuid4())
    athlete_b = AthleteProfile(coach_id="test_coach", athlete_id=ath_b_id, full_name="Athlete B", age=20, gender="Male", height_cm=180, weight_kg=75, swimming_level="Pro", preferred_stroke="Freestyle")
    ath_repo.create(athlete_b, coach_b)
    
    sess_b_id = str(uuid.uuid4())
    session_b = AnalysisSession(account_id="test_account", session_id=sess_b_id, athlete_id=ath_b_id, stroke_type="Freestyle", 
        analysis_timestamp="2026-01-01T00:00:00Z",
        original_video_filename="dummy.mp4",
        processed_video_filename="dummy.mp4",
        metadata_json_path="dummy.json",
        report_json_path="dummy.json",
        performance_score=0.0,
        scientific_confidence="Low",
        completed_cycles=0,
        processing_time_seconds=0.0
    )
    sess_repo.create(session_b, coach_b)
    
    # ATTACK 1: Coach A reads Athlete B
    assert ath_repo.get_by_id_and_coach_id(ath_b_id, coach_a) is None
    
    # ATTACK 2: Coach A attempts to update Athlete B
    athlete_b.full_name = "Hacked by A"
    with pytest.raises(PermissionError):
        ath_repo.update_by_id_and_coach_id(athlete_b, coach_a)
        
    # ATTACK 3: Coach A attempts to steal Athlete B
    athlete_b.coach_id = coach_a
    with pytest.raises(PermissionError):
        ath_repo.update_by_id_and_coach_id(athlete_b, coach_a)
        
    # ATTACK 4: Coach A reads Session B
    assert sess_repo.get_by_id_and_account_id(sess_b_id, coach_a) is None
    
    # ATTACK 5: Coach A reads Sessions of Athlete B
    sessions = sess_repo.get_by_athlete_and_account_id(ath_b_id, coach_a)
    assert len(sessions) == 0
    
    # ATTACK 6: Coach A attempts to update Session B
    session_b.performance_score = 99.9
    with pytest.raises(PermissionError):
        sess_repo.update_by_id_and_account_id(session_b, coach_a)
        
    db.close()
