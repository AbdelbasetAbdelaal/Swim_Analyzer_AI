"""
Explainable Stroke Heuristic Classifier for SwimAnalyzer AI.
Evaluates kinematic feature sets against explicit UNVALIDATED_HEURISTIC thresholds.
"""
from typing import Any, Dict, List
from models.data_models import StrokeType, StrokeDetectionResult
from analysis.classification.feature_extractor import KinematicFeatureSet
from core.logger import setup_logger

logger = setup_logger(__name__)

# EXPLICIT UNVALIDATED HEURISTIC THRESHOLD METADATA
CLASSIFIER_VERSION = "1.0.0-unvalidated"
THRESHOLD_VERSION = "UNVALIDATED_HEURISTIC_v1.0"
CONFIDENCE_THRESHOLD = 0.40

class StrokeHeuristicClassifier:
    """
    Explainable Heuristic Classifier for swimming stroke styles.
    Thresholds are strictly tagged as UNVALIDATED_HEURISTIC.
    """

    def __init__(self, confidence_threshold: float = CONFIDENCE_THRESHOLD):
        self.confidence_threshold = confidence_threshold
        self.classifier_version = CLASSIFIER_VERSION
        self.threshold_version = THRESHOLD_VERSION

    def classify_features(self, feature_set: KinematicFeatureSet, selected_stroke_input: StrokeType = StrokeType.AUTO_DETECT) -> StrokeDetectionResult:
        """
        Classifies a KinematicFeatureSet using explainable kinematic heuristic rules.
        Missing evidence propagates strictly without zero substitutions or artificial inferences.
        """
        feature_vals: Dict[str, Any] = {}
        missing_evidence: List[str] = []

        # Extract feature values safely
        arm_phase = getattr(feature_set, 'arm_phase_correlation', None)
        body_roll_amp = getattr(feature_set, 'body_roll_amplitude', None)
        wrist_range = getattr(feature_set, 'wrist_vertical_range_ratio', None)
        leg_sym = getattr(feature_set, 'leg_kick_symmetry', None)
        head_supine = getattr(feature_set, 'head_supine_ratio', None)

        phi_arm = arm_phase.raw_value if (arm_phase and arm_phase.valid and arm_phase.raw_value is not None) else None
        roll_amp = body_roll_amp.raw_value if (body_roll_amp and body_roll_amp.valid and body_roll_amp.raw_value is not None) else None
        wrist_range_val = wrist_range.raw_value if (wrist_range and wrist_range.valid and wrist_range.raw_value is not None) else None
        leg_sym_val = leg_sym.raw_value if (leg_sym and leg_sym.valid and leg_sym.raw_value is not None) else None
        head_supine_val = head_supine.raw_value if (head_supine and head_supine.valid and head_supine.raw_value is not None) else None

        total_frames_cnt = getattr(feature_set, 'total_frames_in_window', 0)
        valid_frames_cnt = getattr(feature_set, 'valid_frames_in_window', 0)

        if phi_arm is not None:
            feature_vals["arm_phase_correlation"] = phi_arm
        else:
            missing_evidence.append("arm_phase_correlation")

        if roll_amp is not None:
            feature_vals["body_roll_amplitude"] = roll_amp
        else:
            missing_evidence.append("body_roll_amplitude")

        if wrist_range_val is not None:
            feature_vals["wrist_vertical_range_ratio"] = wrist_range_val
        else:
            missing_evidence.append("wrist_vertical_range_ratio")

        if leg_sym_val is not None:
            feature_vals["leg_kick_symmetry"] = leg_sym_val
        else:
            missing_evidence.append("leg_kick_symmetry")

        if head_supine_val is not None:
            feature_vals["head_supine_ratio"] = head_supine_val

        # Diagnostic frame quality check
        has_any_feature = any(v is not None for v in [phi_arm, roll_amp, wrist_range_val, leg_sym_val, head_supine_val])
        if valid_frames_cnt == 0 and not has_any_feature:
            return StrokeDetectionResult(
                predicted_stroke=StrokeType.UNKNOWN,
                confidence=0.0,
                predictions={},
                selected_stroke=selected_stroke_input,
                manual_override=False,
                is_inconsistent=False,
                classification_status="insufficient_data",
                classification_reason="Zero valid frames containing pose landmarks were detected in video.",
                feature_values=feature_vals,
                feature_contributions={},
                missing_evidence=missing_evidence,
                classifier_version=self.classifier_version,
                threshold_version=self.threshold_version
            )

        # Multi-Feature Candidate Scoring Engine
        scores: Dict[StrokeType, float] = {
            StrokeType.FREESTYLE: 0.0,
            StrokeType.BACKSTROKE: 0.0,
            StrokeType.BREASTSTROKE: 0.0,
            StrokeType.BUTTERFLY: 0.0
        }
        contributions: Dict[str, float] = {}

        # 1. Arm Phase Rhythm Signal
        if phi_arm is not None:
            if phi_arm < -0.15:
                scores[StrokeType.FREESTYLE] += 0.40
                scores[StrokeType.BACKSTROKE] += 0.40
                contributions["arm_phase_alternating"] = +0.40
            elif phi_arm > +0.15:
                scores[StrokeType.BREASTSTROKE] += 0.40
                scores[StrokeType.BUTTERFLY] += 0.40
                contributions["arm_phase_simultaneous"] = +0.40
            else:
                contributions["arm_phase_neutral"] = 0.0

        # 2. Head / Posture Orientation Signal
        if head_supine_val is not None:
            if head_supine_val > 0.50:
                scores[StrokeType.BACKSTROKE] += 0.55
                scores[StrokeType.FREESTYLE] = max(0.0, scores[StrokeType.FREESTYLE] - 0.20)
                scores[StrokeType.BREASTSTROKE] = max(0.0, scores[StrokeType.BREASTSTROKE] - 0.30)
                scores[StrokeType.BUTTERFLY] = max(0.0, scores[StrokeType.BUTTERFLY] - 0.30)
                contributions["head_supine_orientation"] = +0.55
            elif head_supine_val <= 0.30:
                scores[StrokeType.FREESTYLE] += 0.30
                scores[StrokeType.BREASTSTROKE] += 0.20
                scores[StrokeType.BUTTERFLY] += 0.20
                contributions["head_prone_orientation"] = +0.30


        # 3. Body Roll Amplitude Signal
        if roll_amp is not None:
            if roll_amp > 15.0:
                scores[StrokeType.FREESTYLE] += 0.30
                scores[StrokeType.BACKSTROKE] += 0.15
                contributions["high_body_roll_rotation"] = +0.30
            else:
                if phi_arm is not None and phi_arm < -0.15:
                    scores[StrokeType.BACKSTROKE] += 0.30
                    scores[StrokeType.FREESTYLE] += 0.10
                    contributions["compact_backstroke_roll"] = +0.30
                else:
                    scores[StrokeType.BREASTSTROKE] += 0.20
                    scores[StrokeType.BUTTERFLY] += 0.20
                    contributions["flat_torso_alignment"] = +0.20


        # 4. Wrist Vertical Excursion Range Signal
        if wrist_range_val is not None:
            if wrist_range_val > 0.12:
                scores[StrokeType.BUTTERFLY] += 0.30
                scores[StrokeType.FREESTYLE] += 0.20
                contributions["high_wrist_excursion"] = +0.30
            else:
                scores[StrokeType.BREASTSTROKE] += 0.25
                scores[StrokeType.BACKSTROKE] += 0.15
                contributions["compact_wrist_excursion"] = +0.25

        # 5. Leg Kick Symmetry Signal
        if leg_sym_val is not None:
            if leg_sym_val > +0.30:
                scores[StrokeType.BREASTSTROKE] += 0.20
                scores[StrokeType.BUTTERFLY] += 0.20
                contributions["symmetric_leg_kick"] = +0.20
            elif leg_sym_val < -0.15:
                scores[StrokeType.FREESTYLE] += 0.15
                scores[StrokeType.BACKSTROKE] += 0.15
                contributions["flutter_kick_rhythm"] = +0.15

        # Normalize Candidate Scores
        total_score = sum(scores.values())

        if total_score <= 0.0:
            return StrokeDetectionResult(
                predicted_stroke=StrokeType.UNKNOWN,
                confidence=0.10,
                predictions={},
                selected_stroke=selected_stroke_input,
                manual_override=False,
                is_inconsistent=False,
                classification_status="insufficient_data",
                classification_reason="Kinematic feature signals yielded zero candidate stroke evidence.",
                feature_values=feature_vals,
                feature_contributions={},
                missing_evidence=missing_evidence,
                classifier_version=self.classifier_version,
                threshold_version=self.threshold_version
            )

        predictions: Dict[str, float] = {st.value: round(sc / total_score, 4) for st, sc in scores.items() if sc > 0.0}

        top_stroke_str = max(predictions, key=predictions.get)
        top_ratio = predictions[top_stroke_str]

        # Deterministic numeric confidence calculation [0.0, 1.0]
        eff_valid = valid_frames_cnt if valid_frames_cnt > 0 else 1
        eff_total = total_frames_cnt if total_frames_cnt > 0 else 1
        temporal_factor = min(1.0, 0.50 + 0.50 * (eff_valid / eff_total))
        computed_confidence = round(float(top_ratio * temporal_factor), 2)

        evidence_list = [f"Rule contribution: {k} ({v:+.2f})" for k, v in contributions.items()]

        # Machine-readable status classification
        if top_ratio < 0.35:
            predicted_stroke = StrokeType.UNKNOWN
            classification_status = "ambiguous"
            classification_reason = f"Ambiguous kinematic movement (flat score distribution across strokes: {top_ratio*100:.0f}% max)."
        else:
            predicted_stroke = StrokeType(top_stroke_str)
            if computed_confidence >= self.confidence_threshold:
                classification_status = "classified"
                classification_reason = f"Deterministic Python kinematic match ({computed_confidence*100:.0f}% confidence) for {predicted_stroke.value}"
            else:
                classification_status = "MODERATE_CONFIDENCE"
                classification_reason = f"Moderate kinematic decision score ({computed_confidence*100:.0f}% confidence) for {predicted_stroke.value}"



        return StrokeDetectionResult(
            predicted_stroke=predicted_stroke,
            confidence=computed_confidence,
            predictions=predictions,
            selected_stroke=selected_stroke_input,
            manual_override=False,
            is_inconsistent=False,
            classification_status=classification_status,
            classification_reason=classification_reason,
            feature_values=feature_vals,
            feature_contributions=contributions,
            missing_evidence=missing_evidence,
            rule_prediction=predicted_stroke,
            confidence_type="UNCALIBRATED_DECISION_SCORE",
            evidence={"rule_evidence": evidence_list},
            classifier_version=self.classifier_version,
            threshold_version=self.threshold_version
        )


