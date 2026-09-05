"""
Test suite verifying P1-12: Admin Role Creation Boundary.
Ensures that registering an account with role='admin' requires an existing admin
principal or explicit bootstrap authorization, preventing open self-assignment.
"""

import pytest
import os
import uuid
from services.auth_service import AuthService
from database.database import SessionLocal, init_db
from database.repository import CoachRepository
from models.coach_profile import CoachProfile


@pytest.fixture(scope="module")
def setup_db():
    init_db()
    yield


@pytest.fixture
def clean_users():
    created_ids = []
    db = SessionLocal()
    repo = CoachRepository(db)
    
    def register_and_track(username, password, full_name, role, **kwargs):
        success, msg, profile = AuthService.register_coach(
            username=username,
            password=password,
            full_name=full_name,
            role=role,
            **kwargs
        )
        if success and profile:
            created_ids.append(profile.coach_id)
        return success, msg, profile

    yield register_and_track

    # Cleanup
    for cid in created_ids:
        repo.delete(cid)
    db.close()


def test_unauthorized_admin_registration_fails(clean_users):
    """Attempting to register an admin without credentials or principal must fail."""
    u = f"unauth_adm_{uuid.uuid4().hex[:6]}"
    success, msg, profile = clean_users(u, "AdminSecret123", "Rogue Admin", role="admin")
    
    assert not success
    assert "Unauthorized" in msg
    assert profile is None


def test_non_admin_principal_cannot_create_admin(clean_users):
    """A regular coach principal cannot create an admin account."""
    coach_u = f"coach_{uuid.uuid4().hex[:6]}"
    ok, _, coach_profile = clean_users(coach_u, "Pass12345", "Regular Coach", role="coach")
    assert ok
    
    target_adm = f"target_adm_{uuid.uuid4().hex[:6]}"
    success, msg, profile = clean_users(
        target_adm, 
        "AdminSecret123", 
        "Elevated Admin", 
        role="admin",
        creator_principal=coach_profile
    )
    assert not success
    assert "Unauthorized" in msg
    assert profile is None


def test_authorized_admin_principal_succeeds(clean_users):
    """An existing admin principal can register a new admin account."""
    admin_u = f"adm_init_{uuid.uuid4().hex[:6]}"
    ok, _, admin_profile = clean_users(
        admin_u, 
        "RootPass123", 
        "Root Administrator", 
        role="admin",
        is_bootstrap=True
    )
    assert ok
    assert admin_profile.role == "admin"

    # New admin created by admin_profile
    new_adm = f"new_adm_{uuid.uuid4().hex[:6]}"
    success, msg, new_profile = clean_users(
        new_adm,
        "SecretAdmin456",
        "Junior Admin",
        role="admin",
        creator_principal=admin_profile
    )
    assert success
    assert new_profile is not None
    assert new_profile.role == "admin"


def test_bootstrap_token_admin_registration(clean_users, monkeypatch):
    """Valid bootstrap token allows admin creation; invalid token fails."""
    monkeypatch.setenv("SWIM_ANALYZER_BOOTSTRAP_ADMIN_TOKEN", "super-secret-token-777")
    
    # Bad token fails
    bad_u = f"bad_tok_{uuid.uuid4().hex[:6]}"
    success_bad, msg_bad, _ = clean_users(
        bad_u, "Pass123456", "Token Admin", role="admin", bootstrap_token="wrong-token"
    )
    assert not success_bad
    assert "Unauthorized" in msg_bad

    # Good token succeeds
    good_u = f"good_tok_{uuid.uuid4().hex[:6]}"
    success_good, msg_good, profile_good = clean_users(
        good_u, "Pass123456", "Token Admin", role="admin", bootstrap_token="super-secret-token-777"
    )
    assert success_good
    assert profile_good is not None
    assert profile_good.role == "admin"


def test_normal_coach_and_user_registration_unaffected(clean_users):
    """Normal user and coach registration require no elevated privileges."""
    u1 = f"user_{uuid.uuid4().hex[:6]}"
    ok1, _, p1 = clean_users(u1, "Pass12345", "Standard User", role="user")
    assert ok1
    assert p1.role == "user"

    u2 = f"coach_{uuid.uuid4().hex[:6]}"
    ok2, _, p2 = clean_users(u2, "Pass12345", "Standard Coach", role="coach")
    assert ok2
    assert p2.role == "coach"
