"""
Service for exporting analysis results to various formats.
"""
import json
import dataclasses
from pathlib import Path
from typing import Any, Tuple
from models.data_models import AnalysisResult
from core.config import config
from core.logger import setup_logger

logger = setup_logger(__name__)

class ExportService:
    """
    Handles exporting structured data objects to files (JSON, etc.)
    """
    
    @staticmethod
    def export_to_json(analysis_result: AnalysisResult, metadata: Any, input_filename: str) -> Tuple[str, str]:
        """
        Exports the AnalysisResult and Metadata to JSON files.
        
        Args:
            analysis_result: The completed result object.
            metadata: The VideoMetadata object.
            input_filename: Original filename to base the export name on.
            
        Returns:
            Tuple[str, str]: The path to the saved JSON report file and the path to the metadata file.
        """
        try:
            # We don't want to export raw_landmarks due to size and serialization issues.
            # We'll create a lightweight dict.
            bm_res = getattr(analysis_result, 'benchmark_result', None)
            export_data = {
                "video_path": analysis_result.video_path,
                "stroke_type": analysis_result.stroke_type,
                "stroke_selection": analysis_result.stroke_selection.to_dict() if analysis_result.stroke_selection else None,
                "average_stroke_rate": analysis_result.average_stroke_rate,
                "report": dataclasses.asdict(analysis_result.report) if analysis_result.report else None,
                "consistency": dataclasses.asdict(analysis_result.consistency) if getattr(analysis_result, 'consistency', None) else None,
                "benchmark_result": dataclasses.asdict(bm_res) if bm_res and dataclasses.is_dataclass(bm_res) else None,
                "frames": []
            }
            
            for frame in analysis_result.frames:
                frame_dict = {
                    "frame_index": frame.frame_index,
                    "timestamp_ms": frame.timestamp_ms,
                    "is_valid": frame.is_valid,
                    "stroke_phase": frame.stroke_phase,
                    "angles": dataclasses.asdict(frame.angles)
                }
                export_data["frames"].append(frame_dict)
                
            from utils.file_security import sanitize_and_resolve_path
            report_name = f"report_{Path(input_filename).stem}.json"
            report_path = sanitize_and_resolve_path(report_name, str(config.reports_dir), generate_unique=True)
            
            with open(report_path, 'w') as f:
                json.dump(export_data, f, indent=4)
                
            metadata_name = f"metadata_{Path(input_filename).stem}.json"
            metadata_path = sanitize_and_resolve_path(metadata_name, str(config.reports_dir), generate_unique=True)
            
            metadata_dict = dataclasses.asdict(metadata)
            
            # Inject consistency metrics into metadata if available
            if getattr(analysis_result, 'consistency', None):
                metadata_dict["consistency_score"] = analysis_result.consistency.overall_score
            if getattr(analysis_result, 'reliability', None):
                metadata_dict["analysis_reliability"] = analysis_result.reliability.analysis_reliability_score
            if getattr(analysis_result, 'stroke_statistics', None):
                metadata_dict["phase_confidence"] = analysis_result.stroke_statistics.average_phase_confidence
            
            # Fix Enum/Object serialization in stroke_detection / stroke_selection
            sd = metadata_dict.get('stroke_detection')
            if sd:
                if isinstance(sd, dict):
                    sel = sd.get('selected_stroke')
                    if hasattr(sel, 'value'):
                        sd['selected_stroke'] = sel.value
                    elif hasattr(sel, '__dict__'):
                        sd['selected_stroke'] = str(sel)
                elif hasattr(sd, 'to_dict'):
                    metadata_dict['stroke_detection'] = sd.to_dict()
                elif hasattr(sd, '__dict__'):
                    sel_val = getattr(sd, 'selected_stroke', 'Freestyle')
                    metadata_dict['stroke_detection'] = {
                        "selected_stroke": sel_val.value if hasattr(sel_val, 'value') else str(sel_val),
                        "selection_source": getattr(sd, 'selection_source', 'USER')
                    }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata_dict, f, indent=4)
                
            # Generate timeline.json
            timeline_data = []
            
            # Map errors to frames
            errors_by_frame = {}
            if analysis_result.report and analysis_result.report.errors:
                for err in analysis_result.report.errors:
                    if err.frame_index not in errors_by_frame:
                        errors_by_frame[err.frame_index] = []
                    errors_by_frame[err.frame_index].append(dataclasses.asdict(err))
                    
            for frame in analysis_result.frames:
                frame_timeline = {
                    "Frame": frame.frame_index,
                    "Timestamp": frame.timestamp_ms,
                    "Stroke_Phase": frame.stroke_phase,
                    "Joint_Angles": dataclasses.asdict(frame.angles),
                    "Confidence": metadata.confidence_statistics.get("average_confidence", 1.0) if frame.is_valid else 0.0,
                    "Detected_Errors": errors_by_frame.get(frame.frame_index, [])
                }
                timeline_data.append(frame_timeline)
                
            timeline_name = f"timeline_{Path(input_filename).stem}.json"
            timeline_path = sanitize_and_resolve_path(timeline_name, str(config.reports_dir), generate_unique=True)
            with open(timeline_path, 'w') as f:
                json.dump(timeline_data, f, indent=4)
                
            logger.info(f"Exported JSON report to {report_path}, metadata to {metadata_path}, timeline to {timeline_path}")
            return str(report_path), str(metadata_path), str(timeline_path)
            
        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")
            return "", "", ""
