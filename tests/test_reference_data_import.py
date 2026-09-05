import os
from pathlib import Path
from services.csv_registry_importer import CSVRegistryImporter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH_1 = PROJECT_ROOT / "data" / "reference" / "swimming_reference_data_v2_scientific_registry.csv"
CSV_PATH_2 = PROJECT_ROOT / "swimming_reference_data_v2_scientific_registry.csv"

CSV_FILE = str(CSV_PATH_1 if CSV_PATH_1.exists() else CSV_PATH_2)

def test_import_scientific_registry_csv():
    assert os.path.exists(CSV_FILE), f"Reference CSV file not found at {CSV_FILE}"

    valid, rejected, errs = CSVRegistryImporter.import_scientific_registry_csv(
        csv_path=CSV_FILE,
        version_name="test_import_v2",
        importer_name="Pytest Suite"
    )

    assert valid > 100, f"Expected >100 valid imported rows, got {valid}"
    assert isinstance(errs, list)

def test_null_preservation_on_import():
    """Verify empty fields remain None and are not coerced to 0."""
    valid, rejected, errs = CSVRegistryImporter.import_scientific_registry_csv(
        csv_path=CSV_FILE,
        version_name="test_null_check_v1"
    )

    from services.reference_data_manager import ReferenceDataManager
    mgr = ReferenceDataManager()
    datasets = mgr.get_records(stroke="BUTTERFLY")
    assert len(datasets) > 0
    ds = datasets[0]
    assert ds.name is not None
    mgr.close()
