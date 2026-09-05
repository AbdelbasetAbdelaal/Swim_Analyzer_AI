"""
Tests for audit event logging and repository CRUD operations.
"""

import pytest
from database import SessionLocal, engine, Base
from database.reference_repository import ReferenceDataRepository
from models.reference_data_models import ReferenceDataset, ReferenceMetric

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    db.close()

def test_audit_event_logging_on_save_and_archive(db_session):
    repo = ReferenceDataRepository(db_session)

    ds = ReferenceDataset(
        name="Audit Test Dataset",
        stroke="FREESTYLE",
        age_min=18,
        age_max=25,
        sex="Male",
        metrics=[ReferenceMetric(metric_name="stroke_rate", value_typical=55.0)]
    )

    success = repo.save_dataset(ds, user="Coach Audit Tester")
    assert success is True

    fetched = repo.get_dataset(ds.dataset_id)
    assert fetched is not None
    assert fetched.name == "Audit Test Dataset"
    assert len(fetched.validation_events) >= 1
    assert fetched.validation_events[0].action == "CREATE"
    assert fetched.validation_events[0].user == "Coach Audit Tester"

    # Archive dataset
    repo.archive_dataset(ds.dataset_id, is_archived=True, user="Coach Audit Tester")
    fetched_archived = repo.get_dataset(ds.dataset_id)
    assert fetched_archived.is_archived is True
    assert len(fetched_archived.validation_events) >= 2
    assert fetched_archived.validation_events[-1].action == "ARCHIVE"
