from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from database.database import Base

class CoachModel(Base):
    __tablename__ = "coaches"

    coach_id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="coach")
    email = Column(String, nullable=True)
    created_at = Column(String, nullable=False)

    athletes = relationship("AthleteModel", back_populates="coach", cascade="all, delete-orphan")


class AthleteModel(Base):
    __tablename__ = "athletes"

    athlete_id = Column(String, primary_key=True, index=True)
    coach_id = Column(String, ForeignKey("coaches.coach_id"), nullable=True, index=True)
    full_name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    shoulder_width_cm = Column(Float, nullable=True)
    swimming_level = Column(String, nullable=False)
    preferred_stroke = Column(String, nullable=False)
    notes = Column(String, nullable=True)
    training_goals = Column(Text, default="")

    coach = relationship("CoachModel", back_populates="athletes")
    analyses = relationship("AnalysisSessionModel", back_populates="athlete", cascade="all, delete-orphan")


class AnalysisSessionModel(Base):
    __tablename__ = "analysis_sessions"

    session_id = Column(String, primary_key=True, index=True)
    athlete_id = Column(String, ForeignKey("athletes.athlete_id"), nullable=True, index=True)
    account_id = Column(String, nullable=True, index=True)
    
    analysis_timestamp = Column(String, nullable=False)
    original_video_filename = Column(String, nullable=False)
    processed_video_filename = Column(String, nullable=False)
    metadata_json_path = Column(String, nullable=False)
    report_json_path = Column(String, nullable=False)
    
    performance_score = Column(Float, nullable=False)
    scientific_confidence = Column(String, nullable=False)
    completed_cycles = Column(Integer, nullable=False)
    stroke_type = Column(String, nullable=False)
    processing_time_seconds = Column(Float, nullable=False)
    benchmark_summary_json = Column(Text, nullable=True)

    athlete = relationship("AthleteModel", back_populates="analyses")


class ReferenceDatasetModel(Base):
    __tablename__ = "reference_datasets"

    dataset_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True, default="")
    stroke = Column(String, nullable=False, default="FREESTYLE", index=True)
    age_min = Column(Integer, nullable=True, default=0)
    age_max = Column(Integer, nullable=True, default=100)
    sex = Column(String, nullable=True, default="Mixed")
    skill_level = Column(String, nullable=True, default="Unknown")
    athlete_category = Column(String, nullable=True, default="Adult")
    training_level = Column(String, nullable=True, default="")
    
    source_type = Column(String, nullable=False, default="COACH_DEFINED")
    evidence_status = Column(String, nullable=False, default="INSUFFICIENT_EVIDENCE")
    benchmark_eligibility = Column(String, nullable=False, default="CONTEXT_ONLY")
    benchmark_priority = Column(String, nullable=False, default="P2")  # P0, P1, P2, P3
    validation_status = Column(String, nullable=False, default="DRAFT")
    is_archived = Column(Integer, nullable=False, default=0)
    is_active = Column(Integer, nullable=False, default=1)
    dataset_version = Column(String, nullable=False, default="manual_reference_v1", index=True)
    
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    metrics = relationship("ReferenceMetricModel", back_populates="dataset", cascade="all, delete-orphan")
    sources = relationship("ReferenceSourceModel", back_populates="dataset", cascade="all, delete-orphan")
    validation_events = relationship("ReferenceValidationEventModel", back_populates="dataset", cascade="all, delete-orphan")


class ReferenceMetricModel(Base):
    __tablename__ = "reference_metrics"

    metric_id = Column(String, primary_key=True, index=True)
    dataset_id = Column(String, ForeignKey("reference_datasets.dataset_id"), nullable=False, index=True)
    
    metric_name = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    value_min = Column(Float, nullable=True)
    value_typical = Column(Float, nullable=True)
    value_median = Column(Float, nullable=True)
    value_max = Column(Float, nullable=True)
    uncertainty_sd = Column(Float, nullable=True)
    unit = Column(String, nullable=True, default="")
    measurement_domain = Column(String, nullable=False, default="UNAVAILABLE")
    status = Column(String, nullable=False, default="unavailable")
    method = Column(String, nullable=True, default="")
    notes = Column(Text, nullable=True, default="")
    
    event_distance = Column(String, nullable=True, default="")
    course = Column(String, nullable=True, default="")
    evidence_grade = Column(String, nullable=True, default="")
    context_only_reason = Column(Text, nullable=True, default="")
    population_match_required = Column(Text, nullable=True, default="")

    dataset = relationship("ReferenceDatasetModel", back_populates="metrics")


class ReferenceSourceModel(Base):
    __tablename__ = "reference_sources"

    source_id = Column(String, primary_key=True, index=True)
    dataset_id = Column(String, ForeignKey("reference_datasets.dataset_id"), nullable=False, index=True)
    
    source_type = Column(String, nullable=False, default="UNKNOWN")
    source_title = Column(Text, nullable=True, default="")
    authors = Column(Text, nullable=True, default="")
    publication_year = Column(Integer, nullable=True)
    doi = Column(String, nullable=True, default="")
    pmid = Column(String, nullable=True, default="")
    url = Column(String, nullable=True, default="")
    sample_size = Column(Integer, nullable=True)
    population_description = Column(Text, nullable=True, default="")

    dataset = relationship("ReferenceDatasetModel", back_populates="sources")


class ReferenceValidationEventModel(Base):
    __tablename__ = "reference_validation_events"

    event_id = Column(String, primary_key=True, index=True)
    dataset_id = Column(String, ForeignKey("reference_datasets.dataset_id"), nullable=False, index=True)
    
    timestamp = Column(String, nullable=False)
    user = Column(String, nullable=False, default="Coach/Admin")
    action = Column(String, nullable=False, default="CREATE")
    old_status = Column(String, nullable=True, default="")
    new_status = Column(String, nullable=True, default="")
    notes = Column(Text, nullable=True, default="")

    dataset = relationship("ReferenceDatasetModel", back_populates="validation_events")


class ReferenceDatasetVersionModel(Base):
    __tablename__ = "reference_dataset_versions"

    version_id = Column(String, primary_key=True, index=True)
    version_name = Column(String, unique=True, nullable=False, index=True)
    filename = Column(String, nullable=False)
    imported_at = Column(String, nullable=False)
    record_count = Column(Integer, nullable=False, default=0)
    valid_count = Column(Integer, nullable=False, default=0)
    rejected_count = Column(Integer, nullable=False, default=0)
    is_active = Column(Integer, nullable=False, default=1)
    importer = Column(String, nullable=False, default="System/Coach")


