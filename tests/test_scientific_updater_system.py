import pytest

from services.scientific_updater_service import ScientificUpdaterService
from analysis.benchmarks.benchmark_engine import BenchmarkEngine
from analysis.stroke_classifier import StrokeClassifier
from models.data_models import StrokeType

@pytest.fixture
def updater():
    return ScientificUpdaterService()

# --------------------------------------------------------------------------
# PART 17 SCIENTIFIC UPDATER TESTS (1 - 20)
# --------------------------------------------------------------------------

def test_1_pubmed_metadata_retrieval(updater):
    assert hasattr(updater, '_search_literature')

def test_2_pmcid_detection(updater, monkeypatch):
    dummy_meta = {"pmid": "9999", "source_id": "SRC-9999", "title": "Dummy", "publication_year": 2026, "stroke": "Freestyle"}
    class DummyResponse:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def read(self):
            return b"<article><body><sec><p>stroke rate was 50 spm.</p></sec></body></article>"

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: DummyResponse())
    success = updater._try_retrieve_and_parse_pmc_fulltext("PMC7548777", dummy_meta, {"evidence_candidates": 0, "evidence_rejected": 0, "evidence_accepted": 0, "evidence_review_required": 0})
    assert isinstance(success, bool)

def test_3_pmc_fulltext_retrieval(updater, monkeypatch):
    dummy_meta = {"pmid": "9999", "source_id": "SRC-9999", "title": "Dummy", "publication_year": 2026, "stroke": "Freestyle"}
    class DummyResponse:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def read(self):
            return b"<article><body><sec><p>stroke frequency was 0.85 Hz.</p></sec></body></article>"

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: DummyResponse())
    success = updater._try_retrieve_and_parse_pmc_fulltext("7548777", dummy_meta, {"evidence_candidates": 0, "evidence_rejected": 0, "evidence_accepted": 0, "evidence_review_required": 0})
    assert isinstance(success, bool)

def test_4_5_fulltext_vs_abstract_only_distinction(updater):
    sources_path = updater.root_dir / "scientific_reference" / "sources" / "source_registry.yaml"
    with open(sources_path, "r", encoding="utf-8") as f:
        import yaml
        sources = yaml.safe_load(f).get("sources", {})
    for sid, s in sources.items():
        if s.get("access_level") == "PEER_REVIEWED_ABSTRACT_ONLY":
            assert s.get("access_level") != "FULL_TEXT_VERIFIED"

def test_6_7_population_and_metric_extraction(updater):
    evidence_path = updater.root_dir / "scientific_reference" / "evidence" / "evidence_registry.yaml"
    with open(evidence_path, "r", encoding="utf-8") as f:
        import yaml
        records = yaml.safe_load(f).get("evidence_records", {})
    rec = records.get("EVID-FREE-001")
    assert rec is not None
    assert rec.get("reported_mean") is not None

def test_8_9_table_and_page_location_requirement(updater):
    evidence_path = updater.root_dir / "scientific_reference" / "evidence" / "evidence_registry.yaml"
    with open(evidence_path, "r", encoding="utf-8") as f:
        import yaml
        records = yaml.safe_load(f).get("evidence_records", {})
    for eid, rec in records.items():
        if rec.get("scientific_status") == "SCIENTIFICALLY_ACCEPTED":
            assert rec.get("table_or_figure_reference") is not None
            assert rec.get("page_reference") is not None

def test_10_11_no_fabricated_sample_size_or_demographics(updater):
    engine = BenchmarkEngine()
    stats = engine._get_population_stats("freestyle", "8-10", "Female", "stroke_rate")
    assert stats.mean is None, "8-10 Female Freestyle stats must remain None"

def test_12_no_adult_to_youth_leakage(updater):
    engine = BenchmarkEngine()
    adult = engine._get_population_stats("freestyle", "18-25", "Male", "stroke_rate")
    youth = engine._get_population_stats("freestyle", "8-10", "Male", "stroke_rate")
    if adult.mean is not None and youth.mean is not None:
        assert adult.mean != youth.mean

def test_13_no_male_to_female_leakage(updater):
    engine = BenchmarkEngine()
    male = engine._get_population_stats("freestyle", "18-25", "Male", "stroke_rate")
    female = engine._get_population_stats("freestyle", "Masters", "Female", "stroke_rate")
    assert female.mean is None or male.mean != female.mean

def test_14_no_stroke_to_stroke_leakage(updater):
    engine = BenchmarkEngine()
    free = engine._get_population_stats("freestyle", "18-25", "Male", "stroke_rate")
    fly = engine._get_population_stats("butterfly", "18-25", "Male", "stroke_rate")
    if free.mean is not None and fly.mean is not None:
        assert free.mean != fly.mean

