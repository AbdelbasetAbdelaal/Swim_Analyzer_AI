"""
Tests for Dataset Versioning and Activation/Deactivation.
"""

import pytest
from services.reference_data_manager import ReferenceDataManager
from models.reference_data_models import ReferenceDataset, ReferenceDatasetVersion

@pytest.fixture
def manager():
    mgr = ReferenceDataManager()
    yield mgr
    mgr.close()

def test_version_activation_deactivation(manager):
    version_name = "test_version_toggle_v1"
    ds = ReferenceDataset(
        name="Versioned Dataset",
        stroke="BUTTERFLY",
        dataset_version=version_name,
        is_active=True
    )
    class MockPrincipal:
        role = "admin"
    admin = MockPrincipal()
    manager.create_record(admin, ds)

    v_info = ReferenceDatasetVersion(
        version_name=version_name,
        filename="test.csv",
        record_count=1,
        valid_count=1,
        is_active=True
    )
    manager._repo.save_dataset_version(v_info)

    # Deactivate version
    manager.deactivate_dataset_version(admin, version_name)
    active_records = manager.get_records(stroke="BUTTERFLY", include_inactive=False)
    assert not any(d.name == "Versioned Dataset" for d in active_records)

    # Re-activate version
    manager.activate_dataset_version(admin, version_name)
    active_records_after = manager.get_records(stroke="BUTTERFLY", include_inactive=False)
    assert any(d.name == "Versioned Dataset" for d in active_records_after)
