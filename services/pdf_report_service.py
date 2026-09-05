import os
import uuid
from datetime import datetime
from typing import List, Optional, Any
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from models.athlete_profile import AthleteProfile
from models.analysis_session import AnalysisSession
from models.coach_profile import CoachProfile
from models.data_models import AnalysisResult
from core.config import config
from core.logger import setup_logger

logger = setup_logger(__name__)

class PDFReportService:
    """
    Generates professional, styled PDF reports for athlete profiles and single analysis sessions.
    """
    def __init__(self):
        self.output_dir = config.data_dir / "pdf_reports"
        os.makedirs(self.output_dir, exist_ok=True)

    def _clean_text(self, text: Any) -> str:
        if text is None:
            return ""
        s = str(text)
        replacements = {
            "—": "-",
            "–": "-",
            "•": "*",
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
            "±": "+/-",
            "°": " deg",
        }
        for orig, repl in replacements.items():
            s = s.replace(orig, repl)
        return s.encode('latin-1', 'replace').decode('latin-1')
        
    def generate_athlete_summary(self, profile: AthleteProfile, history: List[AnalysisSession], coach: Optional[CoachProfile] = None) -> str:
        """Generates an Athlete Profile & Performance History PDF report."""
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.add_page()
        
        # Header
        pdf.set_font("Helvetica", style="B", size=22)
        pdf.set_text_color(0, 85, 255) # Swim Blue
        pdf.cell(0, 15, "SwimAnalyzer AI - Athlete Summary Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(100, 100, 100)
        coach_info = f" | Coach: {coach.full_name}" if coach else ""
        pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}{coach_info}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        pdf.ln(8)
        
        # Athlete Profile
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", style="B", size=14)
        pdf.cell(0, 8, "Athlete Profile", new_x=XPos.LMARGIN, new_y=YPos.NEXT, border="B")
        pdf.ln(4)
        
        pdf.set_font("Helvetica", size=11)
        info_lines = [
            f"Name: {profile.full_name}",
            f"Age: {profile.age} | Gender: {profile.gender}",
            f"Height: {profile.height_cm} cm | Weight: {profile.weight_kg} kg",
            f"Level: {profile.swimming_level} | Preferred Stroke: {profile.preferred_stroke}"
        ]
        for line in info_lines:
            pdf.cell(0, 7, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
        pdf.ln(6)
        
        # Coach Notes
        if profile.notes:
            pdf.set_font("Helvetica", style="B", size=13)
            pdf.set_text_color(0, 85, 255)
            pdf.cell(0, 8, "Coach Notes", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=10)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, profile.notes)
            pdf.ln(4)
            
        # Training Goals
        if profile.training_goals:
            pdf.set_font("Helvetica", style="B", size=13)
            pdf.set_text_color(0, 160, 80) # Green
            pdf.cell(0, 8, "Training Goals", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=10)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, profile.training_goals)
            pdf.ln(6)
            
        # Athlete Performance Overview Stats
        if history:
            scores = [s.performance_score for s in history if s.performance_score is not None]
            total_cycles = sum([s.completed_cycles for s in history])
            avg_score = sum(scores) / len(scores) if scores else None
            max_score = max(scores) if scores else None

            pdf.set_font("Helvetica", style="B", size=13)
            pdf.set_text_color(0, 85, 255)
            pdf.cell(0, 8, "Overall Performance Overview", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            pdf.set_font("Helvetica", size=10)
            pdf.set_fill_color(245, 248, 255)
            pdf.set_draw_color(200, 220, 250)
            pdf.rect(10, pdf.get_y(), 190, 16, style="FD")
            
            pdf.set_xy(12, pdf.get_y() + 4)
            pdf.cell(47, 8, f"Total Sessions: {len(history)}", align="C")
            pdf.cell(47, 8, f"Avg Score: {avg_score:.1f}" if avg_score is not None else "Avg Score: INSUFFICIENT_EVIDENCE", align="C")
            pdf.cell(47, 8, f"Best Score: {max_score:.1f}" if max_score is not None else "Best Score: INSUFFICIENT_EVIDENCE", align="C")
            pdf.cell(47, 8, f"Total Cycles: {total_cycles}", align="C")
            pdf.ln(12)

        # History Table
        if history:
            pdf.set_font("Helvetica", style="B", size=14)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 8, "Recent Sessions Breakdown", new_x=XPos.LMARGIN, new_y=YPos.NEXT, border="B")
            pdf.ln(4)
            
            pdf.set_fill_color(240, 244, 250)
            pdf.set_font("Helvetica", style="B", size=10)
            col_widths = [40, 40, 35, 35, 40] # Total 190 mm width
            start_x = 10
            pdf.set_x(start_x)
            
            headers = ["Date & Time", "Stroke Style", "Score / 100", "Cycles", "Confidence"]
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 8, header, border=1, align="C", fill=True)
            pdf.ln()
            
            pdf.set_font("Helvetica", size=10)
            for s in history[:12]:
                pdf.set_x(start_x)
                date_str = s.analysis_timestamp.replace("T", " ")[:16]
                conf = getattr(s, 'scientific_confidence', 'Medium') or 'Medium'
                pdf.cell(col_widths[0], 8, date_str, border=1, align="C")
                pdf.cell(col_widths[1], 8, str(s.stroke_type), border=1, align="C")
                score_text = f"{s.performance_score:.1f}" if s.performance_score is not None else "INSUFFICIENT_EVIDENCE"
                pdf.cell(col_widths[2], 8, score_text, border=1, align="C")
                pdf.cell(col_widths[3], 8, str(s.completed_cycles), border=1, align="C")
                pdf.cell(col_widths[4], 8, str(conf), border=1, align="C")
                pdf.ln()

        from utils.file_security import sanitize_and_resolve_path
        filename = f"Athlete_{profile.full_name.replace(' ', '_')}.pdf"
        filepath = sanitize_and_resolve_path(filename, str(self.output_dir), generate_unique=True)
        pdf.output(filepath)
        logger.info(f"Generated athlete summary PDF: {filepath}")
        return str(filepath)

    def generate_session_analysis_pdf(self, analysis_result: AnalysisResult,
                                       profile: Optional[AthleteProfile] = None,
                                       coach: Optional[CoachProfile] = None) -> str:
        """Generates a detailed single-session Biomechanical PDF Analysis Report."""
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.add_page()

        # Header Title
        pdf.set_font("Helvetica", style="B", size=22)
        pdf.set_text_color(0, 85, 255)
        pdf.cell(0, 12, "SwimAnalyzer AI - Biomechanical Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(100, 100, 100)
        athlete_name = profile.full_name if profile else "Guest Athlete"
        coach_name = f" | Coach: {coach.full_name}" if coach else ""
        pdf.cell(0, 6, f"Athlete: {athlete_name}{coach_name} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        pdf.ln(6)

        # Performance Score & Stroke Selection Banner
        report = getattr(analysis_result, 'report', None)
        overall_score = report.overall_score if report else None
        consistency = getattr(analysis_result, 'consistency', None)
        scientific_conf = consistency.scientific_confidence if consistency else "Medium"
        stroke_title = str(getattr(analysis_result, 'stroke_type', 'Freestyle')).title()
        reliability = getattr(analysis_result, 'reliability', None)
        rel_score_str = f"{reliability.analysis_reliability_score:.1f}%" if reliability else "N/A"
        rel_level_str = reliability.analysis_reliability_level if reliability else "Medium"

        pdf.set_fill_color(240, 248, 255)
        pdf.set_draw_color(0, 120, 245)
        pdf.rect(10, pdf.get_y(), 190, 30, style="FD")
        
        pdf.set_xy(15, pdf.get_y() + 3)
        pdf.set_font("Helvetica", style="B", size=14)
        pdf.set_text_color(0, 50, 150)
        overall_text = f"Overall Technique Score: {overall_score:.1f} / 100" if overall_score is not None else "Overall Technique Score: INSUFFICIENT_EVIDENCE"
        pdf.cell(100, 7, overall_text)
        
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(70, 7, f"Scientific Confidence: {scientific_conf}", align="R")
        pdf.ln(7)

        pdf.set_x(15)
        pdf.set_font("Helvetica", style="B", size=10)
        pdf.set_text_color(0, 85, 255)
        pdf.cell(90, 6, f"Swimming Stroke: {stroke_title} (Selection: User Selected)")
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(80, 6, f"Analysis Reliability: {rel_level_str} ({rel_score_str})", align="R")
        pdf.set_x(10)
        pdf.ln(12)

        # Key Biomechanical Metrics Table
        pdf.set_font("Helvetica", style="B", size=13)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, "Key Biomechanical Metrics", new_x=XPos.LMARGIN, new_y=YPos.NEXT, border="B")
        pdf.ln(4)

        report = getattr(analysis_result, 'report', None)
        
        def get_val(metric_obj):
            if not metric_obj:
                return None
            if hasattr(metric_obj, 'value') and metric_obj.value is not None and metric_obj.value > 0:
                return metric_obj.value
            if isinstance(metric_obj, (int, float)) and metric_obj > 0:
                return float(metric_obj)
            return None

        sr = get_val(getattr(report, 'stroke_rate', None))
        sl = get_val(getattr(report, 'stroke_length', None))
        kf = get_val(getattr(report, 'kick_frequency', None))
        sym = get_val(getattr(report, 'stroke_symmetry', None))

        # 3D body roll & torsion averages from frames
        rolls_3d = [f.angles.body_roll_3d.value for f in analysis_result.frames if f.is_valid and f.angles and f.angles.body_roll_3d and f.angles.body_roll_3d.value is not None and f.angles.body_roll_3d.value > 0] if analysis_result.frames else []
        torsions = [f.angles.core_torsion_3d.value for f in analysis_result.frames if f.is_valid and f.angles and f.angles.core_torsion_3d and f.angles.core_torsion_3d.value is not None and f.angles.core_torsion_3d.value > 0] if analysis_result.frames else []

        b_roll = (sum(rolls_3d) / len(rolls_3d)) if rolls_3d else None
        torsion = (sum(torsions) / len(torsions)) if torsions else None

        metrics_data = [
            ("Stroke Rate", f"{sr:.1f} spm" if sr is not None else "N/A"),
            ("Stroke Length", f"{sl:.2f} m" if sl is not None else "N/A"),
            ("Kick Frequency", f"{kf:.1f} Hz" if kf is not None else "N/A"),
            ("Stroke Symmetry", f"{sym:.1f}%" if sym is not None else "N/A"),
            ("True 3D Body Roll", f"{b_roll:.1f}°" if b_roll is not None else "N/A"),
            ("3D Core Torsion", f"{torsion:.1f}°" if torsion is not None else "N/A"),
        ]

        pdf.set_font("Helvetica", size=10)
        pdf.set_fill_color(245, 245, 245)
        for i in range(0, len(metrics_data), 2):
            m1_name, m1_val = metrics_data[i]
            m2_name, m2_val = metrics_data[i+1]
            pdf.cell(45, 7, m1_name, border=1, fill=True)
            pdf.cell(48, 7, m1_val, border=1, align="C")
            pdf.cell(2, 7, "")
            pdf.cell(45, 7, m2_name, border=1, fill=True)
            pdf.cell(48, 7, m2_val, border=1, align="C")
            pdf.ln()

        pdf.ln(8)

        # Population Benchmarks & Percentile Rankings
        bm_res = getattr(analysis_result, 'benchmark_result', None)
        if bm_res and getattr(bm_res, 'comparisons', None):
            pdf.set_font("Helvetica", style="B", size=13)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 8, f"Population Benchmarks & Percentiles ({bm_res.age_group} | {bm_res.gender})", new_x=XPos.LMARGIN, new_y=YPos.NEXT, border="B")
            pdf.ln(4)

            pdf.set_fill_color(240, 244, 250)
            pdf.set_font("Helvetica", style="B", size=8)
            bm_widths = [40, 25, 35, 20, 22, 48] # Total 190 mm
            bm_headers = ["Metric", "Value", "Pop Mean +/- Std", "Z-Score", "Percentile", "Evidence Status"]
            for i, h in enumerate(bm_headers):
                pdf.cell(bm_widths[i], 7, h, border=1, align="C", fill=True)
            pdf.ln()

            pdf.set_font("Helvetica", size=8)
            cited_ids = set()
            for m_name, comp in bm_res.comparisons.items():
                ev_meta = getattr(comp, 'evidence', None)
                if ev_meta:
                    val_enum = ev_meta.validation_status.value
                    badge = val_enum.replace("_", " ").title()
                else:
                    badge = "Partially Validated"
                    
                if ev_meta and ev_meta.source_ids:
                    cited_ids.update(ev_meta.source_ids)

                z_str = f"{comp.z_score:+.2f}" if comp.z_score is not None else "N/A"
                pct_str = f"{comp.percentile:.1f}%" if comp.percentile is not None else "N/A"

                pdf.cell(bm_widths[0], 6, m_name.replace("_", " ").title(), border=1)
                pdf.cell(bm_widths[1], 6, f"{comp.raw_value} {comp.unit}", border=1, align="C")
                if comp.population_mean is not None and comp.population_std is not None:
                    pdf.cell(bm_widths[2], 6, f"{comp.population_mean:.1f} +/- {comp.population_std:.1f}", border=1, align="C")
                else:
                    pdf.cell(bm_widths[2], 6, "N/A", border=1, align="C")
                pdf.cell(bm_widths[3], 6, z_str, border=1, align="C")
                pdf.cell(bm_widths[4], 6, pct_str, border=1, align="C")
                pdf.cell(bm_widths[5], 6, badge, border=1, align="C")
                pdf.ln()

            pdf.ln(6)

        # Coaching Feedback & Technique Drills
        pdf.set_font("Helvetica", style="B", size=13)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, "Coaching Feedback & Recommended Drills", new_x=XPos.LMARGIN, new_y=YPos.NEXT, border="B")
        pdf.ln(4)

        feedback_text = report.feedback_summary if (report and report.feedback_summary) else "INSUFFICIENT_EVIDENCE: No reliable coaching assessment is available."
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 6, self._clean_text(feedback_text))
        pdf.ln(6)

        # Section 5: Scientific Literature References & Dataset Provenance
        if bm_res and getattr(bm_res, 'comparisons', None):
            pdf.set_font("Helvetica", style="B", size=11)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 7, "Scientific References & Literature Provenance", new_x=XPos.LMARGIN, new_y=YPos.NEXT, border="B")
            pdf.ln(3)

            pdf.set_font("Helvetica", size=8)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 5, self._clean_text(f"Dataset: {bm_res.dataset_name} (ID: {bm_res.dataset_id}, v{bm_res.dataset_version}, Revision: {bm_res.scientific_revision})"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            from services.scientific_evidence_service import ScientificEvidenceService
            ev_service = ScientificEvidenceService()
            sources = ev_service.get_sources_for_ids(list(cited_ids)) if cited_ids else []
            for src in sources:
                cit_str = ev_service.format_citation(src)
                pdf.multi_cell(0, 4, self._clean_text(f"- [{src.source_id}] {cit_str} (Level {src.evidence_quality.value}, N={src.sample_size})"))

        # Phase Breakdown
        pdf.set_font("Helvetica", style="B", size=13)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, "Cycle & Timeline Statistics", new_x=XPos.LMARGIN, new_y=YPos.NEXT, border="B")
        pdf.ln(4)

        stats = getattr(analysis_result, 'stroke_statistics', None)
        completed_cycles = stats.completed_cycles if stats else 0
        total_frames = len(analysis_result.frames)

        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 6, f"Completed Stroke Cycles: {completed_cycles}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 6, f"Total Analyzed Frames: {total_frames}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        from utils.file_security import sanitize_and_resolve_path
        filename = f"SwimReport_{stroke_title}.pdf"
        filepath = sanitize_and_resolve_path(filename, str(self.output_dir), generate_unique=True)
        pdf.output(filepath)
        logger.info(f"Generated session analysis PDF: {filepath}")
        return str(filepath)
