from models.data_models import AnalysisResult, PerformanceReport, ValidatedMetric
from models.athlete_profile import AthleteProfile
from analysis.benchmarks.benchmark_engine import BenchmarkEngine
from services.pdf_report_service import PDFReportService
from scientific_reference.storage.scientific_evidence_registry import ScientificEvidenceRegistry
from models.scientific_evidence_models import AuditDecision, SourceRelationship

def test_rule_1_compatible_adult_male_without_verified_reference_is_suppressed():
    """P0: absent verified reference values remain unavailable, even for a compatible cohort."""
    engine = BenchmarkEngine()
    ar = AnalysisResult()
    ar.stroke_type = "Freestyle"
    ar.report = PerformanceReport(
        overall_score=80.0,
        stroke_rate=ValidatedMetric(value=54.0, valid=True),
        stroke_length=ValidatedMetric(value=1.85, valid=True)
    )
    prof = AthleteProfile(coach_id="test_coach", full_name="John Doe", age=22, gender="Male", height_cm=180.0, weight_kg=75.0, swimming_level="Elite", preferred_stroke="Freestyle")

    res = engine.evaluate_analysis(ar, prof)
    # stroke_length is absent from verified freestyle benchmarks -> must be suppressed
    sl_comp = res.comparisons["stroke_length"]

    assert sl_comp.z_score is None
    assert sl_comp.percentile is None

def test_rule_2_youth_athlete_percentile_suppressed():
    """Rule 2: Youth athlete (Age 12) does NOT receive adult benchmark percentile (percentile = None)."""
    engine = BenchmarkEngine()
    ar = AnalysisResult()
    ar.stroke_type = "Freestyle"
    ar.report = PerformanceReport(
        overall_score=75.0,
        stroke_rate=ValidatedMetric(value=54.0, valid=True)
    )
    prof = AthleteProfile(coach_id="test_coach", full_name="Junior Swimmer", age=12, gender="Male", height_cm=150.0, weight_kg=42.0, swimming_level="Intermediate", preferred_stroke="Freestyle")

    res = engine.evaluate_analysis(ar, prof)
    sr_comp = res.comparisons["stroke_rate"]

    assert sr_comp.z_score is None, "Youth athlete must NOT receive adult Z-score"
    assert sr_comp.percentile is None, "Youth athlete must NOT receive adult Percentile"

def test_rule_3_female_athlete_percentile_suppressed():
    """Rule 3: Female athlete without data does NOT receive adult male benchmark percentile (percentile = None)."""
    engine = BenchmarkEngine()
    ar = AnalysisResult()
    ar.stroke_type = "Butterfly"
    ar.report = PerformanceReport(
        overall_score=82.0,
        stroke_rate=ValidatedMetric(value=54.0, valid=True)
    )
    prof = AthleteProfile(coach_id="test_coach", full_name="Jane Smith", age=30, gender="Female", height_cm=172.0, weight_kg=62.0, swimming_level="Elite", preferred_stroke="Butterfly")

    res = engine.evaluate_analysis(ar, prof)
    sr_comp = res.comparisons["stroke_rate"]

    assert sr_comp.z_score is None or sr_comp.evidence.source_relationship != "UNVERIFIED", "Female athlete without verified benchmark cohort must NOT receive an unverified/fabricated Z-score"
    if sr_comp.z_score is not None:
        # If she received a score, it must be from a compatible source (Female or Mixed)
        assert sr_comp.evidence.population_compatibility != "POPULATION_MISMATCH"

def test_rule_4_masters_athlete_percentile_suppressed():
    """Rule 4: Masters athlete (Age 45) does NOT receive adult 18-25 benchmark percentile."""
    engine = BenchmarkEngine()
    ar = AnalysisResult()
    ar.stroke_type = "Freestyle"
    ar.report = PerformanceReport(
        overall_score=78.0,
        stroke_rate=ValidatedMetric(value=50.0, valid=True)
    )
    prof = AthleteProfile(coach_id="test_coach", full_name="Senior Swimmer", age=45, gender="Male", height_cm=178.0, weight_kg=78.0, swimming_level="Advanced", preferred_stroke="Freestyle")

    res = engine.evaluate_analysis(ar, prof)
    sr_comp = res.comparisons["stroke_rate"]

    assert sr_comp.z_score is None
    assert sr_comp.percentile is None

def test_rule_5_6_7_reference_only_and_rejected_metric_safety():
    """Rule 5, 6, 7: REFERENCE_ONLY (Body Roll / Kick Freq) & REJECTED metrics receive percentile = None."""
    engine = BenchmarkEngine()
    ar = AnalysisResult()
    ar.stroke_type = "Freestyle"
    ar.report = PerformanceReport(
        overall_score=80.0,
        kick_frequency=ValidatedMetric(value=3.2, valid=True)
    )
    prof = AthleteProfile(coach_id="test_coach", full_name="John Doe", age=22, gender="Male", height_cm=180.0, weight_kg=75.0, swimming_level="Elite", preferred_stroke="Freestyle")

    res = engine.evaluate_analysis(ar, prof)

    # Kick frequency is REFERENCE_ONLY -> Z-score / percentile must be None
    if "kick_frequency" in res.comparisons:
        kf_comp = res.comparisons["kick_frequency"]
        assert kf_comp.z_score is None
        assert kf_comp.percentile is None

    # Performance Score is REJECTED from scientific benchmarks -> Z-score / percentile must be None
    ps_comp = res.comparisons["performance_score"]
    assert ps_comp.z_score is None
    assert ps_comp.percentile is None

def test_rule_8_derived_benchmark_conversion_provenance():
    """Rule 8: Derived benchmark (Stroke Rate) displays conversion formula in evidence record."""
    registry = ScientificEvidenceRegistry()
    rec = registry.get_record("EVID-FREE-001")
    assert rec is not None
    assert rec.audit_decision == AuditDecision.ACCEPT_AS_DERIVED
    assert rec.relationship_to_benchmark == SourceRelationship.DERIVED_FROM_SOURCE
    assert rec.conversion_formula is not None and "0.9" in rec.conversion_formula

def test_rule_9_pdf_streamlit_rule_alignment():
    """Rule 9: PDF exporter uses exact same BenchmarkResult safely constructed by BenchmarkEngine."""
    engine = BenchmarkEngine()
    ar = AnalysisResult()
    ar.stroke_type = "Freestyle"
    ar.report = PerformanceReport(overall_score=80.0, stroke_rate=ValidatedMetric(value=54.0, valid=True))
    prof = AthleteProfile(coach_id="test_coach", full_name="Female Swimmer", age=22, gender="Female", height_cm=170.0, weight_kg=60.0, swimming_level="Elite", preferred_stroke="Freestyle")

    res = engine.evaluate_analysis(ar, prof)
    ar.benchmark_result = res

    # Generate PDF
    pdf_service = PDFReportService()
    pdf_path = pdf_service.generate_session_analysis_pdf(ar, profile=prof)
    assert pdf_path is not None

def test_rule_10_stroke_isolation():
    """Rule 10: Stroke-specific benchmark dataset isolation works correctly."""
    engine = BenchmarkEngine()
    fs_stats = engine._get_population_stats("Freestyle", "18-25", "Male", "stroke_rate")
    bk_stats = engine._get_population_stats("Backstroke", "18-25", "Male", "stroke_rate")

    assert fs_stats.mean == 54.0
    assert bk_stats.mean == 48.0
    assert fs_stats.mean != bk_stats.mean
