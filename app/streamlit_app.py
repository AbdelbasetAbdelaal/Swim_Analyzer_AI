"""
Streamlit Web Application entry point.
Acts purely as the presentation layer.
"""
import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

# Add the root directory to PYTHONPATH so that absolute imports work from within streamlit
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.ui.charts import create_performance_trend_chart, create_cycles_trend_chart
import streamlit as st
from core.config import config
from core.constants import APP_TITLE
from services.analysis_service import AnalysisService
from services.athlete_service import AthleteService
from services.analysis_history_service import AnalysisHistoryService
from services.comparison_service import ComparisonService
from services.pdf_report_service import PDFReportService
from models.analysis_session import AnalysisSession
from services.auth_service import AuthService
from core.logger import setup_logger


logger = setup_logger(__name__)

def safe_log(msg: str):
    logger.info(msg)


# Global stroke icons mapping
STROKE_ICONS = {
    "Freestyle": "🏊",
    "Backstroke": "🔄",
    "Breaststroke": "🐸",
    "Butterfly": "🦋",
    "Auto Detect": "🔍",
}

# --- MODULAR RENDERING FUNCTIONS WITH TRACE LOGGING ---
from app.ui.tabs.summary_tab import render_executive_summary_card, render_summary, render_consistency, render_report_tab
from app.ui.tabs.charts_tab import render_raw_data_tab
from app.ui.tabs.downloads_tab import render_video_section, render_download_buttons
from app.ui.pages.admin_console import render_admin_dashboard_page


def render_athletes_page():
    st.title("👥 Athletes")
    st.markdown("Create and manage athlete profiles for longitudinal tracking and personalized analysis.")
    
    athlete_service = AthleteService()
    current_coach_id = st.session_state.current_coach.coach_id if st.session_state.get("current_coach") else None
    profiles = athlete_service.get_all_profiles(coach_id=current_coach_id)
    
    tab1, tab2 = st.tabs(["Athlete Directory", "Create New Athlete"])
    
    with tab1:
        if not profiles:
            st.info("No athlete profiles found. Create one in the next tab.")
        else:
            for p in profiles:
                with st.container(border=True):
                    col_info, col_btn = st.columns([3, 1])
                    with col_info:
                        st.markdown(f"### 👤 {p.full_name}")
                        st.markdown(f"**Level:** {p.swimming_level} | **Stroke:** {p.preferred_stroke}")
                    with col_btn:
                        if st.button("View Profile", key=f"view_{p.athlete_id}", width="stretch"):
                            st.session_state.viewing_athlete_id = p.athlete_id
                            st.rerun()

    with tab2:
        with st.form("create_athlete_form"):
            st.subheader("New Athlete Profile")
            full_name = st.text_input("Full Name *")
            
            col1, col2 = st.columns(2)
            age = col1.number_input("Age *", min_value=1, max_value=150, value=25)
            gender = col2.selectbox("Gender *", ["Male", "Female", "Other"])
            
            col3, col4 = st.columns(2)
            height = col3.number_input("Height (cm) *", min_value=50.0, max_value=300.0, value=175.0)
            weight = col4.number_input("Weight (kg) *", min_value=20.0, max_value=200.0, value=70.0)
            
            col5, col6 = st.columns(2)
            level = col5.selectbox("Swimming Level *", ["Beginner", "Intermediate", "Advanced", "Elite"])
            stroke = col6.selectbox("Preferred Stroke *", ["Freestyle", "Backstroke", "Breaststroke", "Butterfly"])
            
            notes = st.text_area("Notes")
            
            submitted = st.form_submit_button("Create Profile")
            if submitted:
                if not full_name.strip():
                    st.error("Full Name is required.")
                else:
                    existing_profiles = athlete_service.get_all_profiles(coach_id=current_coach_id)
                    name_exists = any(p.full_name.lower() == full_name.strip().lower() for p in existing_profiles)
                    if name_exists:
                        st.error(f"An athlete with the name '{full_name.strip()}' already exists. Please use a unique name.")
                    else:
                        athlete_service.create_profile(
                            coach_id=current_coach_id,
                            full_name=full_name.strip(),
                            age=age,
                            gender=gender,
                            height_cm=height,
                            weight_kg=weight,
                            swimming_level=level,
                            preferred_stroke=stroke,
                            notes=notes
                        )
                        st.success(f"Athlete profile for '{full_name}' created successfully!")
                        st.rerun()

