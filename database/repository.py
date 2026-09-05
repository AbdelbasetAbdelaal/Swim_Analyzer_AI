from typing import List, Optional
from sqlalchemy.orm import Session
from database.models import AthleteModel, AnalysisSessionModel, CoachModel
from models.athlete_profile import AthleteProfile
from models.analysis_session import AnalysisSession
from models.coach_profile import CoachProfile

class CoachRepository:
    """
    Data access repository for Coach entities.
    """
    def __init__(self, db: Session):
        self.db = db

    def add(self, coach: CoachProfile) -> bool:
        db_coach = self.db.query(CoachModel).filter(CoachModel.coach_id == coach.coach_id).first()
        if db_coach:
            for key, value in coach.to_dict().items():
                setattr(db_coach, key, value)
        else:
            valid_keys = {c.name for c in CoachModel.__table__.columns}
            filtered_data = {k: v for k, v in coach.to_dict().items() if k in valid_keys}
            db_coach = CoachModel(**filtered_data)
            self.db.add(db_coach)
            
        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

    def get_by_id(self, coach_id: str) -> Optional[CoachProfile]:
        db_coach = self.db.query(CoachModel).filter(CoachModel.coach_id == coach_id).first()
        if db_coach:
            data = {c.name: getattr(db_coach, c.name) for c in db_coach.__table__.columns}
            return CoachProfile.from_dict(data)
        return None

    def get_by_username(self, username: str) -> Optional[CoachProfile]:
        db_coach = self.db.query(CoachModel).filter(CoachModel.username == username).first()
        if db_coach:
            data = {c.name: getattr(db_coach, c.name) for c in db_coach.__table__.columns}
            return CoachProfile.from_dict(data)
        return None

    def get_all(self) -> List[CoachProfile]:
        db_coaches = self.db.query(CoachModel).all()
        return [CoachProfile.from_dict({c.name: getattr(coach, c.name) for c in coach.__table__.columns}) for coach in db_coaches]

    def delete(self, coach_id: str) -> bool:
        db_coach = self.db.query(CoachModel).filter(CoachModel.coach_id == coach_id).first()
        if db_coach:
            try:
                self.db.delete(db_coach)
                self.db.commit()
                return True
            except Exception:
                self.db.rollback()
                return False
        return False


class AthleteRepository:
    """
    Data access methods (CRUD) for AthleteProfile entities with Coach isolation support.
    """
    def __init__(self, db: Session):
        self.db = db

    def create(self, profile: AthleteProfile, coach_id: str) -> bool:
        if not coach_id:
            raise ValueError("Security: coach_id is required to create an athlete")
        
        # Enforce owner identity
        profile.coach_id = coach_id
        
        db_athlete = self.db.query(AthleteModel).filter(AthleteModel.athlete_id == profile.athlete_id).first()
        if db_athlete:
            raise ValueError(f"Athlete {profile.athlete_id} already exists. Use update.")
            
        valid_keys = {c.name for c in AthleteModel.__table__.columns}
        filtered_data = {k: v for k, v in profile.to_dict().items() if k in valid_keys}
        db_athlete = AthleteModel(**filtered_data)
        self.db.add(db_athlete)
            
        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

    def update_by_id_and_coach_id(self, profile: AthleteProfile, coach_id: str) -> bool:
        if not coach_id:
            raise ValueError("Security: coach_id is required to update an athlete")
            
        db_athlete = self.db.query(AthleteModel).filter(
            AthleteModel.athlete_id == profile.athlete_id,
            AthleteModel.coach_id == coach_id
        ).first()
        
        if not db_athlete:
            raise PermissionError("Update denied: Athlete not found or belongs to another coach.")
            
        # Prevent ownership takeover
        if profile.coach_id and profile.coach_id != coach_id:
            raise PermissionError("Security: Cannot change coach_id of an existing athlete.")
            
        profile.coach_id = coach_id # Enforce invariant
        
        for key, value in profile.to_dict().items():
            if key != 'coach_id': # skip coach_id modification on the db model explicitly
                setattr(db_athlete, key, value)
                
        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

    def get_by_id_and_coach_id(self, athlete_id: str, coach_id: str) -> Optional[AthleteProfile]:
        if not coach_id:
            raise ValueError("Security: coach_id is required for tenant authorization")
            
        db_athlete = self.db.query(AthleteModel).filter(
            AthleteModel.athlete_id == athlete_id,
            AthleteModel.coach_id == coach_id
        ).first()
        
        if db_athlete:
            data = {c.name: getattr(db_athlete, c.name) for c in db_athlete.__table__.columns}
            return AthleteProfile.from_dict(data)
        return None

    def get_all_by_coach_id(self, coach_id: str) -> List[AthleteProfile]:
        query = self.db.query(AthleteModel)
        if not coach_id:
            raise ValueError("Security: coach_id is required")
            
        # Strict Multi-tenancy filter: show ONLY athletes owned by this coach
        query = query.filter(AthleteModel.coach_id == coach_id)
            
        db_athletes = query.all()
        profiles = []
        for db_athlete in db_athletes:
            data = {c.name: getattr(db_athlete, c.name) for c in db_athlete.__table__.columns}
            profiles.append(AthleteProfile.from_dict(data))
        return profiles

    def delete_by_id_and_coach_id(self, athlete_id: str, coach_id: str) -> bool:
        if not coach_id:
            raise ValueError("Security: coach_id is required for tenant authorization")
            
        db_athlete = self.db.query(AthleteModel).filter(
            AthleteModel.athlete_id == athlete_id,
            AthleteModel.coach_id == coach_id
        ).first()
        
        if db_athlete:
            try:
                self.db.delete(db_athlete)
                self.db.commit()
                return True
            except Exception:
                self.db.rollback()
                return False
        return False


