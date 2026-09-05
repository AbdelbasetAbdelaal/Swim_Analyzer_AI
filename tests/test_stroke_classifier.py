import math
from models.data_models import StrokeType
from analysis.classification.feature_extractor import KinematicFeatureExtractor
from analysis.classification.stroke_heuristic_classifier import StrokeHeuristicClassifier

def create_synthetic_landmarks(arm_phase="alternating", body_roll=30.0, wrist_range=0.2, leg_symmetry="alternating", head_orientation="prone", num_frames=30):
    """Helper to generate synthetic landmark frame sequences for testing."""
    frames = []
    for f_idx in range(num_frames):
        t = f_idx * 0.1
        # Left wrist Y vs Right wrist Y
        arm_amp = wrist_range if wrist_range is not None else 0.2
        if arm_phase == "alternating":
            lw_y = 0.5 + arm_amp * math.sin(t)
            rw_y = 0.5 + arm_amp * math.sin(t + math.pi) # 180 deg anti-phase
        elif arm_phase == "simultaneous":
            lw_y = 0.5 + arm_amp * math.sin(t)
            rw_y = 0.5 + arm_amp * math.sin(t) # In-phase
        else: # Ambiguous / constant
            lw_y = 0.5
            rw_y = 0.5

        # Left leg Y vs Right leg Y
        if leg_symmetry == "simultaneous":
            la_y = 0.8 + 0.1 * math.sin(t)
            ra_y = 0.8 + 0.1 * math.sin(t)
        else:
            la_y = 0.8 + 0.1 * math.sin(t)
            ra_y = 0.8 + 0.1 * math.sin(t + math.pi)

        # Head / Nose position for supine (backstroke) vs prone
        nose_y = 0.15 if head_orientation == "supine" else 0.45

        # Simple landmark objects
        lms = [type('LM', (), {'x': 0.5, 'y': 0.5, 'z': 0.0, 'visibility': 0.9})() for _ in range(33)]
        lms[0] = type('LM', (), {'x': 0.5, 'y': nose_y, 'z': 0.0, 'visibility': 0.9})() # Nose
        lms[11] = type('LM', (), {'x': 0.4, 'y': 0.3, 'z': 0.0, 'visibility': 0.9})() # L Shoulder
        lms[12] = type('LM', (), {'x': 0.6, 'y': 0.3, 'z': 0.0, 'visibility': 0.9})() # R Shoulder
        lms[23] = type('LM', (), {'x': 0.45, 'y': 0.6, 'z': 0.0, 'visibility': 0.9})() # L Hip
        lms[24] = type('LM', (), {'x': 0.55, 'y': 0.6, 'z': 0.0, 'visibility': 0.9})() # R Hip
        lms[15] = type('LM', (), {'x': 0.3, 'y': lw_y, 'z': 0.0, 'visibility': 0.9})() # L Wrist
        lms[16] = type('LM', (), {'x': 0.7, 'y': rw_y, 'z': 0.0, 'visibility': 0.9})() # R Wrist
        lms[27] = type('LM', (), {'x': 0.4, 'y': la_y, 'z': 0.0, 'visibility': 0.9})() # L Ankle
        lms[28] = type('LM', (), {'x': 0.6, 'y': ra_y, 'z': 0.0, 'visibility': 0.9})() # R Ankle

        angles_obj = type('Angles', (), {
            'body_roll': type('Metric', (), {'value': body_roll + 5.0 * math.sin(t), 'valid': True})()
        })()

        frame = type('Frame', (), {
            'frame_index': f_idx,
            'is_valid': True,
            'raw_landmarks': lms,
            'angles': angles_obj
        })()
        frames.append(frame)
    return frames

def test_1_feature_extraction_valid_sequence():
    extractor = KinematicFeatureExtractor(min_valid_frames=10)
    frames = create_synthetic_landmarks(arm_phase="alternating", num_frames=30)
    feat_set = extractor.extract_features(frames)

    assert feat_set.arm_phase_correlation.valid is True
    assert feat_set.arm_phase_correlation.raw_value < -0.8 # Anti-phase
    assert feat_set.mean_body_roll.valid is True

def test_2_missing_landmark_handling():
    extractor = KinematicFeatureExtractor(min_valid_frames=10)
    frames = create_synthetic_landmarks(num_frames=30)
    # Set raw_landmarks to empty to simulate complete landmark failure
    for f in frames:
        f.raw_landmarks = []

    feat_set = extractor.extract_features(frames)
    assert feat_set.arm_phase_correlation.valid is False
    assert feat_set.arm_phase_correlation.raw_value is None
    assert "INSUFFICIENT_VALID_FRAMES" in feat_set.arm_phase_correlation.missing_data_condition