def render_athlete_profile_page():
    coach = st.session_state.get("current_coach")
    current_coach_id = coach.coach_id if coach else None
    athlete_id = st.session_state.viewing_athlete_id
    athlete_service = AthleteService()
    profile = athlete_service.load_profile(athlete_id, current_coach_id)
    
    if not profile:
        st.error("Athlete profile not found.")
        st.session_state.viewing_athlete_id = None
        st.rerun()
        return

    col1, col2, col3 = st.columns([1, 7, 3])
    with col1:
        if st.button("⬅️ Back"):
            st.session_state.viewing_athlete_id = None
            st.rerun()
    with col2:
        st.title(f"🏊 {profile.full_name}")
    with col3:
        st.write("") # Spacing
        history_service = AnalysisHistoryService()
        history = history_service.get_sessions_by_athlete(athlete_id, current_coach_id)
        
        # Generate PDF on the fly
        try:
            pdf_service = PDFReportService()
            current_coach = st.session_state.get("current_coach")
            pdf_path = pdf_service.generate_athlete_summary(profile, history, coach=current_coach)
            with open(pdf_path, "rb") as pdf_file:
                PDFbyte = pdf_file.read()
            st.download_button(
                label="📄 Download PDF Report",
                data=PDFbyte,
                file_name=os.path.basename(pdf_path),
                mime='application/pdf',
                type="primary",
                width="stretch"
            )
        except Exception as e:
            st.error(f"PDF Error: {e}")
    
    st.markdown(f"**Level:** {profile.swimming_level} | **Preferred Stroke:** {profile.preferred_stroke}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Age", f"{profile.age} yrs")
    c2.metric("Gender", profile.gender)
    c3.metric("Height", f"{profile.height_cm} cm")
    c4.metric("Weight", f"{profile.weight_kg} kg")
    
    st.markdown("---")
    st.subheader("🎯 Coach Notes & Goals")
    
    with st.expander("📝 Edit Notes & Goals", expanded=False):
        with st.form("edit_notes_form"):
            new_notes = st.text_area("Coach Notes", value=profile.notes, height=100)
            new_goals = st.text_area("Training Goals (Short/Long term)", value=profile.training_goals, height=100)
            
            if st.form_submit_button("Save Notes", type="primary"):
                profile.notes = new_notes
                profile.training_goals = new_goals
                if athlete_service.update_profile(profile, current_coach_id):
                    st.success("Notes and goals updated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to save. Check logs.")
                    
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        if profile.notes:
            st.info(f"**Notes:**\n\n{profile.notes}")
        else:
            st.caption("No notes recorded.")
    with col_n2:
        if profile.training_goals:
            st.success(f"**Training Goals:**\n\n{profile.training_goals}")
        else:
            st.caption("No training goals set.")
        
    st.markdown("---")
    st.subheader("📊 Analysis History")
    
    history_service = AnalysisHistoryService()
    history = history_service.get_sessions_by_athlete(athlete_id, current_coach_id)
    
    if not history:
        st.info("No analyses recorded for this athlete yet.")
    else:
        history_data = []
        for s in history:
            history_data.append({
                "Date": s.analysis_timestamp.split("T")[0],
                "Time": s.analysis_timestamp.split("T")[1][:5],
                "Score": round(s.performance_score, 1) if s.performance_score is not None else None,
                "Confidence": s.scientific_confidence,
                "Stroke": s.stroke_type,
                "Cycles": s.completed_cycles,
                "Proc. Time (s)": round(s.processing_time_seconds, 1) if (s and getattr(s, 'processing_time_seconds', None) is not None) else None
            })
        
        if len(history) >= 2:
            st.markdown("### 📈 Performance Progression")
            df = pd.DataFrame(history_data)
            
            c_trend1, c_trend2 = st.columns(2)
            with c_trend1:
                st.plotly_chart(create_performance_trend_chart(df), width="stretch")
            with c_trend2:
                st.plotly_chart(create_cycles_trend_chart(df), width="stretch")
            st.markdown("---")
            
        st.dataframe(history_data, width="stretch")
        
        # --- PHASE 7: Session Comparison ---
        if len(history) >= 2:
            st.markdown("---")
            st.subheader("⚖️ Compare Sessions")
            st.markdown("Select two sessions below to visualize technique changes and performance progression.")
            
            # Create a dictionary to map a friendly display string to the session object
            session_options = {}
            for i, s in enumerate(history):
                # Using index to ensure uniqueness if timestamp is identical
                date_str = s.analysis_timestamp.split("T")[0]
                time_str = s.analysis_timestamp.split("T")[1][:5]
                score_label = f"{s.performance_score:.1f}" if s.performance_score is not None else "INSUFFICIENT_EVIDENCE"
                label = f"{date_str} {time_str} | Score: {score_label} | {s.stroke_type} ({i})"
                session_options[label] = s
                
            col_sel_a, col_sel_b = st.columns(2)
            options_list = list(session_options.keys())
            
            with col_sel_a:
                sel_a_label = st.selectbox("Select Session A (Baseline)", options=options_list, index=len(options_list)-1)
            with col_sel_b:
                sel_b_label = st.selectbox("Select Session B (Recent)", options=options_list, index=0)
                
            if st.button("Generate Comparison Report", type="primary"):
                sess_a = session_options[sel_a_label]
                sess_b = session_options[sel_b_label]
                
                comp_service = ComparisonService()
                report = comp_service.compare_sessions(sess_a, sess_b)
                
                st.markdown("### Comparison Results")
                
                # Render Coach Summary if present
                if report.coach_summary:
                    st.info(f"**Coach Summary:** {report.coach_summary}")
                
                # Render Metrics
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                
                if report.overall_score_delta:
                    col_m1.metric("Overall Score", 
                                  f"{report.overall_score_delta.new_value:.1f}", 
                                  f"{report.overall_score_delta.delta:.1f}")
                                  
                if report.confidence_delta:
                    color = "normal" if report.confidence_delta.is_improvement else "inverse"
                    if report.confidence_delta.delta == 0: color = "off"
                    col_m2.metric("Scientific Confidence", 
                                  report.confidence_delta.new_label, 
                                  f"{report.confidence_delta.delta} levels", delta_color=color)
                                  
                if report.cycles_delta:
                    col_m3.metric("Completed Cycles", 
                                  f"{int(report.cycles_delta.new_value)}", 
                                  f"{int(report.cycles_delta.delta)}")
                                  
                if report.cycle_duration_delta:
                    # Note: for duration, negative is usually better, which is_improvement handles conceptually,
                    # but Streamlit native metric interprets negative delta as red by default unless inverse.
                    # We'll let Streamlit default behavior work: negative time = red (bad) wait, inverse is better.
                    col_m4.metric("Avg Cycle Duration", 
                                  f"{report.cycle_duration_delta.new_value:.0f} ms", 
                                  f"{report.cycle_duration_delta.delta:.0f} ms", delta_color="inverse")
                                  
                # Technique Deltas
                if report.technique_deltas:
                    st.markdown("#### Technique Metrics")
                    tech_cols = st.columns(len(report.technique_deltas))
                    for i, t_delta in enumerate(report.technique_deltas):
                        with tech_cols[i]:
                            st.metric(t_delta.metric_name, 
                                      f"{t_delta.new_value:.2f} {t_delta.unit}".strip(), 
                                      f"{t_delta.delta:.2f} {t_delta.unit}".strip())
                                      
                # Movement Errors
                col_e1, col_e2, col_e3 = st.columns(3)
                with col_e1:
                    st.markdown("🟢 **Resolved Errors**")
                    if report.resolved_errors:
                        for e in report.resolved_errors: st.markdown(f"- {e}")
                    else: st.caption("None")
                with col_e2:
                    st.markdown("🔴 **New Errors**")
                    if report.new_errors:
                        for e in report.new_errors: st.markdown(f"- {e}")
                    else: st.caption("None")
                with col_e3:
                    st.markdown("🟡 **Persistent Errors**")
                    if report.persistent_errors:
                        for e in report.persistent_errors: st.markdown(f"- {e}")
                    else: st.caption("None")
                    
                # Video Side-by-Side
                if report.video_path_a and report.video_path_b:
                    st.markdown("#### Video Comparison 🔗")
                    vid_col1, vid_col2 = st.columns(2)
                    try:
                        # Construct absolute paths
                        video_a_full = config.output_dir / report.video_path_a
                        video_b_full = config.output_dir / report.video_path_b
                        
                        with vid_col1:
                            st.markdown(f"**Session A:** {sel_a_label}")
                            if video_a_full.exists():
                                with open(video_a_full, 'rb') as f1: st.video(f1.read())
                            else:
                                st.warning("Video file missing.")
                        with vid_col2:
                            st.markdown(f"**Session B:** {sel_b_label}")
                            if video_b_full.exists():
                                with open(video_b_full, 'rb') as f2: st.video(f2.read())
                            else:
                                st.warning("Video file missing.")
                    except Exception as e:
                        st.warning(f"Could not load comparison videos: {e}")

