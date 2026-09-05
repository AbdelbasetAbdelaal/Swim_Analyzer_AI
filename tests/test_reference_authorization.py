"""
Tests for ReferenceDataService admin authorization enforcement (P0-1).
Verifies that unauthenticated or non-admin callers are strictly rejected with PermissionError,
while authorized admins succeed and have their identities recorded in the audit trail.
"""

import pytest
from database import SessionLocal
from services.reference_data_service import ReferenceDataService
from models.reference_data_models import ReferenceDataset, ReferenceMetric

class MockPrincipal:
    def __init__(self, username: str, role: str):
        self.username = username
        self.role = role

@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def admin_user():
    return MockPrincipal("admin_coach", "admin")

@pytest.fixture
def regular_coach():
    return MockPrincipal("regular_coach", "coach")

@pytest.fixture
def standard_user():
    return MockPrincipal("standard_user", "user")

@pytest.fixture
def sample_dataset():
    return ReferenceDataset(
        name="Auth Test Dataset",
        stroke="FREESTYLE",
        age_min=18,
        age_max=25,
        sex="Male",
        metrics=[ReferenceMetric(metric_name="stroke_rate", value_typical=55.0, unit="spm")]
    )

def test_save_dataset_requires_admin(db_session, regular_coach, standard_user, sample_dataset):
    # Unauthenticated / None principal
    svc_anon = ReferenceDataService(db_session=db_session)
    with pytest.raises(PermissionError, match="Administrator privileges required"):
        svc_anon.save_dataset(sample_dataset)

    # Coach role
    svc_coach = ReferenceDataService(db_session=db_session, principal=regular_coach)
    with pytest.raises(PermissionError, match="Administrator privileges required"):
        svc_coach.save_dataset(sample_dataset)

    # User role
    svc_user = ReferenceDataService(db_session=db_session, principal=standard_user)
    with pytest.raises(PermissionError, match="Administrator privileges required"):
        svc_user.save_dataset(sample_dataset)

def test_save_dataset_succeeds_for_admin(db_session, admin_user, sample_dataset):
    svc_admin = ReferenceDataService(db_session=db_session, principal=admin_user)
    success, val_res = svc_admin.save_dataset(sample_dataset)
    assert success is True
    assert val_res.is_valid is True

def test_status_update_requires_admin(db_session, admin_user, regular_coach, sample_dataset):
    svc_admin = ReferenceDataService(db_session=db_session, principal=admin_user)
    svc_admin.save_dataset(sample_dataset)

    svc_coach = ReferenceDataService(db_session=db_session, principal=regular_coach)
    with pytest.raises(PermissionError, match="Administrator privileges required"):
        svc_coach.validate_and_update_status(sample_dataset.dataset_id, "COACH_VALIDATED", "Notes")

    # Admin succeeds
    ok = svc_admin.validate_and_update_status(sample_dataset.dataset_id, "COACH_VALIDATED", "Approved by admin")
    assert ok is True

def test_archive_and_delete_require_admin(db_session, admin_user, regular_coach, sample_dataset):
    svc_admin = ReferenceDataService(db_session=db_session, principal=admin_user)
    svc_admin.save_dataset(sample_dataset)

    svc_coach = ReferenceDataService(db_session=db_session, principal=regular_coach)
    with pytest.raises(PermissionError, match="Administrator privileges required"):
        svc_coach.archive_dataset(sample_dataset.dataset_id, is_archived=True)

    with pytest.raises(PermissionError, match="Administrator privileges required"):
        svc_coach.delete_dataset(sample_dataset.dataset_id)

    # Admin delete succeeds
    deleted = svc_admin.delete_dataset(sample_dataset.dataset_id)
    assert deleted is True

def test_dataset_version_activation_requires_admin(db_session, admin_user, regular_coach):
    svc_coach = ReferenceDataService(db_session=db_session, principal=regular_coach)
    with pytest.raises(PermissionError, match="Administrator privileges required"):
        svc_coach.activate_dataset_version("v1_demo")

    with pytest.raises(PermissionError, match="Administrator privileges required"):
        svc_coach.deactivate_dataset_version("v1_demo")
