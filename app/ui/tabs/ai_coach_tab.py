"""
AI Coach Tab Presenter for SwimAnalyzer AI (Step 71).
Renders structured AI coaching feedback while strictly isolating it from
original measured biomechanics and displaying mandatory scientific disclaimers.
"""
import streamlit as st
from typing import Optional, Any
from core.config import config
from core.logger import setup_logger
from services.ai_coach_service import AICoachService
from models.ai_coach_models import AICoachFeedback, DEFAULT_AI_COACH_DISCLAIMER

logger = setup_logger(__name__)


def render_ai_coach_tab(analysis_result: Any, athlete_profile: Optional[Any] = None):
    """
    Renders the AI Coach tab.
    Separates measured facts from AI-generated coaching recommendations.
    """
    st.markdown("### 🤖 AI Coaching Interpretation & Recommendations")
    st.caption("AI-assisted analysis providing structured technique observations and coaching drills.")

    # 1. Mandatory Scientific Disclaimer Banner
    st.warning(f"⚠️ **Scientific Disclaimer:** {DEFAULT_AI_COACH_DISCLAIMER}")

    # Check if feedback already generated
    feedback: Optional[AICoachFeedback] = getattr(analysis_result, "ai_coach_feedback", None)

    # If feedback not yet generated, attempt generation via service
    if feedback is None:
        service = AICoachService()
        if not config.ai_coach_enabled:
            st.info(
                "ℹ️ **AI Coach is currently disabled in configuration.**\n\n"
                "To enable automated coaching interpretations, set `SWIM_ANALYZER_AI_COACH_ENABLED=true` in your environment "
                "or `.env` file and provide a valid Hugging Face token (`SWIM_ANALYZER_HF_TOKEN`).\n\n"
                "Core video analysis and measured biomechanics remain 100% operational."
            )
            return

        with st.spinner("Generating AI coaching interpretation..."):
            try:
                feedback = service.generate_coaching_feedback(analysis_result, athlete_profile=athlete_profile)
            except Exception as e:
                logger.error(f"Error generating AI coach feedback: {e}")
                st.error(f"Failed to generate coaching interpretation: {e}")
                return

    # If feedback is disabled status
    if feedback.status == "disabled":
        st.info(
            "ℹ️ **AI Coach is currently disabled in configuration.**\n\n"
            "Set `SWIM_ANALYZER_AI_COACH_ENABLED=true` to enable automated coaching feedback."
        )
        return

    # If fallback status
    if feedback.status == "fallback":
        st.info(
            f"ℹ️ **Notice:** Running in fallback mode. {feedback.error_message or 'External provider unavailable.'}\n"
            "Displaying safe, rule-based observations derived strictly from measured metrics."
        )

    # 2. Executive Coaching Summary Card
    st.markdown("---")
    with st.container(border=True):
        col_hdr, col_meta = st.columns([3, 1])
        with col_hdr:
            st.markdown("#### 📋 Executive Coaching Summary")
            st.markdown(feedback.summary)
        with col_meta:
            st.caption(f"**Provider:** `{feedback.provider}`")
            if feedback.model:
                st.caption(f"**Model:** `{feedback.model}`")
            st.caption(f"**Status:** `{feedback.status.upper()}`")

    st.markdown("---")

    # 3. Strengths and Areas for Improvement
    col_str, col_flaw = st.columns(2)

    with col_str:
        with st.container(border=True):
            st.markdown("#### ✅ Technique Strengths")
            if feedback.strengths:
                for s in feedback.strengths:
                    st.markdown(f"- {s}")
            else:
                st.markdown("_No specific technical strengths highlighted._")

    with col_flaw:
        with st.container(border=True):
            st.markdown("#### ⚠️ Areas for Improvement")
            if feedback.areas_for_improvement:
                for a in feedback.areas_for_improvement:
                    st.markdown(f"- {a}")
            else:
                st.markdown("_No specific technical flaws highlighted._")

    # 4. Actionable Coach Recommendations / Drills
    st.markdown("---")
    with st.container(border=True):
        st.markdown("#### 🏊 Recommended Drills & Technique Focus")
        if feedback.coach_recommendations:
            for idx, rec in enumerate(feedback.coach_recommendations, 1):
                st.markdown(f"**{idx}.** {rec}")
        else:
            st.markdown("_No specific drill recommendations available._")

    # 5. Metric-by-Metric Interpretations
    if feedback.metric_interpretations:
        st.markdown("---")
        with st.container(border=True):
            st.markdown("#### 🔍 Metric Interpretations & Evidence Levels")
            for interp in feedback.metric_interpretations:
                ev_color = "#00D26A" if interp.evidence_level == "measured" else "#FF8C00"
                col_m, col_ev = st.columns([4, 1])
                with col_m:
                    st.markdown(f"**`{interp.metric}`**: {interp.interpretation}")
                with col_ev:
                    st.markdown(f"<span style='color:{ev_color}; font-weight:bold;'>[{interp.evidence_level.upper()}]</span>", unsafe_allow_html=True)

    # 6. Biomechanical Limitations & Reliability Disclaimers
    if feedback.limitations:
        st.markdown("---")
        with st.expander("ℹ️ Scientific Limitations & Biomechanical Caveats", expanded=False):
            for lim in feedback.limitations:
                st.markdown(f"- {lim}")
