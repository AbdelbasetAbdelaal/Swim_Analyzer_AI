from models.data_models import AnalysisResult, ReliabilityResult
from core.logger import setup_logger

logger = setup_logger(__name__)

class ReliabilityEngine:
    """
    Transparent Video Analysis Reliability Engine.
    Calculates empirical data tracking reliability and scientific confidence
    based on video frame coverage, pose validity, landmark visibility,
    temporal stability, and movement cycle quality.
    
    This engine measures ONLY data quality & measurement trustworthiness,
    NEVER stroke style classification probability.
    """
    
    @staticmethod
    def evaluate(analysis: AnalysisResult) -> ReliabilityResult:
        result = ReliabilityResult()
        
        try:
            total_frames = len(analysis.frames)
            if total_frames == 0:
                result.analysis_reliability_score = 0.0
                result.analysis_reliability_level = "Low"
                result.scientific_confidence = "Low"
                result.confidence_status = "Low Reliability (Insufficient Data)"
                result.frame_coverage_pct = 0.0
                result.pose_validity_pct = 0.0
                result.landmark_visibility_pct = 0.0
                result.temporal_stability_pct = 0.0
                result.cycle_quality_pct = 0.0
                result.measurement_stability_pct = 0.0
                result.reasons.append("Insufficient valid pose frames in video.")
                return result
                
            # 1. Frame Coverage & Pose Validity
            valid_frames = [f for f in analysis.frames if f.is_valid]
            valid_count = len(valid_frames)
            frame_coverage = (valid_count / total_frames) * 100.0
            pose_validity = (valid_count / max(1, total_frames)) * 100.0
            
            # 2. Landmark Visibility
            all_visibilities = []
            for f in valid_frames:
                if f.raw_landmarks:
                    for lm in f.raw_landmarks:
                        all_visibilities.append(getattr(lm, 'visibility', 1.0))
            landmark_vis = (sum(all_visibilities) / len(all_visibilities) * 100.0) if all_visibilities else (90.0 if valid_count > 0 else 0.0)
            
            # 3. Temporal Stability & Phase Confidence
            phase_confs = [f.phase_confidence for f in valid_frames if f.stroke_phase != "Unknown"]
            temporal_stability = (sum(phase_confs) / len(phase_confs) * 100.0) if phase_confs else (80.0 if valid_count > 0 else 0.0)
            
            # 4. Cycle Quality
            cycles = analysis.stroke_statistics.completed_cycles if analysis.stroke_statistics else 0
            if cycles >= 3:
                cycle_quality = 100.0
            elif cycles == 2:
                cycle_quality = 80.0
            elif cycles == 1:
                cycle_quality = 50.0
            else:
                cycle_quality = 10.0
                
            # 5. Measurement Stability
            meas_stability = 100.0
            if analysis.report:
                if not analysis.report.stroke_rate.valid:
                    meas_stability -= 25.0
                if not analysis.report.stroke_length.valid:
                    meas_stability -= 25.0
                    
            # Weighted Overall Reliability Score
            # 0.25 frame_coverage + 0.25 pose_validity + 0.20 landmark_vis + 0.15 temporal_stability + 0.15 cycle_quality
            reliability_score = (
                0.25 * frame_coverage +
                0.25 * pose_validity +
                0.20 * landmark_vis +
                0.15 * temporal_stability +
                0.15 * cycle_quality
            )
            
            # Check for low video quality or insufficient evidence penalties
            reasons = []
            if valid_count < 15:
                reliability_score -= 30.0
                reasons.append("Insufficient valid pose frames.")
            if landmark_vis < 50.0:
                reliability_score -= 20.0
                reasons.append("Landmark visibility was insufficient for reliable biomechanical measurements.")
            if cycles == 0:
                reliability_score -= 25.0
                reasons.append("Zero complete stroke cycles detected.")
            if frame_coverage < 50.0:
                reasons.append("Swimmer leaving frame or excessive occlusion detected.")

            final_score = round(min(100.0, max(0.0, reliability_score)), 1)
            
            result.analysis_reliability_score = final_score
            result.analysis_confidence_score = final_score
            result.frame_coverage_pct = round(frame_coverage, 1)
            result.pose_validity_pct = round(pose_validity, 1)
            result.landmark_visibility_pct = round(landmark_vis, 1)
            result.temporal_stability_pct = round(temporal_stability, 1)
            result.cycle_quality_pct = round(cycle_quality, 1)
            result.measurement_stability_pct = round(meas_stability, 1)
            result.reasons = reasons
            
            if final_score >= 80.0:
                result.analysis_reliability_level = "High"
                result.analysis_confidence_level = "High"
                result.scientific_confidence = "High"
                result.confidence_status = "High Reliability"
            elif final_score >= 60.0:
                result.analysis_reliability_level = "Medium"
                result.analysis_confidence_level = "Medium"
                result.scientific_confidence = "Medium"
                result.confidence_status = "Moderate Reliability"
            else:
                result.analysis_reliability_level = "Low"
                result.analysis_confidence_level = "Low"
                result.scientific_confidence = "Low"
                result.confidence_status = "Low Reliability (Review Required)"
                
        except Exception as e:
            logger.error(f"Error in ReliabilityEngine: {e}")
            result.analysis_reliability_score = 0.0
            result.analysis_reliability_level = "Low"
            result.scientific_confidence = "Low"
            result.confidence_status = "Low Reliability (Engine Error)"
            result.reasons.append(f"Engine evaluation error: {e}")
            
        return result
