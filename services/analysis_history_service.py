import logging
from typing import List, Optional
from models.analysis_session import AnalysisSession
from database import SessionLocal, AnalysisHistoryRepository

logger = logging.getLogger(__name__)

class AnalysisHistoryService:
    def __init__(self, db_session=None):
        self._owns_session = False
        if db_session is None:
            self.db = SessionLocal()
            self._owns_session = True
        else:
            self.db = db_session
        self.repository = AnalysisHistoryRepository(self.db)

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

    def create_session(self, session: AnalysisSession, account_id: str) -> bool:
        """Create a new analysis session securely."""
        if not account_id:
            raise ValueError("account_id is required to create a session")
            
        success = self.repository.create(session, account_id)
        if success:
            logger.info(f"Created analysis session: {session.session_id} for account {account_id}")
        else:
            logger.error(f"Error creating analysis session {session.session_id} for account {account_id}")
        return success

    def update_session(self, session: AnalysisSession, account_id: str) -> bool:
        """Update an existing analysis session with ownership validation."""
        if not account_id:
            raise ValueError("account_id is required to update a session")
            
        success = self.repository.update_by_id_and_account_id(session, account_id)
        if success:
            logger.info(f"Updated analysis session: {session.session_id} by account {account_id}")
        else:
            logger.error(f"Error updating analysis session {session.session_id} by account {account_id}")
        return success

    def load_session(self, session_id: str, account_id: str) -> Optional[AnalysisSession]:
        """Load an analysis session from the database, enforcing account ownership strictly."""
        if not account_id:
            logger.warning(f"Security: Missing account_id for session access {session_id}")
            raise ValueError("account_id is required")
            
        session = self.repository.get_by_id_and_account_id(session_id, account_id)
        if not session:
            logger.warning(f"Analysis session not found or access denied: {session_id}")
            return None
                
        return session

    def get_sessions_by_athlete(self, athlete_id: str, account_id: str) -> List[AnalysisSession]:
        """Load all analysis sessions for a specific athlete, enforcing tenant boundaries."""
        if not account_id:
            raise ValueError("account_id is required to fetch athlete sessions")
        if not athlete_id:
            return []
        return self.repository.get_by_athlete_and_account_id(athlete_id, account_id)

    def get_sessions_by_account(self, account_id: str) -> List[AnalysisSession]:
        """Load all analysis sessions for a specific account."""
        if not account_id:
            raise ValueError("account_id is required to fetch account sessions")
        return self.repository.get_all_by_account_id(account_id)

    def get_all_sessions(self, principal) -> List[AnalysisSession]:
        """Load all analysis sessions across all athletes (Admin only)."""
        if not principal or getattr(principal, "role", "coach") != "admin":
            raise PermissionError("Global read access denied. Administrator privileges required.")
            
        return self.repository.get_all()

    def get_performance_history_df(self, account_id: str, athlete_id: Optional[str] = None, principal=None):
        """Returns a Pandas DataFrame of performance progression for historical charting."""
        import pandas as pd
        if not account_id:
            raise ValueError("account_id is required for performance history")
            
        # Admin gets all data if athlete_id is None, otherwise coach gets their own data
        if athlete_id:
            sessions = self.get_sessions_by_athlete(athlete_id, account_id)
        else:
            if principal and getattr(principal, "role", "coach") == "admin":
                sessions = self.get_all_sessions(principal)
            else:
                sessions = self.get_sessions_by_account(account_id)
        rows = []
        for s in sessions:
            dt_parts = s.analysis_timestamp.split("T")
            date_str = dt_parts[0]
            time_str = dt_parts[1][:5] if len(dt_parts) > 1 else "00:00"
            rows.append({
                "SessionID": s.session_id,
                "AthleteID": s.athlete_id,
                "Date": date_str,
                "Time": time_str,
                "Score": s.performance_score,
                "Confidence": s.scientific_confidence,
                "Cycles": s.completed_cycles,
                "Stroke": s.stroke_type
            })
        return pd.DataFrame(rows)

    def delete_session(self, session_id: str, account_id: str) -> bool:
        """Delete an analysis session by ID, enforcing strict account ownership."""
        if not account_id:
            logger.warning(f"Security: Missing account_id for delete operation on {session_id}")
            raise ValueError("account_id is required")
            
        success = self.repository.delete_by_id_and_account_id(session_id, account_id)
        if success:
            logger.info(f"Deleted analysis session: {session_id}")
        else:
            logger.error(f"Error deleting analysis session {session_id}")
        return success


