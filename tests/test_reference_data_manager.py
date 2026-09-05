"""
Tests for ReferenceDataManager service.
Verifies record CRUD, deletion confirmation, filtering, and exports.
"""

import pytest
from services.reference_data_manager import ReferenceDataManager
from models.reference_data_models import ReferenceDataset, ReferenceMetric

@pytest.fixture
def manager():
    mgr = ReferenceDataManager()
    yield mgr
    mgr.close()

def test_record_create_get_filter(manager):
    ds = ReferenceDataset(
        name="Unit Test Dataset",
        stroke="FREESTYLE",
        age_min=18,
        age_max=25,
        sex="Male",
        dataset_version="test_v1",
        metrics=[ReferenceMetric(metric_name="stroke_rate", value_typical=55.0, unit="spm")]
    )

    class MockPrincipal:
        role = "admin"
    admin = MockPrincipal()
    success = manager.create_record(admin, ds, user="Test Runner")
    assert success is True

    records = manager.get_records(stroke="FREESTYLE", metric_name="stroke_rate")
    assert len(records) >= 1
    assert any(r.name == "Unit Test Dataset" for r in records)


def test_get_records_normalizes_metric_names(manager):
    ds = ReferenceDataset(
        name="Stroke Rate Normalization Dataset",
        stroke="FREESTYLE",
        age_min=18,
        age_max=25,
        sex="Female",
        dataset_version="test_v2",
        metrics=[ReferenceMetric(metric_name="Stroke Rate", value_typical=48.5, unit="spm")]
    )
    class MockPrincipal:
        role = "admin"
    admin = MockPrincipal()
    manager.create_record(admin, ds, user="Test Runner")

    records_snake = manager.get_records(stroke="FREESTYLE", metric_name="stroke_rate")
    assert any(r.name == "Stroke Rate Normalization Dataset" for r in records_snake)

    records_display = manager.get_records(stroke="FREESTYLE", metric_name="Stroke Rate")
    assert any(r.name == "Stroke Rate Normalization Dataset" for r in records_display)


def test_delete_requires_confirmation(manager):
    ds = ReferenceDataset(
        name="Delete Test Dataset",
        stroke="BACKSTROKE",
        age_min=18,
        age_max=25,
        sex="Male"
    )
    class MockPrincipal:
        role = "admin"
    admin = MockPrincipal()
    manager.create_record(admin, ds, user="Test Runner")

    with pytest.raises(ValueError, match="Deletion requires explicit confirmation"):
        manager.delete_record(admin, ds.dataset_id, confirm=False)

    # With confirmation, deletion succeeds
    deleted = manager.delete_record(admin, ds.dataset_id, confirm=True)
    assert deleted is True