def render_history_page():
    """Renders the Standalone Analysis History & Session Comparison Page."""
    coach = st.session_state.get("current_coach")
    current_coach_id = coach.coach_id if coach else None
    current_role = coach.role if coach else None

    if current_role == "admin":
        st.title("🏛 Admin Analysis History")
        st.markdown("Review site-wide analysis history and session records across all accounts.")
    elif current_role == "coach":
        st.title("📉 My Team Analysis History")
        st.markdown("Review analysis sessions linked to your coach account and roster.")
    else:
        st.title("📉 My Analysis History")
        st.markdown("Review analysis sessions uploaded using your user account.")
    st.markdown("---")

    history_service = AnalysisHistoryService()
    athlete_service = AthleteService()
    
    profiles = athlete_service.get_all_profiles(coach_id=current_coach_id) if current_role == "coach" else []
    athlete_map = {p.athlete_id: p.full_name for p in profiles}

    if current_role == "admin":
        history = history_service.get_all_sessions(st.session_state.current_coach)
    elif current_coach_id:
        history = history_service.get_sessions_by_account(current_coach_id)
    else:
        history = []

    if current_coach_id:
        st.info(f"Signed in as **{coach.full_name}** ({coach.role.title()}) — account ID: `{current_coach_id}`")

    if not history:
        if current_role == "admin":
            st.info("No analysis sessions are currently recorded in the system.")
        elif current_role == "coach":
            st.info("No analysis sessions have been saved for your coach account yet.")
        else:
            st.info("No personal analysis session uploads found for your account yet.")
        return

    history_data = []
    for s in history:
        if s.athlete_id:
            swimmer_name = athlete_map.get(s.athlete_id, "Guest Swimmer")
        elif s.account_id:
            swimmer_name = "Personal Account Upload"
        else:
            swimmer_name = "Guest Swimmer"
        date_str = s.analysis_timestamp.split("T")[0] if "T" in s.analysis_timestamp else s.analysis_timestamp[:10]
        time_str = s.analysis_timestamp.split("T")[1][:5] if "T" in s.analysis_timestamp else ""
        history_data.append({
            "Session ID": s.session_id[:8],
            "Swimmer": swimmer_name,
            "Date": date_str,
            "Time": time_str,
            "Stroke": s.stroke_type,
            "Score": round(s.performance_score, 1) if s.performance_score is not None else None,
            "Confidence": s.scientific_confidence,
            "Cycles": s.completed_cycles,
            "Proc. Time (s)": round(s.processing_time_seconds, 1) if (s and getattr(s, 'processing_time_seconds', None) is not None) else None
        })

    st.markdown("### 📋 Recorded Session Logs")
    st.dataframe(history_data, width="stretch")

    # Session Comparison Tool
    if len(history) >= 2:
        st.markdown("---")
        st.subheader("⚖️ Session-to-Session Comparison Tool")
        st.markdown("Select two sessions below to analyze technical progression, resolved movement errors, and score deltas.")

        session_options = {}
        for i, s in enumerate(history):
            if s.athlete_id:
                swimmer = athlete_map.get(s.athlete_id, "Guest")
            elif s.account_id:
                swimmer = "Personal Account Upload"
            else:
                swimmer = "Guest"
            date_str = s.analysis_timestamp.split("T")[0] if "T" in s.analysis_timestamp else s.analysis_timestamp[:10]
            score_label = f"{s.performance_score:.1f}" if s.performance_score is not None else "INSUFFICIENT_EVIDENCE"
            label = f"{swimmer} | {date_str} | Score: {score_label} | {s.stroke_type} ({s.session_id[:6]})"
            session_options[label] = s

        col_a, col_b = st.columns(2)
        options_list = list(session_options.keys())

        with col_a:
            sel_a_label = st.selectbox("Select Session A (Baseline)", options=options_list, index=len(options_list)-1, key="hist_sel_a")
        with col_b:
            sel_b_label = st.selectbox("Select Session B (Recent)", options=options_list, index=0, key="hist_sel_b")

        if st.button("Generate Comparison Report", type="primary", key="hist_comp_btn"):
            sess_a = session_options[sel_a_label]
            sess_b = session_options[sel_b_label]

            comp_service = ComparisonService()
            report = comp_service.compare_sessions(sess_a, sess_b)

            st.markdown("### Comparison Results")

            if report.coach_summary:
                st.info(f"**Coach Summary:** {report.coach_summary}")

            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            if report.overall_score_delta:
                col_m1.metric("Overall Score Delta", f"{report.overall_score_delta.new_value:.1f}", f"{report.overall_score_delta.delta:+.1f}")
            if report.confidence_delta:
                col_m2.metric("Scientific Confidence", report.confidence_delta.new_label, f"{report.confidence_delta.delta:+} levels")
            if report.cycles_delta:
                col_m3.metric("Completed Cycles", f"{int(report.cycles_delta.new_value)}", f"{int(report.cycles_delta.delta):+d}")
            if report.cycle_duration_delta:
                col_m4.metric("Avg Cycle Duration", f"{report.cycle_duration_delta.new_value:.0f} ms", f"{report.cycle_duration_delta.delta:+.0f} ms", delta_color="inverse")

            if report.technique_deltas:
                st.markdown("#### Technique Metrics Delta")
                tech_cols = st.columns(len(report.technique_deltas))
                for i, t_delta in enumerate(report.technique_deltas):
                    with tech_cols[i]:
                        st.metric(t_delta.metric_name, f"{t_delta.new_value:.2f} {t_delta.unit}".strip(), f"{t_delta.delta:+.2f} {t_delta.unit}".strip())

            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                st.markdown("🟢 **Resolved Errors**")
                if report.resolved_errors:
                    for e in report.resolved_errors: st.markdown(f"- {e}")
                else: st.caption("None")
            with col_e2:
                st.markdown("🔴 **New Errors**")
                if report.new_errors:
                    for e in report.new_errors: st.markdown(f"- {e}")
                else: st.caption("None")
            with col_e3:
                st.markdown("🟡 **Persistent Errors**")
                if report.persistent_errors:
                    for e in report.persistent_errors: st.markdown(f"- {e}")
                else: st.caption("None")
        
