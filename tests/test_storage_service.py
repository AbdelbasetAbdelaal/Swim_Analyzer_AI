"""
Unit tests for StorageRetentionService.
"""
import time
from pathlib import Path
import pytest
from services.storage_service import StorageRetentionService

def test_storage_stats_retrieval(tmp_path, monkeypatch):
    test_dir = tmp_path / "test_videos"
    test_dir.mkdir()
    
    # Create sample files
    f1 = test_dir / "sample1.mp4"
    f1.write_bytes(b"0" * 1024) # 1 KB
    f2 = test_dir / "sample2.mp4"
    f2.write_bytes(b"0" * 2048) # 2 KB

    monkeypatch.setattr(StorageRetentionService, "TARGET_DIRECTORIES", [test_dir])
    
    stats = StorageRetentionService.get_storage_stats()
    assert stats["total_files"] == 2
    assert stats["total_bytes"] == 3072

def test_storage_cleanup_stale_files(tmp_path, monkeypatch):
    test_dir = tmp_path / "test_reports"
    test_dir.mkdir()

    fresh_file = test_dir / "fresh.json"
    fresh_file.write_text("fresh content")

    stale_file = test_dir / "stale.json"
    stale_file.write_text("stale content")

    # Set stale mtime to 10 days ago
    past_mtime = time.time() - (10 * 86400)
    import os
    os.utime(stale_file, (past_mtime, past_mtime))

    monkeypatch.setattr(StorageRetentionService, "TARGET_DIRECTORIES", [test_dir])

    # Run cleanup with 7-day threshold
    res = StorageRetentionService.cleanup_stale_artifacts(max_age_days=7)
    
    assert res["deleted_files_count"] == 1
    assert not stale_file.exists()
    assert fresh_file.exists()
