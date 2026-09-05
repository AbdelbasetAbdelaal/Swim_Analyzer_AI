import pytest
from unittest.mock import patch, MagicMock
from app.ui.dashboard import render_dashboard_page
from models.coach_profile import CoachProfile
from models.athlete_profile import AthleteProfile
from models.analysis_session import AnalysisSession
from services.analysis_history_service import AnalysisHistoryService
from services.athlete_service import AthleteService

def test_dashboard_coach_role_invokes_get_sessions_by_account():
    with patch('app.ui.dashboard.st') as mock_st, \
         patch('app.ui.dashboard.AthleteService') as MockAthleteService, \
         patch('app.ui.dashboard.AnalysisHistoryService') as MockHistoryService:

        mock_coach = MagicMock()
        mock_coach.coach_id = "test_coach_id"
        mock_coach.role = "coach"
        mock_st.session_state.get.return_value = mock_coach

        mock_athlete_instance = MockAthleteService.return_value
        mock_athlete_instance.get_all_profiles.return_value = []

        mock_history_instance = MockHistoryService.return_value
        mock_history_instance.get_sessions_by_account.return_value = []

        render_dashboard_page()

        mock_athlete_instance.get_all_profiles.assert_called_once_with(coach_id="test_coach_id")
        mock_history_instance.get_sessions_by_account.assert_called_once_with(account_id="test_coach_id")
        mock_history_instance.get_all_sessions.assert_not_called()

def test_dashboard_admin_role_invokes_get_all_sessions():
    with patch('app.ui.dashboard.st') as mock_st, \
         patch('app.ui.dashboard.AthleteService') as MockAthleteService, \
         patch('app.ui.dashboard.AnalysisHistoryService') as MockHistoryService:

        mock_admin = MagicMock()
        mock_admin.coach_id = "test_admin_id"
        mock_admin.role = "admin"
        mock_st.session_state.get.return_value = mock_admin

        mock_athlete_instance = MockAthleteService.return_value
        mock_athlete_instance.get_all_profiles.return_value = []

        mock_history_instance = MockHistoryService.return_value
        mock_history_instance.get_all_sessions.return_value = []

        render_dashboard_page()

        mock_athlete_instance.get_all_profiles.assert_called_once_with(coach_id="test_admin_id")
        mock_history_instance.get_all_sessions.assert_called_once_with(principal=mock_admin)
        mock_history_instance.get_sessions_by_account.assert_not_called()

def test_dashboard_in_memory_session_grouping_avoids_n_plus_one():
    with patch('app.ui.dashboard.st') as mock_st, \
         patch('app.ui.dashboard.AthleteService') as MockAthleteService, \
         patch('app.ui.dashboard.AnalysisHistoryService') as MockHistoryService:

        mock_coach = MagicMock()
        mock_coach.coach_id = "test_coach_id"
        mock_coach.role = "coach"
        mock_st.session_state.get.return_value = mock_coach

        mock_athlete = MagicMock()
        mock_athlete.athlete_id = "ath_001"
        mock_athlete.full_name = "Alex Swimmer"
        mock_athlete.swimming_level = "Elite"
        mock_athlete.preferred_stroke = "Freestyle"

        mock_athlete_instance = MockAthleteService.return_value
        mock_athlete_instance.get_all_profiles.return_value = [mock_athlete]

        mock_session = MagicMock()
        mock_session.athlete_id = "ath_001"
        mock_session.account_id = "test_coach_id"
        mock_session.performance_score = 88.5
        mock_session.analysis_timestamp = "2026-08-15T12:00:00"

        mock_history_instance = MockHistoryService.return_value
        mock_history_instance.get_sessions_by_account.return_value = [mock_session]
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_dashboard_page()

        mock_history_instance.get_sessions_by_account.assert_called_once_with(account_id="test_coach_id")
        mock_history_instance.get_all_sessions.assert_not_called()

def test_tenant_isolation_sessions_and_history(tmp_path):
    # Integration verification across Service/DB layers
    history_svc = AnalysisHistoryService()

    coach_a = CoachProfile(
        coach_id="coach_a_id",
        username="coach_a",
        full_name="Coach Alpha",
        role="coach",
        password_hash="$argon2id$mock",
        salt=""
    )
    coach_b = CoachProfile(
        coach_id="coach_b_id",
        username="coach_b",
        full_name="Coach Beta",
        role="coach",
        password_hash="$argon2id$mock",
        salt=""
    )
    admin = CoachProfile(
        coach_id="admin_id",
        username="admin_user",
        full_name="Admin User",
        role="admin",
        password_hash="$argon2id$mock",
        salt=""
    )

    # 1. Coach cannot invoke get_all_sessions
    with pytest.raises(PermissionError):
        history_svc.get_all_sessions(principal=coach_a)

    # 2. Admin can invoke get_all_sessions
    all_sessions = history_svc.get_all_sessions(principal=admin)
    assert isinstance(all_sessions, list)

def test_dashboard_coach_loads_own_athlete_sessions_successfully():
    with patch('app.ui.dashboard.st') as mock_st, \
         patch('app.ui.dashboard.AthleteService') as MockAthleteService, \
         patch('app.ui.dashboard.AnalysisHistoryService') as MockHistoryService:

        mock_coach = MagicMock(coach_id="coach_alpha", role="coach")
        mock_st.session_state.get.return_value = mock_coach

        ath1 = MagicMock(athlete_id="ath_1", full_name="Swimmer 1", swimming_level="Elite", preferred_stroke="Freestyle")
        ath2 = MagicMock(athlete_id="ath_2", full_name="Swimmer 2", swimming_level="Club", preferred_stroke="Backstroke")

        mock_athlete_instance = MockAthleteService.return_value
        mock_athlete_instance.get_all_profiles.return_value = [ath1, ath2]

        sess1 = MagicMock(athlete_id="ath_1", performance_score=92.0, analysis_timestamp="2026-08-15T10:00:00")
        sess2 = MagicMock(athlete_id="ath_2", performance_score=85.0, analysis_timestamp="2026-08-15T11:00:00")

        mock_history_instance = MockHistoryService.return_value
        mock_history_instance.get_sessions_by_account.return_value = [sess1, sess2]
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_dashboard_page()

        mock_history_instance.get_sessions_by_account.assert_called_once_with(account_id="coach_alpha")
        mock_history_instance.get_all_sessions.assert_not_called()