def render_dashboard_page():
    """Renders the Coach Command Center / Dashboard Hub."""
    coach = st.session_state.get("current_coach")
    coach_name = coach.full_name if coach else "Coach"
    current_coach_id = coach.coach_id if coach else None

    athlete_service = AthleteService()
    history_service = AnalysisHistoryService()

    try:
        profiles = athlete_service.get_all_profiles(coach_id=current_coach_id)
        all_sessions = history_service.get_sessions_by_account(current_coach_id)
    except Exception:
        profiles = []
        all_sessions = []
    
    # Filter sessions belonging to this coach's roster
    coach_athlete_ids = {p.athlete_id for p in profiles}
    roster_sessions = [s for s in all_sessions if s.athlete_id in coach_athlete_ids]

    st.title(f"📊 {coach_name}'s Command Center")
    st.markdown("Team performance overview, roster health metrics, and instant video analysis hub.")
    st.markdown("---")

    # Primary Action CTA Card
    cta_col1, cta_col2 = st.columns([3, 1])
    with cta_col1:
        st.markdown("### Ready to analyze a new swim session?")
        st.caption("Upload underwater or poolside video to run 3D pose detection and scientific biomechanics analysis.")
    with cta_col2:
        st.write("")
        if st.button("➕ Analyze New Video", type="primary", width="stretch"):
            st.session_state["_target_nav"] = "🏊‍♂️ Video Analysis"
            st.rerun()

    st.markdown("---")

    # Team KPI Summary Cards
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    total_athletes = len(profiles)
    total_sessions = len(roster_sessions)
    
    scores = [s.performance_score for s in roster_sessions if s.performance_score is not None]
    avg_score = (sum(scores) / len(scores)) if scores else None

    # At-risk athletes (athletes with average score < 70)
    athlete_scores = {}
    for s in roster_sessions:
        if s.athlete_id:
            if s.performance_score is not None:
                athlete_scores.setdefault(s.athlete_id, []).append(s.performance_score)
            
    at_risk_count = sum(1 for aid, scs in athlete_scores.items() if (sum(scs)/len(scs)) < 72.0)
    
    # Top improver calculation
    top_improver_name = "None"
    max_gain = -999.0
    for p in profiles:
        p_scs = athlete_scores.get(p.athlete_id, [])
        if len(p_scs) >= 2:
            v_latest = p_scs[0]
            v_earliest = p_scs[-1]
            if v_latest is not None and v_earliest is not None:
                gain = v_latest - v_earliest
                if gain > max_gain and gain > 0:
                    max_gain = gain
                    top_improver_name = p.full_name

    kpi1.metric("👥 Total Athletes", total_athletes)
    kpi2.metric("🎥 Total Analyses", total_sessions)
    kpi3.metric("📈 Team Avg Score", f"{avg_score:.1f}/100" if avg_score is not None else "INSUFFICIENT_EVIDENCE")
    kpi4.metric("⚠️ Needs Attention", at_risk_count, delta="-Needs Drill Work" if at_risk_count > 0 else "Optimal", delta_color="inverse")
    kpi5.metric("🏆 Top Improver", top_improver_name, delta=f"+{max_gain:.1f} pts" if max_gain > 0 else None)

    st.markdown("---")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("### ⚠️ Athletes Needing Attention")
        if at_risk_count == 0:
            st.success("All swimmers in your roster are performing above the 72.0 benchmark threshold!")
        else:
            for p in profiles:
                p_scs = athlete_scores.get(p.athlete_id, [])
                if p_scs:
                    latest_sc = p_scs[0]
                    if latest_sc is not None and latest_sc < 72.0:
                        with st.container(border=True):
                            c_info, c_btn = st.columns([3, 1])
                            with c_info:
                                st.markdown(f"**👤 {p.full_name}** ({p.swimming_level})")
                                st.caption(f"Latest Score: **{latest_sc:.1f}/100** | Stroke: {p.preferred_stroke}")
                            with c_btn:
                                if st.button("Inspect", key=f"dash_risk_{p.athlete_id}", width="stretch"):
                                    st.session_state.viewing_athlete_id = p.athlete_id
                                    st.session_state["_target_nav"] = "👥 Athletes"
                                    st.rerun()

    with col_right:
        st.markdown("### 📅 Recent Team Activity Log")
        if not roster_sessions:
            st.info("No swimming analysis sessions logged yet.")
        else:
            athlete_map = {p.athlete_id: p.full_name for p in profiles}
            act_rows = []
            for s in roster_sessions[:6]:
                date_str = s.analysis_timestamp.replace("T", " ")[:16]
                name = athlete_map.get(s.athlete_id, "Guest") if s.athlete_id else "Guest"
                act_rows.append({
                    "Date & Time": date_str,
                    "Athlete": name,
                    "Stroke": s.stroke_type,
                    "Score": f"{s.performance_score:.1f}" if s.performance_score is not None else "INSUFFICIENT_EVIDENCE",
                    "Cycles": s.completed_cycles
                })
            st.dataframe(act_rows, width="stretch")


def render_login_portal():
    """Renders main page Login / Registration Portal when no account is logged in."""
    st.title("🏊‍♂️ SwimAnalyzer AI — Account Portal")
    st.markdown("### Welcome to Professional Swimming Performance Analysis")
    st.info("Sign in to continue with your account, or register as a user to analyze videos without coaching access.")

    tab1, tab2 = st.tabs(["🔐 Sign In", "📝 Register New Account"])

    with tab1:
        with st.form("main_login_form"):
            st.markdown("#### Account Sign In")
            sign_in_role = st.radio(
                "Sign in as:",
                ["User", "Coach", "Admin"],
                index=1,
                horizontal=True
            )

            role_help_text = {
                "User": "Create or use a personal user account for your own analysis history.",
                "Coach": "Sign in as a coach to manage athletes, rosters, and team sessions.",
                "Admin": "Sign in as admin to manage accounts, athletes, and site-wide records."
            }
            st.caption(role_help_text[sign_in_role])

            username = st.text_input("Username", key="main_user")
            password = st.text_input("Password", type="password", key="main_pass")
            submitted = st.form_submit_button("Sign In", type="primary", width="stretch")
            if submitted:
                ok, msg, logged_account = AuthService.login(username, password)
                if ok:
                    st.session_state.current_coach = logged_account
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with tab2:
        with st.form("main_register_form"):
            st.markdown("#### Create New Account")
            new_username = st.text_input("Username", key="reg_user")
            new_fullname = st.text_input("Full Name", key="reg_name")
            new_email = st.text_input("Email Address", key="reg_email")
            new_password = st.text_input("Password (min 6 characters)", type="password", key="reg_pass")
            account_type = st.radio("Account Type", ["User", "Coach"], index=0, horizontal=True)
            submitted = st.form_submit_button("Create Account", type="primary", width="stretch")
            if submitted:
                role = "user" if account_type == "User" else "coach"
                ok, msg, new_account = AuthService.register_coach(new_username, new_password, new_fullname, new_email, role=role)
                if ok:
                    st.session_state.current_coach = new_account
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


def render_coach_auth_sidebar():
    """Renders Authentication card in sidebar."""
    st.sidebar.markdown("### 🔐 Account")
    
    # Ensure default demo accounts exist in DB once per session
    if not st.session_state.get("_db_seeded"):
        try:
            AuthService.seed_default_coach()
            st.session_state["_db_seeded"] = True
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            st.sidebar.error("Service temporarily unavailable. Please try again later.")
            st.stop()

    if "current_coach" not in st.session_state:
        st.session_state.current_coach = None

    coach = st.session_state.current_coach
    if coach:
        st.sidebar.markdown(
            f"""<div style="background:linear-gradient(135deg,#0055FF,#00F0FF); color:white;
            padding:10px 14px; border-radius:10px; margin-bottom:10px;">
            <div style="font-weight:bold; font-size:1.05rem;">📋 {coach.full_name}</div>
            <div style="font-size:0.8rem; opacity:0.9;">Role: {coach.role.title()} | @{coach.username}</div>
            </div>""",
            unsafe_allow_html=True
        )
        if st.sidebar.button("🚪 Logout", key="logout_btn", width="stretch"):
            st.session_state.current_coach = None
            st.session_state.viewing_athlete_id = None
            st.session_state["nav_mode"] = "📊 Coach Dashboard"
            st.rerun()
    else:
        st.sidebar.warning("Not Logged In")
        auth_mode = st.sidebar.radio("Account Action", ["Sign In", "Register New Account"], label_visibility="collapsed")
        if auth_mode == "Sign In":
            with st.sidebar.form("coach_login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign In", type="primary", width="stretch")
                if submitted:
                    ok, msg, logged_coach = AuthService.login(username, password)
                    if ok:
                        st.session_state.current_coach = logged_coach
                        st.sidebar.success(msg)
                        st.rerun()
                    else:
                        st.sidebar.error(msg)
        else:
            with st.sidebar.form("coach_register_form"):
                new_username = st.text_input("New Username")
                new_fullname = st.text_input("Full Name")
                new_email = st.text_input("Email (Optional)")
                new_password = st.text_input("New Password", type="password")
                account_type = st.radio("Account Type", ["User", "Coach"], index=0, horizontal=True)
                submitted = st.form_submit_button("Register Account", type="primary", width="stretch")
                if submitted:
                    role = "user" if account_type == "User" else "coach"
                    ok, msg, new_coach = AuthService.register_coach(new_username, new_password, new_fullname, new_email, role=role)
                    if ok:
                        st.session_state.current_coach = new_coach
                        st.sidebar.success(msg)
                        st.rerun()
                    else:
                        st.sidebar.error(msg)
    st.sidebar.markdown("---")


