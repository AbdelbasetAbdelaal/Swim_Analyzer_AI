import pytest
import os
import hashlib
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
def clean_repo(setup_db):
    db = SessionLocal()
    repo = CoachRepository(db)
    # cleanup test coach if exists
    test_coach = repo.get_by_username("migration_test")
    if test_coach:
        repo.delete(test_coach.coach_id)
    yield repo
    db.close()

def test_argon2_fallback_prevention():
    # If argon2 is installed, hash_password must work
    # If not, it raises RuntimeError
    try:
        from argon2 import PasswordHasher
        has_argon2 = True
    except ImportError:
        has_argon2 = False

    if has_argon2:
        pwd_hash, salt = AuthService.hash_password("password123")
        assert pwd_hash.startswith("$argon2")
        assert salt == ""
    else:
        with pytest.raises(RuntimeError):
            AuthService.hash_password("password123")

def test_auth_migration_pbkdf2_to_argon2(clean_repo):
    # Manually create a PBKDF2 hash coach
    salt_bytes = os.urandom(16)
    salt_hex = salt_bytes.hex()
    hash_bytes = hashlib.pbkdf2_hmac('sha256', b'testpass', salt_bytes, 100000)
    pbkdf2_hash = hash_bytes.hex()
    
    coach = CoachProfile(
        username="migration_test",
        password_hash=pbkdf2_hash,
        salt=salt_hex,
        full_name="Migration Test",
        role="coach"
    )
    clean_repo.add(coach)
    
    # 1. Verify wrong password fails and leaves hash alone
    success, msg, c = AuthService.login("migration_test", "wrongpass")
    assert not success
    assert msg == "Invalid username or password."
    db_coach = clean_repo.get_by_username("migration_test")
    assert db_coach.password_hash == pbkdf2_hash
    
    # 2. Verify correct password works and upgrades hash
    success, msg, c = AuthService.login("migration_test", "testpass")
    assert success
    
    # check if argon2 is present
    try:
        import argon2
        has_argon2 = True
    except ImportError:
        has_argon2 = False
        
    if has_argon2:
        # upgraded
        db_coach = clean_repo.get_by_username("migration_test")
        assert db_coach.password_hash.startswith("$argon2")
        assert db_coach.salt == ""
        
        # 3. Verify Argon2 login works
        success2, msg2, c2 = AuthService.login("migration_test", "testpass")
        assert success2
        
        # 4. Verify Argon2 wrong pass fails
        success3, msg3, c3 = AuthService.login("migration_test", "wrongpass")
        assert not success3