class AnalysisHistoryRepository:
    """
    Data access methods (CRUD) for AnalysisSession entities.
    """
    def __init__(self, db: Session):
        self.db = db

    def create(self, session: AnalysisSession, account_id: str) -> bool:
        if not account_id:
            raise ValueError("Security: account_id is required to create a session")
            
        session.account_id = account_id
        
        db_session = self.db.query(AnalysisSessionModel).filter(AnalysisSessionModel.session_id == session.session_id).first()
        if db_session:
            raise ValueError(f"Session {session.session_id} already exists. Use update.")
            
        valid_keys = {c.name for c in AnalysisSessionModel.__table__.columns}
        filtered_data = {k: v for k, v in session.to_dict().items() if k in valid_keys}
        db_session = AnalysisSessionModel(**filtered_data)
        self.db.add(db_session)
            
        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

    def update_by_id_and_account_id(self, session: AnalysisSession, account_id: str) -> bool:
        if not account_id:
            raise ValueError("Security: account_id is required to update a session")
            
        db_session = self.db.query(AnalysisSessionModel).filter(
            AnalysisSessionModel.session_id == session.session_id,
            AnalysisSessionModel.account_id == account_id
        ).first()
        
        if not db_session:
            raise PermissionError("Update denied: Session not found or belongs to another account.")
            
        if session.account_id and session.account_id != account_id:
            raise PermissionError("Security: Cannot change account_id of an existing session.")
            
        session.account_id = account_id
            
        for key, value in session.to_dict().items():
            if key != 'account_id':
                setattr(db_session, key, value)
                
        try:
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

    def get_by_athlete_and_account_id(self, athlete_id: str, account_id: str) -> List[AnalysisSession]:
        if not account_id:
            raise ValueError("Security: account_id is required")
            
        # Join with AthleteModel to double-check ownership of the athlete
        db_sessions = self.db.query(AnalysisSessionModel).join(
            AthleteModel, AthleteModel.athlete_id == AnalysisSessionModel.athlete_id
        ).filter(
            AnalysisSessionModel.athlete_id == athlete_id,
            AnalysisSessionModel.account_id == account_id,
            AthleteModel.coach_id == account_id
        ).order_by(AnalysisSessionModel.analysis_timestamp.desc()).all()
        
        sessions = []
        for db_session in db_sessions:
            data = {c.name: getattr(db_session, c.name) for c in db_session.__table__.columns}
            sessions.append(AnalysisSession.from_dict(data))
        return sessions

    def get_all_by_account_id(self, account_id: str) -> List[AnalysisSession]:
        db_sessions = self.db.query(AnalysisSessionModel).filter(AnalysisSessionModel.account_id == account_id).order_by(AnalysisSessionModel.analysis_timestamp.desc()).all()
        sessions = []
        for db_session in db_sessions:
            data = {c.name: getattr(db_session, c.name) for c in db_session.__table__.columns}
            sessions.append(AnalysisSession.from_dict(data))
        return sessions

    def get_all(self) -> List[AnalysisSession]:
        db_sessions = self.db.query(AnalysisSessionModel).order_by(AnalysisSessionModel.analysis_timestamp.desc()).all()
        sessions = []
        for db_session in db_sessions:
            data = {c.name: getattr(db_session, c.name) for c in db_session.__table__.columns}
            sessions.append(AnalysisSession.from_dict(data))
        return sessions

    def get_by_id_and_account_id(self, session_id: str, account_id: str) -> Optional[AnalysisSession]:
        if not account_id:
            raise ValueError("Security: account_id is required for tenant authorization")
            
        db_session = self.db.query(AnalysisSessionModel).filter(
            AnalysisSessionModel.session_id == session_id,
            AnalysisSessionModel.account_id == account_id
        ).first()
        
        if db_session:
            data = {c.name: getattr(db_session, c.name) for c in db_session.__table__.columns}
            return AnalysisSession.from_dict(data)
        return None

    def delete_by_id_and_account_id(self, session_id: str, account_id: str) -> bool:
        if not account_id:
            raise ValueError("Security: account_id is required for tenant authorization")
            
        db_session = self.db.query(AnalysisSessionModel).filter(
            AnalysisSessionModel.session_id == session_id,
            AnalysisSessionModel.account_id == account_id
        ).first()
        
        if db_session:
            try:
                self.db.delete(db_session)
                self.db.commit()
                return True
            except Exception:
                self.db.rollback()
                return False
        return False