def main():
    safe_log("STREAMLIT APP RERUN")
    st.set_page_config(
        page_title=APP_TITLE,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Render Coach Auth Widget
    render_coach_auth_sidebar()

    # Require Login to access platform features
    if not st.session_state.get("current_coach"):
        render_login_portal()
        return

    if "viewing_athlete_id" not in st.session_state:
        st.session_state.viewing_athlete_id = None

    current_role = st.session_state.current_coach.role if st.session_state.get("current_coach") else None
    if current_role == "admin":
        nav_options = ["🏛 Admin Console", "📚 Reference Data Manager", "📊 Coach Dashboard", "🏊‍♂️ Video Analysis", "👥 Athletes", "📉 Analysis History"]
    elif current_role == "coach":
        nav_options = ["📊 Coach Dashboard", "📚 Reference Data Manager", "🏊‍♂️ Video Analysis", "👥 Athletes", "📉 Analysis History"]
    else:
        nav_options = ["🏊‍♂️ Video Analysis", "📚 Reference Data Manager", "📉 Analysis History"]

    if "_target_nav" in st.session_state:
        target = st.session_state.pop("_target_nav")
        if target in nav_options:
            st.session_state["nav_mode"] = target

    if "nav_mode" not in st.session_state or st.session_state["nav_mode"] not in nav_options:
        st.session_state["nav_mode"] = nav_options[0]

    st.sidebar.markdown("### Navigation")
    app_mode = st.sidebar.radio("Go to:", nav_options, key="nav_mode", label_visibility="collapsed")
    st.sidebar.markdown("---")

    if current_role == "admin" and st.session_state.get("trigger_sci_db_update", False):
        st.markdown("---")
        st.info("🔄 Initiating ONE Scientific Literature Database Update Transaction...")
        st.caption("Searching PubMed, PMC, Europe PMC for peer-reviewed swimming literature, verifying provenance, and rebuilding coverage matrix...")

        prog_bar = st.progress(0, text="Starting scientific database update...")
        prog_status = st.empty()

        def ui_progress_cb(msg: str, pct: int):
            prog_bar.progress(pct, text=f"{msg} ({pct}%)")
            prog_status.markdown(f"⏳ **{msg}**")

        from services.scientific_updater_service import ScientificUpdaterService
        updater = ScientificUpdaterService()
        res = updater.run_update_cycle(progress_callback=ui_progress_cb)

        st.session_state["trigger_sci_db_update"] = False
        st.session_state["last_sci_db_update_res"] = res
        st.rerun()

    if app_mode == "🏛 Admin Console":
        render_admin_dashboard_page()
        return
    elif app_mode == "📚 Reference Data Manager":
        from app.ui.reference_data_ui import render_reference_data_manager_page
        render_reference_data_manager_page()
        return
    elif app_mode == "📊 Coach Dashboard":
        render_dashboard_page()
        return
    elif app_mode == "👥 Athletes":
        if st.session_state.viewing_athlete_id:
            render_athlete_profile_page()
        else:
            render_athletes_page()
        return
    elif app_mode == "📉 Analysis History":
        render_history_page()
        return

    st.title(f"🏊‍♂️ {APP_TITLE}")
    st.markdown("### Professional Swimming Performance Analysis Platform")
    st.markdown("Upload a recorded swimming video to generate a biomechanical analysis overlay.")

    # Sidebar: Current Athlete
    st.sidebar.markdown("### Current Athlete")
    athlete_service = AthleteService()
    current_coach_id = st.session_state.current_coach.coach_id if st.session_state.get("current_coach") else None
    current_role = st.session_state.current_coach.role if st.session_state.get("current_coach") else None
    profiles = athlete_service.get_all_profiles(coach_id=current_coach_id) if current_role == "coach" else []
    
    if current_role == "coach":
        athlete_options = {"None": "Guest Session"}
        for p in profiles:
            athlete_options[p.athlete_id] = f"{p.full_name} ({p.swimming_level})"
        selected_athlete_id = st.sidebar.selectbox(
            "Select Profile", 
            options=list(athlete_options.keys()), 
            format_func=lambda x: athlete_options[x],
            label_visibility="collapsed"
        )
    else:
        selected_athlete_id = "None"
        st.sidebar.markdown("**Upload type:** Personal account analysis")

    st.sidebar.markdown("---")

    # Main UI: Athlete / Account Summary Card
    if current_role == "coach":
        if selected_athlete_id == "None":
            st.info("ℹ️ **Guest Session:** Analysis will not be linked to an athlete profile.")
        else:
            selected_profile = next((p for p in profiles if p.athlete_id == selected_athlete_id), None)
            if selected_profile:
                with st.container(border=True):
                    st.markdown(f"#### 👤 Active Athlete: {selected_profile.full_name}")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Age", selected_profile.age)
                    col2.metric("Height", f"{selected_profile.height_cm} cm")
                    col3.metric("Level", selected_profile.swimming_level)
                    col4.metric("Preferred Stroke", selected_profile.preferred_stroke)
    else:
        st.info("ℹ️ **Personal Account Upload:** This analysis will be saved to your user account and not treated as a guest session.")

    # Sidebar: Video Upload
    st.sidebar.markdown("### Video Upload")
    uploaded_file = st.sidebar.file_uploader(
            "Upload Swimming Video", 
        type=["mp4", "mov", "avi"],
        label_visibility="collapsed"
    )

    if uploaded_file is not None:
        safe_log(f"VIDEO UPLOADED: {uploaded_file.name}")
        st.subheader("Original Video")
        
        # Use secure file handling to prevent path traversal and enforce directory bounds
        from utils.file_security import sanitize_and_resolve_path
        
        _upload_fingerprint = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get("_upload_fingerprint") != _upload_fingerprint:
            st.session_state.completed_analysis = None
            st.session_state.analysis_state = "ready"
            try:
                temp_input_path = sanitize_and_resolve_path(
                    user_filename=uploaded_file.name,
                    target_dir=str(config.input_dir),
                    generate_unique=True
                )
                with open(temp_input_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.session_state["_upload_fingerprint"] = _upload_fingerprint
                st.session_state["_temp_input_path"] = temp_input_path
            except ValueError as e:
                st.error(f"Security error: {e}")
                st.stop()
        else:
            temp_input_path = st.session_state["_temp_input_path"]
            
        # Read detected FPS & Duration
        from utils.video_utils import get_video_info
        video_info = get_video_info(str(temp_input_path))
        detected_fps = video_info.get("fps", 30.0) if video_info.get("fps", 0) > 0 else 30.0
        frame_count = video_info.get("frame_count", 0)
        video_duration_s = frame_count / detected_fps if (detected_fps > 0 and frame_count > 0) else 0.0

        # Video Duration Warning Banner
        if video_duration_s > config.max_recommended_duration_s:
            st.warning(f"⚠️ **Long Video Notice ({video_duration_s:.1f}s):** For optimal biomechanical accuracy and fast processing speed, clips between 15–30 seconds are recommended.")
        elif video_duration_s > 0:
            st.caption(f"📹 Video Duration: {video_duration_s:.1f}s ({frame_count} frames @ {detected_fps:.1f} FPS)")

        # Sidebar settings
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Video Settings")
        
        stroke_placeholder = "-- Select Swimming Stroke --"
        stroke_options = [stroke_placeholder, "Freestyle", "Backstroke", "Breaststroke", "Butterfly"]
        selected_stroke = st.sidebar.selectbox("Select Swimming Stroke *", stroke_options, index=0, key="stroke_type_select")
        
        selected_stride = 1
        st.session_state["_selected_frame_stride"] = selected_stride

        # Read app config
        import yaml
        app_config = {}
        try:
            with open(config.app_config_path, 'r') as f:
                app_config = yaml.safe_load(f)
        except Exception:
            pass
            
        analysis_cfg = app_config.get('analysis', {})
        fps_override = analysis_cfg.get('fps_override')
            
        # Validate FPS bounds
        if not (10 <= detected_fps <= 240):
            st.sidebar.warning(f"Detected FPS ({detected_fps:.1f}) seems unusual. Defaulting to 30.")
            detected_fps = 30.0
            
        default_effective_fps = float(fps_override) if fps_override is not None else float(detected_fps)
        effective_fps = st.sidebar.number_input("Effective FPS", min_value=10.0, max_value=240.0, value=default_effective_fps, step=1.0)
        
        st.sidebar.info(f"Detected FPS: {detected_fps:.2f} | Full Natural FPS (Stride 1)")

        st.sidebar.markdown("### Visualization")
        viz_mode = st.sidebar.selectbox("Mode", ["User Mode", "Coach Mode", "Developer Mode"])
        
        st.sidebar.markdown("### Video Quality Safety")
        vqa_mode = st.sidebar.selectbox(
            "VQA Safety Mode",
            ["Strict (Abort on Critical)", "Warn and continue on Critical"],
            index=0,
            help="Choose whether the analysis should stop immediately when the video quality is classified as Critical."
        )
        allow_vqa_critical_override = (vqa_mode == "Warn and continue on Critical") or st.session_state.get("vqa_critical_override", False)
        
        trajectory_duration_sec = 2.0
        if viz_mode == "Developer Mode":
            traj_option = st.sidebar.selectbox("Trajectory Length", ["Short (1s)", "Normal (2s)", "Long (4s)"], index=1)
            if traj_option == "Short (1s)":
                trajectory_duration_sec = 1.0
            elif traj_option == "Long (4s)":
                trajectory_duration_sec = 4.0
            forced_conf_input = st.sidebar.number_input("Force Stroke Conf (Dev)", min_value=0.0, max_value=1.0, value=1.0, step=0.1)

        # Use native, high-performance Streamlit video renderer
        video_render_mode = "Native Streamlit (st.video)"

        current_role = st.session_state.current_coach.role if st.session_state.get("current_coach") else None

        if "analysis_state" not in st.session_state:
            st.session_state.analysis_state = "ready"
        if "stroke_result" not in st.session_state:
            st.session_state.stroke_result = None
        if "completed_analysis" not in st.session_state:
            st.session_state.completed_analysis = None

        if current_role == "admin" and st.session_state.get("trigger_sci_db_update", False):
            st.markdown("---")
            st.info("🔄 Initiating ONE Scientific Literature Database Update Transaction...")
            st.caption("Searching PubMed, PMC, Europe PMC for peer-reviewed swimming literature, verifying provenance, and rebuilding coverage matrix...")

            prog_bar = st.progress(0, text="Starting scientific database update...")
            prog_status = st.empty()

            def ui_progress_cb(msg: str, pct: int):
                prog_bar.progress(pct, text=f"{msg} ({pct}%)")
                prog_status.markdown(f"⏳ **{msg}**")

            from services.scientific_updater_service import ScientificUpdaterService
            updater = ScientificUpdaterService()
            res = updater.run_update_cycle(progress_callback=ui_progress_cb)

            st.session_state["trigger_sci_db_update"] = False
            st.session_state["last_sci_db_update_res"] = res
            st.rerun()

        if "last_sci_db_update_res" in st.session_state:
            res = st.session_state["last_sci_db_update_res"]
            verdict = res.get('verdict', '')
            if res.get('database_changed') is False and verdict == "SUCCESSFUL_UPDATE":
                st.success("✓ **Scientific Database Already Up To Date** — No new literature found.")
            elif verdict == "INTERNET_UNAVAILABLE":
                st.warning(f"⚠️ **Internet Literature Update Could Not Be Completed** — External scientific sources were unavailable. Previous verified database preserved intact. (Version: `{res.get('previous_version', '2026.08.08')}`)")
            elif verdict == "UPDATE_ABORTED":
                st.error(f"❌ **Scientific Database Update Aborted** — Safety validation tests failed. Previous verified database preserved intact. (Version: `{res.get('previous_version', '2026.08.08')}`)")
            else:
                st.success(f"✓ **Scientific Database Update Complete!** (Version: `{res.get('previous_version')}` → `{res.get('new_version')}`)")

            with st.container(border=True):
                st.markdown("### 🔬 Scientific Database Update Summary")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Sources Discovered", res.get("sources_discovered", 0))
                c2.metric("New Sources", res.get("new_sources", 0))
                c3.metric("Full-Text Verified", res.get("full_text_verified", 0))
                c4.metric("Evidence Candidates", res.get("evidence_candidates", 0))

                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Evidence Accepted", res.get("evidence_accepted", 0))
                c6.metric("Review Required", res.get("evidence_review_required", 0))
                c7.metric("Rejected", res.get("evidence_rejected", 0))
                c8.metric("Benchmarks Added", res.get("benchmarks_added", 0))

                c9, c10, c11, c12 = st.columns(4)
                c9.metric("Benchmarks Updated", res.get("benchmarks_updated", 0))
                c10.metric("Newly Verified Cohorts", res.get("newly_verified_cohorts", 0))
                c11.metric("Insufficient Evidence Cohorts", res.get("remaining_insufficient_cohorts", 0))
                c12.metric("Database Changed", "Yes" if res.get("database_changed") else "No")

                test_status_str = "PASS (100%)" if res.get('tests_passed') else ("N/A (Offline)" if verdict == "INTERNET_UNAVAILABLE" else "FAIL")
                st.caption(f"**Update Status**: `{res.get('verdict')}` | **Tests**: `{test_status_str}` | **Timestamp**: {res.get('timestamp')}")
            st.markdown("---")

        if st.sidebar.button("Analyze Swimming Technique", type="primary"):
            if selected_stroke == stroke_placeholder:
                st.sidebar.error("⚠️ **Action Required:** Please select a swimming stroke type before starting analysis!")
            else:
                from models.data_models import StrokeType, StrokeSelection
                st.session_state.analysis_state = "processing"
                st.session_state["_is_analyzing_now"] = True
                st.session_state["vqa_critical_override"] = False
                import time
                st.session_state["_processing_start_time"] = time.time()
                st.session_state.stroke_result = StrokeSelection(
                    selected_stroke=StrokeType(selected_stroke),
                    selection_source="USER"
                )
                st.session_state.completed_analysis = None
                st.rerun()

        # Run Video Processing if required
        if st.session_state.analysis_state == "processing" and st.session_state.completed_analysis is None:
            if not st.session_state.get("_is_analyzing_now", False):
                st.session_state.analysis_state = "ready"
                st.warning("⚠️ Video analysis was interrupted by a browser refresh. Please click 'Analyze Swimming Technique' to start.")
                st.rerun()

            st.markdown("---")
            st.subheader("Analysis Processing")
            
            res_stroke = getattr(st.session_state, 'stroke_result', None)
            if res_stroke and hasattr(res_stroke, 'selected_stroke') and res_stroke.selected_stroke:
                p_name = res_stroke.selected_stroke.value.title()
                p_icon = STROKE_ICONS.get(p_name, "🏊")
                st.success(f"🎯 **Analyzing Swimming Stroke:** {p_icon} **{p_name}**")
            
            debug_placeholder = st.empty()
            progress_bar = st.progress(0, text="Starting video analysis...")
            progress_status = st.empty()
            
            # Get total frame count upfront for the progress bar
            from utils.video_utils import get_video_info
            _vinfo = get_video_info(str(temp_input_path))
            _total_frames = int(_vinfo.get("frame_count", 0))
            
            def debug_callback(frame_data, confidence, mode):
                idx = frame_data.frame_index
                # Update progress bar every 30 frames (~1 sec of video) to reduce UI thread overhead
                if idx % 30 == 0 or idx == 1:
                    if _total_frames > 0:
                        pct = min(int((idx / _total_frames) * 100), 99)
                        progress_bar.progress(pct, text=f"Processing frame {idx}/{_total_frames} ({pct}%)...")
                    else:
                        progress_status.markdown(f"⏳ Processing frame **{idx}**...")
                if mode == "Developer Mode" and idx % 30 == 0:
                    with debug_placeholder.container():
                        cols = st.columns(6)
                        cols[0].metric("Frame", idx)
                        cols[1].metric("Time (ms)", frame_data.timestamp_ms)
                        cols[2].metric("Phase", frame_data.stroke_phase)
                        cols[3].metric("Conf", f"{confidence:.2f}")
                        
                        if frame_data.angles.left_elbow and frame_data.angles.left_elbow.valid:
                            cols[4].metric("L. Elbow", f"{frame_data.angles.left_elbow.value:.1f}")
                        if frame_data.angles.right_elbow and frame_data.angles.right_elbow.valid:
                            cols[5].metric("R. Elbow", f"{frame_data.angles.right_elbow.value:.1f}")
            
            vqa_placeholder = st.empty()
            def vqa_callback(vqa_result):
                vqa_placeholder.empty()
                with vqa_placeholder.container():
                    if vqa_result.quality_class == "Critical":
                        st.error(vqa_result.warning_message)
                    elif vqa_result.quality_class == "Poor":
                        st.warning(vqa_result.warning_message)
                        
                    st.markdown(f"**Video Quality Score:** {vqa_result.overall_score}/100 ({vqa_result.quality_class})")
                    st.markdown(f"**Analysis Confidence:** {vqa_result.analysis_confidence}")
                    
                    with st.expander("Diagnostic Report Breakdown"):
                        for crit in vqa_result.criteria:
                            status = "✅ PASS" if crit.passed else "❌ FAIL"
                            st.markdown(f"#### {status} - {crit.name} (Score: {crit.score}, Weight: {crit.weight*100:.0f}%)")
                            if not crit.passed:
                                st.markdown(f"**Why it matters:** {crit.explanation_matters}")
                                st.markdown(f"**Effect on analysis:** {crit.explanation_effect}")
                                st.markdown(f"**Recommendation:** {crit.explanation_fix}")
                            st.markdown("---")
            
            try:
                with st.spinner(f"Analyzing video at {effective_fps} FPS..."):
                    analysis_service = AnalysisService()
                    selected_stride = st.session_state.get("_selected_frame_stride", 2)
                    
                    safe_log("ENTER: process_video")
                    output_video_path, json_report_path, metadata_path, analysis_result = analysis_service.process_video(
                        str(temp_input_path), 
                        effective_fps,
                        visualization_mode=viz_mode,
                        progress_callback=debug_callback,
                        vqa_callback=vqa_callback,
                        trajectory_duration_sec=trajectory_duration_sec,
                        stroke_detection=st.session_state.stroke_result,
                        athlete_id=selected_athlete_id if selected_athlete_id != "None" else None,
                        frame_stride=selected_stride,
                        allow_vqa_critical_override=allow_vqa_critical_override,
                        coach_id=getattr(st.session_state.get("current_coach"), "coach_id", None)
                    )
                    safe_log("EXIT: process_video")
                    progress_bar.progress(100, text="✅ Analysis complete!")
                    progress_status.empty()
                    
                    # --- Post-analysis quality gates ---
                    # Only abort (st.stop) if the analysis was early-halted with no output.
                    # If we have a real output_video_path, show warnings but ALWAYS display results.
                    if analysis_result.vqa_result and analysis_result.vqa_result.quality_class == "Critical":
                        if not output_video_path and not allow_vqa_critical_override:
                            safe_log("EXIT: process_video_aborted_vqa_critical_early_halt")
                            st.error("⛔ Video quality is too poor to analyze. Please upload a clearer video.")
                            if st.button("Continue anyway with Critical VQA"):
                                st.session_state["vqa_critical_override"] = True
                                st.rerun()
                            st.stop()
                        elif not output_video_path and allow_vqa_critical_override:
                            safe_log("WARN: critical_vqa_override_no_output")
                            st.error("⛔ Video quality is critical and no valid analysis output could be produced even with override.")
                            st.stop()
                        else:
                            safe_log("WARN: final_vqa_critical_but_results_available")
                            # Warning already shown by vqa_callback — no duplicate needed
                        
                    if getattr(analysis_result, 'consistency', None) and analysis_result.consistency.validation_status == "Critical":
                        safe_log("WARN: consistency_critical_but_results_available")
                        for w in analysis_result.consistency.warnings:
                            st.warning(f"⚠️ Consistency Warning: {w}")

                    # Automatically save Analysis History session
                    try:
                        import time
                        from datetime import datetime
                        history_service = AnalysisHistoryService()
                        session = AnalysisSession(
                            athlete_id=selected_athlete_id if selected_athlete_id != "None" else None,
                            account_id=st.session_state.current_coach.coach_id if st.session_state.get("current_coach") else None,
                            analysis_timestamp=datetime.now().isoformat(),
                            original_video_filename=uploaded_file.name,
                            processed_video_filename=Path(output_video_path).name if output_video_path else "",
                            metadata_json_path=str(metadata_path),
                            report_json_path=str(json_report_path),
                            performance_score=analysis_result.report.overall_score if analysis_result.report else None,
                            scientific_confidence=analysis_result.consistency.scientific_confidence if getattr(analysis_result, 'consistency', None) else "Low",
                            completed_cycles=analysis_result.stroke_statistics.completed_cycles if analysis_result.stroke_statistics else 0,
                            stroke_type=st.session_state.stroke_result.selected_stroke.value,
                            processing_time_seconds=st.session_state.get("_processing_end_time", time.time()) - st.session_state.get("_processing_start_time", time.time())
                        )
                        history_service.create_session(session, current_coach_id)
                    except Exception as e:
                        safe_log(f"ERROR: Failed to save analysis history: {e}")

                    st.session_state["_is_analyzing_now"] = False
                    st.session_state.completed_analysis = {
                        "output_video_path": output_video_path,
                        "json_report_path": json_report_path,
                        "metadata_path": metadata_path,
                        "analysis_result": analysis_result
                    }
                    st.session_state.analysis_state = "results_ready"
                    st.rerun()

            except Exception as e:
                import traceback
                err_msg = traceback.format_exc()
                logger.error(f"An error occurred during analysis: {str(e)}")
                st.error(f"An error occurred during analysis: {str(e)}\n\n```python\n{err_msg}\n```")

        # Render Completed Analysis Results via Modular Functions
        if st.session_state.completed_analysis is not None:
            try:
                comp = st.session_state.completed_analysis
                output_video_path = comp["output_video_path"]
                json_report_path = comp["json_report_path"]
                metadata_path = comp["metadata_path"]
                analysis_result = comp["analysis_result"]

                st.success("Analysis complete!")
                st.markdown("---")
                
                # 1. Executive Summary Hero Card (10-Second Glanceability)
                render_executive_summary_card(analysis_result)
                
                st.markdown("---")

                # 2. Reorganized Full-Width SaaS Tabs (Zero Scrolling Clutter)
                tab_overview, tab_biomech, tab_benchmarks, tab_3d, tab_charts, tab_downloads = st.tabs([
                    "📋 Overview", 
                    "🧬 Biomechanics", 
                    "📊 Population Benchmarks", 
                    "🧊 3D Analysis", 
                    "📈 Raw Data Charts", 
                    "📥 Downloads"
                ])

                with tab_overview:
                    st.markdown("### 🎥 Session Overview & Quality Consistency")
                    col_vid, col_cons = st.columns([1, 1])
                    with col_vid:
                        render_video_section(output_video_path, video_render_mode)
                    with col_cons:
                        render_summary(analysis_result)
                        st.markdown("---")
                        render_consistency(analysis_result)

                with tab_biomech:
                    st.markdown("### 🧬 Biomechanical Performance & Technical Flaws")
                    render_report_tab(analysis_result)

                with tab_benchmarks:
                    st.markdown("### 📊 Population Reference Values & Evidence Cards")
                    bm_res = getattr(analysis_result, 'benchmark_result', None)
                    profile = st.session_state.get("current_profile") or (
                        AthleteService().load_profile(selected_athlete_id, current_coach_id) if selected_athlete_id != "None" else None
                    )
                    
                    from app.ui.benchmark_ui import render_population_benchmark_cards
                    render_population_benchmark_cards(bm_res, athlete_profile=profile)

                    if bm_res and getattr(bm_res, 'comparisons', None):
                        st.markdown("---")
                        st.markdown("#### 🔔 Bell Curve Population Inspector")
                        from app.ui.charts import create_bell_curve_chart
                        selected_m = st.selectbox("Select Metric for Bell Curve Distribution", [m for m in bm_res.comparisons.keys() if m != "performance_score"])
                        if selected_m in bm_res.comparisons:
                            c_m = bm_res.comparisons[selected_m]
                            st.plotly_chart(
                                create_bell_curve_chart(selected_m, c_m.raw_value, c_m.population_mean, c_m.population_std, c_m.elite_mean),
                                width="stretch"
                            )
                    else:
                        st.info("Population benchmarks not calculated for this video.")

                with tab_3d:
                    st.markdown("### 🧊 Pose-Relative 3D Spatial Biomechanics & Core Rotation")
                    st.caption("Derived from pose-relative 3D coordinate vectors (MediaPipe Spatial Landmarks; monocular depth z is an uncalibrated relative estimate).")

                    gm = getattr(analysis_result, 'global_metrics', {}) or {}
                    b_roll_3d = gm.get("body_roll_3d")
                    torsion_3d = gm.get("core_torsion_3d")

                    c1, c2 = st.columns(2)
                    c1.metric("Pose-Relative 3D Body Roll", f"{b_roll_3d.value:.1f}°" if (b_roll_3d and b_roll_3d.valid and b_roll_3d.value is not None) else "UNAVAILABLE")
                    c2.metric("3D Core Torsion", f"{torsion_3d.value:.1f}°" if (torsion_3d and torsion_3d.valid and torsion_3d.value is not None) else "UNAVAILABLE")

                    from app.ui.charts import create_3d_skeleton_chart, create_3d_torsion_chart
                    st.plotly_chart(create_3d_torsion_chart(analysis_result.frames), width="stretch")

                    st.markdown("---")
                    st.markdown("#### 🔄 360° Rotatable 3D Skeleton Viewer")
                    if analysis_result.frames:
                        selected_frame_num = st.slider(
                            "Inspect 3D Pose Frame", 
                            min_value=0, 
                            max_value=len(analysis_result.frames) - 1, 
                            value=0,
                            key="3d_frame_slider"
                        )
                        target_frame = analysis_result.frames[selected_frame_num]
                        raw_lm = getattr(target_frame, 'raw_landmarks', None)
                        
                        st.plotly_chart(
                            create_3d_skeleton_chart(raw_lm, target_frame.frame_index),
                            width="stretch"
                        )

                with tab_charts:
                    st.markdown("### 📈 Joint Angle Timeseries & Phase Summary")
                    render_raw_data_tab(analysis_result)

                with tab_downloads:
                    st.markdown("### 📥 Session Export Center")
                    st.caption("Download annotated MP4 video, PDF report, or raw JSON data files.")
                    selected_profile = next((p for p in profiles if p.athlete_id == selected_athlete_id), None) if 'profiles' in locals() else None
                    render_download_buttons(output_video_path, json_report_path, metadata_path, analysis_result=analysis_result, profile=selected_profile)
                        
            except Exception as e:
                import traceback
                err_msg = traceback.format_exc()
                logger.error(f"An error occurred during rendering: {str(e)}")
                st.error(f"An error occurred during rendering: {str(e)}\n\n```python\n{err_msg}\n```")


# Standard Streamlit entry point: call main() at module level.
# Do NOT use `if __name__ == "__main__"` — Streamlit re-executes the
# entire script on every rerun, so the guard IS true each time, which
# caused a new heartbeat thread to be spawned on every rerun.
#
# CRITICAL: Do NOT set threading.excepthook here.
# Streamlit uses background threads for WebSocket heartbeats and the
# file watcher. If threading.excepthook is overridden, those threads'
# exceptions bypass Streamlit's own recovery logic, silently killing
# the server without any Python traceback.
main()