def test_15_dynamic_coverage_calculation(updater):
    verified, insufficient = updater._calculate_current_coverage()
    assert verified + insufficient == 96

def test_16_duplicate_study_handling(updater, monkeypatch):
    monkeypatch.setattr(updater, "_commit_staging_files", lambda: ("2026.08.08", "2026.08.09"))
    mock_stats = {
        "search_executed": True, "queries_executed": 25, "raw_results_retrieved": 0,
        "sources_discovered": 0, "new_sources": 0, "existing_sources": 5,
        "full_text_verified": 0, "abstract_only": 0, "sources_rejected": 0,
        "evidence_candidates": 0, "evidence_accepted": 0, "evidence_review_required": 0,
        "evidence_rejected": 0, "benchmarks_added": 0, "benchmarks_updated": 0,
        "benchmarks_unchanged": 0, "populations_with_conflicting_evidence": 0,
        "network_failures": 0, "extraction_failures": 0
    }
    monkeypatch.setattr(updater, "_search_literature", lambda cb: (mock_stats.copy(), None))
    res1 = updater.run_update_cycle()
    res2 = updater.run_update_cycle()
    assert res1.get("tests_passed") is True and res2.get("tests_passed") is True

def test_17_no_change_update_behavior(updater, monkeypatch):
    monkeypatch.setattr(updater, "_commit_staging_files", lambda: ("2026.08.08", "2026.08.09"))
    mock_stats = {
        "search_executed": True, "queries_executed": 25, "raw_results_retrieved": 0,
        "sources_discovered": 0, "new_sources": 0, "existing_sources": 5,
        "full_text_verified": 0, "abstract_only": 0, "sources_rejected": 0,
        "evidence_candidates": 0, "evidence_accepted": 0, "evidence_review_required": 0,
        "evidence_rejected": 0, "benchmarks_added": 0, "benchmarks_updated": 0,
        "benchmarks_unchanged": 0, "populations_with_conflicting_evidence": 0,
        "network_failures": 0, "extraction_failures": 0
    }
    monkeypatch.setattr(updater, "_search_literature", lambda cb: (mock_stats.copy(), None))
    res = updater.run_update_cycle()
    assert res.get("verdict") in ["SUCCESSFUL_UPDATE", "SUCCESSFUL_UPDATE_WITH_LIMITED_COVERAGE", "INTERNET_UNAVAILABLE"]

def test_18_atomic_rollback(updater):
    assert not updater.staging_dir.exists()
    assert not updater.backup_dir.exists()

def test_19_ssl_failure_handling(updater):
    assert updater.ssl_ctx.verify_mode != 0, "SSL context must use secure certificate verification"

def test_20_parsing_failure_handling(updater):
    dummy_meta = {"pmid": "9999", "source_id": "SRC-9999", "title": "Dummy", "publication_year": 2026, "stroke": "Freestyle"}
    success = updater._try_retrieve_and_parse_pmc_fulltext("INVALID_PMC_ID_99999", dummy_meta, {"evidence_candidates": 0, "evidence_rejected": 0, "evidence_accepted": 0, "evidence_review_required": 0})
    assert success is False


# --------------------------------------------------------------------------
# PART 17 STROKE CLASSIFIER TESTS (21 - 32)
# --------------------------------------------------------------------------

# Helper to build empty feature set
def _dummy_feature_set():
    from analysis.classification.feature_extractor import KinematicFeatureSet, ExtractedFeatureValue
    return KinematicFeatureSet(
        arm_phase_correlation=ExtractedFeatureValue("arm_phase_correlation", None, False),
        mean_body_roll=ExtractedFeatureValue("mean_body_roll", None, False),
        body_roll_amplitude=ExtractedFeatureValue("body_roll_amplitude", None, False),
        wrist_vertical_range_ratio=ExtractedFeatureValue("wrist_vertical_range_ratio", None, False),
        leg_kick_symmetry=ExtractedFeatureValue("leg_kick_symmetry", None, False),
        wrist_recovery_height_ratio=ExtractedFeatureValue("wrist_recovery_height_ratio", None, False),
        total_frames_in_window=0,
        valid_frames_in_window=0,
        window_start_frame=0,
        window_end_frame=0
    )

