import os
import streamlit as st
from services.athlete_service import AthleteService
from services.analysis_history_service import AnalysisHistoryService
from services.pdf_report_service import PDFReportService
from app.ui.charts import create_performance_trend_chart, create_cycles_trend_chart

def render_athlete_profile_page(current_coach_id: str):
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
        st.write("")
        history_service = AnalysisHistoryService()
        history = history_service.get_sessions_by_athlete(athlete_id, current_coach_id)
        
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
            st.markdown("#### Longitudinal Progress")
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.plotly_chart(create_performance_trend_chart(history), width='stretch')
            with chart_col2:
                st.plotly_chart(create_cycles_trend_chart(history), width='stretch')

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
