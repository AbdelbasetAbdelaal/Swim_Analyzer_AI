from database.database import Base, engine, get_db, SessionLocal
from database.models import (
    AthleteModel, AnalysisSessionModel,
    ReferenceDatasetModel, ReferenceMetricModel, ReferenceSourceModel,
    ReferenceValidationEventModel, ReferenceDatasetVersionModel
)
from database.repository import AthleteRepository, AnalysisHistoryRepository
from sqlalchemy import inspect, text

# Create all tables in the engine.
Base.metadata.create_all(bind=engine)

# Auto-migration for SQLite columns added in updates
with engine.connect() as conn:
    inspector = inspect(engine)
    if inspector.has_table("reference_datasets"):
        cols = [c["name"] for c in inspector.get_columns("reference_datasets")]
        if "benchmark_priority" not in cols:
            conn.execute(text("ALTER TABLE reference_datasets ADD COLUMN benchmark_priority VARCHAR DEFAULT 'P2'"))
        if "is_active" not in cols:
            conn.execute(text("ALTER TABLE reference_datasets ADD COLUMN is_active INTEGER DEFAULT 1"))
        if "dataset_version" not in cols:
            conn.execute(text("ALTER TABLE reference_datasets ADD COLUMN dataset_version VARCHAR DEFAULT 'manual_reference_v1'"))

    if inspector.has_table("reference_metrics"):
        cols = [c["name"] for c in inspector.get_columns("reference_metrics")]
        if "uncertainty_sd" not in cols:
            conn.execute(text("ALTER TABLE reference_metrics ADD COLUMN uncertainty_sd FLOAT"))
        if "event_distance" not in cols:
            conn.execute(text("ALTER TABLE reference_metrics ADD COLUMN event_distance VARCHAR DEFAULT ''"))
        if "course" not in cols:
            conn.execute(text("ALTER TABLE reference_metrics ADD COLUMN course VARCHAR DEFAULT ''"))
        if "evidence_grade" not in cols:
            conn.execute(text("ALTER TABLE reference_metrics ADD COLUMN evidence_grade VARCHAR DEFAULT ''"))
        if "context_only_reason" not in cols:
            conn.execute(text("ALTER TABLE reference_metrics ADD COLUMN context_only_reason TEXT DEFAULT ''"))
        if "population_match_required" not in cols:
            conn.execute(text("ALTER TABLE reference_metrics ADD COLUMN population_match_required TEXT DEFAULT ''"))
            
    conn.commit()
