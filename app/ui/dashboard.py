import streamlit as st
import pandas as pd
import plotly.express as px
from services.athlete_service import AthleteService
from services.analysis_history_service import AnalysisHistoryService

def render_dashboard_page():
    st.title("📊 Coach Dashboard")
    st.markdown("Overview of all athletes and team performance.")
    
    athlete_service = AthleteService()
    history_service = AnalysisHistoryService()
    
    current_coach = st.session_state.get("current_coach")
    if not current_coach:
        st.error("Authentication required")
        return
        
    profiles = athlete_service.get_all_profiles(coach_id=current_coach.coach_id)
    if getattr(current_coach, "role", "coach") == "admin":
        all_sessions = history_service.get_all_sessions(principal=current_coach)
    else:
        all_sessions = history_service.get_sessions_by_account(account_id=current_coach.coach_id)
    
    if not profiles:
        st.info("No athletes registered yet. Go to the 'Athletes' page to add some.")
        return
        
    # --- Data Aggregation ---
    total_athletes = len(profiles)
    total_sessions = len(all_sessions)
    
    # Group all_sessions by athlete_id in memory (preserving timestamp order)
    sessions_by_athlete = {}
    for s in all_sessions:
        if s.athlete_id:
            sessions_by_athlete.setdefault(s.athlete_id, []).append(s)

    # Calculate latest score for each athlete
    athlete_stats = []
    total_score_sum = 0
    athletes_with_sessions = 0
    
    for p in profiles:
        sessions = sessions_by_athlete.get(p.athlete_id, [])
        latest_score = None
        last_analysis_date = "N/A"
        
        if sessions:
            latest_score = sessions[0].performance_score
            last_analysis_date = sessions[0].analysis_timestamp.split("T")[0]
            # P0-8: only count sessions with a real (non-None) score in team averages
            if latest_score is not None:
                total_score_sum += latest_score
                athletes_with_sessions += 1

            
        athlete_stats.append({
            "Athlete Name": p.full_name,
            "Level": p.swimming_level,
            "Stroke": p.preferred_stroke,
            "Latest Technique Score": round(latest_score, 1) if latest_score is not None else None,
            "Sessions Count": len(sessions),
            "Last Analysis": last_analysis_date
        })
        
    avg_team_score = (total_score_sum / athletes_with_sessions) if athletes_with_sessions > 0 else None
    
    # --- Top Metrics ---
    st.markdown("### 📈 Team Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Athletes", total_athletes)
    c2.metric("Total Analyses", total_sessions)
    c3.metric("Avg Team Technique Score", f"{avg_team_score:.1f}" if avg_team_score is not None else "N/A")
    
    st.markdown("---")
    
    # --- Leaderboard Chart ---
    st.markdown("### 🏆 Available Technique Leaderboard (Latest Measured Sessions)")
    st.caption("ℹ️ Scores represent available technique measurements from completed analyses, not validated overall athletic rankings.")
    
    # Filter only athletes with scores for the chart
    chart_data = [stat for stat in athlete_stats if stat["Latest Technique Score"] is not None]
    
    if chart_data:
        df_chart = pd.DataFrame(chart_data)
        df_chart = df_chart.sort_values(by="Latest Technique Score", ascending=True) # Ascending for horizontal bar
        
        fig = px.bar(
            df_chart, 
            x="Latest Technique Score", 
            y="Athlete Name",
            orientation='h',
            color="Latest Technique Score",
            color_continuous_scale="Viridis",
            text="Latest Technique Score"
        )
        fig.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=30, b=0),
            xaxis_title="Available Technique Score (0-100)",
            yaxis_title="",
            plot_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No analysis data available yet to display the leaderboard.")
        
    st.markdown("---")
    
    # --- Athlete Overview Table ---
    st.markdown("### 📋 Athlete Directory")
    df_table = pd.DataFrame(athlete_stats)
    
    st.dataframe(
        df_table,
        width="stretch",
        column_config={
            "Latest Technique Score": st.column_config.ProgressColumn(
                "Latest Technique Score",
                help="The available technique score from the most recent analysis session",
                format="%.1f",
                min_value=0,
                max_value=100,
            ),
            "Sessions Count": st.column_config.NumberColumn(
                "Analyses",
                help="Total number of video analyses",
            )
        },
        hide_index=True
    )