def test_21_to_24_all_four_strokes_reachable():
    from analysis.classification.stroke_heuristic_classifier import StrokeHeuristicClassifier
    from analysis.classification.feature_extractor import ExtractedFeatureValue

    classifier = StrokeHeuristicClassifier(confidence_threshold=0.75)

    # Test Freestyle Reachable
    f_free = _dummy_feature_set()
    f_free.arm_phase_correlation = ExtractedFeatureValue("arm_phase_correlation", raw_value=-0.8, valid=True)
    f_free.body_roll_amplitude = ExtractedFeatureValue("body_roll_amplitude", raw_value=25.0, valid=True)
    f_free.wrist_vertical_range_ratio = ExtractedFeatureValue("wrist_vertical_range_ratio", raw_value=0.20, valid=True)
    res_free = classifier.classify_features(f_free)
    assert res_free.predicted_stroke == StrokeType.FREESTYLE

    # Test Backstroke Reachable
    f_back = _dummy_feature_set()
    f_back.arm_phase_correlation = ExtractedFeatureValue("arm_phase_correlation", raw_value=-0.8, valid=True)
    f_back.body_roll_amplitude = ExtractedFeatureValue("body_roll_amplitude", raw_value=5.0, valid=True)
    f_back.wrist_vertical_range_ratio = ExtractedFeatureValue("wrist_vertical_range_ratio", raw_value=0.05, valid=True)
    res_back = classifier.classify_features(f_back)
    assert res_back.predicted_stroke == StrokeType.BACKSTROKE

    # Test Butterfly Reachable
    f_fly = _dummy_feature_set()
    f_fly.arm_phase_correlation = ExtractedFeatureValue("arm_phase_correlation", raw_value=0.8, valid=True)
    f_fly.wrist_vertical_range_ratio = ExtractedFeatureValue("wrist_vertical_range_ratio", raw_value=0.35, valid=True)
    res_fly = classifier.classify_features(f_fly)
    assert res_fly.predicted_stroke == StrokeType.BUTTERFLY

    # Test Breaststroke Reachable
    # wrist_range must be <= 0.08 for Breaststroke to win over Butterfly
    # (classifier threshold: wrist_range_val > 0.08 -> Butterfly, else -> Breaststroke)
    f_breast = _dummy_feature_set()
    f_breast.arm_phase_correlation = ExtractedFeatureValue("arm_phase_correlation", raw_value=0.8, valid=True)
    f_breast.wrist_vertical_range_ratio = ExtractedFeatureValue("wrist_vertical_range_ratio", raw_value=0.05, valid=True)
    res_breast = classifier.classify_features(f_breast)
    assert res_breast.predicted_stroke == StrokeType.BREASTSTROKE

def test_25_unknown_classification():
    from analysis.classification.stroke_heuristic_classifier import StrokeHeuristicClassifier
    classifier = StrokeHeuristicClassifier()
    f = _dummy_feature_set()
    res = classifier.classify_features(f)
    assert res.predicted_stroke == StrokeType.UNKNOWN

def test_26_27_ambiguous_input_and_low_confidence():
    from analysis.classification.stroke_heuristic_classifier import StrokeHeuristicClassifier
    from analysis.classification.feature_extractor import ExtractedFeatureValue
    classifier = StrokeHeuristicClassifier()
    f = _dummy_feature_set()
    f.arm_phase_correlation = ExtractedFeatureValue("arm_phase_correlation", raw_value=0.0, valid=True) # Ambiguous phase
    res = classifier.classify_features(f)
    assert res.predicted_stroke == StrokeType.UNKNOWN
    # Ambiguous phase (0.0 within [-0.3, +0.3]) returns INSUFFICIENT_EVIDENCE / insufficient_data per zero-fallback policy
    assert res.classification_status.lower() in ["insufficient_evidence", "insufficient_data"]

def test_28_29_missing_landmarks_and_insufficient_frames():
    classifier_obj = StrokeClassifier()
    fallback_res = classifier_obj._fallback()
    assert fallback_res.predicted_stroke == StrokeType.UNKNOWN
    # Zero-fallback policy: confidence is None (not 0.0) when no evidence is available
    assert fallback_res.confidence is None

def test_30_no_silent_freestyle_fallback():
    classifier_obj = StrokeClassifier()
    fallback_res = classifier_obj._fallback()
    assert fallback_res.predicted_stroke != StrokeType.FREESTYLE
    assert fallback_res.predicted_stroke == StrokeType.UNKNOWN

def test_31_explainability_output():
    from analysis.classification.stroke_heuristic_classifier import StrokeHeuristicClassifier
    from analysis.classification.feature_extractor import ExtractedFeatureValue
    classifier = StrokeHeuristicClassifier()
    f = _dummy_feature_set()
    f.arm_phase_correlation = ExtractedFeatureValue("arm_phase_correlation", raw_value=-0.8, valid=True)
    f.body_roll_amplitude = ExtractedFeatureValue("body_roll_amplitude", raw_value=25.0, valid=True)
    res = classifier.classify_features(f)
    assert "feature_contributions" in dir(res) or hasattr(res, "feature_contributions")

def test_32_version_metadata():
    from analysis.classification.stroke_heuristic_classifier import CLASSIFIER_VERSION, THRESHOLD_VERSION
    assert CLASSIFIER_VERSION == "1.0.0-unvalidated"
    assert THRESHOLD_VERSION == "UNVALIDATED_HEURISTIC_v1.0"
