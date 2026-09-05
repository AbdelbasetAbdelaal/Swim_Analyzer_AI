"""
Tests for Benchmark Mean and Standard Deviation Unit Conversion (P0-4 & P1-9).
Verifies:
1. Freestyle YAML stroke_rate has converted std matching spm unit (std = 6.6, not 0.11).
2. Dispersion scaling is applied proportionally when Hz is converted to spm (factor 60).
3. ScientificUpdaterService validates that std in spm is biologically realistic (>= 1.0 spm).
4. Evidence registry records converted_std alongside converted_value.
"""

import pytest
import yaml
from pathlib import Path
from services.scientific_updater_service import ScientificUpdaterService

def test_freestyle_yaml_stroke_rate_dispersion():
    bm_path = Path("config/benchmarks/freestyle.yaml")
    assert bm_path.exists()
    with open(bm_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    male_sr = data["populations"]["Mixed"]["Male"]["stroke_rate"]
    assert male_sr["unit"] == "spm"
    assert male_sr["mean"] == 54.0
    # Must be 6.6 spm (0.11 Hz * 60 = 6.6), NOT unconverted 0.11
    assert male_sr["std"] == 6.6
    assert male_sr["std"] >= 1.0

def test_evidence_registry_contains_converted_std():
    reg_path = Path("scientific_reference/evidence/evidence_registry.yaml")
    assert reg_path.exists()
    with open(reg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    ev_record = data["evidence_records"].get("EVID-FREE-001")
    assert ev_record is not None
    assert ev_record.get("converted_unit") == "spm"
    assert ev_record.get("converted_value") == 54.0
    assert ev_record.get("converted_std") == 6.6

def test_updater_safety_check_detects_low_dispersion(tmp_path):
    # Test that safety validator catches an unscaled std (e.g. std=0.11 for mean=54.0 spm)
    updater = ScientificUpdaterService(root_dir=tmp_path)
    # Mock staging dir
    staging_bm_dir = updater.staging_dir / "benchmarks"
    staging_bm_dir.mkdir(parents=True, exist_ok=True)
    corrupt_bm = staging_bm_dir / "freestyle.yaml"
    corrupt_data = {
        "dataset_id": "BM-FREE-TEST",
        "populations": {
            "Mixed": {
                "Male": {
                    "stroke_rate": {
                        "mean": 54.0,
                        "std": 0.11,  # Unscaled!
                        "unit": "spm"
                    }
                }
            }
        }
    }
    with open(corrupt_bm, "w", encoding="utf-8") as f:
        yaml.safe_dump(corrupt_data, f)

    assert updater._run_scientific_safety_tests() is False
