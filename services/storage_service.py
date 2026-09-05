"""
Storage Retention Service for SwimAnalyzer AI.
Provides automated and on-demand pruning of stale runtime videos and reports.
"""
import time
from pathlib import Path
from typing import Dict, Any, List
from core.config import config
from core.logger import setup_logger

logger = setup_logger(__name__)

class StorageRetentionService:
    """
    Manages disk storage retention for user-uploaded videos, processed videos,
    and generated JSON/PDF reports.
    """

    TARGET_DIRECTORIES = [
        config.input_dir,
        config.output_dir,
        config.reports_dir,
        config.data_dir / "pdf_reports"
    ]

    @classmethod
    def get_storage_stats(cls) -> Dict[str, Any]:
        """Calculates file counts and total byte usage across runtime directories."""
        stats = {
            "total_files": 0,
            "total_bytes": 0,
            "directories": {}
        }
        
        for d in cls.TARGET_DIRECTORIES:
            d_path = Path(d)
            if not d_path.exists():
                continue
            
            files = [f for f in d_path.glob("*") if f.is_file()]
            dir_bytes = sum(f.stat().st_size for f in files)
            stats["directories"][d_path.name] = {
                "file_count": len(files),
                "bytes": dir_bytes,
                "mb": round(dir_bytes / (1024 * 1024), 2)
            }
            stats["total_files"] += len(files)
            stats["total_bytes"] += dir_bytes

        stats["total_mb"] = round(stats["total_bytes"] / (1024 * 1024), 2)
        return stats

    @classmethod
    def cleanup_stale_artifacts(cls, max_age_days: int = 7) -> Dict[str, Any]:
        """
        Prunes files in runtime directories that are older than max_age_days.
        Safeguards reference registries, models, and configurations.
        """
        now = time.time()
        max_age_seconds = max_age_days * 86400
        
        result = {
            "deleted_files_count": 0,
            "reclaimed_bytes": 0,
            "reclaimed_mb": 0.0,
            "errors": []
        }

        for d in cls.TARGET_DIRECTORIES:
            d_path = Path(d)
            if not d_path.exists():
                continue

            for file_path in d_path.glob("*"):
                if not file_path.is_file():
                    continue

                try:
                    file_age = now - file_path.stat().st_mtime
                    if file_age >= max_age_seconds:
                        size = file_path.stat().st_size
                        file_path.unlink()
                        result["deleted_files_count"] += 1
                        result["reclaimed_bytes"] += size
                except Exception as e:
                    err_msg = f"Failed to delete {file_path.name}: {e}"
                    logger.warning(err_msg)
                    result["errors"].append(err_msg)

        result["reclaimed_mb"] = round(result["reclaimed_bytes"] / (1024 * 1024), 2)
        logger.info(f"Storage cleanup completed: {result['deleted_files_count']} files removed, {result['reclaimed_mb']} MB reclaimed.")
        return result
