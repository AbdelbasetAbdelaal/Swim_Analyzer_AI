import cv2
from models.data_models import StrokeType, StrokeDetectionResult
from analysis.pose_detector import PoseDetector
from core.logger import setup_logger

logger = setup_logger(__name__)

class StrokeClassifier:
    """Analyzes a sampled clip across the active swimming portion of a video to determine the stroke."""
    
    def __init__(self):
        self.pose_detector = PoseDetector()
        
    def predict(self, video_path: str, max_frames: int = 120, forced_confidence: float = None) -> StrokeDetectionResult:
        """
        Predict the stroke type using smart sampling across active swimming frames.
        Avoids pre-swim glides, wall pushes, or starting blocks at frame 0.
        """
        logger.info(f"Starting Stroke Type Detection on: {video_path}")
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error("Could not open video for stroke detection.")
            self.pose_detector.close()
            return self._fallback()
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        # Smart frame sampling window: for short/medium clips (<=300 frames), sample entire sequence
        if total_frames <= 300:
            start_frame = 0
            end_frame = total_frames
        else:
            start_frame = int(total_frames * 0.10)
            end_frame = int(total_frames * 0.90)

        if start_frame > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        # Frame stride to sample up to max_frames across usable duration
        usable_duration = max(1, end_frame - start_frame)
        sample_stride = max(1, usable_duration // max_frames) if usable_duration > max_frames else 1

        frames_list = []
        raw_counter = start_frame
        sampled_count = 0

        while cap.isOpened() and sampled_count < max_frames and raw_counter <= end_frame:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
                
            if (raw_counter - start_frame) % sample_stride == 0:
                landmarks, is_valid = self.pose_detector.detect_pose(frame)
                safe_landmarks = None
                if landmarks:
                    safe_landmarks = [
                        type('SimpleLandmark', (), {
                            'x': float(lm.x),
                            'y': float(lm.y),
                            'z': float(getattr(lm, 'z', 0.0)),
                            'visibility': float(getattr(lm, 'visibility', 1.0))
                        })() for lm in landmarks
                    ]

                frame_data = type('SimpleFrame', (), {
                    'frame_index': raw_counter,
                    'is_valid': is_valid,
                    'raw_landmarks': safe_landmarks,
                    'angles': None
                })()
                frames_list.append(frame_data)
                sampled_count += 1

            raw_counter += 1
            
        cap.release()
        self.pose_detector.close()
        
        # PIPELINE: Python Temporal Kinematic Classifier Engine (Sole Classification Authority)
        from analysis.classification.temporal_kinematic_engine import PythonTemporalKinematicEngine

        engine = PythonTemporalKinematicEngine()
        engine_res = engine.classify_video_sequence(frames_list, selected_stroke_input=StrokeType.AUTO_DETECT)

        # Execution & Diagnostic Logging
        conf_str = f"{engine_res.confidence:.2f}" if engine_res.confidence is not None else "0.00"
        sig_butterfly = engine_res.signature_scores.get("butterfly", {}).get("score", 0.0)
        sig_breaststroke = engine_res.signature_scores.get("breaststroke", {}).get("score", 0.0)
        sig_freestyle = engine_res.signature_scores.get("freestyle", {}).get("score", 0.0)
        sig_backstroke = engine_res.signature_scores.get("backstroke", {}).get("score", 0.0)

        logger.info("[STROKE_CLASSIFIER] Mode: PYTHON_TEMPORAL_KINEMATIC")
        logger.info("[STROKE_CLASSIFIER] AI agent: DISABLED")
        logger.info("[STROKE_CLASSIFIER] Classification mode: PYTHON_ONLY")
        logger.info("[STROKE_CLASSIFIER] Pose quality: %.1f%%", engine_res.pose_quality * 100.0)
        logger.info("[STROKE_CLASSIFIER] Valid frames: %d", len(frames_list))
        logger.info("[STROKE_CLASSIFIER] Temporal windows: %d", engine_res.temporal_windows_count)
        logger.info("[STROKE_CLASSIFIER] Cycles detected: %d", engine_res.cycles_detected)
        logger.info("[STROKE_CLASSIFIER] Stroke signatures:")
        logger.info("[STROKE_CLASSIFIER]   Butterfly: %.2f", sig_butterfly)
        logger.info("[STROKE_CLASSIFIER]   Breaststroke: %.2f", sig_breaststroke)
        logger.info("[STROKE_CLASSIFIER]   Freestyle: %.2f", sig_freestyle)
        logger.info("[STROKE_CLASSIFIER]   Backstroke: %.2f", sig_backstroke)
        logger.info("[STROKE_CLASSIFIER] Temporal window predictions:")
        for st_name, pred_str in engine_res.window_predictions.items():
            logger.info("[STROKE_CLASSIFIER]   %s: %s", st_name, pred_str)
        logger.info("[STROKE_CLASSIFIER] Temporal consistency: %.1f%%", engine_res.temporal_consistency * 100.0)
        logger.info("[STROKE_CLASSIFIER] Signature margin: %.2f", engine_res.signature_margin)
        logger.info("[STROKE_CLASSIFIER] Prediction: %s", engine_res.predicted_stroke.value)
        logger.info("[STROKE_CLASSIFIER] Kinematic confidence: %s", conf_str)
        logger.info("[STROKE_CLASSIFIER] Status: %s", engine_res.classification_status)

        # Build Unified Backward-Compatible StrokeDetectionResult Output
        uncertainty_val = round(1.0 - engine_res.confidence, 4) if engine_res.confidence is not None else 1.0

        res = StrokeDetectionResult(
            predicted_stroke=engine_res.predicted_stroke,
            confidence=forced_confidence if forced_confidence is not None else engine_res.confidence,
            predictions=engine_res.stroke_scores,
            selected_stroke=StrokeType.AUTO_DETECT,
            manual_override=False,
            is_inconsistent=False,
            classification_status=engine_res.classification_status,
            classification_reason=engine_res.classification_reason,
            feature_values=engine_res.feature_values,
            feature_contributions=engine_res.feature_contributions,
            confidence_type="UNCALIBRATED_DECISION_SCORE",
            uncertainty=uncertainty_val,
            rule_prediction=engine_res.predicted_stroke if engine_res.predicted_stroke != StrokeType.UNKNOWN else None,
            ai_prediction=None,
            agreement=None,
            evidence={
                "reason": engine_res.classification_reason,
                "cycles_detected": engine_res.cycles_detected,
                "cycle_predictions": engine_res.cycle_predictions,
                "signature_scores": engine_res.signature_scores
            },
            missing_evidence=engine_res.missing_evidence,
            conflicts=[],
            method="PYTHON_TEMPORAL_KINEMATIC",
            classifier_version="3.0.0-Temporal-Engine",
            threshold_version="TEMPORAL_KINEMATIC_v3.0"
        )
        res.feature_values["uncertainty"] = uncertainty_val
        res.feature_values["visibility_ratio"] = engine_res.pose_quality

        return res



        
    def _fallback(self) -> StrokeDetectionResult:
        return StrokeDetectionResult(
            predicted_stroke=StrokeType.UNKNOWN,
            confidence=None,
            predictions={},
            selected_stroke=StrokeType.AUTO_DETECT,
            manual_override=False,
            is_inconsistent=False,
            classification_status="INSUFFICIENT_EVIDENCE",
            classification_reason="Could not open video file or read frame landmarks for stroke detection.",
            feature_values={},
            feature_contributions={},
            missing_evidence=["video_read_failure"],
            classifier_version="2.0.0-Hybrid-Engine",
            threshold_version="HYBRID_DECISION_v2.0"
        )
