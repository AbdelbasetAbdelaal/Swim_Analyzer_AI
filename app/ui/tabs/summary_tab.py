"""
Summary Tab Presenter for SwimAnalyzer AI.
Renders executive overview, KPI cards, and data reliability metrics.
"""
import streamlit as st
from core.logger import setup_logger

logger = setup_logger(__name__)

STROKE_ICONS = {
    "Freestyle": "🏊",
    "Backstroke": "🔄",
    "Breaststroke": "🐸",
    "Butterfly": "🦋",
    "Auto Detect": "🔍",
}

def safe_log(msg: str):
    logger.debug(msg)

def render_executive_summary_card(analysis_result):
    """
    Renders an Executive Summary Hero Card at the top of analysis results.
    """
    report = getattr(analysis_result, 'report', None)
    score = report.overall_score if report else None

    if score is None:
        status_tier = "Insufficient Evidence"
        status_color = "#888888"
        badge_bg = "rgba(136, 136, 136, 0.15)"
    elif score >= 85.0:
        status_tier = "Excellent"
        status_color = "#00F0FF"
        badge_bg = "rgba(0, 240, 255, 0.15)"
    elif score >= 70.0:
        status_tier = "Good"
        status_color = "#FF8C00"
        badge_bg = "rgba(255, 140, 0, 0.15)"
    else:
        status_tier = "Needs Improvement"
        status_color = "#FF007F"
        badge_bg = "rgba(255, 0, 127, 0.15)"

    consistency = getattr(analysis_result, 'consistency', None)
    conf_str = consistency.scientific_confidence if consistency else "Medium"

    reliability = getattr(analysis_result, 'reliability', None)
    rel_score = reliability.analysis_reliability_score if reliability else None

    bm_res = getattr(analysis_result, 'benchmark_result', None)
    overall_pct = None
    if bm_res and getattr(bm_res, 'comparisons', None) and "stroke_rate" in bm_res.comparisons:
        overall_pct = bm_res.comparisons["stroke_rate"].percentile

    pct_header_str = f"{overall_pct:.1f}th percentile" if overall_pct is not None else "N/A (Unvalidated Cohort)"
    pct_metric_str = f"{overall_pct:.1f}%" if overall_pct is not None else "N/A"

    with st.container(border=True):
        st.markdown(
            f"""<div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:10px; margin-bottom:12px;">
            <div>
                <span style="font-size:1.5rem; font-weight:bold;">🏆 Overall Performance: {f'{score:.1f} / 100' if score is not None else '⚠ INSUFFICIENT_EVIDENCE'}</span>
                <span style="background:{badge_bg}; color:{status_color}; border:1px solid {status_color}; padding:4px 12px; border-radius:16px; font-weight:bold; font-size:0.9rem; margin-left:12px;">
                    {status_tier}
                </span>
            </div>
            <div style="font-size:0.9rem; color:#A0A0A0;">
                Percentile Rank: <b style="color:#00F0FF;">{pct_header_str}</b>
            </div>
            </div>""",
            unsafe_allow_html=True
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Technique Score", f"{score:.1f}/100" if score is not None else "⚠ INSUFFICIENT_EVIDENCE")
        c2.metric("Scientific Confidence", conf_str)
        c3.metric("Analysis Reliability", f"{rel_score:.1f}/100" if rel_score is not None else "UNAVAILABLE")
        c4.metric("Population Rank", pct_metric_str)

        st.markdown("---")
        str_col, weak_col = st.columns(2)

        with str_col:
            st.markdown("##### 🟢 Top Strengths")
            strengths = []
            if report:
                sym_v = getattr(report.stroke_symmetry, 'value', None) if report.stroke_symmetry else None
                sl_v = getattr(report.stroke_length, 'value', None) if report.stroke_length else None
                sr_v = getattr(report.stroke_rate, 'value', None) if report.stroke_rate else None
                if sym_v is not None and sym_v > 85:
                    strengths.append(f"High Stroke Symmetry ({sym_v:.1f}%)")
                if sl_v is not None and sl_v > 1.8:
                    strengths.append(f"Strong Distance Per Stroke ({sl_v:.2f} m)")
                if sr_v is not None and sr_v > 45:
                    strengths.append(f"Consistent Stroke Tempo ({sr_v:.1f} spm)")
            if not strengths:
                strengths = ["No reliable strength assessment is available from this evidence."]
            for s in strengths[:3]:
                st.markdown(f"- ✅ {s}")

        with weak_col:
            st.markdown("##### 🔴 Key Focus Areas & Flaws")
            flaws = []
            if report and report.errors:
                for e in report.errors:
                    flaws.append(f"{e.error_type} ({e.severity} Severity)")
            if not flaws:
                flaws = ["No reliable technique-flaw assessment is available from this evidence."]
            for f in flaws[:3]:
                st.markdown(f"- ⚠️ {f}")

def render_summary(analysis_result):
    safe_log("[TRACE] ENTER render_summary")
    st.markdown("### Analysis Summary")
    
    stroke_name = getattr(analysis_result, 'stroke_type', None)
    if not stroke_name:
        res_stroke = getattr(st.session_state, 'stroke_result', None)
        if res_stroke and hasattr(res_stroke, 'selected_stroke') and res_stroke.selected_stroke:
            stroke_name = res_stroke.selected_stroke.value
    if not stroke_name:
        stroke_name = "Freestyle"
        
    stroke_title = str(stroke_name).title()
    icon = STROKE_ICONS.get(stroke_title, "🏊")
    st.markdown(
        f"""<div style="display:inline-block; background:linear-gradient(135deg,#0055FF,#00F0FF);
        color:white; padding:8px 22px; border-radius:25px; font-size:1.1rem;
        font-weight:700; letter-spacing:0.5px; margin-bottom:14px; box-shadow: 0 4px 12px rgba(0,85,255,0.35);">
        {icon} Swimming Stroke: <strong>{stroke_title}</strong>
        </div>""",
        unsafe_allow_html=True
    )
    
    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    
    vqa_score = analysis_result.vqa_result.overall_score if analysis_result.vqa_result else None
    vqa_class = analysis_result.vqa_result.quality_class if analysis_result.vqa_result else "Unknown"
    
    rel = getattr(analysis_result, 'reliability', None)
    tech_score = analysis_result.report.overall_score if analysis_result.report else None
    if tech_score is not None:
        tech_score_str = f"{tech_score:.1f}/100"
    else:
        tech_score_str = "⚠ INSUFFICIENT_EVIDENCE"
    
    with summary_col1:
        st.metric("Overall Technique Score", tech_score_str)
    with summary_col2:
        st.metric("Video Quality", f"{vqa_score}/100" if vqa_score is not None else "UNAVAILABLE", delta=vqa_class, delta_color="off")
    with summary_col3:
        st.metric("Analysis Reliability", f"{rel.analysis_reliability_score:.1f}%" if rel is not None and getattr(rel, 'analysis_reliability_score', None) is not None else "UNAVAILABLE", delta=getattr(rel, 'analysis_reliability_level', 'Medium'), delta_color="normal")
    with summary_col4:
        st.metric("Scientific Confidence", getattr(rel, 'scientific_confidence', 'Medium') if rel else "Medium", delta="User Selected", delta_color="off")

    if rel:
        with st.expander("🔬 Analysis Data Reliability & Pose Tracking Quality Breakdown", expanded=False):
            sci_status = getattr(rel, 'scientific_validation_status', 'NOT_VALIDATED — INSUFFICIENT GROUND TRUTH')
            st.info(f"**Empirical Scientific Validation Status:** `{sci_status}`\n\n*(Pose tracking reliability reflects video signal quality; physical accuracy is currently unvalidated pending empirical Ground Truth).*")
            st.caption("ℹ️ These metrics measure video tracking stability, landmark visibility, and frame completeness for the requested stroke analysis — NOT stroke style classification.")
            rcol1, rcol2, rcol3, rcol4, rcol5 = st.columns(5)
            cov = getattr(rel, 'pose_tracking_coverage_pct', getattr(rel, 'frame_coverage_pct', 0.0))
            rcol1.metric("Tracking Coverage", f"{cov:.1f}%")
            rcol2.metric("Landmark Visibility", f"{rel.landmark_visibility_pct:.1f}%")
            rcol3.metric("Temporal Stability", f"{rel.temporal_stability_pct:.1f}%")
            rcol4.metric("Cycle Quality", f"{rel.cycle_quality_pct:.1f}%")
            rcol5.metric("Pose Validity", f"{rel.pose_validity_pct:.1f}%")
            if rel.reasons:
                st.markdown("**Data Quality Notes / Limitations:**")
                for r in rel.reasons:
                    st.markdown(f"- ⚠️ {r}")

    safe_log("[TRACE] EXIT render_summary")

def render_consistency(analysis_result):
    safe_log("[TRACE] ENTER render_consistency")
    if getattr(analysis_result, 'consistency', None):
        cons = analysis_result.consistency
        with st.expander("Analysis Consistency & Scientific Trustworthiness", expanded=(cons.validation_status != "Passed")):
            cons_col1, cons_col2, cons_col3 = st.columns(3)
            cons_col1.metric("Validation Status", cons.validation_status)
            cons_col2.metric("Scientific Confidence", cons.scientific_confidence)
            cons_score_str = f"{cons.overall_score:.1f}/100" if cons.overall_score is not None else "⚠ INSUFFICIENT_EVIDENCE"
            cons_col3.metric("Consistency Score", cons_score_str)
            
            if cons.warnings:
                for w in cons.warnings:
                    if cons.validation_status == "Critical":
                        st.error(w)
                    else:
                        st.warning(w)
                        
            st.markdown(f"**Passed Rules:** {len(cons.passed_rules)}")
            st.markdown(f"**Failed Rules:** {len(cons.failed_rules)}")
    safe_log("[TRACE] EXIT render_consistency")

def render_report_tab(analysis_result):
    safe_log("[TRACE] ENTER render_report_tab")
    if analysis_result.report:
        st.markdown(f"**Feedback:** {analysis_result.report.feedback_summary}")
        
        def format_metric(m_obj, is_length=False):
            if getattr(m_obj, 'is_insufficient_data', False):
                return "Insufficient Data"
            if not m_obj.valid:
                return "N/A"
            if m_obj.value is None:
                return "UNAVAILABLE"
            val_str = f"{m_obj.value:.2f}" if is_length else f"{m_obj.value:.1f}"
            est_str = " (est)" if getattr(m_obj, 'is_estimated', False) else ""
            return f"{val_str}{est_str}"
            
        st.markdown("##### Key Metrics")
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            sr_str = format_metric(analysis_result.report.stroke_rate)
            sym_str = format_metric(analysis_result.report.stroke_symmetry)
            st.metric("Stroke Rate", f"{sr_str}" + (" spm" if sr_str not in {"N/A", "UNAVAILABLE", "Insufficient Data"} else ""))
            st.metric("Stroke Symmetry", f"{sym_str}" + ("%" if sym_str not in {"N/A", "UNAVAILABLE", "Insufficient Data"} else ""))
        with m_col2:
            sl_str = format_metric(analysis_result.report.stroke_length, is_length=True)
            kf_str = format_metric(analysis_result.report.kick_frequency)
            st.metric("Stroke Length", f"{sl_str}" + (" (rel)" if sl_str not in {"N/A", "UNAVAILABLE", "Insufficient Data"} else ""))
            st.metric("Kick Frequency", f"{kf_str}" + (" Hz" if kf_str not in {"N/A", "UNAVAILABLE", "Insufficient Data"} else ""))
        
        st.caption("*Legend: (est) = Estimated Value. N/A = Unavailable Value.*")
        
        st.markdown("##### Detected Errors")
        if not analysis_result.report.errors:
            st.success("No significant technique errors detected!")
        else:
            for error in analysis_result.report.errors:
                with st.expander(f"{error.error_type} - {error.severity} Severity (Conf: {getattr(error, 'confidence', 1.0)*100:.0f}%)"):
                    st.write(error.description)
                    st.caption(f"Occurred at frame {error.frame_index} ({error.timestamp_ms / 1000.0:.2f} seconds)")
    else:
        st.info("Performance report not available.")
    safe_log("[TRACE] EXIT render_report_tab")