def test_3_temporal_window_handling():
    extractor = KinematicFeatureExtractor(min_valid_frames=15)
    frames = create_synthetic_landmarks(num_frames=5) # Only 5 frames
    feat_set = extractor.extract_features(frames)

    assert feat_set.arm_phase_correlation.valid is False
    assert "INSUFFICIENT_VALID_FRAMES" in feat_set.arm_phase_correlation.missing_data_condition

def test_4_freestyle_heuristic_classification():
    extractor = KinematicFeatureExtractor(min_valid_frames=10)
    frames = create_synthetic_landmarks(arm_phase="alternating", body_roll=35.0, wrist_range=0.2, head_orientation="prone", num_frames=30)
    feat_set = extractor.extract_features(frames)

    classifier = StrokeHeuristicClassifier()
    res = classifier.classify_features(feat_set)

    assert res.predicted_stroke == StrokeType.FREESTYLE
    assert res.confidence >= 0.40
    assert res.classification_status in ["classified", "ACCEPTED"]

def test_5_backstroke_heuristic_classification():
    extractor = KinematicFeatureExtractor(min_valid_frames=10)
    frames = create_synthetic_landmarks(arm_phase="alternating", body_roll=10.0, wrist_range=0.05, head_orientation="supine", num_frames=30)
    feat_set = extractor.extract_features(frames)

    classifier = StrokeHeuristicClassifier()
    res = classifier.classify_features(feat_set)

    assert res.predicted_stroke == StrokeType.BACKSTROKE
    assert res.confidence >= 0.40

def test_6_breaststroke_heuristic_classification():
    extractor = KinematicFeatureExtractor(min_valid_frames=10)
    frames = create_synthetic_landmarks(arm_phase="simultaneous", wrist_range=0.08, leg_symmetry="simultaneous", head_orientation="prone", num_frames=30)
    feat_set = extractor.extract_features(frames)

    classifier = StrokeHeuristicClassifier()
    res = classifier.classify_features(feat_set)

    assert res.predicted_stroke == StrokeType.BREASTSTROKE
    assert res.confidence >= 0.40

def test_7_butterfly_heuristic_classification():
    extractor = KinematicFeatureExtractor(min_valid_frames=10)
    frames = create_synthetic_landmarks(arm_phase="simultaneous", wrist_range=0.35, leg_symmetry="simultaneous", head_orientation="prone", num_frames=30)
    feat_set = extractor.extract_features(frames)

    classifier = StrokeHeuristicClassifier()
    res = classifier.classify_features(feat_set)

    assert res.predicted_stroke == StrokeType.BUTTERFLY
    assert res.confidence >= 0.40

def test_8_9_10_ambiguous_low_confidence_no_silent_freestyle_fallback():
    extractor = KinematicFeatureExtractor(min_valid_frames=10)
    frames = create_synthetic_landmarks(arm_phase="ambiguous", body_roll=0.0, wrist_range=0.0, num_frames=30)
    # Set flat landmarks
    for f in frames:
        for lm in f.raw_landmarks:
            lm.y = 0.5
    feat_set = extractor.extract_features(frames)

    classifier = StrokeHeuristicClassifier(confidence_threshold=0.85)
    res = classifier.classify_features(feat_set)

    assert res.confidence < 0.85
    assert res.predicted_stroke in [StrokeType.UNKNOWN, StrokeType.BREASTSTROKE, StrokeType.BUTTERFLY]
    assert res.predicted_stroke != StrokeType.FREESTYLE # NO SILENT FREESTYLE FALLBACK!

def test_11_explainability_output():
    extractor = KinematicFeatureExtractor(min_valid_frames=10)
    frames = create_synthetic_landmarks(arm_phase="alternating", body_roll=35.0, num_frames=30)
    feat_set = extractor.extract_features(frames)

    classifier = StrokeHeuristicClassifier()
    res = classifier.classify_features(feat_set)

    assert "classification_reason" in res.__dataclass_fields__
    assert res.classification_reason != ""
    assert "arm_phase_correlation" in res.feature_values
    assert len(res.feature_contributions) > 0

def test_12_version_metadata():
    classifier = StrokeHeuristicClassifier()
    assert classifier.classifier_version == "1.0.0-unvalidated"
    assert classifier.threshold_version == "UNVALIDATED_HEURISTIC_v1.0"
